from pathlib import Path

from app.scrapers.macro_tradingeconomics import _parse_calendar_table

FIXTURES = Path(__file__).parent / "fixtures"


def _rows():
    html = (FIXTURES / "tradingeconomics_calendar_sample.html").read_text(encoding="utf-8")
    return _parse_calendar_table(html, "Interest Rate", "sbp_policy_rate")


def test_parses_only_rows_with_actual_values():
    rows = _rows()
    # Fixture has 3 rows with a real "actual" value and 3 future rows with a
    # blank actual — only the 3 real ones should come through.
    assert len(rows) == 3


def test_row_shape_and_values():
    rows = _rows()
    dates = {r["observed_at"].strftime("%Y-%m-%d") for r in rows}
    assert dates == {"2026-04-27", "2026-06-15", "2026-07-27"}

    latest = max(rows, key=lambda r: r["observed_at"])
    assert latest["value"] == 11.5
    assert latest["unit"] == "%"
    assert latest["factor_type"] == "sbp_policy_rate"
    assert latest["source"] == "trading_economics"


def test_future_rows_with_blank_actual_are_skipped():
    rows = _rows()
    observed_dates = {r["observed_at"].strftime("%Y-%m-%d") for r in rows}
    # These are future scheduled announcements in the fixture — no real
    # "actual" value yet, must not be fabricated.
    assert "2026-09-14" not in observed_dates
    assert "2026-10-26" not in observed_dates
    assert "2026-12-14" not in observed_dates
