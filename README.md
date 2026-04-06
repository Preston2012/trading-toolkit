# Trading Toolkit

A production automation system running a Freqtrade crypto bot, 14 background services, and multiple real-time scanner pipelines on a Hetzner VPS. Features two adaptive brains that auto-tune both crypto and options strategies based on performance data.

Built for trading research and market analysis, but the engineering patterns (persistent agents, real-time data processing, automated decision pipelines, multi-service coordination) transfer to any domain.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB)]()
[![Docker](https://img.shields.io/badge/Docker-Freqtrade-2496ED)]()
[![Hetzner](https://img.shields.io/badge/VPS-Hetzner-D50C2D)]()

---

## Engineering Patterns Demonstrated

- **Adaptive optimization:** Two cron-driven brains that analyze trade outcomes and auto-tune bot config + scanner thresholds
- **Service orchestration:** 14 systemd services with dependency management and coordinated startup/shutdown
- **Real-time data pipelines:** Options scanner processing 15 ETFs with RSI/EMA analysis and thesis-based filtering
- **Paper trading system:** Automatic paper entry for Grade A picks, price tracking via yfinance, P&L in SQLite
- **Alert and notification system:** Telegram bot integration with noise reduction, threshold filtering, and deduplication
- **Regime detection and automated control:** Market regime classifier that adjusts bot behavior based on conditions
- **Modular architecture:** Shared `core/` modules and `config/` settings — no code duplication across 16+ scripts

---

## Architecture

```
Hetzner VPS (Ubuntu 24.04, 4GB RAM)
    |
    +-- Docker
    |     +-- ft-sniper (NFIX7, port 8080)
    |
    +-- Adaptive Brains (cron)
    |     +-- adaptive_brain.py (crypto — tunes Freqtrade pairs via API)
    |     +-- options_brain.py (options — tunes scanner thresholds + sizing)
    |
    +-- 14 systemd services
          +-- options-scanner (thesis-based, 15 ETFs)
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
          +-- regime-filter
          +-- regime-controller
```

## Adaptive Brains

| Brain | Domain | Data Source | What It Tunes | Schedule |
|-------|--------|------------|---------------|----------|
| `adaptive_brain.py` | Crypto (Kraken, 20 pairs) | Freqtrade REST API | Pair blacklist, bot config reload | Every 6 hours |
| `options_brain.py` | Options (15 ETFs) | `paper_trades.db` from scanner | Scanner thresholds (max_otm, min_vol, min_oi), position sizing per ETF | Daily at 10pm |

Both default to **dry-run mode** for safety. Use `--no-dry-run` to apply changes live.

## Scripts

| Script | What It Does |
|--------|-------------|
| `adaptive_brain.py` | Crypto brain — auto-tunes Freqtrade via REST API |
| `options_brain.py` | Options brain — auto-tunes scanner thresholds + sizing |
| `alert_system.py` | Alert routing and delivery |
| `arb_bridge.py` | Polymarket-to-options arbitrage bridge |
| `dashboard.py` | Trading dashboard service |
| `execution_monitor.py` | Trade execution monitoring |
| `ibit_monitor.py` | IBIT ETF monitoring |
| `morning_briefing.py` | Daily morning briefing (8:30 AM ET) |
| `options_scanner.py` | Thesis-based options scanner with paper trading |
| `polymarket_scanner.py` | Polymarket scanner |
| `position_tracker.py` | Position level tracking and alerts |
| `regime_controller.py` | Regime-based bot controller |
| `regime_filter.py` | Market regime classification |
| `replay_engine.py` | Trade replay engine |
| `rss_scraper.py` | RSS news scraper |
| `unified_reporter.py` | Unified reporting service |
| `weekly_report.py` | Weekly performance report |

## Shared Modules

| Module | Purpose |
|--------|---------|
| `config/settings.py` | Centralized env vars, bot definitions, service lists |
| `config/thesis_maps.py` | Macro thesis definitions for 15 ETFs |
| `core/brain_analyzer.py` | Crypto brain analysis engine |
| `core/brain_config.py` | Freqtrade API client + config adjustment logic |
| `core/options_brain_analyzer.py` | Options brain analysis engine |
| `core/grading.py` | Option contract grading (A-D scale) |
| `core/position_sizing.py` | Position sizing and exit ladders |
| `core/technicals.py` | RSI, EMA, SMA, MACD calculations |
| `core/news_scanner.py` | Headline deduplication with fuzzy hashing |
| `core/telegram.py` | Telegram alert delivery |
| `core/ssh_client.py` | VPS SSH connection utilities |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Bots | Freqtrade (Docker) |
| Exchange | Kraken (20 pairs, 5-min candles) |
| Options Data | yfinance (15 ETFs) |
| Alerts | Telegram Bot API |
| Storage | SQLite (paper trades, brain decisions) |
| VPS | Hetzner (Ubuntu 24.04, Docker) |
| Services | systemd (14 units) + cron (2 brains) |

## Other Projects

- **[baseline-showcase](https://github.com/Preston2012/baseline-showcase)** - Political intelligence platform (Flutter/Supabase/4 AI providers)
- **[ai-council](https://github.com/Preston2012/ai-council)** - Multi-model AI orchestration methodology
- **Contact:** preston@baseline.marketing
