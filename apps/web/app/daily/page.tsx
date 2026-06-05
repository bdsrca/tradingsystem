"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchJson, type DailyRun } from "../../lib/api";

export default function DailyPage() {
  const [run, setRun] = useState<DailyRun | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function loadLatest() {
    try {
      setRun(await fetchJson<DailyRun>("/daily/latest"));
      setError(null);
    } catch {
      setRun(null);
    }
  }

  useEffect(() => {
    void loadLatest();
  }, []);

  async function runDailyNow() {
    setRunning(true);
    setStatus("Running daily");
    setError(null);
    try {
      const created = await fetchJson<DailyRun>("/daily/run", { method: "POST" });
      setRun(created);
      setStatus("Daily run saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Daily run failed");
      setStatus(null);
    } finally {
      setRunning(false);
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>Daily Run</h1>
          <p>Post-close watchlist analysis and digest status.</p>
        </div>
        <nav className="link-row" aria-label="Daily navigation">
          <Link className="text-link" href="/watchlist">
            Watchlist
          </Link>
          <Link className="text-link" href="/accuracy">
            Accuracy
          </Link>
          <Link className="text-link" href="/">
            Overview
          </Link>
        </nav>
      </header>

      <div className="action-row">
        <button disabled={running} onClick={runDailyNow} type="button">
          {running ? "Running" : "Run daily now"}
        </button>
        {status ? <span>{status}</span> : null}
      </div>

      {error ? <p className="error">{error}</p> : null}

      {run ? (
        <>
          <section className="paper-grid" aria-label="Daily counts">
            <article className="paper-panel">
              <h2>Status</h2>
              <dl className="metric-grid">
                <div>
                  <dt>Run</dt>
                  <dd>{run.status}</dd>
                </div>
                <div>
                  <dt>Email</dt>
                  <dd>{run.email_sent ? "sent" : "off"}</dd>
                </div>
              </dl>
            </article>
            <article className="paper-panel">
              <h2>Results</h2>
              <dl className="metric-grid">
                <div>
                  <dt>Succeeded</dt>
                  <dd>{run.succeeded_count}</dd>
                </div>
                <div>
                  <dt>Failed</dt>
                  <dd>{run.failed_count}</dd>
                </div>
                <div>
                  <dt>Skipped</dt>
                  <dd>{run.skipped_count}</dd>
                </div>
                <div>
                  <dt>Stale</dt>
                  <dd>{run.stale_count}</dd>
                </div>
              </dl>
            </article>
            <article className="paper-panel">
              <h2>Timing</h2>
              <p className="muted">{new Date(run.started_at).toLocaleString()}</p>
              <p className="muted">{run.triggered_by}</p>
            </article>
          </section>

          <section className="table-shell" aria-label="Daily ticker results">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Status</th>
                  <th>Data</th>
                  <th>Signal</th>
                  <th>Confidence</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {run.items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <Link href={`/stock/${item.ticker}?exchange=${item.exchange}`}>
                        {item.ticker} / {item.exchange}
                      </Link>
                    </td>
                    <td>{item.status}</td>
                    <td>
                      <span className={`freshness freshness-${item.data_freshness}`}>
                        {freshnessLabel(item.data_freshness)}
                      </span>
                    </td>
                    <td>{item.signal ?? "-"}</td>
                    <td>{item.confidence === null ? "-" : item.confidence.toFixed(2)}</td>
                    <td>{item.error_message ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      ) : (
        <p className="muted">No daily runs yet.</p>
      )}
    </main>
  );
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
  return value;
}
