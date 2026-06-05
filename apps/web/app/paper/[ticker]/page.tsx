import AppNav from "../../../components/AppNav";
import { fetchJson, type PaperRun, type PaperSnapshot } from "../../../lib/api";

type Props = {
  params: Promise<{ ticker: string }>;
  searchParams: Promise<{ exchange?: string }>;
};

export const dynamic = "force-dynamic";

export default async function PaperValidationPage({ params, searchParams }: Props) {
  const { ticker } = await params;
  const { exchange } = await searchParams;
  const runs = await Promise.all([1, 2, 3].map((years) => loadRun(ticker, exchange, years)));

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>{ticker.toUpperCase()} Paper</h1>
          <p>Frozen baseline signal validation.</p>
        </div>
        <AppNav />
      </header>

      <section className="paper-grid" aria-label="Paper validation windows">
        {runs.map((run, index) => (
          <article className="paper-panel" key={index}>
            <h2>{index + 1}Y</h2>
            {run ? (
              <>
                <dl className="metric-grid">
                  <div>
                    <dt>Return</dt>
                    <dd>{run.metrics.total_return_pct.toFixed(2)}%</dd>
                  </div>
                  <div>
                    <dt>Max DD</dt>
                    <dd>{run.metrics.max_drawdown_pct.toFixed(2)}%</dd>
                  </div>
                  <div>
                    <dt>Win</dt>
                    <dd>{run.metrics.win_rate_pct.toFixed(2)}%</dd>
                  </div>
                  <div>
                    <dt>Trades</dt>
                    <dd>{run.metrics.trade_count}</dd>
                  </div>
                </dl>
                <EquityCurve snapshots={run.snapshots} />
              </>
            ) : (
              <p className="empty">No run yet.</p>
            )}
          </article>
        ))}
      </section>
    </main>
  );
}

async function loadRun(ticker: string, exchange: string | undefined, years: number) {
  const query = new URLSearchParams({ window_years: String(years) });
  if (exchange) {
    query.set("exchange", exchange);
  }
  try {
    return await fetchJson<PaperRun>(`/paper/${ticker.toUpperCase()}/latest?${query.toString()}`, {
      cache: "no-store"
    });
  } catch {
    return null;
  }
}

function EquityCurve({ snapshots }: { snapshots: PaperSnapshot[] }) {
  if (snapshots.length < 2) {
    return <div className="equity-empty" />;
  }

  const width = 360;
  const height = 120;
  const values = snapshots.map((snapshot) => snapshot.portfolio_value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - ((value - min) / range) * height;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");

  return (
    <svg className="equity-curve" role="img" viewBox={`0 0 ${width} ${height}`}>
      <polyline fill="none" points={points} stroke="#1f7a5c" strokeWidth="3" />
    </svg>
  );
}
