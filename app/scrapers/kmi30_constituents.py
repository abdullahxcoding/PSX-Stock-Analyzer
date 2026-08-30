"""Scrapes the KMI-30 constituent list from PSX's own Data Portal.

Source confirmed live on 2026-08-31: https://dps.psx.com.pk/indices/KMI30 is
a static, server-rendered HTML table (no JS/AJAX needed) titled "KMI INDEX
Constituents", with columns SYMBOL, NAME, LDCP, CURRENT, CHANGE, CHANGE (%),
IDX WTG (%), IDX POINT, VOLUME, FREEFLOAT (M), MARKET CAP (M). There is no
sector column on this page — `sector` is left None here and can be filled in
by a separate per-company lookup in a later phase.

This replaced an earlier guess at Al Meezan's own site
(almeezangroup.com/kmi-30-index), which turned out to only publish the list
as PDFs, not HTML. PSX's own Data Portal is arguably the more authoritative
source anyway (KMI-30 is co-administered by PSX and Al Meezan).
"""

import logging

from bs4 import BeautifulSoup

from app.scrapers.base import ScraperHttpClient
from app.scrapers.exceptions import ParseError

logger = logging.getLogger(__name__)

KMI30_SOURCE_URL = "https://dps.psx.com.pk/indices/KMI30"
SOURCE_NAME = "psx_data_portal"


def _parse_constituents_table(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("tbody", class_="tbl__body")
    if body is None:
        raise ParseError("No constituents table body (tbody.tbl__body) found on KMI-30 source page")

    rows: list[dict] = []
    for tr in body.find_all("tr"):
        symbol_link = tr.find("a", class_="tbl__symbol")
        cells = tr.find_all("td")
        if symbol_link is None or len(cells) < 2:
            continue

        ticker = symbol_link.get_text(strip=True)
        name = cells[1].get_text(strip=True) or symbol_link.get("data-title", "").strip()
        if not ticker or not name:
            continue
        rows.append({"ticker": ticker, "name": name, "sector": None})

    if not rows:
        raise ParseError("Constituents table found but no rows parsed — site structure may have changed")

    return rows


def fetch_kmi30_constituents(client: ScraperHttpClient | None = None) -> list[dict]:
    """Fetch and parse the current KMI-30 constituent list.

    Returns a list of dicts: {"ticker": str, "name": str, "sector": str | None}
    """
    owns_client = client is None
    client = client or ScraperHttpClient()
    try:
        response = client.get(KMI30_SOURCE_URL, cache_key="kmi30_constituents")
        rows = _parse_constituents_table(response.text)
        logger.info("Parsed %d KMI-30 constituents from %s", len(rows), KMI30_SOURCE_URL)
        return rows
    finally:
        if owns_client:
            client.close()
