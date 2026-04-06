#!/bin/bash
systemctl daemon-reload
SERVICES="polymarket-scanner rss-scraper arb-bridge morning-briefing ibit-monitor position-tracker execution-monitor unified-reporter weekly-report trading-alerts regime-filter regime-controller"
for svc in $SERVICES; do
  systemctl restart "$svc" 2>&1
  sleep 1
done
sleep 2
for svc in $SERVICES; do
  STATUS=$(systemctl is-active "$svc")
  echo "$svc: $STATUS"
done
