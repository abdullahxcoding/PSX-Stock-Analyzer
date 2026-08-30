import logging

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.db.models import Fundamentals
from app.services.comparison_utils import pct_change

logger = logging.getLogger(__name__)

_COMPARISON_METRICS = ("sales", "profit_after_tax", "eps")


def upsert_fundamentals(session: Session, rows: list[dict], ticker_to_company_id: dict[str, int]) -> int:
    """Bulk upsert fundamentals rows, keyed on (ticker, period_type, fiscal_year, fiscal_quarter).

    Same MySQL ON DUPLICATE KEY UPDATE pattern as price_service.upsert_prices,
    including the fetched_at fix (it's server-generated, not in the insert
    column list, so it must be bumped via func.now() on update, not
    stmt.inserted.fetched_at).
    """
    resolved_rows = []
    for row in rows:
        company_id = ticker_to_company_id.get(row["ticker"])
        if company_id is None:
            logger.warning("Skipping fundamentals row for unknown ticker %s", row["ticker"])
            continue
        resolved_rows.append({**row, "company_id": company_id})

    if not resolved_rows:
        return 0

    stmt = mysql_insert(Fundamentals).values(resolved_rows)
    update_cols = {
        col: stmt.inserted[col]
        for col in (
            "sales", "profit_after_tax", "eps", "gross_profit_margin_pct",
            "net_profit_margin_pct", "eps_growth_pct", "peg", "source",
        )
    }
    update_cols["fetched_at"] = func.now()
    stmt = stmt.on_duplicate_key_update(**update_cols)

    result = session.execute(stmt)
    session.commit()
    return result.rowcount or 0


def _metric_deltas(current: Fundamentals, previous: Fundamentals) -> dict:
    deltas = {}
    for metric in _COMPARISON_METRICS:
        current_value = getattr(current, metric)
        previous_value = getattr(previous, metric)
        deltas[metric] = {
            "current": current_value,
            "previous": previous_value,
            "pct_change": pct_change(current_value, previous_value),
        }
    return deltas


def get_qoq_comparison(session: Session, ticker: str) -> dict | None:
    """Most recent quarterly period vs. the one immediately before it."""
    rows = session.scalars(
        select(Fundamentals)
        .where(Fundamentals.ticker == ticker, Fundamentals.period_type == "quarterly")
        .order_by(Fundamentals.fiscal_year.desc(), Fundamentals.fiscal_quarter.desc())
        .limit(2)
    ).all()

    if len(rows) < 2:
        return None

    current, previous = rows[0], rows[1]
    return {
        "current_period": f"Q{current.fiscal_quarter} {current.fiscal_year}",
        "previous_period": f"Q{previous.fiscal_quarter} {previous.fiscal_year}",
        **_metric_deltas(current, previous),
    }


def get_yoy_comparison(session: Session, ticker: str) -> dict | None:
    """Most recent quarterly period vs. the same fiscal quarter one year earlier.

    Returns None if that exact prior-year quarter hasn't been captured —
    never fabricates a comparison from a different quarter.
    """
    current = session.scalar(
        select(Fundamentals)
        .where(Fundamentals.ticker == ticker, Fundamentals.period_type == "quarterly")
        .order_by(Fundamentals.fiscal_year.desc(), Fundamentals.fiscal_quarter.desc())
        .limit(1)
    )
    if current is None:
        return None

    previous = session.scalar(
        select(Fundamentals).where(
            Fundamentals.ticker == ticker,
            Fundamentals.period_type == "quarterly",
            Fundamentals.fiscal_year == current.fiscal_year - 1,
            Fundamentals.fiscal_quarter == current.fiscal_quarter,
        )
    )
    if previous is None:
        return None

    return {
        "current_period": f"Q{current.fiscal_quarter} {current.fiscal_year}",
        "previous_period": f"Q{previous.fiscal_quarter} {previous.fiscal_year}",
        **_metric_deltas(current, previous),
    }
