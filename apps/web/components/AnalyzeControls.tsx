"use client";

import { useState } from "react";

import { fetchJson } from "../lib/api";

type Props = {
  ticker: string;
  exchange?: string;
};

export default function AnalyzeControls({ ticker, exchange }: Props) {
  const [status, setStatus] = useState<string | null>(null);
  const analysisQuery = exchange ? `?exchange=${encodeURIComponent(exchange)}` : "";
  const paperQuery = new URLSearchParams({ window_years: "1" });
  if (exchange) {
    paperQuery.set("exchange", exchange);
  }

  async function runBaseline() {
    setStatus("Running baseline");
    await fetchJson(`/analysis/${ticker}/baseline${analysisQuery}`, { method: "POST" });
    setStatus("Baseline signal saved");
    window.location.reload();
  }

  async function runPaper() {
    setStatus("Running paper");
    await fetchJson(`/paper/${ticker}/run?${paperQuery.toString()}`, { method: "POST" });
    setStatus("Paper run saved");
    window.location.href = `/paper/${ticker}${analysisQuery}`;
  }

  return (
    <div className="action-row">
      <button onClick={runBaseline} type="button">
        Run baseline
      </button>
      <button onClick={runPaper} type="button">
        Run paper 1Y
      </button>
      {status ? <span>{status}</span> : null}
    </div>
  );
}
