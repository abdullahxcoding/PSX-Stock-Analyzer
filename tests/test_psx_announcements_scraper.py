from pathlib import Path

import pytest

from app.scrapers.exceptions import ParseError
from app.scrapers.psx_announcements import _parse_announcements_page

FIXTURES = Path(__file__).parent / "fixtures"


def _rows():
    html = (FIXTURES / "company_announcements_sample.html").read_text(encoding="utf-8")
    return _parse_announcements_page(html, "LUCK")


def test_parses_all_three_categories():
    rows = _rows()
    categories = {r["category"] for r in rows}
    assert categories == {"Financial Results", "Board Meetings", "Others"}


def test_financial_results_row_shape():
    rows = _rows()
    fr = [r for r in rows if r["category"] == "Financial Results"]
    assert len(fr) == 5

    first = fr[0]
    assert first["title"] == "Financial Results for the year ended June 30, 2026"
    assert first["url"] == "https://dps.psx.com.pk/download/document/280930.pdf"
    assert first["published_at"].year == 2026
    assert first["published_at"].month == 8
    assert first["published_at"].day == 10
    assert first["ticker"] == "LUCK"
    assert first["source_type"] == "psx_announcement"
    assert first["source"] == "psx_data_portal"


def test_others_row_titles():
    rows = _rows()
    others_titles = {r["title"] for r in rows if r["category"] == "Others"}
    assert "Material Information" in others_titles
    assert "CORPORATE BRIEFING SESSION - LUCKY CEMENT LIMITED" in others_titles


def test_raises_parse_error_when_section_missing():
    with pytest.raises(ParseError):
        _parse_announcements_page("<html><body>nothing here</body></html>", "XXXX")
