# Trading System

Local-first stock signal and explanation platform for US and Canadian equities.

This project is being designed as a personal trading research system, not an automated broker or real-time trading bot. The first version focuses on daily post-close swing signals for a 5-30 trading day window, with transparent explanations and simple paper-validation.

## Scope

V1 targets:

- Single-user local use first, cloud-ready later.
- US and Canadian stocks.
- Watchlist management.
- Daily post-close analysis only.
- Candlestick charts with buy/sell markers.
- Signals: `BUY`, `WATCH`, `HOLD`, `REDUCE`, `SELL`.
- Explanations showing the decision path, risks, and invalidation conditions.
- Optional remote LLM API or local Ollama model.
- Kronos-based forecast input with conservative weighting until exchange-specific validation is complete.
- TradingAgents-based analyst workflow with data-snapshot anchoring.
- Email digest and debounced strong-signal alerts.
- 1-3 year paper-validation using frozen historical signals.

Out of scope for V1:

- Real-time intraday signals.
- Broker integration.
- Automatic order execution.
- Multi-user SaaS.

## Architecture Direction

Planned modules:

- `apps/web`: Next.js UI.
- `apps/api`: FastAPI API.
- `workers/daily`: scheduled analysis runner.
- `packages/data`: market data providers and snapshot cache.
- `packages/quant`: indicators, calendars, Kronos adapter, paper-validation.
- `packages/agents`: LLM and TradingAgents integration.
- `packages/email`: digest and alert delivery.
- `infra`: local Docker and deployment configuration.

V1 runs as a combined API/worker process with APScheduler in the FastAPI lifespan. Cloud deployment can later split API and worker services after a Postgres-backed job table or queue exists.

## Upstream Integration

This project is reuse-first:

- Use Kronos as the upstream forecasting model rather than rewriting its prediction logic.
- Use TradingAgents as the upstream agent workflow foundation rather than building a clean-room multi-agent framework.
- Add adapters only where product requirements need them: US/Canada data snapshots, symbol normalization, Kronos output conversion, watchlist runs, paper-validation, email alerts, and UI.

## Key Design Constraints

- Daily analysis defaults to 17:00 ET with explicit scheduler timezone configuration.
- US and Canadian trading calendars are handled separately.
- TSX calendar behavior must be verified against TMX holiday schedules.
- All agent numerical inputs must come from one stored data snapshot.
- Historical signals are append-only once used for paper-validation.
- Kronos batch jobs are grouped by lookback length and prediction length.
- Strong-signal emails are aggregated and debounced.

## Current Status

The repository is in Phase 1 implementation:

- FastAPI service with health, watchlist CRUD, market-data read, and Twelve Data daily refresh endpoints.
- Alembic Phase 1 schema for watchlist items, OHLCV bars, analysis runs, and signals.
- US/Canada symbol normalization for common Yahoo-style and provider-style tickers.
- Trading calendar abstraction for US and Canadian exchanges.
- Next.js watchlist page and stock detail candlestick page using client-only Lightweight Charts.

## Local Quick Start

1. Copy `.env.example` to `.env`.
2. Create and activate a Python virtual environment.
3. Install Python dependencies: `python -m pip install -r requirements-dev.txt`.
4. Install Node dependencies: `npm install`.
5. Run API tests: `npm run test:api`.
6. Run web type checks: `npm run typecheck:web`.
7. Apply the Phase 1 database migration from the repository root:

```powershell
$env:DATABASE_URL='sqlite+aiosqlite:///./trading_system.db'
.\.venv\Scripts\python.exe -m alembic -c apps/api/alembic.ini upgrade head
```

8. Start the API from the repository root:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
.\.venv\Scripts\python.exe -m uvicorn trading_system_api.main:app --host 127.0.0.1 --port 8000
```

9. Start the web app from `apps/web`: `npx next dev --hostname 127.0.0.1 --port 3001`.

The API health endpoint is `http://127.0.0.1:8000/health`. The web app is available at `http://127.0.0.1:3001`, with the watchlist at `/watchlist` and stock detail pages at `/stock/AAPL` or `/stock/SHOP?exchange=TSX`.

Set `TWELVE_DATA_API_KEY` before using `POST /market-data/{symbol}/refresh` against the live Twelve Data API.

Primary design document:

- [`docs/superpowers/specs/2026-06-04-trading-system-design.md`](docs/superpowers/specs/2026-06-04-trading-system-design.md)

## Disclaimer

This project is for research and decision support. It is not financial advice and does not execute trades.
