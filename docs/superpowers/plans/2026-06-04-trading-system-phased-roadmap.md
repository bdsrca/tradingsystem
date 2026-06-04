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
- Basic health endpoint.
- Basic frontend shell.

Verification:

- `docker compose up` starts Postgres and the app services.
- API health endpoint returns OK.
- Web app loads a simple local page.
- CI or local commands can run lint/typecheck/test placeholders.

Tasks:

- [ ] Scaffold repository structure: `apps/web`, `apps/api`, `packages/data`, `packages/quant`, `packages/agents`, `packages/email`, `workers/daily`, `infra`.
- [ ] Add Python project tooling for FastAPI and shared packages.
- [ ] Add Node project tooling for Next.js.
- [ ] Add Docker Compose with Postgres.
- [ ] Add `.env.example`.
- [ ] Add API health endpoint.
- [ ] Add web shell page.
- [ ] Add initial smoke tests.
- [ ] Commit.

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

Verification:

- Add a US ticker and Canadian ticker to the watchlist.
- Fetch daily OHLCV for both.
- Store bars with provider metadata and adjustment mode.
- Open stock detail page and see a candlestick chart.
- Unit tests cover symbol normalization and calendar window calculation.

Tasks:

- [ ] Write failing tests for symbol normalization: `AAPL`, `SHOP.TO`, `RY.TO`, provider-specific TSX symbols.
- [ ] Implement symbol normalization.
- [ ] Write failing migration tests or schema checks for watchlist and market bars.
- [ ] Implement Alembic migrations.
- [ ] Write failing API tests for watchlist CRUD.
- [ ] Implement watchlist CRUD.
- [ ] Write failing tests for Twelve Data adapter response parsing.
- [ ] Implement Twelve Data adapter.
- [ ] Write failing tests for NYSE/Nasdaq/TSX trading-day windows.
- [ ] Implement calendar abstraction.
- [ ] Build watchlist UI.
- [ ] Build stock detail K-line chart with empty marker support.
- [ ] Commit.

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

Verification:

- Manual analysis creates a signal from technical indicators.
- The signal appears as a marker on the K-line chart.
- Paper page displays equity curve and metrics.
- Unit tests cover repeat BUY, REDUCE 50%, max positions, and frozen signal snapshots.

Tasks:

- [ ] Write failing tests for indicator calculations.
- [ ] Implement indicators.
- [ ] Write failing tests for baseline signal labels.
- [ ] Implement baseline signal engine.
- [ ] Write failing tests for immutable signal behavior.
- [ ] Implement append-only signal storage.
- [ ] Write failing tests for paper-trading rules.
- [ ] Implement paper-trading simulator.
- [ ] Build paper validation page.
- [ ] Add stock-detail signal markers.
- [ ] Commit.

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

- [ ] Decide whether Kronos is vendored, installed from Git, or integrated as a submodule.
- [ ] Write failing test for `test_kronos_batch_grouping_by_lookback_length()`.
- [ ] Implement batch grouping.
- [ ] Write failing tests for minimum history and short-history fallback.
- [ ] Implement Kronos eligibility checks.
- [ ] Write failing tests for Kronos DataFrame to `KronosForecastResult`.
- [ ] Implement `KronosOutputAdapter`.
- [ ] Add timeout/degraded behavior.
- [ ] Add forecast overlay UI.
- [ ] Commit.

## Phase 4: LLM Provider And TradingAgents Reuse-First Integration

Goal: reuse TradingAgents logic for explanation and decision flow while anchoring all numeric inputs to this platform's data snapshot.

Deliverables:

- Remote LLM and Ollama connectivity checks.
- Data snapshot contract for all agent inputs.
- TradingAgents component integration or compatibility wrapper.
- Agent data tool wrapping/disablement so agents do not fetch conflicting prices.
- LangGraph checkpoint pointer support.
- Decision memory compatible with TradingAgents-style memory.
- Prompt guardrail validator.

Verification:

- LLM connectivity test passes for configured provider.
- Agent run consumes a frozen data snapshot.
- Unsupported numbers in LLM output are flagged degraded.
- Checkpoint metadata is stored as a pointer, not mixed blobs.
- Decision memory can inject prior lessons.

Tasks:

- [ ] Write failing tests for provider config and Ollama base URL.
- [ ] Implement LLM provider adapter.
- [ ] Write failing tests for agent data anchoring.
- [ ] Implement snapshot-to-agent input adapter.
- [ ] Integrate or wrap TradingAgents analyst workflow.
- [ ] Write failing tests for disabling conflicting external data pulls.
- [ ] Implement data-tool wrappers.
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
- Per-ticker advisory locks.
- Worker structured logs.
- Daily digest email.
- Strong-signal email aggregation and debounce.

Verification:

- Manual trigger and scheduled trigger call the same analysis function.
- Duplicate ticker run returns 409 or skips when locked.
- Delayed bar retry logic marks stale-data-delayed after retries.
- Repeated same-direction alert is suppressed within debounce window.
- Daily digest shows succeeded, failed, skipped, stale, and degraded counts.

Tasks:

- [ ] Write failing tests for scheduler timezone config.
- [ ] Implement scheduler config.
- [ ] Write failing tests for analysis lock conflict.
- [ ] Implement per-ticker lock handling.
- [ ] Write failing tests for provider freshness retry.
- [ ] Implement freshness retry.
- [ ] Write failing tests for email debounce.
- [ ] Implement email aggregation and debounce.
- [ ] Add structured worker logs and daily summary.
- [ ] Commit.

## Phase 6: Local Hardening And Cloud-Ready Packaging

Goal: prepare for stable self-hosted use.

Deliverables:

- Basic Auth for cloud mode.
- Backup/restore notes for Postgres.
- Deployment notes.
- Secrets handling.
- End-to-end smoke script.
- README update with first-run instructions.

Verification:

- Local first-run instructions work from a clean checkout.
- Cloud mode protects the UI/API.
- Smoke script verifies web, API, DB, watchlist, and one analysis run.

Tasks:

- [ ] Add Basic Auth middleware for deployed mode.
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
- Cross-market Kronos caveat display.
- Optional Kronos fine-tune investigation plan for Nasdaq/NYSE/TSX.

Verification:

- Realized 5/10/20/30 day outcomes are backfilled.
- Accuracy dashboard shows forecast vs actual.
- UI highlights Kronos/agent disagreement.

Tasks:

- [ ] Write failing tests for realized outcome backfill.
- [ ] Implement outcome backfill job.
- [ ] Add accuracy tracking query/API.
- [ ] Add accuracy dashboard.
- [ ] Add Kronos disagreement UI state.
- [ ] Commit.

## Recommended Starting Point

Start with Phase 0 and Phase 1. Do not start Kronos or TradingAgents integration until the local app can store watchlist items, fetch OHLCV, and show a candlestick chart.

