"""One-time historical EOD price backfill for all active KMI-30 tickers.

Not scheduled — run manually, once, to seed enough price history for
technical indicators (50/200-day moving averages etc.) to be meaningful.
Safe to re-run: upserts are idempotent.

Usage: python scripts/run_price_history_backfill_once.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.logging_conf import setup_logging  # noqa: E402
from app.scheduler.jobs import backfill_price_history  # noqa: E402

if __name__ == "__main__":
    setup_logging()
    backfill_price_history()
