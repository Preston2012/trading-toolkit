#!/usr/bin/env python3
import hashlib
import json
import os
import time
from datetime import datetime

import requests
import schedule

from core.telegram import send_tg

try:
    import xml.etree.ElementTree as ET
except Exception:
    pass

SEEN_NEWS = "/root/data/seen_news.json"

FEEDS = [
    "https://news.google.com/rss/search?q=trump+iran+oil&hl=en-US",
    "https://news.google.com/rss/search?q=hormuz+strait&hl=en-US",
    "https://news.google.com/rss/search?q=ceasefire+iran&hl=en-US",
    "https://news.google.com/rss/search?q=federal+reserve+rate&hl=en-US",
]

TRIGGERS = {
    "ceasefire": ("JETS calls / XLE puts", "Peace trade"),
    "peace deal": ("JETS calls / TLT calls", "De-escalation"),
    "hormuz": ("XLE calls / XOP calls", "Supply choke"),
    "tariff": ("SMH puts / SPY puts", "Trade war"),
    "rate cut": ("TLT calls / KRE calls", "Dovish Fed"),
    "kharg": ("XLE calls", "Oil supply threat"),
    "houthi": ("XLE calls", "Shipping disruption"),
    "missile": ("XLE calls / ITA calls", "Active combat"),
    "ground offensive": ("XLE calls / ITA calls", "Escalation"),
    "nuclear": ("GDX calls / TLT calls", "Safety flight"),
}


def scan_rss():
    seen = {}
    if os.path.exists(SEEN_NEWS):
        with open(SEEN_NEWS) as f:
            seen = json.load(f)
    signals = []
    for url in FEEDS:
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
            for item in root.findall(".//item")[:10]:
                title = item.find("title")
                if title is None:
                    continue
                headline = title.text or ""
                h_hash = hashlib.md5(headline.encode()).hexdigest()[:12]
                if h_hash in seen:
                    continue
                hl = headline.lower()
                for trigger, (play, logic) in TRIGGERS.items():
                    if trigger in hl:
                        signals.append({"headline": headline[:120], "play": play, "logic": logic})
                        break
                seen[h_hash] = datetime.now().isoformat()
        except Exception:
            pass
    if len(seen) > 1000:
        seen = dict(sorted(seen.items(), key=lambda x: x[1], reverse=True)[:1000])
    with open(SEEN_NEWS, "w") as f:
        json.dump(seen, f)
    if signals:
        msg = "<b>BREAKING NEWS</b>\n"
        for s in signals[:3]:
            msg += f"\n<b>{s['headline']}</b>"
            msg += f"\n  Play: {s['play']} | {s['logic']}\n"
        send_tg(msg)
    return signals


if __name__ == "__main__":
    print("RSS scraper started")
    scan_rss()
    schedule.every(5).minutes.do(scan_rss)
    while True:
        schedule.run_pending()
        time.sleep(30)
