"""Unit tests for option grading logic."""

import pytest

from core.grading import grade


class TestGrade:
    """Tests for option contract grading."""

    def test_grade_a_perfect_setup(self) -> None:
        """High OI, high volume, cheap premium, sweet spot DTE = Grade A."""
        result = grade(
            premium=0.10, volume=300, oi=600,
            days=45, otm_pct=5.0, max_otm=15.0,
        )
        assert result == "A"

    def test_grade_d_no_liquidity(self) -> None:
        """Zero OI and zero volume should produce Grade D."""
        result = grade(
            premium=0.10, volume=0, oi=0,
            days=45, otm_pct=5.0, max_otm=15.0,
        )
        assert result == "D"

    def test_otm_penalty(self) -> None:
        """OTM exceeding max_otm should apply -30 penalty."""
        # Without OTM penalty this would be A (25+25+25+25 = 100)
        grade_within = grade(
            premium=0.10, volume=300, oi=600,
            days=45, otm_pct=10.0, max_otm=15.0,
        )
        # With OTM penalty (100 - 30 = 70, still A but borderline)
        grade_beyond = grade(
            premium=0.10, volume=300, oi=600,
            days=45, otm_pct=20.0, max_otm=15.0,
        )
        assert grade_within == "A"
        assert grade_beyond == "A"  # 100 - 30 = 70, still >= 70

    def test_grade_a_moderate_liquidity(self) -> None:
        """Moderate OI and volume still scores A with ideal premium and DTE."""
        result = grade(
            premium=0.10, volume=60, oi=120,
            days=45, otm_pct=5.0, max_otm=15.0,
        )
        # OI>100=20, vol>50=20, premium 0.05-0.50=25, DTE 30-60=25 = 90
        assert result == "A"

    def test_grade_b_actual(self) -> None:
        """Score of 60 (OI=30, vol=25, premium=$1.20, DTE=75) should be Grade B."""
        result = grade(
            premium=1.20, volume=25, oi=30,
            days=75, otm_pct=5.0, max_otm=15.0,
        )
        # OI>20=10, vol>20=15, premium 1.00-1.50=15, DTE 60-90=20 = 60
        assert result == "B"

    def test_grade_c_weak_setup(self) -> None:
        """Score of 40 (low volume, cheap OI, short DTE) should be Grade C."""
        result = grade(
            premium=1.20, volume=10, oi=30,
            days=28, otm_pct=5.0, max_otm=15.0,
        )
        # OI>20=10, vol<20=0, premium 1.00-1.50=15, DTE 25-30=15 = 40
        assert result == "C"

    def test_low_oi_penalty(self) -> None:
        """OI below 10 should apply -20 penalty."""
        # Without penalty: vol>200=25, premium=25, DTE=25 = 75 -> A
        # With OI<10 penalty: 75 - 20 = 55 -> B
        result = grade(
            premium=0.10, volume=300, oi=5,
            days=45, otm_pct=5.0, max_otm=15.0,
        )
        assert result == "B"

    def test_low_volume_penalty(self) -> None:
        """Volume below 5 should apply -15 penalty."""
        result = grade(
            premium=0.10, volume=2, oi=600,
            days=45, otm_pct=5.0, max_otm=15.0,
        )
        # OI>500=25, vol<5 penalty=-15, premium=25, DTE=25 = 60 -> B
        assert result == "B"

    def test_grade_boundary_70(self) -> None:
        """Score of exactly 70 should be Grade A."""
        # OI>500=25, vol>200=25, premium=25, DTE=25 = 100, OTM penalty=-30 = 70
        result = grade(
            premium=0.10, volume=300, oi=600,
            days=45, otm_pct=25.0, max_otm=15.0,
        )
        assert result == "A"  # exactly 70

    def test_spread_penalty_wide(self) -> None:
        """Spread > 30% should apply -15 penalty."""
        # Without spread: 25+25+25+25 = 100 -> A
        # With 35% spread: 100 - 15 = 85 -> A (still)
        result = grade(
            premium=0.10, volume=300, oi=600,
            days=45, otm_pct=5.0, max_otm=15.0,
            spread_pct=35.0,
        )
        assert result == "A"  # 85 still A

        # OTM penalty + spread penalty: 100 - 30 - 15 = 55 -> B
        result = grade(
            premium=0.10, volume=300, oi=600,
            days=45, otm_pct=25.0, max_otm=15.0,
            spread_pct=35.0,
        )
        assert result == "B"

    def test_spread_penalty_extreme(self) -> None:
        """Spread > 50% should apply -25 penalty."""
        # 100 - 25 = 75 -> A
        result_extreme = grade(
            premium=0.10, volume=300, oi=600,
            days=45, otm_pct=5.0, max_otm=15.0,
            spread_pct=55.0,
        )
        assert result_extreme == "A"

        # Combined with OTM: 100 - 30 - 25 = 45 -> C
        result_combined = grade(
            premium=0.10, volume=300, oi=600,
            days=45, otm_pct=25.0, max_otm=15.0,
            spread_pct=55.0,
        )
        assert result_combined == "C"

    def test_no_spread_no_penalty(self) -> None:
        """None spread should not affect score (backward compatible)."""
        result = grade(
            premium=0.10, volume=300, oi=600,
            days=45, otm_pct=5.0, max_otm=15.0,
            spread_pct=None,
        )
        assert result == "A"
