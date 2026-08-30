"""Manual one-shot invocation of the price scrapers, for testing.

Usage:
    python scripts/run_price_scrape_once.py --mode eod
    python scripts/run_price_scrape_once.py --mode intraday
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.logging_conf import setup_logging  # noqa: E402
from app.scheduler.jobs import poll_intraday_prices, sync_eod_prices  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["eod", "intraday"], required=True)
    args = parser.parse_args()

    setup_logging()
    if args.mode == "eod":
        sync_eod_prices()
    else:
        poll_intraday_prices()


if __name__ == "__main__":
    main()
