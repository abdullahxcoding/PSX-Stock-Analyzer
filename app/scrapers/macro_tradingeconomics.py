"""Fetches SBP policy rate and CPI inflation from TradingEconomics.

Source confirmed live on 2026-08-31: sbp.org.pk itself is behind an active
Cloudflare JS challenge (hard 403 to a plain scripted request, not a simple
header fix) — not worth a Playwright dependency for this. TradingEconomics'
Pakistan pages carry the same numbers via a real, static-HTML "economic
calendar" table (`<table id="calendar">`, no JS needed): each row has
`data-category="Interest Rate"` or `"Inflation Rate"`, a real announcement
date, and an `id="actual"` cell. Future scheduled announcements appear as
rows with a blank `actual` cell — skipped, not fabricated.

This isn't meant to be deep history (unlike Phase 3's price backfill) — just
current state + whatever recent announcements the calendar carries; the
periodic scrape job accumulates more over time as real announcements land.
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from app.scrapers.base import ScraperHttpClient
from app.scrapers.exceptions import ParseError, ScraperError
from app.scrapers.parsing_utils import parse_float

logger = logging.getLogger(__name__)

POLICY_RATE_URL = "https://tradingeconomics.com/pakistan/interest-rate"
CPI_URL = "https://tradingeconomics.com/pakistan/inflation-cpi"
SOURCE_NAME = "trading_economics"


def _parse_calendar_table(html: str, category: str, factor_type: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="calendar")
    if table is None:
        raise ParseError("No #calendar table found")

    rows = []
    for tr in table.find_all("tr", attrs={"data-category": category}):
        date_cell = tr.find("td")
        actual_cell = tr.find("td", id="actual")
        if date_cell is None or actual_cell is None:
            continue

        value = parse_float(actual_cell.get_text().replace("%", ""))
        if value is None:
            continue  # future scheduled announcement, no actual yet — skip, don't fabricate

        date_text = date_cell.get_text(strip=True)
        try:
            observed_at = datetime.strptime(date_text, "%Y-%m-%d")
        except ValueError:
            logger.warning("Skipping %s row with unparseable date %r", factor_type, date_text)
            continue

        rows.append(
            {
                "factor_type": factor_type,
                "value": value,
                "unit": "%",
                "observed_at": observed_at,
                "source": SOURCE_NAME,
            }
        )

    return rows


def fetch_policy_rate(client: ScraperHttpClient | None = None) -> list[dict]:
    return _fetch_calendar(POLICY_RATE_URL, "Interest Rate", "sbp_policy_rate", client)


def fetch_cpi_inflation(client: ScraperHttpClient | None = None) -> list[dict]:
    return _fetch_calendar(CPI_URL, "Inflation Rate", "cpi_inflation", client)


def _fetch_calendar(
    url: str, category: str, factor_type: str, client: ScraperHttpClient | None = None
) -> list[dict]:
    owns_client = client is None
    client = client or ScraperHttpClient()
    try:
        response = client.get(url, cache_key=f"tradingeconomics_{factor_type}")
        rows = _parse_calendar_table(response.text, category, factor_type)
        logger.info("Parsed %d %s observations", len(rows), factor_type)
        return rows
    except (ParseError, ScraperError) as exc:
        logger.warning("Failed to fetch/parse %s: %s", factor_type, exc)
        return []
    finally:
        if owns_client:
            client.close()
