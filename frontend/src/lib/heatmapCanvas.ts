import type { InterpolationResponse } from '../types/api';
import { getAqiBand } from './aqi';

export interface HeatmapImage {
  url: string;
  coordinates: [[number, number], [number, number], [number, number], [number, number]];
}

export function hasUsableHeatmap(interpolation: InterpolationResponse | null | undefined): boolean {
  if (!interpolation) {
    return false;
  }
  const { rows, cols, values } = interpolation.grid;
  return !interpolation.insufficient_data && rows > 0 && cols > 0 && values.length > 0;
}

export function interpolationToImage(interpolation: InterpolationResponse): HeatmapImage | null {
  if (!hasUsableHeatmap(interpolation)) {
    return null;
  }
  const values = interpolation.grid.values;
  const rows = interpolation.grid.rows;
  const cols = interpolation.grid.cols;

  const canvas = document.createElement('canvas');
  canvas.width = cols;
  canvas.height = rows;
  const context = canvas.getContext('2d');
  if (!context) {
    return null;
  }

  const image = context.createImageData(cols, rows);
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const value = values[row]?.[col] ?? null;
      const index = (row * cols + col) * 4;
      const [red, green, blue, alpha] = colorForValue(value);
      image.data[index] = red;
      image.data[index + 1] = green;
      image.data[index + 2] = blue;
      image.data[index + 3] = alpha;
    }
  }
  context.putImageData(image, 0, 0);

  const bounds = interpolation.grid.bounds;
  return {
    url: canvas.toDataURL('image/png'),
    coordinates: [
      [bounds.min_lon, bounds.max_lat],
      [bounds.max_lon, bounds.max_lat],
      [bounds.max_lon, bounds.min_lat],
      [bounds.min_lon, bounds.min_lat],
    ],
  };
}

function colorForValue(value: number | null): [number, number, number, number] {
  if (value === null || Number.isNaN(value)) {
    return [0, 0, 0, 0];
  }
  const band = getAqiBand(value);
  const [red, green, blue] = hexToRgb(band.color);
  return [red, green, blue, 150];
}

function hexToRgb(hex: string): [number, number, number] {
  const normalized = hex.replace('#', '');
  return [
    Number.parseInt(normalized.slice(0, 2), 16),
    Number.parseInt(normalized.slice(2, 4), 16),
    Number.parseInt(normalized.slice(4, 6), 16),
  ];
}
