import { useEffect, useMemo, useState } from 'react';

import { formatCoverageMode } from '../lib/aqi';
import { formatTimestamp } from '../lib/time';
import { getForecast } from '../services/api';
import type { CoverageMode, ForecastResponse, NearestStation, ObservationType } from '../types/api';

interface GreetingSummaryDialogProps {
  open: boolean;
  greeting: string;
  valleyAqi: number | null;
  coverageMode: CoverageMode | null | undefined;
  freshStationCount: number | null;
  recentStationCount: number | null;
  source: string | null;
  observationType: ObservationType | null;
  lastUpdated: string | null;
  selectedStationName: string | null;
  nearestStation: NearestStation | null;
  forecastStationId: number | null;
  pollutant: string;
  forecastBasisMessage: string;
  locationStatus: string;
  onDismiss: () => void;
}

export function GreetingSummaryDialog({
  open,
  greeting,
  valleyAqi,
  coverageMode,
  freshStationCount,
  recentStationCount,
  source,
  observationType,
  lastUpdated,
  selectedStationName,
  nearestStation,
  forecastStationId,
  pollutant,
  forecastBasisMessage,
  locationStatus,
  onDismiss,
}: GreetingSummaryDialogProps) {
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastError, setForecastError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !forecastStationId) {
      setForecast(null);
      setForecastError(null);
      return;
    }

    const stationId = forecastStationId;
    let cancelled = false;
    async function loadForecast() {
      setForecastLoading(true);
      setForecastError(null);
      try {
        const response = await getForecast(stationId, pollutant);
        if (!cancelled) {
          setForecast(response);
        }
      } catch (error) {
        if (!cancelled) {
          setForecast(null);
          setForecastError(error instanceof Error ? error.message : 'Forecast is not available.');
        }
      } finally {
        if (!cancelled) {
          setForecastLoading(false);
        }
      }
    }

    void loadForecast();
    return () => {
      cancelled = true;
    };
  }, [forecastStationId, open, pollutant]);

  const forecastSummary = useMemo(() => summarizeForecast(forecast), [forecast]);

  if (!open) {
    return null;
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <section className="greeting-dialog" role="dialog" aria-modal="true" aria-labelledby="greeting-dialog-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">First look</span>
            <h2 id="greeting-dialog-title">{greeting}, Kathmandu</h2>
          </div>
          <button type="button" className="button button--secondary" onClick={onDismiss}>
            Dismiss
          </button>
        </div>

        <div className="greeting-dialog__summary">
          <div>
            <span className="eyebrow">Current AQI</span>
            <strong>{valleyAqi === null ? 'not available' : Math.round(valleyAqi)}</strong>
            <small>{formatCoverageMode(coverageMode)}</small>
          </div>
          <div>
            <span className="eyebrow">Observed stations</span>
            <strong>{freshStationCount ?? 0} fresh / {recentStationCount ?? 0} recent</strong>
            <small>{locationStatus}</small>
          </div>
        </div>

        <dl className="provenance-list provenance-list--compact">
          <div>
            <dt>Source</dt>
            <dd>{source ?? 'not available'}</dd>
          </div>
          <div>
            <dt>Observation</dt>
            <dd>{observationType ?? 'not available'}</dd>
          </div>
          <div>
            <dt>Last update</dt>
            <dd>{formatTimestamp(lastUpdated)}</dd>
          </div>
          <div>
            <dt>Station</dt>
            <dd>{stationLabel(selectedStationName, nearestStation)}</dd>
          </div>
        </dl>

        <div className="greeting-dialog__forecast">
          <div>
            <span className="eyebrow">72-hour PM2.5 forecast</span>
            <h3>{forecastBasisMessage}</h3>
          </div>
          {forecastLoading && <p className="muted">Loading forecast...</p>}
          {!forecastLoading && forecastError && <p className="inline-error">Forecast not available: {forecastError}</p>}
          {!forecastLoading && !forecastError && !forecast && <p className="muted">Forecast is not available for this station.</p>}
          {!forecastLoading && !forecastError && forecast && (
            <>
              <div className="greeting-dialog__forecast-grid">
                <div>
                  <span>Next predicted AQI</span>
                  <strong>{forecastSummary.nextAqi}</strong>
                </div>
                <div>
                  <span>72-hour range</span>
                  <strong>{forecastSummary.range}</strong>
                </div>
                <div>
                  <span>Model</span>
                  <strong>{forecast.model}</strong>
                </div>
              </div>
              <p className="muted">
                Generated at {formatTimestamp(forecast.generated_at)}. {forecast.fallback_reason ?? 'Primary forecast model used.'}
              </p>
            </>
          )}
        </div>
      </section>
    </div>
  );
}

function stationLabel(selectedStationName: string | null, nearestStation: NearestStation | null): string {
  if (nearestStation) {
    return `${nearestStation.name} (${nearestStation.distance_km.toFixed(1)} km from browser location)`;
  }
  return selectedStationName ?? 'not available';
}

function summarizeForecast(forecast: ForecastResponse | null): { nextAqi: string; range: string } {
  const points = (forecast?.forecasts ?? []).slice(0, 72);
  if (points.length === 0) {
    return { nextAqi: 'not available', range: 'not available' };
  }

  const predictedValues = points.map((point) => point.predicted_aqi);
  const min = Math.min(...predictedValues);
  const max = Math.max(...predictedValues);
  return {
    nextAqi: String(predictedValues[0]),
    range: `${min}-${max}`,
  };
}
