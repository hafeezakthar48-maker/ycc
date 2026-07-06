import { useMemo } from "react";
import { useEChart } from "./useEChart";
import type { TrendChartSeries } from "../types/dashboard";

interface CashFlowChartProps {
  series: TrendChartSeries[];
}

export default function CashFlowChart({ series }: CashFlowChartProps) {
  const option = useMemo(() => {
    const periods = series[0]?.data.map((item) => item.period) ?? [];

    return {
      color: ["#0f766e", "#d97706", "#2563eb"],
      tooltip: { trigger: "axis" },
      legend: { top: 0 },
      grid: { left: 48, right: 18, top: 44, bottom: 34 },
      xAxis: { type: "category", data: periods },
      yAxis: { type: "value", name: "万元" },
      series: series.map((item) => ({
        name: item.name,
        type: "bar",
        barMaxWidth: 22,
        data: item.data.map((point) => point.value)
      }))
    };
  }, [series]);

  const ref = useEChart(option);
  return <div className="chart" ref={ref} />;
}
