import type { ForecastPoint, HistoryPoint, ValleyHistoryPoint } from '../types/api';

export type HistoryGranularity = 'hour' | 'day';
export type HistoryScope = 'valley' | 'station';

export interface ExplorerPoint {
  timestamp: string;
  value: number | null;
  source: string | null;
}

export interface DailyCell {
  dayKey: string;
  timestamp: string;
  value: number | null;
}

export interface BestWindow {
  start: string;
  end: string;
  avgAqi: number;
}

const DAY_MS = 24 * 60 * 60 * 1000;

export function clampHistoryHours(hours: number): number {
  return Math.max(1, Math.min(24 * 365, Math.round(hours)));
}

export function rangeToHours(startIso: string, endIso: string): number {
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  if (Number.isNaN(start) || Number.isNaN(end) || end <= start) {
    return 24;
  }
  return clampHistoryHours(Math.ceil((end - start) / (60 * 60 * 1000)));
}

export function buildExplorerPointsFromStation(readings: HistoryPoint[]): ExplorerPoint[] {
  return readings.map((reading) => ({
    timestamp: reading.timestamp,
    value: reading.aqi ?? null,
    source: reading.source,
  }));
}

export function buildExplorerPointsFromValley(points: ValleyHistoryPoint[]): ExplorerPoint[] {
  return points.map((point) => ({
    timestamp: point.bucket_start,
    value: point.avg_aqi,
    source: null,
  }));
}

export function filterPointsToRange(points: ExplorerPoint[], startIso: string, endIso: string): ExplorerPoint[] {
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  return points.filter((point) => {
    const timestamp = new Date(point.timestamp).getTime();
    return timestamp >= start && timestamp <= end;
  });
}

export function aggregateToDaily(points: ExplorerPoint[], timeZone: string): ExplorerPoint[] {
  const dayMap = new Map<string, { sum: number; count: number; representative: string }>();
  points.forEach((point) => {
    const dayKey = toDayKey(point.timestamp, timeZone);
    if (!dayKey) {
      return;
    }
    const entry = dayMap.get(dayKey) ?? { sum: 0, count: 0, representative: point.timestamp };
    if (typeof point.value === 'number') {
      entry.sum += point.value;
      entry.count += 1;
    }
    dayMap.set(dayKey, entry);
  });
  return [...dayMap.entries()]
    .map(([dayKey, entry]) => ({
      timestamp: dayKeyToMiddayIso(dayKey),
      value: entry.count > 0 ? round(entry.sum / entry.count, 1) : null,
      source: null,
    }))
    .sort((left, right) => new Date(left.timestamp).getTime() - new Date(right.timestamp).getTime());
}

export function buildCalendarCells(points: ExplorerPoint[], startIso: string, endIso: string, timeZone: string): DailyCell[] {
  const valuesByDay = new Map<string, number>();
  aggregateToDaily(points, timeZone).forEach((point) => {
    const dayKey = toDayKey(point.timestamp, timeZone);
    if (dayKey && typeof point.value === 'number') {
      valuesByDay.set(dayKey, point.value);
    }
  });

  const start = startOfDayUtc(startIso);
  const end = startOfDayUtc(endIso);
  const cells: DailyCell[] = [];
  for (let current = start; current <= end; current += DAY_MS) {
    const dayIso = new Date(current).toISOString();
    const dayKey = toDayKey(dayIso, timeZone);
    if (!dayKey) {
      continue;
    }
    cells.push({
      dayKey,
      timestamp: dayIso,
      value: valuesByDay.get(dayKey) ?? null,
    });
  }
  return cells;
}

export function bestSixHourWindows(forecast: ForecastPoint[], limit = 3): BestWindow[] {
  if (forecast.length < 6) {
    return [];
  }
  const windows: BestWindow[] = [];
  for (let index = 0; index <= forecast.length - 6; index += 1) {
    const slice = forecast.slice(index, index + 6);
    const average = slice.reduce((sum, row) => sum + row.predicted_aqi, 0) / 6;
    windows.push({
      start: slice[0].target_timestamp,
      end: slice[slice.length - 1].target_timestamp,
      avgAqi: round(average, 1),
    });
  }
  return windows.sort((left, right) => left.avgAqi - right.avgAqi).slice(0, limit);
}

function toDayKey(timestamp: string, timeZone: string): string | null {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date);
  const year = parts.find((part) => part.type === 'year')?.value;
  const month = parts.find((part) => part.type === 'month')?.value;
  const day = parts.find((part) => part.type === 'day')?.value;
  if (!year || !month || !day) {
    return null;
  }
  return `${year}-${month}-${day}`;
}

function dayKeyToMiddayIso(dayKey: string): string {
  return `${dayKey}T12:00:00Z`;
}

function startOfDayUtc(value: string): number {
  const date = new Date(value);
  const start = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(), 0, 0, 0, 0));
  return start.getTime();
}

function round(value: number, digits: number): number {
  const multiplier = 10 ** digits;
  return Math.round(value * multiplier) / multiplier;
}
