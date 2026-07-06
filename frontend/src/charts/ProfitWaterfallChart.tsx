import { useMemo } from "react";
import { useEChart } from "./useEChart";
import type { ChartPoint } from "../types/dashboard";

interface ProfitWaterfallChartProps {
  data: ChartPoint[];
}

export default function ProfitWaterfallChart({ data }: ProfitWaterfallChartProps) {
  const option = useMemo(() => {
    let runningTotal = 0;
    const helper: number[] = [];
    const values: number[] = [];

    data.forEach((item, index) => {
      if (index === 0) {
        helper.push(0);
        values.push(item.value);
        runningTotal = item.value;
        return;
      }

      if (item.value < 0) {
        helper.push(runningTotal + item.value);
        values.push(Math.abs(item.value));
      } else {
        helper.push(0);
        values.push(item.value);
      }
      runningTotal += item.value;
    });

    return {
      color: ["#0f766e"],
      tooltip: { trigger: "axis" },
      grid: { left: 46, right: 18, top: 20, bottom: 34 },
      xAxis: { type: "category", data: data.map((item) => item.period) },
      yAxis: { type: "value", name: "万元" },
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
          barMaxWidth: 28,
          data: values
        }
      ]
    };
  }, [data]);

  const ref = useEChart(option);
  return <div className="chart" ref={ref} />;
}
