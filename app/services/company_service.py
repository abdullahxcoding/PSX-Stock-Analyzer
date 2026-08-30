import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Company, ShariahComplianceStatus

logger = logging.getLogger(__name__)


def upsert_companies(session: Session, rows: list[dict], source: str) -> int:
    """Upsert a fresh KMI-30 constituent list by ticker.

    Any previously-active KMI-30 constituent whose ticker is absent from this
    run is soft-removed (is_active=False) rather than deleted, since index
    reconstitution just means a company left the index, not that its history
    should disappear.

    Returns the number of rows touched (inserted or updated).
    """
    now = datetime.utcnow()
    seen_tickers = {row["ticker"].strip().upper() for row in rows}
    touched = 0

    existing = {
        c.ticker: c
        for c in session.scalars(select(Company).where(Company.ticker.in_(seen_tickers)))
    }

    for row in rows:
        ticker = row["ticker"].strip().upper()
        name = row["name"].strip()
        sector = row.get("sector")

        company = existing.get(ticker)
        if company is None:
            company = Company(
                ticker=ticker,
                name=name,
                sector=sector,
                is_kmi30_constituent=True,
                shariah_compliance_status=ShariahComplianceStatus.COMPLIANT,
                source=source,
                last_synced_at=now,
                is_active=True,
            )
            session.add(company)
        else:
            company.name = name
            company.sector = sector
            company.is_kmi30_constituent = True
            company.is_active = True
            company.source = source
            company.last_synced_at = now
        touched += 1

    # Soft-remove KMI-30 constituents that dropped out of this run.
    stale = session.scalars(
        select(Company).where(
            Company.is_kmi30_constituent.is_(True),
            Company.is_active.is_(True),
            Company.ticker.notin_(seen_tickers),
        )
    )
    for company in stale:
        company.is_active = False
        logger.info("Marking %s inactive: no longer in KMI-30 list", company.ticker)
        touched += 1

    session.commit()
    return touched


def get_active_kmi30_tickers(session: Session) -> list[str]:
    rows = session.scalars(
        select(Company.ticker).where(
            Company.is_kmi30_constituent.is_(True),
            Company.is_active.is_(True),
        )
    )
    return list(rows)
