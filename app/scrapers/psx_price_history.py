"""One-time historical EOD price backfill.

Source confirmed live on 2026-08-31: https://dps.psx.com.pk/timeseries/eod/{ticker}
returns `{"data": [[unix_ts, close, volume, prevClose], ...]}`, sorted
newest-first — the *full* history, not just the latest point (e.g. 1,234
daily points for LUCK, back to 2021-08-31). This is the same endpoint
Phase 1's psx_prices.py documented as an unused fallback; here it's used for
exactly what it's good at — a one-time deep backfill — while ongoing daily
scraping stays on psx_prices.py's batched market-watch snapshot.

Limitation: this endpoint gives close + volume only, no open/high/low.
Backfilled rows have open/high/low = None; only the ongoing market-watch-based
EOD scrape captures full OHLC, from the day it started running onward.
"""

import logging
from datetime import datetime

from app.scrapers.base import ScraperHttpClient
from app.scrapers.exceptions import ScraperError
from app.scrapers.parsing_utils import parse_float, parse_int

logger = logging.getLogger(__name__)

HISTORY_URL_TEMPLATE = "https://dps.psx.com.pk/timeseries/eod/{ticker}"
SOURCE_NAME = "psx_data_portal_history_backfill"


def _parse_history_response(ticker: str, payload: dict) -> list[dict]:
    data = payload.get("data") or []
    rows = []
    for point in data:
        try:
            timestamp = datetime.fromtimestamp(point[0])
            close = parse_float(str(point[1]))
            volume = parse_int(str(point[2])) if len(point) > 2 else None
        except (IndexError, TypeError, ValueError, OSError) as exc:
            logger.warning("Skipping malformed history point for %s: %r (%s)", ticker, point, exc)
            continue
        if close is None:
            continue
        rows.append(
            {
                "ticker": ticker,
                "timestamp": timestamp,
                "interval_type": "eod",
                "open": None,
                "high": None,
                "low": None,
                "close": close,
                "volume": volume,
                "source": SOURCE_NAME,
            }
        )
    return rows


def fetch_price_history(ticker: str, client: ScraperHttpClient | None = None) -> list[dict]:
    """Fetch full available EOD history for one ticker. Returns [] (logged)
    rather than raising, so one bad ticker doesn't fail a batch backfill."""
    owns_client = client is None
    client = client or ScraperHttpClient()
    url = HISTORY_URL_TEMPLATE.format(ticker=ticker)
    try:
        response = client.get(url, cache_key=f"history_{ticker}")
        rows = _parse_history_response(ticker, response.json())
        logger.info("Parsed %d historical EOD points for %s", len(rows), ticker)
        return rows
    except (ScraperError, ValueError) as exc:
        logger.warning("Failed to fetch/parse price history for %s: %s", ticker, exc)
        return []
    finally:
        if owns_client:
            client.close()


def fetch_price_history_for_tickers(
    tickers: list[str], client: ScraperHttpClient | None = None
) -> list[dict]:
    """Backfill full EOD history for each ticker in turn. Skips (logs+continues)
    any ticker that fails rather than aborting the whole run."""
    owns_client = client is None
    client = client or ScraperHttpClient()
    rows: list[dict] = []
    try:
        for ticker in tickers:
            rows.extend(fetch_price_history(ticker, client))
        logger.info("Backfilled history for %d tickers (%d rows total)", len(tickers), len(rows))
        return rows
    finally:
        if owns_client:
            client.close()
