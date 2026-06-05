import Link from "next/link";

import AnalyzeControls from "../../../components/AnalyzeControls";
import CandlestickChart from "../../../components/chart/CandlestickChartLoader";
import {
  fetchJson,
  type KronosForecast,
  type PriceBar,
  type SignalMarker
} from "../../../lib/api";

type Props = {
  params: Promise<{ ticker: string }>;
  searchParams: Promise<{ exchange?: string }>;
};

export const dynamic = "force-dynamic";

export default async function StockDetailPage({ params, searchParams }: Props) {
  const { ticker } = await params;
  const { exchange } = await searchParams;
  const query = exchange ? `?exchange=${encodeURIComponent(exchange)}` : "";
  let bars: PriceBar[] = [];
  let markers: SignalMarker[] = [];
  let kronos: KronosForecast | null = null;

  try {
    bars = await fetchJson<PriceBar[]>(`/market-data/${ticker.toUpperCase()}/bars${query}`, {
      cache: "no-store"
    });
  } catch {
    bars = [];
  }
  try {
    markers = await fetchJson<SignalMarker[]>(`/signals/${ticker.toUpperCase()}/markers${query}`, {
      cache: "no-store"
    });
  } catch {
    markers = [];
  }
  try {
    kronos = await fetchJson<KronosForecast>(`/kronos/${ticker.toUpperCase()}/latest${query}`, {
      cache: "no-store"
    });
  } catch {
    kronos = null;
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>{ticker.toUpperCase()}</h1>
          <p>Daily candlestick chart with deterministic baseline markers.</p>
        </div>
        <nav className="link-row" aria-label="Stock navigation">
          <Link className="text-link" href="/watchlist">
            Watchlist
          </Link>
          <Link className="text-link" href={`/paper/${ticker.toUpperCase()}${query}`}>
            Paper
          </Link>
          <Link className="text-link" href="/accuracy">
            Accuracy
          </Link>
        </nav>
      </header>

      <AnalyzeControls ticker={ticker.toUpperCase()} exchange={exchange} />

      <section className="chart-section" aria-label={`${ticker} candlestick chart`}>
        {bars.length > 0 ? (
          <CandlestickChart
            data={bars}
            forecastPath={
              kronos?.status === "ok"
                ? kronos.forecast_path.map((point) => ({
                    time: point.time,
                    value: point.close
                  }))
                : []
            }
            markers={markers}
          />
        ) : (
          <div className="chart-empty">
            <h2>No OHLCV bars yet</h2>
            <p>Bars will appear after the first market data refresh stores daily prices.</p>
          </div>
        )}
      </section>

      {kronos ? (
        <section className="forecast-note" aria-label="Kronos forecast summary">
          <h2>Kronos</h2>
          <p>
            {kronos.status === "ok"
              ? `20D ${kronos.horizons.find((item) => item.horizon_days === 20)?.direction ?? "neutral"} forecast.`
              : `Kronos ${kronos.status}: ${kronos.error_message ?? "unavailable"}`}
          </p>
          <p>Cross-market transfer forecast; exchange-specific accuracy not yet validated.</p>
        </section>
      ) : null}
    </main>
  );
}
