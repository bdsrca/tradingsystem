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

