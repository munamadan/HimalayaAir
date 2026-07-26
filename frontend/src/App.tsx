import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  Activity,
  CalendarClock,
  History,
  Layers3,
  MapPin,
  Waves,
  Wind,
  X,
} from 'lucide-react';

import { AppRail } from './components/AppRail';
import { AppTopBar } from './components/AppTopBar';
import { ForecastPanel } from './components/ForecastPanel';
import { HistoricalExplorer } from './components/HistoricalExplorer';
import { InspectorPanel } from './components/InspectorPanel';
import { LiveMap } from './components/LiveMap';
import { StationPopup } from './components/StationPopup';
import { TimelineSlider } from './components/TimelineSlider';
import { ValleySummary } from './components/ValleySummary';
import { useDashboardData } from './hooks/useDashboardData';
import { useLiveFeed } from './hooks/useLiveFeed';
import { useResponsiveMode } from './hooks/useResponsiveMode';
import { useStationCurrent } from './hooks/useStationCurrent';
import { useTimelineSlider } from './hooks/useTimelineSlider';
import { sortStationsForDisplay } from './lib/aqi';
import {
  loadLastGoodInterpolation,
  loadLastStationHeatmap,
  saveLastGoodInterpolation,
  saveLastStationHeatmap,
} from './lib/heatmapCache';
import { hasUsableHeatmap } from './lib/heatmapCanvas';
import { buildStationHeatmap } from './lib/stationHeatmap';
import { getHealthAdvisory } from './services/api';
import type {
  CoverageMode,
  StationSummary,
  StationsResponse,
  WebSocketEvent,
} from './types/api';
import type {
  InspectorMode,
  InspectorVisibility,
  LocationStatus,
  MobileSheetSnap,
} from './types/ui';

function App() {
  const dashboard = useDashboardData();
  const timeline = useTimelineSlider({ currentInterpolation: dashboard.interpolation });
  const isMobile = useResponsiveMode();
  const [selectedStationId, setSelectedStationId] = useState<number | null>(null);
  const [forecastStationId, setForecastStationId] = useState<number | null>(null);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showWind, setShowWind] = useState(true);
  const [showStations, setShowStations] = useState(true);
  const [historicalPollutant, setHistoricalPollutant] = useState('pm25');
  const [inspectorMode, setInspectorMode] = useState<InspectorMode>('valley');
  const [inspectorVisibility, setInspectorVisibility] = useState<InspectorVisibility>('open');
  const [mobileSheetSnap, setMobileSheetSnap] = useState<MobileSheetSnap>('half');
  const [locationStatus, setLocationStatus] = useState<LocationStatus>('idle');
  const [locationNotice, setLocationNotice] = useState<string | null>(null);
  const [cachedStationHeatmap, setCachedStationHeatmap] = useState(() => loadLastStationHeatmap());
  const [lastGoodInterpolation, setLastGoodInterpolation] = useState(() => loadLastGoodInterpolation());

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
  const selectedStation =
    sortedStations.find((station) => station.id === selectedStationId) ?? null;
  const selectedCurrent = useStationCurrent(selectedStationId);
  const coverage = dashboard.stations ?? dashboard.valley;
  const lastUpdated =
    liveFeed.lastMessageAt ??
    dashboard.stations?.timestamp ??
    dashboard.valley?.timestamp ??
    null;
  const displayAqi =
    dashboard.valley?.composite_aqi ??
    dashboard.stations?.valley_composite_aqi ??
    null;
  const effectiveForecastStationId =
    forecastStationId ?? selectedStationId ?? sortedStations[0]?.id ?? null;
  const forecastStation = sortedStations.find(
    (station) => station.id === effectiveForecastStationId,
  );
  const forecastBasisMessage = forecastStation
    ? `Forecast for ${forecastStation.name}.`
    : 'Choose a station to view the 72-hour forecast.';
  const inspectorOpen = isMobile || inspectorVisibility === 'open';
  const windAvailable = dashboard.windGrid !== null;
  const activeInterpolation = timeline.activeInterpolation;
  const activeInterpolationUsable = hasUsableHeatmap(activeInterpolation);
  const latestStationHeatmap = useMemo(
    () =>
      buildStationHeatmap(sortedStations, {
        rows: activeInterpolation?.grid.rows ?? 50,
        cols: activeInterpolation?.grid.cols ?? 50,
        coverageMode: dashboard.stations?.coverage_mode ?? activeInterpolation?.coverage_mode,
        confidence: dashboard.stations?.confidence ?? 'low',
        source: 'station_snapshot',
        computedAt: dashboard.stations?.timestamp,
        message: 'Showing the latest station AQI surface.',
      }),
    [
      activeInterpolation?.coverage_mode,
      activeInterpolation?.grid.cols,
      activeInterpolation?.grid.rows,
      dashboard.stations?.confidence,
      dashboard.stations?.coverage_mode,
      dashboard.stations?.timestamp,
      sortedStations,
    ],
  );
  const displayInterpolation = activeInterpolationUsable
    ? activeInterpolation
    : latestStationHeatmap ?? cachedStationHeatmap ?? lastGoodInterpolation;
  const heatmapAvailable = hasUsableHeatmap(displayInterpolation);
  const usingFallbackHeatmap = !activeInterpolationUsable && heatmapAvailable;
  const heatmapMessage = usingFallbackHeatmap
    ? displayInterpolation?.message ?? 'Showing the last known AQI surface.'
    : null;

  useEffect(() => {
    if (activeInterpolationUsable && activeInterpolation) {
      saveLastGoodInterpolation(activeInterpolation);
      setLastGoodInterpolation(activeInterpolation);
    }
  }, [activeInterpolation, activeInterpolationUsable]);

  useEffect(() => {
    if (latestStationHeatmap) {
      saveLastStationHeatmap(latestStationHeatmap);
      setCachedStationHeatmap(latestStationHeatmap);
    }
  }, [latestStationHeatmap]);

  useEffect(() => {
    if (!locationNotice) {
      return;
    }
    const timeout = window.setTimeout(() => setLocationNotice(null), 6000);
    return () => window.clearTimeout(timeout);
  }, [locationNotice]);

  const openInspector = useCallback(
    (mode: InspectorMode) => {
      setInspectorMode(mode);
      setInspectorVisibility('open');
      if (isMobile) {
        setMobileSheetSnap(mode === 'forecast' || mode === 'history' ? 'full' : 'half');
      }
    },
    [isMobile],
  );

  const handleSelectStation = useCallback(
    (station: StationSummary) => {
      setSelectedStationId(station.id);
      setForecastStationId((current) => current ?? station.id);
      openInspector('station');
    },
    [openInspector],
  );

  const handleMapStationSelect = useCallback(
    (stationId: number) => {
      const station = sortedStations.find((candidate) => candidate.id === stationId);
      if (station) {
        handleSelectStation(station);
      }
    },
    [handleSelectStation, sortedStations],
  );

  const handleModeChange = useCallback(
    (mode: InspectorMode) => {
      if (mode === 'forecast' && effectiveForecastStationId === null && sortedStations[0]) {
        setForecastStationId(sortedStations[0].id);
      }
      openInspector(mode);
    },
    [effectiveForecastStationId, openInspector, sortedStations],
  );

  const handleForecastStationChange = useCallback((stationId: number) => {
    setForecastStationId(stationId);
    setSelectedStationId(stationId);
  }, []);

  const handleLocate = useCallback(() => {
    if (!('geolocation' in navigator)) {
      setLocationStatus('unavailable');
      setLocationNotice('Location is not available in this browser.');
      return;
    }

    setLocationStatus('locating');
    setLocationNotice('Finding the nearest reporting station...');
    navigator.geolocation.getCurrentPosition(
      (position) => {
        void getHealthAdvisory(position.coords.latitude, position.coords.longitude)
          .then((advisory) => {
            const nearest = advisory.nearest_station;
            if (!nearest) {
              setLocationStatus('unavailable');
              setLocationNotice('No nearby reporting station is available.');
              return;
            }

            setSelectedStationId(nearest.id);
            setForecastStationId(nearest.id);
            openInspector('station');
            setLocationStatus('success');
            setLocationNotice(
              `${nearest.name} is the nearest station, ${nearest.distance_km.toFixed(1)} km away.`,
            );
          })
          .catch(() => {
            setLocationStatus('error');
            setLocationNotice('The nearest station could not be loaded.');
          });
      },
      (error) => {
        const denied = error.code === error.PERMISSION_DENIED;
        setLocationStatus(denied ? 'denied' : 'unavailable');
        setLocationNotice(
          denied
            ? 'Location permission was denied.'
            : 'Your location could not be determined.',
        );
      },
      {
        enableHighAccuracy: false,
        maximumAge: 10 * 60 * 1000,
        timeout: 8000,
      },
    );
  }, [openInspector]);

  const inspectorHeading = getInspectorHeading(inspectorMode, selectedStation);
  const inspectorContent = getInspectorContent({
    mode: inspectorMode,
    selectedStation,
    selectedCurrent,
    sortedStations,
    displayAqi,
    coverageMode: coverage?.coverage_mode,
    dominantPollutant: dashboard.valley?.dominant_pollutant,
    lastUpdated,
    historicalPollutant,
    forecastStationId: effectiveForecastStationId,
    forecastBasisMessage,
    onSelectStation: handleSelectStation,
    onOpenValley: () => openInspector('valley'),
    onOpenForecast: () => openInspector('forecast'),
    onForecastStationChange: handleForecastStationChange,
    onPollutantChange: setHistoricalPollutant,
  });

  return (
    <div
      className={`map-app map-app--inspector-${inspectorVisibility} map-app--sheet-${mobileSheetSnap}`}
    >
      <LiveMap
        stations={sortedStations}
        interpolation={displayInterpolation}
        windGrid={dashboard.windGrid}
        selectedStationId={selectedStationId}
        showHeatmap={showHeatmap}
        showWind={showWind}
        showStations={showStations}
        heatmapMessage={heatmapMessage}
        onSelectStation={handleMapStationSelect}
      />

      <AppTopBar
        stations={sortedStations}
        selectedStation={selectedStation}
        currentAqi={displayAqi}
        coverageMode={coverage?.coverage_mode}
        liveStatus={liveFeed.status}
        refreshing={dashboard.refreshing}
        locationStatus={locationStatus}
        onSelectStation={handleSelectStation}
        onRefresh={() => void dashboard.refresh({ silent: true })}
        onLocate={handleLocate}
      />

      <AppRail
        activeMode={inspectorMode}
        showHeatmap={showHeatmap}
        showWind={showWind}
        showStations={showStations}
        heatmapAvailable={heatmapAvailable}
        heatmapMessage={heatmapMessage}
        windAvailable={windAvailable}
        onModeChange={handleModeChange}
        onToggleHeatmap={() => setShowHeatmap((current) => !current)}
        onToggleWind={() => setShowWind((current) => !current)}
        onToggleStations={() => setShowStations((current) => !current)}
      />

      {inspectorOpen && (
        <InspectorPanel
          title={inspectorHeading.title}
          eyebrow={inspectorHeading.eyebrow}
          open
          mobileSnap={mobileSheetSnap}
          onClose={() => setInspectorVisibility('collapsed')}
          onSnapChange={setMobileSheetSnap}
        >
          {inspectorContent}
        </InspectorPanel>
      )}

      <TimelineSlider
        frameIndex={timeline.frameIndex}
        frameCount={timeline.frameCount}
        activeFrame={timeline.activeFrame}
        isLive={timeline.isLive}
        isPlaying={timeline.isPlaying}
        isAvailable={timeline.isAvailable}
        isLoading={timeline.isLoading}
        onFrameChange={timeline.setFrameIndex}
        onTogglePlay={timeline.togglePlay}
      />

      {dashboard.loading && !dashboard.stations && (
        <div className="map-state-note" role="status">
          Loading air-quality map...
        </div>
      )}

      {dashboard.error && (
        <div className="map-state-note map-state-note--error" role="alert">
          <span>Some air-quality data did not load.</span>
          <button type="button" onClick={() => void dashboard.refresh()}>
            Retry
          </button>
        </div>
      )}

      {locationNotice && (
        <div
          className={`app-toast app-toast--${locationStatus}`}
          role={locationStatus === 'error' || locationStatus === 'denied' ? 'alert' : 'status'}
        >
          <span>{locationNotice}</span>
          <button
            type="button"
            aria-label="Dismiss location message"
            onClick={() => setLocationNotice(null)}
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>
      )}

      <MobileNavigation
        activeMode={inspectorMode}
        showHeatmap={showHeatmap}
        showWind={showWind}
        showStations={showStations}
        windAvailable={windAvailable}
        onModeChange={handleModeChange}
        onToggleHeatmap={() => setShowHeatmap((current) => !current)}
        onToggleWind={() => setShowWind((current) => !current)}
        onToggleStations={() => setShowStations((current) => !current)}
      />
    </div>
  );
}

interface InspectorContentOptions {
  mode: InspectorMode;
  selectedStation: StationSummary | null;
  selectedCurrent: ReturnType<typeof useStationCurrent>;
  sortedStations: StationSummary[];
  displayAqi: number | null;
  coverageMode: CoverageMode | null | undefined;
  dominantPollutant: string | null | undefined;
  lastUpdated: string | null;
  historicalPollutant: string;
  forecastStationId: number | null;
  forecastBasisMessage: string;
  onSelectStation: (station: StationSummary) => void;
  onOpenValley: () => void;
  onOpenForecast: () => void;
  onForecastStationChange: (stationId: number) => void;
  onPollutantChange: (pollutant: string) => void;
}

function getInspectorContent({
  mode,
  selectedStation,
  selectedCurrent,
  sortedStations,
  displayAqi,
  coverageMode,
  dominantPollutant,
  lastUpdated,
  historicalPollutant,
  forecastStationId,
  forecastBasisMessage,
  onSelectStation,
  onOpenValley,
  onOpenForecast,
  onForecastStationChange,
  onPollutantChange,
}: InspectorContentOptions): ReactNode {
  if (mode === 'station' && selectedStation) {
    return (
      <StationPopup
        station={selectedStation}
        current={selectedCurrent.current}
        loading={selectedCurrent.loading}
        error={selectedCurrent.error}
        onClose={onOpenValley}
      />
    );
  }

  if (mode === 'forecast') {
    return (
      <ForecastPanel
        compact
        stations={sortedStations}
        pollutant={historicalPollutant}
        stationId={forecastStationId}
        stationBasisMessage={forecastBasisMessage}
        onStationChange={onForecastStationChange}
      />
    );
  }

  if (mode === 'history') {
    return (
      <HistoricalExplorer
        compact
        stations={sortedStations}
        pollutant={historicalPollutant}
        onPollutantChange={onPollutantChange}
      />
    );
  }

  return (
    <ValleySummary
      aqi={displayAqi}
      coverageMode={coverageMode}
      dominantPollutant={dominantPollutant}
      lastUpdated={lastUpdated}
      stations={sortedStations}
      onSelectStation={onSelectStation}
      onOpenForecast={onOpenForecast}
    />
  );
}

function getInspectorHeading(
  mode: InspectorMode,
  selectedStation: StationSummary | null,
): { eyebrow: string; title: string } {
  if (mode === 'station' && selectedStation) {
    return { eyebrow: 'Station detail', title: selectedStation.name };
  }
  if (mode === 'forecast') {
    return { eyebrow: 'Plan ahead', title: '72-hour forecast' };
  }
  if (mode === 'history') {
    return { eyebrow: 'Explore patterns', title: 'Air quality history' };
  }
  return { eyebrow: 'Current air quality', title: 'Kathmandu Valley' };
}

interface MobileNavigationProps {
  activeMode: InspectorMode;
  showHeatmap: boolean;
  showWind: boolean;
  showStations: boolean;
  windAvailable: boolean;
  onModeChange: (mode: InspectorMode) => void;
  onToggleHeatmap: () => void;
  onToggleWind: () => void;
  onToggleStations: () => void;
}

function MobileNavigation({
  activeMode,
  showHeatmap,
  showWind,
  showStations,
  windAvailable,
  onModeChange,
  onToggleHeatmap,
  onToggleWind,
  onToggleStations,
}: MobileNavigationProps) {
  return (
    <nav className="mobile-app-nav" aria-label="Application views">
      <MobileNavButton
        label="Now"
        active={activeMode === 'valley' || activeMode === 'station'}
        icon={<Activity size={20} />}
        onClick={() => onModeChange('valley')}
      />
      <MobileNavButton
        label="Forecast"
        active={activeMode === 'forecast'}
        icon={<CalendarClock size={20} />}
        onClick={() => onModeChange('forecast')}
      />
      <MobileNavButton
        label="History"
        active={activeMode === 'history'}
        icon={<History size={20} />}
        onClick={() => onModeChange('history')}
      />
      <details className="mobile-layer-menu">
        <summary aria-label="Map layers">
          <Layers3 size={20} aria-hidden="true" />
          <span>Layers</span>
        </summary>
        <div className="mobile-layer-menu__panel">
          <MobileLayerToggle
            label="AQI surface"
            checked={showHeatmap}
            icon={<Waves size={18} />}
            onChange={onToggleHeatmap}
          />
          <MobileLayerToggle
            label="Wind flow"
            checked={showWind && windAvailable}
            disabled={!windAvailable}
            icon={<Wind size={18} />}
            onChange={onToggleWind}
          />
          <MobileLayerToggle
            label="Stations"
            checked={showStations}
            icon={<MapPin size={18} />}
            onChange={onToggleStations}
          />
        </div>
      </details>
    </nav>
  );
}

interface MobileNavButtonProps {
  label: string;
  active: boolean;
  icon: ReactNode;
  onClick: () => void;
}

function MobileNavButton({ label, active, icon, onClick }: MobileNavButtonProps) {
  return (
    <button
      type="button"
      className={active ? 'mobile-nav-button mobile-nav-button--active' : 'mobile-nav-button'}
      onClick={onClick}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

interface MobileLayerToggleProps {
  label: string;
  checked: boolean;
  disabled?: boolean;
  icon: ReactNode;
  onChange: () => void;
}

function MobileLayerToggle({
  label,
  checked,
  disabled = false,
  icon,
  onChange,
}: MobileLayerToggleProps) {
  return (
    <label className={disabled ? 'mobile-layer-toggle mobile-layer-toggle--disabled' : 'mobile-layer-toggle'}>
      {icon}
      <span>{label}</span>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={onChange}
      />
    </label>
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
