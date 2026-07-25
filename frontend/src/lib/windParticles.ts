import type { WindGridResponse } from '../types/api';

interface Particle {
  lng: number;
  lat: number;
  prevLng: number;
  prevLat: number;
  age: number;
  maxAge: number;
}

interface ProjectFn {
  (lngLat: [number, number]): { x: number; y: number };
}

export interface WindCanvasRendererOptions {
  canvas: HTMLCanvasElement;
  particleCount?: number;
  fadeOpacity?: number;
  lineWidth?: number;
  particleColor?: string;
  speedScale?: number;
}

const DEFAULT_PARTICLE_COUNT = 800;
const DEFAULT_FADE_OPACITY = 0.93;
const DEFAULT_LINE_WIDTH = 1.2;
const DEFAULT_PARTICLE_COLOR = 'rgba(12, 96, 130, 0.58)';
const DEFAULT_SPEED_SCALE = 0.00004;
const MIN_PARTICLE_AGE = 40;
const MAX_PARTICLE_AGE = 100;
const FRAME_INTERVAL_MS = 33;

export class WindCanvasRenderer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D | null;
  private grid: WindGridResponse | null = null;
  private project: ProjectFn | null = null;
  private particles: Particle[] = [];
  private animationId: number | null = null;
  private lastFrameTime = 0;
  private running = false;

  private particleCount: number;
  private fadeOpacity: number;
  private lineWidth: number;
  private particleColor: string;
  private speedScale: number;

  constructor(options: WindCanvasRendererOptions) {
    this.canvas = options.canvas;
    this.ctx = this.canvas.getContext('2d');
    this.particleCount = options.particleCount ?? DEFAULT_PARTICLE_COUNT;
    this.fadeOpacity = options.fadeOpacity ?? DEFAULT_FADE_OPACITY;
    this.lineWidth = options.lineWidth ?? DEFAULT_LINE_WIDTH;
    this.particleColor = options.particleColor ?? DEFAULT_PARTICLE_COLOR;
    this.speedScale = options.speedScale ?? DEFAULT_SPEED_SCALE;
  }

  updateGrid(grid: WindGridResponse): void {
    this.grid = grid;
    if (this.particles.length === 0) {
      this.initParticles();
    }
  }

  updateProjection(project: ProjectFn): void {
    this.project = project;
  }

  resize(): void {
    const rect = this.canvas.parentElement?.getBoundingClientRect();
    if (rect) {
      this.canvas.width = rect.width * (window.devicePixelRatio || 1);
      this.canvas.height = rect.height * (window.devicePixelRatio || 1);
      this.canvas.style.width = `${rect.width}px`;
      this.canvas.style.height = `${rect.height}px`;
      this.ctx?.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
    }
  }

  start(): void {
    if (this.running) return;
    this.running = true;
    this.resize();
    this.initParticles();
    this.lastFrameTime = performance.now();
    this.tick();
  }

  stop(): void {
    this.running = false;
    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
    this.clearCanvas();
  }

  destroy(): void {
    this.stop();
    this.particles = [];
    this.grid = null;
    this.project = null;
  }

  private tick = (): void => {
    if (!this.running) return;
    this.animationId = requestAnimationFrame(this.tick);

    const now = performance.now();
    if (now - this.lastFrameTime < FRAME_INTERVAL_MS) return;
    this.lastFrameTime = now;

    this.drawFrame();
  };

  private drawFrame(): void {
    const ctx = this.ctx;
    if (!ctx || !this.grid || !this.project) return;

    const width = this.canvas.width / (window.devicePixelRatio || 1);
    const height = this.canvas.height / (window.devicePixelRatio || 1);

    ctx.globalCompositeOperation = 'destination-in';
    ctx.fillStyle = `rgba(0, 0, 0, ${this.fadeOpacity})`;
    ctx.fillRect(0, 0, width, height);
    ctx.globalCompositeOperation = 'source-over';

    ctx.strokeStyle = this.particleColor;
    ctx.lineWidth = this.lineWidth;
    ctx.lineCap = 'round';

    for (const particle of this.particles) {
      const wind = this.interpolateWind(particle.lng, particle.lat);
      if (!wind) {
        this.respawnParticle(particle);
        continue;
      }

      particle.prevLng = particle.lng;
      particle.prevLat = particle.lat;
      particle.lng += wind.u * this.speedScale;
      particle.lat += wind.v * this.speedScale;
      particle.age += 1;

      if (particle.age >= particle.maxAge || this.isOutOfBounds(particle)) {
        this.respawnParticle(particle);
        continue;
      }

      const from = this.project([particle.prevLng, particle.prevLat]);
      const to = this.project([particle.lng, particle.lat]);

      if (from.x < 0 || from.x > width || from.y < 0 || from.y > height) {
        this.respawnParticle(particle);
        continue;
      }

      const ageFraction = particle.age / particle.maxAge;
      const alpha = 1 - ageFraction * ageFraction;
      ctx.globalAlpha = alpha;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  private interpolateWind(lng: number, lat: number): { u: number; v: number } | null {
    const grid = this.grid;
    if (!grid) return null;

    const { bounds, rows, cols } = grid;
    const latFrac = (lat - bounds.min_lat) / (bounds.max_lat - bounds.min_lat) * (rows - 1);
    const lonFrac = (lng - bounds.min_lon) / (bounds.max_lon - bounds.min_lon) * (cols - 1);

    if (latFrac < 0 || latFrac >= rows - 1 || lonFrac < 0 || lonFrac >= cols - 1) {
      return null;
    }

    const row0 = Math.floor(latFrac);
    const col0 = Math.floor(lonFrac);
    const row1 = row0 + 1;
    const col1 = col0 + 1;
    const rowT = latFrac - row0;
    const colT = lonFrac - col0;

    const p00 = grid.grid[row0][col0];
    const p01 = grid.grid[row0][col1];
    const p10 = grid.grid[row1][col0];
    const p11 = grid.grid[row1][col1];

    const u = bilinear(p00.u, p01.u, p10.u, p11.u, colT, rowT);
    const v = bilinear(p00.v, p01.v, p10.v, p11.v, colT, rowT);

    return { u, v };
  }

  private initParticles(): void {
    this.particles = [];
    for (let i = 0; i < this.particleCount; i++) {
      this.particles.push(this.createParticle());
    }
  }

  private createParticle(): Particle {
    const grid = this.grid;
    const bounds = grid?.bounds ?? { min_lat: 27.57, max_lat: 27.77, min_lon: 85.225, max_lon: 85.49 };
    const lng = bounds.min_lon + Math.random() * (bounds.max_lon - bounds.min_lon);
    const lat = bounds.min_lat + Math.random() * (bounds.max_lat - bounds.min_lat);
    return {
      lng,
      lat,
      prevLng: lng,
      prevLat: lat,
      age: Math.floor(Math.random() * MIN_PARTICLE_AGE),
      maxAge: MIN_PARTICLE_AGE + Math.floor(Math.random() * (MAX_PARTICLE_AGE - MIN_PARTICLE_AGE)),
    };
  }

  private respawnParticle(particle: Particle): void {
    const fresh = this.createParticle();
    particle.lng = fresh.lng;
    particle.lat = fresh.lat;
    particle.prevLng = fresh.lng;
    particle.prevLat = fresh.lat;
    particle.age = 0;
    particle.maxAge = fresh.maxAge;
  }

  private isOutOfBounds(particle: Particle): boolean {
    const bounds = this.grid?.bounds;
    if (!bounds) return true;
    return (
      particle.lng < bounds.min_lon ||
      particle.lng > bounds.max_lon ||
      particle.lat < bounds.min_lat ||
      particle.lat > bounds.max_lat
    );
  }

  private clearCanvas(): void {
    const ctx = this.ctx;
    if (!ctx) return;
    const width = this.canvas.width / (window.devicePixelRatio || 1);
    const height = this.canvas.height / (window.devicePixelRatio || 1);
    ctx.clearRect(0, 0, width, height);
  }
}

function bilinear(p00: number, p01: number, p10: number, p11: number, tx: number, ty: number): number {
  const top = p00 * (1 - tx) + p01 * tx;
  const bottom = p10 * (1 - tx) + p11 * tx;
  return top * (1 - ty) + bottom * ty;
}
