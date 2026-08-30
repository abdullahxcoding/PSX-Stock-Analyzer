"""Scrapes company fundamentals (Sales, Profit after Taxation, EPS, and
annual ratios) from PSX's own company pages.

Source confirmed live on 2026-08-31: https://dps.psx.com.pk/company/{ticker}
has a server-rendered "Financials" section (`#financials`) with Annual and
Quarterly tabs (each a table: row labels Sales / Profit after Taxation / EPS,
columns are period labels — 4 fiscal years for Annual, e.g. "2026", "2025";
4 fiscal quarters for Quarterly, e.g. "Q3 2026", "Q2 2026" — most recent
first, not always calendar-aligned since PSX companies have varying fiscal
year-ends) and a "Ratios" section (`#ratios`, annual-only: Gross Profit
Margin %, Net Profit Margin %, EPS Growth %, PEG). Figures are in thousands
except EPS, per an on-page note. Data is attributed to Capital Stake, a
licensed financial data aggregator PSX embeds — fine for this project's
personal/local/non-redistributed use, same posture as the price data.

Unlike the price scraper, there is no batched multi-company endpoint here —
this is one request per ticker. That's fine at a daily cadence.
"""

import logging
import re

from bs4 import BeautifulSoup, Tag

from app.scrapers.base import ScraperHttpClient
from app.scrapers.exceptions import ParseError, ScraperError
from app.scrapers.parsing_utils import parse_float

logger = logging.getLogger(__name__)

COMPANY_URL_TEMPLATE = "https://dps.psx.com.pk/company/{ticker}"
SOURCE_NAME = "psx_data_portal_capitalstake"

_QUARTER_LABEL_RE = re.compile(r"^Q([1-4])\s+(\d{4})$")

_FINANCIALS_ROW_KEYS = {
    "Sales": "sales",
    "Profit after Taxation": "profit_after_tax",
    "EPS": "eps",
}
_RATIOS_ROW_KEYS = {
    "Gross Profit Margin (%)": "gross_profit_margin_pct",
    "Net Profit Margin (%)": "net_profit_margin_pct",
    "EPS Growth (%)": "eps_growth_pct",
    "PEG": "peg",
}


def _parse_period_table(table: Tag, row_keys: dict[str, str]) -> tuple[list[str], list[dict]]:
    """Parse a PSX financials/ratios table into (period_labels, [{row_key: value}, ...]).

    Each dict in the returned list corresponds to one period column, aligned
    positionally with `period_labels`.
    """
    header_cells = table.find("tr").find_all("th")
    period_labels = [th.get_text(strip=True) for th in header_cells[1:]]

    # Every period dict always carries all of row_keys' values (defaulting to
    # None) so a metric row missing for one ticker/period can't produce rows
    # with inconsistent keys — SQLAlchemy's bulk multi-row insert requires
    # every row in a batch to share the same key set.
    periods: list[dict] = [{key: None for key in row_keys.values()} for _ in period_labels]
    body = table.find("tbody")
    if body is None:
        raise ParseError("Period table has no tbody")

    for tr in body.find_all("tr"):
        cells = tr.find_all("td")
        if not cells:
            continue
        label = cells[0].get_text(strip=True)
        key = row_keys.get(label)
        if key is None:
            continue
        for i, td in enumerate(cells[1:]):
            if i >= len(periods):
                break
            periods[i][key] = parse_float(td.get_text())

    return period_labels, periods


def _parse_annual_label(label: str) -> int | None:
    if label.isdigit():
        return int(label)
    return None


def _parse_quarter_label(label: str) -> tuple[int, int] | None:
    match = _QUARTER_LABEL_RE.match(label)
    if not match:
        return None
    quarter, year = match.groups()
    return int(year), int(quarter)


def _parse_fundamentals_page(html: str, ticker: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    financials_section = soup.find("div", id="financials")
    if financials_section is None:
        raise ParseError(f"No #financials section found for {ticker}")

    annual_panel = financials_section.find("div", class_="tabs__panel", attrs={"data-name": "Annual"})
    quarterly_panel = financials_section.find("div", class_="tabs__panel", attrs={"data-name": "Quarterly"})
    if annual_panel is None or quarterly_panel is None:
        raise ParseError(f"Missing Annual/Quarterly panel in #financials for {ticker}")

    annual_table = annual_panel.find("table")
    quarterly_table = quarterly_panel.find("table")
    if annual_table is None or quarterly_table is None:
        raise ParseError(f"Missing financials table in Annual/Quarterly panel for {ticker}")

    annual_labels, annual_periods = _parse_period_table(annual_table, _FINANCIALS_ROW_KEYS)
    quarterly_labels, quarterly_periods = _parse_period_table(quarterly_table, _FINANCIALS_ROW_KEYS)

    ratios_by_year: dict[int, dict] = {}
    ratios_section = soup.find("div", id="ratios")
    if ratios_section is not None:
        ratios_table = ratios_section.find("table")
        if ratios_table is not None:
            ratio_labels, ratio_periods = _parse_period_table(ratios_table, _RATIOS_ROW_KEYS)
            for label, values in zip(ratio_labels, ratio_periods):
                year = _parse_annual_label(label)
                if year is not None:
                    ratios_by_year[year] = values
        else:
            logger.warning("Ratios section present but no table found for %s", ticker)
    else:
        logger.warning("No #ratios section found for %s — annual rows will have no ratio data", ticker)

    rows: list[dict] = []

    # Every row must carry the same set of keys (ratio columns included, as
    # None where not applicable) — SQLAlchemy's multi-row bulk insert compiles
    # one INSERT statement from the first row's keys, so quarterly rows
    # silently omitting ratio columns (which only exist for annual periods)
    # breaks the batch insert once annual and quarterly rows are combined.
    all_ratio_keys = set(_RATIOS_ROW_KEYS.values())

    for label, values in zip(annual_labels, annual_periods):
        year = _parse_annual_label(label)
        if year is None:
            logger.warning("Skipping unparseable annual period label %r for %s", label, ticker)
            continue
        row = {
            "ticker": ticker,
            "period_type": "annual",
            "fiscal_year": year,
            "fiscal_quarter": 0,  # sentinel for "annual" — see models.Fundamentals.fiscal_quarter
            "source": SOURCE_NAME,
            **{key: None for key in all_ratio_keys},
            **values,
            **ratios_by_year.get(year, {}),
        }
        rows.append(row)

    for label, values in zip(quarterly_labels, quarterly_periods):
        parsed = _parse_quarter_label(label)
        if parsed is None:
            logger.warning("Skipping unparseable quarterly period label %r for %s", label, ticker)
            continue
        year, quarter = parsed
        rows.append(
            {
                "ticker": ticker,
                "period_type": "quarterly",
                "fiscal_year": year,
                "fiscal_quarter": quarter,
                "source": SOURCE_NAME,
                **{key: None for key in all_ratio_keys},
                **values,
            }
        )

    if not rows:
        raise ParseError(f"No fundamentals periods parsed for {ticker} — site structure may have changed")

    return rows


def fetch_fundamentals(ticker: str, client: ScraperHttpClient | None = None) -> list[dict]:
    """Fetch and parse annual + quarterly fundamentals for one ticker.
    Returns [] (logged) rather than raising, so one bad ticker doesn't fail a batch run."""
    owns_client = client is None
    client = client or ScraperHttpClient()
    url = COMPANY_URL_TEMPLATE.format(ticker=ticker)
    try:
        response = client.get(url, cache_key=f"fundamentals_{ticker}")
        rows = _parse_fundamentals_page(response.text, ticker)
        logger.info("Parsed %d fundamentals periods for %s", len(rows), ticker)
        return rows
    except (ParseError, ScraperError) as exc:
        logger.warning("Failed to fetch/parse fundamentals for %s: %s", ticker, exc)
        return []
    finally:
        if owns_client:
            client.close()


def fetch_fundamentals_for_tickers(
    tickers: list[str], client: ScraperHttpClient | None = None
) -> list[dict]:
    """Fetch fundamentals for each ticker in turn (one request per ticker —
    no batched endpoint exists for this data). Skips (logs+continues) any
    ticker that fails rather than aborting the whole run."""
    owns_client = client is None
    client = client or ScraperHttpClient()
    rows: list[dict] = []
    try:
        for ticker in tickers:
            rows.extend(fetch_fundamentals(ticker, client))
        logger.info("Fetched fundamentals rows for %d tickers (%d rows total)", len(tickers), len(rows))
        return rows
    finally:
        if owns_client:
            client.close()
