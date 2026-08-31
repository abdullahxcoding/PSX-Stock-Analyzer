"""Signal engine: combines fundamentals, technicals, news, and macro context
into a ranked, explainable watchlist.

Deliberately NOT a black box (spec Section 3): every trigger is a plain,
named, textbook rule with a one-sentence explanation, never an opaque model
score. Deliberately conservative (spec Section 2): the system optimizes for
risk-managed outperformance vs. KMI-30, not for maximizing how many "buy"
signals fire.

No new data source, no new table, no new scheduler job — this is a pure
computation over data the other four services already expose, same
on-demand-computation precedent as technical_service.get_technicals.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.services.company_service import get_active_kmi30_tickers
from app.services.fundamentals_service import get_qoq_comparison, get_yoy_comparison
from app.services.macro_service import get_relevant_macro_context
from app.services.news_service import get_news_for_ticker
from app.services.technical_service import get_technicals

FUNDAMENTAL_GROWTH_THRESHOLD_PCT = 5.0
NEWS_RECENCY_DAYS = 30
RSI_OVERBOUGHT = 70

FACTOR_LABELS = {
    "oil_wti": "oil & gas exposure",
    "oil_brent": "oil & gas exposure",
    "usd_pkr": "import/export exposure to PKR movements",
    "sbp_policy_rate": "interest-rate sensitivity as a bank",
    "cpi_inflation": "broad market/consumer demand exposure",
    "sp500": "general global market sentiment",
}

FACTOR_DISPLAY_NAMES = {
    "oil_wti": "WTI crude",
    "oil_brent": "Brent crude",
    "usd_pkr": "USD/PKR",
    "sbp_policy_rate": "SBP policy rate",
    "cpi_inflation": "CPI inflation",
    "sp500": "S&P 500",
}


def _score_fundamental_trigger(qoq: dict | None, yoy: dict | None) -> tuple[bool, str | None]:
    for comparison, label in ((qoq, "QoQ"), (yoy, "YoY")):
        if comparison is None:
            continue
        profit = comparison.get("profit_after_tax", {})
        pct = profit.get("pct_change")
        if pct is not None and pct > FUNDAMENTAL_GROWTH_THRESHOLD_PCT:
            return True, (
                f"Profit after tax up {pct}% {label} "
                f"({comparison['previous_period']} → {comparison['current_period']})"
            )
    return False, None


def _score_technical_trigger(technicals: dict) -> tuple[bool, str | None]:
    price, sma_50, sma_200 = technicals.get("current_price"), technicals.get("sma_50"), technicals.get("sma_200")
    if price is None or sma_50 is None or sma_200 is None:
        return False, None
    if price > sma_50 > sma_200:
        return True, (
            f"Price ({price}) trading above both 50-day ({sma_50}) and "
            f"200-day ({sma_200}) averages — established uptrend"
        )
    return False, None


def _score_news_trigger(news_items: list, now: datetime | None = None) -> tuple[bool, str | None]:
    now = now or datetime.utcnow()
    cutoff = now - timedelta(days=NEWS_RECENCY_DAYS)
    recent = [item for item in news_items if item.published_at >= cutoff]
    if not recent:
        return False, None
    recent.sort(key=lambda item: item.published_at, reverse=True)
    latest = recent[0]
    kind = "announcement(s)/article(s)"
    return True, (
        f"{len(recent)} {kind} in the last {NEWS_RECENCY_DAYS} days, "
        f"most recent: '{latest.title}' ({latest.published_at.strftime('%Y-%m-%d')})"
    )


def _build_risk_caution(technicals: dict) -> str | None:
    rsi = technicals.get("rsi_14")
    if rsi is not None and rsi > RSI_OVERBOUGHT:
        return f"RSI is elevated ({rsi}) — a near-term pullback is more likely than usual"
    return None


def _build_macro_context_sentences(macro_context: dict) -> list[str]:
    sentences = []
    for factor_type, data in macro_context.items():
        name = FACTOR_DISPLAY_NAMES.get(factor_type, factor_type)
        label = FACTOR_LABELS.get(factor_type, "general relevance")
        value, unit = data.get("value"), data.get("unit") or ""
        pct_change = data.get("pct_change_from_previous")
        change_phrase = f" ({pct_change:+.1f}% from last observation)" if pct_change is not None else ""
        sentences.append(f"{name} at {value} {unit}{change_phrase} — relevant given this company's {label}")
    return sentences


def _build_entry_target(technicals: dict) -> dict | None:
    price, support, resistance = (
        technicals.get("current_price"), technicals.get("support"), technicals.get("resistance")
    )
    if price is None or support is None or resistance is None:
        return None
    return {
        "entry_zone": {"low": support, "high": price},
        "target_range": {"low": price, "high": resistance},
        "risk_note": (
            "Based on recent (~90-day) trading range, not a prediction — actual "
            "prices can move outside this range in either direction. Not financial advice."
        ),
    }


def compute_signal(session: Session, ticker: str) -> dict:
    qoq = get_qoq_comparison(session, ticker)
    yoy = get_yoy_comparison(session, ticker)
    technicals = get_technicals(session, ticker)
    news_items = get_news_for_ticker(session, ticker, limit=50)
    macro_context = get_relevant_macro_context(session, ticker)

    fundamental_fired, fundamental_reason = _score_fundamental_trigger(qoq, yoy)
    technical_fired, technical_reason = _score_technical_trigger(technicals)
    news_fired, news_reason = _score_news_trigger(news_items)

    score = int(fundamental_fired) + int(technical_fired) + int(news_fired)
    status = "watch" if score == 3 else "consider" if score == 2 else "none"

    entry_target = _build_entry_target(technicals)

    return {
        "ticker": ticker,
        "current_price": technicals.get("current_price"),
        "score": score,
        "status": status,
        "triggers": {
            "fundamental": fundamental_reason,
            "technical": technical_reason,
            "news": news_reason,
        },
        "risk_caution": _build_risk_caution(technicals),
        "macro_context": _build_macro_context_sentences(macro_context),
        "entry_zone": entry_target["entry_zone"] if entry_target else None,
        "target_range": entry_target["target_range"] if entry_target else None,
        "risk_note": entry_target["risk_note"] if entry_target else None,
    }


def get_watchlist(session: Session) -> list[dict]:
    tickers = get_active_kmi30_tickers(session)
    signals = [compute_signal(session, ticker) for ticker in tickers]
    signals.sort(key=lambda s: s["score"], reverse=True)
    return signals
