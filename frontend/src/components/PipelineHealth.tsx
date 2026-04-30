import { formatTimestamp } from '../lib/time';
import type { PipelineHealthResponse } from '../types/api';

interface PipelineHealthProps {
  health: PipelineHealthResponse | null;
}

export function PipelineHealth({ health }: PipelineHealthProps) {
  const runs = health?.pipeline_runs.slice(0, 5) ?? [];

  return (
    <section className="pipeline-card" aria-label="Pipeline health">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Pipeline</span>
          <h2>Ingestion state</h2>
        </div>
        <span className={`health-pill health-pill--${health?.status ?? 'unknown'}`}>{health?.status ?? 'unknown'}</span>
      </div>
      <dl className="provenance-list provenance-list--compact">
        <div>
          <dt>Service</dt>
          <dd>{health?.service ?? 'not loaded'}</dd>
        </div>
        <div>
          <dt>Checked</dt>
          <dd>{formatTimestamp(health?.timestamp)}</dd>
        </div>
        <div>
          <dt>Coverage</dt>
          <dd>{health?.coverage.coverage_mode ?? 'not loaded'}</dd>
        </div>
      </dl>
      {runs.length === 0 ? (
        <p className="muted">No recent pipeline run rows returned by the API.</p>
      ) : (
        <div className="pipeline-list">
          {runs.map((run) => (
            <article key={`${run.component}-${run.run_at ?? run.status}`}>
              <div>
                <strong>{run.component}</strong>
                <span>{formatTimestamp(run.run_at)}</span>
              </div>
              <span className={`health-pill health-pill--${run.status}`}>{run.status}</span>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
