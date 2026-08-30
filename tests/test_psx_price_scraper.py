from pathlib import Path

import pytest

from app.scrapers.exceptions import ParseError
from app.scrapers.parsing_utils import parse_float, parse_int
from app.scrapers.psx_prices import _parse_market_watch_table

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_market_watch_table():
    html = (FIXTURES / "market_watch_sample.html").read_text(encoding="utf-8")
    snapshot = _parse_market_watch_table(html)

    assert set(snapshot) == {"LUCK", "ENGRO", "HALTED"}
    assert snapshot["LUCK"] == {"open": 440.9, "high": 444.0, "low": 438.5, "close": 442.05, "volume": 984191}
    assert snapshot["ENGRO"]["close"] == 301.5
    assert snapshot["ENGRO"]["volume"] == 200000


def test_handles_dashes_for_halted_symbols():
    html = (FIXTURES / "market_watch_sample.html").read_text(encoding="utf-8")
    snapshot = _parse_market_watch_table(html)

    assert snapshot["HALTED"]["open"] is None
    assert snapshot["HALTED"]["close"] is None
    assert snapshot["HALTED"]["volume"] == 0


def test_raises_parse_error_on_missing_table():
    with pytest.raises(ParseError):
        _parse_market_watch_table("<html><body>no table here</body></html>")


def test_raises_parse_error_on_empty_table():
    html = '<tbody class="tbl__body"></tbody>'
    with pytest.raises(ParseError):
        _parse_market_watch_table(html)


def test_parse_float_handles_commas_and_dashes():
    assert parse_float("1,234.56") == 1234.56
    assert parse_float("-") is None
    assert parse_float("") is None


def test_parse_int_handles_commas_and_dashes():
    assert parse_int("984,191") == 984191
    assert parse_int("-") is None
