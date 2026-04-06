#!/usr/bin/env python3
import yfinance as yf
import requests, json, os, time, schedule
from datetime import datetime

TG_TOKEN = "REDACTED_TG_TOKEN"
TG_CHAT = "REDACTED_TG_CHAT"

def send_tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id":TG_CHAT,"text":msg[:4000],"parse_mode":"HTML"},timeout=10)
    except: pass

def implied_move(ticker):
    try:
        t = yf.Ticker(ticker)
        price = t.info.get("regularMarketPrice",0)
        if price == 0: return 0
        for exp in t.options:
            d = (datetime.strptime(exp,"%Y-%m-%d")-datetime.now()).days
            if 20 <= d <= 45:
                chain = t.option_chain(exp)
                atm = min(chain.calls["strike"], key=lambda x: abs(x-price))
                cp = chain.calls[chain.calls["strike"]==atm]["lastPrice"].iloc[0]
                pp = chain.puts[chain.puts["strike"]==atm]["lastPrice"].iloc[0]
                return round((cp+pp)/price*100, 1)
    except: pass
    return 0

EVENT_MAP = {
    "ceasefire":[{"ticker":"JETS","dir":"call","why":"Peace = airlines surge"},
                 {"ticker":"XLE","dir":"put","why":"Peace = oil crash"}],
    "oil":[{"ticker":"XLE","dir":"call","why":"Oil up = energy up"}],
    "iran":[{"ticker":"XLE","dir":"call","why":"Escalation = oil up"},
            {"ticker":"ITA","dir":"call","why":"Military = defense up"}],
}

def scan_arb():
    alerts = []
    try:
        pm = requests.get("https://gamma-api.polymarket.com/events?closed=false&limit=50",timeout=10).json()
        for ev in pm:
            title = ev.get("title","").lower()
            for kw, trades in EVENT_MAP.items():
                if kw not in title: continue
                for m in ev.get("markets",[]):
                    prob = float(m.get("outcomePrices","[0.5]").strip("[]").split(",")[0])
                    q = m.get("question","")
                    for trade in trades:
                        imp = implied_move(trade["ticker"])
                        if imp > 0 and abs(prob*100 - imp) > 15:
                            alerts.append({"event":q[:80],"prob":prob,
                                "ticker":trade["ticker"],"dir":trade["dir"],
                                "imp":imp,"gap":abs(prob*100-imp),"why":trade["why"]})
    except Exception as e:
        print(f"Arb error: {e}")
    if alerts:
        msg = "<b>POLYMARKET vs OPTIONS GAP</b>\n"
        for a in alerts[:5]:
            msg += f"\n<b>{a['event']}</b>"
            msg += f"\n  PM: {a['prob']:.0%} | Implied: {a['imp']}% | GAP: {a['gap']:.0f}%"
            msg += f"\n  Play: {a['ticker']} {a['dir']}s | {a['why']}\n"
        send_tg(msg)
    print(f"Arb: {len(alerts)} gaps")

if __name__ == "__main__":
    print("Arb bridge started")
    scan_arb()
    schedule.every(2).hours.do(scan_arb)
    while True:
        schedule.run_pending()
        time.sleep(60)
