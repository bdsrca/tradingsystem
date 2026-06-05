# Contributing

## Phase 0 Dependency Strategy

This repository follows a reuse-first integration strategy for Kronos and TradingAgents.

### Kronos

Kronos should be integrated as upstream forecasting logic, not rewritten locally.

The default Phase 0 assumption is `vendor/Kronos` or a Git submodule pinned to:

```text
67b630e67f6a18c9e9be918d9b4337c960db1e9a
```

Kronos currently should not be assumed to support a standard `pip install git+...`
workflow because the upstream repository does not expose a `pyproject.toml`,
`setup.py`, or `setup.cfg` at the checked revision.

As of Phase 3, the main API does not import PyTorch or Kronos directly. It uses
`packages/quant/trading_system_quant/kronos/client.py` to call a separate
`services/kronos_service` HTTP wrapper. The wrapper imports upstream Kronos from
`KRONOS_SOURCE_PATH` and calls `KronosPredictor.predict(...)`. This keeps model
runtime dependencies isolated while preserving reuse of upstream forecasting
logic.

Do not reimplement Kronos model inference in this repository. Product-specific
code should stay limited to data preparation, future trading-day timestamps,
batch grouping, timeout/fallback behavior, output adaptation, storage, and UI.

### TradingAgents

TradingAgents should be integrated as upstream agent workflow logic, not rebuilt
from scratch.

The intended pinned upstream reference is:

```text
04f434e86db88e7707bf16db8ed7183f9764fe26
```

Phase 4 pins TradingAgents as a Git submodule at `vendor/TradingAgents` on
commit `04f434e86db88e7707bf16db8ed7183f9764fe26`.

Dependency conflict check result on 2026-06-05:

```powershell
python -m pip install --dry-run -r requirements-dev.txt -e vendor/TradingAgents
```

The first run failed only because `vendor/TradingAgents` was not present yet.
After adding the pinned submodule, the dry-run exited with `PIP_STATUS=0` and
`MATCH_COUNT=0` for `(conflict|ERROR|incompatible|error)`.

TradingAgents internal external data calls must be inventoried and wrapped or
disabled before analyst workflow tests run.

At the pinned commit, TradingAgents exposes `VENDOR_METHODS` and
`route_to_vendor()` in `tradingagents/dataflows/interface.py`. Phase 4 should
prefer registering a platform vendor there so analyst tools read this
platform's frozen data snapshot instead of monkey-patching broad internals.
`route_to_vendor()` builds a fallback chain from the configured primary vendor
plus every vendor registered for the method in `VENDOR_METHODS`. Therefore
platform vendor methods must not raise ordinary exceptions for missing snapshot
data, unsupported methods, or adapter errors. Return a `NO_DATA_AVAILABLE:`
sentinel string or raise upstream `NoMarketDataError`; otherwise upstream can
continue to yfinance or Alpha Vantage after the platform adapter fails.

At the pinned commit, `get_vendor()` reads the process-global
`tradingagents/dataflows/config.py::get_config()` value rather than a per-run
config dict. The actual TradingAgents runner must call upstream `set_config()`
with this platform's merged config inside the synchronous worker before graph
construction or execution. `VENDOR_LIST` is hardcoded to `["yfinance",
"alpha_vantage"]`, but `route_to_vendor()` does not use it as a filter, so do
not edit that list merely to register `platform`.

Known direct yfinance escape paths at the pinned commit:

- `tradingagents/graph/trading_graph.py::_fetch_returns()`
- `tradingagents/graph/trading_graph.py` calls `resolve_instrument_identity()`
- `tradingagents/agents/utils/agent_utils.py::resolve_instrument_identity()` calls `yf.Ticker(...).info`

The Phase 4 default is no live market-data network calls during an agent run.
Tests should fail if yfinance or another external market-data source is reached
outside the platform snapshot. Company identity can fail open to stored metadata
or an empty value, but it should not silently perform live network lookup by
default.

At the pinned commit, `resolve_instrument_identity()` is decorated with
`functools.lru_cache(maxsize=256)`. Agent runner code must clear that cache and
replace the resolver function itself before calling `TradingAgentsGraph.propagate()`;
blocking network calls alone can produce false-positive tests if a previous run
filled the cache. `packages/agents/trading_system_agents/tradingagents_runtime.py`
contains the Phase 4B helper for this: it calls `cache_clear()` when available
and patches both `tradingagents.agents.utils.agent_utils.resolve_instrument_identity`
and the imported `tradingagents.graph.trading_graph.resolve_instrument_identity`
reference with snapshot-backed identity metadata.

`TradingAgentsGraph.propagate()` resolves pending memory-log entries before
running the graph. Those pending entries can call `_fetch_returns()` and then
`yf.Ticker(...).history()`. Phase 4 runner tests must use a fresh
`data_cache_dir` per analysis run and disable pending-entry resolution until the
platform owns realized-return backfill. The runtime helper creates a new run
directory and fails closed if it already exists so stale `trading_memory.md`
files cannot be reused silently.

No-network tests must cover both direct yfinance calls and HTTP client paths.
Patch `yfinance.download` and `yfinance.Ticker` to fail fast in agent workflow
tests, and use `pytest-httpx` or `respx` to block market-data hostnames such as
`finance.yahoo.com`, `query1.finance.yahoo.com`, `twelvedata.com`, and
`finnhub.io`. LLM endpoints may be allowed only in explicit integration tests;
market-data hosts remain blocked.

The V1 analyst whitelist intentionally passes only `market`, `news`, and
`fundamentals` to `TradingAgentsGraph`, even though upstream defaults include
`social`. At the pinned commit, the social analyst shares the same `get_news`
tool family as news, so excluding it reduces unwrapped surface area without
losing a unique data source in V1.

At the pinned commit, TradingAgents constructs LLMs internally with
`create_llm_client(provider=config["llm_provider"], model=..., base_url=config.get("backend_url"))`.
Do not try to inject a prebuilt LangChain client object. The Phase 4 adapter
must produce the upstream config keys `llm_provider`, `deep_think_llm`,
`quick_think_llm`, and `backend_url`, and must set the environment variables
the upstream client reads during construction.

For V1, `packages/agents/trading_system_agents/llm_adapter.py` supports:

- `openai`: upstream provider string `openai`; API key from `OPENAI_API_KEY`;
  optional `OPENAI_BASE_URL` and config `backend_url` for a compatible endpoint.
- `ollama`: upstream provider string `ollama`; no OpenAI API key is required;
  base URL comes from config `backend_url` and is also exported as
  `OLLAMA_BASE_URL` for upstream fallback compatibility.

At the pinned commit, `SignalProcessor.process_signal()` is deterministic and
uses `parse_rating()`; it does not make a second LLM call. The runner still
keeps graph execution and signal extraction as separate timeout windows so a
future upstream change or extraction failure can degrade to the baseline signal
while preserving the graph `final_state` for agent reports.

At the pinned commit, `TradingAgentsGraph.propagate()` returns a LangGraph
`AgentState` dict. `packages/agents/trading_system_agents/output_adapter.py`
adapts this dict directly and must not read the `_log_state()` JSON file from
`results_dir`. The real state keys used for V1 reports are:

- `market_report` -> `technical`
- `fundamentals_report` -> `fundamental`
- `news_report` plus optional `sentiment_report` metadata -> `news`
- `investment_debate_state.bull_history` -> `bull`
- `investment_debate_state.bear_history` -> `bear`
- `risk_debate_state.judge_decision` or fallback `risk_debate_state.history`
  -> `risk`
- `final_trade_decision` -> `final`

The risk debate state uses `aggressive_history`, `conservative_history`, and
`neutral_history`; it does not use `risky`/`safe` field names. Output adapters
must use `.get()`/mapping checks for every field. Missing or empty content should
create an `AgentReport` with empty `content_text` and `is_degraded=True`, not a
`KeyError`.

`AgentReport.structured_json` stores adapter-owned summaries, not parsed LLM
JSON. The V1 adapter stores source key, missing flag, extracted key points,
optional confidence, and for final decisions the extracted TradingAgents rating
mapped to this platform's signal label.

At the pinned commit, TradingAgents checkpoint files are created by
`tradingagents/graph/checkpointer.py::_db_path(data_dir, ticker)` at:

```text
{data_cache_dir}/checkpoints/{safe_ticker.upper()}.db
```

The LangGraph `thread_id` is `sha256(f"{ticker.upper()}:{trade_date}")[:16]`
and the checkpoint namespace is the LangGraph default empty string. Store these
as pointer metadata only: checkpoint DB absolute path, thread ID, and namespace.
Do not copy LangGraph checkpoint rows or blobs into this platform's tables.

`clear_checkpoint(data_dir, ticker, date)` deletes rows from the `writes` and
`checkpoints` tables for that thread ID; it does not delete the SQLite DB file.
`clear_all_checkpoints(data_dir)` is the function that unlinks DB files.

Checkpoint cache must be persistent. Do not point `data_cache_dir` at the
Phase 4B per-run directory when `checkpoint_enabled=True`, because a per-run
cleanup would invalidate the pointer. Instead, use a persistent checkpoint/cache
directory for `data_cache_dir` and set `memory_log_path` to the per-run
`memory/trading_memory.md` path so stale memory entries remain isolated.

V1 decision memory is platform-owned. Store reusable lessons in the
`decision_memories` table and inject formatted lessons into the runner config as
`decision_memory_context`. Do not synchronize or reuse upstream
`trading_memory.md` as the durable memory source in V1; that file remains
per-run isolated to prevent stale pending entries from triggering upstream
return-resolution paths.

`packages/agents/trading_system_agents/checkpoint.py` contains the pointer and
checkpoint fallback helper. If checkpoint initialization fails, the runner must
set `checkpoint_enabled=False`, continue the agent run, and record
`checkpoint_skipped=True` plus the skip reason in agent report/run metadata when
the Phase 4 schema exists.

`packages/agents/trading_system_agents/tradingagents_e2e.py` is the Phase 4B
mock E2E seam for wiring runtime dirs, LLM env, checkpoint pointer metadata,
snapshot context, split timeouts, and output adaptation together before a live
TradingAgents dependency is imported. Its path contract is source-driven:
`config["data_cache_dir"]` points at the persistent checkpoint/cache directory,
while `config["memory_log_path"]` and `config["results_dir"]` point inside the
fresh per-run directory. These paths must not collapse to the same directory.

Snapshot context must be set inside the synchronous executor function, not in
the outer async caller. Python `ContextVar` values do not automatically cross
into `ThreadPoolExecutor` worker threads. The E2E runner wraps the graph step
with `run_with_snapshot(snapshot, ...)` inside the worker function so vendor
bridge calls see the active snapshot and the `finally` reset happens in the
same thread.

Mock E2E final decisions must include a parseable TradingAgents rating such as
`**Rating**: Buy`, `**Rating**: Hold`, or `**Rating**: Sell`. The signal path is
deterministic and derives this platform's `BUY`/`HOLD`/`SELL` style label from
the output adapter's final report summary.

TradingAgents can run in the main Python environment if dependency dry-run
checks pass. Its synchronous graph execution must be wrapped with an executor or
worker boundary before exposing it from FastAPI. Checkpoint support should reuse
the upstream LangGraph/SQLite saver and store only checkpoint pointer metadata
in this platform's database.

Executor lifecycle decision for Phase 4: the TradingAgents sync graph executor
is a FastAPI app-lifespan singleton with `max_workers` from settings, defaulting
to 2. It is not per request. Snapshot context isolation must use a
`ContextVar`-style boundary plus a `finally` reset inside the synchronous runner
so reused executor threads cannot leak one ticker's snapshot into another
ticker's analysis. Phase 5 scheduler work must respect this executor capacity.

Phase 4 checkpoint decision: use upstream LangGraph `SqliteSaver` with
`checkpoint_enabled=True` when initialization succeeds, store sqlite path/thread
ID/namespace as pointer metadata, and degrade to `checkpoint_enabled=False` if
initialization fails. The database persistence columns/table are added by the
Phase 4 Alembic migration; until that migration exists, helpers expose
serializable pointer metadata but do not claim durable DB storage.

## Local Development

1. Copy `.env.example` to `.env`.
2. Create and activate a Python virtual environment.
3. Install Python dependencies with `python -m pip install -r requirements-dev.txt`.
4. Install Node dependencies with `npm install`.
5. Run API tests with `npm run test:api`.
6. Run web type checks with `npm run typecheck:web`.

Docker Compose is provided for local Postgres and app services, but Docker must
be installed separately.
