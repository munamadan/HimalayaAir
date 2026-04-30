import type { CoverageMode, StationSummary } from '../types/api';

export interface AqiBand {
  label: string;
  shortLabel: string;
  min: number;
  max: number;
  color: string;
  textColor: string;
}

export const AQI_BANDS: AqiBand[] = [
  { label: 'Good', shortLabel: 'Good', min: 0, max: 50, color: '#36d399', textColor: '#06231a' },
  { label: 'Moderate', shortLabel: 'Mod', min: 51, max: 100, color: '#f4d35e', textColor: '#211a05' },
  { label: 'Unhealthy for Sensitive Groups', shortLabel: 'USG', min: 101, max: 150, color: '#f59e3d', textColor: '#261205' },
  { label: 'Unhealthy', shortLabel: 'Unhealthy', min: 151, max: 200, color: '#ef476f', textColor: '#2a0610' },
  { label: 'Very Unhealthy', shortLabel: 'Very Unhealthy', min: 201, max: 300, color: '#9b5de5', textColor: '#16091f' },
  { label: 'Hazardous', shortLabel: 'Hazardous', min: 301, max: 500, color: '#7f1d1d', textColor: '#fff1f2' },
];

export const UNKNOWN_AQI_BAND: AqiBand = {
  label: 'No current AQI',
  shortLabel: 'No data',
  min: -1,
  max: -1,
  color: '#64748b',
  textColor: '#f8fafc',
};

export function getAqiBand(aqi: number | null | undefined): AqiBand {
  if (aqi === null || aqi === undefined || Number.isNaN(aqi)) {
    return UNKNOWN_AQI_BAND;
  }
  return AQI_BANDS.find((band) => aqi >= band.min && aqi <= band.max) || AQI_BANDS[AQI_BANDS.length - 1];
}

export function getAqiPercent(aqi: number | null | undefined): number {
  if (aqi === null || aqi === undefined || Number.isNaN(aqi)) {
    return 0;
  }
  return Math.max(0, Math.min(1, aqi / 300));
}

export function markerRadius(aqi: number | null | undefined): number {
  if (aqi === null || aqi === undefined) {
    return 14;
  }
  return Math.max(14, Math.min(36, 14 + aqi / 10));
}

export function formatCoverageMode(mode: CoverageMode | string | null | undefined): string {
  if (!mode) {
    return 'NO DATA';
  }
  return mode.replace(/_/g, ' ');
}

export function formatSource(source: string | null | undefined): string {
  if (!source) {
    return 'not reported';
  }
  const labels: Record<string, string> = {
    openaq_live: 'OpenAQ live sensor',
    openaq_archive: 'OpenAQ archive',
    openmeteo_cams: 'Open-Meteo CAMS modeled',
    demo_replay: 'Kafka/Spark replay',
    manual_seed: 'manual seed',
  };
  return labels[source] || source.replace(/_/g, ' ');
}

export function sortStationsForDisplay(stations: StationSummary[]): StationSummary[] {
  return [...stations].sort((left, right) => {
    const leftAqi = left.current_aqi ?? -1;
    const rightAqi = right.current_aqi ?? -1;
    if (rightAqi !== leftAqi) {
      return rightAqi - leftAqi;
    }
    return left.name.localeCompare(right.name);
  });
}

export function stationHasCurrentData(station: StationSummary): boolean {
  return station.current_aqi !== null && station.current_aqi !== undefined;
}
