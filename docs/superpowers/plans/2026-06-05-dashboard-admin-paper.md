# Dashboard Admin Paper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the V1 split decision dashboard, admin console, and paper overview described in `docs/superpowers/specs/2026-06-05-dashboard-admin-design.md`.

**Architecture:** Add small FastAPI aggregation routers for dashboard, admin, and paper overview. Keep sensitive secrets in environment variables; persist only non-secret runtime settings in `app_settings`. Use a process-local dashboard summary TTL cache for V1 and clear it after daily/admin actions.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, APScheduler hooks, existing quant/paper/outcome services, Next.js App Router, TypeScript, existing CSS system.

---

## File Structure

Create:

- `apps/api/alembic/versions/0010_admin_settings_health.py`: extends `app_settings`, creates `service_health_checks`.
- `apps/api/trading_system_api/dashboard_cache.py`: process-local TTL cache helpers and cache invalidation.
- `apps/api/trading_system_api/dashboard_service.py`: dashboard summary aggregation.
- `apps/api/trading_system_api/admin_service.py`: settings read/update, secret masking, health upsert, health checks.
- `apps/api/trading_system_api/routers/dashboard.py`: `/dashboard/summary`.
- `apps/api/trading_system_api/routers/admin.py`: admin settings, health, and actions.
- `apps/web/components/AppNav.tsx`: shared primary navigation.
- `apps/web/app/dashboard/page.tsx`: decision dashboard.
- `apps/web/app/paper/page.tsx`: paper overview.
- `apps/web/app/admin/page.tsx`: admin console.
- `apps/api/tests/test_dashboard_api.py`: dashboard summary and cache tests.
- `apps/api/tests/test_admin_api.py`: admin settings/action API tests.
- `apps/api/tests/test_admin_schema.py`: model-level schema tests.
- `apps/api/tests/test_admin_migration.py`: Alembic migration tests.
- `apps/api/tests/test_paper_overview_api.py`: paper overview API tests.

Modify:

- `apps/api/trading_system_api/models.py`: add `ServiceHealthCheck`; extend `AppSettings`.
- `apps/api/trading_system_api/schemas.py`: add dashboard, admin, and paper overview response models.
- `apps/api/trading_system_api/main.py`: include dashboard and admin routers.
- `apps/api/trading_system_api/routers/daily.py`: clear dashboard cache after manual daily run.
- `apps/api/trading_system_api/routers/paper.py`: add `/paper/overview` before the existing `/{symbol}/latest` and `/{symbol}/run` routes.
- `apps/web/lib/api.ts`: add dashboard, admin, and paper overview TypeScript types.
- `apps/web/app/page.tsx`: root overview with `Open Dashboard`.
- `apps/web/app/watchlist/page.tsx`: use shared nav.
- `apps/web/app/daily/page.tsx`: use shared nav.
- `apps/web/app/accuracy/page.tsx`: use shared nav.
- `apps/web/app/stock/[ticker]/page.tsx`: use shared nav.
- `apps/web/app/paper/[ticker]/page.tsx`: use shared nav.
- `apps/web/app/globals.css`: add compact dashboard/admin layout classes only when existing classes are insufficient.

Do not create encrypted secret storage in this plan. Do not build the polished dashboard visual phase in this plan.

---

## Task 1: Shared Navigation And Root Overview

**Files:**

- Create: `apps/web/components/AppNav.tsx`
- Modify: `apps/web/app/page.tsx`
- Modify: `apps/web/app/watchlist/page.tsx`
- Modify: `apps/web/app/daily/page.tsx`
- Modify: `apps/web/app/accuracy/page.tsx`
- Modify: `apps/web/app/stock/[ticker]/page.tsx`
- Modify: `apps/web/app/paper/[ticker]/page.tsx`
- Modify: `apps/web/app/globals.css`

- [ ] **Step 1: Create shared navigation component**

Create `apps/web/components/AppNav.tsx`:

```tsx
import Link from "next/link";

type AppNavProps = {
  className?: string;
};

const links = [
  { href: "/watchlist", label: "Watchlist", tone: "normal" },
  { href: "/dashboard", label: "Dashboard", tone: "normal" },
  { href: "/paper", label: "Paper", tone: "normal" },
  { href: "/accuracy", label: "Accuracy", tone: "normal" },
  { href: "/admin", label: "Admin", tone: "muted" }
] as const;

export default function AppNav({ className }: AppNavProps) {
  return (
    <nav className={className ?? "link-row"} aria-label="Primary navigation">
      {links.map((link) => (
        <Link
          className={link.tone === "muted" ? "text-link nav-muted" : "text-link"}
          href={link.href}
          key={link.href}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
```

- [ ] **Step 2: Add low-weight Admin nav styling**

Patch `apps/web/app/globals.css`:

```css
.nav-muted {
  color: var(--muted);
  margin-left: auto;
}
```

If `.link-row` already wraps, keep `margin-left: auto`; it works on wide screens and naturally wraps on narrow screens.

- [ ] **Step 3: Replace page-specific nav links with `AppNav`**

For each page listed in this task, import `AppNav` and replace the manual nav block.

Example for `apps/web/app/watchlist/page.tsx`:

```tsx
import AppNav from "../../components/AppNav";
```

Delete the entire page-specific `<nav className="link-row">` block and replace it with:

```tsx
<AppNav />
```

Use relative import paths:

- `../../components/AppNav` from `watchlist`, `daily`, `accuracy`.
- `../../../components/AppNav` from `stock/[ticker]` and `paper/[ticker]`.
- `../components/AppNav` from root `page.tsx`.

- [ ] **Step 4: Convert root route to lightweight overview**

Modify `apps/web/app/page.tsx` so it keeps a small overview and a prominent dashboard action:

The root route `/` remains a lightweight overview page and does not redirect.

```tsx
import Link from "next/link";

import AppNav from "../components/AppNav";

export default function Home() {
  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>Trading System</h1>
          <p>Local-first US and Canadian equity signal platform.</p>
        </div>
        <AppNav />
      </header>

      <section className="paper-grid" aria-label="Overview">
        <article className="paper-panel">
          <h2>Today's Summary</h2>
          <p className="muted">Open the dashboard for latest signals, data health, and watchlist scan.</p>
          <div className="action-row">
            <Link className="button-link" href="/dashboard">
              Open Dashboard
            </Link>
          </div>
        </article>
      </section>
    </main>
  );
}
```

Add `.button-link` to `globals.css`:

```css
.button-link {
  background: var(--accent);
  border-radius: 6px;
  color: #fff;
  display: inline-flex;
  font-size: 14px;
  font-weight: 700;
  padding: 10px 14px;
  text-decoration: none;
}
```

- [ ] **Step 5: Verify TypeScript and build**

Run:

```powershell
rtk npm run typecheck:web
rtk npm run build:web
```

Expected:

- TypeScript exits 0.
- Build route list still includes `/`, `/watchlist`, `/daily`, `/accuracy`, `/paper/[ticker]`, and `/stock/[ticker]`.

- [ ] **Step 6: Commit**

```powershell
git add apps/web/components/AppNav.tsx apps/web/app apps/web/app/globals.css
git commit -m "Add shared navigation shell"
```

---

## Task 2: Dashboard Summary API And Page

**Files:**

- Create: `apps/api/trading_system_api/dashboard_cache.py`
- Create: `apps/api/trading_system_api/dashboard_service.py`
- Create: `apps/api/trading_system_api/routers/dashboard.py`
- Create: `apps/api/tests/test_dashboard_api.py`
- Create: `apps/web/app/dashboard/page.tsx`
- Modify: `apps/api/trading_system_api/schemas.py`
- Modify: `apps/api/trading_system_api/main.py`
- Modify: `apps/api/trading_system_api/routers/daily.py`
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/app/globals.css`

- [ ] **Step 1: Write failing dashboard API tests**

Create `apps/api/tests/test_dashboard_api.py`:

```python
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from trading_system_api.dashboard_cache import clear_dashboard_summary_cache
from trading_system_api.database import Base, get_session
from trading_system_api.main import create_app
from trading_system_api.models import (
    DailyWorkerRun,
    DailyWorkerTickerResult,
    Signal,
    SignalOutcome,
    WatchlistItem,
)


@pytest.mark.anyio
async def test_dashboard_summary_orders_attention_and_reports_cache() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with Session() as session:
        watch = WatchlistItem(
            ticker="AAPL",
            exchange="NASDAQ",
            market="US",
            provider_symbol="AAPL",
            display_name="Apple",
        )
        run = DailyWorkerRun(triggered_by="manual", status="completed")
        session.add_all([watch, run])
        await session.flush()
        session.add(
            DailyWorkerTickerResult(
                worker_run_id=run.id,
                watchlist_item_id=watch.id,
                ticker="AAPL",
                exchange="NASDAQ",
                market="US",
                status="failed",
                data_freshness="no_data",
                signal=None,
                confidence=None,
                error_message="provider returned no bars",
            )
        )
        await session.commit()

    app = create_app()
    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    clear_dashboard_summary_cache()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.get("/dashboard/summary?max_age_seconds=30")
        second = await client.get("/dashboard/summary?max_age_seconds=30")

    assert first.status_code == 200
    assert first.json()["cache_hit"] is False
    assert second.json()["cache_hit"] is True
    item = first.json()["attention_items"][0]
    assert item["ticker"] == "AAPL"
    assert item["severity"] == "error"
    assert "no data" in item["reason"].lower()


@pytest.mark.anyio
async def test_dashboard_summary_accuracy_excludes_backfilled_by_default() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with Session() as session:
        signal = Signal(
            ticker="AAPL",
            exchange="NASDAQ",
            analysis_date=datetime(2026, 6, 1, tzinfo=UTC).date(),
            signal="BUY",
            confidence=0.9,
            created_at=datetime(2026, 6, 20, tzinfo=UTC),
        )
        session.add(signal)
        await session.flush()
        session.add(
            SignalOutcome(
                signal_id=signal.id,
                ticker="AAPL",
                exchange="NASDAQ",
                horizon_days=20,
                target_date=datetime(2026, 6, 30, tzinfo=UTC).date(),
                realized_price=100,
                realized_return_pct=12,
                realized_outcome="win",
                evaluation_eligibility="backfilled",
                lag_days=19,
            )
        )
        await session.commit()

    app = create_app()
    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    clear_dashboard_summary_cache()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/dashboard/summary?force_refresh=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["accuracy_snapshot"]["evaluated_count"] == 0
    assert payload["accuracy_snapshot"]["backfilled_excluded_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
rtk proxy .\.venv\Scripts\python.exe -m pytest apps\api\tests\test_dashboard_api.py -q
```

Expected:

- Fails with `ModuleNotFoundError: trading_system_api.dashboard_cache` or 404 for `/dashboard/summary`.

- [ ] **Step 3: Add dashboard schemas**

Modify `apps/api/trading_system_api/schemas.py`:

```python
class DashboardLatestRunRead(BaseModel):
    id: str | None
    status: str
    started_at: datetime | None
    succeeded_count: int
    failed_count: int
    skipped_count: int
    stale_count: int
    degraded_count: int
    email_sent: bool


class DashboardAttentionItemRead(BaseModel):
    ticker: str
    exchange: str
    severity: str
    reason: str
    signal: str | None
    confidence: float | None
    href: str


class DashboardWatchlistRowRead(BaseModel):
    ticker: str
    exchange: str
    market: str
    display_name: str | None
    latest_signal: str | None
    confidence: float | None
    data_freshness: str
    last_analyzed_at: datetime | None
    accuracy_20d_win_rate_pct: float | None
    paper_1y_return_pct: float | None
    paper_1y_max_drawdown_pct: float | None
    caveat: str | None


class DashboardAccuracySnapshotRead(BaseModel):
    window: int
    evaluated_count: int
    win_rate_pct: float
    average_return_pct: float
    backfilled_excluded_count: int


class DashboardSummaryRead(BaseModel):
    latest_run: DashboardLatestRunRead | None
    attention_items: list[DashboardAttentionItemRead]
    watchlist_rows: list[DashboardWatchlistRowRead]
    accuracy_snapshot: DashboardAccuracySnapshotRead
    paper_snapshot: dict
    service_warnings: list[str]
    generated_at: datetime
    cache_hit: bool
```

- [ ] **Step 4: Implement TTL cache helper**

Create `apps/api/trading_system_api/dashboard_cache.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass
class DashboardCacheEntry:
    key: tuple[str]
    value: dict[str, Any]
    expires_at: datetime


_entry: DashboardCacheEntry | None = None


def get_cached_dashboard_summary(key: tuple[str]) -> dict[str, Any] | None:
    if _entry is None:
        return None
    if _entry.key != key:
        return None
    if datetime.now(UTC) >= _entry.expires_at:
        return None
    cached = dict(_entry.value)
    cached["cache_hit"] = True
    return cached


def set_cached_dashboard_summary(
    key: tuple[str],
    value: dict[str, Any],
    *,
    max_age_seconds: int,
) -> dict[str, Any]:
    global _entry
    fresh = dict(value)
    fresh["cache_hit"] = False
    _entry = DashboardCacheEntry(
        key=key,
        value=fresh,
        expires_at=datetime.now(UTC) + timedelta(seconds=max_age_seconds),
    )
    return fresh


def clear_dashboard_summary_cache() -> None:
    global _entry
    _entry = None
```

- [ ] **Step 5: Implement dashboard service**

Create `apps/api/trading_system_api/dashboard_service.py`.

Key functions and signatures:

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.models import (
    DailyWorkerRun,
    DailyWorkerTickerResult,
    PaperSimulationRun,
    Signal,
    SignalOutcome,
    WatchlistItem,
)


async def build_dashboard_summary(session: AsyncSession) -> dict:
    latest_run = (
        await session.execute(select(DailyWorkerRun).order_by(desc(DailyWorkerRun.started_at)).limit(1))
    ).scalar_one_or_none()
    latest_results = await _latest_daily_results(session, latest_run.id if latest_run else None)
    rows = await _watchlist_rows(session, latest_results)
    attention = _attention_items(rows, latest_results)
    accuracy = await _accuracy_snapshot(session)
    return {
        "latest_run": _latest_run_payload(latest_run),
        "attention_items": attention,
        "watchlist_rows": rows,
        "accuracy_snapshot": accuracy,
        "paper_snapshot": {"window_years": 1},
        "service_warnings": _service_warnings(rows),
        "generated_at": datetime.now(UTC),
        "cache_hit": False,
    }
```

Implementation details:

- `_latest_daily_results()` returns latest run ticker results keyed by `(ticker, exchange)`.
- `_watchlist_rows()` selects enabled watchlist rows and joins latest signal by querying non-superseded `Signal` ordered by `created_at desc`.
- `_watchlist_rows()` selects latest 1Y `PaperSimulationRun` per ticker/exchange and reads `metrics.total_return_pct` and `metrics.max_drawdown_pct`.
- `_accuracy_snapshot()` selects `SignalOutcome` where `horizon_days == 20` and `evaluation_eligibility != "backfilled"`.
- `_attention_items()` emits severity `error` for failed/no_data, `warning` for degraded/stale, `signal` for confidence `>= 0.7` and signal in `BUY`, `SELL`, `REDUCE`.

- [ ] **Step 6: Add dashboard router and include it**

Create `apps/api/trading_system_api/routers/dashboard.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.dashboard_cache import (
    get_cached_dashboard_summary,
    set_cached_dashboard_summary,
)
from trading_system_api.dashboard_service import build_dashboard_summary
from trading_system_api.database import get_session
from trading_system_api.schemas import DashboardSummaryRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryRead)
async def dashboard_summary(
    max_age_seconds: int = 30,
    force_refresh: bool = False,
    session: AsyncSession = Depends(get_session),
) -> DashboardSummaryRead:
    max_age_seconds = max(0, min(max_age_seconds, 300))
    key = ("summary",)
    if not force_refresh and max_age_seconds > 0:
        cached = get_cached_dashboard_summary(key)
        if cached is not None:
            return DashboardSummaryRead(**cached)
    payload = await build_dashboard_summary(session)
    if max_age_seconds > 0:
        payload = set_cached_dashboard_summary(key, payload, max_age_seconds=max_age_seconds)
    return DashboardSummaryRead(**payload)
```

Modify `apps/api/trading_system_api/main.py`:

```python
from trading_system_api.routers import analysis, daily, dashboard, kronos, market_data, paper, signals, watchlist
```

and include:

```python
app.include_router(dashboard.router)
```

- [ ] **Step 7: Clear dashboard cache after manual daily run**

Modify `apps/api/trading_system_api/routers/daily.py`.

Import:

```python
from trading_system_api.dashboard_cache import clear_dashboard_summary_cache
```

After the awaited `run_daily_analysis` call completes in `run_daily_now`, call:

```python
clear_dashboard_summary_cache()
```

- [ ] **Step 8: Run dashboard API tests**

Run:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
rtk proxy .\.venv\Scripts\python.exe -m pytest apps\api\tests\test_dashboard_api.py -q
```

Expected:

- Both dashboard tests pass.

- [ ] **Step 9: Add frontend types and dashboard page**

Modify `apps/web/lib/api.ts`:

```ts
export type DashboardSummary = {
  latest_run: {
    id: string | null;
    status: string;
    started_at: string | null;
    succeeded_count: number;
    failed_count: number;
    skipped_count: number;
    stale_count: number;
    degraded_count: number;
    email_sent: boolean;
  } | null;
  attention_items: Array<{
    ticker: string;
    exchange: string;
    severity: string;
    reason: string;
    signal: string | null;
    confidence: number | null;
    href: string;
  }>;
  watchlist_rows: Array<{
    ticker: string;
    exchange: string;
    market: string;
    display_name: string | null;
    latest_signal: string | null;
    confidence: number | null;
    data_freshness: string;
    last_analyzed_at: string | null;
    accuracy_20d_win_rate_pct: number | null;
    paper_1y_return_pct: number | null;
    paper_1y_max_drawdown_pct: number | null;
    caveat: string | null;
  }>;
  accuracy_snapshot: {
    window: number;
    evaluated_count: number;
    win_rate_pct: number;
    average_return_pct: number;
    backfilled_excluded_count: number;
  };
  paper_snapshot: Record<string, unknown>;
  service_warnings: string[];
  generated_at: string;
  cache_hit: boolean;
};
```

Create `apps/web/app/dashboard/page.tsx` as a client component that:

- Fetches `/dashboard/summary?max_age_seconds=30`.
- Has a `Refresh` button that fetches `/dashboard/summary?force_refresh=true`.
- Renders top metric cards, attention table, and watchlist scan table.
- Uses `AppNav`.

- [ ] **Step 10: Add small dashboard CSS only if needed**

If the page needs severity labels, add:

```css
.severity {
  border-radius: 999px;
  display: inline-block;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 8px;
}

.severity-error {
  background: #fde8e4;
  color: #b42318;
}

.severity-warning {
  background: #fff4d8;
  color: #8a5a00;
}

.severity-signal {
  background: #e7f6ef;
  color: #1f7a5c;
}
```

- [ ] **Step 11: Verify API, lint, typecheck, build**

Run:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
rtk proxy .\.venv\Scripts\python.exe -m pytest apps\api\tests\test_dashboard_api.py apps\api\tests\test_daily_api.py -q
rtk proxy .\.venv\Scripts\python.exe -m ruff check apps packages workers infra
rtk npm run typecheck:web
rtk npm run build:web
```

Expected:

- Tests pass.
- Ruff exits 0.
- `/dashboard` appears in the Next.js route list.

- [ ] **Step 12: Commit**

```powershell
git add apps/api/trading_system_api/dashboard_cache.py apps/api/trading_system_api/dashboard_service.py apps/api/trading_system_api/routers/dashboard.py apps/api/trading_system_api/main.py apps/api/trading_system_api/routers/daily.py apps/api/trading_system_api/schemas.py apps/api/tests/test_dashboard_api.py apps/web/lib/api.ts apps/web/app/dashboard/page.tsx apps/web/app/globals.css
git commit -m "Add dashboard summary"
```

---

## Task 3: Paper Overview API And Page

**Files:**

- Create: `apps/api/tests/test_paper_overview_api.py`
- Create: `apps/web/app/paper/page.tsx`
- Modify: `apps/api/trading_system_api/routers/paper.py`
- Modify: `apps/api/trading_system_api/schemas.py`
- Modify: `apps/web/lib/api.ts`

- [ ] **Step 1: Write failing paper overview API test**

Create `apps/api/tests/test_paper_overview_api.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from trading_system_api.database import Base, get_session
from trading_system_api.main import create_app
from trading_system_api.models import PaperSimulationRun, WatchlistItem


@pytest.mark.anyio
async def test_paper_overview_returns_latest_runs_and_empty_state() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with Session() as session:
        session.add_all(
            [
                WatchlistItem(ticker="AAPL", exchange="NASDAQ", market="US", provider_symbol="AAPL"),
                WatchlistItem(ticker="WELL", exchange="TSX", market="CA", provider_symbol="WELL:TSX"),
            ]
        )
        session.add(
            PaperSimulationRun(
                ticker="AAPL",
                exchange="NASDAQ",
                window_years=1,
                initial_capital=100000,
                position_size_pct=0.05,
                max_positions=10,
                max_holding_days=30,
                signal_snapshot={"signal_ids": ["s1"]},
                metrics={
                    "total_return_pct": 12.5,
                    "max_drawdown_pct": -4.2,
                    "win_rate_pct": 60.0,
                    "trade_count": 5,
                },
            )
        )
        await session.commit()

    app = create_app()
    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/paper/overview")

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["one_year"]["status"] == "simulated"
    assert rows[0]["one_year"]["total_return_pct"] == 12.5
    assert rows[1]["ticker"] == "WELL"
    assert rows[1]["one_year"]["status"] == "not_simulated"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
rtk proxy .\.venv\Scripts\python.exe -m pytest apps\api\tests\test_paper_overview_api.py -q
```

Expected:

- Fails with 404 for `/paper/overview` or missing schema.

- [ ] **Step 3: Add paper overview schemas**

Modify `apps/api/trading_system_api/schemas.py`:

```python
class PaperOverviewWindowRead(BaseModel):
    status: str
    total_return_pct: float | None
    max_drawdown_pct: float | None
    win_rate_pct: float | None
    trade_count: int | None
    simulation_run_id: str | None
    created_at: datetime | None


class PaperOverviewRowRead(BaseModel):
    ticker: str
    exchange: str
    market: str
    display_name: str | None
    one_year: PaperOverviewWindowRead
    two_year: PaperOverviewWindowRead
    three_year: PaperOverviewWindowRead


class PaperOverviewRead(BaseModel):
    rows: list[PaperOverviewRowRead]
```

- [ ] **Step 4: Add `/paper/overview` route before dynamic routes**

Modify `apps/api/trading_system_api/routers/paper.py`.

Place this route above the existing `@router.get("/{symbol}/latest", response_model=PaperRunRead)` route:

```python
@router.get("/overview", response_model=PaperOverviewRead)
async def get_paper_overview(session: AsyncSession = Depends(get_session)) -> PaperOverviewRead:
    watchlist = (
        await session.execute(select(WatchlistItem).where(WatchlistItem.enabled.is_(True)).order_by(WatchlistItem.ticker))
    ).scalars().all()
    rows = []
    for item in watchlist:
        rows.append(
            PaperOverviewRowRead(
                ticker=item.ticker,
                exchange=item.exchange,
                market=item.market,
                display_name=item.display_name,
                one_year=await _latest_paper_window(session, item, 1),
                two_year=await _latest_paper_window(session, item, 2),
                three_year=await _latest_paper_window(session, item, 3),
            )
        )
    return PaperOverviewRead(rows=rows)
```

Add helper:

```python
async def _latest_paper_window(
    session: AsyncSession,
    item: WatchlistItem,
    window_years: int,
) -> PaperOverviewWindowRead:
    run = (
        await session.execute(
            select(PaperSimulationRun)
            .where(
                PaperSimulationRun.ticker == item.ticker,
                PaperSimulationRun.exchange == item.exchange,
                PaperSimulationRun.window_years == window_years,
            )
            .order_by(desc(PaperSimulationRun.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if run is None:
        return PaperOverviewWindowRead(
            status="not_simulated",
            total_return_pct=None,
            max_drawdown_pct=None,
            win_rate_pct=None,
            trade_count=None,
            simulation_run_id=None,
            created_at=None,
        )
    metrics = run.metrics or {}
    return PaperOverviewWindowRead(
        status="simulated",
        total_return_pct=metrics.get("total_return_pct"),
        max_drawdown_pct=metrics.get("max_drawdown_pct"),
        win_rate_pct=metrics.get("win_rate_pct"),
        trade_count=metrics.get("trade_count"),
        simulation_run_id=run.id,
        created_at=run.created_at,
    )
```

Add these imports:

```python
from sqlalchemy import desc, select
from trading_system_api.models import WatchlistItem
from trading_system_api.schemas import PaperOverviewRead, PaperOverviewRowRead, PaperOverviewWindowRead
```

- [ ] **Step 5: Run paper overview API test**

Run:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
rtk proxy .\.venv\Scripts\python.exe -m pytest apps\api\tests\test_paper_overview_api.py apps\api\tests\test_phase2_api.py -q
```

Expected:

- Paper overview test passes.
- Existing per-ticker paper tests still pass, proving `/paper/overview` did not get captured as a `{symbol}`.

- [ ] **Step 6: Add frontend type and page**

Modify `apps/web/lib/api.ts`:

```ts
export type PaperOverviewWindow = {
  status: string;
  total_return_pct: number | null;
  max_drawdown_pct: number | null;
  win_rate_pct: number | null;
  trade_count: number | null;
  simulation_run_id: string | null;
  created_at: string | null;
};

export type PaperOverview = {
  rows: Array<{
    ticker: string;
    exchange: string;
    market: string;
    display_name: string | null;
    one_year: PaperOverviewWindow;
    two_year: PaperOverviewWindow;
    three_year: PaperOverviewWindow;
  }>;
};
```

Create `apps/web/app/paper/page.tsx`:

- Client component.
- Fetch `/paper/overview`.
- Render table with ticker, 1Y return, 1Y drawdown, 1Y win rate, 2Y return, 3Y return, trade count, detail link.
- Use `AppNav`.
- Empty state: `No paper simulations yet.`

- [ ] **Step 7: Verify frontend and commit**

Run:

```powershell
rtk npm run typecheck:web
rtk npm run build:web
```

Expected:

- `/paper` appears as a static route.
- `/paper/[ticker]` remains dynamic.

Commit:

```powershell
git add apps/api/trading_system_api/routers/paper.py apps/api/trading_system_api/schemas.py apps/api/tests/test_paper_overview_api.py apps/web/lib/api.ts apps/web/app/paper/page.tsx
git commit -m "Add paper overview"
```

---

## Task 4: Admin Settings And Health Schema

**Files:**

- Create: `apps/api/alembic/versions/0010_admin_settings_health.py`
- Create: `apps/api/trading_system_api/admin_service.py`
- Create: `apps/api/trading_system_api/routers/admin.py`
- Create: `apps/api/tests/test_admin_schema.py`
- Create: `apps/api/tests/test_admin_migration.py`
- Create: `apps/api/tests/test_admin_api.py`
- Create: `apps/web/app/admin/page.tsx`
- Modify: `apps/api/trading_system_api/models.py`
- Modify: `apps/api/trading_system_api/schemas.py`
- Modify: `apps/api/trading_system_api/main.py`
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/app/globals.css`

- [ ] **Step 1: Write failing schema test**

Create `apps/api/tests/test_admin_schema.py`:

```python
from sqlalchemy import CheckConstraint, UniqueConstraint

from trading_system_api.models import AppSettings, Base, ServiceHealthCheck


def test_admin_settings_columns_exist() -> None:
    columns = AppSettings.__table__.columns
    for name in [
        "provider_preference",
        "llm_provider_type",
        "llm_base_url",
        "llm_model_name",
        "tradingagents_enabled",
        "max_debate_rounds",
        "max_risk_discuss_rounds",
        "smtp_host",
        "smtp_port",
        "smtp_user",
        "smtp_from",
        "smtp_to",
        "daily_digest_enabled",
        "strong_signal_alert_threshold",
        "kronos_enabled",
    ]:
        assert name in columns


def test_service_health_checks_schema() -> None:
    assert ServiceHealthCheck.__tablename__ == "service_health_checks"
    assert "service_health_checks" in Base.metadata.tables
    constraints = ServiceHealthCheck.__table__.constraints
    assert any(
        isinstance(constraint, UniqueConstraint)
        and set(constraint.columns.keys()) == {"service_name"}
        for constraint in constraints
    )
    assert any(
        isinstance(constraint, CheckConstraint)
        and "status" in str(constraint.sqltext)
        for constraint in constraints
    )
```

- [ ] **Step 2: Run schema test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
rtk proxy .\.venv\Scripts\python.exe -m pytest apps\api\tests\test_admin_schema.py -q
```

Expected:

- Fails with `ImportError: ServiceHealthCheck` or missing columns.

- [ ] **Step 3: Extend models**

Modify `apps/api/trading_system_api/models.py`.

Add to `AppSettings`:

```python
provider_preference: Mapped[str] = mapped_column(String(32), default="twelve_data", nullable=False)
llm_provider_type: Mapped[str] = mapped_column(String(32), default="ollama", nullable=False)
llm_base_url: Mapped[str | None] = mapped_column(String(255))
llm_model_name: Mapped[str | None] = mapped_column(String(128))
tradingagents_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
max_debate_rounds: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
max_risk_discuss_rounds: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
smtp_host: Mapped[str | None] = mapped_column(String(255))
smtp_port: Mapped[int] = mapped_column(Integer, default=587, nullable=False)
smtp_user: Mapped[str | None] = mapped_column(String(255))
smtp_from: Mapped[str | None] = mapped_column(String(255))
smtp_to: Mapped[str | None] = mapped_column(String(255))
daily_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
strong_signal_alert_threshold: Mapped[float] = mapped_column(Numeric(5, 4), default=0.7, nullable=False)
kronos_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

Add model:

```python
class ServiceHealthCheck(Base):
    __tablename__ = "service_health_checks"
    __table_args__ = (
        UniqueConstraint("service_name", name="uq_service_health_checks_service_name"),
        CheckConstraint(
            "service_name IN ('api', 'db', 'kronos', 'email', 'data_provider')",
            name="ck_service_health_checks_service_name",
        ),
        CheckConstraint(
            "status IN ('ok', 'degraded', 'unreachable')",
            name="ck_service_health_checks_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    service_name: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
```

- [ ] **Step 4: Add Alembic migration and migration test**

Create `apps/api/alembic/versions/0010_admin_settings_health.py` with `down_revision = "0009_phase7"`.

Upgrade:

- Add nullable or server-defaulted `app_settings` columns listed in Step 3.
- Create `service_health_checks` table with constraints.

Downgrade:

- Drop `service_health_checks`.
- Drop added `app_settings` columns.

Create `apps/api/tests/test_admin_migration.py`:

```python
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_admin_alembic_upgrade_preserves_existing_settings(tmp_path: Path) -> None:
    db_path = tmp_path / "admin.db"
    url = f"sqlite:///{db_path}"
    config = Config("apps/api/alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "0009_phase7")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO app_settings (id, scheduler_enabled, scheduler_timezone, daily_trigger_hour, daily_trigger_minute, daily_kronos_enabled, daily_email_enabled, email_debounce_days, created_at, updated_at) "
                "VALUES ('settings', 0, 'America/Toronto', 17, 0, 0, 0, 7, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
    command.upgrade(config, "head")
    inspector = inspect(engine)
    assert "service_health_checks" in inspector.get_table_names()
    settings_columns = {column["name"] for column in inspector.get_columns("app_settings")}
    assert "llm_provider_type" in settings_columns
    with engine.connect() as conn:
        value = conn.execute(text("SELECT llm_provider_type FROM app_settings WHERE id='settings'")).scalar_one()
    assert value == "ollama"
```

- [ ] **Step 5: Run schema and migration tests**

Run:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
rtk proxy .\.venv\Scripts\python.exe -m pytest apps\api\tests\test_admin_schema.py apps\api\tests\test_admin_migration.py -q
```

Expected:

- Tests pass after model and migration implementation.

- [ ] **Step 6: Write failing admin API tests**

Append to `apps/api/tests/test_admin_api.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from trading_system_api.database import Base, get_session
from trading_system_api.main import create_app
from trading_system_api.models import AppSettings, ServiceHealthCheck


@pytest.mark.anyio
async def test_admin_settings_patch_saves_non_secret_and_masks_secrets(monkeypatch) -> None:
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "secret-key")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()
    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/admin/settings",
            json={
                "llm_provider_type": "ollama",
                "llm_base_url": "http://127.0.0.1:11434",
                "llm_model_name": "qwen3:8b",
                "twelve_data_api_key": "must-not-save",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert "twelve_data_api_key" not in payload
    assert payload["secrets"]["twelve_data_api_key"] == "configured"
    async with Session() as session:
        row = (await session.execute(select(AppSettings))).scalar_one()
        assert row.llm_model_name == "qwen3:8b"


@pytest.mark.anyio
async def test_admin_health_upserts_one_row_per_service() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()
    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.get("/admin/health")
        second = await client.get("/admin/health")

    assert first.status_code == 200
    assert second.status_code == 200
    async with Session() as session:
        rows = (await session.execute(select(ServiceHealthCheck))).scalars().all()
        assert len({row.service_name for row in rows}) == len(rows)
```

- [ ] **Step 7: Run admin API tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
rtk proxy .\.venv\Scripts\python.exe -m pytest apps\api\tests\test_admin_api.py -q
```

Expected:

- Fails with 404 for `/admin/settings` or `/admin/health`.

- [ ] **Step 8: Add admin schemas**

Modify `apps/api/trading_system_api/schemas.py`:

```python
class AdminSecretsRead(BaseModel):
    twelve_data_api_key: str
    remote_llm_api_key: str
    smtp_password: str


class AdminSettingsRead(BaseModel):
    provider_preference: str
    llm_provider_type: str
    llm_base_url: str | None
    llm_model_name: str | None
    tradingagents_enabled: bool
    max_debate_rounds: int
    max_risk_discuss_rounds: int
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_from: str | None
    smtp_to: str | None
    daily_digest_enabled: bool
    strong_signal_alert_threshold: float
    scheduler_enabled: bool
    daily_trigger_hour: int
    daily_trigger_minute: int
    scheduler_timezone: str
    kronos_enabled: bool
    email_debounce_days: int
    secrets: AdminSecretsRead


class AdminSettingsUpdate(BaseModel):
    provider_preference: str | None = None
    llm_provider_type: str | None = None
    llm_base_url: str | None = None
    llm_model_name: str | None = None
    tradingagents_enabled: bool | None = None
    max_debate_rounds: int | None = None
    max_risk_discuss_rounds: int | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_from: str | None = None
    smtp_to: str | None = None
    daily_digest_enabled: bool | None = None
    strong_signal_alert_threshold: float | None = None
    scheduler_enabled: bool | None = None
    daily_trigger_hour: int | None = None
    daily_trigger_minute: int | None = None
    scheduler_timezone: str | None = None
    kronos_enabled: bool | None = None
    email_debounce_days: int | None = None

    model_config = {"extra": "forbid"}


class ServiceHealthRead(BaseModel):
    service_name: str
    status: str
    checked_at: datetime
    latency_ms: int | None
    details_json: dict


class AdminHealthRead(BaseModel):
    services: list[ServiceHealthRead]
```

- [ ] **Step 9: Implement admin service**

Create `apps/api/trading_system_api/admin_service.py`.

Implement:

- `async get_or_create_app_settings(session) -> AppSettings`
- `settings_to_read(row, settings: Settings) -> AdminSettingsRead`
- `async update_app_settings(session, payload, settings) -> AdminSettingsRead`
- `async upsert_service_health(session, service_name, status, latency_ms=None, details=None) -> ServiceHealthCheck`
- `async collect_admin_health(session, settings) -> AdminHealthRead`

Secret status helper:

```python
def _secret_status(value: str | None) -> str:
    return "configured" if value else "missing"
```

Map env secrets:

- `twelve_data_api_key`: `settings.twelve_data_api_key`
- `remote_llm_api_key`: any of `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY` via `os.getenv`
- `smtp_password`: `settings.smtp_password`

- [ ] **Step 10: Implement admin router and include it**

Create `apps/api/trading_system_api/routers/admin.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.admin_service import collect_admin_health, update_app_settings, get_admin_settings
from trading_system_api.config import Settings, get_settings
from trading_system_api.dashboard_cache import clear_dashboard_summary_cache
from trading_system_api.database import get_session
from trading_system_api.schemas import AdminHealthRead, AdminSettingsRead, AdminSettingsUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/settings", response_model=AdminSettingsRead)
async def read_admin_settings(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AdminSettingsRead:
    return await get_admin_settings(session, settings)


@router.patch("/settings", response_model=AdminSettingsRead)
async def patch_admin_settings(
    payload: AdminSettingsUpdate,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AdminSettingsRead:
    result = await update_app_settings(session, payload, settings)
    clear_dashboard_summary_cache()
    return result


@router.get("/health", response_model=AdminHealthRead)
async def admin_health(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AdminHealthRead:
    result = await collect_admin_health(session, settings)
    clear_dashboard_summary_cache()
    return result
```

Modify `main.py`:

```python
from trading_system_api.routers import admin, analysis, daily, dashboard, kronos, market_data, paper, signals, watchlist
```

Include:

```python
app.include_router(admin.router)
```

- [ ] **Step 11: Run admin API tests**

Run:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
rtk proxy .\.venv\Scripts\python.exe -m pytest apps\api\tests\test_admin_api.py apps\api\tests\test_admin_schema.py -q
```

Expected:

- Admin settings and health tests pass.

- [ ] **Step 12: Add frontend admin types and page**

Modify `apps/web/lib/api.ts` with `AdminSettings`, `AdminHealth`.

Create `apps/web/app/admin/page.tsx`:

- Client component.
- On load, fetch `/admin/settings` and `/admin/health`.
- Render one vertical page with sections:
  - Settings.
  - Services.
  - Jobs & Logs shell.
  - Safety Notes.
- Settings form saves via `PATCH /admin/settings`.
- Secret fields show status text only.
- Buttons for actions added in Task 5 can be disabled or wired when Task 5 lands.

- [ ] **Step 13: Verify migration, API, and frontend**

Run:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
rtk proxy .\.venv\Scripts\python.exe -m pytest apps\api\tests\test_admin_schema.py apps\api\tests\test_admin_migration.py apps\api\tests\test_admin_api.py -q
rtk proxy .\.venv\Scripts\python.exe -m alembic -c apps\api\alembic.ini upgrade head
rtk npm run typecheck:web
rtk npm run build:web
```

Expected:

- Tests pass.
- Local DB upgrades to `head`.
- `/admin` appears in the Next.js route list.

- [ ] **Step 14: Commit**

```powershell
git add apps/api/alembic/versions/0010_admin_settings_health.py apps/api/trading_system_api/models.py apps/api/trading_system_api/admin_service.py apps/api/trading_system_api/routers/admin.py apps/api/trading_system_api/main.py apps/api/trading_system_api/schemas.py apps/api/tests/test_admin_schema.py apps/api/tests/test_admin_migration.py apps/api/tests/test_admin_api.py apps/web/lib/api.ts apps/web/app/admin/page.tsx apps/web/app/globals.css
git commit -m "Add admin settings and health"
```

---

## Task 5: Admin Actions And Final Verification

**Files:**

- Modify: `apps/api/trading_system_api/admin_service.py`
- Modify: `apps/api/trading_system_api/routers/admin.py`
- Modify: `apps/api/tests/test_admin_api.py`
- Modify: `apps/web/app/admin/page.tsx`
- Modify: `apps/web/lib/api.ts`
- Modify: `docs/superpowers/plans/2026-06-04-trading-system-phased-roadmap.md`

- [ ] **Step 1: Add failing admin action tests**

Append to `apps/api/tests/test_admin_api.py`:

```python
@pytest.mark.anyio
async def test_admin_provider_check_updates_health(monkeypatch) -> None:
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "fake")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()
    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/admin/check-provider")

    assert response.status_code == 200
    assert response.json()["service_name"] == "data_provider"


@pytest.mark.anyio
async def test_admin_smoke_action_clears_dashboard_cache() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()
    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/dashboard/summary?max_age_seconds=30")
        cached = await client.get("/dashboard/summary?max_age_seconds=30")
        smoke = await client.post("/admin/run-smoke")
        after = await client.get("/dashboard/summary?max_age_seconds=30")

    assert cached.json()["cache_hit"] is True
    assert smoke.status_code == 200
    assert after.json()["cache_hit"] is False
```

- [ ] **Step 2: Run action tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
rtk proxy .\.venv\Scripts\python.exe -m pytest apps\api\tests\test_admin_api.py::test_admin_provider_check_updates_health apps\api\tests\test_admin_api.py::test_admin_smoke_action_clears_dashboard_cache -q
```

Expected:

- Fails with 404 for new action endpoints.

- [ ] **Step 3: Add action schemas**

Modify `apps/api/trading_system_api/schemas.py`:

```python
class AdminActionResultRead(BaseModel):
    service_name: str
    status: str
    message: str
    details_json: dict
```

- [ ] **Step 4: Implement provider, LLM, email, smoke actions**

In `admin_service.py`, implement:

```python
async def check_data_provider(session: AsyncSession, settings: Settings) -> AdminActionResultRead:
    if not settings.twelve_data_api_key:
        row = await upsert_service_health(
            session,
            "data_provider",
            "unreachable",
            details={"last_error": "TWELVE_DATA_API_KEY missing"},
        )
        return _action_from_health(row, "Twelve Data key missing")
    row = await upsert_service_health(
        session,
        "data_provider",
        "ok",
        details={"provider": "twelve_data"},
    )
    return _action_from_health(row, "Provider configured")
```

For V1, `test_llm` may validate configured provider/model/base URL without making a live paid request unless a provider key or Ollama URL is configured. It writes `ok`, `degraded`, or `unreachable` to `service_health_checks`.

For `test_email`, use existing email package transport when SMTP host and password are configured. If the password is missing, return `unreachable` with a clear details error.

For `run_smoke`, run the low-cost local smoke checks inside `admin_service.run_smoke_check`: DB connection, settings read, watchlist query, and latest daily run read. Always clear dashboard cache after completion.

- [ ] **Step 5: Add router endpoints**

In `routers/admin.py`:

```python
@router.post("/check-provider", response_model=AdminActionResultRead)
async def check_provider(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    result = await check_data_provider(session, settings)
    clear_dashboard_summary_cache()
    return result


@router.post("/test-llm", response_model=AdminActionResultRead)
async def test_llm(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    result = await check_llm(session, settings)
    clear_dashboard_summary_cache()
    return result


@router.post("/test-email", response_model=AdminActionResultRead)
async def test_email(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    result = await check_email(session, settings)
    clear_dashboard_summary_cache()
    return result


@router.post("/run-smoke", response_model=AdminActionResultRead)
async def run_smoke(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    result = await run_smoke_check(session, settings)
    clear_dashboard_summary_cache()
    return result
```

- [ ] **Step 6: Wire admin action buttons**

Modify `apps/web/app/admin/page.tsx`:

- `Check provider` calls `POST /admin/check-provider`.
- `Test LLM` calls `POST /admin/test-llm`.
- `Send test email` calls `POST /admin/test-email`.
- `Run smoke test` calls `POST /admin/run-smoke`.
- Each button shows running/saved/error status.
- After an action completes, reload `/admin/health`.

- [ ] **Step 7: Update roadmap**

Modify `docs/superpowers/plans/2026-06-04-trading-system-phased-roadmap.md`:

- Add a Phase 8 or "Dashboard/Admin" section if none exists.
- Mark design complete.
- Mark implementation tasks complete as they land.

- [ ] **Step 8: Run full verification**

Run:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
rtk proxy .\.venv\Scripts\python.exe -m pytest apps\api\tests packages\quant\tests
rtk proxy .\.venv\Scripts\python.exe -m ruff check apps packages workers infra
rtk npm run typecheck:web
rtk npm run build:web
```

Expected:

- API and quant tests pass.
- Ruff exits 0.
- TypeScript exits 0.
- Next.js build includes `/dashboard`, `/paper`, `/admin`, `/accuracy`, `/watchlist`.

- [ ] **Step 9: Browser smoke check**

With API and web servers running:

```powershell
$env:PYTHONPATH='apps/api;packages/data;packages/quant;packages/agents;packages/email;workers/daily'
.\.venv\Scripts\python.exe -m uvicorn trading_system_api.main:app --host 127.0.0.1 --port 8002
$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8002'
npm run dev:web -- --hostname 127.0.0.1 --port 3002
```

Check:

- `http://127.0.0.1:3002/dashboard` loads.
- `http://127.0.0.1:3002/paper` loads.
- `http://127.0.0.1:3002/admin` loads.
- Browser console has no errors on those pages.

- [ ] **Step 10: Commit and push**

```powershell
git add apps api packages docs
git commit -m "Add admin actions"
git push origin main
```

After pushing, report:

- Commit hashes.
- Verification commands and pass/fail result.
- Local URLs.
- Any actions that are degraded because env secrets are missing.
