import { Activity, CalendarClock, History, Layers3, MapPin, Waves, Wind } from 'lucide-react';
import type { ReactNode } from 'react';

import type { InspectorMode } from '../types/ui';

interface AppRailProps {
  activeMode: InspectorMode;
  showHeatmap: boolean;
  showWind: boolean;
  showStations: boolean;
  heatmapAvailable: boolean;
  heatmapMessage: string | null;
  windAvailable: boolean;
  onModeChange: (mode: InspectorMode) => void;
  onToggleHeatmap: () => void;
  onToggleWind: () => void;
  onToggleStations: () => void;
}

export function AppRail({
  activeMode,
  showHeatmap,
  showWind,
  showStations,
  heatmapAvailable,
  heatmapMessage,
  windAvailable,
  onModeChange,
  onToggleHeatmap,
  onToggleWind,
  onToggleStations,
}: AppRailProps) {
  return (
    <nav className="app-rail" aria-label="Application views">
      <RailButton
        label="Now"
        active={activeMode === 'valley' || activeMode === 'station'}
        onClick={() => onModeChange('valley')}
        icon={<Activity size={20} />}
      />
      <RailButton
        label="Forecast"
        active={activeMode === 'forecast'}
        onClick={() => onModeChange('forecast')}
        icon={<CalendarClock size={20} />}
      />
      <RailButton
        label="History"
        active={activeMode === 'history'}
        onClick={() => onModeChange('history')}
        icon={<History size={20} />}
      />

      <div className="app-rail__separator" />

      <details className="layer-popover">
        <summary className="rail-button" aria-label="Map layers" data-label="Layers">
          <Layers3 size={20} aria-hidden="true" />
        </summary>
        <div className="layer-popover__panel">
          <header>
            <span>Map layers</span>
          </header>
          <LayerToggle
            label="AQI surface"
            checked={showHeatmap && heatmapAvailable}
            disabled={!heatmapAvailable}
            detail={heatmapAvailable ? null : heatmapMessage ?? 'AQI surface data is not available yet.'}
            onChange={onToggleHeatmap}
            icon={<Waves size={18} />}
          />
          <LayerToggle
            label="Wind flow"
            checked={showWind && windAvailable}
            disabled={!windAvailable}
            onChange={onToggleWind}
            icon={<Wind size={18} />}
          />
          <LayerToggle
            label="Station values"
            checked={showStations}
            onChange={onToggleStations}
            icon={<MapPin size={18} />}
          />
        </div>
      </details>
    </nav>
  );
}

interface RailButtonProps {
  label: string;
  active: boolean;
  icon: ReactNode;
  onClick: () => void;
}

function RailButton({ label, active, icon, onClick }: RailButtonProps) {
  return (
    <button
      type="button"
      className={active ? 'rail-button rail-button--active' : 'rail-button'}
      aria-label={label}
      data-label={label}
      onClick={onClick}
    >
      {icon}
    </button>
  );
}

interface LayerToggleProps {
  label: string;
  checked: boolean;
  disabled?: boolean;
  detail?: string | null;
  icon: ReactNode;
  onChange: () => void;
}

function LayerToggle({ label, checked, disabled = false, detail = null, icon, onChange }: LayerToggleProps) {
  return (
    <label className={disabled ? 'layer-toggle layer-toggle--disabled' : 'layer-toggle'}>
      <span className="layer-toggle__icon">{icon}</span>
      <span>
        <strong>{label}</strong>
        {detail && <small>{detail}</small>}
      </span>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={onChange} />
    </label>
  );
}
