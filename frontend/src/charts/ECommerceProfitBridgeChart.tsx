import { useMemo } from "react";
import type { ECommerceChartPoint } from "../types/ecommerce";
import { useEChart } from "./useEChart";

interface ECommerceProfitBridgeChartProps {
  data: ECommerceChartPoint[];
}

export default function ECommerceProfitBridgeChart({ data }: ECommerceProfitBridgeChartProps) {
  const option = useMemo(() => {
    let runningTotal = 0;
    const helper: number[] = [];
    const values: number[] = [];
    const colors: string[] = [];

    data.forEach((item, index) => {
      if (index === 0 || index === data.length - 1) {
        helper.push(0);
        values.push(item.value);
        runningTotal = item.value;
        colors.push(item.value >= 0 ? "#0f766e" : "#dc2626");
        return;
      }

      helper.push(item.value < 0 ? runningTotal + item.value : runningTotal);
      values.push(Math.abs(item.value));
      runningTotal += item.value;
      colors.push(item.value >= 0 ? "#0f766e" : "#dc2626");
    });

    return {
      tooltip: { trigger: "axis" },
      grid: { left: 52, right: 18, top: 22, bottom: 46 },
      xAxis: {
        type: "category",
        axisLabel: { interval: 0, rotate: 24 },
        data: data.map((item) => item.name)
      },
      yAxis: { type: "value", name: "元" },
      series: [
        {
          type: "bar",
          stack: "total",
          itemStyle: { color: "transparent" },
          emphasis: { itemStyle: { color: "transparent" } },
          data: helper
        },
        {
          type: "bar",
          stack: "total",
          barMaxWidth: 30,
          data: values.map((value, index) => ({
            value,
            itemStyle: { color: colors[index] }
          }))
        }
      ]
    };
  }, [data]);

  const ref = useEChart(option);
  return <div className="chart" ref={ref} />;
}
