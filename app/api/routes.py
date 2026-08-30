from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Company, Fundamentals, PriceOHLCV
from app.db.session import get_session
from app.services.fundamentals_service import get_qoq_comparison, get_yoy_comparison
from app.services.macro_service import get_latest_macro_snapshot, get_relevant_macro_context
from app.services.news_service import get_news_for_ticker
from app.services.technical_service import get_technicals

router = APIRouter()


def _get_company_or_404(ticker: str, session: Session) -> Company:
    ticker = ticker.strip().upper()
    company = session.scalar(select(Company).where(Company.ticker == ticker))
    if company is None:
        raise HTTPException(status_code=404, detail=f"Unknown ticker: {ticker}")
    return company


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@router.get("/api/companies")
def list_companies(session: Session = Depends(get_session)) -> list[dict]:
    companies = session.scalars(
        select(Company).where(Company.is_active.is_(True)).order_by(Company.ticker)
    )
    return [
        {
            "ticker": c.ticker,
            "name": c.name,
            "sector": c.sector,
            "shariah_compliance_status": c.shariah_compliance_status,
            "last_synced_at": c.last_synced_at,
        }
        for c in companies
    ]


@router.get("/api/prices/{ticker}")
def get_prices(ticker: str, limit: int = 50, session: Session = Depends(get_session)) -> list[dict]:
    company = _get_company_or_404(ticker, session)

    prices = session.scalars(
        select(PriceOHLCV)
        .where(PriceOHLCV.ticker == company.ticker)
        .order_by(PriceOHLCV.timestamp.desc())
        .limit(limit)
    )
    return [
        {
            "timestamp": p.timestamp,
            "interval_type": p.interval_type,
            "open": p.open,
            "high": p.high,
            "low": p.low,
            "close": p.close,
            "volume": p.volume,
            "source": p.source,
        }
        for p in prices
    ]


@router.get("/api/fundamentals/{ticker}")
def get_fundamentals(ticker: str, session: Session = Depends(get_session)) -> list[dict]:
    company = _get_company_or_404(ticker, session)

    periods = session.scalars(
        select(Fundamentals)
        .where(Fundamentals.ticker == company.ticker)
        .order_by(Fundamentals.fiscal_year.desc(), Fundamentals.fiscal_quarter.desc())
    )
    return [
        {
            "period_type": f.period_type,
            "fiscal_year": f.fiscal_year,
            "fiscal_quarter": f.fiscal_quarter or None,  # 0 is the DB's "annual" sentinel
            "sales": f.sales,
            "profit_after_tax": f.profit_after_tax,
            "eps": f.eps,
            "gross_profit_margin_pct": f.gross_profit_margin_pct,
            "net_profit_margin_pct": f.net_profit_margin_pct,
            "eps_growth_pct": f.eps_growth_pct,
            "peg": f.peg,
        }
        for f in periods
    ]


@router.get("/api/fundamentals/{ticker}/comparison")
def get_fundamentals_comparison(ticker: str, session: Session = Depends(get_session)) -> dict:
    company = _get_company_or_404(ticker, session)

    return {
        "qoq": get_qoq_comparison(session, company.ticker),
        "yoy": get_yoy_comparison(session, company.ticker),
    }


@router.get("/api/technicals/{ticker}")
def get_technicals_endpoint(ticker: str, session: Session = Depends(get_session)) -> dict:
    company = _get_company_or_404(ticker, session)
    return get_technicals(session, company.ticker)


@router.get("/api/news/{ticker}")
def get_news(ticker: str, limit: int = 50, session: Session = Depends(get_session)) -> list[dict]:
    company = _get_company_or_404(ticker, session)

    items = get_news_for_ticker(session, company.ticker, limit=limit)
    return [
        {
            "source_type": n.source_type,
            "category": n.category,
            "title": n.title,
            "url": n.url,
            "published_at": n.published_at,
            "source": n.source,
        }
        for n in items
    ]


@router.get("/api/macro")
def get_macro_snapshot(session: Session = Depends(get_session)) -> dict:
    return get_latest_macro_snapshot(session)


@router.get("/api/macro/{ticker}")
def get_macro_for_ticker(ticker: str, session: Session = Depends(get_session)) -> dict:
    company = _get_company_or_404(ticker, session)
    return get_relevant_macro_context(session, company.ticker)
