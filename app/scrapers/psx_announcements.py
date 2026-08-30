"""Scrapes official PSX company announcements (Financial Results, Board
Meetings, Others) from the same company page Phase 2's fundamentals scraper
visits.

Source confirmed live on 2026-08-31: https://dps.psx.com.pk/company/{ticker}
has a server-rendered `#announcements` section with three tabs, each a real
HTML table of {Date, Title, Document} rows (Document links to a PDF). This
is precise, official, and already tied to a specific company by
construction — no fuzzy text matching needed, unlike general news.

Kept as an independent scraper/request from psx_fundamentals.py (even
though it's the same URL) so a failure in one doesn't affect the other.
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from app.scrapers.base import ScraperHttpClient
from app.scrapers.exceptions import ParseError, ScraperError

logger = logging.getLogger(__name__)

COMPANY_URL_TEMPLATE = "https://dps.psx.com.pk/company/{ticker}"
SOURCE_NAME = "psx_data_portal"

_TAB_NAMES = ("Financial Results", "Board Meetings", "Others")


def _parse_announcements_table(table: Tag) -> list[dict]:
    body = table.find("tbody")
    if body is None:
        return []

    rows = []
    for tr in body.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 3:
            continue

        date_text = cells[0].get_text(strip=True)
        title = cells[1].get_text(strip=True)
        pdf_link = cells[2].find("a", href=lambda h: h and h.endswith(".pdf"))

        try:
            published_at = datetime.strptime(date_text, "%b %d, %Y")
        except ValueError:
            logger.warning("Skipping announcement with unparseable date %r", date_text)
            continue

        if not title or pdf_link is None:
            continue

        rows.append(
            {
                "title": title,
                "url": "https://dps.psx.com.pk" + pdf_link["href"],
                "published_at": published_at,
            }
        )

    return rows


def _parse_announcements_page(html: str, ticker: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    section = soup.find("div", id="announcements")
    if section is None:
        raise ParseError(f"No #announcements section found for {ticker}")

    rows: list[dict] = []
    for tab_name in _TAB_NAMES:
        panel = section.find("div", class_="tabs__panel", attrs={"data-name": tab_name})
        if panel is None:
            logger.warning("No %r announcements panel found for %s", tab_name, ticker)
            continue

        table = panel.find("table")
        if table is None:
            continue

        for row in _parse_announcements_table(table):
            rows.append(
                {
                    "ticker": ticker,
                    "source_type": "psx_announcement",
                    "category": tab_name,
                    "title": row["title"],
                    "url": row["url"],
                    "published_at": row["published_at"],
                    "source": SOURCE_NAME,
                }
            )

    if not rows:
        raise ParseError(f"No announcements parsed for {ticker} — site structure may have changed")

    return rows


def fetch_announcements(ticker: str, client: ScraperHttpClient | None = None) -> list[dict]:
    """Fetch and parse announcements for one ticker.
    Returns [] (logged) rather than raising, so one bad ticker doesn't fail a batch run."""
    owns_client = client is None
    client = client or ScraperHttpClient()
    url = COMPANY_URL_TEMPLATE.format(ticker=ticker)
    try:
        response = client.get(url, cache_key=f"announcements_{ticker}")
        rows = _parse_announcements_page(response.text, ticker)
        logger.info("Parsed %d announcements for %s", len(rows), ticker)
        return rows
    except (ParseError, ScraperError) as exc:
        logger.warning("Failed to fetch/parse announcements for %s: %s", ticker, exc)
        return []
    finally:
        if owns_client:
            client.close()


def fetch_announcements_for_tickers(
    tickers: list[str], client: ScraperHttpClient | None = None
) -> list[dict]:
    """Fetch announcements for each ticker in turn. Skips (logs+continues)
    any ticker that fails rather than aborting the whole run."""
    owns_client = client is None
    client = client or ScraperHttpClient()
    rows: list[dict] = []
    try:
        for ticker in tickers:
            rows.extend(fetch_announcements(ticker, client))
        logger.info("Fetched announcements for %d tickers (%d rows total)", len(tickers), len(rows))
        return rows
    finally:
        if owns_client:
            client.close()
