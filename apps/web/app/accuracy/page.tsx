"use client";

import { FormEvent, useEffect, useState } from "react";

import AppNav from "../../components/AppNav";
import {
  fetchJson,
  type SignalAccuracy,
  type SignalOutcomeBackfill
} from "../../lib/api";

const WINDOWS = [5, 10, 20, 30];

export default function AccuracyPage() {
  const [ticker, setTicker] = useState("");
  const [exchange, setExchange] = useState("");
  const [horizonDays, setHorizonDays] = useState(20);
  const [accuracy, setAccuracy] = useState<SignalAccuracy | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [backfilling, setBackfilling] = useState(false);

  async function loadAccuracy(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setLoading(true);
    setStatus(null);
    setError(null);
    try {
      setAccuracy(await fetchJson<SignalAccuracy>(`/signals/accuracy?${accuracyParams()}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load accuracy");
      setAccuracy(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAccuracy();
  }, []);

  async function runBackfill() {
    setBackfilling(true);
    setStatus("Backfilling outcomes");
    setError(null);
    try {
      const result = await fetchJson<SignalOutcomeBackfill>(
        `/signals/outcomes/backfill?${backfillParams()}`,
        { method: "POST" }
      );
      setStatus(`Filled ${result.filled_count}; skipped ${result.skipped_count}`);
      setAccuracy(await fetchJson<SignalAccuracy>(`/signals/accuracy?${accuracyParams()}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Backfill failed");
      setStatus(null);
    } finally {
      setBackfilling(false);
    }
  }

  function accuracyParams() {
    const params = new URLSearchParams({ window: String(horizonDays) });
    const cleanTicker = ticker.trim().toUpperCase();
    const cleanExchange = exchange.trim().toUpperCase();
    if (cleanTicker) {
      params.set("ticker", cleanTicker);
    }
    if (cleanExchange) {
      params.set("exchange", cleanExchange);
    }
    return params.toString();
  }

  function backfillParams() {
    const params = new URLSearchParams({ horizon_days: String(horizonDays) });
    const cleanTicker = ticker.trim().toUpperCase();
    const cleanExchange = exchange.trim().toUpperCase();
    if (cleanTicker) {
      params.set("ticker", cleanTicker);
    }
    if (cleanExchange) {
      params.set("exchange", cleanExchange);
    }
    return params.toString();
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>Accuracy</h1>
          <p>Signal outcome tracking by trading-day window.</p>
        </div>
        <AppNav />
      </header>

      <form className="toolbar" onSubmit={loadAccuracy}>
        <input
          aria-label="Ticker filter"
          onChange={(event) => setTicker(event.target.value)}
          placeholder="Ticker"
          value={ticker}
        />
        <input
          aria-label="Exchange filter"
          onChange={(event) => setExchange(event.target.value)}
          placeholder="Exchange"
          value={exchange}
        />
        <select
          aria-label="Outcome window"
          onChange={(event) => setHorizonDays(Number(event.target.value))}
          value={horizonDays}
        >
          {WINDOWS.map((value) => (
            <option key={value} value={value}>
              {value}D
            </option>
          ))}
        </select>
        <button disabled={loading} type="submit">
          {loading ? "Loading" : "Load"}
        </button>
      </form>

      <div className="action-row">
        <button disabled={backfilling} onClick={runBackfill} type="button">
          {backfilling ? "Backfilling" : "Backfill outcomes"}
        </button>
        {status ? <span>{status}</span> : null}
      </div>

      {error ? <p className="error">{error}</p> : null}

      {accuracy ? (
        <>
          <section className="paper-grid" aria-label="Accuracy metrics">
            <article className="paper-panel">
              <h2>Outcome</h2>
              <dl className="metric-grid">
                <div>
                  <dt>Window</dt>
                  <dd>{accuracy.window}D</dd>
                </div>
                <div>
                  <dt>Signals</dt>
                  <dd>{accuracy.evaluated_count}</dd>
                </div>
              </dl>
            </article>
            <article className="paper-panel">
              <h2>Performance</h2>
              <dl className="metric-grid">
                <div>
                  <dt>Win rate</dt>
                  <dd>{formatPercent(accuracy.win_rate_pct)}</dd>
                </div>
                <div>
                  <dt>Avg return</dt>
                  <dd>{formatPercent(accuracy.average_return_pct)}</dd>
                </div>
              </dl>
            </article>
            <article className="paper-panel">
              <h2>Trust</h2>
              <dl className="metric-grid">
                <div>
                  <dt>Trusted</dt>
                  <dd>{accuracy.trusted_count}</dd>
                </div>
                <div>
                  <dt>Delayed</dt>
                  <dd>{accuracy.delayed_count}</dd>
                </div>
                <div>
                  <dt>Excluded</dt>
                  <dd>{accuracy.backfilled_excluded_count}</dd>
                </div>
              </dl>
            </article>
          </section>

          <section className="table-shell" aria-label="Accuracy trust breakdown">
            <table>
              <thead>
                <tr>
                  <th>Scope</th>
                  <th>Trusted</th>
                  <th>Delayed</th>
                  <th>Backfilled</th>
                  <th>Backfilled excluded</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{scopeLabel(accuracy)}</td>
                  <td>{accuracy.trusted_count}</td>
                  <td>{accuracy.delayed_count}</td>
                  <td>{accuracy.backfilled_count}</td>
                  <td>{accuracy.backfilled_excluded_count}</td>
                </tr>
              </tbody>
            </table>
          </section>
        </>
      ) : (
        <p className="muted">No accuracy data loaded.</p>
      )}
    </main>
  );
}

function formatPercent(value: number) {
  return `${value.toFixed(2)}%`;
}

function scopeLabel(accuracy: SignalAccuracy) {
  if (accuracy.ticker && accuracy.exchange) {
    return `${accuracy.ticker} / ${accuracy.exchange}`;
  }
  if (accuracy.ticker) {
    return accuracy.ticker;
  }
  return "All signals";
}
