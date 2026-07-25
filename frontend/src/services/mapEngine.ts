const MAPLIBRE_DEFAULT_STYLE: Record<string, unknown> = {
  version: 8,
  name: 'HimalayaAir Light',
  sources: {
    'openstreetmap-light': {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      maxzoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    },
  },
  layers: [
    {
      id: 'openstreetmap-light',
      type: 'raster',
      source: 'openstreetmap-light',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};
const MAPBOX_DEFAULT_STYLE = 'mapbox://styles/mapbox/light-v11';

export type MapProvider = 'mapbox' | 'maplibre';

export interface MapEngineModule {
  accessToken?: string;
  Map: new (options: MapCreateOptions) => MapInstance;
  Marker: new (options: MarkerCreateOptions) => MapMarker;
  Popup: new (options: PopupCreateOptions) => MapPopup;
  NavigationControl: new (options?: Record<string, unknown>) => unknown;
  AttributionControl: new (options?: Record<string, unknown>) => unknown;
}

export interface MapCreateOptions {
  container: HTMLElement;
  style: string | Record<string, unknown>;
  center: [number, number];
  zoom: number;
  maxBounds?: [[number, number], [number, number]];
  minZoom?: number;
  pitch?: number;
  bearing?: number;
  attributionControl?: boolean;
}

export interface MarkerCreateOptions {
  element: HTMLElement;
  anchor?: string;
}

export interface PopupCreateOptions {
  closeButton?: boolean;
  offset?: number;
  className?: string;
}

export interface MapMarker {
  setLngLat(coordinates: [number, number]): MapMarker;
  addTo(map: MapInstance): MapMarker;
  remove(): void;
}

export interface MapPopup {
  setLngLat(coordinates: [number, number]): MapPopup;
  setHTML(html: string): MapPopup;
  addTo(map: MapInstance): MapPopup;
  remove(): void;
}

export interface MapImageSource {
  updateImage?(image: {
    url: string;
    coordinates: [[number, number], [number, number], [number, number], [number, number]];
  }): void;
  setData?(data: unknown): void;
}

export interface MapInstance {
  addControl(control: unknown, position?: string): void;
  addLayer(layer: Record<string, unknown>, beforeId?: string): void;
  addSource(id: string, source: Record<string, unknown>): void;
  easeTo(options: { center: [number, number]; zoom: number; duration: number }): void;
  getCanvas(): HTMLCanvasElement;
  getLayer(id: string): unknown;
  getSource(id: string): MapImageSource | undefined;
  getZoom(): number;
  on(event: 'load', callback: () => void): void;
  on(event: 'error', callback: (event: { error?: Error }) => void): void;
  on(event: 'click' | 'mouseenter' | 'mouseleave', layerId: string, callback: (event: MapLayerEvent) => void): void;
  on(event: 'move' | 'moveend' | 'resize', callback: () => void): void;
  off(event: 'move' | 'moveend' | 'resize', callback: () => void): void;
  project(lngLat: [number, number]): { x: number; y: number };
  unproject(point: { x: number; y: number }): { lng: number; lat: number };
  remove(): void;
  removeLayer(id: string): void;
  removeSource(id: string): void;
  setPaintProperty?(layerId: string, propertyName: string, value: unknown): void;
}

export interface MapLayerEvent {
  features?: Array<{
    properties?: Record<string, unknown>;
  }>;
}

export interface LoadedMapEngine {
  mapModule: MapEngineModule;
  provider: MapProvider;
  styleUrl: string | Record<string, unknown>;
  notice: string | null;
}

export async function loadMapEngine(): Promise<LoadedMapEngine> {
  const requested = (import.meta.env.VITE_MAP_PROVIDER || 'maplibre').toLowerCase();
  const token = import.meta.env.VITE_MAPBOX_TOKEN || '';
  const configuredStyle = import.meta.env.VITE_MAP_STYLE_URL || '';

  if (requested === 'mapbox' && token) {
    const mapbox = await import('mapbox-gl');
    const mapModule = (mapbox.default ?? mapbox) as unknown as MapEngineModule;
    mapModule.accessToken = token;
    return {
      mapModule,
      provider: 'mapbox',
      styleUrl: configuredStyle || MAPBOX_DEFAULT_STYLE,
      notice: null,
    };
  }

  const maplibre = await import('maplibre-gl');
  const mapModule = (maplibre.default ?? maplibre) as unknown as MapEngineModule;
  const styleUrl =
    configuredStyle && !configuredStyle.startsWith('mapbox://')
      ? configuredStyle
      : MAPLIBRE_DEFAULT_STYLE;
  return {
    mapModule,
    provider: 'maplibre',
    styleUrl,
    notice: requested === 'mapbox' ? 'MapLibre fallback is active because no public Mapbox token is configured.' : null,
  };
}
