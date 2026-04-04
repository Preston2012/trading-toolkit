"""VPS full system audit.

Audits all services, scripts, data directories, cron jobs,
and memory on the trading VPS.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import VPS_HOST, VPS_PASSWORD, VPS_USER
from core.ssh_client import VPSClient

AUDIT_COMMANDS: list[tuple[str, str]] = [
    ("SCRIPTS", "ls -la /root/scripts/"),
    ("TRADING-INFRA", "ls -la /root/trading-infra/ 2>/dev/null || echo 'NO DIR'"),
    ("DATA DIR", "ls -la /root/data/ 2>/dev/null || echo 'NO DIR'"),
    ("DASHBOARD", "ls -la /root/dashboard/ 2>/dev/null || echo 'NO DIR'"),
    ("SERVICES", "systemctl list-units --type=service --state=active | grep -E 'trading|poly|replay|exec|ibit|dash'"),
    ("TMUX", "tmux list-sessions 2>&1"),
    ("CRON", "crontab -l"),
    ("KRAKEN DATA", "ls -lh /root/freqtrade-sniper/user_data/data/kraken/ 2>/dev/null || echo 'NO DATA'"),
    ("ENV FILE", "cat /root/.env 2>/dev/null || echo 'NO .env'"),
    ("PORT 8083", "ss -tlnp | grep 8083 || echo 'Dashboard not serving'"),
]


def main() -> None:
    """Run full system audit on VPS."""
    with VPSClient(VPS_HOST, VPS_USER, VPS_PASSWORD) as vps:
        for section, command in AUDIT_COMMANDS:
            print(f"=== {section} ===")
            result = vps.run(command)
            print(result.output)
            print()


if __name__ == "__main__":
    main()
