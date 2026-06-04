"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { fetchJson, type WatchlistItem } from "../../lib/api";

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [symbol, setSymbol] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadWatchlist() {
    setLoading(true);
    try {
      setItems(await fetchJson<WatchlistItem[]>("/watchlist"));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadWatchlist();
  }, []);

  async function addSymbol(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!symbol.trim()) {
      return;
    }
    try {
      await fetchJson<WatchlistItem>("/watchlist", {
        method: "POST",
        body: JSON.stringify({ symbol })
      });
      setSymbol("");
      await loadWatchlist();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add symbol");
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>Watchlist</h1>
          <p>Manage the symbols that will drive daily post-close analysis.</p>
        </div>
        <Link className="text-link" href="/">
          Overview
        </Link>
      </header>

      <form className="toolbar" onSubmit={addSymbol}>
        <input
          aria-label="Ticker symbol"
          onChange={(event) => setSymbol(event.target.value)}
          placeholder="AAPL, SHOP.TO, RY:TSX"
          value={symbol}
        />
        <button type="submit">Add</button>
      </form>

      {error ? <p className="error">{error}</p> : null}
      {loading ? <p className="muted">Loading watchlist...</p> : null}

      <section className="table-shell" aria-label="Watchlist table">
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Market</th>
              <th>Provider Symbol</th>
              <th>Status</th>
              <th>Tags</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>
                  <Link href={`/stock/${item.ticker}?exchange=${item.exchange}`}>
                    {item.ticker}
                  </Link>
                </td>
                <td>
                  {item.exchange} / {item.market}
                </td>
                <td>{item.provider_symbol}</td>
                <td>{item.enabled ? "Enabled" : "Paused"}</td>
                <td>{item.tags.join(", ") || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && items.length === 0 ? <p className="empty">No symbols yet.</p> : null}
      </section>
    </main>
  );
}

