import Link from "next/link";

import AppNav from "../components/AppNav";

export default function Home() {
  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>Trading System</h1>
          <p>Local-first US and Canadian equity signal platform.</p>
        </div>
        <div className="status" aria-label="Phase 2 status">
          <span className="status-dot" aria-hidden="true" />
          Local-first
        </div>
      </header>
      <AppNav className="home-nav" />

      <section className="paper-grid" aria-label="Overview">
        <article className="paper-panel">
          <h2>Today's Summary</h2>
          <p className="muted">Open the dashboard for latest signals, data health, and watchlist scan.</p>
          <div className="action-row">
            <Link className="button-link" href="/dashboard">
              Open Dashboard
            </Link>
          </div>
        </article>
      </section>
    </main>
  );
}
