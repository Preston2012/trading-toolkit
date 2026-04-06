#!/usr/bin/env python3
import yfinance as yf
import requests, json, time, schedule, os
from datetime import datetime

TG_TOKEN = "REDACTED_TG_TOKEN"
TG_CHAT = "REDACTED_TG_CHAT"
STATE_FILE = "/root/data/position_levels.json"

POSITIONS = [
    {"ticker":"XLE","strike":68,"side":"call","expiry":"2026-04-17","qty":26,
     "levels":[64,65,66,67,68,70]},
]

def send_tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id":TG_CHAT,"text":msg[:4000],"parse_mode":"HTML"},timeout=10)
    except: pass

def check_levels():
    prev = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f: prev = json.load(f)
    for pos in POSITIONS:
        try:
            t = yf.Ticker(pos["ticker"])
            price = t.info.get("regularMarketPrice",0)
            if price == 0: continue
            to_strike = pos["strike"] - price
            key = pos["ticker"] + str(pos["strike"])
            pp = prev.get(key, 0)
            for lvl in pos["levels"]:
                if pp < lvl <= price:
                    send_tg(f"<b>LEVEL BREAK: {pos['ticker']} crossed ${lvl}!</b>\n"
                        f"Price: ${price:.2f} | Strike: ${pos['strike']}\n"
                        f"Distance: ${to_strike:.2f} ({to_strike/price*100:.1f}%)")
                elif pp > lvl >= price:
                    send_tg(f"<b>LEVEL LOST: {pos['ticker']} below ${lvl}</b>\n"
                        f"Price: ${price:.2f} | Distance: ${to_strike:.2f}")
            prev[key] = price
        except: pass
    with open(STATE_FILE,"w") as f: json.dump(prev,f)

if __name__ == "__main__":
    print("Position tracker started")
    check_levels()
    schedule.every(5).minutes.do(check_levels)
    while True:
        schedule.run_pending()
        time.sleep(30)
