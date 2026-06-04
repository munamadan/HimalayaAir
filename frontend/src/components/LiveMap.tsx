import { useEffect, useMemo, useRef, useState } from 'react';

import 'mapbox-gl/dist/mapbox-gl.css';
import 'maplibre-gl/dist/maplibre-gl.css';

import { getAqiBand, markerRadius } from '../lib/aqi';
import { interpolationToImage } from '../lib/heatmapCanvas';
import { formatFreshness } from '../lib/time';
import {
  loadMapEngine,
  type MapEngineModule,
  type MapInstance,
  type MapMarker,
  type MapPopup,
  type MapProvider,
} from '../services/mapEngine';
import type { FireEvent, InterpolationResponse, StationSummary } from '../types/api';

const KATHMANDU_CENTER: [number, number] = [85.324, 27.7172];
const HEATMAP_SOURCE_ID = 'himalayaair-current-grid';
const HEATMAP_LAYER_ID = 'himalayaair-current-grid-layer';

interface LiveMapProps {
  stations: StationSummary[];
  interpolation: InterpolationResponse | null;
  selectedStationId: number | null;
  showHeatmap: boolean;
  showFireEvents: boolean;
  fireEvents: FireEvent[];
  onSelectStation: (stationId: number) => void;
  onToggleHeatmap: () => void;
  onToggleFireEvents: () => void;
}

export function LiveMap({
  stations,
  interpolation,
  selectedStationId,
  showHeatmap,
  showFireEvents,
  fireEvents,
  onSelectStation,
  onToggleHeatmap,
  onToggleFireEvents,
}: LiveMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const mapModuleRef = useRef<MapEngineModule | null>(null);
  const markersRef = useRef<Map<number, MapMarker>>(new Map());
  const popupRef = useRef<MapPopup | null>(null);
  const fireMarkersRef = useRef<MapMarker[]>([]);
  const [mapReady, setMapReady] = useState(false);
  const [provider, setProvider] = useState<MapProvider | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const selectedStation = useMemo(
    () => stations.find((station) => station.id === selectedStationId) ?? null,
    [selectedStationId, stations],
  );

  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }

    let cancelled = false;
    let mapInstance: MapInstance | null = null;
    const markerStore = markersRef.current;

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
          pitch: 0,
          bearing: 0,
          attributionControl: false,
        });
        mapRef.current = map;
        mapInstance = map;
        map.addControl(new engine.mapModule.NavigationControl({ visualizePitch: true }), 'bottom-right');
        map.addControl(new engine.mapModule.AttributionControl({ compact: true }), 'bottom-left');
        map.on('load', () => setMapReady(true));
        map.on('error', (event: { error?: Error }) => {
          setNotice(event.error?.message || 'The map style could not be loaded.');
        });
      })
      .catch((error: unknown) => {
        setNotice(error instanceof Error ? error.message : 'The map engine could not be loaded.');
      });

    return () => {
      cancelled = true;
      markerStore.forEach((marker) => marker.remove());
      markerStore.clear();
      fireMarkersRef.current.forEach((marker) => marker.remove());
      fireMarkersRef.current = [];
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

    const map = mapRef.current;
    const mapModule = mapModuleRef.current;
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current.clear();

    stations.forEach((station) => {
      const element = document.createElement('button');
      const radius = markerRadius(station.current_aqi);
      const band = getAqiBand(station.current_aqi);
      element.type = 'button';
      element.className = station.id === selectedStationId ? 'station-marker station-marker--selected' : 'station-marker';
      element.style.width = `${radius}px`;
      element.style.height = `${radius}px`;
      element.style.background = band.color;
      element.style.color = band.textColor;
      element.setAttribute('aria-label', `${station.name}: AQI ${station.current_aqi ?? 'not available'}`);
      element.textContent = station.current_aqi === null || station.current_aqi === undefined ? '' : String(station.current_aqi);
      element.addEventListener('click', () => onSelectStation(station.id));

      const marker = new mapModule.Marker({ element, anchor: 'center' }).setLngLat([station.lon, station.lat]).addTo(map);
      markersRef.current.set(station.id, marker);
    });
  }, [mapReady, onSelectStation, selectedStationId, stations]);

  useEffect(() => {
    if (!mapReady || !mapRef.current || !mapModuleRef.current || !selectedStation) {
      return;
    }
    popupRef.current?.remove();
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
    upsertHeatmap(mapRef.current, image.url, image.coordinates);
  }, [interpolation, mapReady, showHeatmap]);

  useEffect(() => {
    if (!mapReady || !mapRef.current || !mapModuleRef.current) {
      return;
    }
    fireMarkersRef.current.forEach((marker) => marker.remove());
    fireMarkersRef.current = [];
    if (!showFireEvents) {
      return;
    }
    fireMarkersRef.current = fireEvents.map((event) => {
      const element = document.createElement('span');
      element.className = 'fire-marker';
      element.textContent = '\u25cf';
      element.setAttribute('aria-label', `Fire event ${event.acq_date}`);
      return new mapModuleRef.current!.Marker({ element, anchor: 'center' }).setLngLat([event.lon, event.lat]).addTo(mapRef.current!);
    });
  }, [fireEvents, mapReady, showFireEvents]);

  const heatmapStatus = interpolation?.insufficient_data
    ? interpolation.message
    : `${interpolation?.source ?? 'no source'} grid, ${interpolation?.station_count ?? 0} input stations`;

  return (
    <section className="map-panel" aria-label="Kathmandu Valley live AQI map">
      <div ref={containerRef} className="map-canvas" />
      <div className="map-panel__toolbar" aria-label="Map layer controls">
        <span className="layer-chip layer-chip--static">Stations</span>
        <button type="button" className="button button--secondary" onClick={onToggleHeatmap}>
          {showHeatmap ? 'AQI heatmap on' : 'AQI heatmap off'}
        </button>
        <button type="button" className="button button--secondary" onClick={onToggleFireEvents}>
          {showFireEvents ? 'Fire layer on' : 'Fire layer off'}
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
        'raster-opacity': 0.62,
        'raster-fade-duration': 300,
      },
    });
  }
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
