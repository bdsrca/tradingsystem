# Phase 5 Daily Worker And Email Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a daily post-close worker that refreshes watchlist data, runs baseline/Kronos analysis, records run summaries, and sends one debounced email digest.

**Architecture:** Keep Phase 5 local-first and single-user: one shared worker service function runs both manual and scheduled jobs, protected by an in-process `asyncio.Lock`. Persist operational summaries and email decisions in the API database, while the email package owns digest rendering and SMTP transport boundaries.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, APScheduler, httpx/Twelve Data, existing baseline/Kronos APIs, Python stdlib email/smtplib, Next.js App Router.

---

### Task 1: Phase 5 Schema

**Files:**
- Create: `apps/api/alembic/versions/0007_phase5_daily_worker_email.py`
- Modify: `apps/api/trading_system_api/models.py`
- Test: `apps/api/tests/test_phase5_schema.py`

- [ ] Write a failing schema test that asserts `daily_worker_runs`, `daily_worker_ticker_results`, and `email_notifications` exist after `Base.metadata.create_all`.
- [ ] Add SQLAlchemy models for worker run summaries, per-ticker results, and notification debounce records.
- [ ] Add Alembic migration `0007_phase5` after `0006_phase4`.
- [ ] Verify schema tests pass.

### Task 2: Email Digest And Debounce

**Files:**
- Create: `packages/email/trading_system_email/digest.py`
- Create: `packages/email/tests/test_digest.py`

- [ ] Write failing tests for one-email digest aggregation and same ticker/signal debounce suppression.
- [ ] Implement `EmailDigestItem`, `EmailDigest`, `EmailDebouncePolicy`, `should_send_signal_alert()`, and `render_digest_text()`.
- [ ] Verify email package tests pass.

### Task 3: Daily Worker Core

**Files:**
- Create: `workers/daily/trading_system_worker/daily.py`
- Create: `workers/daily/tests/test_daily_worker.py`

- [ ] Write failing tests proving a duplicate ticker run is skipped while its `asyncio.Lock` is held.
- [ ] Write failing tests proving worker summary counts include succeeded, failed, skipped, stale, and degraded buckets.
- [ ] Implement a dependency-injected `DailyWorker` that refreshes data, runs baseline, optionally calls Kronos, records per-ticker result objects, and builds an email digest payload.
- [ ] Verify worker tests pass.

### Task 4: API Manual Trigger And Scheduler Config

**Files:**
- Create: `apps/api/trading_system_api/routers/daily.py`
- Modify: `apps/api/trading_system_api/config.py`
- Modify: `apps/api/trading_system_api/main.py`
- Test: `apps/api/tests/test_daily_api.py`

- [ ] Write failing API tests for `POST /daily/run` and `GET /daily/latest`.
- [ ] Add scheduler settings: timezone, trigger hour/minute, enabled flag, Kronos enabled flag, email enabled flag.
- [ ] Add API endpoints that call the same worker function as the scheduler.
- [ ] Wire APScheduler in FastAPI lifespan only when enabled.
- [ ] Verify API tests pass.

### Task 5: Minimal UI

**Files:**
- Modify: `apps/web/lib/api.ts`
- Create: `apps/web/app/daily/page.tsx`
- Modify: `apps/web/app/watchlist/page.tsx`

- [ ] Add types for daily run summary.
- [ ] Add a `/daily` page with a `Run daily now` button and latest run counts.
- [ ] Link Watchlist to Daily.
- [ ] Verify `npm run typecheck:web` and browser smoke pass.

### Task 6: Final Verification And Commit

- [ ] Run `ruff check apps packages services workers`.
- [ ] Run full Python tests through `.venv`.
- [ ] Run `npm run build:web`.
- [ ] Smoke-test `/daily`, `/watchlist`, and one stock page.
- [ ] Commit and push to `main`.
