import type { MetricCard as MetricCardType } from "../types/dashboard";

interface MetricCardProps {
  metric: MetricCardType;
}

export default function MetricCard({ metric }: MetricCardProps) {
  return (
    <article className={`metric-card metric-card--${metric.status}`}>
      <span>{metric.title}</span>
      <strong>{metric.value}</strong>
      <small>{metric.change}</small>
    </article>
  );
}
