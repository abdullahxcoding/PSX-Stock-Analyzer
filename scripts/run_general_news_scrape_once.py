"""Manual one-shot invocation of the general news sync, for testing.

Usage: python scripts/run_general_news_scrape_once.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.logging_conf import setup_logging  # noqa: E402
from app.scheduler.jobs import sync_general_news  # noqa: E402

if __name__ == "__main__":
    setup_logging()
    sync_general_news()
