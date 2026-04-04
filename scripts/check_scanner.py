"""Scanner log checker.

Checks options scanner output logs, scan results,
and news headline dedup data on the VPS.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import (
    SCAN_RESULTS_FILE,
    SCANNER_LOG_FILE,
    SEEN_HEADLINES_FILE,
    VPS_HOST,
    VPS_PASSWORD,
    VPS_USER,
)
from core.ssh_client import VPSClient


def main() -> None:
    """Check scanner logs and data files."""
    with VPSClient(VPS_HOST, VPS_USER, VPS_PASSWORD) as vps:
        print("=== SCANNER LOG ===")
        result = vps.run(f"tail -15 {SCANNER_LOG_FILE} 2>/dev/null")
        print(result.output)

        print("\n=== SCAN RESULTS ===")
        result = vps.run(f"cat {SCAN_RESULTS_FILE} 2>/dev/null | head -80")
        print(result.output)

        print("\n=== SEEN HEADLINES ===")
        result = vps.run(f"cat {SEEN_HEADLINES_FILE} 2>/dev/null | head -5")
        print(result.output)


if __name__ == "__main__":
    main()
