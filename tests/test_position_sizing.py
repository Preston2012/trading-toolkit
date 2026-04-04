"""Unit tests for position sizing and exit ladder generation."""

import pytest

from core.position_sizing import PositionResult, build_ladder, calc_position


class TestCalcPosition:
    """Tests for position size calculation."""

    def test_basic_sizing(self) -> None:
        """$3000 fund, $0.10 premium = 9 contracts (3% = $90 / $10 per contract)."""
        result = calc_position(
            premium=0.10, price=50.0, strike=55.0,
            days=45, trade_fund=3000.0, side="call",
        )
        assert result["contracts"] == 9
        assert result["total_cost"] == 90.0
        assert result["pct_of_fund"] == 3.0

    def test_expensive_premium_minimum_one(self) -> None:
        """Very expensive premium should still give at least 1 contract."""
        result = calc_position(
            premium=5.00, price=100.0, strike=110.0,
            days=45, trade_fund=3000.0, side="call",
        )
        assert result["contracts"] == 1
        assert result["total_cost"] == 500.0

    def test_kill_price(self) -> None:
        """Kill price should be 50% of premium."""
        result = calc_position(
            premium=0.50, price=100.0, strike=105.0,
            days=45, trade_fund=3000.0, side="call",
        )
        assert result["kill_price"] == 0.25

    def test_put_side(self) -> None:
        """Put side should calculate correctly."""
        result = calc_position(
            premium=0.20, price=100.0, strike=90.0,
            days=45, trade_fund=3000.0, side="put",
        )
        assert result["contracts"] == 4
        assert result["total_cost"] == 80.0

    def test_pct_of_fund_accuracy(self) -> None:
        """Percentage of fund should be accurate."""
        result = calc_position(
            premium=1.00, price=100.0, strike=110.0,
            days=45, trade_fund=5000.0, side="call",
        )
        expected_pct = round(result["total_cost"] / 5000.0 * 100, 1)
        assert result["pct_of_fund"] == expected_pct


class TestBuildLadder:
    """Tests for exit ladder generation."""

    def test_four_tranches_for_8_plus(self) -> None:
        """8+ contracts should produce 4 exit tranches."""
        ladder = build_ladder(10)
        assert len(ladder) == 4
        total = sum(t["contracts"] for t in ladder)
        assert total == 10, f"Ladder contracts should sum to 10, got {total}"

    def test_three_tranches_for_4_to_7(self) -> None:
        """4-7 contracts should produce 3 exit tranches."""
        ladder = build_ladder(6)
        assert len(ladder) == 3
        total = sum(t["contracts"] for t in ladder)
        assert total == 6

    def test_two_tranches_for_under_4(self) -> None:
        """Under 4 contracts should produce 2 exit tranches."""
        ladder = build_ladder(2)
        assert len(ladder) == 2
        total = sum(t["contracts"] for t in ladder)
        assert total == 2

    def test_single_contract_ladder(self) -> None:
        """Single contract should split into 1 + 0."""
        ladder = build_ladder(1)
        assert len(ladder) == 2
        assert ladder[0]["contracts"] == 1
        assert ladder[1]["contracts"] == 0

    def test_ladder_targets_present(self) -> None:
        """Each tranche should have a target description."""
        ladder = build_ladder(10)
        for tranche in ladder:
            assert "target" in tranche
            assert len(tranche["target"]) > 0
