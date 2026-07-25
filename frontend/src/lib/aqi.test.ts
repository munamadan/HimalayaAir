import { describe, expect, it } from 'vitest';

import { formatDataModeLabel, getAqiBand, healthAdviceForAqi, markerRadius } from './aqi';

describe('AQI helpers', () => {
  it('maps AQI values to EPA categories', () => {
    expect(getAqiBand(42).label).toBe('Good');
    expect(getAqiBand(118).shortLabel).toBe('USG');
    expect(getAqiBand(325).label).toBe('Hazardous');
  });

  it('formats source modes as product-facing labels', () => {
    expect(formatDataModeLabel('MODELED_BASELINE')).toBe('Estimated air quality');
    expect(formatDataModeLabel('REPLAY_DEMO')).toBe('Demo replay');
  });

  it('returns concise AQI health advice', () => {
    expect(healthAdviceForAqi(42)).toContain('normal outdoor activity');
    expect(healthAdviceForAqi(180)).toContain('Limit prolonged outdoor activity');
  });

  it('keeps marker radius bounded for map rendering', () => {
    expect(markerRadius(null)).toBe(14);
    expect(markerRadius(500)).toBe(36);
  });
});
