import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from 'recharts';

import { formatTimeOnly } from '../lib/time';
import type { StationHistorySet } from '../types/api';

const SERIES_COLORS = ['#36d399', '#f4d35e', '#38bdf8', '#ef476f', '#f59e3d'];

interface Pm25ChartProps {
  histories: StationHistorySet[];
}

export function Pm25Chart({ histories }: Pm25ChartProps) {
  const series = histories.filter((set) => set.history.readings.length > 0).slice(0, 5);
  const rows = buildRows(series);

  return (
    <section className="chart-card" aria-label="PM2.5 multi-station chart">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Trends</span>
          <h2>PM2.5 over the last day</h2>
        </div>
        <span className="chart-card__meta">last 24 hours</span>
      </div>

      {rows.length === 0 ? (
        <div className="empty-chart">
          <strong>No PM2.5 history available</strong>
          <p>Recent trend lines will appear when station history is available.</p>
        </div>
      ) : (
        <div className="chart-frame">
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={rows} margin={{ top: 18, right: 24, left: 0, bottom: 8 }}>
              <CartesianGrid stroke="rgba(148, 163, 184, 0.16)" vertical={false} />
              <XAxis dataKey="label" stroke="#94a3b8" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} width={42} domain={[0, 'dataMax + 25']} />
              <Tooltip
                contentStyle={{
                  background: '#08111f',
                  border: '1px solid rgba(148, 163, 184, 0.28)',
                  borderRadius: '8px',
                  color: '#e5edf6',
                }}
                labelStyle={{ color: '#b6c3d1' }}
              />
              {series.map((set, index) => (
                <Line
                  key={set.station.id}
                  type="monotone"
                  dataKey={seriesKey(set.station.id)}
                  name={set.station.name}
                  stroke={SERIES_COLORS[index % SERIES_COLORS.length]}
                  strokeWidth={2.4}
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="chart-legend">
        {series.map((set, index) => (
          <span key={set.station.id}>
            <i style={{ background: SERIES_COLORS[index % SERIES_COLORS.length] }} />
            {set.station.name}
          </span>
        ))}
      </div>
    </section>
  );
}

interface ChartRow {
  timestamp: string;
  label: string;
  [key: string]: string | number | null;
}

function buildRows(series: StationHistorySet[]): ChartRow[] {
  const rowsByTimestamp = new Map<string, ChartRow>();

  series.forEach((set) => {
    set.history.readings.forEach((reading) => {
      const existing = rowsByTimestamp.get(reading.timestamp) ?? {
        timestamp: reading.timestamp,
        label: formatTimeOnly(reading.timestamp),
      };
      existing[seriesKey(set.station.id)] = reading.aqi ?? reading.value;
      rowsByTimestamp.set(reading.timestamp, existing);
    });
  });

  return [...rowsByTimestamp.values()].sort((left, right) => new Date(left.timestamp).getTime() - new Date(right.timestamp).getTime());
}

function seriesKey(stationId: number): string {
  return `station_${stationId}`;
}
