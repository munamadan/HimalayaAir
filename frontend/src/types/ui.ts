import type { StationSummary } from './api';

export type InspectorMode = 'valley' | 'station' | 'forecast' | 'history';
export type InspectorVisibility = 'open' | 'collapsed';
export type MobileSheetSnap = 'peek' | 'half' | 'full';
export type LocationStatus = 'idle' | 'locating' | 'success' | 'denied' | 'unavailable' | 'error';

export interface StationSearchResult {
  station: StationSummary;
  score: number;
}
