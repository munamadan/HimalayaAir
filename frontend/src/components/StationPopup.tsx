import { AqiBadge } from './AqiBadge';
import { formatSource } from '../lib/aqi';
import { formatFreshness, formatTimestamp } from '../lib/time';
import type { StationCurrentResponse, StationSummary } from '../types/api';

interface StationPopupProps {
  station: StationSummary | null;
  current: StationCurrentResponse | null;
  loading: boolean;
  error: string | null;
}

export function StationPopup({ station, current, loading, error }: StationPopupProps) {
  if (!station) {
    return (
      <section className="station-card station-card--empty">
        <span className="eyebrow">Station detail</span>
        <strong>Select a marker</strong>
        <p>Station readings and provenance will appear here.</p>
      </section>
    );
  }

  const readings = current?.readings ?? [];

  return (
    <section className="station-card" aria-label="Selected station detail">
      <div className="station-card__header">
        <div>
          <span className="eyebrow">Selected station</span>
          <h2>{station.name}</h2>
        </div>
        <AqiBadge aqi={station.current_aqi} />
      </div>

      <dl className="provenance-list">
        <div>
          <dt>Source</dt>
          <dd>{formatSource(station.source)}</dd>
        </div>
        <div>
          <dt>Observation</dt>
          <dd>{station.observation_type ?? 'not reported'}</dd>
        </div>
        <div>
          <dt>Coverage</dt>
          <dd>{station.coverage_mode ?? 'not reported'}</dd>
        </div>
        <div>
          <dt>Freshness</dt>
          <dd>{formatFreshness(station.freshness_minutes)}</dd>
        </div>
        <div>
          <dt>Last seen</dt>
          <dd>{formatTimestamp(station.last_seen)}</dd>
        </div>
      </dl>

      {loading && <p className="muted">Loading latest pollutant readings.</p>}
      {error && <p className="inline-error">Could not load station readings: {error}</p>}
      {!loading && readings.length === 0 && <p className="muted">No current pollutant readings returned by the API.</p>}

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
