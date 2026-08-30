import logging

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.db.models import MacroFactor
from app.services.comparison_utils import pct_change
from app.services.macro_sensitivity import get_relevant_factor_types

logger = logging.getLogger(__name__)


def upsert_macro_factors(session: Session, rows: list[dict]) -> int:
    """Bulk upsert macro factor observations, keyed on (factor_type, observed_at).

    Same MySQL ON DUPLICATE KEY UPDATE pattern as every other table so far,
    including the fetched_at fix (server-generated, bumped via func.now()).
    """
    if not rows:
        return 0

    stmt = mysql_insert(MacroFactor).values(rows)
    update_cols = {col: stmt.inserted[col] for col in ("value", "unit", "source")}
    update_cols["fetched_at"] = func.now()
    stmt = stmt.on_duplicate_key_update(**update_cols)

    result = session.execute(stmt)
    session.commit()
    return result.rowcount or 0


def _latest_two(session: Session, factor_type: str) -> list[MacroFactor]:
    return list(
        session.scalars(
            select(MacroFactor)
            .where(MacroFactor.factor_type == factor_type)
            .order_by(MacroFactor.observed_at.desc())
            .limit(2)
        )
    )


def get_latest_macro_snapshot(session: Session) -> dict[str, dict]:
    """Latest observation of every factor_type present in the DB, with
    pct_change from the previous observation where available."""
    factor_types = session.scalars(select(MacroFactor.factor_type).distinct()).all()

    snapshot = {}
    for factor_type in factor_types:
        rows = _latest_two(session, factor_type)
        if not rows:
            continue
        current = rows[0]
        previous = rows[1] if len(rows) > 1 else None
        snapshot[factor_type] = {
            "value": current.value,
            "unit": current.unit,
            "observed_at": current.observed_at,
            "pct_change_from_previous": pct_change(
                current.value, previous.value if previous else None
            ),
        }
    return snapshot


def get_relevant_macro_context(session: Session, ticker: str) -> dict:
    relevant_types = set(get_relevant_factor_types(ticker))
    snapshot = get_latest_macro_snapshot(session)
    return {factor_type: data for factor_type, data in snapshot.items() if factor_type in relevant_types}
