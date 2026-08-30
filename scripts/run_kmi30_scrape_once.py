"""Manual one-shot invocation of the KMI-30 constituent sync, for testing.

Usage: python scripts/run_kmi30_scrape_once.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.logging_conf import setup_logging  # noqa: E402
from app.scheduler.jobs import sync_kmi30_constituents  # noqa: E402

if __name__ == "__main__":
    setup_logging()
    sync_kmi30_constituents()
