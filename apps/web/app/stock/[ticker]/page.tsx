import Link from "next/link";

import AnalyzeControls from "../../../components/AnalyzeControls";
import CandlestickChart from "../../../components/chart/CandlestickChartLoader";
import { fetchJson, type PriceBar, type SignalMarker } from "../../../lib/api";

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
        </nav>
      </header>

      <AnalyzeControls ticker={ticker.toUpperCase()} exchange={exchange} />

      <section className="chart-section" aria-label={`${ticker} candlestick chart`}>
        {bars.length > 0 ? (
          <CandlestickChart data={bars} markers={markers} />
        ) : (
          <div className="chart-empty">
            <h2>No OHLCV bars yet</h2>
            <p>Bars will appear after the first market data refresh stores daily prices.</p>
          </div>
        )}
      </section>
    </main>
  );
}
