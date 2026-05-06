import { useEffect, useMemo, useState } from 'react';

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { bestSixHourWindows } from '../lib/historical';
import { formatTimestamp } from '../lib/time';
import { ApiError, getForecast } from '../services/api';
import type { ForecastResponse, StationSummary } from '../types/api';

interface ForecastPanelProps {
  stations: StationSummary[];
  pollutant: string;
}

export function ForecastPanel({ stations, pollutant }: ForecastPanelProps) {
  const [stationId, setStationId] = useState<number>(stations[0]?.id ?? 0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);

  useEffect(() => {
    if (stationId === 0) {
      return;
    }
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await getForecast(stationId, pollutant);
        if (!cancelled) {
          setForecast(response);
        }
      } catch (loadError) {
        if (!cancelled) {
          if (loadError instanceof ApiError && loadError.status === 404) {
            setForecast(null);
            setError('No forecast exists for this station/pollutant. Modeled fallback was not returned for this query.');
          } else {
            setError(loadError instanceof Error ? loadError.message : 'Could not load forecast.');
          }
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [pollutant, stationId]);

  const chartRows = useMemo(
    () =>
      (forecast?.forecasts ?? []).slice(0, 72).map((point) => ({
        label: new Intl.DateTimeFormat(undefined, { day: '2-digit', hour: '2-digit' }).format(new Date(point.target_timestamp)),
        predicted: point.predicted_aqi,
        lower: point.lower_bound ?? point.predicted_aqi,
        upper: point.upper_bound ?? point.predicted_aqi,
      })),
    [forecast?.forecasts],
  );

  const bestWindows = useMemo(() => bestSixHourWindows((forecast?.forecasts ?? []).slice(0, 72), 3), [forecast?.forecasts]);

  return (
    <section id="forecast" className="forecast-card" aria-label="Forecast panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Forecast panel</span>
          <h2>72-hour confidence band and best windows</h2>
        </div>
        <span className="chart-card__meta">{pollutant.toUpperCase()}</span>
      </div>
      <div className="forecast-controls">
        <label>
          Station
          <select value={stationId} onChange={(event) => setStationId(Number(event.target.value))}>
            {stations.map((station) => (
              <option key={station.id} value={station.id}>
                {station.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading && <p className="muted">Loading forecast…</p>}
      {error && <p className="inline-error">{error}</p>}

      {!loading && !error && !forecast && <p className="muted">No forecast data returned for the selected station and pollutant.</p>}

      {!loading && !error && forecast && (
        <>
          <dl className="provenance-list provenance-list--compact">
            <div>
              <dt>Model</dt>
              <dd>{forecast.model}</dd>
            </div>
            <div>
              <dt>Model source</dt>
              <dd>{forecast.model_source}</dd>
            </div>
            <div>
              <dt>Fallback reason</dt>
              <dd>{forecast.fallback_reason ?? 'none (primary model used)'}</dd>
            </div>
            <div>
              <dt>Historical MAE</dt>
              <dd>{forecast.historical_mae ?? 'not available'}</dd>
            </div>
          </dl>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartRows} margin={{ top: 10, right: 18, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="rgba(148, 163, 184, 0.16)" vertical={false} />
                <XAxis dataKey="label" stroke="#94a3b8" tick={{ fontSize: 11 }} minTickGap={20} />
                <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} width={44} />
                <Tooltip
                  contentStyle={{ background: '#08111f', border: '1px solid rgba(148,163,184,0.28)', borderRadius: '16px' }}
                  labelStyle={{ color: '#b6c3d1' }}
                />
                <Area type="monotone" dataKey="upper" stroke="transparent" fill="rgba(56, 189, 248, 0.24)" />
                <Area type="monotone" dataKey="lower" stroke="transparent" fill="rgba(3, 7, 17, 0.9)" />
                <Area type="monotone" dataKey="predicted" stroke="#36d399" fill="rgba(54, 211, 153, 0.28)" strokeWidth={2.2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="forecast-windows">
            <h3>Best 6-hour outdoor windows</h3>
            {bestWindows.length === 0 ? (
              <p className="muted">Insufficient forecast points to compute 6-hour windows.</p>
            ) : (
              <ul>
                {bestWindows.map((window) => (
                  <li key={`${window.start}-${window.end}`}>
                    <strong>AQI {window.avgAqi}</strong>
                    <span>
                      {formatTimestamp(window.start)} to {formatTimestamp(window.end)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <p className="muted">Generated at {formatTimestamp(forecast.generated_at)}. Confidence band reflects lower/upper forecast bounds.</p>
        </>
      )}
    </section>
  );
}
