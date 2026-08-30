"""Manual one-shot invocation of the PSX announcements sync, for testing.

Usage: python scripts/run_psx_announcements_scrape_once.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.logging_conf import setup_logging  # noqa: E402
from app.scheduler.jobs import sync_psx_announcements  # noqa: E402

if __name__ == "__main__":
    setup_logging()
    sync_psx_announcements()
