#!/usr/bin/env python3
import ccxt, json, time, os, schedule, requests
from collections import defaultdict

TG_TOKEN = "REDACTED_TG_TOKEN"
TG_CHAT = "REDACTED_TG_CHAT"
SPREAD_FILE = "/root/data/spread_history.json"
BLACKLIST_FILE = "/root/scripts/temp_blacklist.json"

def send_tg(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"})

def check_spreads():
    try:
        kraken = ccxt.kraken()
        pairs = ["BTC/USDT","ETH/USDT","SOL/USDT","XRP/USDT","DOGE/USDT","LTC/USDT","LINK/USDT","ADA/USDT","AVAX/USDT","BNB/USDT"]
        history = {}
        if os.path.exists(SPREAD_FILE):
            with open(SPREAD_FILE) as f:
                history = json.load(f)
        blacklist = []
        for pair in pairs:
            try:
                ob = kraken.fetch_order_book(pair, limit=5)
                if ob["bids"] and ob["asks"]:
                    spread = (ob["asks"][0][0] - ob["bids"][0][0]) / ob["bids"][0][0]
                    h = history.get(pair, [])
                    h.append(spread)
                    h = h[-20:]
                    history[pair] = h
                    if len(h) >= 5:
                        avg = sum(h) / len(h)
                        if spread > avg * 2:
                            blacklist.append(pair)
                            # send_tg(f"<b>SPREAD ALERT</b>\n{pair} spread {spread:.4%} > 2x avg {avg:.4%}\nTemporarily blacklisted")
            except:
                pass
        with open(SPREAD_FILE, "w") as f:
            json.dump(history, f)
        with open(BLACKLIST_FILE, "w") as f:
            json.dump(blacklist, f)
    except Exception as e:
        print(f"Spread check error: {e}")

if __name__ == "__main__":
    print("Execution monitor started")
    check_spreads()
    schedule.every(60).seconds.do(check_spreads)
    while True:
        schedule.run_pending()
        time.sleep(10)
