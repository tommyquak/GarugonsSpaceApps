// Written with Super Intelligence (SI) assistance.
// Types and loaders for the files that scripts/make_layers.py writes into public/.

export interface Ramp {
  title?: string;
  colors: string[];
  scale: [number, number];
  shown_from: number;
  full_at: number;
}

export type LayerKind = "season" | "pass" | "reference" | "fire" | "recovery";

// One entry of layers/layers.json (docs/DATA_CONTRACT.md section 5, plus a few fields).
export interface LayerEntry {
  id: string;
  title: string;
  url: string;
  bounds: [number, number, number, number]; // west, south, east, north
  date: string | null;
  unit: string | null;
  legend: string;
  source: string;
  kind?: LayerKind;
  site?: string;
  track?: string;
  orbit?: string | null;
  ramp?: Ramp;
  color?: string;
}

// One radar pass: a date and a track, with one image per site.
export interface PassStep {
  date: string;
  track: string;
  orbit: string | null;
  layers: LayerEntry[];
}

export function asset(path: string): string {
  return import.meta.env.BASE_URL + path.replace(/^\//, "");
}

export async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(asset(path));
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function loadLayers(): Promise<LayerEntry[]> {
  const list = await fetchJson<LayerEntry[]>("layers/layers.json");
  return Array.isArray(list) ? list.filter((e) => e && e.id && e.url && Array.isArray(e.bounds)) : [];
}

export function passSteps(layers: LayerEntry[]): PassStep[] {
  const steps = new Map<string, PassStep>();
  for (const entry of layers) {
    if (!entry.date) continue;
    const track = entry.track ?? "";
    const key = `${entry.date}|${track}`;
    let step = steps.get(key);
    if (!step) {
      step = { date: entry.date, track, orbit: entry.orbit ?? null, layers: [] };
      steps.set(key, step);
    }
    step.layers.push(entry);
  }
  return [...steps.values()].sort((a, b) => a.date.localeCompare(b.date) || a.track.localeCompare(b.track));
}

export function unionBounds(layers: LayerEntry[]): [number, number, number, number] | null {
  if (!layers.length) return null;
  return [
    Math.min(...layers.map((l) => l.bounds[0])),
    Math.min(...layers.map((l) => l.bounds[1])),
    Math.max(...layers.map((l) => l.bounds[2])),
    Math.max(...layers.map((l) => l.bounds[3])),
  ];
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export function parseDay(iso: string): Date {
  return new Date(`${iso}T00:00:00Z`);
}

export function monthName(iso: string): string {
  return MONTHS[parseDay(iso).getUTCMonth()];
}

export function formatDay(iso: string): string {
  const day = parseDay(iso);
  return `${day.getUTCDate()} ${monthName(iso).slice(0, 3)} ${day.getUTCFullYear()}`;
}

export function passLabel(step: { date: string; track: string; orbit: string | null }): string {
  const orbit = step.orbit ? ` (${step.orbit} pass)` : "";
  return `${formatDay(step.date)}, track ${step.track}${orbit}`;
}

// Colour of a ramp at a value, linear between evenly spaced stops, as in the pipeline's map.
export function rampColor(ramp: Ramp, value: number): string {
  const [lo, hi] = ramp.scale;
  const t = Math.min(1, Math.max(0, (value - lo) / (hi - lo)));
  const x = t * (ramp.colors.length - 1);
  const i = Math.min(Math.floor(x), ramp.colors.length - 2);
  const f = x - i;
  const a = hexRgb(ramp.colors[i]);
  const b = hexRgb(ramp.colors[i + 1]);
  const mix = a.map((v, k) => Math.round(v * (1 - f) + b[k] * f));
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`;
}

function hexRgb(hex: string): number[] {
  return [1, 3, 5].map((k) => parseInt(hex.slice(k, k + 2), 16));
}
