import { Pause, Play } from 'lucide-react';

import type { TimelineFrame } from '../types/api';

interface TimelineSliderProps {
  frameIndex: number;
  frameCount: number;
  activeFrame: TimelineFrame | null;
  isLive: boolean;
  isPlaying: boolean;
  isAvailable: boolean;
  isLoading: boolean;
  onFrameChange: (index: number) => void;
  onTogglePlay: () => void;
}

export function TimelineSlider({
  frameIndex,
  frameCount,
  activeFrame,
  isLive,
  isPlaying,
  isAvailable,
  isLoading,
  onFrameChange,
  onTogglePlay,
}: TimelineSliderProps) {
  let label = '';
  if (isLive) {
    label = 'Live';
  } else if (activeFrame) {
    const date = new Date(activeFrame.hour_bucket);
    label = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  if (isLoading || !isAvailable) return null;

  return (
    <div className="timeline-slider" aria-label="Air quality timeline">
      <button
        type="button"
        className="timeline-slider__play"
        onClick={onTogglePlay}
        aria-label={isPlaying ? 'Pause timeline' : 'Play timeline'}
        title={isPlaying ? 'Pause timeline' : 'Play timeline'}
      >
        {isPlaying ? <Pause size={15} fill="currentColor" aria-hidden="true" /> : <Play size={15} fill="currentColor" aria-hidden="true" />}
      </button>
      <input
        type="range"
        className="timeline-slider__range"
        min={0}
        max={frameCount - 1}
        value={frameIndex}
        onChange={(e) => onFrameChange(Number(e.target.value))}
        aria-label="Select hour"
        aria-valuetext={label}
      />
      <span className="timeline-slider__label">
        {isLive && <span className="timeline-slider__live-dot" />}
        {label}
      </span>
    </div>
  );
}
