import type { Confidence, CoverageMode, InterpolationResponse, StationSummary } from '../types/api';

const KATHMANDU_BOUNDS = {
  min_lat: 27.55,
  max_lat: 27.8,
  min_lon: 85.2,
  max_lon: 85.5,
};
const KATHMANDU_CENTER_LAT = 27.7172;
const KATHMANDU_CENTER_LON = 85.324;
const METERS_PER_DEGREE_LAT = 111_320;
const METERS_PER_DEGREE_LON = METERS_PER_DEGREE_LAT * Math.cos((KATHMANDU_CENTER_LAT * Math.PI) / 180);

interface StationHeatmapOptions {
  rows?: number;
  cols?: number;
  power?: number;
  coverageMode?: CoverageMode;
  confidence?: Confidence;
  source?: string;
  computedAt?: string;
  message?: string;
}

interface ProjectedStation {
  x: number;
  y: number;
  aqi: number;
}

export function buildStationHeatmap(
  stations: StationSummary[],
  options: StationHeatmapOptions = {},
): InterpolationResponse | null {
  const usable = stations.filter(
    (station): station is StationSummary & { current_aqi: number } =>
      station.current_aqi !== null && station.current_aqi !== undefined,
  );
  const rows = options.rows ?? 50;
  const cols = options.cols ?? 50;
  if (usable.length === 0 || rows <= 0 || cols <= 0) {
    return null;
  }

  const projected = usable.map((station) => ({
    x: xMeters(station.lon),
    y: yMeters(station.lat),
    aqi: station.current_aqi,
  }));
  const power = options.power ?? 2;
  const latStep = rows <= 1 ? 0 : (KATHMANDU_BOUNDS.max_lat - KATHMANDU_BOUNDS.min_lat) / (rows - 1);
  const lonStep = cols <= 1 ? 0 : (KATHMANDU_BOUNDS.max_lon - KATHMANDU_BOUNDS.min_lon) / (cols - 1);
  const values: Array<Array<number | null>> = [];

  for (let row = 0; row < rows; row += 1) {
    const lat = KATHMANDU_BOUNDS.min_lat + row * latStep;
    const y = yMeters(lat);
    const rowValues: Array<number | null> = [];
    for (let col = 0; col < cols; col += 1) {
      const lon = KATHMANDU_BOUNDS.min_lon + col * lonStep;
      rowValues.push(idwValue(projected, xMeters(lon), y, power));
    }
    values.push(rowValues);
  }

  const firstStation = usable[0];
  return {
    grid: {
      rows,
      cols,
      bounds: KATHMANDU_BOUNDS,
      values,
    },
    station_count: usable.length,
    coverage_mode: options.coverageMode ?? firstStation.coverage_mode ?? 'STATION_ONLY',
    confidence: options.confidence ?? firstStation.confidence ?? 'low',
    source: options.source ?? firstStation.source ?? 'station_snapshot',
    computed_at: options.computedAt ?? latestSeen(usable) ?? '1970-01-01T00:00:00.000Z',
    insufficient_data: false,
    message: options.message ?? 'Showing station AQI surface.',
  };
}

function latestSeen(stations: StationSummary[]): string | null {
  const timestamps = stations
    .map((station) => station.last_seen)
    .filter((timestamp): timestamp is string => timestamp !== null)
    .sort();
  return timestamps.length > 0 ? timestamps[timestamps.length - 1] : null;
}

function idwValue(stations: ProjectedStation[], x: number, y: number, power: number): number {
  let weightedSum = 0;
  let weightTotal = 0;
  for (const station of stations) {
    const distance = Math.hypot(station.x - x, station.y - y);
    if (distance <= 1) {
      return station.aqi;
    }
    const weight = 1 / distance ** power;
    weightedSum += weight * station.aqi;
    weightTotal += weight;
  }
  return Math.round((weightedSum / weightTotal) * 100) / 100;
}

function xMeters(lon: number): number {
  return (lon - KATHMANDU_CENTER_LON) * METERS_PER_DEGREE_LON;
}

function yMeters(lat: number): number {
  return (lat - KATHMANDU_CENTER_LAT) * METERS_PER_DEGREE_LAT;
}
