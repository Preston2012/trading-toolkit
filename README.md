# Trading Toolkit

A production automation system running 3 long-lived agents, 14 background services, and multiple real-time scanner pipelines on a Hetzner VPS. Demonstrates service orchestration (systemd), container management (Docker/Freqtrade), alert delivery (Telegram), health monitoring, and automated regime-based control logic.

Built for trading research and market analysis, but the engineering patterns (persistent agents, real-time data processing, automated decision pipelines, multi-service coordination) transfer to any domain.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB)]()
[![Docker](https://img.shields.io/badge/Docker-Freqtrade-2496ED)]()
[![Hetzner](https://img.shields.io/badge/VPS-Hetzner-D50C2D)]()

---

## Engineering Patterns Demonstrated

- **Long-running agent management:** 3 containerized bots with health checks, auto-restart, and performance tracking
- **Service orchestration:** 14 systemd services with dependency management and coordinated startup/shutdown
- **Real-time data pipelines:** Options scanner processing 12 ETFs with RSI/EMA analysis on 5-minute candles
- **Alert and notification system:** Telegram bot integration with noise reduction, threshold filtering, and deduplication
- **Regime detection and automated control:** Market regime classifier that adjusts bot behavior based on conditions
- **Infrastructure as code:** VPS provisioning, Docker configuration, and deployment scripts

---

## Architecture

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

## Scripts

| Script | What It Does |
|--------|-------------|
| `alert_system.py` | Alert routing and delivery |
| `arb_bridge.py` | Polymarket-to-options arbitrage bridge |
| `dashboard.py` | Trading dashboard service |
| `execution_monitor.py` | Trade execution monitoring |
| `ibit_monitor.py` | IBIT ETF monitoring |
| `morning_briefing.py` | Daily morning briefing (8:30 AM ET) |
| `options_scanner.py` | Thesis-based options scanner |
| `polymarket_scanner.py` | Polymarket scanner |
| `position_tracker.py` | Position tracking |
| `regime_controller.py` | Regime-based bot controller |
| `regime_filter.py` | Market regime classification |
| `replay_engine.py` | Trade replay engine |
| `rss_scraper.py` | RSS news scraper |
| `unified_reporter.py` | Unified reporting service |
| `weekly_report.py` | Weekly performance report |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Bots | Freqtrade (Docker) |
| Exchange | Kraken (20 pairs, 5-min candles) |
| Alerts | Telegram Bot API |
| VPS | Hetzner (Ubuntu 24.04, Docker) |
| Services | systemd (14 units) |

## Other Projects

- **[baseline-showcase](https://github.com/Preston2012/baseline-showcase)** - Political intelligence platform (Flutter/Supabase/4 AI providers)
- **[ai-council](https://github.com/Preston2012/ai-council)** - Multi-model AI orchestration methodology
- **Contact:** preston@baseline.marketing
