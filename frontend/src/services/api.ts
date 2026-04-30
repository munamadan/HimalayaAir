import type {
  InterpolationResponse,
  PipelineHealthResponse,
  StationCurrentResponse,
  StationHistoryResponse,
  StationsResponse,
  ValleyCurrentResponse,
} from '../types/api';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const DEFAULT_WS_PATH = '/ws/live-feed';

export class ApiError extends Error {
  readonly status: number;
  readonly details: unknown;

  constructor(message: string, status: number, details: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

export function getApiBaseUrl(): string {
  return trimTrailingSlash(import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL);
}

export function getWebSocketUrl(): string {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  const base = getApiBaseUrl();
  const wsBase = base.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
  return `${wsBase}${DEFAULT_WS_PATH}`;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(toApiUrl(path), {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init.headers || {}),
    },
  });

  const payload = await parsePayload(response);
  if (!response.ok) {
    throw new ApiError(response.statusText || 'API request failed', response.status, payload);
  }
  return payload as T;
}

export function getStations(): Promise<StationsResponse> {
  return apiFetch<StationsResponse>('/api/stations');
}

export function getValleyCurrent(): Promise<ValleyCurrentResponse> {
  return apiFetch<ValleyCurrentResponse>('/api/valley/current');
}

export function getInterpolationCurrent(pollutant = 'pm25'): Promise<InterpolationResponse> {
  return apiFetch<InterpolationResponse>(`/api/interpolation/current?pollutant=${encodeURIComponent(pollutant)}`);
}

export function getStationCurrent(stationId: number): Promise<StationCurrentResponse> {
  return apiFetch<StationCurrentResponse>(`/api/stations/${stationId}/current`);
}

export function getStationHistory(stationId: number, pollutant = 'pm25', hours = 24): Promise<StationHistoryResponse> {
  const search = new URLSearchParams({ pollutant, hours: String(hours), limit: '600' });
  return apiFetch<StationHistoryResponse>(`/api/stations/${stationId}/history?${search.toString()}`);
}

export function getPipelineHealth(): Promise<PipelineHealthResponse> {
  return apiFetch<PipelineHealthResponse>('/api/pipeline/health');
}

function toApiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path;
  }
  return `${getApiBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`;
}

async function parsePayload(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    return response.text();
  }
  return response.json();
}

function trimTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}
