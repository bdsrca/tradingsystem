# Trading System Phased Implementation Plan
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Phase Overview

The project should be built in 7 phases. Each phase should leave the repository in a working, testable state and should be committed before the next phase starts.

The guiding rule is reuse-first integration:

- Reuse Kronos forecasting logic directly where practical.
- Reuse TradingAgents workflow, checkpoint, memory, and provider patterns where practical.
- Build only the product adapters needed around those upstream projects.

## Phase 0: Repository And Local Runtime Foundation

Goal: create a clean monorepo foundation that can run locally.

Deliverables:

- Next.js web app scaffold.
- FastAPI app scaffold.
- Python package structure for data, quant, agents, email, and worker code.
- Docker Compose for Postgres and local services.
- Environment template.
- Upstream dependency strategy documented for Kronos and TradingAgents.
- Basic health endpoint.
- Basic frontend shell.

Verification:

- `docker compose up` starts Postgres and the app services.
- API health endpoint returns OK.
- Web app loads a simple local page.
- CI or local commands can run lint/typecheck/test placeholders.

Tasks:

- [x] Scaffold repository structure: `apps/web`, `apps/api`, `packages/data`, `packages/quant`, `packages/agents`, `packages/email`, `workers/daily`, `infra`.
- [x] Add Python project tooling for FastAPI and shared packages.
- [x] Add Node project tooling for Next.js.
- [x] Add Docker Compose with Postgres.
- [x] Add `.env.example`.
- [x] Document the Kronos integration strategy in `CONTRIBUTING.md`. Default to `vendor/Kronos` or a Git submodule unless a standard package install is verified; Kronos currently should not be assumed to support `pip install git+...` from a `pyproject.toml`.
- [x] Add explicit configuration for the chosen Kronos source path or pinned commit in Python configuration and Docker build notes.
- [x] Pin the intended TradingAgents source to a specific commit or version in the dependency plan.
- [x] Run an initial dependency conflict check plan for Kronos, TradingAgents, LangGraph, LangChain, pandas, yfinance, and FastAPI. The actual lock can be finalized when dependencies are added, but the integration constraints must be visible from Phase 0.
- [x] Add API health endpoint.
- [x] Add web shell page.
- [x] Add initial smoke tests.
- [x] Commit.

## Phase 1: Database, Watchlist, Market Data, And Candlestick UI

Goal: make the app useful without AI yet.

Deliverables:

- Alembic migrations.
- Core tables: `watchlist_items`, `market_data_bars`, `analysis_runs`, `signals`.
- Watchlist CRUD API.
- Watchlist page.
- Twelve Data provider adapter.
- US/Canada symbol normalization.
- OHLCV refresh.
- Trading calendar abstraction for NYSE/Nasdaq/TSX.
- Candlestick detail page with buy/sell marker support.
- Lightweight Charts loaded client-side only in Next.js.

Verification:

- Add a US ticker and Canadian ticker to the watchlist.
- Fetch daily OHLCV for both.
- Store bars with provider metadata and adjustment mode.
- Open stock detail page and see a candlestick chart.
- Unit tests cover symbol normalization and calendar window calculation.

Tasks:

- [x] Write failing tests for symbol normalization: `AAPL`, `SHOP.TO`, `RY.TO`, provider-specific TSX symbols.
- [x] Implement symbol normalization.
- [x] Write failing migration tests or schema checks for watchlist and market bars.
- [x] Implement Alembic migrations.
- [x] Write failing API tests for watchlist CRUD.
- [x] Implement watchlist CRUD.
- [x] Write failing tests for Twelve Data adapter response parsing.
- [x] Implement Twelve Data adapter.
- [x] Write failing tests for NYSE/Nasdaq/TSX trading-day windows.
- [x] Implement calendar abstraction.
- [x] Build watchlist UI.
- [x] Build stock detail K-line chart with empty marker support.
- [x] Wrap every Lightweight Charts component in a client-only boundary. Components that reference `window`, DOM APIs, or `lightweight-charts` must live under `'use client'` and be loaded with Next.js `dynamic(..., { ssr: false })` from server-rendered routes.
- [x] Add a build/smoke check that would catch `window is not defined` errors from accidental server-side chart imports.
- [x] Commit.

## Phase 2: Deterministic Baseline Signals And Paper Validation

Goal: produce real stored signals before adding model complexity.

Deliverables:

- Technical indicators: moving averages, RSI, MACD, ATR, volume trend.
- Deterministic baseline signal engine.
- Append-only `signals`.
- `paper_trades`.
- `paper_portfolio_snapshots`.
- Paper validation page with 1Y/2Y/3Y view.
- Realized outcome backfill fields.
- Nullable `signals.disagreement_level` column for later Kronos-vs-final-decision tracking.

Verification:

- Manual analysis creates a signal from technical indicators.
- The signal appears as a marker on the K-line chart.
- Paper page displays equity curve and metrics.
- Unit tests cover repeat BUY, REDUCE 50%, max positions, and frozen signal snapshots.
- `paper_portfolio_snapshots.benchmark_value` exists from the first schema version, even if Phase 2 initially stores `null`.
- `signals.disagreement_level` accepts `none`, `soft`, `hard`, or `null`, with fill logic deferred until Phase 7.

Tasks:

- [x] Write failing tests for indicator calculations.
- [x] Implement indicators.
- [x] Write failing tests for baseline signal labels.
- [x] Implement baseline signal engine.
- [x] Write failing tests for immutable signal behavior.
- [x] Implement append-only signal storage.
- [x] Add a Phase 2 Alembic migration for fields and tables introduced after Phase 1: deterministic signal metadata, `paper_trades`, `paper_portfolio_snapshots`, realized outcome fields, and nullable `signals.disagreement_level`. Do not assume Phase 1 created these future fields.
- [x] Write failing tests for paper-trading rules.
- [x] Implement paper-trading simulator.
- [x] Keep Phase 2 paper validation based on deterministic baseline signals only. Kronos forecast overlays on paper charts are deferred until after Kronos integration.
- [x] Include `benchmark_symbol` and `benchmark_value` in `paper_portfolio_snapshots` during the initial schema, populated as `null` until benchmark comparison is implemented.
- [x] Include nullable `disagreement_level` on `signals` during the initial schema to avoid a later migration just for Phase 7 disagreement display.
- [x] Build paper validation page.
- [x] Add stock-detail signal markers.
- [x] Commit.

## Phase 3: Kronos Reuse-First Integration

Goal: integrate Kronos as the upstream forecast model without rewriting it.

Deliverables:

- Kronos dependency strategy.
- Kronos input adapter for OHLCV plus zero-filled `amount` when unavailable.
- `predict_batch` grouping by `(lookback_length_bucket, pred_len)`.
- Minimum history requirement.
- Timeout and degraded fallback.
- `KronosOutputAdapter`.
- Forecast overlay on the stock detail chart.

Verification:

- Tests prove batch grouping rejects incompatible shapes before inference.
- A ticker with enough history produces `KronosForecastResult`.
- A ticker with short history marks Kronos as skipped/degraded.
- The chart can display forecast path or band.

Tasks:

- [x] Implement the Kronos dependency strategy chosen in Phase 0. Do not re-decide the strategy here unless Phase 0's assumption is proven invalid. Phase 3 uses a separate HTTP wrapper around pinned upstream Kronos so the main API does not import PyTorch.
- [x] Record that Kronos is not vendored into the main app in Phase 3; `services/kronos_service` imports upstream source from `KRONOS_SOURCE_PATH`, pinned by `KRONOS_GIT_REF`.
- [x] Write failing test for `test_kronos_batch_grouping_by_lookback_length()`.
- [x] Implement batch grouping.
- [x] Write failing tests for minimum history and short-history fallback.
- [x] Implement Kronos eligibility checks.
- [x] Write failing tests for Kronos DataFrame to `KronosForecastResult`.
- [x] Implement `KronosOutputAdapter`.
- [x] Add timeout/degraded behavior.
- [x] Add forecast overlay UI.
- [x] Commit.

## Phase 4: LLM Provider And TradingAgents Reuse-First Integration

Goal: reuse TradingAgents logic for explanation and decision flow while anchoring all numeric inputs to this platform's data snapshot.

Deliverables:

- Remote LLM and Ollama connectivity checks.
- Data snapshot contract for all agent inputs.
- TradingAgents dependency pinned to a specific commit or version.
- Dependency lock/conflict check with Kronos and TradingAgents active together.
- TradingAgents component integration or compatibility wrapper.
- Agent data tool wrapping/disablement so agents do not fetch conflicting prices.
- LangGraph checkpoint pointer support.
- Decision memory compatible with TradingAgents-style memory.
- Prompt guardrail validator.

Verification:

- LLM connectivity test passes for configured provider.
- Dependency lock succeeds with the selected TradingAgents commit and Kronos integration strategy.
- Agent run consumes a frozen data snapshot.
- Unsupported numbers in LLM output are flagged degraded.
- Checkpoint metadata is stored as a pointer, not mixed blobs.
- Decision memory can inject prior lessons.

Tasks:

- [ ] Pin TradingAgents to a specific commit or version before importing its components.
- [ ] Run dependency conflict checks with Kronos and TradingAgents enabled together.
- [ ] Write failing tests for provider config and Ollama base URL.
- [ ] Implement LLM provider adapter.
- [ ] Write failing tests for agent data anchoring.
- [ ] Implement snapshot-to-agent input adapter.
- [ ] Inventory TradingAgents internal external-data tools, especially yfinance-backed calls, before enabling the workflow.
- [ ] Write failing tests for disabling conflicting external data pulls.
- [ ] Implement data-tool wrappers.
- [ ] Integrate or wrap TradingAgents analyst workflow only after the external-data inventory and wrappers are in place, so test runs cannot leak live yfinance/provider calls.
- [ ] Write failing tests for hallucination validator.
- [ ] Implement validator and one retry path.
- [ ] Add checkpoint pointer support.
- [ ] Add decision memory persistence.
- [ ] Commit.

## Phase 5: Scheduler, Worker, Freshness, Email, And Observability

Goal: make the system run daily and notify sanely.

Deliverables:

- APScheduler in FastAPI lifespan.
- Explicit `SCHEDULER_TIMEZONE`, default `America/Toronto`.
- Default trigger at 17:00 ET.
- Provider bar freshness retries.
- Per-ticker job lease or advisory-lock strategy that does not hold a long database transaction across Kronos or LLM calls.
- Worker structured logs.
- Daily digest email.
- Strong-signal email aggregation and debounce.

Verification:

- Manual trigger and scheduled trigger call the same analysis function.
- Duplicate ticker run returns 409 or skips when locked.
- Lock tests prove a slow Kronos/LLM run does not hold a long open database transaction.
- Delayed bar retry logic marks stale-data-delayed after retries.
- Repeated same-direction alert is suppressed within debounce window.
- Daily digest shows succeeded, failed, skipped, stale, and degraded counts.

Tasks:

- [ ] Write failing tests for scheduler timezone config.
- [ ] Implement scheduler config.
- [ ] Write failing tests for analysis lock conflict.
- [ ] Implement the V1 default lock strategy with an in-process `asyncio.Lock` keyed by `ticker::market`, plus persisted `analysis_runs` status checks for recovery visibility. Avoid wrapping the full Kronos/LLM analysis in one long `pg_advisory_xact_lock` transaction.
- [ ] Document lock key derivation if Postgres advisory locks are used, such as `hashtext(ticker || '::' || market)`, and document why the lock does or does not span the full run.
- [ ] Write failing tests for provider freshness retry.
- [ ] Implement freshness retry.
- [ ] Add a Phase 5 Alembic migration for scheduler/worker/email fields introduced after Phase 1 and Phase 2, including email debounce metadata, worker run summaries, freshness/degraded status fields, and any persisted job lease/status fields. Do not assume Phase 1 created these operational fields.
- [ ] Write failing tests for email debounce.
- [ ] Implement email aggregation and debounce.
- [ ] Add structured worker logs and daily summary.
- [ ] Commit.

## Phase 6: Local Hardening And Cloud-Ready Packaging

Goal: prepare for stable self-hosted use.

Deliverables:

- Basic Auth for cloud mode.
- Backup/restore notes for Postgres.
- Idempotent database initialization script.
- Deployment notes.
- Secrets handling.
- End-to-end smoke script.
- README update with first-run instructions.

Verification:

- Local first-run instructions work from a clean checkout.
- Cloud mode protects the UI/API.
- Database initialization runs Alembic and LangGraph checkpoint setup safely more than once.
- Smoke script verifies web, API, DB, watchlist, and one analysis run.

Tasks:

- [ ] Add Basic Auth middleware for deployed mode.
- [ ] Add `infra/scripts/init_db.py` or equivalent Python initialization command that runs Alembic migrations, awaits LangGraph checkpointer setup when enabled, and is idempotent.
- [ ] Document the database initialization command as a required first-run step in README.
- [ ] Add deployment env documentation.
- [ ] Add backup/restore documentation.
- [ ] Add smoke test script.
- [ ] Update README with first-run instructions.
- [ ] Commit.

## Phase 7: Calibration And Quality Tracking

Goal: measure whether the system is useful before increasing automation.

Deliverables:

- Forecast accuracy tracking.
- Signal outcome dashboard.
- Kronos vs final-decision disagreement view.
- Defined disagreement threshold rule.
- Cross-market Kronos caveat display.
- Optional Kronos fine-tune investigation plan for Nasdaq/NYSE/TSX.

Verification:

- Realized 5/10/20/30 day outcomes are backfilled.
- Accuracy dashboard shows forecast vs actual.
- UI highlights Kronos/agent disagreement.
- Disagreement calculation fills `signals.disagreement_level` using the stored nullable column from Phase 2.

Tasks:

- [ ] Write failing tests for realized outcome backfill.
- [ ] Implement outcome backfill job.
- [ ] Add accuracy tracking query/API.
- [ ] Add accuracy dashboard.
- [ ] Define disagreement rules before UI work: direction mismatch is `hard`; Kronos magnitude above the configured threshold while the final signal is `HOLD` or `WATCH` is `soft`; otherwise `none`.
- [ ] Add Kronos disagreement UI state.
- [ ] Commit.

## Recommended Starting Point

Start with Phase 0 and Phase 1. Do not start Kronos or TradingAgents integration until the local app can store watchlist items, fetch OHLCV, and show a candlestick chart.
