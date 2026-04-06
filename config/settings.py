"""Centralized configuration for trading toolkit.

All environment variables, bot definitions, and service lists
are accessed through this module.
"""

import os
from typing import TypedDict


class BotConfig(TypedDict):
    """Configuration for a single Freqtrade bot."""

    name: str
    port: int
    container: str


# VPS connection
VPS_HOST: str = os.environ.get("VPS_HOST", "")
VPS_USER: str = os.environ.get("VPS_USER", "root")
VPS_PASSWORD: str = os.environ.get("VPS_PASSWORD", "")

# Telegram alerts
TELEGRAM_TOKEN: str = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.environ.get("TELEGRAM_CHAT_ID", "")

# Market data
FINNHUB_KEY: str = os.environ.get("FINNHUB_KEY", "")

# Trading parameters
TRADE_FUND: float = float(os.environ.get("TRADE_FUND", "3000"))

# Freqtrade API
FT_USER: str = os.environ.get("FT_USER", "")
FT_PASS: str = os.environ.get("FT_PASS", "")

# Bot definitions (Hunter + Scout decommissioned; add new bots here)
BOTS: list[BotConfig] = [
    {"name": "Sniper", "port": 8080, "container": "ft-sniper"},
]

# Services started by start_services.py
MANAGED_SERVICES: list[str] = [
    "morning-briefing",
    "arb-bridge",
    "position-tracker",
    "rss-scraper",
    "weekly-report",
]

# Full service list for system health check
ALL_SERVICES: list[str] = [
    "polymarket-scanner",
    "replay-engine",
    "execution-monitor",
    "ibit-monitor",
    "trading-alerts",
    "trading-dashboard",
    "dashboard-http",
    "unified-reporter",
    "options-scanner",
    "morning-briefing",
    "arb-bridge",
    "position-tracker",
    "rss-scraper",
    "weekly-report",
]

# Scanner config
SEEN_HEADLINES_FILE: str = "/root/data/seen_headlines.json"
SCAN_RESULTS_FILE: str = "/root/data/options_scan.json"
SCANNER_LOG_FILE: str = "/root/logs/options-scanner.log"

# Adaptive Brain
BRAIN_DB_PATH: str = os.environ.get("BRAIN_DB_PATH", "/root/data/brain.db")
BRAIN_MIN_WIN_RATE: float = float(os.environ.get("BRAIN_MIN_WIN_RATE", "0.45"))
BRAIN_MIN_PROFIT_FACTOR: float = float(os.environ.get("BRAIN_MIN_PROFIT_FACTOR", "1.2"))
BRAIN_MAX_CONSEC_LOSSES: int = int(os.environ.get("BRAIN_MAX_CONSEC_LOSSES", "5"))
BRAIN_LOOKBACK_DAYS: int = int(os.environ.get("BRAIN_LOOKBACK_DAYS", "7"))
BRAIN_DRY_RUN: bool = os.environ.get("BRAIN_DRY_RUN", "true").lower() == "true"
