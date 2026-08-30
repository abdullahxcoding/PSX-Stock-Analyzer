"""Manual one-shot invocation of the fundamentals sync, for testing.

Usage: python scripts/run_fundamentals_scrape_once.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.logging_conf import setup_logging  # noqa: E402
from app.scheduler.jobs import sync_fundamentals  # noqa: E402

if __name__ == "__main__":
    setup_logging()
    sync_fundamentals()
