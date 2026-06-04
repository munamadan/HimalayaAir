import { useCallback, useEffect, useMemo, useState } from 'react';

import { ErrorPanel } from './components/ErrorPanel';
import { ForecastPanel } from './components/ForecastPanel';
import { HistoricalExplorer } from './components/HistoricalExplorer';
import { LiveMap } from './components/LiveMap';
import { LoadingState } from './components/LoadingState';
import { MetricCard } from './components/MetricCard';
import { PipelineHealth } from './components/PipelineHealth';
import { Pm25Chart } from './components/Pm25Chart';
import { ProvenancePanel } from './components/ProvenancePanel';
import { StationPopup } from './components/StationPopup';
import { WindRose } from './components/WindRose';
import { useDashboardData } from './hooks/useDashboardData';
import { useLiveFeed } from './hooks/useLiveFeed';
import { useStationCurrent } from './hooks/useStationCurrent';
import { formatCoverageMode, sortStationsForDisplay, stationHasCurrentData } from './lib/aqi';
import { formatTimestamp } from './lib/time';
import type { StationsResponse, WebSocketEvent } from './types/api';

function App() {
  const dashboard = useDashboardData();
  const [selectedStationId, setSelectedStationId] = useState<number | null>(null);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showFireEvents, setShowFireEvents] = useState(true);
  const [historicalPollutant, setHistoricalPollutant] = useState('pm25');

  const handleLiveEvent = useCallback(
    (event: WebSocketEvent) => {
      if (event.event === 'station_snapshot' && isStationsResponse(event.data)) {
        dashboard.applyStationSnapshot(event.data);
      }
      if (event.event === 'new_readings') {
        void dashboard.refresh({ silent: true });
      }
    },
    [dashboard],
  );

  const liveFeed = useLiveFeed({ onEvent: handleLiveEvent });

  const sortedStations = useMemo(
    () => sortStationsForDisplay(dashboard.stations?.stations ?? []),
    [dashboard.stations?.stations],
  );

  useEffect(() => {
    if (sortedStations.length === 0) {
      return;
    }
    const selectedStillExists = selectedStationId !== null && sortedStations.some((station) => station.id === selectedStationId);
    if (!selectedStillExists) {
      setSelectedStationId(sortedStations[0].id);
    }
  }, [selectedStationId, sortedStations]);

  const selectedStation = sortedStations.find((station) => station.id === selectedStationId) ?? null;
  const selectedCurrent = useStationCurrent(selectedStationId);
  const coverage = dashboard.stations ?? dashboard.valley;
  const lastUpdated = liveFeed.lastMessageAt ?? dashboard.stations?.timestamp ?? dashboard.valley?.timestamp ?? null;
  const activeStations = sortedStations.filter((station) => station.active).length;
  const reportingStations = sortedStations.filter(stationHasCurrentData).length;
  const displayAqi = dashboard.valley?.composite_aqi ?? dashboard.stations?.valley_composite_aqi ?? null;
  const cigaretteEquivalent = displayAqi === null ? null : Math.max(Math.round(displayAqi / 22), 0);
  const greeting = getKathmanduGreeting();
  const freshnessText = coverage?.fresh_station_count || coverage?.recent_station_count
    ? `${coverage?.fresh_station_count ?? 0} fresh / ${coverage?.recent_station_count ?? 0} recent`
    : 'station coverage sparse';

  return (
    <div className="app-shell">
      <main id="top">
        <section id="map" className="map-stage" aria-label="Kathmandu Valley air quality map">
          <div className="map-commandbar">
            <a className="brand" href="#top" aria-label="HimalayaAir dashboard home">
              <span className="brand__mark">HA</span>
              <span>
                <strong>HimalayaAir</strong>
                <small>Kathmandu Valley air-quality intelligence</small>
              </span>
            </a>
            <div className="map-commandbar__greeting">
              <span>{greeting}, Kathmandu</span>
              <strong>{displayAqi === null ? 'No current AQI' : `AQI ${Math.round(displayAqi)}`}</strong>
            </div>
            <nav aria-label="Dashboard sections">
              <a href="#map">Map</a>
              <a href="#charts">Trends</a>
              <a href="#forecast">Forecast</a>
              <a href="#pipeline">Pipeline</a>
            </nav>
            <button type="button" className="button button--primary" onClick={() => void dashboard.refresh({ silent: true })}>
              {dashboard.refreshing ? 'Refreshing' : 'Refresh'}
            </button>
          </div>

          <div className="map-status-strip" aria-label="Current data status">
            <div>
              <span className="eyebrow">Coverage</span>
              <strong>{formatCoverageMode(coverage?.coverage_mode)}</strong>
            </div>
            <div>
              <span className="eyebrow">Observed stations</span>
              <strong>{freshnessText}</strong>
            </div>
            <div>
              <span className="eyebrow">Updated</span>
              <strong>{dashboard.refreshing ? 'refreshing' : formatTimestamp(lastUpdated)}</strong>
            </div>
            <div className="ws-state">
              <span className={`status-dot status-dot--${liveFeed.status}`} />
              <span>{liveFeed.status}</span>
            </div>
          </div>

          <LiveMap
            stations={sortedStations}
            interpolation={dashboard.interpolation}
            selectedStationId={selectedStationId}
            showHeatmap={showHeatmap}
            showFireEvents={showFireEvents}
            fireEvents={dashboard.events?.events ?? []}
            onSelectStation={setSelectedStationId}
            onToggleHeatmap={() => setShowHeatmap((current) => !current)}
            onToggleFireEvents={() => setShowFireEvents((current) => !current)}
          />
          <div className="station-float">
            <StationPopup
              station={selectedStation}
              current={selectedCurrent.current}
              loading={selectedCurrent.loading}
              error={selectedCurrent.error}
            />
          </div>
        </section>

        {dashboard.loading && !dashboard.stations && (
          <LoadingState title="Loading dashboard state" detail="Fetching stations, interpolation, charts, and pipeline health from FastAPI." />
        )}

        {dashboard.error && <ErrorPanel message={dashboard.error} onRetry={() => void dashboard.refresh()} />}

        <section className="metrics-grid" aria-label="Dashboard summary metrics">
          <MetricCard label="Coverage" value={formatCoverageMode(coverage?.coverage_mode)} detail={coverage?.message ?? 'Waiting for API coverage metadata.'} />
          <MetricCard label="Stations" value={`${reportingStations}/${activeStations}`} detail="current AQI reporting stations over active stations" />
          <MetricCard label="Source" value={dashboard.valley?.source ?? selectedStation?.source ?? 'not reported'} detail="dominant current source from API metadata" />
          <MetricCard
            label="Cigarette Eq."
            value={cigaretteEquivalent === null ? 'n/a' : `${cigaretteEquivalent}`}
            detail="estimated equivalent cigarette exposure for one day at current AQI"
          />
        </section>

        <section id="charts" className="lower-grid">
          <Pm25Chart histories={dashboard.histories} />
          <ProvenancePanel stations={dashboard.stations} valley={dashboard.valley} />
        </section>

        <section className="lower-grid lower-grid--narrow">
          <WindRose data={dashboard.windRose} />
        </section>

        <HistoricalExplorer
          stations={sortedStations}
          pollutant={historicalPollutant}
          onPollutantChange={setHistoricalPollutant}
        />

        <ForecastPanel stations={sortedStations} pollutant={historicalPollutant} />

        <section id="pipeline" className="lower-grid lower-grid--narrow">
          <PipelineHealth health={dashboard.pipelineHealth} />
          <section id="method" className="method-card">
            <span className="eyebrow">Method</span>
            <h2>Current-mode rules</h2>
            <p>
              LIVE_OBSERVED and RECENT_OBSERVED come from observed sensor readings. MODELED_BASELINE is labeled as
              Open-Meteo/CAMS modeled fallback. REPLAY_DEMO is reserved for historical data replayed through Kafka and
              Spark, not frontend-only generated values.
            </p>
            <p className="muted">Last live event: {liveFeed.lastEvent?.event ?? 'none'} at {formatTimestamp(lastUpdated)}</p>
          </section>
        </section>
      </main>
    </div>
  );
}

function isStationsResponse(data: unknown): data is StationsResponse {
  if (!data || typeof data !== 'object') {
    return false;
  }
  const candidate = data as Partial<StationsResponse>;
  return Array.isArray(candidate.stations) && typeof candidate.coverage_mode === 'string';
}

export default App;

function getKathmanduGreeting(): string {
  const hour = Number(
    new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      hour12: false,
      timeZone: 'Asia/Kathmandu',
    }).format(new Date()),
  );

  if (hour < 12) {
    return 'Good morning';
  }
  if (hour < 17) {
    return 'Good afternoon';
  }
  return 'Good evening';
}
