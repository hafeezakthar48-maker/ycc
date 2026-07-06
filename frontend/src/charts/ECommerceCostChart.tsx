import { useMemo } from "react";
import type { ECommerceChartPoint } from "../types/ecommerce";
import { useEChart } from "./useEChart";

interface ECommerceCostChartProps {
  data: ECommerceChartPoint[];
}

export default function ECommerceCostChart({ data }: ECommerceCostChartProps) {
  const option = useMemo(
    () => ({
      color: ["#0f766e", "#2563eb", "#d97706", "#7c3aed", "#0891b2", "#be123c", "#4b5563", "#65a30d"],
      tooltip: { trigger: "item" },
      legend: { bottom: 0, type: "scroll" },
      series: [
        {
          type: "pie",
          radius: ["44%", "68%"],
          center: ["50%", "42%"],
          data: data.map((item) => ({ name: item.name, value: item.value }))
        }
      ]
    }),
    [data]
  );

  const ref = useEChart(option);
  return <div className="chart" ref={ref} />;
}
