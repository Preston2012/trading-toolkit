# Thesis-Based Options Scanner v5
# Scans 12 ETFs for cheap OTM options matching macro thesis
# Technical analysis, position sizing, exit ladders, Telegram alerts
# github.com/Preston2012/trading-toolkit

import os
import paramiko, time, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(os.environ["VPS_HOST"], username=os.environ.get("VPS_USER", "root"), password=os.environ["VPS_PASSWORD"])

def run(cmd, t=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=t)
    o = stdout.read().decode("utf-8", errors="replace").strip()
    e = stderr.read().decode("utf-8", errors="replace").strip()
    if o: print(o[-500:].encode("ascii","replace").decode())
    if e and "WARNING" not in e and "Future" not in e and "Deprecat" not in e:
        print("E:", e[-200:].encode("ascii","replace").decode())
    return o

sftp = ssh.open_sftp()
print("=== SCANNER v5: Position Sizing + Fresh Trump + Technical Analysis ===")

scanner_v5 = r'''#!/usr/bin/env python3
import yfinance as yf
import requests, json, time, schedule, os, hashlib
from datetime import datetime, timedelta

TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"]
FINNHUB_KEY = os.environ["FINNHUB_KEY"]
SEEN_FILE = "/root/data/seen_headlines.json"
TRADE_FUND = 3000  # Starting trade fund estimate

THESIS_MAP = {
    "XLE": {"call": "Oil war escalation. Hormuz closed, Houthis active. $110 WTI = XLE $70+",
            "put": "Ceasefire/peace = oil crashes 20% = XLE drops to $52-55",
            "catalyst": "Apr 6 Trump deadline, Kharg Island, ceasefire talks",
            "max_otm": 15, "min_vol": 20, "min_oi": 50, "beta": 1.2},
    "JETS": {"call": "Peace hedge. Ceasefire = oil crashes = airlines surge 20-30%",
            "put": "War extends = jet fuel $7+ = airlines bleed another 15%",
            "catalyst": "Iran deal/ceasefire, jet fuel prices, airline guidance",
            "max_otm": 25, "min_vol": 15, "min_oi": 30, "beta": 1.5},
    "TLT": {"call": "Oil kills economy -> recession -> Fed cuts -> bonds rip 8-12%",
            "put": "Inflation stays hot from oil -> Fed holds -> bonds drop 5%",
            "catalyst": "FOMC Apr 28-29, CPI, recession signals",
            "max_otm": 10, "min_vol": 50, "min_oi": 50, "beta": 0.8},
    "XBI": {"call": "Biotech FDA binary. ONLY with known PDUFA date",
            "put": "Rate fear selloff crushes speculative biotech",
            "catalyst": "FDA PDUFA dates ONLY",
            "max_otm": 15, "min_vol": 30, "min_oi": 50, "beta": 1.4},
    "KRE": {"call": "Regional banks recover on Fed cut + oil drop",
            "put": "Oil recession = loan defaults = bank crisis 2.0",
            "catalyst": "Fed decision, oil reversal, bank earnings",
            "max_otm": 18, "min_vol": 10, "min_oi": 30, "beta": 1.3},
    "GDX": {"call": "Gold miners surge on rate cuts + dollar weakness",
            "put": "Dollar strength = gold drops = miners crushed",
            "catalyst": "Fed pivot, dollar index, gold price",
            "max_otm": 15, "min_vol": 10, "min_oi": 20, "beta": 1.5},
    "IBIT": {"call": "BTC depressed by war. Peace = risk-on = BTC $85K+",
             "put": "Crypto winter extends on macro fear",
             "catalyst": "Ceasefire, ETF flows, Fed signals",
             "max_otm": 20, "min_vol": 20, "min_oi": 30, "beta": 1.8},
    "SMH": {"call": "Semis oversold. AI capex intact. Mean reversion 15%",
            "put": "Trade war + chip bans = semis drop another 15%",
            "catalyst": "NVDA/AMD earnings, trade deals, AI capex",
            "max_otm": 12, "min_vol": 50, "min_oi": 100, "beta": 1.3},
    "XLF": {"call": "Financials pop on rate cut clarity",
            "put": "Recession = loan losses = financials dump",
            "catalyst": "FOMC, yield curve, bank earnings",
            "max_otm": 12, "min_vol": 20, "min_oi": 30, "beta": 1.1},
    "SPY": {"call": "War ends = market rips on relief rally",
            "put": "Oil recession + Fed stuck = market -10-15%",
            "catalyst": "Ceasefire, FOMC, GDP, earnings season",
            "max_otm": 8, "min_vol": 100, "min_oi": 200, "beta": 1.0},
    "XOP": {"call": "Oil E&P pure play. Higher beta than XLE",
            "put": "Peace = oil crash = XOP -25% (high beta both ways)",
            "catalyst": "Same as XLE amplified",
            "max_otm": 15, "min_vol": 20, "min_oi": 30, "beta": 1.6},
    "ITA": {"call": "Defense spending up regardless. Election cycle boost",
            "put": "Peace = defense budget cut narrative",
            "catalyst": "Defense budget, contracts, election",
            "max_otm": 12, "min_vol": 10, "min_oi": 20, "beta": 0.9},
}

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TG_CHAT, "text": msg[:4000], "parse_mode": "HTML"}, timeout=10)
    except: pass

def get_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f: return json.load(f)
    return {}

def save_seen(seen):
    with open(SEEN_FILE, "w") as f: json.dump(seen, f)

def get_technicals(ticker):
    """RSI, trend direction, support/resistance, avg volume"""
    try:
        t = yf.Ticker(ticker)
        h = t.history(period="3mo")
        if len(h) < 20: return {}
        close = h["Close"]
        price = close.iloc[-1]
        # RSI 14
        delta = close.diff()
        gain = delta.where(delta>0, 0).rolling(14).mean()
        loss = (-delta.where(delta<0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = round(rsi.iloc[-1], 1)
        # EMA 20/50 trend
        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]
        trend = "BULLISH" if ema20 > ema50 else "BEARISH"
        # Support/Resistance (recent high/low)
        hi_20 = round(close.tail(20).max(), 2)
        lo_20 = round(close.tail(20).min(), 2)
        # Avg volume
        avg_vol = int(h["Volume"].tail(20).mean())
        # Historical volatility 30d
        ret = close.pct_change().dropna()
        hv30 = round(ret.tail(30).std() * (252**0.5) * 100, 1)
        return {"rsi": rsi_val, "trend": trend, "ema20": round(ema20,2),
                "ema50": round(ema50,2), "hi20": hi_20, "lo20": lo_20,
                "avg_vol": avg_vol, "hv30": hv30, "price": round(price,2)}
    except: return {}

def calc_position(premium, price, strike, days, ticker, info, tech, side="call"):
    """Calculate suggested position size and exit ladder"""
    max_risk = TRADE_FUND * 0.03  # 3% max risk per play
    contracts = max(1, int(max_risk / (premium * 100)))
    total_cost = contracts * premium * 100
    # Target based on OTM distance and days
    if side == "call":
        otm_pct = (strike - price) / price
    else:
        otm_pct = (price - strike) / price
    # Exit ladder - scale out in 3-4 tranches
    if contracts >= 8:
        ladder = [
            (int(contracts*0.25), "2x (recover basis)"),
            (int(contracts*0.25), "3-4x (lock profit)"),
            (int(contracts*0.25), "6-8x (let run)"),
            (contracts - 3*int(contracts*0.25), "10x+ (moon bag)")
        ]
    elif contracts >= 4:
        ladder = [
            (int(contracts*0.33), "2x (recover basis)"),
            (int(contracts*0.33), "4-5x (lock profit)"),
            (contracts - 2*int(contracts*0.33), "8x+ (moon bag)")
        ]
    else:
        ladder = [
            (max(1, contracts//2), "2x (recover basis)"),
            (contracts - max(1, contracts//2), "5x+ (let ride)")
        ]
    # Kill price
    kill_pct = 50  # cut at 50% loss of premium
    kill_price = round(premium * 0.5, 2)
    return {"contracts": contracts, "total_cost": round(total_cost, 2),
            "pct_of_fund": round(total_cost/TRADE_FUND*100, 1),
            "ladder": ladder, "kill_price": kill_price}

def grade(premium, volume, oi, days, otm_pct, info):
    score = 0
    if oi > 500: score += 25
    elif oi > 100: score += 20
    elif oi > 50: score += 15
    elif oi > 20: score += 10
    if volume > 200: score += 25
    elif volume > 50: score += 20
    elif volume > 20: score += 15
    if 0.05 <= premium <= 0.50: score += 25
    elif 0.50 < premium <= 1.00: score += 20
    elif 1.00 < premium <= 1.50: score += 15
    if 30 <= days <= 60: score += 25
    elif 60 < days <= 90: score += 20
    elif 25 <= days < 30: score += 15
    if oi < 10: score -= 20
    if volume < 5: score -= 15
    if otm_pct > info.get("max_otm", 20): score -= 30
    if score >= 70: return "A"
    elif score >= 55: return "B"
    elif score >= 40: return "C"
    return "D"

def scan_options():
    results = []
    for ticker, info in THESIS_MAP.items():
        tech = get_technicals(ticker)
        try:
            t = yf.Ticker(ticker)
            price = t.info.get("regularMarketPrice", 0)
            if price == 0: continue
            exps = t.options
            now = datetime.now()
            max_otm = info.get("max_otm", 15)
            for exp in exps:
                exp_dt = datetime.strptime(exp, "%Y-%m-%d")
                days = (exp_dt - now).days
                if not (25 <= days <= 120): continue
                chain = t.option_chain(exp)
                for side, opts, thesis_key in [("CALL", chain.calls, "call"), ("PUT", chain.puts, "put")]:
                    if side == "CALL":
                        otm = opts[(opts["strike"]>price*1.03)&(opts["strike"]<price*(1+max_otm/100))]
                    else:
                        otm = opts[(opts["strike"]<price*0.97)&(opts["strike"]>price*(1-max_otm/100))]
                    cheap = otm[otm["lastPrice"]<=1.50]
                    for _, row in cheap.iterrows():
                        vol=int(row.get("volume",0) or 0)
                        oi_v=int(row.get("openInterest",0) or 0)
                        if vol < info.get("min_vol",10) and oi_v < info.get("min_oi",20): continue
                        iv_v=round((row.get("impliedVolatility",0) or 0)*100,1)
                        if side=="CALL": otm_pct=round((row["strike"]-price)/price*100,1)
                        else: otm_pct=round((price-row["strike"])/price*100,1)
                        g = grade(row["lastPrice"],vol,oi_v,days,otm_pct,info)
                        if g == "D": continue
                        pos = calc_position(row["lastPrice"],price,row["strike"],days,ticker,info,tech,side.lower())
                        results.append({"ticker":ticker,"side":side,"price":round(price,2),
                            "strike":row["strike"],"expiry":exp,"days":days,
                            "premium":row["lastPrice"],"volume":vol,"oi":oi_v,"iv":iv_v,
                            "otm_pct":otm_pct,"grade":g,"thesis":info[thesis_key],
                            "catalyst":info["catalyst"],"tech":tech,"pos":pos})
        except Exception as e:
            print(f"Scan error {ticker}: {e}")
    results.sort(key=lambda x:("A","B","C").index(x["grade"]))
    return results

def scan_trump_fresh():
    """Only show NEW Trump headlines - dedup via hash"""
    seen = get_seen()
    signals = []
    trade_map = {"ceasefire":("JETS calls / XLE puts","Peace = oil down airlines up"),
        "peace talk":("JETS calls / XLE puts","De-escalation signal"),
        "peace deal":("JETS calls / TLT calls","Major de-escalation"),
        "iran deal":("JETS calls / TLT calls","De-escalation"),
        "hormuz":("XLE calls / XOP calls","Supply choke = oil up"),
        "tariff":("SMH puts / SPY puts","Trade war = risk off"),
        "sanctions":("XLE calls","Supply squeeze"),
        "rate cut":("TLT calls / KRE calls","Dovish = bonds+banks"),
        "military":("ITA calls / XLE calls","Escalation"),
        "destroy":("XLE calls / ITA calls","Extreme escalation"),
        "kharg":("XLE calls","Direct oil supply threat"),
        "oil well":("XLE calls / XOP calls","Supply destruction"),
        "ground offensive":("XLE calls / ITA calls","Major escalation"),
        "nuclear":("GDX calls / TLT calls","Flight to safety")}
    try:
        import finnhub
        client = finnhub.Client(api_key=FINNHUB_KEY)
        news = client.general_news('general', min_id=0)
        trump_kw = ["trump","truth social","president said","white house"]
        for n in news[:50]:
            headline = n.get("headline","")
            h_hash = hashlib.md5(headline.encode()).hexdigest()[:12]
            if h_hash in seen: continue  # SKIP ALREADY SEEN
            hl = headline.lower()
            if not any(kw in hl for kw in trump_kw): continue
            for tkw, (play, logic) in trade_map.items():
                if tkw in hl:
                    signals.append({"headline":headline[:120],"play":play,
                        "logic":logic,"hash":h_hash})
                    seen[h_hash] = datetime.now().isoformat()
                    break
    except Exception as e:
        print(f"Trump scan error: {e}")
    # Clean old seen (keep last 500)
    if len(seen) > 500:
        items = sorted(seen.items(), key=lambda x:x[1], reverse=True)[:500]
        seen = dict(items)
    save_seen(seen)
    return signals

def get_technicals(ticker):
    try:
        t = yf.Ticker(ticker)
        h = t.history(period="3mo")
        if len(h) < 20: return {}
        close = h["Close"]
        price = close.iloc[-1]
        delta = close.diff()
        gain = delta.where(delta>0, 0).rolling(14).mean()
        loss = (-delta.where(delta<0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = round((100 - (100 / (1 + rs))).iloc[-1], 1)
        ema20 = round(close.ewm(span=20).mean().iloc[-1], 2)
        ema50 = round(close.ewm(span=50).mean().iloc[-1], 2)
        trend = "BULL" if ema20 > ema50 else "BEAR"
        hi20 = round(close.tail(20).max(), 2)
        lo20 = round(close.tail(20).min(), 2)
        ret = close.pct_change().dropna()
        hv30 = round(ret.tail(30).std() * (252**0.5) * 100, 1)
        return {"rsi":rsi,"trend":trend,"ema20":ema20,"ema50":ema50,"hi20":hi20,"lo20":lo20,"hv30":hv30,"price":round(price,2)}
    except: return {}

def calc_position(premium, price, strike, days, side="call"):
    fund = TRADE_FUND
    max_risk = fund * 0.03
    contracts = max(1, int(max_risk / (premium * 100)))
    total = round(contracts * premium * 100, 2)
    if side == "call":
        otm_pct = (strike - price) / price
    else:
        otm_pct = (price - strike) / price
    if contracts >= 8:
        ladder = f"{int(contracts*.25)}x@2x | {int(contracts*.25)}x@4x | {int(contracts*.25)}x@7x | {contracts-3*int(contracts*.25)}x@10x+"
    elif contracts >= 4:
        ladder = f"{int(contracts*.33)}x@2x | {int(contracts*.33)}x@5x | {contracts-2*int(contracts*.33)}x@10x+"
    else:
        ladder = f"{max(1,contracts//2)}x@2x | {contracts-max(1,contracts//2)}x@5x+"
    kill = round(premium * 0.5, 2)
    return {"qty": contracts, "cost": total, "pct": round(total/fund*100,1), "ladder": ladder, "kill": kill}

def scan_options():
    results = []
    for ticker, info in THESIS_MAP.items():
        tech = get_technicals(ticker)
        try:
            t = yf.Ticker(ticker)
            price = t.info.get("regularMarketPrice", 0)
            if price == 0: continue
            exps = t.options
            now = datetime.now()
            mx = info.get("max_otm", 15)
            for exp in exps:
                exp_dt = datetime.strptime(exp, "%Y-%m-%d")
                days = (exp_dt - now).days
                if not (25 <= days <= 120): continue
                chain = t.option_chain(exp)
                for side, opts, tkey in [("CALL",chain.calls,"call"),("PUT",chain.puts,"put")]:
                    if side=="CALL":
                        otm = opts[(opts["strike"]>price*1.03)&(opts["strike"]<price*(1+mx/100))]
                    else:
                        otm = opts[(opts["strike"]<price*0.97)&(opts["strike"]>price*(1-mx/100))]
                    cheap = otm[otm["lastPrice"]<=1.50]
                    for _, row in cheap.iterrows():
                        vol=int(row.get("volume",0) or 0)
                        oi_v=int(row.get("openInterest",0) or 0)
                        if vol<info.get("min_vol",10) and oi_v<info.get("min_oi",20): continue
                        iv_v=round((row.get("impliedVolatility",0) or 0)*100,1)
                        if side=="CALL": otm_pct=round((row["strike"]-price)/price*100,1)
                        else: otm_pct=round((price-row["strike"])/price*100,1)
                        g = grade(row["lastPrice"],vol,oi_v,days,otm_pct,info)
                        if g == "D": continue
                        pos = calc_position(row["lastPrice"],price,row["strike"],days,side.lower())
                        results.append({"ticker":ticker,"side":side,"price":round(price,2),
                            "strike":row["strike"],"expiry":exp,"days":days,
                            "premium":row["lastPrice"],"volume":vol,"oi":oi_v,"iv":iv_v,
                            "otm_pct":otm_pct,"grade":g,"thesis":info[tkey],
                            "catalyst":info["catalyst"],"tech":tech,"pos":pos})
        except Exception as e:
            print(f"Scan error {ticker}: {e}")
    results.sort(key=lambda x:("A","B","C").index(x["grade"]))
    return results

def fmt_alert(r):
    s = "C" if r["side"]=="CALL" else "P"
    tech = r.get("tech",{})
    pos = r.get("pos",{})
    trend = tech.get("trend","?")
    rsi = tech.get("rsi","?")
    hi = tech.get("hi20","?")
    lo = tech.get("lo20","?")
    msg = f"<b>[{r['grade']}] {r['ticker']}</b> ${r['price']} | ${r['strike']}{s}"
    msg += f"\n  Exp: {r['expiry']} ({r['days']}d) @ ${r['premium']:.2f}"
    msg += f"\n  OTM:{r['otm_pct']}% | Vol:{r['volume']} OI:{r['oi']} IV:{r['iv']}%"
    msg += f"\n  Trend:{trend} RSI:{rsi} | 20d Range:${lo}-${hi}"
    msg += f"\n  <b>Size:</b> {pos.get('qty',1)}x (${pos.get('cost',0)}) = {pos.get('pct',0)}% of fund"
    msg += f"\n  <b>Ladder:</b> {pos.get('ladder','')}"
    msg += f"\n  <b>Kill:</b> ${pos.get('kill',0)} (-50% of premium)"
    msg += f"\n  <i>{r['thesis']}</i>"
    msg += f"\n  Catalyst: {r['catalyst']}"
    return msg

def run_mega_scan():
    ts = datetime.now().strftime("%H:%M")
    print(f"Mega scan at {ts}")
    results = scan_options()
    with open("/root/data/options_scan.json","w") as f:
        json.dump(results, f, indent=2, default=str)
    a_calls = [r for r in results if r["grade"]=="A" and r["side"]=="CALL"]
    a_puts = [r for r in results if r["grade"]=="A" and r["side"]=="PUT"]
    b_all = [r for r in results if r["grade"]=="B"]
    if a_calls:
        msg = f"<b>TOP CALLS (Grade A) {ts}</b>\n"
        for r in a_calls[:5]:
            msg += "\n" + fmt_alert(r) + "\n"
        send_tg(msg)
    if a_puts:
        msg = f"<b>TOP PUTS (Grade A) {ts}</b>\n"
        for r in a_puts[:5]:
            msg += "\n" + fmt_alert(r) + "\n"
        send_tg(msg)
    if b_all:
        msg = f"<b>WATCHLIST (Grade B) {ts}</b>\n"
        for r in b_all[:6]:
            s = "C" if r["side"]=="CALL" else "P"
            pos = r.get("pos",{})
            msg += f"\n<b>{r['ticker']}</b> ${r['strike']}{s} {r['expiry']} ({r['days']}d) @ ${r['premium']:.2f}"
            msg += f"\n  Size:{pos.get('qty',1)}x | <i>{r['thesis'][:60]}</i>\n"
        send_tg(msg)
    # Trump - FRESH ONLY
    trump = scan_trump_fresh()
    if trump:
        msg = "<b>FRESH TRUMP SIGNAL</b>\n"
        for s in trump:
            msg += f"\n<b>{s['headline']}</b>"
            msg += f"\n  Play: {s['play']}"
            msg += f"\n  Logic: {s['logic']}\n"
        send_tg(msg)
    if not results and not trump:
        send_tg(f"<b>OPTIONS SCAN {ts}</b>\nNo quality setups this cycle.")
    c_cnt = len([r for r in results if r["side"]=="CALL"])
    p_cnt = len([r for r in results if r["side"]=="PUT"])
    print(f"Done: {c_cnt}C {p_cnt}P {len(trump)}trump")

if __name__ == "__main__":
    print("Smart Options Scanner v5 started")
    run_mega_scan()
    schedule.every(2).hours.do(run_mega_scan)
    # Trump only every 15 min - FRESH only, no repeats
    def trump_check():
        sigs = scan_trump_fresh()
        if sigs:
            msg = "<b>FRESH TRUMP SIGNAL</b>\n"
            for s in sigs:
                msg += f"\n<b>{s['headline']}</b>\n  Play: {s['play']}\n  Logic: {s['logic']}\n"
            send_tg(msg)
    schedule.every(15).minutes.do(trump_check)
    while True:
        schedule.run_pending()
        time.sleep(60)
'''

# Deploy to VPS
with sftp.file("/root/scripts/options_scanner.py", "w") as f:
    f.write(scanner_v5)
run("chmod +x /root/scripts/options_scanner.py")
# Install finnhub
run("pip3 install finnhub-python --break-system-packages --quiet 2>/dev/null", 30)
# Clear old seen headlines so we start fresh
run("rm -f /root/data/seen_headlines.json")
sftp.close()

print("Restarting scanner...")
run("systemctl restart options-scanner")
time.sleep(3)
print(f"Service: {run('systemctl is-active options-scanner')}")
print("\nWaiting 120s for first scan...")
time.sleep(120)
print("Log:")
print(run("tail -10 /root/logs/options-scanner.log 2>/dev/null"))
ssh.close()
print("\nScanner v5 DEPLOYED. Check Telegram.")
