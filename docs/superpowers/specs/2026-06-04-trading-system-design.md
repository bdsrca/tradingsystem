# Trading System Design

Date: 2026-06-04

## 1. Purpose

Build a single-user, local-first stock signal and explanation platform for US and Canadian equities. The system analyzes a saved watchlist after the market close and produces 5-30 trading day swing signals with clear reasoning, risk conditions, and historical validation.

The first version does not provide real-time intraday signals, broker integration, or live order execution. It focuses on signal generation, explainability, alerts, and simple paper-trading validation.

## 2. Product Scope

### In Scope

- Single-user self-hosted/local use.
- US and Canadian equity support.
- Saved watchlist management.
- Daily post-close analysis only.
- 5, 10, 20, and 30 trading day forecast and validation windows.
- Signal output: `BUY`, `WATCH`, `HOLD`, `REDUCE`, `SELL`.
- Confidence score and explanation for every signal.
- Candlestick chart with historical buy/sell markers.
- Optional overlays for moving averages, stop/invalidation level, and Kronos forecast.
- Daily email digest and strong-signal alerts.
- Simple paper-trading validation over 1, 2, and 3 year windows.
- Local model option through Ollama.
- Remote LLM/API option through an OpenAI-compatible adapter.
- Cloud-ready architecture for later deployment.

### Out of Scope for V1

- Real-time intraday signals.
- Automatic broker trading.
- Multi-user SaaS account management.
- Portfolio tax accounting.
- Complex order simulation.
- Options, crypto, forex, and futures.
- Guaranteed profitability claims.

## 3. Reference Projects

### Kronos

Kronos is used as the market time-series forecast component. It is a financial K-line foundation model designed around OHLCV-style market sequences. In this product, Kronos should act as one quantitative analyst, not the final trading decision maker.

Primary use:

- Forecast price path or return tendency over 5-30 trading days.
- Estimate directional alignment with technical indicators.
- Provide a model-derived forecast summary for the explanation layer.

Reference: https://github.com/shiyu-coder/Kronos

### TradingAgents

TradingAgents is used as the inspiration for the explanation and decision workflow. The system should not blindly copy every agent, but should preserve the useful structure: specialized analysts, bull/bear debate, risk review, and final decision.

Primary use:

- Technical analysis report.
- Fundamental and company context report.
- News and macro context report.
- Bull case and bear case.
- Risk manager decision.
- Final signal explanation.

Reference: https://github.com/tauricresearch/tradingagents

## 4. User Experience

### Main Flow

1. User adds tickers to the watchlist.
2. System fetches historical daily OHLCV and supporting data.
3. After market close, the worker analyzes all enabled watchlist items.
4. Each ticker receives a signal, confidence score, forecast window, explanation, and risk invalidation condition.
5. Strong signals trigger email alerts; otherwise the user receives a daily digest.
6. User reviews the watchlist dashboard or opens a stock detail page.
7. Paper validation shows how similar signals performed over 1-3 years.

### Watchlist Page

The watchlist is the main entry point.

Columns:

- Ticker
- Market or exchange
- Company name
- Last price
- Current signal
- Confidence
- Forecast window
- Last analyzed time
- Alert status
- Data status
- Tags

Actions:

- Add ticker.
- Remove ticker.
- Enable or pause analysis.
- Edit tags.
- Set alert threshold.
- Open stock detail page.
- Manually run analysis for one ticker.
- Manually run analysis for all enabled tickers.

Ticker examples:

- US: `AAPL`, `MSFT`, `SPY`
- Canada: provider-specific formats such as `SHOP.TRT`, `SHOP.TO`, or `RY:TSX`

The app should normalize provider-specific symbols internally so the UI can display a consistent canonical ticker and exchange.

### Stock Detail Page

The stock detail page is centered on a candlestick chart.

Chart requirements:

- Daily candlestick data.
- Time range selector: 1M, 3M, 6M, 1Y, 3Y.
- Buy markers on chart.
- Sell or reduce markers on chart.
- Optional display of watch/hold markers, disabled by default to reduce noise.
- Volume pane.
- Optional moving average overlays.
- Optional Kronos forecast overlay or forecast band.
- Optional invalidation or stop-risk line.

Marker hover content:

- Date.
- Signal.
- Confidence.
- Price at signal.
- Main reason summary.
- 5, 10, 20, and 30 day forward returns if already known.

Below the chart:

- Current signal summary.
- Kronos forecast summary.
- Technical analysis summary.
- Fundamental/company context summary.
- News/macro summary.
- Bull case.
- Bear case.
- Risk manager decision.
- Final explanation.
- Historical signal performance for this ticker.

Recommended chart library: TradingView Lightweight Charts.

Reference: https://tradingview.github.io/lightweight-charts/

### Paper Validation Page

This page validates signal quality without placing real trades.

Controls:

- Time window: 1Y, 2Y, 3Y.
- Market filter: US, Canada, All.
- Ticker/tag filter.
- Position size setting display.

Metrics:

- Simulated equity curve.
- Total return.
- Annualized return.
- Maximum drawdown.
- Win rate.
- Average trade return.
- Average holding days.
- Number of simulated trades.
- Best contributors.
- Worst contributors.
- Recent simulated trades.

V1 simulation rules:

- Initial capital defaults to 100,000.
- Position sizing uses equal weight by default: 5% of total simulated capital per new position.
- Each `BUY` opens a position only when the ticker has no currently open simulated position.
- Repeated `BUY` signals for an already-open ticker are recorded as confirmations, not additional buys.
- Each `SELL` exits the full simulated position.
- Each `REDUCE` exits 50% of the simulated position.
- `WATCH` and `HOLD` do not open new positions.
- Maximum holding period defaults to 30 trading days.
- Maximum open positions defaults to 20.
- New positions are skipped when there is not enough simulated cash or the maximum open position count has been reached.
- Stop/invalidation exits are simulated when historical price crosses the risk level.
- Slippage and fees are configurable but simple.
- Simulation assumptions are stored with each run so results are reproducible.

This page is for validation only. It must not imply live trading execution.

### Settings Page

Settings:

- Data provider API keys.
- Preferred data provider.
- LLM provider.
- Remote LLM API key/base URL.
- Ollama base URL.
- Ollama model name.
- Email provider settings.
- Daily digest on/off.
- Strong-signal alert threshold.
- Market close analysis schedule.
- Paper validation assumptions.

## 5. Architecture

The system should be local-first but cloud-ready.

Recommended top-level modules:

- `apps/web`: Next.js frontend.
- `apps/api`: FastAPI backend.
- `packages/quant`: forecasting, indicators, scoring, and backtesting.
- `packages/agents`: LLM-based analyst and decision workflows.
- `packages/data`: market data provider adapters and local cache.
- `packages/email`: digest and alert generation.
- `workers/daily`: scheduled post-close analysis worker.
- `infra`: Docker Compose and later cloud deployment configuration.

### V1 Default Decisions

To avoid blocking implementation on open architecture questions, V1 uses these defaults:

- Primary market data provider: Twelve Data for daily OHLCV across US and Canadian tickers.
- Supplemental data provider: Finnhub for company, fundamentals, and news context where available.
- Canadian ticker display format: Yahoo-style symbols such as `SHOP.TO`; provider adapters translate to provider-specific formats such as `SHOP:TSX` when needed.
- Kronos runtime: worker module in the Python analysis process, not a separate model service for V1.
- Scheduler: APScheduler embedded in the local API/worker process.
- Paper position sizing: equal weight, 5% of total simulated capital per new position.
- Cloud access protection: HTTP Basic Auth through environment variables for single-user deployment, unless a stronger deployment-specific access layer is used.

These defaults are intentionally simple. They can be replaced later without changing the product surface if the interfaces below remain stable.

### Local Runtime

Local development should run through Docker Compose where practical:

- Web app.
- API service.
- Worker service.
- Postgres.
- Redis or task queue if needed.
- Optional model service.

Ollama can run outside Compose on the host or inside a dedicated service, depending on local hardware and user preference.

### Cloud Runtime

The architecture should allow later cloud deployment:

- Web/API deployed to a cloud platform.
- Postgres moved to managed Postgres.
- Worker deployed as scheduled job or long-running worker.
- Kronos/Ollama served from a GPU/VPS host or separate model service.
- Email provider configured with production credentials.

Kronos inference should not be assumed to fit normal serverless function limits.

### Analysis Concurrency And Timeouts

Daily analysis must complete within a practical post-close window. V1 should assume that Kronos can be slow on CPU and should not run all tickers in an unbounded serial loop.

Rules:

- The worker processes watchlist items through a bounded worker pool.
- Kronos calls have a per-ticker timeout.
- LLM calls have a per-agent timeout.
- Provider calls have retries with backoff and rate-limit awareness.
- If Kronos times out for a ticker, the run is marked degraded and falls back to a technical-indicator-only signal plus a clear explanation that Kronos was unavailable.
- If the LLM layer times out, the run is marked degraded and uses deterministic summaries from computed data only.
- Degraded runs must not trigger strong-signal emails unless explicitly allowed in settings.

The system records per-step duration so slow providers, tickers, and agents can be identified.

## 6. Data Sources

V1 should implement one primary market data provider plus a provider interface that allows swapping later.

Candidate providers:

- Twelve Data: V1 default for daily OHLCV, with explicit startup health checks for US and Canadian symbols.
- Alpha Vantage: fallback source for development and comparison; free-tier rate limits make it unsuitable as the only provider for larger watchlists.
- Finnhub: useful for company fundamentals, economic data, and news.
- Polygon: strong US market data option; Canadian coverage and cost require separate verification before relying on it.

References:

- https://www.alphavantage.co/documentation/
- https://twelvedata.com/docs
- https://finnhub.io/docs/api
- https://polygon.io/docs

Required V1 data:

- Daily OHLCV.
- Symbol search or symbol validation.
- Company name and exchange.
- Market calendar or enough date handling to compute trading-day windows.
- Provider health check for configured API keys.
- Data freshness metadata.

Useful later data:

- Financial statements.
- Earnings calendar.
- News.
- Analyst ratings.
- Macro indicators.
- Social sentiment.

### Provider Health Checks

The API or worker startup should verify configured providers before running analysis.

Health check requirements:

- Validate API key presence and basic connectivity.
- Fetch one known US ticker sample.
- Fetch one known Canadian ticker sample.
- Confirm historical daily bar availability.
- Report rate-limit or entitlement failures distinctly from network failures.
- Store the latest provider health status for display in settings and worker error digests.

The analysis worker should skip or degrade jobs when the required provider is unhealthy rather than producing unsupported conclusions.

### Data Freshness

Stored market bars must include:

- `source_provider`
- `source_symbol`
- `data_source_version` when available
- `fetched_at`
- `bar_date`
- `market`
- `exchange`

Freshness rules:

- A ticker is fresh when the latest expected market bar for that ticker's exchange has been fetched within the configured freshness window.
- `watchlist_items.data_stale_after_hours` controls the default refetch threshold.
- US and Canadian tickers use their own exchange calendars before deciding whether a bar is missing or simply not expected due to a holiday.
- Stale data is visible in the watchlist status column and prevents strong-signal alerts.

### Trading Calendars

The quant package must include a trading calendar abstraction for exchange-specific trading days.

Requirements:

- Distinguish NYSE/Nasdaq calendars from TSX calendars.
- Compute 5, 10, 20, and 30 trading day forward windows using the correct exchange calendar.
- Treat market holidays and early closes explicitly.
- Prefer a maintained calendar library such as `pandas_market_calendars` where it fits the Python stack.

## 7. Signal Workflow

### Daily Analysis Pipeline

For each enabled watchlist item:

1. Resolve canonical ticker and provider ticker.
2. Fetch or refresh historical daily OHLCV.
3. Compute technical indicators.
4. Run Kronos forecast for 5, 10, 20, and 30 trading day horizons.
5. Gather optional company/news/fundamental context.
6. Run analyst reports.
7. Run bull/bear debate.
8. Run risk manager review.
9. Produce final signal.
10. Store analysis result and decision trace.
11. Update paper validation results.
12. Trigger email if alert conditions are met.

### Kronos Forecast Contract

Kronos output must be converted into a structured result before it enters the agent workflow.

`KronosForecastResult`:

- `ticker`
- `analysis_date`
- `horizon_days`
- `direction`: `bullish`, `bearish`, or `neutral`
- `magnitude_pct`: forecast return estimate for the horizon
- `confidence`: normalized value from 0 to 1 when available
- `forecast_close`
- `forecast_low`
- `forecast_high`
- `volatility_note`
- `model_name`
- `model_version`
- `runtime_ms`
- `status`: `ok`, `timeout`, `error`, or `skipped`
- `error_message`

The technical analyst receives `KronosForecastResult` together with computed indicators. The final decision must preserve whether Kronos agreed or disagreed with the non-LLM technical signal.

When Kronos and the final signal materially disagree, the UI should highlight the disagreement rather than hiding it.

### Signal Schema

Each analysis run should store:

- Ticker.
- Market/exchange.
- Analysis date.
- Data snapshot ID.
- Signal.
- Confidence.
- Forecast horizon.
- Current price.
- Suggested entry note.
- Invalidation condition.
- Risk level.
- Kronos summary.
- Technical summary.
- Fundamental summary.
- News/macro summary.
- Bull case.
- Bear case.
- Final explanation.
- Model/provider metadata.
- Raw structured outputs where useful.

### Signal Scoring

The final signal should combine:

- Kronos forecast direction and magnitude.
- Technical trend alignment.
- Volatility and drawdown risk.
- Recent volume behavior.
- Fundamental/news risk flags when available.
- LLM-generated reasoning, constrained by structured inputs.

The LLM should explain and adjudicate. It should not invent market data. All numerical claims must come from retrieved data or computed indicators.

### Agent Prompt Guardrails

Agent prompts must separate facts, computed values, and opinions.

Required prompt blocks:

- `[DATA]`: retrieved market, company, provider, and news records.
- `[COMPUTED]`: indicators, Kronos result, paper validation metrics, and deterministic scores.
- `[CONSTRAINTS]`: allowed signal labels, horizon, risk rules, and forbidden claims.
- `[OPINION]`: the agent's interpretation.

Rules:

- Agents must not introduce new numerical facts that are absent from `[DATA]` or `[COMPUTED]`.
- Agents must cite the field name or source block for important numerical claims.
- The final explanation step includes a validation pass that checks generated numbers against structured input.
- If the validator detects unsupported numbers or contradictions, the run is marked degraded and regenerated once with stricter instructions.
- Prompt versions are recorded with each analysis run so future signal quality can be compared across prompt changes.

## 8. Data Model

Core tables:

- `watchlist_items`
- `market_data_bars`
- `analysis_runs`
- `signals`
- `agent_reports`
- `paper_trades`
- `paper_portfolio_snapshots`
- `email_notifications`
- `settings`

### watchlist_items

Fields:

- `id`
- `ticker`
- `provider_symbol`
- `market`
- `exchange`
- `display_name`
- `enabled`
- `tags`
- `alert_enabled`
- `alert_threshold`
- `data_stale_after_hours`
- `created_at`
- `updated_at`
- `last_analyzed_at`

Even though V1 is single-user, tables may include a nullable or default `user_id` only if it does not complicate the MVP. Do not build full authentication in V1.

### analysis_runs

Additional observability fields:

- `job_id`
- `status`
- `degraded`
- `degradation_reason`
- `duration_seconds`
- `data_fetch_duration_ms`
- `kronos_duration_ms`
- `llm_duration_ms`
- `paper_validation_duration_ms`
- `prompt_version`
- `provider_health_snapshot`

### paper_trades

Fields should include enough information to reproduce validation results:

- `simulation_run_id`
- `ticker`
- `entry_signal_id`
- `exit_signal_id`
- `entry_date`
- `exit_date`
- `entry_price`
- `exit_price`
- `position_sizing_method`
- `position_size_pct`
- `shares`
- `fees`
- `slippage`
- `exit_reason`
- `return_pct`
- `holding_days`

## 9. Email Alerts

Email modes:

- Daily digest.
- Strong signal alert.
- Error digest for failed data or analysis runs.

Strong signal criteria:

- Signal is `BUY`, `SELL`, or `REDUCE`.
- Confidence exceeds configured threshold.
- Signal changed from prior run, or risk condition materially changed.
- Run is not degraded, unless degraded alerts are explicitly enabled.

Email content:

- Ticker.
- Signal.
- Confidence.
- Forecast window.
- Main reason.
- Bear case.
- Invalidation condition.
- Link to local/cloud stock detail page.

### Debounce And Aggregation

The email system must avoid becoming noisy.

Rules:

- Strong signals from the same daily run are aggregated into one email.
- The same ticker and same signal direction should not send repeated strong-signal emails within the configured debounce window.
- Default debounce window is 5 trading days.
- A materially changed signal can bypass debounce when confidence crosses a higher threshold or the signal direction changes.
- Daily digest includes all watchlist outcomes, including skipped and degraded runs.
- Error digest includes counts for succeeded, failed, skipped, stale-data, and degraded tickers.

`email_notifications` should record ticker, signal direction, debounce key, sent status, and provider response metadata.

## 10. Error Handling

Expected failures:

- API rate limits.
- Provider symbol mismatch.
- Missing Canadian ticker mapping.
- Market holiday or no fresh bars.
- Kronos unavailable.
- Ollama unavailable.
- Remote LLM API failure.
- Email provider failure.

Behavior:

- Store failed run status.
- Show data status in watchlist.
- Do not send confident alerts from partial data.
- Fall back from full agent analysis to deterministic technical-only summary only when explicitly marked as degraded.
- Preserve enough logs for later debugging.

### Worker Observability

Workers must emit structured logs for each major step.

Log fields:

- `job_id`
- `ticker`
- `market`
- `step`
- `status`
- `duration_ms`
- `provider`
- `degraded`
- `error_code`

Daily worker completion should produce a run summary:

- Total tickers.
- Succeeded.
- Failed.
- Skipped.
- Degraded.
- Stale data.
- Strong signals generated.
- Emails sent or suppressed by debounce.

The summary should be visible in logs and included in the error digest when any run fails or degrades.

## 11. Testing And Verification

Minimum verification for V1:

- Unit tests for symbol normalization.
- Unit tests for indicator calculations.
- Unit tests for signal scoring.
- Unit tests for paper-trading simulation rules.
- Integration test for one complete analysis run with mocked provider data.
- API tests for watchlist CRUD.
- UI smoke test for watchlist and stock detail chart rendering.
- Backtest fixture for at least one US ticker and one Canadian ticker.

Success criteria:

- User can add a US ticker and a Canadian ticker.
- User can run daily analysis manually.
- System produces a stored signal and explanation.
- Stock detail page shows candlestick chart and buy/sell markers.
- Paper page shows 1Y, 2Y, and 3Y validation metrics.
- Email digest can be generated in test mode.

## 12. Security And Risk Notes

- This system provides analysis and educational decision support, not financial advice.
- No broker credentials in V1.
- API keys must be stored in environment variables or encrypted local config, not committed.
- LLM prompts must distinguish between retrieved facts, computed indicators, and model opinion.
- The UI should show uncertainty and invalidation conditions with every actionable signal.
- Cloud deployment must protect API keys and restrict access because the app is intended for single-user use.

## 13. Recommended V1 Build Order

1. Repository scaffold and local Docker setup.
2. Database schema.
3. Watchlist CRUD.
4. Market data provider adapter.
5. OHLCV storage and refresh.
6. Candlestick chart with buy/sell markers.
7. Technical indicators and deterministic baseline signal.
8. Paper validation engine.
9. Kronos integration.
10. LLM provider adapter with remote API and Ollama option.
11. TradingAgents-style analyst workflow.
12. Daily worker.
13. Email digest and alerting.
14. Cloud deployment preparation.

## 14. Deferred Decisions And Future Enhancements

The major V1 defaults are defined in the architecture section. The remaining decisions can be finalized during implementation planning:

- Exact Twelve Data symbol mapping rules for each Canadian exchange edge case.
- Whether Finnhub is required in V1 or enabled only when credentials exist.
- Exact Kronos timeout value after measuring local hardware performance.
- Whether degraded technical-only runs should be allowed to appear as `WATCH` or `HOLD` only.
- Exact chart overlays enabled by default.
- Whether cloud deployment uses Basic Auth only or sits behind a private network/VPN.

Future enhancements to preserve in the design:

- Signal consistency checks when Kronos and the final agent decision disagree.
- Forecast accuracy tracking that compares predicted prices with actual 5, 10, 20, and 30 trading day outcomes.
- Prompt A/B testing using recorded prompt versions.
- More detailed tag-based watchlist runs.
- Volatility-adjusted paper-trading position sizing.
- Full broker paper account integration after the signal engine proves useful.
