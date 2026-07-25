import { ChevronDown, ChevronUp, PanelRightClose } from 'lucide-react';
import { useRef, type PointerEvent, type ReactNode } from 'react';

import type { MobileSheetSnap } from '../types/ui';

interface InspectorPanelProps {
  title: string;
  eyebrow: string;
  open: boolean;
  mobileSnap: MobileSheetSnap;
  children: ReactNode;
  onClose: () => void;
  onSnapChange: (snap: MobileSheetSnap) => void;
}

const SNAP_ORDER: MobileSheetSnap[] = ['peek', 'half', 'full'];

export function InspectorPanel({
  title,
  eyebrow,
  open,
  mobileSnap,
  children,
  onClose,
  onSnapChange,
}: InspectorPanelProps) {
  const dragStartY = useRef<number | null>(null);

  const moveSnap = (direction: -1 | 1) => {
    const currentIndex = SNAP_ORDER.indexOf(mobileSnap);
    const nextIndex = Math.max(0, Math.min(SNAP_ORDER.length - 1, currentIndex + direction));
    onSnapChange(SNAP_ORDER[nextIndex]);
  };

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    dragStartY.current = event.clientY;
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerUp = (event: PointerEvent<HTMLDivElement>) => {
    if (dragStartY.current === null) {
      return;
    }
    const delta = event.clientY - dragStartY.current;
    dragStartY.current = null;
    if (Math.abs(delta) < 60) {
      return;
    }
    moveSnap(delta > 0 ? -1 : 1);
  };

  return (
    <aside
      className={`app-inspector app-inspector--${open ? 'open' : 'collapsed'} app-inspector--snap-${mobileSnap}`}
      aria-label={`${title} inspector`}
    >
      <div
        className="app-inspector__drag-handle"
        aria-hidden="true"
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
      >
        <span />
      </div>
      <header className="app-inspector__header">
        <div>
          <span>{eyebrow}</span>
          <h1>{title}</h1>
        </div>
        <div className="app-inspector__actions">
          <button type="button" className="sheet-action sheet-action--mobile" aria-label="Expand panel" onClick={() => moveSnap(1)}>
            <ChevronUp size={18} aria-hidden="true" />
          </button>
          <button type="button" className="sheet-action sheet-action--mobile" aria-label="Collapse panel" onClick={() => moveSnap(-1)}>
            <ChevronDown size={18} aria-hidden="true" />
          </button>
          <button type="button" className="sheet-action sheet-action--desktop" aria-label="Collapse inspector" onClick={onClose}>
            <PanelRightClose size={18} aria-hidden="true" />
          </button>
        </div>
      </header>
      <div className="app-inspector__body">{children}</div>
    </aside>
  );
}
