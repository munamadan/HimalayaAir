import { useEffect, useState } from 'react';

import { getStationCurrent } from '../services/api';
import type { StationCurrentResponse } from '../types/api';

interface StationCurrentState {
  current: StationCurrentResponse | null;
  loading: boolean;
  error: string | null;
}

export function useStationCurrent(stationId: number | null): StationCurrentState {
  const [current, setCurrent] = useState<StationCurrentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!stationId) {
      setCurrent(null);
      setError(null);
      setLoading(false);
      return;
    }

    const abortController = new AbortController();
    setLoading(true);
    setError(null);

    getStationCurrent(stationId)
      .then((response) => {
        if (!abortController.signal.aborted) {
          setCurrent(response);
        }
      })
      .catch((reason: unknown) => {
        if (!abortController.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Could not load station details.');
        }
      })
      .finally(() => {
        if (!abortController.signal.aborted) {
          setLoading(false);
        }
      });

    return () => {
      abortController.abort();
    };
  }, [stationId]);

  return { current, loading, error };
}
