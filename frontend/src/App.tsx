import { useCallback, useEffect, useMemo, useState } from 'react';

import { ErrorPanel } from './components/ErrorPanel';
import { ForecastPanel } from './components/ForecastPanel';
import { GreetingSummaryDialog } from './components/GreetingSummaryDialog';
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
import { getHealthAdvisory } from './services/api';
import type { HealthAdvisoryResponse, NearestStation, StationsResponse, WebSocketEvent } from './types/api';

const GREETING_DIALOG_SESSION_KEY = 'himalayaair.greeting.dismissed.v1';
const LOCATION_FORECAST_SESSION_KEY = 'himalayaair.locationForecast.v1';

type LocationForecastStatus = 'idle' | 'locating' | 'nearest' | 'manual' | 'denied' | 'unavailable' | 'error';

interface LocationForecastState {
  status: LocationForecastStatus;
  message: string;
  nearestStation: NearestStation | null;
  advisory: HealthAdvisoryResponse | null;
}

function App() {
  const dashboard = useDashboardData();
  const [selectedStationId, setSelectedStationId] = useState<number | null>(null);
  const [forecastStationId, setForecastStationId] = useState<number | null>(null);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [heatmapChangedByUser, setHeatmapChangedByUser] = useState(false);
  const [historicalPollutant, setHistoricalPollutant] = useState('pm25');
  const [showGreetingDialog, setShowGreetingDialog] = useState(() => shouldShowGreetingDialog());
  const [locationForecast, setLocationForecast] = useState<LocationForecastState>(() => readLocationForecastState());

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

  const setLocationForecastState = useCallback((state: LocationForecastState) => {
    setLocationForecast(state);
    writeSessionValue(LOCATION_FORECAST_SESSION_KEY, JSON.stringify(state));
  }, []);

  const loadLocationAdvisory = useCallback(async (lat: number, lon: number) => {
    try {
      const advisory = await getHealthAdvisory(lat, lon);
      if (advisory.nearest_station) {
        const state: LocationForecastState = {
          status: 'nearest',
          message: `Forecast is based on nearest station ${advisory.nearest_station.name}.`,
          nearestStation: advisory.nearest_station,
          advisory,
        };
        setSelectedStationId(advisory.nearest_station.id);
        setForecastStationId(advisory.nearest_station.id);
        setLocationForecastState(state);
        return;
      }

      setLocationForecastState({
        status: 'unavailable',
        message: 'No nearest station was returned. Forecast uses the default Kathmandu station.',
        nearestStation: null,
        advisory,
      });
    } catch {
      const state = fallbackLocationForecast('Location advisory failed. Forecast uses the default Kathmandu station.', 'error');
      setLocationForecastState(state);
    }
  }, [setLocationForecastState]);

  useEffect(() => {
    if (sortedStations.length === 0) {
      return;
    }
    const selectedStillExists = selectedStationId !== null && sortedStations.some((station) => station.id === selectedStationId);
    if (!selectedStillExists) {
      setSelectedStationId(sortedStations[0].id);
    }
    if (forecastStationId === null) {
      setForecastStationId(sortedStations[0].id);
    }
  }, [forecastStationId, selectedStationId, sortedStations]);

  useEffect(() => {
    if (heatmapChangedByUser || !dashboard.interpolation || dashboard.interpolation.insufficient_data) {
      return;
    }
    if (dashboard.interpolation.coverage_mode === 'MODELED_BASELINE') {
      setShowHeatmap(true);
    }
  }, [dashboard.interpolation, heatmapChangedByUser]);

  useEffect(() => {
    if (!showGreetingDialog || locationForecast.status !== 'idle') {
      return;
    }

    if (!('geolocation' in navigator)) {
      const state = fallbackLocationForecast('Browser location is unavailable. Forecast uses the default Kathmandu station.');
      setLocationForecastState(state);
      return;
    }

    setLocationForecastState({
      status: 'locating',
      message: 'Waiting for browser location to choose the nearest forecast station.',
      nearestStation: null,
      advisory: null,
    });

    navigator.geolocation.getCurrentPosition(
      (position) => {
        void loadLocationAdvisory(position.coords.latitude, position.coords.longitude);
      },
      (error) => {
        const denied = error.code === error.PERMISSION_DENIED;
        const state = fallbackLocationForecast(
          denied
            ? 'Location permission was denied. Forecast uses the default Kathmandu station.'
            : 'Browser location could not be resolved. Forecast uses the default Kathmandu station.',
          denied ? 'denied' : 'unavailable',
        );
        setLocationForecastState(state);
      },
      { enableHighAccuracy: false, maximumAge: 10 * 60 * 1000, timeout: 8000 },
    );
  }, [loadLocationAdvisory, locationForecast.status, setLocationForecastState, showGreetingDialog]);

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
  const selectedOrNearestStationName = locationForecast.nearestStation?.name ?? selectedStation?.name ?? null;
  const forecastBasisMessage = locationForecast.message || 'Forecast uses the default Kathmandu station.';

  const handleForecastStationChange = useCallback((stationId: number) => {
    const station = sortedStations.find((candidate) => candidate.id === stationId);
    setForecastStationId(stationId);
    setLocationForecastState({
      ...locationForecast,
      status: 'manual',
      message: `Forecast station changed manually${station ? ` to ${station.name}` : ''}.`,
    });
  }, [locationForecast, setLocationForecastState, sortedStations]);

  const dismissGreetingDialog = useCallback(() => {
    writeSessionValue(GREETING_DIALOG_SESSION_KEY, 'true');
    setShowGreetingDialog(false);
  }, []);

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
            onSelectStation={setSelectedStationId}
            onToggleHeatmap={() => {
              setHeatmapChangedByUser(true);
              setShowHeatmap((current) => !current);
            }}
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

        <ForecastPanel
          stations={sortedStations}
          pollutant={historicalPollutant}
          stationId={forecastStationId}
          stationBasisMessage={forecastBasisMessage}
          onStationChange={handleForecastStationChange}
        />

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
      <GreetingSummaryDialog
        open={showGreetingDialog}
        greeting={greeting}
        valleyAqi={locationForecast.advisory?.aqi ?? displayAqi}
        coverageMode={locationForecast.advisory?.coverage_mode ?? coverage?.coverage_mode}
        freshStationCount={locationForecast.advisory?.fresh_station_count ?? coverage?.fresh_station_count ?? null}
        recentStationCount={locationForecast.advisory?.recent_station_count ?? coverage?.recent_station_count ?? null}
        source={dashboard.valley?.source ?? selectedStation?.source ?? null}
        observationType={selectedStation?.observation_type ?? null}
        lastUpdated={lastUpdated}
        selectedStationName={selectedOrNearestStationName}
        nearestStation={locationForecast.nearestStation}
        forecastStationId={forecastStationId}
        pollutant="pm25"
        forecastBasisMessage={forecastBasisMessage}
        locationStatus={locationForecast.message}
        onDismiss={dismissGreetingDialog}
      />
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

function shouldShowGreetingDialog(): boolean {
  return readSessionValue(GREETING_DIALOG_SESSION_KEY) !== 'true';
}

function readLocationForecastState(): LocationForecastState {
  const stored = readSessionValue(LOCATION_FORECAST_SESSION_KEY);
  if (!stored) {
    return fallbackLocationForecast('Waiting for browser location to choose a forecast station.', 'idle');
  }

  try {
    const parsed = JSON.parse(stored) as Partial<LocationForecastState>;
    if (!parsed.status || !isLocationForecastStatus(parsed.status)) {
      return fallbackLocationForecast('Forecast uses the default Kathmandu station.');
    }
    if (parsed.status === 'locating') {
      return fallbackLocationForecast('Location lookup did not complete. Forecast uses the default Kathmandu station.');
    }
    return {
      status: parsed.status,
      message: parsed.message ?? 'Forecast uses the default Kathmandu station.',
      nearestStation: parsed.nearestStation ?? null,
      advisory: parsed.advisory ?? null,
    };
  } catch {
    return fallbackLocationForecast('Forecast uses the default Kathmandu station.');
  }
}

function fallbackLocationForecast(
  message: string,
  status: LocationForecastStatus = 'unavailable',
): LocationForecastState {
  return {
    status,
    message,
    nearestStation: null,
    advisory: null,
  };
}

function isLocationForecastStatus(value: string): value is LocationForecastStatus {
  return ['idle', 'locating', 'nearest', 'manual', 'denied', 'unavailable', 'error'].includes(value);
}

function readSessionValue(key: string): string | null {
  try {
    return window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeSessionValue(key: string, value: string): void {
  try {
    window.sessionStorage.setItem(key, value);
  } catch {
    return;
  }
}
