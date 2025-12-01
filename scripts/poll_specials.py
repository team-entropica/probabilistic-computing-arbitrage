#!/usr/bin/env python3
"""
Simple loop to poll Pinnacle special markets every 10 minutes until 21:45 today.

It reuses the existing fetch_special_markets.py script, so the CSVs in
src/visualizations/plots/ are refreshed on each loop, building a timeseries
via the wide CSV (fetched_at as the time index).
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, time as dtime
from pathlib import Path

# CONFIGURE THESE
EVENT_ID = "1619456922"
POLL_SECONDS = 600  # 10 minutes
CUTOFF_TIME = dtime(21, 45)  # stop at 21:45 local time


ROOT = Path(__file__).resolve().parents[1]
FETCH_SCRIPT = ROOT / "src" / "apis" / "pinnacle-odds" / "special-markets" / "fetch_special_markets.py"


def main():
    while True:
        now = datetime.now()
        if now.time() > CUTOFF_TIME:
            print("Reached cutoff time, stopping.")
            break

        stamp = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{stamp}] Fetching specials for event {EVENT_ID}...")
        cmd = [sys.executable, str(FETCH_SCRIPT), "--event-id", EVENT_ID, "--preview", "0"]
        try:
            subprocess.run(cmd, check=False, cwd=str(ROOT))
        except KeyboardInterrupt:
            print("Interrupted, exiting.")
            break

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
