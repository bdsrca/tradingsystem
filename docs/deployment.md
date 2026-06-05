# Deployment Notes

This project remains single-user and local-first, but Phase 6 makes it safer to
run on a small cloud VM or container platform.

## Required First Run

After installing dependencies and setting environment variables, initialize the
database before starting the API:

```powershell
.\.venv\Scripts\python.exe -m infra.scripts.init_db
```

For Docker or Linux shells:

```bash
python -m infra.scripts.init_db
```

The command is idempotent. It runs Alembic migrations to `head`. If
`TRADINGAGENTS_CHECKPOINT_SETUP_ENABLED=true`, it also initializes the
TradingAgents LangGraph SQLite checkpointer under
`TRADINGAGENTS_CHECKPOINT_DATA_DIR`.

`docker compose up` runs the same command through the `init-db` service before
starting the API service.

## Cloud Auth

Set these variables when the app is reachable from the internet:

```env
CLOUD_MODE=true
BASIC_AUTH_USERNAME=<your-user>
BASIC_AUTH_PASSWORD=<long-random-password>
```

`CLOUD_MODE=true` enables Basic Auth for both the FastAPI service and the
Next.js UI. The API fails closed if the username or password is missing.

For split API/web deployments, either put both services behind one authenticated
origin or configure the same Basic Auth credentials for both services.

## Deployment Environment

Minimum production-like variables:

```env
DATABASE_URL=postgresql+asyncpg://trading:<password>@<host>:5432/trading_system
TWELVE_DATA_API_KEY=<key>
NEXT_PUBLIC_API_BASE_URL=<api-url>
SCHEDULER_ENABLED=true
SCHEDULER_TIMEZONE=America/Toronto
DAILY_TRIGGER_HOUR=17
DAILY_TRIGGER_MINUTE=0
```

Optional:

```env
DAILY_KRONOS_ENABLED=true
KRONOS_SERVICE_URL=<kronos-service-url>
DAILY_EMAIL_ENABLED=true
DAILY_EMAIL_RECIPIENT=<you@example.com>
SMTP_HOST=<smtp-host>
SMTP_USERNAME=<smtp-user>
SMTP_PASSWORD=<smtp-password>
SMTP_FROM_EMAIL=<from@example.com>
TRADINGAGENTS_CHECKPOINT_SETUP_ENABLED=true
TRADINGAGENTS_CHECKPOINT_DATA_DIR=/data/tradingagents
```

Keep `.env` out of git. Rotate API, SMTP, and Basic Auth secrets after any
accidental exposure.

## Backup And Restore

For Docker Compose Postgres:

```bash
docker compose exec postgres pg_dump -U trading -d trading_system -Fc -f /tmp/trading_system.dump
docker compose cp postgres:/tmp/trading_system.dump ./backups/trading_system.dump
```

Restore into an empty database:

```bash
docker compose cp ./backups/trading_system.dump postgres:/tmp/trading_system.dump
docker compose exec postgres pg_restore -U trading -d trading_system --clean --if-exists /tmp/trading_system.dump
```

Also back up persistent TradingAgents checkpoint storage if enabled:

```bash
tar -czf backups/tradingagents-checkpoints.tgz .runtime/tradingagents
```

## Smoke Test

After deployment:

```bash
python -m infra.scripts.smoke
```

The smoke script checks API health, the web app, database migration state,
watchlist access, and a daily analysis run. To avoid triggering a daily run:

```bash
python -m infra.scripts.smoke --skip-daily-run
```

For authenticated deployments, set `BASIC_AUTH_USERNAME` and
`BASIC_AUTH_PASSWORD` in the smoke-test environment.
