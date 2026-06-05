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

Before Phase 4 implementation, run a dependency conflict check with Kronos,
TradingAgents, LangGraph, LangChain, pandas, yfinance, FastAPI, and this
repository's own dependencies enabled together. TradingAgents internal external
data calls must be inventoried and wrapped or disabled before analyst workflow
tests run.

At the pinned commit, TradingAgents exposes `VENDOR_METHODS` and
`route_to_vendor()` in `tradingagents/dataflows/interface.py`. Phase 4 should
prefer registering a platform vendor there so analyst tools read this
platform's frozen data snapshot instead of monkey-patching broad internals.

Known direct yfinance escape paths at the pinned commit:

- `tradingagents/graph/trading_graph.py::_fetch_returns()`
- `tradingagents/graph/trading_graph.py` calls `resolve_instrument_identity()`
- `tradingagents/agents/utils/agent_utils.py::resolve_instrument_identity()` calls `yf.Ticker(...).info`

The Phase 4 default is no live market-data network calls during an agent run.
Tests should fail if yfinance or another external market-data source is reached
outside the platform snapshot. Company identity can fail open to stored metadata
or an empty value, but it should not silently perform live network lookup by
default.

No-network tests must cover both direct yfinance calls and HTTP client paths.
Patch `yfinance.download` and `yfinance.Ticker` to fail fast in agent workflow
tests, and use `pytest-httpx` or `respx` to block market-data hostnames such as
`finance.yahoo.com`, `query1.finance.yahoo.com`, `twelvedata.com`, and
`finnhub.io`. LLM endpoints may be allowed only in explicit integration tests;
market-data hosts remain blocked.

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

Phase 4 must choose one checkpoint path before implementation starts:

- Enable upstream LangGraph `SqliteSaver`, set `checkpoint_enabled=True`, store
  sqlite path/thread ID as database pointer metadata, and test that the pointer
  is written and readable.
- Or defer checkpoint pointer support to Phase 6, keep `checkpoint_enabled=False`,
  and remove checkpoint completion claims from Phase 4 verification.

## Local Development

1. Copy `.env.example` to `.env`.
2. Create and activate a Python virtual environment.
3. Install Python dependencies with `python -m pip install -r requirements-dev.txt`.
4. Install Node dependencies with `npm install`.
5. Run API tests with `npm run test:api`.
6. Run web type checks with `npm run typecheck:web`.

Docker Compose is provided for local Postgres and app services, but Docker must
be installed separately.
