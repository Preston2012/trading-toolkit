#!/bin/bash
for log in arb-bridge rss-scraper morning-briefing trading-alerts unified-reporter ibit-monitor position-tracker; do
  echo "=== $log ==="
  tail -2 /root/logs/$log.log 2>/dev/null || echo "no log"
done
