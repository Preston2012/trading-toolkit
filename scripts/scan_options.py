"""Thesis-based options scanner.

Scans 12 ETFs for cheap OTM options matching macro theses,
applies technical analysis and grading, calculates position
sizes with exit ladders, and sends Telegram alerts.
Skips scans outside US market hours to avoid stale data.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import schedule
import yfinance as yf

from config.settings import (
    FINNHUB_KEY,
    SCAN_RESULTS_FILE,
    SEEN_HEADLINES_FILE,
    TELEGRAM_CHAT_ID,
    TELEGRAM_TOKEN,
    TRADE_FUND,
)
from config.thesis_maps import NEWS_KEYWORDS, THESIS_MAP, TRADE_MAP
from core.grading import grade
from core.news_scanner import scan_news
from core.position_sizing import calc_position
from core.technicals import get_technicals
from core.telegram import send_tg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Grade sort order (safe dict lookup, no crash on unexpected grades)
GRADE_ORDER: dict[str, int] = {"A": 0, "B": 1, "C": 2, "D": 3}

# US Eastern Time offset (UTC-5, or UTC-4 during DST)
ET_OFFSET = timezone(timedelta(hours=-4))


def is_market_hours() -> bool:
    """Check if US equity markets are currently open.

    Returns True during 9:30 AM - 4:00 PM ET, Monday through Friday.
    News scans bypass this check since news breaks anytime.
    """
    now_et = datetime.now(ET_OFFSET)
    if now_et.weekday() >= 5:
        return False
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now_et <= market_close


def compute_spread_pct(bid: float, ask: float) -> float | None:
    """Calculate bid-ask spread as percentage of mid price.

    Args:
        bid: Bid price.
        ask: Ask price.

    Returns:
        Spread percentage, or None if data is invalid.
    """
    if bid <= 0 or ask <= 0 or ask < bid:
        return None
    mid = (bid + ask) / 2
    if mid <= 0:
        return None
    return round((ask - bid) / mid * 100, 1)


def scan_options() -> list[dict]:
    """Scan all ETFs for options matching thesis criteria.

    Iterates THESIS_MAP, pulls option chains via yfinance, filters
    for cheap OTM contracts within thesis parameters, grades each
    contract (including bid-ask spread quality), and calculates
    position sizing.

    Returns:
        List of option results sorted by grade (A first).
    """
    results: list[dict] = []

    for ticker, info in THESIS_MAP.items():
        tech = get_technicals(ticker)
        try:
            t = yf.Ticker(ticker)
            price = t.info.get("regularMarketPrice", 0)
            if price == 0:
                continue

            exps = t.options
            now = datetime.now()
            max_otm = info.get("max_otm", 15)

            for exp in exps:
                exp_dt = datetime.strptime(exp, "%Y-%m-%d")
                days = (exp_dt - now).days
                if not (25 <= days <= 120):
                    continue

                chain = t.option_chain(exp)
                sides = [
                    ("CALL", chain.calls, "call"),
                    ("PUT", chain.puts, "put"),
                ]

                for side, opts, thesis_key in sides:
                    if side == "CALL":
                        otm = opts[
                            (opts["strike"] > price * 1.03)
                            & (opts["strike"] < price * (1 + max_otm / 100))
                        ]
                    else:
                        otm = opts[
                            (opts["strike"] < price * 0.97)
                            & (opts["strike"] > price * (1 - max_otm / 100))
                        ]

                    cheap = otm[otm["lastPrice"] <= 1.50]

                    for _, row in cheap.iterrows():
                        vol = int(row.get("volume", 0) or 0)
                        oi_val = int(row.get("openInterest", 0) or 0)

                        if vol < info.get("min_vol", 10) and oi_val < info.get("min_oi", 20):
                            continue

                        iv_val = round((row.get("impliedVolatility", 0) or 0) * 100, 1)

                        if side == "CALL":
                            otm_pct = round((row["strike"] - price) / price * 100, 1)
                        else:
                            otm_pct = round((price - row["strike"]) / price * 100, 1)

                        # Bid-ask spread quality check
                        bid = float(row.get("bid", 0) or 0)
                        ask = float(row.get("ask", 0) or 0)
                        spread_pct = compute_spread_pct(bid, ask)

                        # Filter out contracts with extreme spreads (>50% of mid)
                        if spread_pct is not None and spread_pct > 50:
                            continue

                        g = grade(
                            row["lastPrice"], vol, oi_val, days,
                            otm_pct, max_otm, spread_pct,
                        )
                        if g == "D":
                            continue

                        pos = calc_position(
                            row["lastPrice"], price, row["strike"],
                            days, TRADE_FUND, side.lower(),
                        )

                        results.append({
                            "ticker": ticker,
                            "side": side,
                            "price": round(price, 2),
                            "strike": row["strike"],
                            "expiry": exp,
                            "days": days,
                            "premium": row["lastPrice"],
                            "volume": vol,
                            "oi": oi_val,
                            "iv": iv_val,
                            "otm_pct": otm_pct,
                            "spread_pct": spread_pct,
                            "grade": g,
                            "thesis": info[thesis_key],
                            "catalyst": info["catalyst"],
                            "tech": tech or {},
                            "pos": pos,
                        })

        except Exception as exc:
            logger.warning("Scan error %s: %s", ticker, exc)

    results.sort(key=lambda x: GRADE_ORDER.get(x["grade"], 99))
    return results


def fmt_alert(r: dict) -> str:
    """Format a single option result as an HTML Telegram alert.

    Args:
        r: Option result dict from scan_options().

    Returns:
        HTML-formatted string for Telegram.
    """
    s = "C" if r["side"] == "CALL" else "P"
    tech = r.get("tech", {})
    pos = r.get("pos", {})

    trend = tech.get("trend", "?")
    rsi = tech.get("rsi", "?")
    hi = tech.get("hi20", "?")
    lo = tech.get("lo20", "?")
    spread = r.get("spread_pct")
    spread_str = f" Sprd:{spread}%" if spread is not None else ""

    msg = f"<b>[{r['grade']}] {r['ticker']}</b> ${r['price']} | ${r['strike']}{s}"
    msg += f"\n  Exp: {r['expiry']} ({r['days']}d) @ ${r['premium']:.2f}"
    msg += f"\n  OTM:{r['otm_pct']}% | Vol:{r['volume']} OI:{r['oi']} IV:{r['iv']}%{spread_str}"
    msg += f"\n  Trend:{trend} RSI:{rsi} | 20d Range:${lo}-${hi}"
    msg += f"\n  <b>Size:</b> {pos.get('contracts', 1)}x (${pos.get('total_cost', 0)}) = {pos.get('pct_of_fund', 0)}% of fund"

    ladder_parts = []
    for tranche in pos.get("ladder", []):
        ladder_parts.append(f"{tranche['contracts']}x@{tranche['target']}")
    msg += f"\n  <b>Ladder:</b> {' | '.join(ladder_parts)}"

    msg += f"\n  <b>Kill:</b> ${pos.get('kill_price', 0)} (-50% of premium)"
    msg += f"\n  <i>{r['thesis']}</i>"
    msg += f"\n  Catalyst: {r['catalyst']}"
    return msg


def _send(msg: str) -> None:
    """Send a Telegram message using configured credentials."""
    send_tg(msg, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)


def run_scan() -> None:
    """Execute a full scan cycle: options + news + alerts.

    Skips option scanning outside market hours. News scanning
    runs regardless since news breaks anytime.
    """
    ts = datetime.now().strftime("%H:%M")

    # Options scan only during market hours
    results: list[dict] = []
    if is_market_hours():
        logger.info("Options scan started at %s", ts)
        results = scan_options()

        os.makedirs(os.path.dirname(SCAN_RESULTS_FILE), exist_ok=True)
        with open(SCAN_RESULTS_FILE, "w") as f:
            json.dump(results, f, indent=2, default=str)

        # Grade A calls
        a_calls = [r for r in results if r["grade"] == "A" and r["side"] == "CALL"]
        if a_calls:
            msg = f"<b>TOP CALLS (Grade A) {ts}</b>\n"
            for r in a_calls[:5]:
                msg += "\n" + fmt_alert(r) + "\n"
            _send(msg)

        # Grade A puts
        a_puts = [r for r in results if r["grade"] == "A" and r["side"] == "PUT"]
        if a_puts:
            msg = f"<b>TOP PUTS (Grade A) {ts}</b>\n"
            for r in a_puts[:5]:
                msg += "\n" + fmt_alert(r) + "\n"
            _send(msg)

        # Grade B watchlist
        b_all = [r for r in results if r["grade"] == "B"]
        if b_all:
            msg = f"<b>WATCHLIST (Grade B) {ts}</b>\n"
            for r in b_all[:6]:
                s = "C" if r["side"] == "CALL" else "P"
                pos = r.get("pos", {})
                msg += f"\n<b>{r['ticker']}</b> ${r['strike']}{s} {r['expiry']} ({r['days']}d) @ ${r['premium']:.2f}"
                msg += f"\n  Size:{pos.get('contracts', 1)}x | <i>{r['thesis'][:60]}</i>\n"
            _send(msg)
    else:
        logger.info("Outside market hours at %s, skipping options scan", ts)

    # News signals run 24/7
    news = scan_news(FINNHUB_KEY, SEEN_HEADLINES_FILE, TRADE_MAP, NEWS_KEYWORDS)
    if news:
        msg = "<b>FRESH NEWS SIGNAL</b>\n"
        for sig in news:
            msg += f"\n<b>{sig['headline']}</b>"
            msg += f"\n  Play: {sig['play']}"
            msg += f"\n  Logic: {sig['logic']}\n"
        _send(msg)

    if is_market_hours() and not results and not news:
        _send(f"<b>OPTIONS SCAN {ts}</b>\nNo quality setups this cycle.")

    c_cnt = len([r for r in results if r["side"] == "CALL"])
    p_cnt = len([r for r in results if r["side"] == "PUT"])
    logger.info("Scan complete: %d calls, %d puts, %d news signals", c_cnt, p_cnt, len(news))


def news_check() -> None:
    """Quick news-only scan (runs more frequently than full scan)."""
    signals = scan_news(FINNHUB_KEY, SEEN_HEADLINES_FILE, TRADE_MAP, NEWS_KEYWORDS)
    if signals:
        msg = "<b>FRESH NEWS SIGNAL</b>\n"
        for sig in signals:
            msg += f"\n<b>{sig['headline']}</b>\n  Play: {sig['play']}\n  Logic: {sig['logic']}\n"
        _send(msg)


if __name__ == "__main__":
    logger.info("Smart Options Scanner started")
    run_scan()
    schedule.every(2).hours.do(run_scan)
    schedule.every(15).minutes.do(news_check)
    while True:
        schedule.run_pending()
        time.sleep(60)
