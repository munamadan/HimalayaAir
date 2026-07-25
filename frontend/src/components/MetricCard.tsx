import type { ReactNode } from 'react';

interface MetricCardProps {
  icon?: ReactNode;
  label: string;
  value: string | number;
  detail: string;
}

export function MetricCard({ icon, label, value, detail }: MetricCardProps) {
  return (
    <article className="metric-card">
      <span className="metric-card__label">
        {icon}
        {label}
      </span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}
