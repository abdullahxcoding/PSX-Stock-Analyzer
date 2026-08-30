from app.scrapers.parsing_utils import parse_float, parse_int


def test_parse_float_basic():
    assert parse_float("136,527,017") == 136527017.0
    assert parse_float("31.83") == 31.83


def test_parse_float_dash_is_none():
    assert parse_float("-") is None
    assert parse_float("") is None


def test_parse_float_parenthesized_negative():
    assert parse_float("(56.08)") == -56.08
    assert parse_float("(1,234.5)") == -1234.5


def test_parse_int_basic():
    assert parse_int("1,014,707") == 1014707


def test_parse_int_parenthesized_negative():
    assert parse_int("(500)") == -500
