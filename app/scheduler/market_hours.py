"""PSX market-hours helpers.

NOTE — needs live verification: PSX's regular session is commonly cited as
~9:15 AM-3:30 PM PKT, Mon-Fri, but Friday has historically sometimes had a
shortened/split session around prayer time, and this has changed over PSX's
history. Confirm current hours against PSX's published trading calendar
before relying on this for anything beyond Phase 1's polling guard.

Holidays are NOT accounted for in Phase 1 (`is_market_holiday` is a stub) —
the intraday poller will still fire on PSX holidays and simply find nothing
new to record (or get errors from upstream, which are logged and skipped).
"""

import logging
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.config import settings

logger = logging.getLogger(__name__)

# TODO(verify): maintain/expand this list, or replace with a scraped PSX holiday calendar.
KNOWN_PSX_HOLIDAYS: set[date] = set()


def _market_tz() -> ZoneInfo:
    return ZoneInfo(settings.market_timezone)


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def is_market_holiday(day: date) -> bool:
    if day in KNOWN_PSX_HOLIDAYS:
        return True
    return False


def is_market_open(dt: datetime | None = None) -> bool:
    """True if `dt` (default: now) falls within PSX's regular trading session."""
    tz = _market_tz()
    now = dt.astimezone(tz) if dt else datetime.now(tz)

    if now.weekday() >= 5:  # Saturday/Sunday
        return False

    if is_market_holiday(now.date()):
        return False

    open_time = _parse_hhmm(settings.market_open_time)
    close_time = _parse_hhmm(settings.market_close_time)
    return open_time <= now.time() <= close_time
