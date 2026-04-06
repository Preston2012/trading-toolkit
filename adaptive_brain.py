#!/usr/bin/env python3
"""Adaptive trading brain — cron-driven performance optimizer for Freqtrade bots.

Analyzes recent trade history, identifies underperforming pairs, adjusts
bot configuration (blacklist/whitelist), and logs all decisions to SQLite.

Usage:
    python adaptive_brain.py                # Run for all bots (dry-run by default)
    python adaptive_brain.py --no-dry-run   # Apply changes for real
    python adaptive_brain.py --bot Sniper   # Target a specific bot

Cron example (every 6 hours):
    0 */6 * * * cd /root/scripts && python adaptive_brain.py >> /root/logs/brain.log 2>&1
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
from datetime import datetime, timezone

from config.settings import (
    BOTS,
    BRAIN_DB_PATH,
    BRAIN_DRY_RUN,
    BRAIN_LOOKBACK_DAYS,
    BRAIN_MAX_CONSEC_LOSSES,
    BRAIN_MIN_PROFIT_FACTOR,
    BRAIN_MIN_WIN_RATE,
    FT_PASS,
    FT_USER,
)
from core.brain_analyzer import (
    analyze_pair_performance,
    analyze_timeframe_performance,
    filter_trades_by_lookback,
    recommend_adjustments,
)
from core.brain_config import apply_adjustments, ft_auth, get_trades
from core.telegram import send_tg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("adaptive_brain")

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS brain_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    bot_name TEXT NOT NULL,
    trades_analyzed INTEGER,
    adjustments_made TEXT,
    dry_run BOOLEAN
);
CREATE TABLE IF NOT EXISTS pair_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES brain_runs(id),
    pair TEXT NOT NULL,
    win_rate REAL,
    profit_factor REAL,
    total_trades INTEGER,
    avg_duration_min REAL,
    action TEXT
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    """Create DB and tables if they don't exist."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    return conn


def log_run(conn: sqlite3.Connection, bot_name: str, trades_analyzed: int,
            actions: list[str], dry_run: bool) -> int:
    """Insert a brain_runs row and return the run_id."""
    cur = conn.execute(
        "INSERT INTO brain_runs (timestamp, bot_name, trades_analyzed, adjustments_made, dry_run) "
        "VALUES (?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), bot_name, trades_analyzed,
         json.dumps(actions), dry_run),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def log_pair_stats(conn: sqlite3.Connection, run_id: int,
                   pair_stats: dict[str, dict], pair_actions: dict[str, str]) -> None:
    """Insert per-pair stats for a run."""
    rows = []
    for pair, s in pair_stats.items():
        rows.append((
            run_id, pair, s["win_rate"], s["profit_factor"],
            s["total_trades"], s["avg_duration_min"],
            pair_actions.get(pair, "keep"),
        ))
    conn.executemany(
        "INSERT INTO pair_stats (run_id, pair, win_rate, profit_factor, "
        "total_trades, avg_duration_min, action) VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def run_brain(bot_filter: str | None = None, dry_run: bool = BRAIN_DRY_RUN) -> None:
    """Main brain loop — iterate bots, analyze, adjust, log."""
    thresholds = {
        "min_win_rate": BRAIN_MIN_WIN_RATE,
        "min_profit_factor": BRAIN_MIN_PROFIT_FACTOR,
        "max_consec_losses": BRAIN_MAX_CONSEC_LOSSES,
        "min_trades": 5,
    }

    conn = init_db(BRAIN_DB_PATH)
    bots = BOTS
    if bot_filter:
        bots = [b for b in BOTS if b["name"].lower() == bot_filter.lower()]
        if not bots:
            logger.error("Bot '%s' not found in config. Available: %s",
                         bot_filter, [b["name"] for b in BOTS])
            return

    for bot in bots:
        bot_name = bot["name"]
        base_url = f"http://localhost:{bot['port']}"
        logger.info("=== Processing %s (%s) ===", bot_name, base_url)

        try:
            token = ft_auth(base_url, FT_USER, FT_PASS)
        except Exception:
            logger.exception("Failed to authenticate with %s", bot_name)
            continue

        try:
            all_trades = get_trades(base_url, token, limit=500)
        except Exception:
            logger.exception("Failed to fetch trades from %s", bot_name)
            continue

        trades = filter_trades_by_lookback(all_trades, BRAIN_LOOKBACK_DAYS)
        logger.info("Analyzing %d trades (last %d days) for %s",
                     len(trades), BRAIN_LOOKBACK_DAYS, bot_name)

        if not trades:
            logger.info("No trades in lookback window for %s, skipping", bot_name)
            run_id = log_run(conn, bot_name, 0, ["No trades in window"], dry_run)
            continue

        pair_stats = analyze_pair_performance(trades)
        tf_stats = analyze_timeframe_performance(trades)
        recommendations = recommend_adjustments(pair_stats, tf_stats, thresholds, trades)

        try:
            actions = apply_adjustments(base_url, token, recommendations, dry_run=dry_run)
        except Exception:
            logger.exception("Failed to apply adjustments to %s", bot_name)
            actions = ["ERROR: failed to apply adjustments"]

        run_id = log_run(conn, bot_name, len(trades), actions, dry_run)
        log_pair_stats(conn, run_id, pair_stats, recommendations.get("pair_actions", {}))

        # Telegram summary
        mode = "DRY RUN" if dry_run else "LIVE"
        bl_count = len(recommendations.get("blacklist_add", []))
        summary = (
            f"<b>BRAIN [{mode}] — {bot_name}</b>\n"
            f"Trades analyzed: {len(trades)}\n"
            f"Pairs flagged: {bl_count}\n"
        )
        if actions:
            summary += "Actions:\n" + "\n".join(f"  • {a}" for a in actions)
        send_tg(summary)
        logger.info("Run complete for %s: %d actions", bot_name, len(actions))

    conn.close()
    logger.info("Brain run complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive trading brain")
    parser.add_argument("--bot", help="Target a specific bot by name")
    parser.add_argument("--dry-run", action="store_true", default=None,
                        help="Log actions without applying (default from env)")
    parser.add_argument("--no-dry-run", action="store_true",
                        help="Apply changes for real")
    args = parser.parse_args()

    if args.no_dry_run:
        dry_run = False
    elif args.dry_run:
        dry_run = True
    else:
        dry_run = BRAIN_DRY_RUN

    run_brain(bot_filter=args.bot, dry_run=dry_run)


if __name__ == "__main__":
    main()
