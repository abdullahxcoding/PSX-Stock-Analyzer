import json
from datetime import datetime
from pathlib import Path

from app.scrapers.macro_yahoo import _parse_quote

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_yahoo_quote():
    payload = json.loads((FIXTURES / "yahoo_quote_sample.json").read_text(encoding="utf-8"))
    row = _parse_quote("oil_wti", payload)

    assert row["factor_type"] == "oil_wti"
    assert row["value"] == 83.4
    assert row["unit"] == "USD"
    assert row["observed_at"] == datetime.fromtimestamp(1787950798)
    assert row["source"] == "yahoo_finance"


def test_returns_none_on_malformed_payload():
    assert _parse_quote("oil_wti", {"chart": {"result": []}}) is None
    assert _parse_quote("oil_wti", {}) is None
