# Trading Toolkit

> Python automation suite for managing algorithmic trading bots, options scanning, and VPS infrastructure.
> Built by one person. 3 trading bots, 14 background services, real-time Telegram alerts.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB)]()
[![Docker](https://img.shields.io/badge/Docker-Freqtrade-2496ED)]()
[![Hetzner](https://img.shields.io/badge/VPS-Hetzner-D50C2D)]()

---

## What This Does

Manages a production trading infrastructure running on a Hetzner VPS:

- **3 Freqtrade bots** (Docker) scanning 20 Kraken pairs on 5-min candles
- **14 systemd services** including options scanner, Polymarket scanner, news scraper, regime filter, morning briefing
- **Smart options scanner** with thesis-based filtering across 12 ETFs
- **Telegram alerting** for actionable signals only (noise reduction applied)
- **Position sizing** with automatic exit ladder generation

---

## Scripts

### `scripts/options_scanner.py` (452 lines)
The crown jewel. Thesis-driven options scanner that:
- Maintains macro thesis maps for 12 ETFs (XLE, JETS, TLT, XBI, KRE, GDX, IBIT, SMH, XLF, SPY, XOP, ITA)
- Runs RSI, EMA trend, support/resistance, and historical volatility analysis
- Filters for cheap OTM options ($0.02-$1.50 premium range)
- Calculates position sizes with 3% max risk per play
- Generates staged exit ladders (recover basis -> lock profit -> moon bag)
- Scans Finnhub for Trump/Houthi/Iran headlines with hash dedup
- Sends formatted Telegram alerts with technical context

### `scripts/check_bots.py`
Health check for 3 Freqtrade Docker containers. Pulls container status, recent logs, and memory usage via SSH.

### `scripts/full_audit.py`
Full VPS system audit: scripts directory, data files, active services, tmux sessions, cron jobs, Kraken data, environment, and dashboard status.

### `scripts/start_all.py`
Service orchestrator. Starts all 14 systemd services, verifies each is active, reports Docker container count and memory usage.

### `scripts/quick_trades.py`
Pulls recent trades from 3 Freqtrade bot REST APIs. Shows trade count, pairs, open dates, and profit status.

### `scripts/check_scanner.py`
Checks options scanner output logs, scan results JSON, and Trump headline dedup data.

---

## Infrastructure

```
Hetzner VPS (Ubuntu 24.04, 4GB RAM)
    |
    +-- Docker
    |     +-- ft-sniper (NFIX7, port 8080)
    |     +-- ft-hunter (NFIX4, port 8081)
    |     +-- ft-scout  (NFIX5, port 8082)
    |
    +-- 14 systemd services
          +-- options-scanner (v5, thesis-based)
          +-- polymarket-scanner
          +-- arb-bridge (Polymarket-to-options)
          +-- rss-scraper
          +-- trump-signal (hash dedup)
          +-- position-tracker
          +-- morning-briefing (8:30 AM ET)
          +-- execution-monitor
          +-- ibit-monitor
          +-- unified-reporter
          +-- replay-engine
          +-- trading-dashboard
          +-- weekly-report
          +-- regime-filter (auto bot controller)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Bots | Freqtrade (Docker) |
| Exchange | Kraken (20 pairs, 5-min candles) |
| Market Data | yfinance, Finnhub API |
| Alerts | Telegram Bot API |
| VPS | Hetzner (Ubuntu 24.04, Docker) |
| Remote Mgmt | Paramiko (SSH/SFTP) |
| Services | systemd (14 units) |

## Setup

```bash
cp .env.example .env
# Fill in your credentials
pip install paramiko requests yfinance schedule
python scripts/options_scanner.py
```

## Environment Variables

See `.env.example` for all required variables. Never commit real credentials.

---

## Related

- **[baseline-showcase](https://github.com/Preston2012/baseline-showcase)** - Political intelligence platform (Flutter/Supabase/4 AI providers)
- **Portfolio:** [baseline.marketing/built](https://baseline.marketing/built)
- **Contact:** Droiddna2013@gmail.com
