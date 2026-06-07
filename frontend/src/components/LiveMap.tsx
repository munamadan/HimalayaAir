import { useEffect, useMemo, useRef, useState, type MutableRefObject } from 'react';

import 'mapbox-gl/dist/mapbox-gl.css';
import 'maplibre-gl/dist/maplibre-gl.css';

import { getAqiBand, markerRadius } from '../lib/aqi';
import { interpolationToImage } from '../lib/heatmapCanvas';
import { formatFreshness } from '../lib/time';
import {
  loadMapEngine,
  type MapEngineModule,
  type MapInstance,
  type MapPopup,
  type MapProvider,
} from '../services/mapEngine';
import type { InterpolationResponse, StationSummary } from '../types/api';

const KATHMANDU_CENTER: [number, number] = [85.324, 27.7172];
const KATHMANDU_BOUNDS: [[number, number], [number, number]] = [[85.2, 27.55], [85.5, 27.8]];
const HEATMAP_SOURCE_ID = 'himalayaair-current-grid';
const HEATMAP_LAYER_ID = 'himalayaair-current-grid-layer';
const STATIONS_SOURCE_ID = 'himalayaair-stations';
const STATIONS_SELECTED_LAYER_ID = 'himalayaair-stations-selected';
const STATIONS_CIRCLE_LAYER_ID = 'himalayaair-stations-circles';
const STATIONS_LABEL_LAYER_ID = 'himalayaair-stations-labels';

interface PointFeatureCollection {
  type: 'FeatureCollection';
  features: PointFeature[];
}

interface PointFeature {
  type: 'Feature';
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  };
  properties: Record<string, string | number | boolean | null>;
}

interface LiveMapProps {
  stations: StationSummary[];
  interpolation: InterpolationResponse | null;
  selectedStationId: number | null;
  showHeatmap: boolean;
  onSelectStation: (stationId: number) => void;
  onToggleHeatmap: () => void;
}

export function LiveMap({
  stations,
  interpolation,
  selectedStationId,
  showHeatmap,
  onSelectStation,
  onToggleHeatmap,
}: LiveMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const mapModuleRef = useRef<MapEngineModule | null>(null);
  const popupRef = useRef<MapPopup | null>(null);
  const selectStationRef = useRef(onSelectStation);
  const [mapReady, setMapReady] = useState(false);
  const [provider, setProvider] = useState<MapProvider | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const selectedStation = useMemo(
    () => stations.find((station) => station.id === selectedStationId) ?? null,
    [selectedStationId, stations],
  );

  useEffect(() => {
    selectStationRef.current = onSelectStation;
  }, [onSelectStation]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }

    let cancelled = false;
    let mapInstance: MapInstance | null = null;

    loadMapEngine()
      .then((engine) => {
        if (cancelled || !containerRef.current) {
          return;
        }
        mapModuleRef.current = engine.mapModule;
        setProvider(engine.provider);
        setNotice(engine.notice);
        const map = new engine.mapModule.Map({
          container: containerRef.current,
          style: engine.styleUrl,
          center: KATHMANDU_CENTER,
          zoom: 11.35,
          minZoom: 10.2,
          maxBounds: KATHMANDU_BOUNDS,
          pitch: 0,
          bearing: 0,
          attributionControl: false,
        });
        mapRef.current = map;
        mapInstance = map;
        map.addControl(new engine.mapModule.NavigationControl({ visualizePitch: true }), 'bottom-right');
        map.addControl(new engine.mapModule.AttributionControl({ compact: true }), 'bottom-left');
        map.on('load', () => {
          ensureStationLayers(map);
          registerStationLayerEvents(map, selectStationRef);
          setMapReady(true);
        });
        map.on('error', (event: { error?: Error }) => {
          setNotice(event.error?.message || 'The map style could not be loaded.');
        });
      })
      .catch((error: unknown) => {
        setNotice(error instanceof Error ? error.message : 'The map engine could not be loaded.');
      });

    return () => {
      cancelled = true;
      popupRef.current?.remove();
      mapInstance?.remove();
      mapRef.current = null;
      setMapReady(false);
    };
  }, []);

  useEffect(() => {
    if (!mapReady || !mapRef.current || !mapModuleRef.current) {
      return;
    }

    ensureStationLayers(mapRef.current);
    setGeoJsonSourceData(mapRef.current, STATIONS_SOURCE_ID, stationsToFeatures(stations, selectedStationId));
  }, [mapReady, selectedStationId, stations]);

  useEffect(() => {
    if (!mapReady || !mapRef.current || !mapModuleRef.current) {
      return;
    }
    popupRef.current?.remove();
    if (!selectedStation) {
      popupRef.current = null;
      return;
    }
    popupRef.current = new mapModuleRef.current.Popup({ closeButton: false, offset: 22, className: 'station-map-popup' })
      .setLngLat([selectedStation.lon, selectedStation.lat])
      .setHTML(renderPopupHtml(selectedStation))
      .addTo(mapRef.current);
    mapRef.current.easeTo({ center: [selectedStation.lon, selectedStation.lat], zoom: Math.max(mapRef.current.getZoom(), 11.8), duration: 650 });
  }, [mapReady, selectedStation]);

  useEffect(() => {
    if (!mapReady || !mapRef.current) {
      return;
    }
    if (!showHeatmap || !interpolation) {
      removeHeatmap(mapRef.current);
      return;
    }
    const image = interpolationToImage(interpolation);
    if (!image) {
      removeHeatmap(mapRef.current);
      return;
    }
    upsertHeatmap(mapRef.current, image.url, image.coordinates, heatmapOpacity(interpolation));
  }, [interpolation, mapReady, showHeatmap]);

  const modeledBaselineMap = interpolation?.coverage_mode === 'MODELED_BASELINE' && !interpolation.insufficient_data;
  const heatmapStatus = heatmapStatusText(interpolation);

  return (
    <section className="map-panel" aria-label="Kathmandu Valley live AQI map">
      <div ref={containerRef} className="map-canvas" />
      <div className="map-panel__toolbar" aria-label="Map layer controls">
        <span className="layer-chip layer-chip--static">Stations</span>
        {modeledBaselineMap && <span className="layer-chip layer-chip--modeled">Modeled baseline map</span>}
        <button type="button" className="button button--secondary" onClick={onToggleHeatmap}>
          {showHeatmap ? 'AQI heatmap on' : 'AQI heatmap off'}
        </button>
      </div>
      <div className="map-panel__footer">
        <span>{provider ? `${provider} engine` : 'loading map engine'}</span>
        <span>{heatmapStatus}</span>
      </div>
      {notice && <p className="map-notice">{notice}</p>}
    </section>
  );
}

function upsertHeatmap(
  map: MapInstance,
  url: string,
  coordinates: [[number, number], [number, number], [number, number], [number, number]],
  opacity: number,
): void {
  const source = map.getSource(HEATMAP_SOURCE_ID);
  if (source?.updateImage) {
    source.updateImage({ url, coordinates });
  } else {
    removeHeatmap(map);
    map.addSource(HEATMAP_SOURCE_ID, {
      type: 'image',
      url,
      coordinates,
    });
  }

  if (!map.getLayer(HEATMAP_LAYER_ID)) {
    map.addLayer({
      id: HEATMAP_LAYER_ID,
      source: HEATMAP_SOURCE_ID,
      type: 'raster',
      paint: {
        'raster-opacity': opacity,
        'raster-fade-duration': 0,
      },
    }, map.getLayer(STATIONS_SELECTED_LAYER_ID) ? STATIONS_SELECTED_LAYER_ID : undefined);
  } else {
    map.setPaintProperty?.(HEATMAP_LAYER_ID, 'raster-opacity', opacity);
  }
}

function heatmapOpacity(interpolation: InterpolationResponse): number {
  return interpolation.coverage_mode === 'MODELED_BASELINE' ? 0.55 : 0.42;
}

function heatmapStatusText(interpolation: InterpolationResponse | null): string {
  if (!interpolation) {
    return 'no interpolation grid loaded';
  }
  if (interpolation.insufficient_data) {
    return interpolation.message;
  }
  if (interpolation.coverage_mode === 'MODELED_BASELINE') {
    return `${interpolation.coverage_mode} ${interpolation.source} grid, ${interpolation.confidence} confidence`;
  }
  return `${interpolation.source} grid, ${interpolation.station_count} input stations`;
}

function removeHeatmap(map: MapInstance): void {
  if (map.getLayer(HEATMAP_LAYER_ID)) {
    map.removeLayer(HEATMAP_LAYER_ID);
  }
  if (map.getSource(HEATMAP_SOURCE_ID)) {
    map.removeSource(HEATMAP_SOURCE_ID);
  }
}

function renderPopupHtml(station: StationSummary): string {
  const band = getAqiBand(station.current_aqi);
  return `
    <div class="station-popup-html">
      <strong>${escapeHtml(station.name)}</strong>
      <span style="background:${band.color};color:${band.textColor}">AQI ${station.current_aqi ?? 'not reported'}</span>
      <small>${escapeHtml(station.observation_type ?? 'not reported')} - ${escapeHtml(formatFreshness(station.freshness_minutes))}</small>
    </div>
  `;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function ensureStationLayers(map: MapInstance): void {
  if (!map.getSource(STATIONS_SOURCE_ID)) {
    map.addSource(STATIONS_SOURCE_ID, {
      type: 'geojson',
      data: emptyFeatureCollection(),
    });
  }

  if (!map.getLayer(STATIONS_SELECTED_LAYER_ID)) {
    map.addLayer({
      id: STATIONS_SELECTED_LAYER_ID,
      source: STATIONS_SOURCE_ID,
      type: 'circle',
      filter: ['==', ['get', 'selected'], true],
      paint: {
        'circle-radius': ['+', ['get', 'radius'], 5],
        'circle-color': '#ffffff',
        'circle-opacity': 0.92,
        'circle-stroke-color': '#b91f32',
        'circle-stroke-width': 3,
      },
    });
  }

  if (!map.getLayer(STATIONS_CIRCLE_LAYER_ID)) {
    map.addLayer({
      id: STATIONS_CIRCLE_LAYER_ID,
      source: STATIONS_SOURCE_ID,
      type: 'circle',
      paint: {
        'circle-radius': ['get', 'radius'],
        'circle-color': ['get', 'color'],
        'circle-opacity': 0.95,
        'circle-stroke-color': '#fffaf0',
        'circle-stroke-width': 2,
      },
    });
  }

  if (!map.getLayer(STATIONS_LABEL_LAYER_ID)) {
    map.addLayer({
      id: STATIONS_LABEL_LAYER_ID,
      source: STATIONS_SOURCE_ID,
      type: 'symbol',
      layout: {
        'text-field': ['get', 'aqiLabel'],
        'text-size': ['interpolate', ['linear'], ['zoom'], 9, 9, 11, 10, 13, 12],
        'text-allow-overlap': true,
        'text-ignore-placement': true,
      },
      paint: {
        'text-color': ['get', 'textColor'],
        'text-halo-color': 'rgba(255, 250, 240, 0.7)',
        'text-halo-width': 0.5,
      },
    });
  }
}

function registerStationLayerEvents(map: MapInstance, selectStationRef: MutableRefObject<(stationId: number) => void>): void {
  const handleClick = (event: { features?: Array<{ properties?: Record<string, unknown> }> }) => {
    const stationId = Number(event.features?.[0]?.properties?.stationId);
    if (Number.isFinite(stationId)) {
      selectStationRef.current(stationId);
    }
  };
  const showPointer = () => {
    map.getCanvas().style.cursor = 'pointer';
  };
  const hidePointer = () => {
    map.getCanvas().style.cursor = '';
  };

  [STATIONS_CIRCLE_LAYER_ID, STATIONS_LABEL_LAYER_ID].forEach((layerId) => {
    map.on('click', layerId, handleClick);
    map.on('mouseenter', layerId, showPointer);
    map.on('mouseleave', layerId, hidePointer);
  });
}

function setGeoJsonSourceData(map: MapInstance, sourceId: string, data: PointFeatureCollection): void {
  const source = map.getSource(sourceId);
  if (source?.setData) {
    source.setData(data);
  }
}

function stationsToFeatures(stations: StationSummary[], selectedStationId: number | null): PointFeatureCollection {
  return {
    type: 'FeatureCollection',
    features: stations.map((station) => {
      const band = getAqiBand(station.current_aqi);
      const aqiLabel = station.current_aqi === null || station.current_aqi === undefined ? '' : String(station.current_aqi);
      return {
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [station.lon, station.lat],
        },
        properties: {
          stationId: station.id,
          aqi: station.current_aqi,
          aqiLabel,
          color: band.color,
          textColor: band.textColor,
          selected: station.id === selectedStationId,
          radius: markerRadius(station.current_aqi) / 2,
        },
      };
    }),
  };
}

function emptyFeatureCollection(): PointFeatureCollection {
  return {
    type: 'FeatureCollection',
    features: [],
  };
}
