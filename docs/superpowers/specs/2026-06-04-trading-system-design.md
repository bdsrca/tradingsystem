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
- Each `BUY` opens a fixed-size simulated position.
- Each `SELL` exits the position.
- Each `REDUCE` exits or reduces according to a simple configured rule.
- `WATCH` and `HOLD` do not open new positions.
- Maximum holding period defaults to 30 trading days.
- Stop/invalidation exits are simulated when historical price crosses the risk level.
- Slippage and fees are configurable but simple.

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

## 6. Data Sources

V1 should implement one primary market data provider plus a provider interface that allows swapping later.

Candidate providers:

- Alpha Vantage: supports US and Canadian exchange examples.
- Twelve Data: supports symbols with exchange context, including TSX examples.
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

Useful later data:

- Financial statements.
- Earnings calendar.
- News.
- Analyst ratings.
- Macro indicators.
- Social sentiment.

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
- `created_at`
- `updated_at`
- `last_analyzed_at`

Even though V1 is single-user, tables may include a nullable or default `user_id` only if it does not complicate the MVP. Do not build full authentication in V1.

## 9. Email Alerts

Email modes:

- Daily digest.
- Strong signal alert.
- Error digest for failed data or analysis runs.

Strong signal criteria:

- Signal is `BUY`, `SELL`, or `REDUCE`.
- Confidence exceeds configured threshold.
- Signal changed from prior run, or risk condition materially changed.

Email content:

- Ticker.
- Signal.
- Confidence.
- Forecast window.
- Main reason.
- Bear case.
- Invalidation condition.
- Link to local/cloud stock detail page.

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

## 14. Open Decisions

These can be decided during implementation planning:

- Primary V1 market data provider.
- Exact provider symbol format for Canadian stocks.
- Whether Kronos runs in-process, as a worker module, or as a separate model service.
- Whether to use Redis/RQ/Celery immediately or start with a simpler scheduler.
- Exact default paper-trading position size and stop logic.
- Whether to include authentication for cloud deployment or use network-level access control first.

