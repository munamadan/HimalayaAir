import type { InterpolationResponse } from '../types/api';

import { hasUsableHeatmap } from './heatmapCanvas';

const LAST_GOOD_INTERPOLATION_KEY = 'himalayaair:last-aqi-grid';
const LAST_STATION_HEATMAP_KEY = 'himalayaair:last-station-aqi-grid';

export function loadLastGoodInterpolation(): InterpolationResponse | null {
  return loadUsableInterpolation(LAST_GOOD_INTERPOLATION_KEY);
}

export function saveLastGoodInterpolation(interpolation: InterpolationResponse): void {
  saveUsableInterpolation(LAST_GOOD_INTERPOLATION_KEY, interpolation);
}

export function loadLastStationHeatmap(): InterpolationResponse | null {
  return loadUsableInterpolation(LAST_STATION_HEATMAP_KEY);
}

export function saveLastStationHeatmap(interpolation: InterpolationResponse): void {
  saveUsableInterpolation(LAST_STATION_HEATMAP_KEY, interpolation);
}

function loadUsableInterpolation(key: string): InterpolationResponse | null {
  const storage = getStorage();
  if (!storage) {
    return null;
  }
  try {
    const raw = storage.getItem(key);
    if (!raw) {
      return null;
    }
    return toUsableInterpolation(JSON.parse(raw));
  } catch {
    return null;
  }
}

function saveUsableInterpolation(key: string, interpolation: InterpolationResponse): void {
  const storage = getStorage();
  if (!storage || !hasUsableHeatmap(interpolation)) {
    return;
  }
  const existing = loadUsableInterpolation(key);
  if (existing && Date.parse(existing.computed_at) > Date.parse(interpolation.computed_at)) {
    return;
  }
  try {
    storage.setItem(key, JSON.stringify(interpolation));
  } catch {
    return;
  }
}

function toUsableInterpolation(value: unknown): InterpolationResponse | null {
  if (!value || typeof value !== 'object') {
    return null;
  }
  const candidate = value as InterpolationResponse;
  if (!candidate.grid || !Array.isArray(candidate.grid.values)) {
    return null;
  }
  return hasUsableHeatmap(candidate) ? candidate : null;
}

function getStorage(): Storage | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}
