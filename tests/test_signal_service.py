from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.signal_service import (
    _build_entry_target,
    _build_macro_context_sentences,
    _build_risk_caution,
    _score_fundamental_trigger,
    _score_news_trigger,
    _score_technical_trigger,
)


def _comparison(pct_change, period_label="Q1 2026", previous_label="Q4 2025"):
    return {
        "current_period": period_label,
        "previous_period": previous_label,
        "profit_after_tax": {"current": 100, "previous": 90, "pct_change": pct_change},
    }


def _news_item(days_ago, title="Some announcement"):
    return SimpleNamespace(published_at=datetime.utcnow() - timedelta(days=days_ago), title=title)


# --- fundamental trigger ---

def test_fundamental_trigger_fires_on_strong_qoq_growth():
    fired, reason = _score_fundamental_trigger(_comparison(6.0), None)
    assert fired is True
    assert "6.0%" in reason
    assert "QoQ" in reason


def test_fundamental_trigger_fires_on_strong_yoy_when_qoq_weak():
    fired, reason = _score_fundamental_trigger(_comparison(2.0), _comparison(12.0))
    assert fired is True
    assert "YoY" in reason


def test_fundamental_trigger_does_not_fire_on_weak_growth():
    fired, reason = _score_fundamental_trigger(_comparison(3.0), _comparison(1.0))
    assert fired is False
    assert reason is None


def test_fundamental_trigger_does_not_fire_when_no_data():
    fired, reason = _score_fundamental_trigger(None, None)
    assert fired is False
    assert reason is None


# --- technical trigger ---

def test_technical_trigger_fires_on_clean_uptrend():
    fired, reason = _score_technical_trigger({"current_price": 110, "sma_50": 105, "sma_200": 95})
    assert fired is True
    assert "uptrend" in reason


def test_technical_trigger_does_not_fire_when_price_below_sma50():
    fired, reason = _score_technical_trigger({"current_price": 100, "sma_50": 105, "sma_200": 95})
    assert fired is False
    assert reason is None


def test_technical_trigger_does_not_fire_with_insufficient_data():
    fired, reason = _score_technical_trigger({"current_price": 110, "sma_50": 105, "sma_200": None})
    assert fired is False
    assert reason is None


# --- news trigger ---

def test_news_trigger_fires_with_recent_item():
    items = [_news_item(5, title="Recent news")]
    fired, reason = _score_news_trigger(items)
    assert fired is True
    assert "Recent news" in reason
    assert "1 " in reason


def test_news_trigger_does_not_fire_with_only_old_items():
    items = [_news_item(45)]
    fired, reason = _score_news_trigger(items)
    assert fired is False
    assert reason is None


def test_news_trigger_reports_most_recent_of_multiple():
    items = [_news_item(20, title="Older"), _news_item(2, title="Newest")]
    fired, reason = _score_news_trigger(items)
    assert fired is True
    assert "Newest" in reason
    assert "2 " in reason


# --- risk caution ---

def test_risk_caution_present_when_overbought():
    note = _build_risk_caution({"rsi_14": 75})
    assert note is not None
    assert "75" in note


def test_risk_caution_absent_when_rsi_normal():
    assert _build_risk_caution({"rsi_14": 50}) is None


def test_risk_caution_absent_when_rsi_missing():
    assert _build_risk_caution({"rsi_14": None}) is None


# --- macro context ---

def test_macro_context_sentence_for_oil_factor():
    context = {"oil_brent": {"value": 88.1, "unit": "USD", "pct_change_from_previous": 2.1}}
    sentences = _build_macro_context_sentences(context)
    assert len(sentences) == 1
    assert "Brent crude" in sentences[0]
    assert "oil & gas exposure" in sentences[0]
    assert "+2.1%" in sentences[0]


def test_macro_context_sentence_for_universal_factor_with_no_prior_change():
    context = {"sp500": {"value": 7711.76, "unit": "USD", "pct_change_from_previous": None}}
    sentences = _build_macro_context_sentences(context)
    assert len(sentences) == 1
    assert "S&P 500" in sentences[0]
    assert "general global market sentiment" in sentences[0]


def test_macro_context_empty_when_no_relevant_factors():
    assert _build_macro_context_sentences({}) == []


# --- entry/target range ---

def test_entry_target_computed_when_complete():
    result = _build_entry_target({"current_price": 100, "support": 90, "resistance": 115})
    assert result["entry_zone"] == {"low": 90, "high": 100}
    assert result["target_range"] == {"low": 100, "high": 115}
    assert "not a prediction" in result["risk_note"]


def test_entry_target_none_when_incomplete():
    assert _build_entry_target({"current_price": 100, "support": None, "resistance": 115}) is None
    assert _build_entry_target({"current_price": None, "support": 90, "resistance": 115}) is None
