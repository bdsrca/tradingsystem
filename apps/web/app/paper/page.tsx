"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import AppNav from "../../components/AppNav";
import { fetchJson, type PaperOverview, type PaperOverviewWindow } from "../../lib/api";

export default function PaperOverviewPage() {
  const [overview, setOverview] = useState<PaperOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadOverview() {
    setLoading(true);
    setError(null);
    try {
      setOverview(await fetchJson<PaperOverview>("/paper/overview"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load paper overview");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadOverview();
  }, []);

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>Paper</h1>
          <p>Watchlist paper-validation overview.</p>
        </div>
        <AppNav />
      </header>

      <div className="action-row">
        <button disabled={loading} onClick={() => void loadOverview()} type="button">
          {loading ? "Loading" : "Refresh"}
        </button>
      </div>

      {error ? <p className="error">{error}</p> : null}

      {overview ? (
        <section className="table-shell" aria-label="Paper overview table">
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>1Y Return</th>
                <th>1Y Max DD</th>
                <th>1Y Win</th>
                <th>2Y Return</th>
                <th>3Y Return</th>
                <th>Trades</th>
                <th>Last Run</th>
              </tr>
            </thead>
            <tbody>
              {overview.rows.map((row) => (
                <tr key={`${row.ticker}-${row.exchange}`}>
                  <td>
                    <Link href={`/paper/${row.ticker}?exchange=${row.exchange}`}>
                      {row.ticker} / {row.exchange}
                    </Link>
                  </td>
                  <td>{formatWindowReturn(row.one_year)}</td>
                  <td>{formatPercent(row.one_year.max_drawdown_pct)}</td>
                  <td>{formatPercent(row.one_year.win_rate_pct)}</td>
                  <td>{formatWindowReturn(row.two_year)}</td>
                  <td>{formatWindowReturn(row.three_year)}</td>
                  <td>{row.one_year.trade_count ?? "-"}</td>
                  <td>{formatDate(row.one_year.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!loading && overview.rows.length === 0 ? (
            <p className="empty">No paper simulations yet.</p>
          ) : null}
        </section>
      ) : (
        <p className="muted">No paper overview loaded.</p>
      )}
    </main>
  );
}

function formatWindowReturn(window: PaperOverviewWindow) {
  if (window.status !== "simulated") {
    return "not simulated";
  }
  return formatPercent(window.total_return_pct);
}

function formatPercent(value: number | null) {
  return value === null ? "-" : `${value.toFixed(2)}%`;
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleDateString() : "-";
}
