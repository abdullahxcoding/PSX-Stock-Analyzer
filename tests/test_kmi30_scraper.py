from pathlib import Path

import pytest

from app.scrapers.exceptions import ParseError
from app.scrapers.kmi30_constituents import _parse_constituents_table

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_constituents_table():
    html = (FIXTURES / "kmi30_sample.html").read_text(encoding="utf-8")
    rows = _parse_constituents_table(html)

    assert len(rows) == 3
    assert rows[0] == {"ticker": "LUCK", "name": "Lucky Cement Limited", "sector": None}
    assert rows[1]["ticker"] == "ENGRO"
    assert rows[2]["name"] == "Oil & Gas Development Company Limited"


def test_raises_parse_error_on_missing_table():
    with pytest.raises(ParseError):
        _parse_constituents_table("<html><body>no table here</body></html>")


def test_raises_parse_error_on_empty_table():
    html = '<tbody class="tbl__body"></tbody>'
    with pytest.raises(ParseError):
        _parse_constituents_table(html)
