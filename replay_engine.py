#!/usr/bin/env python3
import sqlite3, json, os, time, schedule
from datetime import datetime

from config.settings import BOTS as _BOT_CONFIGS

DB_PATH = "/root/data/trade_replay.db"
# Build (name, db_path) tuples from centralized config
BOTS = [(b["name"].lower(),
         f"/root/freqtrade-{b['container'].split('-')[-1]}/user_data/tradesv3.sqlite")
        for b in _BOT_CONFIGS]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY, bot TEXT, pair TEXT, direction TEXT,
        entry_price REAL, entry_time TEXT, exit_price REAL, exit_time TEXT,
        profit_pct REAL, regime TEXT, strategy TEXT, stake REAL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS regime_log (
        id INTEGER PRIMARY KEY, timestamp TEXT, btc_price REAL,
        sma50 REAL, volatility REAL, regime TEXT)""")
    conn.commit()
    return conn

def sync_trades():
    conn = init_db()
    regime = "UNKNOWN"
    rf = "/root/scripts/regime_state.json"
    if os.path.exists(rf):
        with open(rf) as f:
            regime = json.load(f).get("regime", "UNKNOWN")
    for bot_name, db_path in BOTS:
        if not os.path.exists(db_path):
            continue
        try:
            src = sqlite3.connect(db_path)
            trades = src.execute("SELECT pair, open_rate, open_date, close_rate, close_date, close_profit, stake_amount, strategy FROM trades WHERE close_date IS NOT NULL").fetchall()
            for t in trades:
                exists = conn.execute("SELECT 1 FROM trades WHERE bot=? AND pair=? AND entry_time=?", (bot_name, t[0], t[2])).fetchone()
                if not exists:
                    conn.execute("INSERT INTO trades (bot,pair,direction,entry_price,entry_time,exit_price,exit_time,profit_pct,regime,strategy,stake) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (bot_name, t[0], "long", t[1], t[2], t[3], t[4], t[5], regime, t[7], t[6]))
            src.close()
        except Exception as e:
            print(f"Error syncing {bot_name}: {e}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("Replay engine started")
    init_db()
    sync_trades()
    schedule.every(5).minutes.do(sync_trades)
    while True:
        schedule.run_pending()
        time.sleep(30)
