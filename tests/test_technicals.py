"""Unit tests for technical analysis indicators."""

import pandas as pd
import pytest

from core.technicals import compute_ema, compute_historical_volatility, compute_rsi


class TestComputeRSI:
    """Tests for RSI calculation."""

    def test_overbought_rsi(self) -> None:
        """Consistently rising prices produce RSI above 70."""
        prices = pd.Series([100 + i * 2 for i in range(30)])
        rsi = compute_rsi(prices, period=14)
        assert rsi > 70, f"Expected overbought RSI > 70, got {rsi}"

    def test_oversold_rsi(self) -> None:
        """Consistently falling prices produce RSI below 30."""
        prices = pd.Series([100 - i * 2 for i in range(30)])
        rsi = compute_rsi(prices, period=14)
        assert rsi < 30, f"Expected oversold RSI < 30, got {rsi}"

    def test_neutral_rsi(self) -> None:
        """Alternating up/down prices produce RSI near 50."""
        prices = pd.Series([100 + (1 if i % 2 == 0 else -1) for i in range(30)])
        rsi = compute_rsi(prices, period=14)
        assert 30 <= rsi <= 70, f"Expected neutral RSI 30-70, got {rsi}"

    def test_rsi_range(self) -> None:
        """RSI should always be between 0 and 100."""
        prices = pd.Series([50 + i * 0.5 for i in range(30)])
        rsi = compute_rsi(prices, period=14)
        assert 0 <= rsi <= 100

    def test_rsi_flat_prices_not_nan(self) -> None:
        """Flat prices should return 50 (neutral), not NaN."""
        prices = pd.Series([100.0] * 30)
        rsi = compute_rsi(prices, period=14)
        assert rsi == 50.0


class TestComputeEMA:
    """Tests for exponential moving average."""

    def test_ema_tracks_uptrend(self) -> None:
        """EMA of rising series should be below latest price."""
        prices = pd.Series([100.0 + i for i in range(50)])
        ema = compute_ema(prices, span=20)
        assert ema < prices.iloc[-1], "EMA should lag below in uptrend"

    def test_ema_tracks_downtrend(self) -> None:
        """EMA of falling series should be above latest price."""
        prices = pd.Series([200.0 - i for i in range(50)])
        ema = compute_ema(prices, span=20)
        assert ema > prices.iloc[-1], "EMA should lag above in downtrend"

    def test_shorter_ema_more_responsive(self) -> None:
        """EMA 20 should react faster than EMA 50 in a trend change."""
        flat_then_up = [100.0] * 30 + [100.0 + i * 3 for i in range(20)]
        prices = pd.Series(flat_then_up)
        ema20 = compute_ema(prices, span=20)
        ema50 = compute_ema(prices, span=50)
        assert ema20 > ema50, "Shorter EMA should lead in uptrend"


class TestHistoricalVolatility:
    """Tests for historical volatility calculation."""

    def test_flat_prices_low_vol(self) -> None:
        """Flat prices should produce near-zero volatility."""
        prices = pd.Series([100.0] * 40)
        hv = compute_historical_volatility(prices, window=30)
        assert hv == 0.0, f"Expected 0 vol for flat prices, got {hv}"

    def test_volatile_prices_high_vol(self) -> None:
        """Wildly swinging prices should produce high volatility."""
        prices = pd.Series([100 + (20 if i % 2 == 0 else -20) for i in range(40)],
                          dtype=float)
        hv = compute_historical_volatility(prices, window=30)
        assert hv > 100, f"Expected high vol for swinging prices, got {hv}"
