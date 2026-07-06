import { useMemo } from "react";
import { useEChart } from "./useEChart";
import type { ChartPoint } from "../types/dashboard";

interface ExpensePieChartProps {
  data: ChartPoint[];
}

export default function ExpensePieChart({ data }: ExpensePieChartProps) {
  const option = useMemo(
    () => ({
      color: ["#2563eb", "#0f766e", "#d97706", "#7c3aed"],
      tooltip: { trigger: "item" },
      legend: { bottom: 0 },
      series: [
        {
          type: "pie",
          radius: ["44%", "68%"],
          center: ["50%", "42%"],
          avoidLabelOverlap: true,
          data: data.map((item) => ({ name: item.period, value: item.value }))
        }
      ]
    }),
    [data]
  );

  const ref = useEChart(option);
  return <div className="chart" ref={ref} />;
}
