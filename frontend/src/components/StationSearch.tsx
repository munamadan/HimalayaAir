import { useEffect, useMemo, useRef, useState } from 'react';
import { Search, X } from 'lucide-react';

import { getAqiBand } from '../lib/aqi';
import { searchStations } from '../lib/stationSearch';
import type { StationSummary } from '../types/api';

interface StationSearchProps {
  stations: StationSummary[];
  selectedStation: StationSummary | null;
  onSelectStation: (station: StationSummary) => void;
}

export function StationSearch({ stations, selectedStation, onSelectStation }: StationSearchProps) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const results = useMemo(() => searchStations(stations, query), [query, stations]);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, []);

  useEffect(() => {
    setHighlightedIndex(0);
  }, [query]);

  const selectStation = (station: StationSummary) => {
    setQuery(station.name);
    setOpen(false);
    onSelectStation(station);
  };

  return (
    <div ref={rootRef} className="station-search">
      <Search size={18} aria-hidden="true" />
      <input
        type="search"
        value={query}
        placeholder={selectedStation?.name ?? 'Search stations'}
        aria-label="Search Kathmandu Valley stations"
        aria-expanded={open && results.length > 0}
        aria-controls="station-search-results"
        onFocus={() => setOpen(true)}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown' && results.length > 0) {
            event.preventDefault();
            setHighlightedIndex((current) => Math.min(current + 1, results.length - 1));
          }
          if (event.key === 'ArrowUp' && results.length > 0) {
            event.preventDefault();
            setHighlightedIndex((current) => Math.max(current - 1, 0));
          }
          if (event.key === 'Enter' && results[highlightedIndex]) {
            event.preventDefault();
            selectStation(results[highlightedIndex].station);
          }
          if (event.key === 'Escape') {
            setOpen(false);
          }
        }}
      />
      {query && (
        <button
          type="button"
          className="station-search__clear"
          aria-label="Clear station search"
          onClick={() => {
            setQuery('');
            setOpen(false);
          }}
        >
          <X size={16} aria-hidden="true" />
        </button>
      )}

      {open && query.trim() && (
        <div id="station-search-results" className="station-search__results" role="listbox">
          {results.length === 0 && <p>No stations match "{query.trim()}".</p>}
          {results.map(({ station }, index) => {
            const band = getAqiBand(station.current_aqi);
            return (
              <button
                key={station.id}
                type="button"
                role="option"
                aria-selected={index === highlightedIndex}
                className={index === highlightedIndex ? 'station-search__result station-search__result--active' : 'station-search__result'}
                onMouseEnter={() => setHighlightedIndex(index)}
                onClick={() => selectStation(station)}
              >
                <span>
                  <strong>{station.name}</strong>
                  <small>{station.freshness_minutes === null ? 'No recent update' : `${station.freshness_minutes} min ago`}</small>
                </span>
                <b style={{ background: band.color, color: band.textColor }}>
                  {station.current_aqi === null ? '--' : Math.round(station.current_aqi)}
                </b>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
