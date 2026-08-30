import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Store a Python Enum's `.value`s in the DB, not its member `.name`s
    (SQLAlchemy's default Enum binding stores `.name` unless told otherwise —
    see Phase 1 postmortem in project memory)."""
    return [e.value for e in enum_cls]


class ShariahComplianceStatus(str, enum.Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNDER_REVIEW = "under_review"
    UNKNOWN = "unknown"


class IntervalType(str, enum.Enum):
    EOD = "eod"
    INTRADAY = "intraday"


class ScrapeRunStatus(str, enum.Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class PeriodType(str, enum.Enum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"


class NewsSourceType(str, enum.Enum):
    PSX_ANNOUNCEMENT = "psx_announcement"
    GENERAL_NEWS = "general_news"


class MacroFactorType(str, enum.Enum):
    OIL_WTI = "oil_wti"
    OIL_BRENT = "oil_brent"
    USD_PKR = "usd_pkr"
    SBP_POLICY_RATE = "sbp_policy_rate"
    CPI_INFLATION = "cpi_inflation"
    SP500 = "sp500"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_kmi30_constituent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    shariah_compliance_status: Mapped[ShariahComplianceStatus] = mapped_column(
        Enum(ShariahComplianceStatus, native_enum=False, length=20, values_callable=_enum_values),
        default=ShariahComplianceStatus.COMPLIANT,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    prices: Mapped[list["PriceOHLCV"]] = relationship(back_populates="company")


class PriceOHLCV(Base):
    __tablename__ = "price_ohlcv"
    __table_args__ = (
        UniqueConstraint("ticker", "timestamp", "interval_type", name="uq_price_ticker_ts_interval"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    interval_type: Mapped[IntervalType] = mapped_column(
        Enum(IntervalType, native_enum=False, length=10, values_callable=_enum_values),
        nullable=False,
    )
    open: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    close: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    company: Mapped["Company"] = relationship(back_populates="prices")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[ScrapeRunStatus] = mapped_column(
        Enum(ScrapeRunStatus, native_enum=False, length=10, values_callable=_enum_values),
        nullable=False,
    )
    rows_affected: Mapped[int | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class Fundamentals(Base):
    __tablename__ = "fundamentals"
    __table_args__ = (
        UniqueConstraint(
            "ticker", "period_type", "fiscal_year", "fiscal_quarter",
            name="uq_fundamentals_ticker_period",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    period_type: Mapped[PeriodType] = mapped_column(
        Enum(PeriodType, native_enum=False, length=10, values_callable=_enum_values),
        nullable=False,
    )
    fiscal_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # 0 for annual rows, 1-4 for quarterly — NOT NULL is deliberate: MySQL's
    # unique constraint treats NULL != NULL, so a NULLable fiscal_quarter
    # would let annual rows re-insert as "new" on every re-scrape instead of
    # upserting. Exposed as null to API consumers (see app/api/routes.py).
    fiscal_quarter: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    sales: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    profit_after_tax: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    eps: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    gross_profit_margin_pct: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    net_profit_margin_pct: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    eps_growth_pct: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    peg: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    company: Mapped["Company"] = relationship()


class NewsItem(Base):
    __tablename__ = "news_items"
    __table_args__ = (
        UniqueConstraint("ticker", "source_type", "url", name="uq_news_ticker_source_url"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_type: Mapped[NewsSourceType] = mapped_column(
        Enum(NewsSourceType, native_enum=False, length=20, values_callable=_enum_values),
        nullable=False,
    )
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    company: Mapped["Company"] = relationship()


class MacroFactor(Base):
    __tablename__ = "macro_factors"
    __table_args__ = (
        UniqueConstraint("factor_type", "observed_at", name="uq_macro_factor_observed"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    factor_type: Mapped[MacroFactorType] = mapped_column(
        Enum(MacroFactorType, native_enum=False, length=20, values_callable=_enum_values),
        nullable=False,
        index=True,
    )
    value: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
