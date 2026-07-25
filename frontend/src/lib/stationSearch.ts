import type { StationSummary } from '../types/api';
import type { StationSearchResult } from '../types/ui';

export function searchStations(
  stations: StationSummary[],
  query: string,
  limit = 8,
): StationSearchResult[] {
  const normalizedQuery = normalize(query);
  if (!normalizedQuery) {
    return [];
  }

  return stations
    .flatMap((station) => {
      const score = stationMatchScore(station, normalizedQuery);
      return score === null ? [] : [{ station, score }];
    })
    .sort((left, right) => {
      if (left.score !== right.score) {
        return left.score - right.score;
      }
      const leftHasData = left.station.current_aqi !== null && left.station.current_aqi !== undefined;
      const rightHasData = right.station.current_aqi !== null && right.station.current_aqi !== undefined;
      if (leftHasData !== rightHasData) {
        return leftHasData ? -1 : 1;
      }
      return left.station.name.localeCompare(right.station.name);
    })
    .slice(0, limit);
}

function stationMatchScore(station: StationSummary, normalizedQuery: string): number | null {
  const name = normalize(station.name);
  let score: number | null = null;

  if (name === normalizedQuery) {
    score = 0;
  } else if (name.startsWith(normalizedQuery)) {
    score = 100;
  } else {
    const wordIndex = name.split(' ').findIndex((word) => word.startsWith(normalizedQuery));
    if (wordIndex >= 0) {
      score = 200 + wordIndex;
    } else {
      const substringIndex = name.indexOf(normalizedQuery);
      if (substringIndex >= 0) {
        score = 300 + substringIndex;
      }
    }
  }

  if (score === null) {
    return null;
  }
  if (!station.active) {
    score += 20;
  }
  if (station.current_aqi === null || station.current_aqi === undefined) {
    score += 5;
  }
  return score;
}

function normalize(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}
