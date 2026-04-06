"""Unit tests for the adaptive trading brain analyzer and config modules."""

from datetime import datetime, timedelta, timezone

from core.brain_analyzer import (
    analyze_pair_performance,
    analyze_timeframe_performance,
    calculate_consecutive_losses,
    filter_trades_by_lookback,
    identify_underperformers,
    recommend_adjustments,
)
from core.brain_config import build_blacklist_update


def _make_trade(pair: str, profit_ratio: float, profit_abs: float,
                duration: float = 60.0, hours_ago: float = 1.0) -> dict:
    """Helper to create a mock trade dict matching Freqtrade API format."""
    now = datetime.now(timezone.utc)
    open_dt = now - timedelta(hours=hours_ago + duration / 60)
    close_dt = now - timedelta(hours=hours_ago)
    return {
        "pair": pair,
        "profit_ratio": profit_ratio,
        "profit_abs": profit_abs,
        "trade_duration": duration,
        "open_date": open_dt.isoformat(),
        "close_date": close_dt.isoformat(),
    }


# --- analyze_pair_performance ---

def test_pair_performance_basic():
    trades = [
        _make_trade("BTC/USDT", 0.05, 10.0),
        _make_trade("BTC/USDT", -0.02, -4.0),
        _make_trade("ETH/USDT", 0.03, 6.0),
    ]
    stats = analyze_pair_performance(trades)
    assert "BTC/USDT" in stats
    assert "ETH/USDT" in stats
    assert stats["BTC/USDT"]["total_trades"] == 2
    assert stats["BTC/USDT"]["win_rate"] == 0.5
    assert stats["ETH/USDT"]["win_rate"] == 1.0


def test_pair_performance_profit_factor():
    trades = [
        _make_trade("BTC/USDT", 0.05, 10.0),
        _make_trade("BTC/USDT", 0.03, 6.0),
        _make_trade("BTC/USDT", -0.02, -4.0),
    ]
    stats = analyze_pair_performance(trades)
    # profit_factor = gross_profit / gross_loss = 16 / 4 = 4.0
    assert stats["BTC/USDT"]["profit_factor"] == 4.0


def test_pair_performance_empty():
    stats = analyze_pair_performance([])
    assert stats == {}


def test_pair_performance_all_wins():
    trades = [
        _make_trade("SOL/USDT", 0.05, 10.0),
        _make_trade("SOL/USDT", 0.03, 6.0),
    ]
    stats = analyze_pair_performance(trades)
    assert stats["SOL/USDT"]["profit_factor"] == float("inf")


# --- analyze_timeframe_performance ---

def test_timeframe_returns_structure():
    trades = [_make_trade("BTC/USDT", 0.05, 10.0, hours_ago=1.0)]
    tf = analyze_timeframe_performance(trades)
    assert "by_hour" in tf
    assert "by_day" in tf


# --- calculate_consecutive_losses ---

def test_consecutive_losses():
    trades = [
        _make_trade("BTC/USDT", 0.05, 10.0, hours_ago=5.0),
        _make_trade("BTC/USDT", -0.01, -2.0, hours_ago=4.0),
        _make_trade("BTC/USDT", -0.02, -4.0, hours_ago=3.0),
        _make_trade("BTC/USDT", -0.01, -2.0, hours_ago=2.0),
    ]
    assert calculate_consecutive_losses(trades, "BTC/USDT") == 3


def test_consecutive_losses_no_streak():
    trades = [
        _make_trade("BTC/USDT", -0.01, -2.0, hours_ago=3.0),
        _make_trade("BTC/USDT", 0.05, 10.0, hours_ago=1.0),
    ]
    assert calculate_consecutive_losses(trades, "BTC/USDT") == 0


def test_consecutive_losses_wrong_pair():
    trades = [_make_trade("ETH/USDT", -0.01, -2.0)]
    assert calculate_consecutive_losses(trades, "BTC/USDT") == 0


# --- identify_underperformers ---

def test_identify_underperformers():
    trades = (
        [_make_trade("BAD/USDT", -0.01, -2.0, hours_ago=i) for i in range(1, 8)]
        + [_make_trade("GOOD/USDT", 0.05, 10.0, hours_ago=i) for i in range(1, 8)]
    )
    pair_stats = analyze_pair_performance(trades)
    thresholds = {"min_win_rate": 0.45, "min_profit_factor": 1.2,
                  "max_consec_losses": 5, "min_trades": 5}
    under = identify_underperformers(pair_stats, thresholds, trades)
    assert "BAD/USDT" in under
    assert "GOOD/USDT" not in under


def test_identify_underperformers_skips_low_trade_count():
    trades = [_make_trade("NEW/USDT", -0.01, -2.0)]
    pair_stats = analyze_pair_performance(trades)
    thresholds = {"min_win_rate": 0.45, "min_profit_factor": 1.2,
                  "max_consec_losses": 5, "min_trades": 5}
    under = identify_underperformers(pair_stats, thresholds, trades)
    assert "NEW/USDT" not in under


# --- recommend_adjustments ---

def test_recommend_adjustments_structure():
    trades = [_make_trade("BTC/USDT", 0.05, 10.0, hours_ago=i) for i in range(1, 8)]
    pair_stats = analyze_pair_performance(trades)
    tf_stats = analyze_timeframe_performance(trades)
    thresholds = {"min_win_rate": 0.45, "min_profit_factor": 1.2,
                  "max_consec_losses": 5, "min_trades": 5}
    rec = recommend_adjustments(pair_stats, tf_stats, thresholds, trades)
    assert "blacklist_add" in rec
    assert "blacklist_remove" in rec
    assert "pair_actions" in rec


# --- build_blacklist_update ---

def test_build_blacklist_update_no_duplicates():
    result = build_blacklist_update(["BTC/USDT", "ETH/USDT"], ["BTC/USDT"])
    assert result["add"] == ["ETH/USDT"]


def test_build_blacklist_update_all_new():
    result = build_blacklist_update(["SOL/USDT"], [])
    assert result["add"] == ["SOL/USDT"]


# --- filter_trades_by_lookback ---

def test_filter_trades_by_lookback():
    recent = _make_trade("BTC/USDT", 0.05, 10.0, hours_ago=1.0)
    old = _make_trade("BTC/USDT", 0.05, 10.0, hours_ago=200.0)
    filtered = filter_trades_by_lookback([recent, old], lookback_days=7)
    assert len(filtered) == 1
