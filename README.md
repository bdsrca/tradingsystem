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

The repository is in design/specification stage.

Primary design document:

- [`docs/superpowers/specs/2026-06-04-trading-system-design.md`](docs/superpowers/specs/2026-06-04-trading-system-design.md)

## Disclaimer

This project is for research and decision support. It is not financial advice and does not execute trades.
