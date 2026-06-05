# Dashboard, Admin, And Paper Overview Design

Date: 2026-06-05

## Goal

Add a split daily decision surface and operations surface:

- `/dashboard` helps the user decide what to inspect after the daily run.
- `/admin` helps the user configure non-secret runtime settings and diagnose failures.
- `/paper` becomes the top-level paper validation overview, while `/paper/[ticker]` remains the ticker detail page.

This is a V1 personal-use design. It favors clear data, simple controls, and low operational risk over a polished analytics dashboard. A separate visual-polish phase can reuse these endpoints.

## Route And Navigation Model

All primary app pages use the same top navigation:

`Watchlist | Dashboard | Paper | Accuracy | Admin`

Rules:

- `Admin` stays at the far right with lower visual weight.
- `Dashboard` is the daily entry point.
- Root route `/` remains a lightweight overview route for debugging and orientation.
- `/` shows a small today's summary card and a prominent `Open Dashboard` action.
- `/paper` shows paper validation overview rows.
- `/paper/[ticker]` keeps the existing per-ticker detail chart and metrics.

## Dashboard

The dashboard answers four questions in the first screen:

1. Did the latest daily run complete?
2. Which stocks need attention?
3. Which signals have data or model caveats?
4. What is the watchlist-wide state?

### Layout

Top summary row:

- Latest daily run: status, start time, success, failed, skipped, stale, degraded.
- Strong signals: count of BUY, SELL, and REDUCE signals above the configured confidence threshold.
- Data health: fresh, stale cache, and no-data counts.
- Accuracy snapshot: default 20D evaluated count, win rate, and average return. If only backfilled outcomes exist, show that the system has no trusted outcomes yet.

Attention panel:

- Failed ticker.
- No-data ticker.
- Degraded signal.
- Stale-cache ticker.
- High-confidence BUY, SELL, or REDUCE.
- Kronos caveat or disagreement when those fields exist.

Each item includes ticker, exchange, reason, latest signal, and a stock detail link.

Watchlist scan table:

- Ticker.
- Market and exchange.
- Latest signal.
- Confidence.
- Data freshness.
- Last analyzed time.
- 20D accuracy.
- Paper 1Y return and max drawdown.
- Caveat.

Default ordering:

1. Failed, no-data, or degraded rows.
2. Strong BUY, SELL, or REDUCE rows.
3. Stale-cache rows.
4. Other rows by ticker.

### Dashboard API

Add:

`GET /dashboard/summary?max_age_seconds=30&force_refresh=false`

The endpoint returns:

- `latest_run`
- `attention_items`
- `watchlist_rows`
- `accuracy_snapshot`
- `paper_snapshot`
- `service_warnings`
- `generated_at`
- `cache_hit`

Use a process-local TTL cache in FastAPI. The default TTL is 30 seconds. Cache key includes endpoint parameters that affect the result.

Clear or bypass the cache after:

- Manual daily run.
- Admin settings save.
- Health check action.
- Smoke test action.
- `force_refresh=true`.

V1 runs as a single-user service, so Redis is not required. A multi-instance cloud deployment should replace this with Redis or a DB-backed cache.

## Admin

The admin page covers two categories:

- Required setup: configuration without which the system cannot run.
- Diagnosis: controls and status needed when the system fails.

Use one vertical page with four sections instead of tabs.

### Settings

Secrets do not enter the DB and the API never returns secret values. Admin shows only `configured` or `missing` for each secret.

Non-secret settings are saved in the DB and should apply to the next run. Scheduler changes also reschedule the in-process scheduler.

Configuration precedence:

1. Environment secrets.
2. DB runtime settings.
3. Code defaults.

Data Provider:

- Saveable: preferred provider.
- Env-only: Twelve Data API key.
- Read-only status: configured or missing.
- Action: check provider.

LLM Provider:

- Saveable: provider type, base URL, model name, TradingAgents enabled, max debate rounds, max risk discussion rounds.
- Env-only: remote API keys.
- Action: test LLM.

Email:

- Saveable: SMTP host, port, user, from address, to address, daily digest enabled, strong signal alert threshold, debounce days.
- Env-only: SMTP password.
- Action: send test email.

Scheduler:

- Saveable: auto-run enabled, trigger time, timezone, Kronos enabled.
- Action: save and reschedule.

### Services

Show read-only health cards:

- API: status and app version or commit when available.
- Database: connection OK and Alembic current/head version.
- Kronos service: connected or unreachable, latency, last error.
- Email: last digest sent time and last error.
- Data provider: last health check, quota remaining when available, last error.

### Jobs And Logs

Show:

- Recent 10 daily runs: time, trigger, status, success, failed, skipped, stale, degraded.
- Recent errors: ticker, stage, error type or message, time.

Actions:

- Run daily now. Reuse `POST /daily/run`.
- Run smoke test. Add `POST /admin/run-smoke`.
- Refresh health.

### Safety Notes

Keep these notes at low visual weight near the bottom:

- Secrets come from environment variables.
- Admin changes affect the next run and do not mutate immutable historical signals.
- Smoke tests may call configured external providers.

## Admin API And Schema

Add:

- `GET /admin/settings`
- `PATCH /admin/settings`
- `GET /admin/health`
- `POST /admin/check-provider`
- `POST /admin/test-llm`
- `POST /admin/test-email`
- `POST /admin/run-smoke`

Reuse:

- `POST /daily/run`
- Existing daily latest/run result endpoints.

Extend `app_settings` with non-sensitive fields:

- `provider_preference`
- `llm_provider_type`
- `llm_base_url`
- `llm_model_name`
- `tradingagents_enabled`
- `max_debate_rounds`
- `max_risk_discuss_rounds`
- `smtp_host`
- `smtp_port`
- `smtp_user`
- `smtp_from`
- `smtp_to`
- `daily_digest_enabled`
- `strong_signal_alert_threshold`
- `scheduler_enabled`
- `daily_trigger_hour`
- `daily_trigger_minute`
- `daily_timezone`
- `kronos_enabled`
- `email_debounce_days`

Add `service_health_checks`:

- `service_name`: `api`, `db`, `kronos`, `email`, or `data_provider`
- `status`: `ok`, `degraded`, or `unreachable`
- `checked_at`
- `latency_ms`
- `details_json`

Use upsert by `service_name`. V1 stores only the latest state for each service and does not keep health history.

## Paper Overview

Add `/paper` as the top-level route.

Columns:

- Ticker.
- Exchange.
- 1Y total return.
- 1Y max drawdown.
- 1Y win rate.
- 2Y total return.
- 3Y total return.
- Trade count.
- Last simulation time.
- Detail link.

Add:

`GET /paper/overview`

The endpoint returns the latest frozen paper run per watchlist ticker and window. If a ticker has no paper run, the row returns `not_simulated`.

The detail link points to `/paper/[ticker]?exchange=...`.

## Implementation Split

Commit 1: Shared shell/navigation and dashboard summary.

- Add shared navigation.
- Add `/dashboard`.
- Add `GET /dashboard/summary` with TTL cache.
- Add tests for summary shape, attention ordering, and cache behavior.

Commit 2: Paper overview.

- Add `/paper`.
- Add `GET /paper/overview`.
- Add tests for latest-run selection and empty state.

Commit 3: Admin settings and health schema.

- Add Alembic migration for `app_settings` extensions and `service_health_checks`.
- Add `GET/PATCH /admin/settings`.
- Add `GET /admin/health`.
- Add tests for secret masking, settings persistence, scheduler reschedule path, and health upsert.

Commit 4: Admin actions.

- Add provider check.
- Add test email.
- Add test LLM.
- Add smoke test trigger.
- Clear dashboard cache after settings save, health check, daily run, and smoke test.
- Add UI buttons and status states.

## Testing

Backend tests:

- Dashboard summary labels stale cache and no-data rows.
- Dashboard TTL returns cached data within `max_age_seconds`.
- `force_refresh=true` bypasses cache.
- Admin settings PATCH rejects secret fields and never returns secret values.
- Service health upsert keeps one row per service.
- Scheduler settings save triggers reschedule.
- Paper overview returns latest frozen simulation per ticker and window.
- Smoke-test action clears dashboard cache.

Frontend checks:

- `npm run typecheck:web`
- `npm run build:web`
- Dashboard, Paper, Accuracy, Watchlist, and Admin navigation render on desktop and mobile.

## Out Of Scope For This Spec

- Full visual polish for a rich analytics dashboard.
- Editable secret storage with encryption.
- Health trend history.
- Redis or distributed cache.
- Kronos disagreement UI beyond reserving caveat fields in dashboard rows.
