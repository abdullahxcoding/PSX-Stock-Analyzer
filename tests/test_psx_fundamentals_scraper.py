from pathlib import Path

import pytest

from app.scrapers.exceptions import ParseError
from app.scrapers.psx_fundamentals import _parse_fundamentals_page, _parse_quarter_label

FIXTURES = Path(__file__).parent / "fixtures"


def _rows():
    html = (FIXTURES / "company_financials_sample.html").read_text(encoding="utf-8")
    return _parse_fundamentals_page(html, "LUCK")


def test_parses_annual_and_quarterly_rows():
    rows = _rows()
    annual = [r for r in rows if r["period_type"] == "annual"]
    quarterly = [r for r in rows if r["period_type"] == "quarterly"]

    assert len(annual) == 4
    assert len(quarterly) == 4


def test_annual_row_has_sales_profit_eps_and_ratios():
    rows = _rows()
    row_2026 = next(r for r in rows if r["period_type"] == "annual" and r["fiscal_year"] == 2026)

    assert row_2026["sales"] == 136527017.0
    assert row_2026["profit_after_tax"] == 46629367.0
    assert row_2026["eps"] == 31.83
    assert row_2026["gross_profit_margin_pct"] == 37.48
    assert row_2026["net_profit_margin_pct"] == 34.15
    assert row_2026["fiscal_quarter"] == 0


def test_annual_row_handles_parenthesized_negative_ratio():
    rows = _rows()
    row_2024 = next(r for r in rows if r["period_type"] == "annual" and r["fiscal_year"] == 2024)

    assert row_2024["eps_growth_pct"] == -56.08
    assert row_2024["peg"] == -0.85


def test_quarterly_row_parses_period_label_correctly():
    rows = _rows()
    q3_2026 = next(
        r for r in rows if r["period_type"] == "quarterly" and r["fiscal_year"] == 2026 and r["fiscal_quarter"] == 3
    )

    assert q3_2026["sales"] == 33247128.0
    assert q3_2026["profit_after_tax"] == 13489662.0
    assert q3_2026["eps"] == 9.21
    # Quarterly rows don't carry ratio data (only published annually).
    assert "gross_profit_margin_pct" not in q3_2026 or q3_2026.get("gross_profit_margin_pct") is None


def test_quarter_label_parsing():
    assert _parse_quarter_label("Q3 2026") == (2026, 3)
    assert _parse_quarter_label("Q1 2023") == (2023, 1)
    assert _parse_quarter_label("FY2026") is None
    assert _parse_quarter_label("2026") is None


def test_raises_parse_error_when_financials_section_missing():
    with pytest.raises(ParseError):
        _parse_fundamentals_page("<html><body>no financials here</body></html>", "XXXX")
