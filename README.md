# PSX Shariah Analyzer — Phase 1 + Phase 2

Personal, single-user tool. Phase 1: KMI-30 constituent scraper + PSX price scraper (EOD + intraday). Phase 2: company fundamentals scraper (Sales, Profit after Taxation, EPS, annual ratios) + QoQ/YoY comparison logic. All backed by MySQL, with APScheduler running the jobs on schedule. No frontend, no bot yet — see `PSX-Shariah-Analyzer-Spec.md` for the full roadmap.

## Setup

1. Create a virtualenv and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your local MySQL credentials.
3. Create the database and tables:
   ```
   mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS psx_shariah_analyzer CHARACTER SET utf8mb4;"
   python scripts/init_db.py
   ```
4. Run the test suite (offline, uses fixtures — no live scraping):
   ```
   python -m pytest tests/ -v
   ```
5. Start the app (FastAPI + scheduler):
   ```
   uvicorn app.main:app --reload
   ```
   Check `http://127.0.0.1:8000/health`, `/api/companies`, `/api/prices/{ticker}`.

## Manual one-shot scraper runs (for testing/debugging)

```
python scripts/run_kmi30_scrape_once.py
python scripts/run_price_scrape_once.py --mode eod
python scripts/run_price_scrape_once.py --mode intraday
python scripts/run_fundamentals_scrape_once.py
```

Each run writes a row to `scrape_runs` (status, rows affected, error message) regardless of success/failure — check that table if something looks off.

## Scraper sources (confirmed working against live data, 2026-08-31)

- **KMI-30 constituents**: `https://dps.psx.com.pk/indices/KMI30` — PSX's own Data Portal, static HTML table, no JS/auth needed. This replaced the original guess at Al Meezan's site, which turned out to only publish the list as PDFs. No sector column on this page — `sector` stays `NULL` for now, fillable later via a per-company page scrape.
- **Prices (EOD + intraday)**: `https://dps.psx.com.pk/market-watch` — one static HTML table with live OHLCV for every PSX-listed symbol (~490 rows), filtered down to the 30 KMI-30 tickers. This is a single batched request instead of 30 per-ticker calls; `interval_type` on the stored row (not the source) distinguishes an EOD run from an intraday poll. The per-ticker `dps.psx.com.pk/timeseries/{eod,int}/{ticker}` endpoints were also confirmed live and work, and remain a documented fallback in scraper comments if market-watch scraping ever breaks.

- **Fundamentals**: `https://dps.psx.com.pk/company/{ticker}` — same PSX Data Portal domain, one request per ticker (no batched endpoint exists for this). Server-rendered `#financials` section (Annual: Sales/Profit after Taxation/EPS for the last 4 fiscal years; Quarterly: same 3 metrics for the last 4 fiscal quarters) and `#ratios` section (Gross Profit Margin %, Net Profit Margin %, EPS Growth %, PEG — annual-only). Attributed to Capital Stake, a licensed data aggregator PSX embeds. No PDF parsing needed — the original spec assumed PDFs would be required, but this structured HTML source made that unnecessary.

All three were verified end-to-end: real requests, real row inserts into MySQL, verified via the API.

## What's verified working end-to-end

- MySQL schema (`companies`, `price_ohlcv`, `fundamentals`, `scrape_runs`) created and matches the plan
- FastAPI app boots, all 4 scheduler jobs register on startup, `/health`, `/api/companies`, `/api/prices/{ticker}`, `/api/fundamentals/{ticker}`, `/api/fundamentals/{ticker}/comparison` all serve real data
- Live KMI-30 constituent scrape: 30/30 real tickers inserted
- Live EOD price scrape: 30/30 tickers, real OHLCV from market-watch
- Live intraday poll (tested with the market-hours guard mocked open, since testing happened outside trading hours): 30/30 tickers, correctly no-ops with zero rows/no error when run for real outside market hours
- Live fundamentals scrape: 30/30 tickers, 240 rows (4 annual + 4 quarterly periods × 30 companies); QoQ/YoY comparison endpoint verified against hand-checked numbers (e.g. LUCK Q3 2026 vs Q2 2026: profit +56.41%; vs Q3 2025: profit -0.13%)
- Re-run idempotency: re-scraping KMI-30 and fundamentals doesn't create duplicate rows (240 → 240 → 240 across repeated fundamentals runs)
- Offline parser unit tests (20/20) pass using saved fixtures, independent of the live site
- Found and fixed real bugs during live testing (unit tests alone couldn't catch these — they only surface against a real MySQL upsert): (1) the price/fundamentals upserts referenced a server-generated `fetched_at` column that wasn't in the INSERT list; (2) SQLAlchemy's default `Enum` binding stored Python enum *names* (`EOD`, `FAILED`) instead of `.value` (`eod`, `failed`); (3) a bulk multi-row insert requires every row dict to share the same keys — quarterly fundamentals rows silently omitting ratio columns broke the batch once combined with annual rows; (4) **the big one**: MySQL's unique constraint treats `NULL != NULL`, so using `NULL` for `fiscal_quarter` on annual rows meant every re-scrape inserted fresh duplicate annual rows instead of upserting — fixed by using `0` as an explicit "annual" sentinel (stored as `0`, exposed as `null` over the API)
