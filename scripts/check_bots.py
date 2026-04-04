"""Freqtrade bot health checker.

Connects to VPS and checks Docker container status,
recent logs, and memory usage for all trading bots.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import BOTS, VPS_HOST, VPS_PASSWORD, VPS_USER
from core.ssh_client import VPSClient


def main() -> None:
    """Check health of all Freqtrade bot containers."""
    with VPSClient(VPS_HOST, VPS_USER, VPS_PASSWORD) as vps:
        print("=== CONTAINER STATUS ===")
        result = vps.run("docker ps -a")
        print(result.stdout)

        for bot in BOTS:
            print(f"\n=== {bot['name'].upper()} ({bot['container']}) ===")
            result = vps.run(f"docker logs {bot['container']} --tail 15 2>&1")
            print(result.output)

        print("\n=== MEMORY ===")
        result = vps.run("free -m")
        print(result.stdout)


if __name__ == "__main__":
    main()
