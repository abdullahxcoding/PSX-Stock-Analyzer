"""Scrapes general business news RSS feeds and tags articles to KMI-30
companies by text matching.

Sources confirmed live on 2026-08-31 (standard RSS 2.0, same shape on both
sites): brecorder.com/feeds/business, brecorder.com/feeds/markets,
dawn.com/feeds/business. These are general Pakistan/world finance feeds, not
PSX-specific — most items won't mention any single KMI-30 company. A low
match rate day-to-day is expected, not a bug: most financial news isn't
about one small-cap Pakistani stock.

Tagging matches (a) the ticker as a standalone uppercase word (e.g. \bOGDC\b)
and (b) the company's official name as a case-insensitive substring. This is
a known-imperfect heuristic: ticker matching is reliable but tickers can be
short/ambiguous; name matching works well when a company's official name is
also its common usage name ("Lucky Cement") but may rarely fire for more
formally-named companies ("Oil & Gas Development Company Limited"). No
synonym/alias list is built here — a reasonable future refinement.

Uses stdlib xml.etree.ElementTree, not a new dependency, since both feeds
are standard RSS 2.0.
"""

import logging
import re
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

from app.scrapers.base import ScraperHttpClient
from app.scrapers.exceptions import ParseError, ScraperError

logger = logging.getLogger(__name__)

FEEDS = [
    ("business_recorder_business", "https://www.brecorder.com/feeds/business"),
    ("business_recorder_markets", "https://www.brecorder.com/feeds/markets"),
    ("dawn_business", "https://www.dawn.com/feeds/business"),
]

_SOURCE_BY_FEED_NAME = {
    "business_recorder_business": "business_recorder",
    "business_recorder_markets": "business_recorder",
    "dawn_business": "dawn",
}


def _parse_rss(xml_text: str) -> list[dict]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise ParseError(f"Malformed RSS XML: {exc}") from exc

    items = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        pub_date_text = (item.findtext("pubDate") or "").strip()

        if not title or not link:
            continue

        published_at = None
        if pub_date_text:
            try:
                published_at = parsedate_to_datetime(pub_date_text).replace(tzinfo=None)
            except (TypeError, ValueError):
                logger.warning("Skipping unparseable pubDate %r", pub_date_text)

        items.append(
            {
                "title": title,
                "link": link,
                "description": description,
                "published_at": published_at,
            }
        )

    return items


def fetch_feed(feed_name: str, url: str, client: ScraperHttpClient | None = None) -> list[dict]:
    """Fetch and parse one RSS feed. Returns [] (logged) on failure rather
    than raising, so one bad feed doesn't fail the whole batch."""
    owns_client = client is None
    client = client or ScraperHttpClient()
    try:
        response = client.get(url, cache_key=f"rss_{feed_name}")
        items = _parse_rss(response.text)
        logger.info("Parsed %d items from %s", len(items), feed_name)
        for item in items:
            item["feed_name"] = feed_name
        return items
    except (ParseError, ScraperError) as exc:
        logger.warning("Failed to fetch/parse feed %s: %s", feed_name, exc)
        return []
    finally:
        if owns_client:
            client.close()


def tag_to_companies(items: list[dict], companies: list[dict]) -> list[dict]:
    """For each article, check each company for a ticker or name match in
    title+description. Emits one row per (article, company) match — an
    article mentioning two companies produces two rows."""
    ticker_patterns = {c["ticker"]: re.compile(rf"\b{re.escape(c['ticker'])}\b") for c in companies}

    rows: list[dict] = []
    for item in items:
        if item.get("published_at") is None:
            continue
        haystack = f"{item['title']} {item['description']}"
        haystack_lower = haystack.lower()

        for company in companies:
            ticker, name = company["ticker"], company["name"]
            matched = bool(ticker_patterns[ticker].search(haystack)) or name.lower() in haystack_lower
            if not matched:
                continue

            rows.append(
                {
                    "ticker": ticker,
                    "source_type": "general_news",
                    "category": item["feed_name"],
                    "title": item["title"],
                    "url": item["link"],
                    "published_at": item["published_at"],
                    "source": _SOURCE_BY_FEED_NAME.get(item["feed_name"], item["feed_name"]),
                }
            )

    return rows


def fetch_and_tag_news(companies: list[dict], client: ScraperHttpClient | None = None) -> list[dict]:
    owns_client = client is None
    client = client or ScraperHttpClient()
    try:
        all_items = []
        for feed_name, url in FEEDS:
            all_items.extend(fetch_feed(feed_name, url, client))

        rows = tag_to_companies(all_items, companies)
        logger.info("Tagged %d news rows from %d feed items across %d companies", len(rows), len(all_items), len(companies))
        return rows
    finally:
        if owns_client:
            client.close()
