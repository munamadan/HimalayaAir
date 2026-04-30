import { useCallback, useEffect, useMemo, useState } from 'react';

import { AqiGauge } from './components/AqiGauge';
import { CoverageRibbon } from './components/CoverageRibbon';
import { ErrorPanel } from './components/ErrorPanel';
import { LiveMap } from './components/LiveMap';
import { LoadingState } from './components/LoadingState';
import { MetricCard } from './components/MetricCard';
import { PipelineHealth } from './components/PipelineHealth';
import { Pm25Chart } from './components/Pm25Chart';
import { ProvenancePanel } from './components/ProvenancePanel';
import { StationPopup } from './components/StationPopup';
import { useDashboardData } from './hooks/useDashboardData';
import { useLiveFeed } from './hooks/useLiveFeed';
import { useStationCurrent } from './hooks/useStationCurrent';
import { formatCoverageMode, sortStationsForDisplay, stationHasCurrentData } from './lib/aqi';
import { formatTimestamp } from './lib/time';
import type { StationsResponse, WebSocketEvent } from './types/api';

function App() {
  const dashboard = useDashboardData();
  const [selectedStationId, setSelectedStationId] = useState<number | null>(null);
  const [showHeatmap, setShowHeatmap] = useState(true);

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

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="HimalayaAir dashboard home">
          <span className="brand__mark">HA</span>
          <span>
            <strong>HimalayaAir</strong>
            <small>Kathmandu Valley air-quality intelligence</small>
          </span>
        </a>
        <nav aria-label="Dashboard sections">
          <a href="#map">Map</a>
          <a href="#charts">PM2.5</a>
          <a href="#pipeline">Pipeline</a>
          <a href="#method">Method</a>
        </nav>
      </header>

      <main id="top">
        <section className="hero">
          <div className="hero__copy">
            <span className="eyebrow">Live dashboard core</span>
            <h1>Pollution signals with source honesty built into the interface.</h1>
            <p>
              The dashboard prioritizes observed OpenAQ sensors, degrades to recent or modeled coverage when needed,
              and exposes confidence, freshness, and provenance on every current view.
            </p>
          </div>
          <AqiGauge aqi={dashboard.valley?.composite_aqi ?? dashboard.stations?.valley_composite_aqi ?? null} label="Valley AQI" />
        </section>

        <CoverageRibbon
          coverage={coverage}
          lastUpdated={lastUpdated}
          websocketStatus={liveFeed.status}
          refreshing={dashboard.refreshing}
        />

        {dashboard.loading && !dashboard.stations && (
          <LoadingState title="Loading dashboard state" detail="Fetching stations, interpolation, charts, and pipeline health from FastAPI." />
        )}

        {dashboard.error && <ErrorPanel message={dashboard.error} onRetry={() => void dashboard.refresh()} />}

        <section className="metrics-grid" aria-label="Dashboard summary metrics">
          <MetricCard label="Coverage" value={formatCoverageMode(coverage?.coverage_mode)} detail={coverage?.message ?? 'Waiting for API coverage metadata.'} />
          <MetricCard label="Stations" value={`${reportingStations}/${activeStations}`} detail="current AQI reporting stations over active stations" />
          <MetricCard label="Source" value={dashboard.valley?.source ?? selectedStation?.source ?? 'not reported'} detail="dominant current source from API metadata" />
        </section>

        <section id="map" className="live-grid">
          <LiveMap
            stations={sortedStations}
            interpolation={dashboard.interpolation}
            selectedStationId={selectedStationId}
            showHeatmap={showHeatmap}
            onSelectStation={setSelectedStationId}
            onToggleHeatmap={() => setShowHeatmap((current) => !current)}
          />
          <StationPopup
            station={selectedStation}
            current={selectedCurrent.current}
            loading={selectedCurrent.loading}
            error={selectedCurrent.error}
          />
        </section>

        <section id="charts" className="lower-grid">
          <Pm25Chart histories={dashboard.histories} />
          <ProvenancePanel stations={dashboard.stations} valley={dashboard.valley} />
        </section>

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
