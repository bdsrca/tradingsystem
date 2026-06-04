import Link from "next/link";

const phaseCards = [
  {
    title: "Watchlist",
    text: "Single-user watchlist management will drive daily post-close analysis."
  },
  {
    title: "Signals",
    text: "The first signal engine starts deterministic before Kronos and TradingAgents are integrated."
  },
  {
    title: "Validation",
    text: "Paper validation will use frozen historical signals so results stay reproducible."
  }
];

export default function Home() {
  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <h1>Trading System</h1>
          <p>Local-first US and Canadian equity signal platform.</p>
        </div>
        <div className="status" aria-label="Phase 0 status">
          <span className="status-dot" aria-hidden="true" />
          Phase 1 foundation
        </div>
      </header>
      <nav className="home-nav" aria-label="Primary">
        <Link href="/watchlist">Open Watchlist</Link>
      </nav>

      <section className="grid" aria-label="Planned surfaces">
        {phaseCards.map((card) => (
          <article className="panel" key={card.title}>
            <h2>{card.title}</h2>
            <p>{card.text}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
