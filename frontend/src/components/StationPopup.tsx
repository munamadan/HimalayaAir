import { X } from 'lucide-react';

import { AqiBadge } from './AqiBadge';
import { formatDataModeLabel, healthAdviceForAqi } from '../lib/aqi';
import { formatFreshness, formatTimestamp } from '../lib/time';
import type { StationCurrentResponse, StationSummary } from '../types/api';

interface StationPopupProps {
  station: StationSummary | null;
  current: StationCurrentResponse | null;
  loading: boolean;
  error: string | null;
  onClose?: () => void;
}

export function StationPopup({ station, current, loading, error, onClose }: StationPopupProps) {
  if (!station) {
    return (
      <section className="station-card station-card--empty">
        <span className="eyebrow">Place detail</span>
        <strong>Select a place</strong>
        <p>Current readings will appear here.</p>
      </section>
    );
  }

  const readings = current?.readings ?? [];

  return (
    <section className="station-card" aria-label="Selected station detail">
      <div className="station-card__header">
        <div>
          <span className="eyebrow">Selected place</span>
          <h2>{station.name}</h2>
        </div>
        <div className="station-card__actions">
          <AqiBadge aqi={station.current_aqi} />
          {onClose && (
            <button type="button" className="button button--secondary button--icon" onClick={onClose} aria-label="Close station detail">
              <X size={18} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      <dl className="detail-list">
        <div>
          <dt>Health</dt>
          <dd>{station.health_category ?? healthAdviceForAqi(station.current_aqi)}</dd>
        </div>
        <div>
          <dt>Map basis</dt>
          <dd>{formatDataModeLabel(station.coverage_mode)}</dd>
        </div>
        <div>
          <dt>Updated</dt>
          <dd>{formatFreshness(station.freshness_minutes)}</dd>
        </div>
        <div>
          <dt>Last seen</dt>
          <dd>{formatTimestamp(station.last_seen)}</dd>
        </div>
      </dl>

      <p className="station-card__advice">{healthAdviceForAqi(station.current_aqi)}</p>

      {loading && <p className="muted">Loading latest readings.</p>}
      {error && <p className="inline-error">Could not load latest readings: {error}</p>}
      {!loading && readings.length === 0 && <p className="muted">No current pollutant readings are available for this place.</p>}

      {readings.length > 0 && (
        <div className="reading-list">
          {readings.map((reading) => (
            <article key={`${reading.pollutant}-${reading.timestamp}`} className="reading-pill">
              <div>
                <strong>{reading.pollutant.toUpperCase()}</strong>
                <span>{reading.value.toFixed(1)} {reading.unit}</span>
              </div>
              <AqiBadge aqi={reading.aqi} compact />
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
