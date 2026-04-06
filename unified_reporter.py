#!/usr/bin/env python3
import json
import os
import sqlite3
import time

import requests
import schedule

from core.telegram import send_tg

BOTS = [
    ("Sniper", "NFIX7", "/root/freqtrade-sniper/user_data/tradesv3.sqlite", 8080),
    ("Hunter", "NFIX4", "/root/freqtrade-hunter/user_data/tradesv3.sqlite", 8081),
    ("Scout", "NFIX5", "/root/freqtrade-scout/user_data/tradesv3.sqlite", 8082),
]
LAST_TRADE_FILE = "/root/data/last_trade_ids.json"
FT_USER = os.environ.get("FT_USER", "")
FT_PASS = os.environ.get("FT_PASS", "")


def get_last_ids():
    if os.path.exists(LAST_TRADE_FILE):
        with open(LAST_TRADE_FILE) as f:
            return json.load(f)
    return {}


def save_last_ids(ids):
    with open(LAST_TRADE_FILE, "w") as f:
        json.dump(ids, f)


def check_new_trades():
    last_ids = get_last_ids()
    for name, strat, db_path, port in BOTS:
        if not os.path.exists(db_path):
            continue
        try:
            conn = sqlite3.connect(db_path)
            last_id = last_ids.get(name, 0)
            new_open = conn.execute(
                "SELECT id, pair, open_rate, open_date, stake_amount FROM trades WHERE id > ? AND close_date IS NULL",
                (last_id,)).fetchall()
            for t in new_open:
                send_tg(f"<b>{name} OPENED</b>\n{t[1]} @ ${t[2]:.4f}\nStake: ${t[4]:.2f}\nTime: {t[3]}")
            new_closed = conn.execute(
                "SELECT id, pair, open_rate, close_rate, close_profit, close_date FROM trades WHERE id > ? AND close_date IS NOT NULL",
                (last_id,)).fetchall()
            for t in new_closed:
                emoji = "+" if t[4] > 0 else "-"
                pct = t[4] * 100
                send_tg(f"{emoji} <b>{name} CLOSED</b>\n{t[1]}\nEntry: ${t[2]:.4f} Exit: ${t[3]:.4f}\nProfit: {pct:+.2f}%")
            max_id = conn.execute("SELECT MAX(id) FROM trades").fetchone()[0]
            if max_id:
                last_ids[name] = max_id
            conn.close()
        except Exception as e:
            print(f"Error checking {name}: {e}")
    save_last_ids(last_ids)


def hourly_summary():
    lines = ["<b>HOURLY BOT SUMMARY</b>"]
    for name, strat, db_path, port in BOTS:
        try:
            r = requests.get(f"http://localhost:{port}/api/v1/profit",
                             auth=(FT_USER, FT_PASS), timeout=5)
            d = r.json()
            profit = d.get("profit_all_coin", 0)
            trades = d.get("trade_count", 0)
            lines.append(f"{name} ({strat}): {trades} trades, {profit:.2f} USDT")
        except Exception:
            lines.append(f"{name}: offline or no data")
    send_tg("\n".join(lines))


if __name__ == "__main__":
    print("Unified bot reporter started")
    schedule.every(2).minutes.do(check_new_trades)
    schedule.every(1).hours.do(hourly_summary)
    check_new_trades()
    while True:
        schedule.run_pending()
        time.sleep(30)
