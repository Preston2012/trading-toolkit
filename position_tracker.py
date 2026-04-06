#!/usr/bin/env python3
import json
import os
import time

import requests
import schedule
import yfinance as yf

from core.telegram import send_tg

STATE_FILE = "/root/data/position_levels.json"

POSITIONS = [
    {"ticker": "XLE", "strike": 68, "side": "call", "expiry": "2026-04-17", "qty": 26,
     "levels": [64, 65, 66, 67, 68, 70]},
]


def check_levels():
    prev = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            prev = json.load(f)
    for pos in POSITIONS:
        try:
            t = yf.Ticker(pos["ticker"])
            price = t.info.get("regularMarketPrice", 0)
            if price == 0:
                continue
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
        except Exception:
            pass
    with open(STATE_FILE, "w") as f:
        json.dump(prev, f)


if __name__ == "__main__":
    print("Position tracker started")
    check_levels()
    schedule.every(5).minutes.do(check_levels)
    while True:
        schedule.run_pending()
        time.sleep(30)
