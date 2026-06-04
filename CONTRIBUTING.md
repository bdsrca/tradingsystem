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
`setup.py`, or `setup.cfg` at the checked revision. Docker and Python path
configuration must account for the chosen local source path.

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

## Local Development

1. Copy `.env.example` to `.env`.
2. Create and activate a Python virtual environment.
3. Install Python dependencies with `python -m pip install -r requirements-dev.txt`.
4. Install Node dependencies with `npm install`.
5. Run API tests with `npm run test:api`.
6. Run web type checks with `npm run typecheck:web`.

Docker Compose is provided for local Postgres and app services, but Docker must
be installed separately.
