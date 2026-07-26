import { describe, expect, it } from 'vitest';

import { hasUsableHeatmap } from './heatmapCanvas';
import type { InterpolationResponse } from '../types/api';

describe('hasUsableHeatmap', () => {
  it('returns true only when the interpolation grid can be rendered', () => {
    expect(hasUsableHeatmap(interpolation())).toBe(true);
  });

  it('returns false when interpolation is missing or marked insufficient', () => {
    expect(hasUsableHeatmap(null)).toBe(false);
    expect(hasUsableHeatmap(interpolation({ insufficient_data: true }))).toBe(false);
  });

  it('returns false when the grid has no renderable values', () => {
    expect(hasUsableHeatmap(interpolation({ values: [] }))).toBe(false);
    expect(hasUsableHeatmap(interpolation({ rows: 0 }))).toBe(false);
    expect(hasUsableHeatmap(interpolation({ cols: 0 }))).toBe(false);
  });
});

function interpolation(overrides: {
  insufficient_data?: boolean;
  rows?: number;
  cols?: number;
  values?: Array<Array<number | null>>;
} = {}): InterpolationResponse {
  return {
    grid: {
      rows: overrides.rows ?? 2,
      cols: overrides.cols ?? 2,
      bounds: { min_lat: 27.55, max_lat: 27.8, min_lon: 85.2, max_lon: 85.5 },
      values: overrides.values ?? [[42, 50], [55, 61]],
    },
    station_count: 3,
    coverage_mode: 'LIVE_OBSERVED',
    confidence: 'high',
    source: 'openaq_live',
    computed_at: '2026-07-26T00:00:00Z',
    insufficient_data: overrides.insufficient_data ?? false,
    message: 'ok',
  };
}
