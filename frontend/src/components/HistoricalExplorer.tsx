import { useEffect, useMemo, useState } from 'react';

import { getStationHistory, getValleyHistory } from '../services/api';
import type { StationSummary } from '../types/api';
import {
  aggregateToDaily,
  buildCalendarCells,
  buildExplorerPointsFromStation,
  buildExplorerPointsFromValley,
  clampHistoryHours,
  filterPointsToRange,
  type ExplorerPoint,
  type HistoryGranularity,
  type HistoryScope,
} from '../lib/historical';
import { CalendarHeatmap } from './CalendarHeatmap';
import { ErrorPanel } from './ErrorPanel';
import { HistoricalTimeSeries, type AnnotationBand } from './HistoricalTimeSeries';
import { LoadingState } from './LoadingState';

interface HistoricalExplorerProps {
  stations: StationSummary[];
  pollutant: string;
  onPollutantChange: (pollutant: string) => void;
  compact?: boolean;
}

const TIME_ZONE = 'Asia/Kathmandu';
const POLLUTANTS = ['pm25', 'pm10', 'o3', 'no2', 'so2', 'co'];

export function HistoricalExplorer({
  stations,
  pollutant,
  onPollutantChange,
  compact = false,
}: HistoricalExplorerProps) {
  const [scope, setScope] = useState<HistoryScope>('valley');
  const [stationId, setStationId] = useState<number | null>(stations[0]?.id ?? null);
  const [granularity, setGranularity] = useState<HistoryGranularity>('hour');
  const [endDate, setEndDate] = useState(toDateInput(new Date()));
  const [startDate, setStartDate] = useState(toDateInput(daysAgo(90)));
  const [points, setPoints] = useState<ExplorerPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showTihar, setShowTihar] = useState(true);
  const [showMonsoon, setShowMonsoon] = useState(true);
  const [showCovid, setShowCovid] = useState(true);
  const [retryNonce, setRetryNonce] = useState(0);

  const hours = useMemo(() => {
    const raw = Math.ceil((new Date(endDate).getTime() - new Date(startDate).getTime()) / (60 * 60 * 1000));
    return clampHistoryHours(raw);
  }, [endDate, startDate]);

  useEffect(() => {
    if (scope === 'station' && stationId === null && stations.length > 0) {
      setStationId(stations[0].id);
    }
  }, [scope, stationId, stations]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (scope === 'station' && stationId === null) {
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const historyPoints =
          scope === 'valley'
            ? buildExplorerPointsFromValley((await getValleyHistory(pollutant, hours, granularity)).points)
            : buildExplorerPointsFromStation((await getStationHistory(stationId as number, pollutant, hours)).readings);
        if (cancelled) {
          return;
        }
        const filtered = filterPointsToRange(historyPoints, `${startDate}T00:00:00Z`, `${endDate}T23:59:59Z`);
        setPoints(granularity === 'day' ? aggregateToDaily(filtered, TIME_ZONE) : filtered);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Could not load historical explorer data.');
          setPoints([]);
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
  }, [endDate, granularity, hours, pollutant, retryNonce, scope, startDate, stationId]);

  const calendar = useMemo(
    () => buildCalendarCells(points, `${startDate}T00:00:00Z`, `${endDate}T23:59:59Z`, TIME_ZONE),
    [endDate, points, startDate],
  );
  const annotations = useMemo(() => {
    const years = uniqueYears(startDate, endDate);
    const bands: AnnotationBand[] = [];
    if (showMonsoon) {
      years.forEach((year) => {
        bands.push({
          id: `monsoon-${year}`,
          label: 'Monsoon season',
          start: `${year}-06-01T00:00:00Z`,
          end: `${year}-09-30T23:59:59Z`,
          kind: 'season',
        });
      });
    }
    if (showTihar) {
      bands.push(...tiharBandsInRange(years));
    }
    if (showCovid) {
      bands.push({
        id: 'covid-lockdown-2020',
        label: 'COVID lockdown period',
        start: '2020-03-24T00:00:00Z',
        end: '2021-09-01T23:59:59Z',
        kind: 'policy',
      });
    }
    return bands.filter((band) => intersectsRange(band.start, band.end, `${startDate}T00:00:00Z`, `${endDate}T23:59:59Z`));
  }, [endDate, showCovid, showMonsoon, showTihar, startDate]);

  return (
    <section
      id="historical"
      className={compact ? 'historical-card historical-card--compact' : 'historical-card'}
      aria-label="Historical explorer"
    >
      {!compact && (
        <div className="section-heading">
          <div>
            <span className="eyebrow">History</span>
            <h2>Air quality patterns over time</h2>
          </div>
          <span className="chart-card__meta">bounded to 365 days</span>
        </div>
      )}

      <div className="historical-controls">
        <label>
          Scope
          <select value={scope} onChange={(event) => setScope(event.target.value as HistoryScope)}>
            <option value="valley">Valley</option>
            <option value="station">Station</option>
          </select>
        </label>
        <label>
          Station
          <select value={stationId ?? ''} onChange={(event) => setStationId(Number(event.target.value))} disabled={scope !== 'station'}>
            {stations.map((station) => (
              <option key={station.id} value={station.id}>
                {station.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Pollutant
            <select value={pollutant} onChange={(event) => onPollutantChange(event.target.value)}>
            {POLLUTANTS.map((name) => (
              <option key={name} value={name}>
                {name.toUpperCase()}
              </option>
            ))}
          </select>
        </label>
        <label>
          From
          <input type="date" value={startDate} max={endDate} onChange={(event) => setStartDate(event.target.value)} />
        </label>
        <label>
          To
          <input type="date" value={endDate} min={startDate} max={toDateInput(new Date())} onChange={(event) => setEndDate(event.target.value)} />
        </label>
        <label>
          Granularity
          <select value={granularity} onChange={(event) => setGranularity(event.target.value as HistoryGranularity)}>
            <option value="hour">Hourly</option>
            <option value="day">Daily</option>
          </select>
        </label>
      </div>

      <div className="annotation-toggles">
        <label><input type="checkbox" checked={showTihar} onChange={(event) => setShowTihar(event.target.checked)} /> Tihar</label>
        <label><input type="checkbox" checked={showMonsoon} onChange={(event) => setShowMonsoon(event.target.checked)} /> Monsoon</label>
        <label><input type="checkbox" checked={showCovid} onChange={(event) => setShowCovid(event.target.checked)} /> COVID</label>
      </div>

      {loading && <LoadingState title="Loading historical data" detail="Preparing the selected date range." />}
      {error && <ErrorPanel message={error} onRetry={() => setRetryNonce((current) => current + 1)} />}

      {!loading && !error && (
        <div className="historical-grid">
          <CalendarHeatmap cells={calendar} timeZone={TIME_ZONE} />
          <HistoricalTimeSeries points={points} annotations={annotations} />
        </div>
      )}
    </section>
  );
}

function daysAgo(days: number): Date {
  return new Date(Date.now() - days * 24 * 60 * 60 * 1000);
}

function toDateInput(date: Date): string {
  return `${date.getUTCFullYear()}-${pad2(date.getUTCMonth() + 1)}-${pad2(date.getUTCDate())}`;
}

function pad2(value: number): string {
  return String(value).padStart(2, '0');
}

function uniqueYears(startDate: string, endDate: string): number[] {
  const years: number[] = [];
  const startYear = new Date(startDate).getUTCFullYear();
  const endYear = new Date(endDate).getUTCFullYear();
  for (let year = startYear; year <= endYear; year += 1) {
    years.push(year);
  }
  return years;
}

function tiharBandsInRange(years: number[]): AnnotationBand[] {
  const curated: Record<number, { start: string; end: string }> = {
    2020: { start: '2020-11-13T00:00:00Z', end: '2020-11-17T23:59:59Z' },
    2021: { start: '2021-11-02T00:00:00Z', end: '2021-11-06T23:59:59Z' },
    2022: { start: '2022-10-24T00:00:00Z', end: '2022-10-28T23:59:59Z' },
    2023: { start: '2023-11-11T00:00:00Z', end: '2023-11-15T23:59:59Z' },
    2024: { start: '2024-10-31T00:00:00Z', end: '2024-11-04T23:59:59Z' },
    2025: { start: '2025-10-20T00:00:00Z', end: '2025-10-24T23:59:59Z' },
    2026: { start: '2026-11-08T00:00:00Z', end: '2026-11-12T23:59:59Z' },
  };
  return years.flatMap((year) => {
    const range = curated[year];
    if (!range) {
      return [];
    }
    return [{ id: `tihar-${year}`, label: 'Tihar festival', start: range.start, end: range.end, kind: 'festival' as const }];
  });
}

function intersectsRange(start: string, end: string, rangeStart: string, rangeEnd: string): boolean {
  const a = new Date(start).getTime();
  const b = new Date(end).getTime();
  const c = new Date(rangeStart).getTime();
  const d = new Date(rangeEnd).getTime();
  return a <= d && b >= c;
}
