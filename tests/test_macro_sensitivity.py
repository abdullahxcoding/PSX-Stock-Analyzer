from app.services.macro_sensitivity import get_relevant_factor_types


def test_oil_company_gets_oil_factors_plus_universal():
    factors = get_relevant_factor_types("OGDC")
    assert "oil_wti" in factors
    assert "oil_brent" in factors
    assert "cpi_inflation" in factors
    assert "sp500" in factors


def test_cement_company_gets_usd_pkr_not_oil():
    factors = get_relevant_factor_types("LUCK")
    assert "usd_pkr" in factors
    assert "oil_wti" not in factors


def test_unmapped_ticker_still_gets_universal_factors():
    factors = get_relevant_factor_types("NOTATICKER")
    assert factors == ["cpi_inflation", "sp500"]


def test_bank_gets_policy_rate():
    factors = get_relevant_factor_types("MEBL")
    assert "sbp_policy_rate" in factors
