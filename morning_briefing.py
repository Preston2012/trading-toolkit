#!/usr/bin/env python3
"""One Telegram message every morning with everything that matters."""
import json
import os
import time
from datetime import datetime

import requests
import schedule
import yfinance as yf

from core.telegram import send_tg


def morning_briefing():
    msg = "<b>MORNING BRIEFING</b>\n"
    msg += f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
    try:
        tickers = {"WTI": "CL=F", "Brent": "BZ=F", "XLE": "XLE", "JETS": "JETS", "VIX": "^VIX", "SPY": "SPY", "IBIT": "IBIT"}
        msg += "\n<b>MARKETS:</b>\n"
        for name, sym in tickers.items():
            t = yf.Ticker(sym)
            p = t.info.get("regularMarketPrice", 0)
            chg = t.info.get("regularMarketChangePercent", 0)
            sign = "+" if chg > 0 else ""
            msg += f"  {name}: ${p:,.2f} ({sign}{chg:.1f}%)\n"
    except Exception as e:
        msg += f"  Market data error: {e}\n"
    try:
        xle = yf.Ticker("XLE").info.get("regularMarketPrice", 0)
        to_strike = 68 - xle
        msg += f"\n<b>XLE POSITION:</b>\n"
        msg += f"  26x $68C Apr 17 | XLE: ${xle:.2f}\n"
        msg += f"  Distance to strike: ${to_strike:.2f} ({to_strike/xle*100:.1f}%)\n"
        if to_strike < 3:
            msg += "  STATUS: APPROACHING STRIKE\n"
        elif to_strike < 5:
            msg += "  STATUS: Getting close\n"
        else:
            msg += "  STATUS: Needs more oil upside\n"
    except Exception:
        pass
    try:
        rf = "/root/scripts/regime_state.json"
        if os.path.exists(rf):
            with open(rf) as f:
                r = json.load(f)
            msg += f"\n<b>REGIME:</b> {r.get('regime', '?')}\n"
            msg += f"  BTC: ${r.get('price', 0):,.0f} | SMA50: ${r.get('sma50', 0):,.0f}\n"
    except Exception:
        pass
    try:
        pm = requests.get("https://gamma-api.polymarket.com/events?closed=false&limit=50", timeout=10).json()
        for ev in pm:
            title = ev.get("title", "").lower()
            if any(kw in title for kw in ["iran", "ceasefire", "oil", "crude"]):
                for m in ev.get("markets", [])[:2]:
                    q = m.get("question", "")
                    prob = float(m.get("outcomePrices", "[0.5]").strip("[]").split(",")[0])
                    msg += f"\n<b>POLYMARKET:</b> {q[:60]}\n  Probability: {prob:.0%}\n"
    except Exception:
        pass
    try:
        if os.path.exists("/root/data/options_scan.json"):
            with open("/root/data/options_scan.json") as f:
                picks = json.load(f)
            if picks:
                top = picks[0]
                s = "C" if top["side"] == "CALL" else "P"
                msg += f"\n<b>TOP SCANNER PICK:</b>\n"
                msg += f"  [{top['score']}] {top['ticker']} ${top['strike']}{s} {top['expiry']}\n"
                msg += f"  @ ${top['premium']:.2f} | {top['thesis'][:60]}\n"
    except Exception:
        pass
    try:
        import sqlite3
        conn = sqlite3.connect("/root/data/paper_trades.db")
        total = conn.execute("SELECT COUNT(*) FROM paper_trades").fetchone()[0]
        winners = conn.execute("SELECT COUNT(*) FROM paper_trades WHERE current_premium > entry_premium AND status='OPEN'").fetchone()[0]
        conn.close()
        if total > 0:
            msg += f"\n<b>PAPER TRADES:</b> {total} tracked, {winners} winning\n"
    except Exception:
        pass
    msg += "\n<b>KEY DATES:</b>\n  Apr 6: Trump Iran deadline\n  Apr 17: XLE calls expiry\n  Apr 28-29: FOMC meeting"
    send_tg(msg)
    print(f"Morning briefing sent at {datetime.utcnow()}")


if __name__ == "__main__":
    print("Morning briefing service started")
    morning_briefing()
    schedule.every().day.at("12:30").do(morning_briefing)
    while True:
        schedule.run_pending()
        time.sleep(60)
