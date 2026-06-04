import Link from "next/link";

import CandlestickChart from "../../../components/chart/CandlestickChartLoader";
import { fetchJson, type PriceBar } from "../../../lib/api";

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

  try {
    bars = await fetchJson<PriceBar[]>(`/market-data/${ticker.toUpperCase()}/bars${query}`, {
      cache: "no-store"
    });
  } catch {
    bars = [];
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>{ticker.toUpperCase()}</h1>
          <p>Daily candlestick chart with Phase 1 empty signal markers.</p>
        </div>
        <Link className="text-link" href="/watchlist">
          Watchlist
        </Link>
      </header>

      <section className="chart-section" aria-label={`${ticker} candlestick chart`}>
        {bars.length > 0 ? (
          <CandlestickChart data={bars} markers={[]} />
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

