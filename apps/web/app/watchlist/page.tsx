"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import AppNav from "../../components/AppNav";
import { fetchJson, type WatchlistItem } from "../../lib/api";

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [symbol, setSymbol] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

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
    setAdding(true);
    setError(null);
    try {
      const created = await fetchJson<WatchlistItem>("/watchlist", {
        method: "POST",
        body: JSON.stringify({ symbol })
      });
      setSymbol("");
      let refreshError: string | null = null;
      try {
        await fetchJson(
          `/market-data/${created.ticker}/refresh?exchange=${encodeURIComponent(created.exchange)}`,
          { method: "POST" }
        );
      } catch (err) {
        refreshError =
          err instanceof Error
            ? `Added ${created.ticker}, but price refresh failed: ${err.message}`
            : `Added ${created.ticker}, but price refresh failed`;
      }
      await loadWatchlist();
      if (refreshError) {
        setError(refreshError);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add symbol");
    } finally {
      setAdding(false);
    }
  }

  async function removeSymbol(item: WatchlistItem) {
    setDeletingId(item.id);
    setError(null);
    try {
      await fetchJson(`/watchlist/${item.id}`, { method: "DELETE" });
      await loadWatchlist();
    } catch (err) {
      setError(
        err instanceof Error
          ? `Failed to remove ${item.ticker}: ${err.message}`
          : `Failed to remove ${item.ticker}`
      );
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>Watchlist</h1>
          <p>Manage the symbols that will drive daily post-close analysis.</p>
        </div>
        <AppNav />
      </header>

      <form className="toolbar" onSubmit={addSymbol}>
        <input
          aria-label="Ticker symbol"
          onChange={(event) => setSymbol(event.target.value)}
          placeholder="AAPL, MDA:NYSE, SHOP.TO, RY:TSX"
          value={symbol}
        />
        <button disabled={adding} type="submit">
          {adding ? "Adding" : "Add"}
        </button>
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
              <th>Actions</th>
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
                <td>
                  <button
                    className="table-button danger"
                    disabled={deletingId === item.id}
                    onClick={() => void removeSymbol(item)}
                    type="button"
                  >
                    {deletingId === item.id ? "Removing" : "Remove"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && items.length === 0 ? <p className="empty">No symbols yet.</p> : null}
      </section>
    </main>
  );
}
