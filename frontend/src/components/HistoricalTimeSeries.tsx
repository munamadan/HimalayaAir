import { useEffect, useMemo, useRef, useState } from 'react';

import { axisBottom, axisLeft } from 'd3-axis';
import type { D3BrushEvent } from 'd3-brush';
import { brushX } from 'd3-brush';
import { extent, max, min } from 'd3-array';
import { line } from 'd3-shape';
import { select } from 'd3-selection';
import { scaleLinear, scaleTime } from 'd3-scale';
import type { D3ZoomEvent } from 'd3-zoom';
import { zoom } from 'd3-zoom';

import type { ExplorerPoint } from '../lib/historical';

interface HistoricalTimeSeriesProps {
  points: ExplorerPoint[];
  annotations: AnnotationBand[];
}

export interface AnnotationBand {
  id: string;
  label: string;
  start: string;
  end: string;
  kind: 'season' | 'festival' | 'policy';
}

const WIDTH = 980;
const HEIGHT = 330;
const CONTEXT_HEIGHT = 74;
const MARGIN = { top: 14, right: 18, bottom: 24, left: 42 };
const CONTEXT_MARGIN = { top: 266, right: 18, bottom: 14, left: 42 };

export function HistoricalTimeSeries({ points, annotations }: HistoricalTimeSeriesProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const brushRef = useRef<SVGGElement | null>(null);
  const zoomRectRef = useRef<SVGRectElement | null>(null);
  const [domain, setDomain] = useState<[Date, Date] | null>(null);

  const rows = useMemo(
    () =>
      points
        .filter((point) => typeof point.value === 'number')
        .map((point) => ({ x: new Date(point.timestamp), y: point.value as number }))
        .sort((left, right) => left.x.getTime() - right.x.getTime()),
    [points],
  );

  useEffect(() => {
    if (rows.length < 2 || !svgRef.current || !brushRef.current || !zoomRectRef.current) {
      return;
    }

    const fullDomain = extent(rows, (row) => row.x) as [Date, Date];
    const yMax = max(rows, (row) => row.y) ?? 300;
    const yMin = min(rows, (row) => row.y) ?? 0;
    const xScaleFull = scaleTime().domain(fullDomain).range([MARGIN.left, WIDTH - MARGIN.right]);
    const xScale = scaleTime()
      .domain(domain ?? fullDomain)
      .range([MARGIN.left, WIDTH - MARGIN.right]);
    const yScale = scaleLinear()
      .domain([Math.max(0, yMin - 15), yMax + 15])
      .nice()
      .range([HEIGHT - MARGIN.bottom, MARGIN.top]);
    const yContextScale = scaleLinear()
      .domain([Math.max(0, yMin - 15), yMax + 15])
      .nice()
      .range([CONTEXT_MARGIN.top + CONTEXT_HEIGHT, CONTEXT_MARGIN.top]);

    const mainLine = line<{ x: Date; y: number }>()
      .x((row) => xScale(row.x))
      .y((row) => yScale(row.y));
    const contextLine = line<{ x: Date; y: number }>()
      .x((row) => xScaleFull(row.x))
      .y((row) => yContextScale(row.y));

    const svg = select(svgRef.current);
    svg.selectAll('.historical-time-series__line').remove();
    svg.selectAll('.historical-time-series__context-line').remove();
    svg.selectAll('.historical-time-series__x-axis').remove();
    svg.selectAll('.historical-time-series__y-axis').remove();
    svg.selectAll('.historical-time-series__band').remove();

    svg
      .append('g')
      .attr('class', 'historical-time-series__x-axis')
      .attr('transform', `translate(0,${HEIGHT - MARGIN.bottom})`)
      .call(axisBottom(xScale).ticks(6));
    svg.append('g').attr('class', 'historical-time-series__y-axis').attr('transform', `translate(${MARGIN.left},0)`).call(axisLeft(yScale).ticks(5));

    annotations.forEach((annotation) => {
      const start = new Date(annotation.start);
      const end = new Date(annotation.end);
      const x1 = xScale(start);
      const x2 = xScale(end);
      if (x2 < MARGIN.left || x1 > WIDTH - MARGIN.right) {
        return;
      }
      svg
        .append('rect')
        .attr('class', `historical-time-series__band historical-time-series__band--${annotation.kind}`)
        .attr('x', Math.max(MARGIN.left, x1))
        .attr('y', MARGIN.top)
        .attr('width', Math.max(2, Math.min(WIDTH - MARGIN.right, x2) - Math.max(MARGIN.left, x1)))
        .attr('height', HEIGHT - MARGIN.bottom - MARGIN.top)
        .append('title')
        .text(`${annotation.label} (${annotation.start} to ${annotation.end})`);
    });

    const pathMain = mainLine(rows);
    const pathContext = contextLine(rows);
    if (pathMain) {
      svg
        .append('path')
        .attr('class', 'historical-time-series__line')
        .attr('d', pathMain);
    }
    if (pathContext) {
      svg
        .append('path')
        .attr('class', 'historical-time-series__context-line')
        .attr('d', pathContext);
    }

    const brush = brushX<unknown>()
      .extent([
        [MARGIN.left, CONTEXT_MARGIN.top],
        [WIDTH - MARGIN.right, CONTEXT_MARGIN.top + CONTEXT_HEIGHT],
      ])
      .on('brush end', (event: D3BrushEvent<unknown>) => {
        if (!event.selection) {
          return;
        }
        const [left, right] = event.selection as [number, number];
        setDomain([xScaleFull.invert(left), xScaleFull.invert(right)]);
      });

    select(brushRef.current).call(brush);
    if (!domain) {
      const fullRange: [number, number] = [xScaleFull.range()[0], xScaleFull.range()[1]];
      select(brushRef.current).call(brush.move, fullRange);
    }

    const zoomBehavior = zoom<SVGRectElement, unknown>()
      .scaleExtent([1, 16])
      .translateExtent([
        [MARGIN.left, MARGIN.top],
        [WIDTH - MARGIN.right, HEIGHT - MARGIN.bottom],
      ])
      .extent([
        [MARGIN.left, MARGIN.top],
        [WIDTH - MARGIN.right, HEIGHT - MARGIN.bottom],
      ])
      .on('zoom', (event: D3ZoomEvent<SVGRectElement, unknown>) => {
        const transformed = event.transform.rescaleX(xScaleFull);
        const nextDomain = transformed.domain() as [Date, Date];
        setDomain(nextDomain);
      });

    select(zoomRectRef.current).call(zoomBehavior);
  }, [annotations, domain, rows]);

  if (rows.length < 2) {
    return (
      <div className="empty-chart">
        <strong>No sufficient points for time series</strong>
        <p>At least two AQI points are required to render brush and zoom interactions.</p>
      </div>
    );
  }

  return (
    <svg
      ref={svgRef}
      className="historical-time-series"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label="Historical AQI time series with zoom and brush"
    >
      <rect
        ref={zoomRectRef}
        x={MARGIN.left}
        y={MARGIN.top}
        width={WIDTH - MARGIN.left - MARGIN.right}
        height={HEIGHT - MARGIN.top - MARGIN.bottom}
        fill="transparent"
      />
      <g ref={brushRef} />
    </svg>
  );
}
