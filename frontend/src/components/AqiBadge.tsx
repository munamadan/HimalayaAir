import { getAqiBand } from '../lib/aqi';

interface AqiBadgeProps {
  aqi: number | null | undefined;
  compact?: boolean;
}

export function AqiBadge({ aqi, compact = false }: AqiBadgeProps) {
  const band = getAqiBand(aqi);
  return (
    <span
      className={compact ? 'aqi-badge aqi-badge--compact' : 'aqi-badge'}
      style={{ background: band.color, color: band.textColor }}
    >
      <strong>{aqi ?? 'No AQI'}</strong>
      {!compact && <span>{band.shortLabel}</span>}
    </span>
  );
}
