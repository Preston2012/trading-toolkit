"""Quick trade viewer.

Pulls recent trades from Freqtrade bot REST APIs.
No SSH required -- connects directly to bot API endpoints.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests

from config.settings import BOTS, FT_PASS, FT_USER, VPS_HOST


def main() -> None:
    """Fetch and display recent trades from all bots."""
    for bot in BOTS:
        url = f"http://{VPS_HOST}:{bot['port']}/api/v1/trades"
        try:
            resp = requests.get(
                url,
                auth=(FT_USER, FT_PASS),
                params={"limit": 5},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            total = data.get("trades_count", 0)
            trades = data.get("trades", [])
            print(f"{bot['name']}: {total} trades total, {len(trades)} shown")
            for t in trades:
                pair = t.get("pair", "?")
                open_date = t.get("open_date", "?")
                profit = t.get("close_profit", "open")
                print(f"  {pair} | {open_date} | profit: {profit}")
        except requests.RequestException as exc:
            print(f"{bot['name']}: Error - {exc}")


if __name__ == "__main__":
    main()
