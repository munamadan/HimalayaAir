import { formatCoverageMode } from '../lib/aqi';
import { formatTimestamp } from '../lib/time';
import type { CoverageMetadata } from '../types/api';

interface CoverageRibbonProps {
  coverage: CoverageMetadata | null;
  lastUpdated: string | null;
  websocketStatus: string;
  refreshing: boolean;
}

export function CoverageRibbon({ coverage, lastUpdated, websocketStatus, refreshing }: CoverageRibbonProps) {
  return (
    <section className="coverage-ribbon" aria-label="Current data coverage state">
      <div>
        <span className="eyebrow">Coverage mode</span>
        <strong>{formatCoverageMode(coverage?.coverage_mode)}</strong>
      </div>
      <div>
        <span className="eyebrow">Confidence</span>
        <strong>{coverage?.confidence ?? 'unknown'}</strong>
      </div>
      <div>
        <span className="eyebrow">Observed stations</span>
        <strong>
          {coverage?.fresh_station_count ?? 0} fresh / {coverage?.recent_station_count ?? 0} recent
        </strong>
      </div>
      <div>
        <span className="eyebrow">Updated</span>
        <strong>{refreshing ? 'refreshing' : formatTimestamp(lastUpdated)}</strong>
      </div>
      <div className="ws-state">
        <span className={`status-dot status-dot--${websocketStatus}`} />
        <span>{websocketStatus}</span>
      </div>
    </section>
  );
}
