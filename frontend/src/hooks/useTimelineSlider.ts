import { useCallback, useEffect, useRef, useState } from 'react';

import { getInterpolationTimeline } from '../services/api';
import type { InterpolationResponse, InterpolationTimelineResponse, TimelineFrame } from '../types/api';

interface UseTimelineSliderOptions {
  pollutant?: string;
  hours?: number;
  currentInterpolation: InterpolationResponse | null;
}

interface UseTimelineSliderReturn {
  activeInterpolation: InterpolationResponse | null;
  activeFrame: TimelineFrame | null;
  frameIndex: number;
  frameCount: number;
  isLive: boolean;
  isPlaying: boolean;
  isLoading: boolean;
  isAvailable: boolean;
  setFrameIndex: (index: number) => void;
  togglePlay: () => void;
}

export function useTimelineSlider({
  pollutant = 'pm25',
  hours = 24,
  currentInterpolation,
}: UseTimelineSliderOptions): UseTimelineSliderReturn {
  const [timeline, setTimeline] = useState<InterpolationTimelineResponse | null>(null);
  const [frameIndex, setFrameIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    getInterpolationTimeline(pollutant, hours)
      .then((data) => {
        if (!cancelled) {
          setTimeline(data);
          setFrameIndex(0);
        }
      })
      .catch(() => {
        if (!cancelled) setTimeline(null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, [pollutant, hours]);

  const frameCount = timeline?.frames.length ?? 0;
  const isAvailable = frameCount > 1;
  const isLive = frameIndex === 0;
  const activeFrame = timeline?.frames[frameIndex] ?? null;

  const activeInterpolation: InterpolationResponse | null = (() => {
    if (!isAvailable || !activeFrame || !timeline) {
      return currentInterpolation;
    }
    if (isLive) {
      return currentInterpolation;
    }
    return {
      grid: activeFrame.grid,
      station_count: activeFrame.station_count,
      coverage_mode: timeline.coverage_mode,
      confidence: timeline.confidence,
      source: timeline.source,
      computed_at: activeFrame.hour_bucket,
      insufficient_data: activeFrame.insufficient_data,
      message: `Historical: ${activeFrame.hour_bucket}`,
    };
  })();

  useEffect(() => {
    if (!isPlaying || !isAvailable) return;
    intervalRef.current = setInterval(() => {
      setFrameIndex((prev) => {
        const next = prev + 1;
        return next >= frameCount ? 0 : next;
      });
    }, 1500);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, isAvailable, frameCount]);

  const togglePlay = useCallback(() => {
    setIsPlaying((prev) => !prev);
  }, []);

  return {
    activeInterpolation,
    activeFrame,
    frameIndex,
    frameCount,
    isLive,
    isPlaying,
    isLoading,
    isAvailable,
    setFrameIndex,
    togglePlay,
  };
}
