"""Create all tables directly from the SQLAlchemy models.

Shortcut in place of Alembic migrations — run this against the MySQL
database (`psx_shariah_analyzer` per .env.example) any time new models are
added; `create_all` only creates tables that don't exist yet, it won't alter
existing ones, so this is safe to re-run across phases.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import Base  # noqa: E402
from app.db.models import (  # noqa: E402, F401
    Company,
    Fundamentals,
    MacroFactor,
    NewsItem,
    PriceOHLCV,
    ScrapeRun,
)
from app.db.session import engine  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Tables created (or already existed):", ", ".join(Base.metadata.tables))


if __name__ == "__main__":
    main()
