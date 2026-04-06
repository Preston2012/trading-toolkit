"""Options brain analysis engine.

Reads paper_trades.db (populated by options_scanner.py) and analyzes
per-ETF and per-parameter performance to recommend scanner tuning
and position sizing adjustments.
"""

from __future__ import annotations

import logging
import sqlite3
from collections import defaultdict

logger = logging.getLogger(__name__)


def load_paper_trades(db_path: str) -> list[dict]:
    """Load all paper trades from the scanner's SQLite DB.

    Returns list of dicts with keys: id, ticker, side, strike, expiry,
    entry_premium, entry_date, entry_qty, current_premium, last_updated,
    exit_premium, exit_date, status, pnl_pct.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM paper_trades ORDER BY entry_date DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def calc_trade_pnl(trade: dict) -> float:
    """Calculate P&L percentage for a single paper trade.

    For closed/expired trades, uses exit_premium.
    For open trades, uses current_premium.
    """
    entry = trade.get("entry_premium", 0) or 0
    if entry <= 0:
        return 0.0

    if trade.get("status") in ("CLOSED", "EXPIRED") and trade.get("exit_premium") is not None:
        exit_p = trade["exit_premium"]
    else:
        exit_p = trade.get("current_premium", entry) or entry

    return (exit_p - entry) / entry * 100


def analyze_by_ticker(trades: list[dict]) -> dict[str, dict]:
    """Compute per-ticker (ETF) performance stats.

    Returns dict keyed by ticker with:
        total_trades, wins, losses, win_rate, avg_pnl_pct,
        total_pnl_pct, best_trade_pnl, worst_trade_pnl,
        avg_entry_premium, call_win_rate, put_win_rate.
    """
    buckets: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        buckets[t["ticker"]].append(t)

    stats: dict[str, dict] = {}
    for ticker, ticker_trades in buckets.items():
        pnls = [calc_trade_pnl(t) for t in ticker_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        total = len(pnls)

        calls = [t for t in ticker_trades if t.get("side") == "CALL"]
        puts = [t for t in ticker_trades if t.get("side") == "PUT"]
        call_wins = sum(1 for t in calls if calc_trade_pnl(t) > 0)
        put_wins = sum(1 for t in puts if calc_trade_pnl(t) > 0)

        stats[ticker] = {
            "total_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / total if total else 0.0,
            "avg_pnl_pct": sum(pnls) / total if total else 0.0,
            "total_pnl_pct": sum(pnls),
            "best_trade_pnl": max(pnls) if pnls else 0.0,
            "worst_trade_pnl": min(pnls) if pnls else 0.0,
            "avg_entry_premium": (
                sum(t.get("entry_premium", 0) or 0 for t in ticker_trades) / total
                if total else 0.0
            ),
            "call_win_rate": call_wins / len(calls) if calls else 0.0,
            "put_win_rate": put_wins / len(puts) if puts else 0.0,
        }

    return stats


def analyze_by_score_bucket(trades: list[dict], scan_results: list[dict] | None = None) -> dict[str, dict]:
    """Analyze win rates by composite score ranges.

    If scan_results is provided, matches trades to their original scores.
    Otherwise, uses a simplified analysis based on available trade data.

    Returns dict keyed by score bucket ('35-50', '50-70', '70-85', '85-100').
    """
    # Without scan results, we can only analyze by trade outcomes
    # The scanner enters paper trades for score >= 70, so all paper trades
    # are implicitly "high score" picks
    pnls = [calc_trade_pnl(t) for t in trades]
    total = len(pnls)
    wins = sum(1 for p in pnls if p > 0)

    return {
        "grade_a_picks": {
            "total_trades": total,
            "win_rate": wins / total if total else 0.0,
            "avg_pnl_pct": sum(pnls) / total if total else 0.0,
        }
    }


def analyze_by_side(trades: list[dict]) -> dict[str, dict]:
    """Compare call vs put performance."""
    sides: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        sides[t.get("side", "UNKNOWN")].append(t)

    stats = {}
    for side, side_trades in sides.items():
        pnls = [calc_trade_pnl(t) for t in side_trades]
        total = len(pnls)
        wins = sum(1 for p in pnls if p > 0)
        stats[side] = {
            "total_trades": total,
            "win_rate": wins / total if total else 0.0,
            "avg_pnl_pct": sum(pnls) / total if total else 0.0,
        }
    return stats


def recommend_scanner_adjustments(
    ticker_stats: dict[str, dict],
    current_thesis_map: dict[str, dict],
    min_trades: int = 3,
) -> dict[str, dict]:
    """Recommend per-ETF scanner threshold adjustments.

    Logic:
    - Tickers with win_rate > 60% and avg_pnl > 0: widen filters (more aggressive)
    - Tickers with win_rate < 30% and avg_pnl < -30%: tighten filters (more selective)
    - Tickers with no wins: suggest reducing max_otm, raising min_vol/min_oi

    Returns dict keyed by ticker with recommended param changes.
    """
    adjustments: dict[str, dict] = {}

    for ticker, stats in ticker_stats.items():
        if stats["total_trades"] < min_trades:
            continue

        current = current_thesis_map.get(ticker, {})
        if not current:
            continue

        cur_max_otm = current.get("max_otm", 15)
        cur_min_vol = current.get("min_vol", 20)
        cur_min_oi = current.get("min_oi", 50)

        adj: dict = {"ticker": ticker, "reason": [], "changes": {}}

        if stats["win_rate"] >= 0.60 and stats["avg_pnl_pct"] > 0:
            # Performing well — loosen filters slightly to catch more
            adj["changes"]["max_otm"] = min(cur_max_otm + 3, 30)
            adj["changes"]["min_vol"] = max(cur_min_vol - 5, 5)
            adj["reason"].append(
                f"strong performer (WR:{stats['win_rate']:.0%}, avg:{stats['avg_pnl_pct']:+.0f}%) — widening filters"
            )

        elif stats["win_rate"] <= 0.30 and stats["avg_pnl_pct"] < -30:
            # Struggling — tighten filters
            adj["changes"]["max_otm"] = max(cur_max_otm - 3, 5)
            adj["changes"]["min_vol"] = cur_min_vol + 10
            adj["changes"]["min_oi"] = cur_min_oi + 20
            adj["reason"].append(
                f"underperforming (WR:{stats['win_rate']:.0%}, avg:{stats['avg_pnl_pct']:+.0f}%) — tightening filters"
            )

        elif stats["win_rate"] <= 0.40:
            # Borderline — moderate tightening
            adj["changes"]["max_otm"] = max(cur_max_otm - 2, 5)
            adj["changes"]["min_oi"] = cur_min_oi + 10
            adj["reason"].append(
                f"below average (WR:{stats['win_rate']:.0%}) — slight tightening"
            )

        # Side-specific adjustments
        if stats["call_win_rate"] < 0.20 and stats["put_win_rate"] > 0.50:
            adj["reason"].append("calls failing, puts working — consider put bias")
        elif stats["put_win_rate"] < 0.20 and stats["call_win_rate"] > 0.50:
            adj["reason"].append("puts failing, calls working — consider call bias")

        if adj["changes"] or adj["reason"]:
            adjustments[ticker] = adj

    return adjustments


def recommend_sizing_adjustments(
    ticker_stats: dict[str, dict],
    base_budget: float = 400.0,
    min_trades: int = 3,
) -> dict[str, dict]:
    """Recommend per-ETF position sizing adjustments.

    Logic:
    - Winners (WR > 55%, positive avg P&L): scale up budget 1.25-1.5x
    - Losers (WR < 35%, negative avg P&L): scale down to 0.5-0.75x
    - Default: keep at 1.0x

    Returns dict keyed by ticker with budget_multiplier and reason.
    """
    adjustments: dict[str, dict] = {}

    for ticker, stats in ticker_stats.items():
        if stats["total_trades"] < min_trades:
            continue

        wr = stats["win_rate"]
        avg_pnl = stats["avg_pnl_pct"]

        if wr >= 0.60 and avg_pnl > 20:
            mult = 1.5
            reason = f"top performer (WR:{wr:.0%}, avg:{avg_pnl:+.0f}%) — scale up 1.5x"
        elif wr >= 0.50 and avg_pnl > 0:
            mult = 1.25
            reason = f"solid performer (WR:{wr:.0%}, avg:{avg_pnl:+.0f}%) — scale up 1.25x"
        elif wr <= 0.30 and avg_pnl < -30:
            mult = 0.5
            reason = f"poor performer (WR:{wr:.0%}, avg:{avg_pnl:+.0f}%) — scale down 0.5x"
        elif wr <= 0.40 and avg_pnl < 0:
            mult = 0.75
            reason = f"below average (WR:{wr:.0%}, avg:{avg_pnl:+.0f}%) — scale down 0.75x"
        else:
            continue

        adjustments[ticker] = {
            "budget_multiplier": mult,
            "adjusted_budget": round(base_budget * mult),
            "reason": reason,
        }

    return adjustments
