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
- TradingAgents component integration in the main Python environment if dependency checks pass.
- TradingAgents vendor bridge registered through upstream vendor routing where available.
- Agent data tool wrapping/disablement so agents do not fetch conflicting prices.
- No-network guard proving agent runs do not call yfinance or external market-data providers outside the platform snapshot.
- Async runner that wraps synchronous TradingAgents graph execution with an executor or worker boundary.
- Snapshot context isolation that prevents executor thread reuse from leaking one ticker's data into another ticker's run.
- Explicit `agent_reports` schema boundary before migration work starts.
- V1 analyst whitelist so unsupported TradingAgents analysts cannot silently fall back to yfinance-backed tools.
- LangGraph checkpoint pointer support.
- Decision memory compatible with TradingAgents-style memory.
- Prompt guardrail validator.

Verification:

- LLM connectivity test passes for configured provider.
- Dependency lock succeeds with the selected TradingAgents commit and Kronos integration strategy.
- Agent run consumes a frozen data snapshot.
- Agent workflow tests fail if `yfinance.download`, `yfinance.Ticker`, or external market-data hosts are called during execution; no-network guard is enforced at both yfinance monkeypatch and HTTP transport layers.
- `resolve_instrument_identity()` does not issue a network request during any agent run.
- Unsupported numbers in LLM output are flagged degraded.
- Unsupported future event dates in LLM output are recorded as hallucination warnings and mark the affected agent stage degraded.
- Checkpoint metadata is stored as a pointer, not mixed blobs, and checkpoint support is not claimed while upstream checkpointing is disabled.
- Decision memory can inject prior lessons.

Tasks:

- [x] Pin TradingAgents to a specific commit or version before importing its components.
- [x] Run dependency conflict checks with Kronos and TradingAgents enabled together.
- [x] Inventory TradingAgents internal external-data tools before enabling workflow tests. At the pinned commit this must include `tradingagents/dataflows/interface.py`, `VENDOR_METHODS`, `route_to_vendor()`, and the direct yfinance paths in `tradingagents/graph/trading_graph.py`.
- [x] Record the direct yfinance escape-path decision in `CONTRIBUTING.md`: `_fetch_returns()` is disabled or wrapped for Phase 4 agent runs, and `resolve_instrument_identity()` must use stored metadata or fail open without network by default.
- [x] Verify that `resolve_instrument_identity()` at the pinned TradingAgents commit calls `yf.Ticker().info` network-first and is `lru_cache`-backed. Add a Phase 4B runtime helper that clears the cache, replaces the function itself with snapshot-backed metadata, and patches the imported `trading_graph` reference. Record the patch location and method in `CONTRIBUTING.md`.
- [x] Write failing tests for registering a platform vendor through TradingAgents' vendor-routing layer.
- [x] Implement the platform vendor bridge for snapshot-backed market data, indicators, fundamentals, and news where the upstream method shape allows it.
- [x] Verify the pinned `route_to_vendor()` fallback chain and record the source fact in `CONTRIBUTING.md`: after configured primary vendors, upstream appends every registered vendor for the method. Platform vendor methods must return a `NO_DATA_AVAILABLE:` sentinel for missing snapshot data, unsupported methods, or adapter errors instead of raising ordinary exceptions that allow fallback to yfinance or Alpha Vantage.
- [x] Verify that pinned `get_vendor()` reads process-global `get_config()`, not only the local runner config dict. Add platform vendor config and an E2E seam test that calls upstream-style `set_config()` inside the sync worker before graph execution.
- [x] Verify that pinned `VENDOR_LIST = ["yfinance", "alpha_vantage"]` is not used as a `route_to_vendor()` filter. Do not modify that list for V1 platform routing.
- [x] Write failing no-network tests that monkeypatch `yfinance.download` and `yfinance.Ticker` to raise immediately during agent workflow execution.
- [x] Add HTTP-layer no-network tests with `pytest-httpx`, `respx`, or a native HTTPX transport guard, blocking external market-data hostnames such as `finance.yahoo.com`, `query1.finance.yahoo.com`, `twelvedata.com`, and `finnhub.io`. Split tests into unit tests with full network blocked and explicit integration tests where configured LLM endpoints may be allowed while market-data hosts remain blocked.
- [x] Add Phase 4B escape-path guard helpers for TradingAgents runs: fresh per-run `data_cache_dir`/`results_dir` creation that fails closed when reused, plus a pending-entry resolution no-op guard so stale memory logs cannot trigger `_fetch_returns()` and yfinance before the platform owns realized-return backfill.
- [x] Integrate the Phase 4B escape-path guard helpers into the actual TradingAgents runner before constructing workflow tests.
- [x] Ensure `vendor_bridge` snapshot context is reset in a `finally` block inside `_sync_run` so `ThreadPoolExecutor` thread reuse cannot carry a stale snapshot from one ticker analysis into the next. Prefer `contextvars.ContextVar` over `threading.local`. Add a test that runs two tickers sequentially on the same executor thread and asserts each gets only its own snapshot data.
- [x] Write failing tests for provider config and Ollama base URL.
- [x] Implement LLM provider adapter that emits TradingAgents' real config keys (`llm_provider`, `deep_think_llm`, `quick_think_llm`, `backend_url`) and scoped environment overrides for OpenAI and Ollama.
- [x] Write failing tests for agent data anchoring.
- [x] Implement snapshot-to-agent input adapter.
- [x] Whitelist the permitted analyst combinations for V1. Only `["market", "news", "fundamentals"]` is allowed. The runner must reject unsupported analysts such as `social_media` or `insider` with a clear config error before constructing `TradingAgentsGraph`.
- [x] Make `max_debate_rounds` and `max_risk_discuss_rounds` configurable via settings. Remote models default to one round; Ollama/local small models default to two rounds. Document that single-round debate with small local models may increase degraded structured-output rates.
- [x] Write failing tests for split timeout/degraded behavior around synchronous TradingAgents graph execution and signal extraction. At the pinned commit, `SignalProcessor.process_signal()` is deterministic, but the runner still preserves `final_state` if extraction fails or times out.
- [x] Add a split-timeout runner helper using `run_in_executor`: default graph timeout 240s, signal extraction timeout 30s, total timeout 280s.
- [x] Integrate the split-timeout helper into the actual TradingAgents runner with the Phase 4B runtime guards and LLM environment adapter.
- [x] Integrate or wrap TradingAgents analyst workflow only after the external-data inventory and wrappers are in place, so test runs cannot leak live yfinance/provider calls.
- [x] Write failing tests for hallucination validator.
- [x] Implement validator for unsupported numbers and future event dates that cannot be sourced from `snapshot.news_items`, `snapshot.fundamentals`, or explicit event records.
- [x] Implement one retry path for degraded agent output.
- [x] Define `agent_reports` schema before writing the Phase 4 Alembic migration: one row per analyst stage (`technical`, `fundamental`, `news`, `bull`, `bear`, `risk`, `final`) with `role`, `stage`, `content_text`, `structured_json`, `prompt_version`, `model_provider`, `model_name`, `duration_ms`, and `is_degraded`. `analysis_runs` stores snapshot/checkpoint/run-level timing metadata; `signals` stores only the final trade signal and confidence.
- [x] Add Phase 4 Alembic migration for data snapshot IDs, agent report storage, checkpoint pointer metadata, and prompt/model version fields introduced after Phase 3. This migration adds `analysis_runs.data_snapshot_id`, runtime duration/status columns, `agent_reports`, and `agent_checkpoint_pointers`; it does not modify `signals`, paper trading tables, email notification tables, or Phase 7 outcome backfill fields.
- [x] Add Phase 4 retry-attempt migration for `agent_reports.attempt_number` and `agent_reports.is_current`. Retry attempts append rows instead of upserting; `stage` remains one of the canonical analyst stages and is not overloaded with attempt labels.
- [x] Verify TradingAgents checkpoint source at the pinned commit: `get_checkpointer(data_cache_dir, ticker)` stores `{data_cache_dir}/checkpoints/{safe_ticker.upper()}.db`; `thread_id` is `sha256(f"{ticker.upper()}:{trade_date}")[:16]`; `clear_checkpoint()` deletes thread rows from `writes` and `checkpoints` and does not delete the DB file.
- [x] Make the Phase 4 checkpoint decision: use upstream LangGraph `SqliteSaver` with `checkpoint_enabled=True` when initialization succeeds, store pointer metadata only, and degrade to `checkpoint_enabled=False` when initialization fails.
- [x] Add checkpoint pointer helper and tests for write/read serialization, persistent checkpoint cache path, per-run memory-log isolation, and checkpoint initialization fallback.
- [x] Add Phase 4 DB store helpers for analysis-run status transitions, output-adapter `AgentReport` row persistence, retry append semantics, and checkpoint pointer metadata persistence.
- [x] Add decision memory persistence for V1: store prior lessons in the platform DB, expose `save_memory()` / `get_relevant_memories(ticker)`, and inject formatted lessons into the agent runner config as `decision_memory_context`. Do not synchronize upstream `trading_memory.md`; keep that file per-run isolated.
- [x] Call the Phase 4 DB store helpers from the live TradingAgents runner path once the pinned `TradingAgentsGraph` integration replaces the mock seam.
- [x] Verify TradingAgents `AgentState` keys at the pinned commit before writing the output adapter: `market_report`, `sentiment_report`, `news_report`, `fundamentals_report`, `investment_debate_state`, `investment_plan`, `trader_investment_plan`, `risk_debate_state`, and `final_trade_decision`.
- [x] Add an output adapter that parses `final_state` directly into `AgentReport` rows without reading `_log_state()` JSON files. Missing/empty report fields degrade the corresponding row instead of raising `KeyError`; `structured_json` stores adapter-owned summaries rather than parsed LLM JSON.
- [x] Integrate output adapter rows into the Phase 4 DB storage helper after the Phase 4 Alembic migration exists.
- [x] Add a mock E2E TradingAgents runner seam that wires Phase 4B runtime dirs, persistent checkpoint cache, per-run memory log, LLM environment, executor-thread snapshot context, split timeouts, signal extraction, and output adapter reports together.
- [x] Add E2E seam tests for the three runner junction risks: persistent checkpoint path must differ from per-run memory/results paths, `ContextVar` snapshot setup happens inside the executor thread, and mock `final_trade_decision` contains a parseable rating for deterministic signal extraction.
- [x] In the live `TradingAgentsGraph` integration, call actual `tradingagents.dataflows.config.set_config(config)` inside the worker before graph construction/execution and keep no-network workflow tests enabled.
- [x] Replace the mock graph step with the pinned `TradingAgentsGraph` construction after dependency checks and no-network workflow tests are in place.
- [x] Commit.

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
