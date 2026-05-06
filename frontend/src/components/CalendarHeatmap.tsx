import { scaleSequential } from 'd3-scale';
import { interpolateTurbo } from 'd3-scale-chromatic';

import type { DailyCell } from '../lib/historical';

interface CalendarHeatmapProps {
  cells: DailyCell[];
  timeZone: string;
}

const CELL = 14;
const GAP = 2;
const WEEKDAY_LABELS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

export function CalendarHeatmap({ cells, timeZone }: CalendarHeatmapProps) {
  if (cells.length === 0) {
    return (
      <div className="empty-chart">
        <strong>No history points for calendar</strong>
        <p>Select a wider range or different station/pollutant.</p>
      </div>
    );
  }

  const first = new Date(cells[0].timestamp);
  const weekStart = first.getUTCDate() - first.getUTCDay();
  const anchor = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth(), weekStart));
  const values = cells.flatMap((cell) => (typeof cell.value === 'number' ? [cell.value] : []));
  const min = values.length > 0 ? Math.min(...values) : 0;
  const max = values.length > 0 ? Math.max(...values) : 300;
  const color = scaleSequential(interpolateTurbo).domain([Math.max(0, min), Math.max(min + 1, max)]);
  const maxWeek = Math.max(...cells.map((cell) => weekOffset(anchor, cell.timestamp)));
  const width = (maxWeek + 2) * (CELL + GAP) + 56;
  const height = 7 * (CELL + GAP) + 24;

  return (
    <div className="calendar-heatmap-wrap">
      <svg className="calendar-heatmap" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Daily AQI calendar heatmap">
        {WEEKDAY_LABELS.map((label, index) => (
          <text key={label + index} x={0} y={20 + index * (CELL + GAP)} className="calendar-heatmap__axis">
            {label}
          </text>
        ))}
        {cells.map((cell) => {
          const week = weekOffset(anchor, cell.timestamp);
          const day = new Date(cell.timestamp).getUTCDay();
          const x = 30 + week * (CELL + GAP);
          const y = 10 + day * (CELL + GAP);
          return (
            <g key={cell.dayKey}>
              <rect
                x={x}
                y={y}
                width={CELL}
                height={CELL}
                rx={2}
                className={cell.value === null ? 'calendar-heatmap__cell calendar-heatmap__cell--empty' : 'calendar-heatmap__cell'}
                fill={cell.value === null ? 'rgba(100, 116, 139, 0.22)' : (color(cell.value) as string)}
              >
                <title>{`${cell.dayKey} (${timeZone}): ${cell.value === null ? 'no data' : `AQI ${cell.value}`}`}</title>
              </rect>
            </g>
          );
        })}
      </svg>
      <p className="muted">Day boundaries in {timeZone}. Empty cells represent no reported AQI, not clean air.</p>
    </div>
  );
}

function weekOffset(anchor: Date, timestamp: string): number {
  const date = new Date(timestamp);
  const diffDays = Math.floor((date.getTime() - anchor.getTime()) / (24 * 60 * 60 * 1000));
  return Math.floor(diffDays / 7);
}
