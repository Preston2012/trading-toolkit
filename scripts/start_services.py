"""Service orchestrator.

Starts, enables, and verifies all systemd services on the trading VPS.
Reports overall system health including Docker containers and memory.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import ALL_SERVICES, MANAGED_SERVICES, VPS_HOST, VPS_PASSWORD, VPS_USER
from core.ssh_client import VPSClient


def main() -> None:
    """Start all managed services and report system health."""
    with VPSClient(VPS_HOST, VPS_USER, VPS_PASSWORD) as vps:
        vps.run("systemctl daemon-reload", timeout=60)

        print("=== Starting managed services ===")
        for service in MANAGED_SERVICES:
            vps.run(f"systemctl enable {service} 2>/dev/null")
            vps.run(f"systemctl restart {service}")
            result = vps.run(f"systemctl is-active {service}")
            print(f"  {service}: {result.stdout}")

        print("\n=== FULL SYSTEM CHECK ===")
        active_count = 0
        for service in ALL_SERVICES:
            result = vps.run(f"systemctl is-active {service}")
            status = result.stdout
            print(f"  {service}: {status}")
            if status == "active":
                active_count += 1

        print(f"\n{active_count}/{len(ALL_SERVICES)} services active")

        containers = vps.run("docker ps --format {{.Names}} | wc -l")
        memory = vps.run("free -m | grep Mem")
        scripts = vps.run("ls /root/scripts/*.py | wc -l")

        print(f"\nDocker: {containers.stdout} containers")
        print(f"Memory: {memory.stdout}")
        print(f"Scripts: {scripts.stdout} total")


if __name__ == "__main__":
    main()
