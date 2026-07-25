import { useEffect, useMemo, useRef, useState, type MutableRefObject } from 'react';
import { Crosshair } from 'lucide-react';

import 'mapbox-gl/dist/mapbox-gl.css';
import 'maplibre-gl/dist/maplibre-gl.css';

import { AQI_BANDS, getAqiBand } from '../lib/aqi';
import { interpolationToImage } from '../lib/heatmapCanvas';
import { WindCanvasRenderer } from '../lib/windParticles';
import {
  loadMapEngine,
  type MapEngineModule,
  type MapInstance,
} from '../services/mapEngine';
import type { InterpolationResponse, StationSummary, WindGridResponse } from '../types/api';

const KATHMANDU_CENTER: [number, number] = [85.35, 27.69];
const KATHMANDU_CORE_BOUNDS: [[number, number], [number, number]] = [[85.225, 27.57], [85.49, 27.77]];
const HEATMAP_SOURCE_ID = 'himalayaair-current-grid';
const HEATMAP_LAYER_ID = 'himalayaair-current-grid-layer';
const STATIONS_SOURCE_ID = 'himalayaair-stations';
const STATIONS_SELECTED_LAYER_ID = 'himalayaair-stations-selected';
const STATIONS_DISC_LAYER_ID = 'himalayaair-stations-disc';
const STATIONS_VALUE_LAYER_ID = 'himalayaair-stations-value';
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
  properties: Record<string, string | number | boolean | null | number[]>;
}

interface LiveMapProps {
  stations: StationSummary[];
  interpolation: InterpolationResponse | null;
  windGrid: WindGridResponse | null;
  selectedStationId: number | null;
  showHeatmap: boolean;
  showWind: boolean;
  showStations: boolean;
  onSelectStation: (stationId: number) => void;
}

export function LiveMap({
  stations,
  interpolation,
  windGrid,
  selectedStationId,
  showHeatmap,
  showWind,
  showStations,
  onSelectStation,
}: LiveMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const mapModuleRef = useRef<MapEngineModule | null>(null);
  const selectStationRef = useRef(onSelectStation);
  const windCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const windRendererRef = useRef<WindCanvasRenderer | null>(null);
  const [mapReady, setMapReady] = useState(false);
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
    let loadTimeout: number | null = null;

    loadMapEngine()
      .then((engine) => {
        if (cancelled || !containerRef.current) {
          return;
        }
        mapModuleRef.current = engine.mapModule;
        setNotice(null);
        const map = new engine.mapModule.Map({
          container: containerRef.current,
          style: engine.styleUrl,
          center: KATHMANDU_CENTER,
          zoom: 11.25,
          minZoom: 10.6,
          maxBounds: KATHMANDU_CORE_BOUNDS,
          pitch: 0,
          bearing: 0,
          attributionControl: false,
        });
        mapRef.current = map;
        mapInstance = map;
        loadTimeout = window.setTimeout(() => {
          if (!cancelled) {
            setNotice('Map tiles are taking longer than expected. Station readings remain available.');
          }
        }, 8000);
        map.addControl(new engine.mapModule.NavigationControl({ visualizePitch: false }), 'bottom-right');
        map.addControl(new engine.mapModule.AttributionControl({ compact: true }), 'bottom-left');
        map.on('load', () => {
          if (loadTimeout !== null) {
            window.clearTimeout(loadTimeout);
            loadTimeout = null;
          }
          setNotice(null);
          ensureStationLayers(map);
          registerStationLayerEvents(map, selectStationRef);
          setMapReady(true);
        });
      })
      .catch(() => {
        setNotice('The map background could not load. Station readings remain available.');
      });

    return () => {
      cancelled = true;
      if (loadTimeout !== null) {
        window.clearTimeout(loadTimeout);
      }
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
    setGeoJsonSourceData(
      mapRef.current,
      STATIONS_SOURCE_ID,
      showStations ? stationsToFeatures(stations, selectedStationId) : emptyFeatureCollection(),
    );
  }, [mapReady, selectedStationId, showStations, stations]);

  useEffect(() => {
    if (!mapReady || !mapRef.current || !selectedStation) {
      return;
    }
    mapRef.current.easeTo({
      center: [selectedStation.lon, selectedStation.lat],
      zoom: Math.max(mapRef.current.getZoom(), 11.8),
      duration: 420,
    });
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

  useEffect(() => {
    if (!mapReady || !mapRef.current || !windCanvasRef.current) return;

    if (!windRendererRef.current) {
      windRendererRef.current = new WindCanvasRenderer({
        canvas: windCanvasRef.current,
        particleCount: 800,
      });
    }

    const map = mapRef.current;
    const renderer = windRendererRef.current;

    const updateProjection = () => {
      renderer.updateProjection((lngLat) => map.project(lngLat));
    };

    map.on('move', updateProjection);
    map.on('resize', () => renderer.resize());
    updateProjection();

    return () => {
      map.off('move', updateProjection);
      renderer.destroy();
      windRendererRef.current = null;
    };
  }, [mapReady]);

  useEffect(() => {
    const renderer = windRendererRef.current;
    if (!renderer) return;

    if (showWind && windGrid) {
      renderer.updateGrid(windGrid);
      renderer.updateProjection((lngLat) => mapRef.current!.project(lngLat));
      renderer.start();
    } else {
      renderer.stop();
    }
  }, [showWind, windGrid, mapReady]);

  const resetMapView = () => {
    mapRef.current?.easeTo({
      center: KATHMANDU_CENTER,
      zoom: 11.25,
      duration: 420,
    });
  };

  return (
    <section className="map-panel" aria-label="Kathmandu Valley live AQI map">
      <div ref={containerRef} className="map-canvas" />
      <canvas ref={windCanvasRef} className="wind-particle-canvas" aria-hidden="true" />

      <button
        type="button"
        className="map-reset-control"
        aria-label="Reset map to Kathmandu Valley"
        title="Reset map"
        onClick={resetMapView}
      >
        <Crosshair size={20} aria-hidden="true" />
      </button>

      <div className="map-legend" aria-label="AQI color legend">
        <strong>AQI</strong>
        {AQI_BANDS.slice(0, 5).map((band) => (
          <span key={band.label}>
            <i style={{ background: band.color }} />
            {band.shortLabel}
          </span>
        ))}
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
  return interpolation.coverage_mode === 'MODELED_BASELINE' ? 0.64 : 0.56;
}

function removeHeatmap(map: MapInstance): void {
  if (map.getLayer(HEATMAP_LAYER_ID)) {
    map.removeLayer(HEATMAP_LAYER_ID);
  }
  if (map.getSource(HEATMAP_SOURCE_ID)) {
    map.removeSource(HEATMAP_SOURCE_ID);
  }
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
        'circle-radius': ['+', ['get', 'discRadius'], 5],
        'circle-color': 'rgba(255, 255, 255, 0)',
        'circle-stroke-color': ['get', 'color'],
        'circle-stroke-width': 2.4,
        'circle-stroke-opacity': 0.9,
      },
    });
  }

  if (!map.getLayer(STATIONS_DISC_LAYER_ID)) {
    map.addLayer({
      id: STATIONS_DISC_LAYER_ID,
      source: STATIONS_SOURCE_ID,
      type: 'circle',
      paint: {
        'circle-radius': ['get', 'discRadius'],
        'circle-color': ['get', 'color'],
        'circle-opacity': 0.94,
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': ['case', ['get', 'selected'], 2.2, 1.4],
      },
    });
  }

  if (!map.getLayer(STATIONS_VALUE_LAYER_ID)) {
    map.addLayer({
      id: STATIONS_VALUE_LAYER_ID,
      source: STATIONS_SOURCE_ID,
      type: 'symbol',
      layout: {
        'text-field': ['get', 'aqiValue'],
        'text-size': ['interpolate', ['linear'], ['zoom'], 10, 11, 12, 12.5, 14, 14],
        'text-allow-overlap': true,
        'text-ignore-placement': true,
      },
      paint: {
        'text-color': ['get', 'textColor'],
      },
    });
  }

  if (!map.getLayer(STATIONS_LABEL_LAYER_ID)) {
    map.addLayer({
      id: STATIONS_LABEL_LAYER_ID,
      source: STATIONS_SOURCE_ID,
      type: 'symbol',
      layout: {
        'text-field': ['get', 'stationName'],
        'text-size': ['interpolate', ['linear'], ['zoom'], 10, 10, 12, 11, 14, 12],
        'text-offset': ['get', 'labelOffset'],
        'text-anchor': 'top',
        'text-allow-overlap': false,
        'text-ignore-placement': false,
      },
      paint: {
        'text-color': '#15202b',
        'text-halo-color': 'rgba(255, 255, 255, 0.92)',
        'text-halo-width': 1.4,
        'text-halo-blur': 0.2,
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

  [STATIONS_DISC_LAYER_ID, STATIONS_VALUE_LAYER_ID, STATIONS_SELECTED_LAYER_ID, STATIONS_LABEL_LAYER_ID].forEach((layerId) => {
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
      const hasAqi = station.current_aqi !== null && station.current_aqi !== undefined;
      const aqiValue = hasAqi ? String(Math.round(station.current_aqi as number)) : '--';
      const discRadius = stationDiscRadius(station.current_aqi);
      const stationName = compactStationName(station.name);
      return {
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [station.lon, station.lat],
        },
        properties: {
          stationId: station.id,
          aqi: station.current_aqi,
          aqiValue,
          stationName,
          color: band.color,
          textColor: band.textColor,
          discRadius,
          labelOffset: [0, (discRadius + 6) / 12],
          selected: station.id === selectedStationId,
        },
      };
    }),
  };
}

function stationDiscRadius(aqi: number | null | undefined): number {
  if (aqi === null || aqi === undefined) {
    return 12;
  }
  return Math.max(13, Math.min(22, 13 + aqi / 22));
}

function compactStationName(name: string): string {
  const cleaned = name
    .replace(/\s+replay\s+station$/i, '')
    .replace(/\s+fixture\s+station$/i, '')
    .replace(/\s*-\s*Kathmandu$/i, '')
    .trim();
  return cleaned.length > 24 ? `${cleaned.slice(0, 21)}...` : cleaned;
}

function emptyFeatureCollection(): PointFeatureCollection {
  return {
    type: 'FeatureCollection',
    features: [],
  };
}
