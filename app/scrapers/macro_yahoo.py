"""Fetches oil (WTI, Brent), USD/PKR, and S&P 500 from Yahoo Finance's
unofficial chart API.

Source confirmed live on 2026-08-31: https://query1.finance.yahoo.com/v8/
finance/chart/{symbol} returns JSON with the current quote in
`chart.result[0].meta` (`regularMarketPrice`, `regularMarketTime` — a real
market timestamp, used as `observed_at`, `currency`). No API key needed.
"""

import logging
from datetime import datetime

from app.scrapers.base import ScraperHttpClient
from app.scrapers.exceptions import ScraperError

logger = logging.getLogger(__name__)

CHART_URL_TEMPLATE = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
SOURCE_NAME = "yahoo_finance"

YAHOO_SYMBOLS = {
    "oil_wti": "CL=F",
    "oil_brent": "BZ=F",
    "usd_pkr": "PKR=X",
    "sp500": "%5EGSPC",
}


def _parse_quote(factor_type: str, payload: dict) -> dict | None:
    try:
        meta = payload["chart"]["result"][0]["meta"]
        price = meta["regularMarketPrice"]
        market_time = meta["regularMarketTime"]
        currency = meta.get("currency")
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("Unexpected Yahoo Finance payload shape for %s: %s", factor_type, exc)
        return None

    return {
        "factor_type": factor_type,
        "value": float(price),
        "unit": currency,
        "observed_at": datetime.fromtimestamp(market_time),
        "source": SOURCE_NAME,
    }


def fetch_yahoo_quote(factor_type: str, symbol: str, client: ScraperHttpClient | None = None) -> dict | None:
    """Fetch one quote. Returns None (logged) rather than raising, so one
    bad symbol doesn't fail the batch."""
    owns_client = client is None
    client = client or ScraperHttpClient()
    url = CHART_URL_TEMPLATE.format(symbol=symbol)
    try:
        response = client.get(url, cache_key=f"yahoo_{factor_type}")
        row = _parse_quote(factor_type, response.json())
        if row:
            logger.info("Fetched %s = %s %s", factor_type, row["value"], row["unit"])
        return row
    except (ScraperError, ValueError) as exc:
        logger.warning("Failed to fetch/parse Yahoo quote for %s (%s): %s", factor_type, symbol, exc)
        return None
    finally:
        if owns_client:
            client.close()


def fetch_all_yahoo_quotes(client: ScraperHttpClient | None = None) -> list[dict]:
    owns_client = client is None
    client = client or ScraperHttpClient()
    rows = []
    try:
        for factor_type, symbol in YAHOO_SYMBOLS.items():
            row = fetch_yahoo_quote(factor_type, symbol, client)
            if row:
                rows.append(row)
        return rows
    finally:
        if owns_client:
            client.close()
