import { useMemo } from "react";
import { useEChart } from "./useEChart";

interface RiskHeatmapProps {
  data: number[][];
}

export default function RiskHeatmap({ data }: RiskHeatmapProps) {
  const option = useMemo(() => {
    const rows = ["收入与利润", "现金流", "税负与库存"];
    const cols = ["一季度", "二季度", "三季度", "四季度"];
    const cells = data.flatMap((row, rowIndex) =>
      row.map((value, colIndex) => [colIndex, rowIndex, value])
    );

    return {
      tooltip: {
        position: "top",
        formatter: (params: { value: [number, number, number] }) =>
          `${rows[params.value[1]]} ${cols[params.value[0]]}：${params.value[2]} 星`
      },
      grid: { left: 78, right: 22, top: 16, bottom: 32 },
      xAxis: { type: "category", data: cols, splitArea: { show: true } },
      yAxis: { type: "category", data: rows, splitArea: { show: true } },
      visualMap: {
        min: 1,
        max: 5,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        inRange: { color: ["#dcfce7", "#fef3c7", "#fee2e2", "#b91c1c"] }
      },
      series: [
        {
          type: "heatmap",
          data: cells,
          label: { show: true },
          emphasis: {
            itemStyle: {
              shadowBlur: 8,
              shadowColor: "rgba(0, 0, 0, 0.18)"
            }
          }
        }
      ]
    };
  }, [data]);

  const ref = useEChart(option);
  return <div className="chart" ref={ref} />;
}
