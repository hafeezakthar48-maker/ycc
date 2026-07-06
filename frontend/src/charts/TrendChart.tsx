import { useMemo } from "react";
import { useEChart } from "./useEChart";
import type { TrendChartSeries } from "../types/dashboard";

interface TrendChartProps {
  series: TrendChartSeries[];
}

export default function TrendChart({ series }: TrendChartProps) {
  const option = useMemo(() => {
    const periods = series[0]?.data.map((item) => item.period) ?? [];

    return {
      color: ["#2563eb", "#d97706", "#0f766e"],
      tooltip: { trigger: "axis" },
      legend: { top: 0 },
      grid: { left: 46, right: 18, top: 44, bottom: 34 },
      xAxis: { type: "category", data: periods },
      yAxis: { type: "value", name: "万元" },
      series: series.map((item) => ({
        name: item.name,
        type: "line",
        smooth: true,
        symbolSize: 6,
        data: item.data.map((point) => point.value)
      }))
    };
  }, [series]);

  const ref = useEChart(option);
  return <div className="chart" ref={ref} />;
}
