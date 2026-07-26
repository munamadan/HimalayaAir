import { describe, expect, it } from 'vitest';

import { buildStationHeatmap } from './stationHeatmap';
import type { StationSummary } from '../types/api';

describe('buildStationHeatmap', () => {
  it('builds a usable heatmap from one station AQI reading', () => {
    const heatmap = buildStationHeatmap([station(1, 87)], { source: 'station_snapshot' });

    expect(heatmap).not.toBeNull();
    expect(heatmap?.insufficient_data).toBe(false);
    expect(heatmap?.station_count).toBe(1);
    expect(heatmap?.source).toBe('station_snapshot');
    expect(heatmap?.grid.values.every((row) => row.every((value) => value === 87))).toBe(true);
  });

  it('interpolates between multiple station readings', () => {
    const heatmap = buildStationHeatmap([station(1, 40), station(2, 120)], { rows: 5, cols: 5 });

    expect(heatmap?.grid.values).toHaveLength(5);
    expect(heatmap?.grid.values[0]).toHaveLength(5);
    const values = heatmap!.grid.values.flat().filter((value): value is number => value !== null);
    expect(Math.min(...values)).toBeGreaterThanOrEqual(40);
    expect(Math.max(...values)).toBeLessThanOrEqual(120);
  });

  it('returns null when no station has an AQI reading', () => {
    expect(buildStationHeatmap([station(1, null)])).toBeNull();
  });
});

function station(id: number, currentAqi: number | null): StationSummary {
  return {
    id,
    name: `Station ${id}`,
    lat: 27.68 + id * 0.01,
    lon: 85.3 + id * 0.01,
    active: true,
    status: 'active',
    last_seen: '2026-07-26T00:00:00Z',
    current_aqi: currentAqi,
    dominant_pollutant: 'pm25',
    source: 'openaq_live',
    observation_type: 'observed',
    coverage_mode: 'RECENT_OBSERVED',
    confidence: 'medium',
    freshness_minutes: 30,
    health_category: null,
  };
}
