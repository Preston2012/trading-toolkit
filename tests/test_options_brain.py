"""Unit tests for the options brain analyzer."""

from core.options_brain_analyzer import (
    analyze_by_side,
    analyze_by_ticker,
    calc_trade_pnl,
    recommend_scanner_adjustments,
    recommend_sizing_adjustments,
)


def _trade(ticker: str, side: str, entry: float, current: float,
           status: str = "OPEN", exit_premium: float | None = None,
           qty: int = 10) -> dict:
    """Helper to create a mock paper trade."""
    return {
        "id": 1,
        "ticker": ticker,
        "side": side,
        "strike": 100.0,
        "expiry": "2026-05-15",
        "entry_premium": entry,
        "entry_date": "2026-04-01T10:00:00",
        "entry_qty": qty,
        "current_premium": current,
        "last_updated": "2026-04-06T10:00:00",
        "exit_premium": exit_premium,
        "exit_date": None,
        "status": status,
        "pnl_pct": None,
    }


# --- calc_trade_pnl ---

def test_pnl_open_trade_profit():
    t = _trade("XLE", "CALL", entry=0.50, current=0.75)
    assert calc_trade_pnl(t) == 50.0  # (0.75 - 0.50) / 0.50 * 100


def test_pnl_open_trade_loss():
    t = _trade("XLE", "CALL", entry=1.00, current=0.60)
    assert calc_trade_pnl(t) == -40.0


def test_pnl_expired_trade():
    t = _trade("XLE", "CALL", entry=0.50, current=0.0, status="EXPIRED", exit_premium=0.0)
    assert calc_trade_pnl(t) == -100.0


def test_pnl_closed_trade():
    t = _trade("SPY", "PUT", entry=0.40, current=0.0, status="CLOSED", exit_premium=1.20)
    assert abs(calc_trade_pnl(t) - 200.0) < 0.01


def test_pnl_zero_entry():
    t = _trade("XLE", "CALL", entry=0.0, current=0.50)
    assert calc_trade_pnl(t) == 0.0


# --- analyze_by_ticker ---

def test_by_ticker_basic():
    trades = [
        _trade("XLE", "CALL", 0.50, 0.75),   # +50%
        _trade("XLE", "CALL", 0.50, 0.25),   # -50%
        _trade("XLE", "PUT", 0.30, 0.60),    # +100%
        _trade("SPY", "CALL", 1.00, 0.50),   # -50%
    ]
    stats = analyze_by_ticker(trades)
    assert "XLE" in stats
    assert "SPY" in stats
    assert stats["XLE"]["total_trades"] == 3
    assert stats["XLE"]["wins"] == 2
    assert stats["XLE"]["losses"] == 1
    assert stats["SPY"]["total_trades"] == 1
    assert stats["SPY"]["win_rate"] == 0.0


def test_by_ticker_empty():
    assert analyze_by_ticker([]) == {}


def test_by_ticker_win_rate():
    trades = [
        _trade("JETS", "CALL", 0.20, 0.50),  # win
        _trade("JETS", "CALL", 0.20, 0.40),  # win
        _trade("JETS", "CALL", 0.20, 0.10),  # loss
        _trade("JETS", "CALL", 0.20, 0.30),  # win
    ]
    stats = analyze_by_ticker(trades)
    assert stats["JETS"]["win_rate"] == 0.75


def test_by_ticker_call_put_split():
    trades = [
        _trade("XLE", "CALL", 0.50, 0.75),  # call win
        _trade("XLE", "CALL", 0.50, 0.25),  # call loss
        _trade("XLE", "PUT", 0.30, 0.60),   # put win
        _trade("XLE", "PUT", 0.30, 0.10),   # put loss
    ]
    stats = analyze_by_ticker(trades)
    assert stats["XLE"]["call_win_rate"] == 0.5
    assert stats["XLE"]["put_win_rate"] == 0.5


# --- analyze_by_side ---

def test_by_side():
    trades = [
        _trade("XLE", "CALL", 0.50, 0.75),
        _trade("SPY", "CALL", 0.50, 0.25),
        _trade("TLT", "PUT", 0.30, 0.60),
    ]
    stats = analyze_by_side(trades)
    assert stats["CALL"]["total_trades"] == 2
    assert stats["PUT"]["total_trades"] == 1
    assert stats["PUT"]["win_rate"] == 1.0


# --- recommend_scanner_adjustments ---

def test_scanner_adj_strong_performer():
    ticker_stats = {
        "XLE": {
            "total_trades": 10, "wins": 7, "losses": 3,
            "win_rate": 0.70, "avg_pnl_pct": 30.0, "total_pnl_pct": 300.0,
            "best_trade_pnl": 100.0, "worst_trade_pnl": -40.0,
            "avg_entry_premium": 0.40, "call_win_rate": 0.70, "put_win_rate": 0.70,
        }
    }
    thesis = {"XLE": {"max_otm": 15, "min_vol": 20, "min_oi": 50}}
    adj = recommend_scanner_adjustments(ticker_stats, thesis)
    assert "XLE" in adj
    assert adj["XLE"]["changes"]["max_otm"] == 18  # widened by 3


def test_scanner_adj_poor_performer():
    ticker_stats = {
        "JETS": {
            "total_trades": 8, "wins": 1, "losses": 7,
            "win_rate": 0.125, "avg_pnl_pct": -50.0, "total_pnl_pct": -400.0,
            "best_trade_pnl": 10.0, "worst_trade_pnl": -100.0,
            "avg_entry_premium": 0.30, "call_win_rate": 0.10, "put_win_rate": 0.20,
        }
    }
    thesis = {"JETS": {"max_otm": 25, "min_vol": 15, "min_oi": 30}}
    adj = recommend_scanner_adjustments(ticker_stats, thesis)
    assert "JETS" in adj
    assert adj["JETS"]["changes"]["max_otm"] == 22  # tightened by 3
    assert adj["JETS"]["changes"]["min_vol"] == 25   # raised by 10


def test_scanner_adj_skips_low_trades():
    ticker_stats = {
        "NEW": {"total_trades": 1, "wins": 0, "losses": 1,
                "win_rate": 0.0, "avg_pnl_pct": -80.0, "total_pnl_pct": -80.0,
                "best_trade_pnl": -80.0, "worst_trade_pnl": -80.0,
                "avg_entry_premium": 0.50, "call_win_rate": 0.0, "put_win_rate": 0.0}
    }
    thesis = {"NEW": {"max_otm": 15, "min_vol": 20, "min_oi": 50}}
    adj = recommend_scanner_adjustments(ticker_stats, thesis)
    assert "NEW" not in adj


def test_scanner_adj_no_change_for_average():
    ticker_stats = {
        "SPY": {
            "total_trades": 10, "wins": 5, "losses": 5,
            "win_rate": 0.50, "avg_pnl_pct": 5.0, "total_pnl_pct": 50.0,
            "best_trade_pnl": 60.0, "worst_trade_pnl": -40.0,
            "avg_entry_premium": 0.80, "call_win_rate": 0.50, "put_win_rate": 0.50,
        }
    }
    thesis = {"SPY": {"max_otm": 8, "min_vol": 100, "min_oi": 200}}
    adj = recommend_scanner_adjustments(ticker_stats, thesis)
    assert "SPY" not in adj


# --- recommend_sizing_adjustments ---

def test_sizing_scale_up():
    ticker_stats = {
        "XLE": {
            "total_trades": 10, "wins": 7, "losses": 3,
            "win_rate": 0.70, "avg_pnl_pct": 40.0, "total_pnl_pct": 400.0,
            "best_trade_pnl": 100.0, "worst_trade_pnl": -30.0,
            "avg_entry_premium": 0.40, "call_win_rate": 0.70, "put_win_rate": 0.70,
        }
    }
    adj = recommend_sizing_adjustments(ticker_stats, base_budget=400)
    assert "XLE" in adj
    assert adj["XLE"]["budget_multiplier"] == 1.5
    assert adj["XLE"]["adjusted_budget"] == 600


def test_sizing_scale_down():
    ticker_stats = {
        "JETS": {
            "total_trades": 10, "wins": 2, "losses": 8,
            "win_rate": 0.20, "avg_pnl_pct": -45.0, "total_pnl_pct": -450.0,
            "best_trade_pnl": 20.0, "worst_trade_pnl": -100.0,
            "avg_entry_premium": 0.25, "call_win_rate": 0.20, "put_win_rate": 0.20,
        }
    }
    adj = recommend_sizing_adjustments(ticker_stats, base_budget=400)
    assert "JETS" in adj
    assert adj["JETS"]["budget_multiplier"] == 0.5
    assert adj["JETS"]["adjusted_budget"] == 200


def test_sizing_no_change_average():
    ticker_stats = {
        "SPY": {
            "total_trades": 10, "wins": 4, "losses": 6,
            "win_rate": 0.45, "avg_pnl_pct": -2.0, "total_pnl_pct": -20.0,
            "best_trade_pnl": 60.0, "worst_trade_pnl": -40.0,
            "avg_entry_premium": 0.80, "call_win_rate": 0.45, "put_win_rate": 0.45,
        }
    }
    adj = recommend_sizing_adjustments(ticker_stats, base_budget=400)
    assert "SPY" not in adj  # 45% WR with small negative avg = no adjustment
