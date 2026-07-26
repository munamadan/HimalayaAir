import { afterEach, describe, expect, it } from 'vitest';

import { loadLastStationHeatmap, saveLastStationHeatmap } from './heatmapCache';
import type { InterpolationResponse } from '../types/api';

describe('heatmap cache', () => {
  afterEach(() => {
    Reflect.deleteProperty(globalThis, 'localStorage');
  });

  it('returns null when browser storage is unavailable', () => {
    expect(loadLastStationHeatmap()).toBeNull();
  });

  it('saves and loads the newest usable station heatmap', () => {
    installLocalStorage();
    const older = interpolation('2026-07-26T00:00:00Z');
    const newer = interpolation('2026-07-26T01:00:00Z');

    saveLastStationHeatmap(older);
    saveLastStationHeatmap(newer);
    expect(loadLastStationHeatmap()?.computed_at).toBe(newer.computed_at);

    saveLastStationHeatmap(older);
    expect(loadLastStationHeatmap()?.computed_at).toBe(newer.computed_at);
  });

  it('ignores insufficient or empty heatmap payloads', () => {
    installLocalStorage();

    saveLastStationHeatmap(interpolation('2026-07-26T00:00:00Z', true));
    expect(loadLastStationHeatmap()).toBeNull();
  });
});

function installLocalStorage(): void {
  const store = new Map<string, string>();
  const storage = {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (key: string) => (store.has(key) ? store.get(key)! : null),
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    removeItem: (key: string) => {
      store.delete(key);
    },
    setItem: (key: string, value: string) => {
      store.set(key, String(value));
    },
  } as Storage;
  Object.defineProperty(globalThis, 'localStorage', { value: storage, configurable: true });
}

function interpolation(computedAt: string, insufficient = false): InterpolationResponse {
  return {
    grid: {
      rows: 2,
      cols: 2,
      bounds: { min_lat: 27.55, max_lat: 27.8, min_lon: 85.2, max_lon: 85.5 },
      values: [[42, 50], [55, 61]],
    },
    station_count: 2,
    coverage_mode: 'RECENT_OBSERVED',
    confidence: 'low',
    source: 'cached_station_aqi',
    computed_at: computedAt,
    insufficient_data: insufficient,
    message: 'cached',
  };
}
