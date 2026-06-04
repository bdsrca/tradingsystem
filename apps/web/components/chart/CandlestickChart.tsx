"use client";

import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  type CandlestickData,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time
} from "lightweight-charts";
import { useEffect, useRef } from "react";

export type ChartMarker = {
  time: string;
  signal: "BUY" | "SELL" | "REDUCE";
  text?: string;
};

type Props = {
  data: CandlestickData<Time>[];
  markers?: ChartMarker[];
};

export default function CandlestickChart({ data, markers = [] }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }

    const chart: IChartApi = createChart(containerRef.current, {
      height: 420,
      layout: {
        background: { type: ColorType.Solid, color: "#ffffff" },
        textColor: "#293241"
      },
      grid: {
        horzLines: { color: "#eef1f5" },
        vertLines: { color: "#eef1f5" }
      },
      rightPriceScale: {
        borderColor: "#d9dee7"
      },
      timeScale: {
        borderColor: "#d9dee7",
        timeVisible: true
      }
    });

    const series: ISeriesApi<"Candlestick", Time> = chart.addSeries(CandlestickSeries, {
      upColor: "#1f7a5c",
      downColor: "#b42318",
      borderVisible: false,
      wickUpColor: "#1f7a5c",
      wickDownColor: "#b42318"
    });

    series.setData(data);
    createSeriesMarkers(series, markers.map(toSeriesMarker));
    chart.timeScale().fitContent();

    const resizeObserver = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width;
      if (width) {
        chart.applyOptions({ width });
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [data, markers]);

  return <div className="chart-frame" ref={containerRef} />;
}

function toSeriesMarker(marker: ChartMarker): SeriesMarker<Time> {
  const isBuy = marker.signal === "BUY";
  return {
    time: marker.time as Time,
    position: isBuy ? "belowBar" : "aboveBar",
    color: isBuy ? "#1f7a5c" : "#b42318",
    shape: isBuy ? "arrowUp" : "arrowDown",
    text: marker.text ?? marker.signal
  };
}

