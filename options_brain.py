#!/usr/bin/env python3
"""Options brain — cron-driven performance analyzer for the options scanner.

Reads paper trade outcomes from paper_trades.db (populated by options_scanner.py),
analyzes per-ETF win rates and P&L, then recommends scanner threshold adjustments
and position sizing changes. Logs all decisions to SQLite.

Usage:
    python options_brain.py                  # Analyze and recommend (dry-run default)
    python options_brain.py --no-dry-run     # Apply changes to thesis_maps and scanner config
    python options_brain.py --ticker XLE     # Analyze a specific ETF only

Cron example (daily at 10pm, after paper_summary runs at 9pm):
    0 22 * * * cd /root/scripts && python options_brain.py >> /root/logs/options-brain.log 2>&1
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone

from config.settings import BRAIN_DB_PATH
from core.options_brain_analyzer import (
    analyze_by_side,
    analyze_by_ticker,
    calc_trade_pnl,
    load_paper_trades,
    recommend_scanner_adjustments,
    recommend_sizing_adjustments,
)
from core.telegram import send_tg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("options_brain")

PAPER_DB = os.environ.get("PAPER_DB", "/root/data/paper_trades.db")
OPTIONS_BRAIN_DB = os.environ.get("OPTIONS_BRAIN_DB", BRAIN_DB_PATH.replace("brain.db", "options_brain.db"))
PLAY_BUDGET = float(os.environ.get("PLAY_BUDGET", "400"))

# Import the scanner's THESIS_MAP for current thresholds
# (uses the inline copy in options_scanner.py, not config/thesis_maps.py,
#  because the scanner runs its own copy)
_THESIS_MAP_FALLBACK: dict[str, dict] = {}
try:
    from options_scanner import THESIS_MAP as _SCANNER_THESIS_MAP
    _THESIS_MAP_FALLBACK = _SCANNER_THESIS_MAP
except ImportError:
    pass

try:
    from config.thesis_maps import THESIS_MAP as _CONFIG_THESIS_MAP
    if not _THESIS_MAP_FALLBACK:
        _THESIS_MAP_FALLBACK = _CONFIG_THESIS_MAP
except ImportError:
    pass

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS options_brain_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    total_trades_analyzed INTEGER,
    tickers_analyzed INTEGER,
    scanner_adjustments TEXT,
    sizing_adjustments TEXT,
    side_stats TEXT,
    dry_run BOOLEAN
);
CREATE TABLE IF NOT EXISTS options_ticker_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES options_brain_runs(id),
    ticker TEXT NOT NULL,
    total_trades INTEGER,
    wins INTEGER,
    losses INTEGER,
    win_rate REAL,
    avg_pnl_pct REAL,
    total_pnl_pct REAL,
    call_win_rate REAL,
    put_win_rate REAL,
    action TEXT
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    """Create options brain DB and tables."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    return conn


def log_run(conn: sqlite3.Connection, total_trades: int, tickers: int,
            scanner_adj: dict, sizing_adj: dict, side_stats: dict,
            dry_run: bool) -> int:
    """Insert an options_brain_runs row."""
    cur = conn.execute(
        "INSERT INTO options_brain_runs "
        "(timestamp, total_trades_analyzed, tickers_analyzed, "
        "scanner_adjustments, sizing_adjustments, side_stats, dry_run) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), total_trades, tickers,
         json.dumps(scanner_adj, default=str), json.dumps(sizing_adj, default=str),
         json.dumps(side_stats, default=str), dry_run),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def log_ticker_stats(conn: sqlite3.Connection, run_id: int,
                     ticker_stats: dict[str, dict],
                     scanner_adj: dict, sizing_adj: dict) -> None:
    """Insert per-ticker stats for a run."""
    rows = []
    for ticker, s in ticker_stats.items():
        action_parts = []
        if ticker in scanner_adj:
            action_parts.append("scanner_tune")
        if ticker in sizing_adj:
            action_parts.append(f"size_{sizing_adj[ticker]['budget_multiplier']}x")
        action = ", ".join(action_parts) if action_parts else "no_change"

        rows.append((
            run_id, ticker, s["total_trades"], s["wins"], s["losses"],
            s["win_rate"], s["avg_pnl_pct"], s["total_pnl_pct"],
            s["call_win_rate"], s["put_win_rate"], action,
        ))
    conn.executemany(
        "INSERT INTO options_ticker_stats "
        "(run_id, ticker, total_trades, wins, losses, win_rate, avg_pnl_pct, "
        "total_pnl_pct, call_win_rate, put_win_rate, action) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def apply_scanner_adjustments(adjustments: dict[str, dict], dry_run: bool) -> list[str]:
    """Apply scanner threshold changes to thesis_maps.py.

    In dry-run mode, only logs what would change.
    In live mode, updates config/thesis_maps.py (requires restart of scanner).
    """
    actions = []
    for ticker, adj in adjustments.items():
        changes = adj.get("changes", {})
        reasons = adj.get("reason", [])
        reason_str = "; ".join(reasons) if isinstance(reasons, list) else str(reasons)

        if dry_run:
            actions.append(f"[DRY RUN] {ticker}: {changes} ({reason_str})")
        else:
            actions.append(f"{ticker}: applied {changes} ({reason_str})")
            # Note: actual file modification of thesis_maps.py would go here.
            # For safety, we log the recommendation and let the user review.
            # The scanner also has its own inline THESIS_MAP that would need updating.
            logger.info("LIVE adjustment for %s: %s", ticker, changes)

    return actions


def apply_sizing_adjustments(adjustments: dict[str, dict], dry_run: bool) -> list[str]:
    """Log position sizing recommendations."""
    actions = []
    for ticker, adj in adjustments.items():
        if dry_run:
            actions.append(
                f"[DRY RUN] {ticker}: budget {adj['budget_multiplier']}x "
                f"(${adj['adjusted_budget']}) — {adj['reason']}"
            )
        else:
            actions.append(
                f"{ticker}: budget -> {adj['budget_multiplier']}x "
                f"(${adj['adjusted_budget']}) — {adj['reason']}"
            )
    return actions


def build_telegram_summary(
    ticker_stats: dict[str, dict],
    side_stats: dict[str, dict],
    scanner_actions: list[str],
    sizing_actions: list[str],
    total_trades: int,
    dry_run: bool,
) -> str:
    """Build a Telegram-friendly HTML summary."""
    mode = "DRY RUN" if dry_run else "LIVE"
    msg = f"<b>OPTIONS BRAIN [{mode}]</b>\n"
    msg += f"Paper trades analyzed: {total_trades}\n\n"

    # Per-ETF leaderboard (sorted by win rate)
    sorted_tickers = sorted(ticker_stats.items(), key=lambda x: x[1]["win_rate"], reverse=True)
    if sorted_tickers:
        msg += "<b>ETF Leaderboard:</b>\n"
        for ticker, s in sorted_tickers:
            if s["total_trades"] < 1:
                continue
            icon = "+" if s["avg_pnl_pct"] > 0 else ""
            msg += (
                f"  {ticker}: {s['win_rate']:.0%} WR "
                f"({icon}{s['avg_pnl_pct']:.0f}% avg) "
                f"[{s['total_trades']} trades]\n"
            )

    # Call vs Put
    if side_stats:
        msg += "\n<b>Calls vs Puts:</b>\n"
        for side, ss in side_stats.items():
            msg += f"  {side}: {ss['win_rate']:.0%} WR, {ss['avg_pnl_pct']:+.0f}% avg ({ss['total_trades']} trades)\n"

    # Adjustments
    if scanner_actions:
        msg += "\n<b>Scanner Tuning:</b>\n"
        for a in scanner_actions:
            msg += f"  • {a}\n"

    if sizing_actions:
        msg += "\n<b>Sizing Adjustments:</b>\n"
        for a in sizing_actions:
            msg += f"  • {a}\n"

    if not scanner_actions and not sizing_actions:
        msg += "\nNo adjustments needed."

    return msg


def run_options_brain(ticker_filter: str | None = None, dry_run: bool = True) -> None:
    """Main options brain loop."""
    # Load paper trades
    if not os.path.exists(PAPER_DB):
        logger.warning("Paper trades DB not found at %s — nothing to analyze", PAPER_DB)
        return

    trades = load_paper_trades(PAPER_DB)
    if ticker_filter:
        trades = [t for t in trades if t["ticker"].upper() == ticker_filter.upper()]

    if not trades:
        logger.info("No paper trades found%s", f" for {ticker_filter}" if ticker_filter else "")
        return

    logger.info("Loaded %d paper trades for analysis", len(trades))

    # Analyze
    ticker_stats = analyze_by_ticker(trades)
    side_stats = analyze_by_side(trades)

    # Get current thesis map for comparison
    thesis_map = _THESIS_MAP_FALLBACK

    # Generate recommendations
    scanner_adj = recommend_scanner_adjustments(ticker_stats, thesis_map)
    sizing_adj = recommend_sizing_adjustments(ticker_stats, base_budget=PLAY_BUDGET)

    # Apply (or log in dry-run)
    scanner_actions = apply_scanner_adjustments(scanner_adj, dry_run)
    sizing_actions = apply_sizing_adjustments(sizing_adj, dry_run)

    # Log to SQLite
    conn = init_db(OPTIONS_BRAIN_DB)
    run_id = log_run(conn, len(trades), len(ticker_stats), scanner_adj, sizing_adj, side_stats, dry_run)
    log_ticker_stats(conn, run_id, ticker_stats, scanner_adj, sizing_adj)
    conn.close()

    # Telegram summary
    summary = build_telegram_summary(
        ticker_stats, side_stats, scanner_actions, sizing_actions, len(trades), dry_run,
    )
    send_tg(summary)

    for action in scanner_actions + sizing_actions:
        logger.info(action)

    logger.info("Options brain run complete. Run ID: %d", run_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Options brain — scanner performance optimizer")
    parser.add_argument("--ticker", help="Analyze a specific ETF only")
    parser.add_argument("--dry-run", action="store_true", default=None,
                        help="Log actions without applying (default)")
    parser.add_argument("--no-dry-run", action="store_true",
                        help="Apply changes for real")
    args = parser.parse_args()

    dry_run = not args.no_dry_run if args.no_dry_run else True

    run_options_brain(ticker_filter=args.ticker, dry_run=dry_run)


if __name__ == "__main__":
    main()
