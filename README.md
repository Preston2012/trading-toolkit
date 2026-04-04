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

## Architecture

```
trading-toolkit/
    config/
        settings.py          # Centralized env var access, bot/service definitions
        thesis_maps.py       # 12-ETF macro thesis map + news keyword-to-trade map
    core/
        ssh_client.py        # VPSClient: shared SSH/SFTP with retry + context manager
        telegram.py          # Telegram Bot API alert helper
        technicals.py        # RSI 14, EMA 20/50, support/resistance, hist. volatility
        position_sizing.py   # 3% max risk sizing, staged exit ladder generation
        grading.py           # Option scoring: OI, volume, premium, DTE -> A/B/C/D
        news_scanner.py      # Finnhub headline scanner with hash-based dedup
    scripts/
        scan_options.py      # Main scanner entry point (imports core/, runs on schedule)
        check_bots.py        # Health check for 3 Freqtrade Docker containers
        full_audit.py        # Full VPS system audit (services, cron, memory, data)
        start_services.py    # Start and verify all 14 systemd services
        quick_trades.py      # Pull recent trades from Freqtrade REST APIs
        check_scanner.py     # Check scanner logs and scan result data
    tests/
        test_technicals.py   # RSI, EMA, volatility calculations
        test_position_sizing.py  # Position sizing and exit ladder logic
        test_grading.py      # Option grading and scoring thresholds
```

---

## Options Scanner

The core of this toolkit. Thesis-driven options scanner that:

- Maintains **macro thesis maps for 12 ETFs** (XLE, JETS, TLT, XBI, KRE, GDX, IBIT, SMH, XLF, SPY, XOP, ITA) with call/put theses, catalysts, and per-ticker filtering parameters
- Runs **RSI 14, EMA 20/50 trend detection**, support/resistance from 20-day range, and 30-day historical volatility via yfinance
- Filters for **cheap OTM options** ($0.02-$1.50 premium, 3-15% OTM depending on ticker beta)
- **Grades contracts A through D** based on open interest, volume, premium sweetness, and days to expiry
- Calculates **position sizes** with 3% max risk per play and automatic exit ladders:
  - 8+ contracts: 4 tranches (recover basis / lock profit / let run / moon bag)
  - 4-7 contracts: 3 tranches
  - Under 4: 2 tranches
  - Kill price at 50% premium loss
- Scans **Finnhub news** for actionable headlines with hash-based dedup (no repeat alerts)
- Sends **HTML-formatted Telegram alerts** with full technical context

### Scanner Schedule

- Full options scan: every 2 hours
- News headline scan: every 15 minutes

---

## Scripts

| Script | What It Does |
|--------|-------------|
| `scan_options.py` | Full thesis-based options scanner with Telegram alerts |
| `check_bots.py` | Health check for 3 Freqtrade Docker containers |
| `full_audit.py` | Complete VPS system audit |
| `start_services.py` | Start and verify all 14 systemd services |
| `quick_trades.py` | Pull recent trades from bot REST APIs |
| `check_scanner.py` | Check scanner logs and data files |

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
          +-- options-scanner (thesis-based)
          +-- polymarket-scanner
          +-- arb-bridge (Polymarket-to-options)
          +-- rss-scraper
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
| Testing | pytest |

## Setup

```bash
cp .env.example .env
# Fill in your credentials
pip install -r requirements.txt
python scripts/scan_options.py
```

## Testing

```bash
python -m pytest tests/ -v
```

## Environment Variables

See `.env.example` for all required variables. Never commit real credentials.

---

## Related

- **[baseline-showcase](https://github.com/Preston2012/baseline-showcase)** - Political intelligence platform (Flutter/Supabase/4 AI providers)
- **[ai-council](https://github.com/Preston2012/ai-council)** - Multi-model AI orchestration methodology
- **Portfolio:** [baseline.marketing/built](https://baseline.marketing/built)
- **Contact:** Droiddna2013@gmail.com
