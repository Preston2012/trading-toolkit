#!/usr/bin/env python3
import json
import os
from datetime import datetime

import ccxt
import requests

from core.telegram import send_tg

STATE_FILE = "/root/scripts/regime_state.json"


def get_btc_data():
    kraken = ccxt.kraken()
    ohlcv = kraken.fetch_ohlcv("BTC/USDT", "1d", limit=60)
    closes = [c[4] for c in ohlcv]
    current = closes[-1]
    sma50 = sum(closes[-50:]) / min(len(closes), 50)
    returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
    vol20 = (sum(r ** 2 for r in returns[-20:]) / 20) ** 0.5 * (365 ** 0.5)
    return current, sma50, vol20


def get_regime():
    try:
        price, sma50, vol = get_btc_data()
        above_sma = price > sma50
        high_vol = vol > 0.80
        if above_sma and not high_vol:
            regime = "RISK_ON"
        elif not above_sma or high_vol:
            regime = "RISK_OFF"
        else:
            regime = "NEUTRAL"
        return regime, price, sma50, vol
    except Exception:
        return "NEUTRAL", 0, 0, 0


def main():
    regime, price, sma50, vol = get_regime()
    prev_regime = None
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            prev = json.load(f)
            prev_regime = prev.get("regime")
    state = {"regime": regime, "price": price, "sma50": sma50, "vol": vol,
             "updated": datetime.utcnow().isoformat()}
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)
    if regime != prev_regime:
        msg = f"<b>REGIME CHANGE: {regime}</b>\nBTC: ${price:,.0f}\n50-SMA: ${sma50:,.0f}\nVol: {vol:.0%}"
        send_tg(msg)
        print(f"REGIME CHANGE: {regime}")
    else:
        print(f"Regime: {regime} (no change)")


if __name__ == "__main__":
    main()
