// Written with Super Intelligence (SI) assistance.
// Puts the layers of layers.json on the map and keeps them in step with the controls.
import type { ImageSource, Map as MapLibreMap } from "maplibre-gl";
import { asset, passSteps, type LayerEntry, type PassStep } from "./data";

export type Mode = "season" | "pass";

type Corners = [[number, number], [number, number], [number, number], [number, number]];

// The images are in Web Mercator, so their four corners follow from the bounds.
function corners(b: LayerEntry["bounds"]): Corners {
  const [west, south, east, north] = b;
  return [
    [west, north],
    [east, north],
    [east, south],
    [west, south],
  ];
}

export class Overlays {
  mode: Mode = "season";
  opacity = 0.9;
  stepIndex = 0;
  readonly on = new Set<string>();
  readonly statics: LayerEntry[];
  readonly steps: PassStep[];
  readonly sites: string[];

  private listeners: (() => void)[] = [];
  private loading = new Map<string, Promise<void>>();
  private ready = new Map<string, string>();
  private shownPass = new Map<string, string>();

  constructor(
    private map: MapLibreMap,
    readonly layers: LayerEntry[],
  ) {
    this.statics = layers.filter((l) => !l.date);
    this.steps = passSteps(layers);
    this.sites = [...new Set(layers.filter((l) => l.date).map((l) => l.site ?? ""))];
    for (const l of this.statics) {
      if (l.kind !== "reference" && l.kind !== "recovery") this.on.add(l.id);
    }
    this.sync();
  }

  onChange(fn: () => void): void {
    this.listeners.push(fn);
  }

  get step(): PassStep | null {
    return this.mode === "pass" ? (this.steps[this.stepIndex] ?? null) : null;
  }

  setLayer(id: string, on: boolean): void {
    if (on) this.on.add(id);
    else this.on.delete(id);
    this.changed();
  }

  setOpacity(value: number): void {
    this.opacity = value;
    this.changed();
  }

  setMode(mode: Mode): void {
    if (mode === "pass" && !this.steps.length) return;
    this.mode = mode;
    this.changed();
  }

  setStep(index: number): void {
    if (!this.steps.length) return;
    this.stepIndex = Math.min(this.steps.length - 1, Math.max(0, index));
    this.mode = "pass";
    this.changed();
  }

  // A whole-season layer is hidden while the map steps through single passes.
  isShown(entry: LayerEntry): boolean {
    return this.on.has(entry.id) && !(this.mode === "pass" && entry.kind === "season");
  }

  // Fetches every per-pass image once and keeps it in memory, so stepping does not wait on the network.
  preloadPasses(progress?: (done: number, total: number) => void): Promise<void> {
    const all = this.steps.flatMap((s) => s.layers);
    let done = 0;
    const queue = [...all];
    const worker = async (): Promise<void> => {
      for (let entry = queue.shift(); entry; entry = queue.shift()) {
        await this.load(entry);
        done += 1;
        progress?.(done, all.length);
      }
    };
    return Promise.all(Array.from({ length: 6 }, worker)).then(() => undefined);
  }

  private load(entry: LayerEntry): Promise<void> {
    let job = this.loading.get(entry.id);
    if (!job) {
      job = fetch(asset(entry.url))
        .then((res) => (res.ok ? res.blob() : Promise.reject(new Error(String(res.status)))))
        .then((blob) => {
          this.ready.set(entry.id, URL.createObjectURL(blob));
        })
        .catch(() => undefined); // A missing image is skipped; the map falls back to its plain address.
      this.loading.set(entry.id, job);
    }
    return job;
  }

  private changed(): void {
    this.sync();
    for (const fn of this.listeners) fn();
  }

  private sync(): void {
    for (const entry of this.statics) {
      const shown = this.isShown(entry);
      if (shown && !this.map.getLayer(entry.id)) this.addImage(entry.id, entry, asset(entry.url));
      this.show(entry.id, shown);
    }
    const step = this.step;
    for (const site of this.sites) {
      const id = `pass-${site}`;
      const entry = step?.layers.find((l) => (l.site ?? "") === site);
      if (entry) {
        const url = this.ready.get(entry.id) ?? asset(entry.url);
        if (!this.map.getLayer(id)) {
          this.addImage(id, entry, url);
        } else if (this.shownPass.get(site) !== entry.id) {
          (this.map.getSource(id) as ImageSource).updateImage({ url, coordinates: corners(entry.bounds) });
        }
        this.shownPass.set(site, entry.id);
      }
      this.show(id, Boolean(entry));
    }
  }

  private addImage(id: string, entry: LayerEntry, url: string): void {
    this.map.addSource(id, { type: "image", url, coordinates: corners(entry.bounds) });
    const marks = entry.kind === "reference" || entry.kind === "fire";
    this.map.addLayer(
      {
        id,
        type: "raster",
        source: id,
        paint: { "raster-opacity": this.opacity, "raster-fade-duration": 0 },
      },
      marks ? "z-marks" : "z-fall",
    );
  }

  private show(id: string, shown: boolean): void {
    if (!this.map.getLayer(id)) return;
    this.map.setLayoutProperty(id, "visibility", shown ? "visible" : "none");
    this.map.setPaintProperty(id, "raster-opacity", this.opacity);
  }
}
