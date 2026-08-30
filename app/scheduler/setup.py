import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.scheduler.jobs import (
    poll_intraday_prices,
    sync_eod_prices,
    sync_fundamentals,
    sync_general_news,
    sync_kmi30_constituents,
    sync_psx_announcements,
)

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.market_timezone)

    scheduler.add_job(
        sync_kmi30_constituents,
        trigger=CronTrigger(day_of_week="mon-fri", hour=17, minute=0),
        id="kmi30_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_eod_prices,
        trigger=CronTrigger(day_of_week="mon-fri", hour=16, minute=30),
        id="psx_eod_price_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_fundamentals,
        trigger=CronTrigger(day_of_week="mon-fri", hour=18, minute=0),
        id="psx_fundamentals_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_psx_announcements,
        trigger=CronTrigger(day_of_week="mon-fri", hour=18, minute=30),
        id="psx_announcements_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_general_news,
        trigger=CronTrigger(day_of_week="mon-fri", hour=19, minute=0),
        id="general_news_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        poll_intraday_prices,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour="9-15",
            minute=f"*/{settings.intraday_poll_interval_minutes}",
        ),
        id="psx_intraday_poll",
        replace_existing=True,
    )
    return scheduler


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = build_scheduler()
        _scheduler.start()
        logger.info("Scheduler started with jobs: %s", [j.id for j in _scheduler.get_jobs()])
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
        _scheduler = None
