"use client";

import dynamic from "next/dynamic";

const CandlestickChart = dynamic(() => import("./CandlestickChart"), {
  ssr: false,
  loading: () => <div className="chart-skeleton" aria-label="Loading chart" />
});

export default CandlestickChart;
