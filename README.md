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
- `services/kronos_service`: optional local/remote HTTP wrapper around upstream Kronos.
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

The repository is in Phase 4 implementation:

- FastAPI service with health, watchlist CRUD, market-data read, and Twelve Data daily refresh endpoints.
- Alembic schema for watchlist items, OHLCV bars, analysis runs, signals, paper trades, portfolio snapshots, and Kronos forecasts.
- US/Canada symbol normalization for common Yahoo-style and provider-style tickers.
- Trading calendar abstraction for US and Canadian exchanges.
- Deterministic baseline indicators and signal engine.
- Append-only signal insertion for reproducible paper validation.
- Kronos input preparation, batch-shape grouping, minimum-history checks, timeout fallback, and output adaptation.
- Optional Kronos HTTP service wrapper that imports upstream Kronos from `KRONOS_SOURCE_PATH`.
- TradingAgents pinned as `vendor/TradingAgents` at commit `04f434e86db88e7707bf16db8ed7183f9764fe26`.
- TradingAgents live runner adapter with snapshot-anchored platform vendor routing, yfinance escape-path guards,
  checkpoint pointer metadata, split timeout handling, output adaptation, decision memory injection, and hallucination
  retry/store orchestration.
- Next.js watchlist, stock detail candlestick, signal marker, Kronos forecast overlay, and paper validation pages.

The deterministic baseline uses a pure pandas indicator implementation with pandas-ta-compatible column names. `pandas-ta` currently pulls a `numba` version that does not install under the local Python 3.14 environment, so the project avoids that runtime dependency until the package stack supports this interpreter cleanly.

## Local Quick Start

1. Copy `.env.example` to `.env`.
2. Initialize submodules: `git submodule update --init --recursive`.
3. Create and activate a Python virtual environment.
4. Install Python dependencies: `python -m pip install -r requirements-dev.txt`.
5. To run live TradingAgents analysis, also install the pinned upstream workflow:
   `python -m pip install -e vendor/TradingAgents`.
6. Install Node dependencies: `npm install`.
7. Run API tests: `npm run test:api`.
8. Run web type checks: `npm run typecheck:web`.
9. Initialize the database from the repository root:

```powershell
$env:DATABASE_URL='sqlite+aiosqlite:///./trading_system.db'
.\.venv\Scripts\python.exe -m infra.scripts.init_db
```

10. Start the API from the repository root:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
.\.venv\Scripts\python.exe -m uvicorn trading_system_api.main:app --host 127.0.0.1 --port 8000
```

11. Start the web app from `apps/web`: `npx next dev --hostname 127.0.0.1 --port 3001`.

The API health endpoint is `http://127.0.0.1:8000/health`. The web app is available at `http://127.0.0.1:3001`, with the watchlist at `/watchlist`, stock detail pages at `/stock/AAPL` or `/stock/SHOP?exchange=TSX`, and paper validation at `/paper/AAPL`.

Set `TWELVE_DATA_API_KEY` before using `POST /market-data/{symbol}/refresh` against the live Twelve Data API.

To use Kronos forecasts, run a Kronos service separately and set
`KRONOS_SERVICE_URL`. See
[`services/kronos_service/README.md`](services/kronos_service/README.md).
Without that service, `POST /kronos/{symbol}/forecast` stores a degraded
fallback result instead of blocking the baseline workflow.

Cloud deployment, Basic Auth, smoke-test, and backup/restore notes are in
[`docs/deployment.md`](docs/deployment.md).

Primary design document:

- [`docs/superpowers/specs/2026-06-04-trading-system-design.md`](docs/superpowers/specs/2026-06-04-trading-system-design.md)

## Disclaimer

This project is for research and decision support. It is not financial advice and does not execute trades.
