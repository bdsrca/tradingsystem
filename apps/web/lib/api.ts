export type WatchlistItem = {
  id: string;
  ticker: string;
  exchange: string;
  market: string;
  provider_symbol: string;
  display_name: string | null;
  enabled: boolean;
  tags: string[];
  alert_enabled: boolean;
  alert_threshold: number | null;
  data_stale_after_hours: number;
  last_analyzed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type PriceBar = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
};

export type SignalMarker = {
  time: string;
  signal: string;
  position: "aboveBar" | "belowBar";
  color: string;
  shape: "arrowUp" | "arrowDown" | "circle" | "square";
  text: string;
};

export type SignalOutcomeBackfill = {
  horizon_days: number;
  filled_count: number;
  skipped_count: number;
};

export type SignalAccuracy = {
  ticker: string | null;
  exchange: string | null;
  window: number;
  evaluated_count: number;
  trusted_count: number;
  delayed_count: number;
  backfilled_count: number;
  backfilled_excluded_count: number;
  win_rate_pct: number;
  average_return_pct: number;
};

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

export type KronosForecastPoint = {
  time: string;
  close: number;
};

export type KronosForecast = {
  id: string | null;
  ticker: string;
  exchange: string;
  analysis_date: string;
  status: string;
  is_fallback: boolean;
  error_message: string | null;
  volatility_note: string | null;
  forecast_path: KronosForecastPoint[];
  horizons: Array<{
    horizon_days: number;
    expected_return_pct: number;
    direction: string;
    confidence: number;
    forecast_close: number;
    forecast_low: number;
    forecast_high: number;
  }>;
};

export type PaperSnapshot = {
  time: string;
  portfolio_value: number;
  cash: number;
  positions_value: number;
  benchmark_symbol: string | null;
  benchmark_value: number | null;
};

export type PaperRun = {
  id: string;
  ticker: string;
  exchange: string;
  window_years: number;
  signal_snapshot: { signal_ids?: string[]; source?: string };
  metrics: {
    total_return_pct: number;
    max_drawdown_pct: number;
    win_rate_pct: number;
    trade_count: number;
  };
  snapshots: PaperSnapshot[];
};

export type DailyTickerResult = {
  id: string;
  ticker: string;
  exchange: string;
  market: string | null;
  status: string;
  data_freshness: string;
  signal: string | null;
  confidence: number | null;
  error_message: string | null;
  started_at: string;
  finished_at: string | null;
};

export type DailyRun = {
  id: string;
  triggered_by: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  succeeded_count: number;
  failed_count: number;
  skipped_count: number;
  stale_count: number;
  degraded_count: number;
  email_sent: boolean;
  summary: Record<string, unknown>;
  items: DailyTickerResult[];
};

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    }
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
