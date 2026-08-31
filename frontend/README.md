# PSX Shariah Analyzer — Frontend

React (Vite, plain JS) + Tailwind CSS dashboard consuming the FastAPI backend in `../app`.

## Setup

```
npm install
npm run dev
```

Runs on `http://localhost:5173`. Requires the backend running separately on `http://127.0.0.1:8000` (`uvicorn app.main:app --reload` from the project root) — CORS is configured for this dev pair only.

`VITE_API_BASE_URL` in `.env` controls the backend URL.

## Pages

- **Watchlist** (`/`) — ranked signal list from `GET /api/signals`
- **Companies** (`/companies`) — limited screener (Shariah status / signal status / price — no sector or market-cap filters, that data doesn't exist yet)
- **Company detail** (`/company/:ticker`) — price chart with SMA50/SMA200 overlays, fundamentals, signal reasoning, macro context, news

## Build

```
npm run build
```

Outputs to `dist/` (not committed). No production server wiring yet — this is a personal local-machine tool.
