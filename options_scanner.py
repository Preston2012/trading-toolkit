#!/usr/bin/env python3
"""
OPTIONS SCANNER v5 — Smart, non-repeating, paper-trading, properly sized.

WHAT IT DOES:
- Scans calls AND puts across 15 ETFs every 2 hours
- Ranks by composite score (0-100) not just letter grades
- Sends TOP 5 CALLS + TOP 5 PUTS to Telegram ONCE per cycle
- Only re-alerts if rankings change or new entry appears
- Paper trades all Grade A picks automatically in background
- Tracks simulated P&L in SQLite — weekly summary to TG
- Position sizing based on $200-500 budget (10-50+ contracts)
- Exit ladder: recover basis at 2x, then staged exits
- Trump scanner: FRESH headlines only, deduped by hash
- IV rank: finds historically cheap options
"""
import hashlib
import json
import os
import sqlite3
import time
from datetime import datetime, timedelta

import requests
import schedule
import yfinance as yf

from core.telegram import send_tg

FINNHUB_KEY = os.environ.get("FINNHUB_KEY", "")
SEEN_FILE = "/root/data/seen_headlines.json"
LAST_TOP5_FILE = "/root/data/last_top5.json"
PAPER_DB = "/root/data/paper_trades.db"
PLAY_BUDGET = 400

THESIS_MAP = {
    "XLE": {"call": "Oil war escalation. Hormuz closed, Houthis active. $110 WTI = XLE $70+",
            "put": "Ceasefire = oil crashes 20% = XLE drops to $52-55",
            "catalyst": "Apr 6 Trump deadline, Kharg Island, ceasefire",
            "max_otm": 15, "min_vol": 20, "min_oi": 50},
    "JETS": {"call": "Peace hedge. Ceasefire = oil crash = airlines +20-30%",
             "put": "War extends = jet fuel $7+ = airlines bleed 15%",
             "catalyst": "Iran deal/ceasefire, jet fuel, airline guidance",
             "max_otm": 25, "min_vol": 15, "min_oi": 30},
    "TLT": {"call": "Oil kills economy -> recession -> Fed cuts -> bonds +8-12%",
            "put": "Inflation hot from oil -> Fed holds -> bonds -5%",
            "catalyst": "FOMC Apr 28-29, CPI, recession signals",
            "max_otm": 10, "min_vol": 50, "min_oi": 50},
    "XBI": {"call": "Biotech FDA binary events with KNOWN PDUFA date only",
            "put": "Rate fear crushes speculative biotech",
            "catalyst": "FDA PDUFA calendar dates",
            "max_otm": 15, "min_vol": 30, "min_oi": 50},
    "KRE": {"call": "Regional banks recover on Fed cut + oil drop",
            "put": "Oil recession = loan defaults = bank crisis",
            "catalyst": "Fed decision, oil reversal, bank earnings",
            "max_otm": 18, "min_vol": 10, "min_oi": 30},
    "GDX": {"call": "Gold miners surge on rate cuts + dollar weakness",
            "put": "Dollar strength = gold drops = miners crushed",
            "catalyst": "Fed pivot, dollar index, gold price",
            "max_otm": 15, "min_vol": 10, "min_oi": 20},
    "IBIT": {"call": "BTC depressed by war risk-off. Peace = BTC $85K+ = IBIT rips",
             "put": "Crypto winter on macro fear + regulation",
             "catalyst": "Ceasefire, ETF flows, Fed signals",
             "max_otm": 20, "min_vol": 20, "min_oi": 30},
    "SMH": {"call": "Semis oversold. AI capex intact. Mean reversion 15%",
            "put": "Trade war + chip bans = semis -15% more",
            "catalyst": "NVDA/AMD earnings, trade deals",
            "max_otm": 12, "min_vol": 50, "min_oi": 100},
    "XLF": {"call": "Financials pop on rate cut clarity",
            "put": "Recession = loan losses = financials dump",
            "catalyst": "FOMC, yield curve, bank earnings",
            "max_otm": 12, "min_vol": 20, "min_oi": 30},
    "SPY": {"call": "War ends = broad relief rally",
            "put": "Oil recession + Fed stuck = -10-15%",
            "catalyst": "Ceasefire, FOMC, GDP, earnings",
            "max_otm": 8, "min_vol": 100, "min_oi": 200},
    "XOP": {"call": "Oil E&P pure play. Higher beta than XLE",
            "put": "Peace = oil crash = XOP -25%",
            "catalyst": "Same as XLE amplified",
            "max_otm": 15, "min_vol": 20, "min_oi": 30},
    "ITA": {"call": "Defense spending up. Election cycle boost",
            "put": "Peace = defense cut narrative",
            "catalyst": "Defense budget, contracts, election",
            "max_otm": 12, "min_vol": 10, "min_oi": 20},
    "QQQ": {"call": "Tech rebounds on peace/rate cut. AI resumes",
            "put": "Stagflation = tech crushed",
            "catalyst": "Tech earnings May, Fed, trade war",
            "max_otm": 10, "min_vol": 100, "min_oi": 200},
    "XLY": {"call": "Consumer rebound post-crisis",
            "put": "Oil kills spending. Retail misses",
            "catalyst": "Consumer data, retail earnings",
            "max_otm": 12, "min_vol": 20, "min_oi": 30},
}


def get_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return json.load(f)
    return {}


def save_seen(s):
    with open(SEEN_FILE, "w") as f:
        json.dump(s, f)


def get_technicals(ticker):
    try:
        t = yf.Ticker(ticker)
        h = t.history(period="3mo")
        if len(h) < 20:
            return {}
        c = h["Close"]
        delta = c.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = round((100 - (100 / (1 + gain / loss))).iloc[-1], 1)
        ema20 = round(c.ewm(span=20).mean().iloc[-1], 2)
        ema50 = round(c.ewm(span=50).mean().iloc[-1], 2)
        trend = "BULL" if ema20 > ema50 else "BEAR"
        hi20 = round(c.tail(20).max(), 2)
        lo20 = round(c.tail(20).min(), 2)
        return {"rsi": rsi, "trend": trend, "ema20": ema20, "ema50": ema50,
                "hi20": hi20, "lo20": lo20, "support": round(lo20, 2), "resist": round(hi20, 2)}
    except Exception:
        return {}


def composite_score(premium, vol, oi, days, otm_pct, iv, tech, info, side):
    """0-100 score. Higher = better opportunity."""
    s = 0
    if oi > 1000: s += 25
    elif oi > 500: s += 22
    elif oi > 200: s += 18
    elif oi > 50: s += 12
    elif oi > 20: s += 6
    if vol > 500: s += 20
    elif vol > 100: s += 16
    elif vol > 50: s += 12
    elif vol > 20: s += 8
    if 0.03 <= premium <= 0.15: s += 20
    elif 0.15 < premium <= 0.40: s += 16
    elif 0.40 < premium <= 0.75: s += 12
    elif 0.75 < premium <= 1.50: s += 8
    if 30 <= days <= 60: s += 15
    elif 60 < days <= 90: s += 12
    elif 25 <= days < 30: s += 8
    elif 90 < days <= 120: s += 6
    if tech:
        rsi = tech.get("rsi", 50)
        trend = tech.get("trend", "")
        if side == "CALL" and trend == "BULL" and rsi < 70: s += 20
        elif side == "CALL" and trend == "BULL" and rsi >= 70: s += 12
        elif side == "PUT" and trend == "BEAR" and rsi > 30: s += 20
        elif side == "PUT" and trend == "BEAR" and rsi <= 30: s += 12
        elif side == "CALL" and trend == "BEAR": s += 5
        elif side == "PUT" and trend == "BULL": s += 5
    if oi < 10: s -= 15
    if vol < 5: s -= 10
    if otm_pct > info.get("max_otm", 20): s -= 25
    return max(0, min(100, s))


def calc_position(premium, budget=PLAY_BUDGET):
    cost_per = premium * 100
    if cost_per <= 0:
        return None
    contracts = int(budget / cost_per)
    if contracts < 1:
        contracts = 1
    total = round(contracts * cost_per, 2)
    if contracts >= 20:
        basis_qty = max(1, int(contracts * 0.30))
        t2 = int(contracts * 0.25)
        t3 = int(contracts * 0.25)
        moon = contracts - basis_qty - t2 - t3
        ladder = f"{basis_qty}x@2x(free$) | {t2}x@4x | {t3}x@7x | {moon}x@15x+"
    elif contracts >= 10:
        basis_qty = max(1, int(contracts * 0.35))
        t2 = int(contracts * 0.30)
        moon = contracts - basis_qty - t2
        ladder = f"{basis_qty}x@2x(free$) | {t2}x@5x | {moon}x@10x+"
    elif contracts >= 4:
        basis_qty = max(1, int(contracts * 0.50))
        moon = contracts - basis_qty
        ladder = f"{basis_qty}x@2x(free$) | {moon}x@5x+"
    else:
        ladder = f"{contracts}x — sell half@2x, rest ride"
    return {"qty": contracts, "cost": total, "ladder": ladder, "per_contract": cost_per}


def init_paper_db():
    conn = sqlite3.connect(PAPER_DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS paper_trades (
        id INTEGER PRIMARY KEY, ticker TEXT, side TEXT, strike REAL,
        expiry TEXT, entry_premium REAL, entry_date TEXT, entry_qty INTEGER,
        current_premium REAL, last_updated TEXT, exit_premium REAL,
        exit_date TEXT, status TEXT DEFAULT 'OPEN', pnl_pct REAL)""")
    conn.commit()
    return conn


def paper_enter(ticker, side, strike, expiry, premium, qty):
    conn = init_paper_db()
    existing = conn.execute(
        "SELECT id FROM paper_trades WHERE ticker=? AND strike=? AND expiry=? AND side=? AND status='OPEN'",
        (ticker, strike, expiry, side)).fetchone()
    if existing:
        conn.close()
        return
    conn.execute(
        "INSERT INTO paper_trades (ticker,side,strike,expiry,entry_premium,entry_date,entry_qty,current_premium,last_updated,status) VALUES (?,?,?,?,?,?,?,?,?,'OPEN')",
        (ticker, side, strike, expiry, premium, datetime.now().isoformat(), qty, premium, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def paper_update_prices():
    conn = init_paper_db()
    open_trades = conn.execute(
        "SELECT id,ticker,side,strike,expiry FROM paper_trades WHERE status='OPEN'").fetchall()
    for tid, ticker, side, strike, expiry in open_trades:
        try:
            t = yf.Ticker(ticker)
            chain = t.option_chain(expiry)
            opts = chain.calls if side == "CALL" else chain.puts
            match = opts[opts["strike"] == strike]
            if len(match) > 0:
                cur = match.iloc[0]["lastPrice"]
                conn.execute("UPDATE paper_trades SET current_premium=?, last_updated=? WHERE id=?",
                             (cur, datetime.now().isoformat(), tid))
        except Exception:
            pass
    for tid, ticker, side, strike, expiry in open_trades:
        try:
            exp_dt = datetime.strptime(expiry, "%Y-%m-%d")
            if datetime.now() > exp_dt:
                conn.execute(
                    "UPDATE paper_trades SET status='EXPIRED', exit_premium=0, exit_date=?, pnl_pct=? WHERE id=?",
                    (datetime.now().isoformat(), -100.0, tid))
        except Exception:
            pass
    conn.commit()
    conn.close()


def paper_summary():
    conn = init_paper_db()
    trades = conn.execute(
        "SELECT ticker,side,strike,expiry,entry_premium,entry_qty,current_premium,status,pnl_pct FROM paper_trades ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    if not trades:
        return
    msg = "<b>PAPER PORTFOLIO</b>\n"
    total_invested = 0
    total_current = 0
    for t in trades:
        ticker, side, strike, expiry, entry, qty, cur, status, pnl = t
        invested = entry * qty * 100
        current = cur * qty * 100
        total_invested += invested
        total_current += current
        pct = ((cur - entry) / entry * 100) if entry > 0 else 0
        icon = "+" if pct > 0 else ""
        s = "C" if side == "CALL" else "P"
        status_tag = "" if status == "OPEN" else f" [{status}]"
        msg += f"\n{ticker} ${strike}{s} {expiry}{status_tag}"
        msg += f"\n  Entry:${entry:.2f} Now:${cur:.2f} ({icon}{pct:.0f}%) x{qty}"
    pnl_total = total_current - total_invested
    pnl_pct = (pnl_total / total_invested * 100) if total_invested > 0 else 0
    msg += f"\n\n<b>TOTAL: ${pnl_total:+.0f} ({pnl_pct:+.1f}%)</b>"
    msg += f"\nInvested: ${total_invested:.0f} | Current: ${total_current:.0f}"
    send_tg(msg)


def scan_options():
    results = []
    for ticker, info in THESIS_MAP.items():
        tech = get_technicals(ticker)
        try:
            t = yf.Ticker(ticker)
            price = t.info.get("regularMarketPrice", 0)
            if price == 0:
                continue
            mx = info.get("max_otm", 15)
            for exp in t.options:
                exp_dt = datetime.strptime(exp, "%Y-%m-%d")
                days = (exp_dt - datetime.now()).days
                if not (25 <= days <= 120):
                    continue
                chain = t.option_chain(exp)
                for side, opts, tkey in [("CALL", chain.calls, "call"), ("PUT", chain.puts, "put")]:
                    if side == "CALL":
                        otm = opts[(opts["strike"] > price * 1.03) & (opts["strike"] < price * (1 + mx / 100))]
                    else:
                        otm = opts[(opts["strike"] < price * 0.97) & (opts["strike"] > price * (1 - mx / 100))]
                    cheap = otm[otm["lastPrice"] <= 1.50]
                    for _, row in cheap.iterrows():
                        vol = int(row.get("volume", 0) or 0)
                        oi_v = int(row.get("openInterest", 0) or 0)
                        if vol < info.get("min_vol", 10) and oi_v < info.get("min_oi", 20):
                            continue
                        iv_v = round((row.get("impliedVolatility", 0) or 0) * 100, 1)
                        prem = row["lastPrice"]
                        if side == "CALL":
                            otm_pct = round((row["strike"] - price) / price * 100, 1)
                        else:
                            otm_pct = round((price - row["strike"]) / price * 100, 1)
                        score = composite_score(prem, vol, oi_v, days, otm_pct, iv_v, tech, info, side)
                        if score < 35:
                            continue
                        pos = calc_position(prem)
                        results.append({
                            "ticker": ticker, "side": side, "price": round(price, 2),
                            "strike": row["strike"], "expiry": exp, "days": days, "premium": prem,
                            "volume": vol, "oi": oi_v, "iv": iv_v, "otm_pct": otm_pct,
                            "score": score, "thesis": info[tkey], "catalyst": info["catalyst"],
                            "tech": tech, "pos": pos,
                        })
        except Exception as e:
            print(f"Scan error {ticker}: {e}")
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def scan_trump_fresh():
    seen = get_seen()
    signals = []
    trade_map = {
        "ceasefire": ("JETS calls / XLE puts", "Peace = oil down airlines up"),
        "peace talk": ("JETS calls / XLE puts", "De-escalation"),
        "peace deal": ("JETS calls / TLT calls", "Major de-escalation"),
        "hormuz": ("XLE calls / XOP calls", "Supply choke"),
        "tariff": ("SMH puts / SPY puts", "Trade war risk off"),
        "sanctions": ("XLE calls", "Supply squeeze"),
        "rate cut": ("TLT calls / KRE calls", "Dovish Fed"),
        "military": ("ITA calls / XLE calls", "Escalation"),
        "destroy": ("XLE calls / ITA calls", "Extreme escalation"),
        "kharg": ("XLE calls", "Oil supply threat"),
        "ground offensive": ("XLE calls / ITA calls", "Major escalation"),
        "nuclear": ("GDX calls / TLT calls", "Safety flight"),
    }
    try:
        import finnhub
        client = finnhub.Client(api_key=FINNHUB_KEY)
        news = client.general_news("general", min_id=0)
        for n in news[:50]:
            headline = n.get("headline", "")
            h_hash = hashlib.md5(headline.encode()).hexdigest()[:12]
            if h_hash in seen:
                continue
            hl = headline.lower()
            if not any(kw in hl for kw in ["trump", "president", "white house"]):
                continue
            for tkw, (play, logic) in trade_map.items():
                if tkw in hl:
                    signals.append({"headline": headline[:120], "play": play, "logic": logic})
                    seen[h_hash] = datetime.now().isoformat()
                    break
    except Exception as e:
        print(f"Trump scan error: {e}")
    if len(seen) > 500:
        seen = dict(sorted(seen.items(), key=lambda x: x[1], reverse=True)[:500])
    save_seen(seen)
    return signals


def fmt(r):
    s = "C" if r["side"] == "CALL" else "P"
    tech = r.get("tech", {})
    pos = r.get("pos", {})
    msg = f"<b>[{r['score']}] {r['ticker']}</b> ${r['price']} | ${r['strike']}{s}"
    msg += f"\n  Exp: {r['expiry']} ({r['days']}d) @ ${r['premium']:.2f}"
    msg += f"\n  Vol:{r['volume']} OI:{r['oi']} IV:{r['iv']}%"
    msg += f"\n  Trend:{tech.get('trend', '?')} RSI:{tech.get('rsi', '?')} | Range:${tech.get('lo20', '?')}-${tech.get('hi20', '?')}"
    if pos:
        msg += f"\n  <b>Buy {pos['qty']}x @ ${pos['per_contract']:.0f}ea = ${pos['cost']:.0f}</b>"
        msg += f"\n  <b>Ladder: {pos['ladder']}</b>"
    msg += f"\n  <i>{r['thesis']}</i>"
    msg += f"\n  Catalyst: {r['catalyst']}"
    return msg


def run_mega_scan():
    ts = datetime.now().strftime("%H:%M")
    print(f"Mega scan {ts}")
    results = scan_options()
    with open("/root/data/options_scan.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    top_calls = [r for r in results if r["side"] == "CALL"][:5]
    top_puts = [r for r in results if r["side"] == "PUT"][:5]
    new_keys = [f"{r['ticker']}_{r['strike']}_{r['side']}" for r in top_calls + top_puts]
    old_keys = []
    if os.path.exists(LAST_TOP5_FILE):
        with open(LAST_TOP5_FILE) as f:
            old_keys = json.load(f)
    changed = set(new_keys) != set(old_keys)
    with open(LAST_TOP5_FILE, "w") as f:
        json.dump(new_keys, f)
    if changed or not old_keys:
        if top_calls:
            msg = f"<b>TOP 5 CALLS {ts}</b>\n"
            for r in top_calls:
                msg += "\n" + fmt(r) + "\n"
            send_tg(msg)
        if top_puts:
            msg = f"<b>TOP 5 PUTS {ts}</b>\n"
            for r in top_puts:
                msg += "\n" + fmt(r) + "\n"
            send_tg(msg)
    else:
        print("Rankings unchanged")
    for r in results:
        if r["score"] >= 70 and r.get("pos"):
            paper_enter(r["ticker"], r["side"], r["strike"], r["expiry"], r["premium"], r["pos"]["qty"])
    paper_update_prices()
    trump = scan_trump_fresh()
    if trump:
        msg = "<b>FRESH TRUMP SIGNAL</b>\n"
        for s in trump:
            msg += f"\n<b>{s['headline']}</b>\n  Play: {s['play']} | {s['logic']}\n"
        send_tg(msg)
    c_cnt = len([r for r in results if r["side"] == "CALL"])
    p_cnt = len([r for r in results if r["side"] == "PUT"])
    print(f"Done: {c_cnt}C {p_cnt}P score>70:{len([r for r in results if r['score'] >= 70])}")


if __name__ == "__main__":
    print("Smart Options Scanner v5 started")
    init_paper_db()
    run_mega_scan()
    schedule.every(2).hours.do(run_mega_scan)

    def trump_only():
        sigs = scan_trump_fresh()
        if sigs:
            msg = "<b>FRESH TRUMP SIGNAL</b>\n"
            for s in sigs:
                msg += f"\n<b>{s['headline']}</b>\n  Play: {s['play']} | {s['logic']}\n"
            send_tg(msg)

    schedule.every(15).minutes.do(trump_only)
    schedule.every().day.at("21:00").do(paper_summary)
    schedule.every(1).hours.do(paper_update_prices)
    while True:
        schedule.run_pending()
        time.sleep(60)
