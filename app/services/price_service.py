import logging

from sqlalchemy import func
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.db.models import PriceOHLCV

logger = logging.getLogger(__name__)


def upsert_prices(session: Session, rows: list[dict]) -> int:
    """Bulk upsert OHLCV rows, keyed on (ticker, timestamp, interval_type).

    Uses MySQL's INSERT ... ON DUPLICATE KEY UPDATE so re-polling within the
    same bar (e.g. two intraday polls landing on the same timestamp) updates
    the row instead of erroring on the unique constraint.
    """
    if not rows:
        return 0

    stmt = mysql_insert(PriceOHLCV).values(rows)
    update_cols = {
        col: stmt.inserted[col] for col in ("open", "high", "low", "close", "volume", "source")
    }
    # fetched_at isn't in the INSERT column list (it's server-generated on
    # insert), so it can't be referenced via stmt.inserted — bump it to now()
    # explicitly on update instead.
    update_cols["fetched_at"] = func.now()
    stmt = stmt.on_duplicate_key_update(**update_cols)

    result = session.execute(stmt)
    session.commit()
    return result.rowcount or 0
