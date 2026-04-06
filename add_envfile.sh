#!/bin/bash
SERVICES="arb-bridge dashboard-http execution-monitor ibit-monitor morning-briefing options-scanner polymarket-scanner position-tracker replay-engine rss-scraper trading-alerts trading-dashboard unified-reporter weekly-report"
for svc in $SERVICES; do
  FILE="/etc/systemd/system/${svc}.service"
  if [ -f "$FILE" ]; then
    if ! grep -q "EnvironmentFile" "$FILE"; then
      sed -i '/\[Service\]/a EnvironmentFile=/root/scripts/.env' "$FILE"
      echo "UPDATED: $svc"
    else
      echo "ALREADY: $svc"
    fi
  else
    echo "MISSING: $svc"
  fi
done
