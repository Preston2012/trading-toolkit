#!/usr/bin/env python3
import os
import sqlite3
import time

import requests
import schedule

from core.telegram import send_tg

PAPER_DB = "/root/data/paper_trades.db"


def weekly_report():
    if not os.path.exists(PAPER_DB):
        return
    conn = sqlite3.connect(PAPER_DB)
    try:
        total = conn.execute("SELECT COUNT(*) FROM paper_trades").fetchone()[0]
    except Exception:
        conn.close()
        return
    if total == 0:
        conn.close()
        return
    open_t = conn.execute(
        "SELECT ticker,side,strike,expiry,entry_premium,current_premium,entry_qty FROM paper_trades WHERE status='OPEN'").fetchall()
    closed_t = conn.execute(
        "SELECT ticker,side,strike,expiry,entry_premium,exit_premium,pnl_pct FROM paper_trades WHERE status!='OPEN'").fetchall()
    winners = [t for t in open_t if t[5] > t[4]]
    losers = [t for t in open_t if t[5] <= t[4]]
    msg = "<b>WEEKLY REPORT CARD</b>\n"
    msg += f"Open: {len(open_t)} | Closed: {len(closed_t)}\n"
    msg += f"Winning: {len(winners)} | Losing: {len(losers)}\n"
    if open_t:
        total_inv = sum(t[4] * t[6] * 100 for t in open_t)
        total_cur = sum(t[5] * t[6] * 100 for t in open_t)
        pnl = total_cur - total_inv
        pct = pnl / total_inv * 100 if total_inv > 0 else 0
        msg += f"\n<b>P&L: ${pnl:+,.0f} ({pct:+.1f}%)</b>\n"
    if open_t:
        best = max(open_t, key=lambda t: (t[5] - t[4]) / t[4] if t[4] > 0 else 0)
        worst = min(open_t, key=lambda t: (t[5] - t[4]) / t[4] if t[4] > 0 else 0)
        s1 = "C" if best[1] == "CALL" else "P"
        s2 = "C" if worst[1] == "CALL" else "P"
        b_pct = (best[5] - best[4]) / best[4] * 100 if best[4] > 0 else 0
        w_pct = (worst[5] - worst[4]) / worst[4] * 100 if worst[4] > 0 else 0
        msg += f"\nBest: {best[0]} ${best[2]}{s1} ({b_pct:+.0f}%)"
        msg += f"\nWorst: {worst[0]} ${worst[2]}{s2} ({w_pct:+.0f}%)"
    conn.close()
    send_tg(msg)


if __name__ == "__main__":
    print("Weekly report started")
    schedule.every().sunday.at("18:00").do(weekly_report)
    weekly_report()
    while True:
        schedule.run_pending()
        time.sleep(60)
