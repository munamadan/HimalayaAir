import { useCallback, useEffect, useState } from 'react';

import {
  getInterpolationCurrent,
  getPipelineHealth,
  getStationHistory,
  getStations,
  getValleyCurrent,
} from '../services/api';
import type {
  InterpolationResponse,
  PipelineHealthResponse,
  StationHistorySet,
  StationsResponse,
  ValleyCurrentResponse,
} from '../types/api';
import { sortStationsForDisplay } from '../lib/aqi';

interface DashboardDataState {
  stations: StationsResponse | null;
  valley: ValleyCurrentResponse | null;
  interpolation: InterpolationResponse | null;
  pipelineHealth: PipelineHealthResponse | null;
  histories: StationHistorySet[];
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  refresh: (options?: { silent?: boolean }) => Promise<void>;
  applyStationSnapshot: (snapshot: StationsResponse) => void;
}

export function useDashboardData(): DashboardDataState {
  const [stations, setStations] = useState<StationsResponse | null>(null);
  const [valley, setValley] = useState<ValleyCurrentResponse | null>(null);
  const [interpolation, setInterpolation] = useState<InterpolationResponse | null>(null);
  const [pipelineHealth, setPipelineHealth] = useState<PipelineHealthResponse | null>(null);
  const [histories, setHistories] = useState<StationHistorySet[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (options: { silent?: boolean } = {}) => {
    const silent = options.silent ?? false;
    if (!silent) {
      setLoading(true);
    }
    setRefreshing(silent);
    setError(null);

    const [stationsResult, valleyResult, interpolationResult, pipelineResult] = await Promise.allSettled([
      getStations(),
      getValleyCurrent(),
      getInterpolationCurrent('pm25'),
      getPipelineHealth(),
    ]);

    const failures: string[] = [];
    let nextStations: StationsResponse | null = null;

    if (stationsResult.status === 'fulfilled') {
      nextStations = stationsResult.value;
      setStations(stationsResult.value);
    } else {
      failures.push(errorMessage(stationsResult.reason, 'station snapshot'));
    }

    if (valleyResult.status === 'fulfilled') {
      setValley(valleyResult.value);
    } else {
      failures.push(errorMessage(valleyResult.reason, 'valley current state'));
    }

    if (interpolationResult.status === 'fulfilled') {
      setInterpolation(interpolationResult.value);
    } else {
      failures.push(errorMessage(interpolationResult.reason, 'interpolation grid'));
    }

    if (pipelineResult.status === 'fulfilled') {
      setPipelineHealth(pipelineResult.value);
    } else {
      failures.push(errorMessage(pipelineResult.reason, 'pipeline health'));
    }

    if (nextStations) {
      setHistories(await loadHistories(nextStations));
    }

    if (failures.length > 0) {
      setError(failures.join(' '));
    }

    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const applyStationSnapshot = useCallback((snapshot: StationsResponse) => {
    setStations(snapshot);
    void loadHistories(snapshot).then(setHistories);
  }, []);

  return {
    stations,
    valley,
    interpolation,
    pipelineHealth,
    histories,
    loading,
    refreshing,
    error,
    refresh: load,
    applyStationSnapshot,
  };
}

async function loadHistories(stations: StationsResponse): Promise<StationHistorySet[]> {
  const stationSlice = sortStationsForDisplay(stations.stations)
    .filter((station) => station.active)
    .slice(0, 5);

  const results = await Promise.allSettled(
    stationSlice.map(async (station) => ({
      station,
      history: await getStationHistory(station.id, 'pm25', 24),
    })),
  );

  return results.flatMap((result) => (result.status === 'fulfilled' ? [result.value] : []));
}

function errorMessage(error: unknown, label: string): string {
  if (error instanceof Error) {
    return `Could not load ${label}: ${error.message}.`;
  }
  return `Could not load ${label}.`;
}
