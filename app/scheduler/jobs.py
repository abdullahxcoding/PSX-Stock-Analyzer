import logging
from datetime import datetime

from sqlalchemy import select

from app.db.models import Company, ScrapeRun, ScrapeRunStatus
from app.db.session import SessionLocal
from app.scheduler.market_hours import is_market_open
from app.scrapers.exceptions import ScraperError
from app.scrapers.kmi30_constituents import SOURCE_NAME as KMI30_SOURCE, fetch_kmi30_constituents
from app.scrapers.psx_fundamentals import fetch_fundamentals_for_tickers
from app.scrapers.psx_prices import fetch_eod_prices, fetch_intraday_prices
from app.services.company_service import get_active_kmi30_tickers, upsert_companies
from app.services.fundamentals_service import upsert_fundamentals
from app.services.price_service import upsert_prices

logger = logging.getLogger(__name__)


def _record_run(job_name: str, started_at: datetime, status: ScrapeRunStatus,
                 rows_affected: int | None = None, error_message: str | None = None) -> None:
    with SessionLocal() as session:
        session.add(
            ScrapeRun(
                job_name=job_name,
                started_at=started_at,
                finished_at=datetime.utcnow(),
                status=status,
                rows_affected=rows_affected,
                error_message=error_message,
            )
        )
        session.commit()


def sync_kmi30_constituents() -> None:
    job_name = "kmi30_constituents_sync"
    started_at = datetime.utcnow()
    logger.info("Starting job: %s", job_name)
    try:
        rows = fetch_kmi30_constituents()
        with SessionLocal() as session:
            touched = upsert_companies(session, rows, source=KMI30_SOURCE)
        _record_run(job_name, started_at, ScrapeRunStatus.SUCCESS, rows_affected=touched)
        logger.info("Finished job: %s (%d rows touched)", job_name, touched)
    except ScraperError as exc:
        logger.exception("Job failed: %s", job_name)
        _record_run(job_name, started_at, ScrapeRunStatus.FAILED, error_message=str(exc))


def _price_rows_with_company_id(session_tickers: dict[str, int], rows: list[dict]) -> list[dict]:
    resolved = []
    for row in rows:
        company_id = session_tickers.get(row["ticker"])
        if company_id is None:
            logger.warning("Skipping price row for unknown ticker %s", row["ticker"])
            continue
        row = {**row, "company_id": company_id}
        resolved.append(row)
    return resolved


def sync_eod_prices() -> None:
    job_name = "psx_eod_price_sync"
    started_at = datetime.utcnow()
    logger.info("Starting job: %s", job_name)
    try:
        with SessionLocal() as session:
            tickers = get_active_kmi30_tickers(session)
            ticker_to_id = dict(session.execute(select(Company.ticker, Company.id)).all())

        if not tickers:
            logger.warning("No active KMI-30 tickers found; skipping %s", job_name)
            _record_run(job_name, started_at, ScrapeRunStatus.SUCCESS, rows_affected=0)
            return

        raw_rows = fetch_eod_prices(tickers)
        rows = _price_rows_with_company_id(ticker_to_id, raw_rows)

        with SessionLocal() as session:
            affected = upsert_prices(session, rows)

        status = ScrapeRunStatus.SUCCESS if len(rows) == len(tickers) else ScrapeRunStatus.PARTIAL
        _record_run(job_name, started_at, status, rows_affected=affected)
        logger.info("Finished job: %s (%d/%d tickers)", job_name, len(rows), len(tickers))
    except ScraperError as exc:
        logger.exception("Job failed: %s", job_name)
        _record_run(job_name, started_at, ScrapeRunStatus.FAILED, error_message=str(exc))


def sync_fundamentals() -> None:
    job_name = "psx_fundamentals_sync"
    started_at = datetime.utcnow()
    logger.info("Starting job: %s", job_name)
    try:
        with SessionLocal() as session:
            tickers = get_active_kmi30_tickers(session)
            ticker_to_id = dict(session.execute(select(Company.ticker, Company.id)).all())

        if not tickers:
            logger.warning("No active KMI-30 tickers found; skipping %s", job_name)
            _record_run(job_name, started_at, ScrapeRunStatus.SUCCESS, rows_affected=0)
            return

        rows = fetch_fundamentals_for_tickers(tickers)
        tickers_with_data = {row["ticker"] for row in rows}

        with SessionLocal() as session:
            affected = upsert_fundamentals(session, rows, ticker_to_id)

        status = ScrapeRunStatus.SUCCESS if len(tickers_with_data) == len(tickers) else ScrapeRunStatus.PARTIAL
        _record_run(job_name, started_at, status, rows_affected=affected)
        logger.info(
            "Finished job: %s (%d/%d tickers, %d rows)",
            job_name, len(tickers_with_data), len(tickers), affected,
        )
    except ScraperError as exc:
        logger.exception("Job failed: %s", job_name)
        _record_run(job_name, started_at, ScrapeRunStatus.FAILED, error_message=str(exc))


def poll_intraday_prices() -> None:
    job_name = "psx_intraday_poll"
    if not is_market_open():
        logger.debug("%s: market closed, skipping poll", job_name)
        return

    started_at = datetime.utcnow()
    logger.info("Starting job: %s", job_name)
    try:
        with SessionLocal() as session:
            tickers = get_active_kmi30_tickers(session)
            ticker_to_id = dict(session.execute(select(Company.ticker, Company.id)).all())

        if not tickers:
            logger.warning("No active KMI-30 tickers found; skipping %s", job_name)
            _record_run(job_name, started_at, ScrapeRunStatus.SUCCESS, rows_affected=0)
            return

        raw_rows = fetch_intraday_prices(tickers)
        rows = _price_rows_with_company_id(ticker_to_id, raw_rows)

        with SessionLocal() as session:
            affected = upsert_prices(session, rows)

        status = ScrapeRunStatus.SUCCESS if len(rows) == len(tickers) else ScrapeRunStatus.PARTIAL
        _record_run(job_name, started_at, status, rows_affected=affected)
        logger.info("Finished job: %s (%d/%d tickers)", job_name, len(rows), len(tickers))
    except ScraperError as exc:
        logger.exception("Job failed: %s", job_name)
        _record_run(job_name, started_at, ScrapeRunStatus.FAILED, error_message=str(exc))
