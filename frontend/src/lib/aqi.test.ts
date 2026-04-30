import { describe, expect, it } from 'vitest';

import { formatCoverageMode, getAqiBand, markerRadius } from './aqi';

describe('AQI helpers', () => {
  it('maps AQI values to EPA categories', () => {
    expect(getAqiBand(42).label).toBe('Good');
    expect(getAqiBand(118).shortLabel).toBe('USG');
    expect(getAqiBand(325).label).toBe('Hazardous');
  });

  it('formats approved source modes for display without changing values', () => {
    expect(formatCoverageMode('MODELED_BASELINE')).toBe('MODELED BASELINE');
    expect(formatCoverageMode('REPLAY_DEMO')).toBe('REPLAY DEMO');
  });

  it('keeps marker radius bounded for map rendering', () => {
    expect(markerRadius(null)).toBe(14);
    expect(markerRadius(500)).toBe(36);
  });
});
