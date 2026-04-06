#!/bin/bash
echo "Starting trade data download at $(date)"
cd /root/freqtrade-sniper

# Download trades for each pair individually (more reliable)
PAIRS="BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT LTC/USDT LINK/USDT ADA/USDT"

for PAIR in $PAIRS; do
    echo "=== Downloading $PAIR at $(date) ==="
    docker-compose run --rm freqtrade download-data \
        --exchange kraken \
        --pairs $PAIR \
        --dl-trades \
        --timeframes 5m 15m 1h \
        --days 60 2>&1
    echo "=== $PAIR complete at $(date) ==="
done

echo "=== ALL DOWNLOADS COMPLETE at $(date) ==="
