"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import AppNav from "../../components/AppNav";
import { fetchJson, type DashboardSummary } from "../../lib/api";

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadSummary(forceRefresh = false) {
    setLoading(true);
    setError(null);
    try {
      const query = forceRefresh ? "force_refresh=true" : "max_age_seconds=30";
      setSummary(await fetchJson<DashboardSummary>(`/dashboard/summary?${query}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSummary();
  }, []);

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>Dashboard</h1>
          <p>Daily signals, data health, and watchlist scan.</p>
        </div>
        <AppNav />
      </header>

      <div className="action-row">
        <button disabled={loading} onClick={() => void loadSummary(true)} type="button">
          {loading ? "Loading" : "Refresh"}
        </button>
        {summary ? (
          <span>
            {summary.cache_hit ? "Cached" : "Fresh"} at{" "}
            {new Date(summary.generated_at).toLocaleTimeString()}
          </span>
        ) : null}
      </div>

      {error ? <p className="error">{error}</p> : null}

      {summary ? (
        <>
          <section className="dashboard-strip" aria-label="Dashboard summary">
            <article className="summary-card">
              <h2>Daily Run</h2>
              <dl className="compact-metrics">
                <div>
                  <dt>Status</dt>
                  <dd>{summary.latest_run?.status ?? "none"}</dd>
                </div>
                <div>
                  <dt>Failed</dt>
                  <dd>{summary.latest_run?.failed_count ?? 0}</dd>
                </div>
                <div>
                  <dt>Stale</dt>
                  <dd>{summary.latest_run?.stale_count ?? 0}</dd>
                </div>
                <div>
                  <dt>Degraded</dt>
                  <dd>{summary.latest_run?.degraded_count ?? 0}</dd>
                </div>
              </dl>
            </article>

            <article className="summary-card">
              <h2>Attention</h2>
              <dl className="compact-metrics">
                <div>
                  <dt>Items</dt>
                  <dd>{summary.attention_items.length}</dd>
                </div>
                <div>
                  <dt>Warnings</dt>
                  <dd>{summary.service_warnings.length}</dd>
                </div>
              </dl>
            </article>

            <article className="summary-card">
              <h2>20D Accuracy</h2>
              <dl className="compact-metrics">
                <div>
                  <dt>Evaluated</dt>
                  <dd>{summary.accuracy_snapshot.evaluated_count}</dd>
                </div>
                <div>
                  <dt>Win</dt>
                  <dd>{formatPercent(summary.accuracy_snapshot.win_rate_pct)}</dd>
                </div>
                <div>
                  <dt>Avg</dt>
                  <dd>{formatPercent(summary.accuracy_snapshot.average_return_pct)}</dd>
                </div>
                <div>
                  <dt>Excluded</dt>
                  <dd>{summary.accuracy_snapshot.backfilled_excluded_count}</dd>
                </div>
              </dl>
            </article>
          </section>

          <section className="table-shell" aria-label="Attention items">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Severity</th>
                  <th>Reason</th>
                  <th>Signal</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {summary.attention_items.map((item) => (
                  <tr key={`${item.ticker}-${item.exchange}-${item.reason}`}>
                    <td>
                      <Link href={item.href}>
                        {item.ticker} / {item.exchange}
                      </Link>
                    </td>
                    <td>
                      <span className={`severity severity-${item.severity}`}>{item.severity}</span>
                    </td>
                    <td>{item.reason}</td>
                    <td>{item.signal ?? "-"}</td>
                    <td>{item.confidence === null ? "-" : item.confidence.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {summary.attention_items.length === 0 ? <p className="empty">No attention items.</p> : null}
          </section>

          <section className="table-shell" aria-label="Watchlist scan">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Signal</th>
                  <th>Confidence</th>
                  <th>Data</th>
                  <th>Paper 1Y</th>
                  <th>Max DD</th>
                  <th>Caveat</th>
                </tr>
              </thead>
              <tbody>
                {summary.watchlist_rows.map((row) => (
                  <tr key={`${row.ticker}-${row.exchange}`}>
                    <td>
                      <Link href={`/stock/${row.ticker}?exchange=${row.exchange}`}>
                        {row.ticker} / {row.exchange}
                      </Link>
                    </td>
                    <td>{row.latest_signal ?? "-"}</td>
                    <td>{row.confidence === null ? "-" : row.confidence.toFixed(2)}</td>
                    <td>
                      <span className={`freshness freshness-${row.data_freshness}`}>
                        {freshnessLabel(row.data_freshness)}
                      </span>
                    </td>
                    <td>{formatNullablePercent(row.paper_1y_return_pct)}</td>
                    <td>{formatNullablePercent(row.paper_1y_max_drawdown_pct)}</td>
                    <td>{row.caveat ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {summary.watchlist_rows.length === 0 ? <p className="empty">No watchlist rows.</p> : null}
          </section>
        </>
      ) : (
        <p className="muted">No dashboard data loaded.</p>
      )}
    </main>
  );
}

function formatPercent(value: number) {
  return `${value.toFixed(2)}%`;
}

function formatNullablePercent(value: number | null) {
  return value === null ? "-" : formatPercent(value);
}

function freshnessLabel(value: string) {
  if (value === "fresh") {
    return "Fresh";
  }
  if (value === "stale_used") {
    return "Stale cache";
  }
  if (value === "no_data") {
    return "No data";
  }
  if (value === "unknown") {
    return "Unknown";
  }
  return value;
}
