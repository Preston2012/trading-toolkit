#!/usr/bin/env python3
import requests, json, os, time
from datetime import datetime, timedelta

DATA_DIR = "/root/freqtrade-sniper/user_data/data/kraken"
os.makedirs(DATA_DIR, exist_ok=True)

PAIRS = [("BTC","USDT"),("ETH","USDT"),("SOL","USDT"),("XRP","USDT"),
         ("DOGE","USDT"),("LTC","USDT"),("LINK","USDT"),("ADA","USDT"),
         ("AVAX","USDT"),("BNB","USDT"),("DOT","USDT"),("ATOM","USDT")]
TFS = {"5m":300000,"15m":900000,"1h":3600000,"1d":86400000}

def dl_candles(symbol, tf_str, tf_ms, days=180):
    end = int(time.time()*1000)
    start = end - (days*86400000)
    all_candles = []
    cur = start
    while cur < end:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={tf_str}&startTime={cur}&limit=1000"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                print(f"  Error {r.status_code} for {symbol} {tf_str}")
                break
            data = r.json()
            if not data:
                break
            all_candles.extend(data)
            cur = data[-1][0] + tf_ms
            time.sleep(0.2)
        except Exception as e:
            print(f"  Exception: {e}")
            time.sleep(1)
            continue
    return all_candles

def to_freqtrade_json(candles):
    result = []
    for c in candles:
        result.append([c[0]/1000, float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])])
    return result

for base, quote in PAIRS:
    symbol = f"{base}{quote}"
    pair_name = f"{base}_{quote}"
    for tf_str, tf_ms in TFS.items():
        fname = f"{pair_name}-{tf_str}.json"
        fpath = os.path.join(DATA_DIR, fname)
        if os.path.exists(fpath):
            print(f"  Skip {fname} (exists)")
            continue
        print(f"  Downloading {symbol} {tf_str}...")
        candles = dl_candles(symbol, tf_str, tf_ms)
        if candles:
            data = to_freqtrade_json(candles)
            with open(fpath, "w") as f:
                json.dump(data, f)
            print(f"  Saved {fname}: {len(data)} candles")
        else:
            print(f"  No data for {fname}")

print("Backfill complete!")
