# PSX Shariah Analyzer — Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 5 + Phase 6 + Phase 7

Personal, single-user tool. Phase 1: KMI-30 constituent scraper + PSX price scraper (EOD + intraday). Phase 2: company fundamentals scraper (Sales, Profit after Taxation, EPS, annual ratios) + QoQ/YoY comparison logic. Phase 3: historical price backfill + technical indicators (SMA, RSI, volume MA, support/resistance). Phase 4: PSX official announcements + general news scraping, tagged to companies. Phase 5: macro factor tracking (oil, USD/PKR, SBP policy rate, CPI, S&P 500), tagged to sensitive companies. Phase 6: signal engine — ranked, explainable watchlist combining fundamentals + technicals + news, with macro context and non-guaranteed entry/target ranges. Phase 7: React web dashboard (Watchlist, Company Deep-Dive, limited Companies screener) consuming the API. Backend: MySQL + APScheduler. No Telegram bot yet — see `PSX-Shariah-Analyzer-Spec.md` for the full roadmap.

## Setup

One-time, per machine:
1. Backend: create the virtualenv and install dependencies:
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
4. Run the backend test suite (offline, uses fixtures — no live scraping):
   ```
   python -m pytest tests/ -v
   ```
5. Install the frontend and root dev-runner dependencies:
   ```
   npm install
   npm install --prefix frontend
   ```

## Run the whole project (one command)

```
npm run dev
```

Starts the FastAPI backend (`:8000`, with the scheduler) and the Vite frontend dev server (`:5173`) together, labeled `[backend]`/`[frontend]` in one terminal. Open `http://localhost:5173`. Ctrl+C stops both.

To run them separately instead (e.g. to watch backend logs on their own): `uvicorn app.main:app --reload` in one terminal (venv activated), `npm run dev --prefix frontend` in another.

## Manual one-shot scraper runs (for testing/debugging)

```
python scripts/run_kmi30_scrape_once.py
python scripts/run_price_scrape_once.py --mode eod
python scripts/run_price_scrape_once.py --mode intraday
python scripts/run_fundamentals_scrape_once.py
python scripts/run_price_history_backfill_once.py  # one-time, seeds ~5yr history for indicators
python scripts/run_psx_announcements_scrape_once.py
python scripts/run_general_news_scrape_once.py
python scripts/run_macro_scrape_once.py
```

Each run writes a row to `scrape_runs` (status, rows affected, error message) regardless of success/failure — check that table if something looks off.

## Scraper sources (confirmed working against live data, 2026-08-31)

- **KMI-30 constituents**: `https://dps.psx.com.pk/indices/KMI30` — PSX's own Data Portal, static HTML table, no JS/auth needed. This replaced the original guess at Al Meezan's site, which turned out to only publish the list as PDFs. No sector column on this page — `sector` stays `NULL` for now, fillable later via a per-company page scrape.
- **Prices (EOD + intraday)**: `https://dps.psx.com.pk/market-watch` — one static HTML table with live OHLCV for every PSX-listed symbol (~490 rows), filtered down to the 30 KMI-30 tickers. This is a single batched request instead of 30 per-ticker calls; `interval_type` on the stored row (not the source) distinguishes an EOD run from an intraday poll. The per-ticker `dps.psx.com.pk/timeseries/{eod,int}/{ticker}` endpoints were also confirmed live and work, and remain a documented fallback in scraper comments if market-watch scraping ever breaks.

- **Fundamentals**: `https://dps.psx.com.pk/company/{ticker}` — same PSX Data Portal domain, one request per ticker (no batched endpoint exists for this). Server-rendered `#financials` section (Annual: Sales/Profit after Taxation/EPS for the last 4 fiscal years; Quarterly: same 3 metrics for the last 4 fiscal quarters) and `#ratios` section (Gross Profit Margin %, Net Profit Margin %, EPS Growth %, PEG — annual-only). Attributed to Capital Stake, a licensed data aggregator PSX embeds. No PDF parsing needed — the original spec assumed PDFs would be required, but this structured HTML source made that unnecessary.

- **Historical price backfill**: `https://dps.psx.com.pk/timeseries/eod/{ticker}` — same per-ticker endpoint noted above, but used here for its *full* history (~1,239 daily points per ticker, back to 2021) rather than just the latest point. One-time seed so technical indicators have enough real history to be meaningful immediately. Gives close + volume only, no open/high/low — that's fine for SMA/RSI/volume-MA, which are close/volume-based.

- **PSX official announcements**: `https://dps.psx.com.pk/company/{ticker}` — same page fundamentals visits, `#announcements` section with three tabs (Financial Results, Board Meetings, Others), each a real table of dated, titled disclosures with PDF links. Already tied to a specific company by construction — no fuzzy matching needed. Independent request/scraper from the fundamentals one, so a failure in either doesn't affect the other.
- **General news**: RSS feeds `brecorder.com/feeds/business`, `brecorder.com/feeds/markets`, `dawn.com/feeds/business` (standard RSS 2.0, parsed with stdlib `xml.etree.ElementTree` — no new dependency). Not PSX-specific, so articles are tagged to KMI-30 companies by matching the ticker (as a standalone uppercase word) or company name (case-insensitive substring) in the title+description. **Known limitation**: match rate is low day-to-day by nature (most financial news isn't about one small-cap Pakistani stock — live-verified at 5 matches out of 90 articles pulled), and name-matching only works well for companies whose official name matches everyday usage; no synonym/alias list is built for this.

- **Macro factors**: oil (WTI `CL=F`, Brent `BZ=F`), USD/PKR (`PKR=X`), and S&P 500 (`^GSPC`) from Yahoo Finance's unofficial `query1.finance.yahoo.com/v8/finance/chart/{symbol}` JSON API (no key needed). SBP policy rate and CPI inflation from `tradingeconomics.com/pakistan/{interest-rate,inflation-cpi}`'s real static-HTML "economic calendar" table — SBP's own site (`sbp.org.pk`) is behind an active Cloudflare JS challenge (hard 403), not worth a Playwright dependency for. Tagged to companies via a **hand-curated, not scraped** ticker→factor mapping (`app/services/macro_sensitivity.py`) — PSX's own `/sector-summary` page turned out to be client-rendered with no data in the static HTML, so `companies.sector` stays `NULL` as it has since Phase 1, and sector-sensitivity is asserted from each company's evident business (official name) instead.

All eight sources were verified end-to-end: real requests, real row inserts into MySQL, verified via the API.

## Signal engine (Phase 6)

`GET /api/signals` (ranked watchlist, all 30 companies) and `GET /api/signals/{ticker}` (one company's full detail) combine the four services above into an explainable score — **no black-box model, no new data source**: every trigger is a plain, named rule with a one-sentence explanation, reusing data the other services already compute.

- **Fundamental trigger**: profit after tax QoQ or YoY growth > +5%
- **Technical trigger**: `price > SMA50 > SMA200` (textbook uptrend structure)
- **News trigger**: at least one announcement/article in the last 30 days
- **Score/status**: 0-3 triggers fired → `none`/`consider`/`watch`; the full ranked list is always returned, including `none`-status companies, so it's clear *why* something isn't flagged, not just what is
- **Risk caution**: flagged independently whenever RSI > 70 (overbought), regardless of score — a high score never reads as "chase this now"
- **Macro context**: attached as explanatory text (not scored), one sentence per factor relevant to that company's sector exposure
- **Entry zone / target range**: reuses Phase 3's support/resistance directly (no new prediction model), always paired with an explicit non-guarantee risk note

Deliberately deferred: historical signal tracking/backtesting (needs its own design — a natural fit for Phase 7's dashboard) and any real news sentiment analysis (the news trigger is presence/recency-based only, not positive/negative scored — no such model exists anywhere in this project).

## Web dashboard (Phase 7)

`frontend/` — React (Vite, plain JS) + Tailwind CSS, three pages, all consuming the existing API with no new backend logic beyond CORS + one field:

- **Watchlist** (`/`) — the ranked signal list
- **Company Deep-Dive** (`/company/:ticker`) — price chart with SMA50/SMA200 overlays (computed **client-side** from `/api/prices`, same plain rolling-mean formula as the backend — `/api/technicals` only returns the latest single value, not a series), fundamentals with QoQ/YoY badges, full signal reasoning, macro context, entry/target range, and the complete news/announcements list
- **Companies** (`/companies`) — a **limited** screener (Shariah status / signal status / price only — sector and market-cap/valuation filters aren't built since that data doesn't exist, same dead end noted in Phases 1 and 5), sortable and filterable, using only 2 bulk API calls (no per-ticker N+1)

Chart built following the `dataviz` skill's guidance: validated categorical palette (blue/orange/aqua, CVD-safe per the skill's documented Delta-E checks) for the 3 series, legend + hover tooltip, single y-axis.

## What's verified working end-to-end

- MySQL schema (`companies`, `price_ohlcv`, `fundamentals`, `news_items`, `macro_factors`, `scrape_runs`) created and matches the plan
- FastAPI app boots, all 7 scheduler jobs register on startup (the price-history backfill is one-time/manual, not scheduled), `/health`, `/api/companies`, `/api/prices/{ticker}`, `/api/fundamentals/{ticker}`, `/api/fundamentals/{ticker}/comparison`, `/api/technicals/{ticker}`, `/api/news/{ticker}`, `/api/macro`, `/api/macro/{ticker}`, `/api/signals`, `/api/signals/{ticker}` all serve real data
- Live KMI-30 constituent scrape: 30/30 real tickers inserted
- Live EOD price scrape: 30/30 tickers, real OHLCV from market-watch
- Live intraday poll (tested with the market-hours guard mocked open, since testing happened outside trading hours): 30/30 tickers, correctly no-ops with zero rows/no error when run for real outside market hours
- Live fundamentals scrape: 30/30 tickers, 240 rows (4 annual + 4 quarterly periods × 30 companies); QoQ/YoY comparison endpoint verified against hand-checked numbers (e.g. LUCK Q3 2026 vs Q2 2026: profit +56.41%; vs Q3 2025: profit -0.13%)
- Live historical backfill: 30/30 tickers, 37,128 rows (~1,239 daily points per ticker, back to 2021); `/api/technicals/LUCK` returns real SMA20/50/200, RSI14, volume MA, support/resistance — SMA20 spot-checked by hand against raw `/api/prices/LUCK` closes and matches exactly (444.9975)
- Live PSX announcements scrape: 30/30 tickers, 417 real rows (Financial Results/Board Meetings/Others)
- Live general news scrape: 90 articles pulled across 3 feeds, 5 correctly tagged to companies (e.g. "Pakistan State Oil (PSO)" and "Sui Southern Gas Company (SSGC)" mentions found and matched, verified against the raw article text) — a low match count is the expected, not a failure
- Live macro factors scrape: all 6 factor types landed with real values (WTI $83.40, Brent $88.10, USD/PKR 277.23, S&P 500 7711.76, SBP policy rate 11.5%, CPI 9.2%); `/api/macro/OGDC` correctly includes oil factors and excludes usd_pkr/policy-rate, `/api/macro/LUCK` the reverse — confirming the sector-sensitivity filter works as designed; % change math verified by hand (CPI -17.12% = (9.2-11.1)/11.1×100)
- Re-run idempotency: re-scraping KMI-30, fundamentals, the price history backfill, PSX announcements, general news, and macro factors all leave row counts unchanged on a second run
- Live signal engine: `/api/signals` returns all 30 companies ranked; spot-checked ATRL's full detail (score 3, "watch") against its raw `/api/fundamentals/ATRL/comparison` and `/api/technicals/ATRL` output — the reasoning text's numbers (217.95% QoQ profit growth, price/SMA50/SMA200 values, entry/target range) match the underlying data exactly
- Offline unit tests (66/66) pass using saved fixtures, known reference values, and synthetic data for the pure scoring functions, independent of the live site
- Found and fixed real bugs during live testing (unit tests alone couldn't catch these — they only surface against a real MySQL upsert or real site structure): (1) the price/fundamentals upserts referenced a server-generated `fetched_at` column that wasn't in the INSERT list; (2) SQLAlchemy's default `Enum` binding stored Python enum *names* (`EOD`, `FAILED`) instead of `.value` (`eod`, `failed`); (3) a bulk multi-row insert requires every row dict to share the same keys — quarterly fundamentals rows silently omitting ratio columns broke the batch once combined with annual rows; (4) MySQL's unique constraint treats `NULL != NULL`, so using `NULL` for `fiscal_quarter` on annual rows meant every re-scrape inserted fresh duplicate annual rows instead of upserting — fixed by using `0` as an explicit "annual" sentinel (stored as `0`, exposed as `null` over the API); (5) the support/resistance fallback initially picked the "nearest value" instead of the intended rolling min/max, caught by a unit test on a monotonic price series before it ever hit production data
- Frontend visually verified end-to-end with both dev servers running (Playwright, headless Chromium, screenshots): Watchlist renders all 30 companies ranked with correct status colors; Company Deep-Dive renders a real, correctly-computed price chart (SMA50/SMA200 lines visibly track the price series) plus fundamentals, macro context, entry/target range, and 15 real news items for a sample ticker; Companies page filter interaction tested directly — selecting "watch" status correctly narrowed 30 rows to exactly the 6 companies shown as "watch" on the Watchlist; zero console/page errors across all three pages
