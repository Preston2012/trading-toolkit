#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime

import requests
import schedule

from core.telegram import send_tg

TG_CRITICAL = os.environ.get("TG_CRITICAL", "")
TG_DAILY = os.environ.get("TG_DAILY", "")
FINNHUB_KEY = os.environ.get("FINNHUB_KEY", "")


def alert(chat_id, msg):
    """Send to a specific channel."""
    send_tg(msg, chat_id=chat_id)


def check_oil_prices():
    try:
        import yfinance as yf
        wti = yf.Ticker("CL=F").info.get("regularMarketPrice", 0)
        brent = yf.Ticker("BZ=F").info.get("regularMarketPrice", 0)
        xle = yf.Ticker("XLE").info.get("regularMarketPrice", 0)
        jets = yf.Ticker("JETS").info.get("regularMarketPrice", 0)
        vix = yf.Ticker("^VIX").info.get("regularMarketPrice", 0)
        levels = {
            "WTI": [(105, "$105"), (110, "$110"), (115, "$115"), (120, "$120")],
            "XLE": [(65, "$65"), (68, "$68"), (70, "$70"), (73, "$73"), (75, "$75")],
        }
        state_file = "/root/scripts/alert_state.json"
        prev = {}
        if os.path.exists(state_file):
            with open(state_file) as f:
                prev = json.load(f)
        alerts = []
        if wti > 0:
            for lvl, name in levels.get("WTI", []):
                key = f"WTI_{lvl}"
                if wti >= lvl and not prev.get(key):
                    alerts.append(f"WTI crossed {name}! Now ${wti:.2f}")
                    prev[key] = True
        if xle > 0:
            for lvl, name in levels.get("XLE", []):
                key = f"XLE_{lvl}"
                if xle >= lvl and not prev.get(key):
                    alerts.append(f"XLE crossed {name}! Now ${xle:.2f}")
                    prev[key] = True
        if jets > 0 and jets < 20 and not prev.get("JETS_below_20"):
            alerts.append(f"JETS below $20! Now ${jets:.2f} - ENTRY ZONE")
            prev["JETS_below_20"] = True
        if vix > 35 and not prev.get("VIX_35"):
            alerts.append(f"VIX above 35! Now {vix:.1f}")
            prev["VIX_35"] = True
        with open(state_file, "w") as f:
            json.dump(prev, f)
        for a in alerts:
            alert(TG_CRITICAL, f"🔴 {a}")
        return wti, brent, xle, jets, vix
    except Exception as e:
        print(f"Price check error: {e}")
        return 0, 0, 0, 0, 0


def check_polymarket():
    try:
        url = "https://gamma-api.polymarket.com/events?closed=false&tag=iran&limit=10"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            events = r.json()
            for ev in events:
                title = ev.get("title", "")
                if "ceasefire" in title.lower() or "oil" in title.lower():
                    print(f"  Polymarket: {title}")
    except Exception as e:
        print(f"Polymarket error: {e}")


def check_news():
    try:
        import finnhub
        client = finnhub.Client(api_key=FINNHUB_KEY)
        news = client.general_news("general", min_id=0)
        keywords = ["ceasefire", "hormuz", "houthi", "kharg", "iran deal", "iran war"]
        for n in news[:20]:
            headline = n.get("headline", "").lower()
            for kw in keywords:
                if kw in headline:
                    alert(TG_CRITICAL, f"📰 {n.get('headline', '')}\n{n.get('url', '')}")
                    break
    except Exception as e:
        print(f"News error: {e}")


def daily_report():
    wti, brent, xle, jets, vix = check_oil_prices()
    import yfinance as yf
    btc = yf.Ticker("BTC-USD").info.get("regularMarketPrice", 0)
    regime = "UNKNOWN"
    if os.path.exists("/root/scripts/regime_state.json"):
        with open("/root/scripts/regime_state.json") as f:
            regime = json.load(f).get("regime", "UNKNOWN")
    report = f"""<b>DAILY REPORT - {datetime.utcnow().strftime('%Y-%m-%d')}</b>

<b>MARKETS:</b>
WTI: ${wti:,.2f} | Brent: ${brent:,.2f}
XLE: ${xle:.2f} | JETS: ${jets:.2f}
VIX: {vix:.1f} | BTC: ${btc:,.0f}

<b>REGIME:</b> {regime}

<b>XLE POSITION:</b>
26x $68C 4/17 | House money"""
    alert(TG_DAILY, report)
    print("Daily report sent!")


def run_alerts():
    print(f"Alert system started at {datetime.utcnow()}")
    schedule.every(30).minutes.do(check_oil_prices)
    schedule.every(5).minutes.do(check_polymarket)
    schedule.every(15).minutes.do(check_news)
    schedule.every().day.at("21:00").do(daily_report)
    check_oil_prices()
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    run_alerts()
