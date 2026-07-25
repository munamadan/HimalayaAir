import { LocateFixed, LoaderCircle, Mountain, RefreshCw } from 'lucide-react';
import type { CSSProperties } from 'react';

import { formatDataModeLabel, getAqiBand } from '../lib/aqi';
import type { CoverageMode, StationSummary } from '../types/api';
import type { LocationStatus } from '../types/ui';
import { StationSearch } from './StationSearch';

interface AppTopBarProps {
  stations: StationSummary[];
  selectedStation: StationSummary | null;
  currentAqi: number | null;
  coverageMode: CoverageMode | null | undefined;
  liveStatus: string;
  refreshing: boolean;
  locationStatus: LocationStatus;
  onSelectStation: (station: StationSummary) => void;
  onRefresh: () => void;
  onLocate: () => void;
}

export function AppTopBar({
  stations,
  selectedStation,
  currentAqi,
  coverageMode,
  liveStatus,
  refreshing,
  locationStatus,
  onSelectStation,
  onRefresh,
  onLocate,
}: AppTopBarProps) {
  const band = getAqiBand(currentAqi);
  const locating = locationStatus === 'locating';

  return (
    <header className="app-topbar">
      <a className="app-brand" href="#map" aria-label="HimalayaAir home">
        <span aria-hidden="true"><Mountain size={21} strokeWidth={2.4} /></span>
        <strong>HimalayaAir</strong>
      </a>

      <StationSearch
        stations={stations}
        selectedStation={selectedStation}
        onSelectStation={onSelectStation}
      />

      <div className="app-topbar__status">
        <span className="topbar-aqi" style={{ '--aqi-color': band.color, '--aqi-text': band.textColor } as CSSProperties}>
          <small>AQI</small>
          <strong>{currentAqi === null ? '--' : Math.round(currentAqi)}</strong>
        </span>
        <span className="topbar-mode">
          <small>{formatDataModeLabel(coverageMode)}</small>
          <strong><i className={`status-dot status-dot--${liveStatus}`} /> {liveStatus === 'open' ? 'Live' : 'Updating'}</strong>
        </span>
        <button
          type="button"
          className="icon-button"
          aria-label="Find nearest air-quality station"
          title="Find nearest station"
          disabled={locating}
          onClick={onLocate}
        >
          {locating ? <LoaderCircle className="spin" size={19} aria-hidden="true" /> : <LocateFixed size={19} aria-hidden="true" />}
        </button>
        <button
          type="button"
          className="icon-button"
          aria-label="Refresh air-quality data"
          title="Refresh data"
          disabled={refreshing}
          onClick={onRefresh}
        >
          <RefreshCw className={refreshing ? 'spin' : undefined} size={19} aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}
