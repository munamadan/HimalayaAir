import { formatCoverageMode, formatSource } from '../lib/aqi';
import type { StationsResponse, ValleyCurrentResponse } from '../types/api';

interface ProvenancePanelProps {
  stations: StationsResponse | null;
  valley: ValleyCurrentResponse | null;
}

export function ProvenancePanel({ stations, valley }: ProvenancePanelProps) {
  const mode = stations?.coverage_mode ?? valley?.coverage_mode ?? 'NO_DATA';
  const source = valley?.source ?? topStationSource(stations);

  return (
    <section className="provenance-card" aria-label="Data provenance">
      <span className="eyebrow">Source transparency</span>
      <h2>{formatCoverageMode(mode)}</h2>
      <p>{stations?.message ?? valley?.message ?? 'No coverage explanation returned by the API.'}</p>
      <dl className="provenance-list provenance-list--compact">
        <div>
          <dt>Primary source</dt>
          <dd>{formatSource(source)}</dd>
        </div>
        <div>
          <dt>Modeled fallback</dt>
          <dd>{stations?.modeled_available ? 'available' : 'not active'}</dd>
        </div>
        <div>
          <dt>Replay mode</dt>
          <dd>{stations?.replay_active ? 'active through pipeline' : 'not active'}</dd>
        </div>
      </dl>
    </section>
  );
}

function topStationSource(stations: StationsResponse | null): string | null {
  return stations?.stations.find((station) => station.source)?.source ?? null;
}
