"""Scrapes PSX price data (EOD closes and intraday quotes) from a single,
whole-market snapshot rather than N per-ticker requests.

Source confirmed live on 2026-08-31: https://dps.psx.com.pk/market-watch is a
static, server-rendered HTML table listing every PSX-listed symbol's current
session data (SYMBOL, SECTOR code, LISTED IN indices, LDCP, OPEN, HIGH, LOW,
CURRENT (close), CHANGE, CHANGE (%), VOLUME) in ONE response — this is the
"single market-wide endpoint" the plan asked to check for before falling back
to per-ticker requests, and it exists, so both EOD and intraday scraping use
it (filtered down to KMI-30 tickers) rather than hitting
dps.psx.com.pk/timeseries/{eod,int}/{ticker} 30 times per poll.

(Those per-ticker `/timeseries/...` endpoints were also confirmed live and
do work — e.g. https://dps.psx.com.pk/timeseries/eod/LUCK returns
`{"data": [[unix_ts, close, volume, prevClose], ...]}` sorted newest-first —
so they remain a reasonable fallback if market-watch scraping ever breaks,
but aren't used by default given the batching win.)

EOD vs. intraday is just *when* this is scraped (after-close vs. during
market hours), not a different source — `interval_type` on the stored row
is what distinguishes them.
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from app.scrapers.base import ScraperHttpClient
from app.scrapers.exceptions import ParseError
from app.scrapers.parsing_utils import parse_float, parse_int

logger = logging.getLogger(__name__)

MARKET_WATCH_URL = "https://dps.psx.com.pk/market-watch"
SOURCE_NAME = "psx_data_portal"

# Column order confirmed against the live table's <thead>/<tr> markup.
_COLUMN_ORDER = [
    "symbol", "sector", "listed_in", "ldcp", "open", "high", "low", "close",
    "change", "change_pct", "volume",
]


def _parse_market_watch_table(html: str) -> dict[str, dict]:
    """Parse the whole-market snapshot table into {ticker: {open, high, low, close, volume}}."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("tbody", class_="tbl__body")
    if body is None:
        raise ParseError("No market-watch table body (tbody.tbl__body) found")

    snapshot: dict[str, dict] = {}
    for tr in body.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < len(_COLUMN_ORDER):
            continue

        symbol_link = cells[0].find("a", class_="tbl__symbol")
        ticker = symbol_link.get_text(strip=True) if symbol_link else cells[0].get_text(strip=True)
        if not ticker:
            continue

        snapshot[ticker] = {
            "open": parse_float(cells[4].get_text()),
            "high": parse_float(cells[5].get_text()),
            "low": parse_float(cells[6].get_text()),
            "close": parse_float(cells[7].get_text()),
            "volume": parse_int(cells[10].get_text()),
        }

    if not snapshot:
        raise ParseError("Market-watch table found but no rows parsed — site structure may have changed")

    return snapshot


def fetch_market_snapshot(client: ScraperHttpClient | None = None) -> dict[str, dict]:
    owns_client = client is None
    client = client or ScraperHttpClient()
    try:
        response = client.get(MARKET_WATCH_URL, cache_key="market_watch")
        snapshot = _parse_market_watch_table(response.text)
        logger.info("Parsed market-watch snapshot for %d symbols", len(snapshot))
        return snapshot
    finally:
        if owns_client:
            client.close()


def _rows_for_tickers(
    tickers: list[str], interval_type: str, client: ScraperHttpClient | None = None
) -> list[dict]:
    snapshot = fetch_market_snapshot(client)
    now = datetime.now()
    rows: list[dict] = []
    for ticker in tickers:
        quote = snapshot.get(ticker)
        if quote is None or quote["close"] is None:
            logger.warning("No market-watch quote found for %s", ticker)
            continue
        rows.append(
            {
                "ticker": ticker,
                "timestamp": now,
                "interval_type": interval_type,
                "open": quote["open"],
                "high": quote["high"],
                "low": quote["low"],
                "close": quote["close"],
                "volume": quote["volume"],
                "source": SOURCE_NAME,
            }
        )
    logger.info("Built %d/%d %s price rows from market-watch snapshot", len(rows), len(tickers), interval_type)
    return rows


def fetch_eod_prices(tickers: list[str], client: ScraperHttpClient | None = None) -> list[dict]:
    """Fetch EOD OHLCV for the given tickers from the whole-market snapshot.
    Intended to run after market close, when CURRENT == the day's close."""
    return _rows_for_tickers(tickers, "eod", client)


def fetch_intraday_prices(tickers: list[str], client: ScraperHttpClient | None = None) -> list[dict]:
    """Fetch the latest intraday quote for the given tickers from the
    whole-market snapshot. Intended to run during market hours."""
    return _rows_for_tickers(tickers, "intraday", client)
