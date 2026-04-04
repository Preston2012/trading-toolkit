"""Technical analysis indicators.

Computes RSI 14, EMA 20/50 trend, 20-day support/resistance,
average volume, and 30-day historical volatility from price data.
"""

from typing import TypedDict

import pandas as pd


class TechnicalData(TypedDict):
    """Technical indicator snapshot for a ticker."""

    rsi: float
    trend: str
    ema20: float
    ema50: float
    hi20: float
    lo20: float
    avg_vol: int
    hv30: float
    price: float


def compute_rsi(close: pd.Series, period: int = 14) -> float:
    """Calculate RSI from a closing price series.

    Args:
        close: Series of closing prices.
        period: Lookback period (default 14).

    Returns:
        RSI value rounded to one decimal place.
    """
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    last_gain = float(gain.iloc[-1])
    last_loss = float(loss.iloc[-1])
    if last_loss == 0:
        return 100.0 if last_gain > 0 else 50.0
    rs = last_gain / last_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 1)


def compute_ema(close: pd.Series, span: int) -> float:
    """Calculate exponential moving average.

    Args:
        close: Series of closing prices.
        span: EMA span in periods.

    Returns:
        Latest EMA value rounded to two decimal places.
    """
    return round(float(close.ewm(span=span).mean().iloc[-1]), 2)


def compute_historical_volatility(close: pd.Series, window: int = 30) -> float:
    """Calculate annualized historical volatility.

    Args:
        close: Series of closing prices.
        window: Lookback window in trading days.

    Returns:
        Annualized volatility as a percentage, rounded to one decimal.
    """
    returns = close.pct_change().dropna()
    std = returns.tail(window).std()
    return round(float(std * (252 ** 0.5) * 100), 1)


def get_technicals(ticker: str) -> TechnicalData | None:
    """Fetch technical indicators for a ticker.

    Pulls 3 months of daily data via yfinance and computes
    RSI 14, EMA 20/50, 20-day high/low, average volume,
    and 30-day historical volatility.

    Args:
        ticker: Stock or ETF ticker symbol.

    Returns:
        TechnicalData dict, or None if insufficient data.
    """
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        hist = t.history(period="3mo")
        if len(hist) < 20:
            return None

        close = hist["Close"]
        price = round(float(close.iloc[-1]), 2)

        rsi = compute_rsi(close)
        ema20 = compute_ema(close, 20)
        ema50 = compute_ema(close, 50)
        trend = "BULLISH" if ema20 > ema50 else "BEARISH"

        hi20 = round(float(close.tail(20).max()), 2)
        lo20 = round(float(close.tail(20).min()), 2)
        avg_vol = int(hist["Volume"].tail(20).mean())
        hv30 = compute_historical_volatility(close)

        return TechnicalData(
            rsi=rsi,
            trend=trend,
            ema20=ema20,
            ema50=ema50,
            hi20=hi20,
            lo20=lo20,
            avg_vol=avg_vol,
            hv30=hv30,
            price=price,
        )
    except Exception:
        return None
