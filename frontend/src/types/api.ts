export type CoverageMode = 'LIVE_OBSERVED' | 'RECENT_OBSERVED' | 'MODELED_BASELINE' | 'REPLAY_DEMO' | 'STATION_ONLY' | 'NO_DATA';
export type Confidence = 'high' | 'medium' | 'low' | 'demo';
export type ObservationType = 'observed' | 'modeled' | 'replay' | 'synthetic';

export interface CoverageMetadata {
  coverage_mode: CoverageMode;
  confidence: Confidence;
  fresh_station_count: number;
  recent_station_count: number;
  modeled_available: boolean;
  replay_active: boolean;
  message: string | null;
}

export interface StationSummary {
  id: number;
  name: string;
  lat: number;
  lon: number;
  active: boolean;
  status: string;
  last_seen: string | null;
  current_aqi: number | null;
  dominant_pollutant: string | null;
  source: string | null;
  observation_type: ObservationType | null;
  coverage_mode: CoverageMode | null;
  confidence: Confidence | null;
  freshness_minutes: number | null;
  health_category: string | null;
}

export interface StationsResponse extends CoverageMetadata {
  timestamp: string;
  valley_composite_aqi: number | null;
  stations: StationSummary[];
}

export interface StationIdentity {
  id: number;
  name: string;
  lat: number;
  lon: number;
  active: boolean;
  status: string;
  last_seen: string | null;
}

export interface PollutantCurrent {
  pollutant: string;
  value: number;
  unit: string;
  aqi: number | null;
  timestamp: string;
  freshness_minutes: number | null;
  is_anomaly: boolean;
  anomaly_reason: string | null;
  quality_flag: string;
  source: string;
  observation_type: ObservationType;
  coverage_mode: CoverageMode | null;
  confidence: Confidence | null;
  health_category: string | null;
}

export interface StationCurrentResponse extends CoverageMetadata {
  station: StationIdentity;
  current_aqi: number | null;
  dominant_pollutant: string | null;
  readings: PollutantCurrent[];
}

export interface HistoryPoint {
  timestamp: string;
  pollutant: string;
  value: number;
  unit: string;
  aqi: number | null;
  is_anomaly: boolean;
  quality_flag: string;
  source: string;
  observation_type: ObservationType;
  coverage_mode: CoverageMode | null;
  confidence: Confidence | null;
}

export interface StationHistoryResponse {
  station_id: number;
  pollutant: string | null;
  hours: number;
  readings: HistoryPoint[];
}

export interface ValleyHistoryPoint {
  bucket_start: string;
  pollutant: string;
  avg_aqi: number | null;
  max_aqi: number | null;
  station_count: number;
  reading_count: number;
}

export interface ValleyHistoryResponse {
  pollutant: string | null;
  hours: number;
  granularity: 'hour' | 'day';
  points: ValleyHistoryPoint[];
}

export interface StationHistorySet {
  station: StationSummary;
  history: StationHistoryResponse;
}

export interface ValleyCurrentResponse extends CoverageMetadata {
  timestamp: string | null;
  composite_aqi: number | null;
  dominant_pollutant: string | null;
  recommendation: string;
  source: string | null;
}

export interface GridBounds {
  min_lat: number;
  max_lat: number;
  min_lon: number;
  max_lon: number;
}

export interface InterpolationGrid {
  rows: number;
  cols: number;
  bounds: GridBounds;
  values: Array<Array<number | null>>;
}

export interface InterpolationResponse {
  grid: InterpolationGrid;
  station_count: number;
  coverage_mode: CoverageMode;
  confidence: Confidence;
  source: string;
  computed_at: string;
  insufficient_data: boolean;
  message: string;
}

export interface PipelineRunHealth {
  component: string;
  run_at: string | null;
  status: string;
  records_processed: number | null;
  error_message: string | null;
  duration_seconds: number | null;
  metadata: Record<string, unknown>;
}

export interface PipelineHealthResponse {
  status: string;
  service: string;
  timestamp: string;
  checks: Record<string, unknown>;
  pipeline_runs: PipelineRunHealth[];
  coverage: CoverageMetadata;
}

export interface WindRoseBin {
  direction_start: number;
  direction_end: number;
  avg_speed: number | null;
  sample_count: number;
}

export interface WindRoseResponse {
  hours: number;
  bins: WindRoseBin[];
  total_samples: number;
}

export interface NearestStation {
  id: number;
  name: string;
  lat: number;
  lon: number;
  distance_km: number;
  current_aqi: number | null;
}

export interface HealthAdvisoryResponse extends CoverageMetadata {
  aqi: number | null;
  category: string | null;
  recommendation: string;
  nearest_station: NearestStation | null;
}

export interface ForecastPoint {
  target_timestamp: string;
  horizon_hours: number;
  predicted_aqi: number;
  lower_bound: number | null;
  upper_bound: number | null;
}

export interface ForecastResponse {
  station_id: number;
  pollutant: string;
  generated_at: string;
  model: string;
  model_source: string;
  fallback_reason: string | null;
  historical_mae: number | null;
  forecasts: ForecastPoint[];
}

export interface WebSocketEvent<TData = Record<string, unknown>> {
  event: string;
  timestamp: string;
  data: TData;
}

export interface ProcessedAQStationSummary {
  station_id: number;
  station_name: string | null;
  aqi: number | null;
  dominant_pollutant: string;
  district_id: number | null;
  district: string | null;
  is_anomaly: boolean;
  source: string;
  observation_type: ObservationType;
  latitude: number | null;
  longitude: number | null;
  timestamp: string;
}

export interface ProcessedAQBatchSummary {
  schema_version: string;
  batch_id: number;
  processed_at: string;
  records_received: number;
  records_written: number;
  records_skipped_duplicate: number;
  records_invalid: number;
  anomaly_count: number;
  coverage_mode: CoverageMode;
  confidence: Confidence;
  stations: ProcessedAQStationSummary[];
}
