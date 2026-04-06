"""Performance analysis engine for the adaptive trading brain.

Analyzes Freqtrade trade history to identify underperforming pairs
and recommend configuration adjustments.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def analyze_pair_performance(trades: list[dict]) -> dict[str, dict]:
    """Compute per-pair stats from trade history.

    Args:
        trades: List of trade dicts from Freqtrade API (/api/v1/trades).

    Returns:
        Dict keyed by pair with stats: win_rate, profit_factor,
        total_trades, avg_duration_min, total_profit.
    """
    pairs: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        pair = t.get("pair", "UNKNOWN")
        pairs[pair].append(t)

    stats: dict[str, dict] = {}
    for pair, pair_trades in pairs.items():
        wins = [t for t in pair_trades if (t.get("profit_ratio", 0) or 0) > 0]
        losses = [t for t in pair_trades if (t.get("profit_ratio", 0) or 0) <= 0]

        gross_profit = sum(t.get("profit_abs", 0) or 0 for t in wins)
        gross_loss = abs(sum(t.get("profit_abs", 0) or 0 for t in losses))

        durations = []
        for t in pair_trades:
            dur = t.get("trade_duration")
            if dur is not None:
                durations.append(dur)

        total = len(pair_trades)
        stats[pair] = {
            "win_rate": len(wins) / total if total else 0.0,
            "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else float("inf"),
            "total_trades": total,
            "avg_duration_min": sum(durations) / len(durations) if durations else 0.0,
            "total_profit": sum(t.get("profit_abs", 0) or 0 for t in pair_trades),
        }

    return stats


def analyze_timeframe_performance(trades: list[dict]) -> dict[str, dict]:
    """Bucket trade performance by entry hour and day-of-week.

    Returns:
        Dict with 'by_hour' (0-23) and 'by_day' (0=Mon..6=Sun) keys,
        each mapping to {bucket: {win_rate, total_trades, avg_profit}}.
    """
    by_hour: dict[int, list[dict]] = defaultdict(list)
    by_day: dict[int, list[dict]] = defaultdict(list)

    for t in trades:
        open_date_str = t.get("open_date")
        if not open_date_str:
            continue
        try:
            dt = datetime.fromisoformat(open_date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        by_hour[dt.hour].append(t)
        by_day[dt.weekday()].append(t)

    def _bucket_stats(bucket_trades: list[dict]) -> dict:
        total = len(bucket_trades)
        wins = sum(1 for t in bucket_trades if (t.get("profit_ratio", 0) or 0) > 0)
        avg_profit = (
            sum(t.get("profit_abs", 0) or 0 for t in bucket_trades) / total
            if total
            else 0.0
        )
        return {"win_rate": wins / total if total else 0.0, "total_trades": total, "avg_profit": avg_profit}

    return {
        "by_hour": {h: _bucket_stats(ts) for h, ts in sorted(by_hour.items())},
        "by_day": {d: _bucket_stats(ts) for d, ts in sorted(by_day.items())},
    }


def calculate_consecutive_losses(trades: list[dict], pair: str) -> int:
    """Count current consecutive losing streak for a pair.

    Trades should be sorted by close_date ascending (as returned by FT API).
    """
    pair_trades = [t for t in trades if t.get("pair") == pair]
    streak = 0
    for t in reversed(pair_trades):
        if (t.get("profit_ratio", 0) or 0) <= 0:
            streak += 1
        else:
            break
    return streak


def identify_underperformers(
    pair_stats: dict[str, dict],
    thresholds: dict,
    trades: list[dict] | None = None,
) -> list[str]:
    """Flag pairs that fall below performance thresholds.

    Args:
        pair_stats: Output of analyze_pair_performance().
        thresholds: Dict with min_win_rate, min_profit_factor, max_consec_losses.
        trades: Full trade list (needed for consecutive loss calculation).

    Returns:
        List of pair names that should be blacklisted.
    """
    min_wr = thresholds.get("min_win_rate", 0.45)
    min_pf = thresholds.get("min_profit_factor", 1.2)
    max_cl = thresholds.get("max_consec_losses", 5)
    min_trades = thresholds.get("min_trades", 5)

    underperformers = []
    for pair, s in pair_stats.items():
        if s["total_trades"] < min_trades:
            continue
        reasons = []
        if s["win_rate"] < min_wr:
            reasons.append(f"win_rate={s['win_rate']:.2f}")
        if s["profit_factor"] < min_pf:
            reasons.append(f"pf={s['profit_factor']:.2f}")
        if trades:
            cl = calculate_consecutive_losses(trades, pair)
            if cl >= max_cl:
                reasons.append(f"consec_losses={cl}")
        if reasons:
            logger.info("Underperformer: %s — %s", pair, ", ".join(reasons))
            underperformers.append(pair)

    return underperformers


def recommend_adjustments(
    pair_stats: dict[str, dict],
    timeframe_stats: dict[str, dict],
    thresholds: dict,
    trades: list[dict] | None = None,
) -> dict:
    """Generate adjustment recommendations based on analysis.

    Returns:
        Dict with:
            blacklist_add: list of pairs to blacklist
            blacklist_remove: list of pairs performing well enough to un-blacklist
            pair_actions: dict mapping pair -> action ('keep'|'blacklist'|'watch')
    """
    underperformers = identify_underperformers(pair_stats, thresholds, trades)

    pair_actions = {}
    for pair, s in pair_stats.items():
        if pair in underperformers:
            pair_actions[pair] = "blacklist"
        elif s["total_trades"] < thresholds.get("min_trades", 5):
            pair_actions[pair] = "watch"
        else:
            pair_actions[pair] = "keep"

    return {
        "blacklist_add": underperformers,
        "blacklist_remove": [],  # Future: rehabilitate pairs after cooldown
        "pair_actions": pair_actions,
    }


def filter_trades_by_lookback(trades: list[dict], lookback_days: int) -> list[dict]:
    """Filter trades to only include those within the lookback window."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    filtered = []
    for t in trades:
        close_str = t.get("close_date")
        if not close_str:
            continue
        try:
            dt = datetime.fromisoformat(close_str.replace("Z", "+00:00"))
            if dt >= cutoff:
                filtered.append(t)
        except (ValueError, AttributeError):
            continue
    return filtered
