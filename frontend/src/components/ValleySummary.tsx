import { CalendarClock, Clock3, MapPin, Radio, Wind } from 'lucide-react';
import type { CSSProperties } from 'react';

import { dataModeSummary, formatDataModeLabel, getAqiBand, healthAdviceForAqi, stationHasCurrentData } from '../lib/aqi';
import { formatTimestamp } from '../lib/time';
import type { CoverageMode, StationSummary } from '../types/api';

interface ValleySummaryProps {
  aqi: number | null;
  coverageMode: CoverageMode | null | undefined;
  dominantPollutant: string | null | undefined;
  lastUpdated: string | null;
  stations: StationSummary[];
  onSelectStation: (station: StationSummary) => void;
  onOpenForecast: () => void;
}

export function ValleySummary({
  aqi,
  coverageMode,
  dominantPollutant,
  lastUpdated,
  stations,
  onSelectStation,
  onOpenForecast,
}: ValleySummaryProps) {
  const band = getAqiBand(aqi);
  const reporting = stations.filter(stationHasCurrentData);
  const rankedStations = [...stations]
    .sort((left, right) => (right.current_aqi ?? -1) - (left.current_aqi ?? -1))
    .slice(0, 8);

  return (
    <div className="valley-summary">
      <section className="inspector-aqi" style={{ '--aqi-color': band.color, '--aqi-text': band.textColor } as CSSProperties}>
        <div>
          <span>AQI</span>
          <strong>{aqi === null ? '--' : Math.round(aqi)}</strong>
        </div>
        <article>
          <small>Kathmandu Valley</small>
          <h2>{band.label}</h2>
          <p>{healthAdviceForAqi(aqi)}</p>
        </article>
      </section>

      <button type="button" className="inspector-primary-action" onClick={onOpenForecast}>
        <CalendarClock size={18} aria-hidden="true" />
        Plan with the 72-hour forecast
      </button>

      <dl className="inspector-stats">
        <div>
          <dt><MapPin size={15} aria-hidden="true" /> Reporting</dt>
          <dd>{reporting.length}/{stations.filter((station) => station.active).length} stations</dd>
        </div>
        <div>
          <dt><Wind size={15} aria-hidden="true" /> Dominant</dt>
          <dd>{dominantPollutant?.toUpperCase() ?? 'Not available'}</dd>
        </div>
        <div>
          <dt><Clock3 size={15} aria-hidden="true" /> Updated</dt>
          <dd>{formatTimestamp(lastUpdated)}</dd>
        </div>
      </dl>

      <section className="data-basis-note">
        <Radio size={17} aria-hidden="true" />
        <span>
          <strong>{formatDataModeLabel(coverageMode)}</strong>
          <small>{dataModeSummary(coverageMode)}</small>
        </span>
      </section>

      <section className="station-rank">
        <header>
          <span>Stations</span>
          <small>Highest AQI first</small>
        </header>
        <div>
          {rankedStations.map((station) => {
            const stationBand = getAqiBand(station.current_aqi);
            return (
              <button key={station.id} type="button" onClick={() => onSelectStation(station)}>
                <span>
                  <strong>{station.name}</strong>
                  <small>{station.freshness_minutes === null ? 'No recent reading' : `${station.freshness_minutes} min ago`}</small>
                </span>
                <b style={{ background: stationBand.color, color: stationBand.textColor }}>
                  {station.current_aqi === null ? '--' : Math.round(station.current_aqi)}
                </b>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}
