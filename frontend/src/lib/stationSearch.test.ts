import { describe, expect, it } from 'vitest';

import { searchStations } from './stationSearch';
import type { StationSummary } from '../types/api';

const stations: StationSummary[] = [
  station(1, 'Embassy Kathmandu', 80),
  station(2, 'Kathmandu Central', 110),
  station(3, 'Bagdol', null),
  { ...station(4, 'Kathmandu East', 60), active: false },
];

describe('searchStations', () => {
  it('returns exact and prefix matches before substring matches', () => {
    expect(searchStations(stations, 'Kathmandu').map((result) => result.station.name)).toEqual([
      'Kathmandu Central',
      'Kathmandu East',
      'Embassy Kathmandu',
    ]);
  });

  it('prefers reporting stations when match scores are equal', () => {
    expect(searchStations(stations, 'Bagdol')[0].station.id).toBe(3);
    expect(searchStations(stations, 'Kathmandu')[0].station.id).toBe(2);
  });

  it('normalizes punctuation and whitespace', () => {
    expect(searchStations(stations, ' embassy-kathmandu ')[0].station.id).toBe(1);
  });

  it('returns an empty list for blank or unmatched queries', () => {
    expect(searchStations(stations, '   ')).toEqual([]);
    expect(searchStations(stations, 'Patan')).toEqual([]);
  });
});

function station(id: number, name: string, currentAqi: number | null): StationSummary {
  return {
    id,
    name,
    lat: 27.7,
    lon: 85.3,
    active: true,
    status: 'active',
    last_seen: null,
    current_aqi: currentAqi,
    dominant_pollutant: 'pm25',
    source: 'openaq_live',
    observation_type: 'observed',
    coverage_mode: 'LIVE_OBSERVED',
    confidence: 'high',
    freshness_minutes: 15,
    health_category: null,
  };
}
