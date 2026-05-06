import type { WindRoseResponse } from '../types/api';

interface WindRoseProps {
  data: WindRoseResponse | null;
}

export function WindRose({ data }: WindRoseProps) {
  return (
    <section className="card wind-rose" aria-label="Wind rose">
      <span className="eyebrow">Wind context</span>
      <h2>Wind rose (last 24h)</h2>
      {!data || data.total_samples === 0 ? (
        <p className="muted">Weather wind data is unavailable for the selected window.</p>
      ) : (
        <div className="wind-rose__grid">
          {data.bins.map((bin) => {
            const speed = bin.avg_speed ?? 0;
            const width = Math.min(Math.round(speed * 9), 100);
            return (
              <div key={`${bin.direction_start}-${bin.direction_end}`} className="wind-rose__row">
                <span>{`${bin.direction_start}-${bin.direction_end}`}</span>
                <div className="wind-rose__bar-wrap">
                  <div className="wind-rose__bar" style={{ width: `${width}%` }} />
                </div>
                <span>{bin.sample_count}</span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
