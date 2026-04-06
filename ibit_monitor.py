#!/usr/bin/env python3
import csv
import json
import os
import time
from datetime import datetime

import ccxt
import requests
import schedule
import yfinance as yf

from core.telegram import send_tg

CSV_PATH = "/root/data/ibit_tracking.csv"


def track_ibit():
    try:
        ibit = yf.Ticker("IBIT")
        btc_kr = ccxt.kraken().fetch_ticker("BTC/USDT")
        ibit_price = ibit.info.get("regularMarketPrice", 0)
        btc_price = btc_kr["last"]
        wti = yf.Ticker("CL=F").info.get("regularMarketPrice", 0)
        xle = yf.Ticker("XLE").info.get("regularMarketPrice", 0)
        jets = yf.Ticker("JETS").info.get("regularMarketPrice", 0)
        vix = yf.Ticker("^VIX").info.get("regularMarketPrice", 0)
        row = [datetime.utcnow().isoformat(), ibit_price, btc_price, wti, xle, jets, vix]
        exists = os.path.exists(CSV_PATH)
        with open(CSV_PATH, "a") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["timestamp", "ibit", "btc", "wti", "xle", "jets", "vix"])
            w.writerow(row)
        return ibit_price, btc_price, wti, xle, jets, vix
    except Exception as e:
        print(f"IBIT track error: {e}")
        return 0, 0, 0, 0, 0, 0


def daily_report():
    ibit, btc, wti, xle, jets, vix = track_ibit()
    regime = "UNKNOWN"
    rf = "/root/scripts/regime_state.json"
    if os.path.exists(rf):
        with open(rf) as f:
            regime = json.load(f).get("regime", "UNKNOWN")
    msg = f"""<b>DAILY REPORT - {datetime.utcnow().strftime("%Y-%m-%d")}</b>
<b>MARKETS:</b>
WTI: ${wti:,.2f} | XLE: ${xle:.2f} | JETS: ${jets:.2f}
VIX: {vix:.1f} | BTC: ${btc:,.0f} | IBIT: ${ibit:.2f}
<b>REGIME:</b> {regime}
<b>XLE POSITION:</b> 26x $68C 4/17"""
    send_tg(msg)


if __name__ == "__main__":
    print("IBIT monitor started")
    track_ibit()
    schedule.every(30).minutes.do(track_ibit)
    schedule.every().day.at("21:00").do(daily_report)
    while True:
        schedule.run_pending()
        time.sleep(30)
