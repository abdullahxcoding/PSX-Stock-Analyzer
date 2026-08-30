import logging

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.db.models import NewsItem

logger = logging.getLogger(__name__)


def upsert_news_items(session: Session, rows: list[dict], ticker_to_company_id: dict[str, int]) -> int:
    """Bulk upsert news items, keyed on (ticker, source_type, url).

    Same MySQL ON DUPLICATE KEY UPDATE pattern as price_service/
    fundamentals_service, including the fetched_at fix (server-generated,
    not in the INSERT list, so bumped via func.now() on update).
    """
    resolved_rows = []
    for row in rows:
        company_id = ticker_to_company_id.get(row["ticker"])
        if company_id is None:
            logger.warning("Skipping news row for unknown ticker %s", row["ticker"])
            continue
        resolved_rows.append({**row, "company_id": company_id})

    if not resolved_rows:
        return 0

    stmt = mysql_insert(NewsItem).values(resolved_rows)
    update_cols = {
        col: stmt.inserted[col] for col in ("category", "title", "published_at", "source")
    }
    update_cols["fetched_at"] = func.now()
    stmt = stmt.on_duplicate_key_update(**update_cols)

    result = session.execute(stmt)
    session.commit()
    return result.rowcount or 0


def get_news_for_ticker(session: Session, ticker: str, limit: int = 50) -> list[NewsItem]:
    return list(
        session.scalars(
            select(NewsItem)
            .where(NewsItem.ticker == ticker)
            .order_by(NewsItem.published_at.desc())
            .limit(limit)
        )
    )
