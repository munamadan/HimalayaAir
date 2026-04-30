import { getAqiBand, getAqiPercent } from '../lib/aqi';

interface AqiGaugeProps {
  aqi: number | null | undefined;
  label: string;
}

export function AqiGauge({ aqi, label }: AqiGaugeProps) {
  const band = getAqiBand(aqi);
  const percent = getAqiPercent(aqi);
  const circumference = 2 * Math.PI * 52;
  const dashOffset = circumference * (1 - percent);

  return (
    <section className="aqi-gauge" aria-label={`${label} AQI gauge`}>
      <svg viewBox="0 0 132 132" role="img" aria-label={aqi === null || aqi === undefined ? 'No current AQI' : `AQI ${aqi}`}>
        <circle className="aqi-gauge__track" cx="66" cy="66" r="52" />
        <circle
          className="aqi-gauge__value"
          cx="66"
          cy="66"
          r="52"
          stroke={band.color}
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
        />
      </svg>
      <div className="aqi-gauge__center">
        <span>{label}</span>
        <strong>{aqi ?? '--'}</strong>
        <small>{band.label}</small>
      </div>
    </section>
  );
}
