// Written with Super Intelligence (SI) assistance.
// Click a place: reads the time series of that cell (docs/DATA_CONTRACT.md section 4) and draws
// HH and HV over the season for both orbits, with a plain reading of what HH did, the days
// with a fire detection in that cell, and daily rain.
//
//   createPlaceChart(byId("panel-place"), map, overlays, () => setTab("place"));
import { Marker, type Map as MapLibreMap } from "maplibre-gl";
import { asset, fetchJson, formatDay, monthName, parseDay } from "../data";
import { withChips, type NumberEntry } from "../chip";
import { h } from "../dom";
import type { Overlays } from "../overlays";

interface Band {
  track: string;
  pol: string;
  date: string;
}

interface SeriesMeta {
  site: string;
  bounds: [number, number, number, number];
  cell_deg: number;
  rows: number;
  cols: number;
  scale: number;
  offset: number;
  nodata: number;
  bands: Band[];
}

interface SiteFiles {
  series: string;
  bin: string;
  rain: string | null;
  fires?: string | null; // fire dates per cell, contract section 4
}

interface Site {
  meta: SeriesMeta;
  files: SiteFiles;
  bin?: Promise<Uint8Array | null>;
  rain?: Promise<Record<string, number> | null>;
  fires?: Promise<Record<string, string[]> | null>;
}

interface Pass {
  date: string;
  track: string;
  hh: number | null;
  hv: number | null;
}

// Two series colours checked for colour-blind separation and contrast on the dark panel.
const TRACK_COLORS = ["#c98500", "#3987e5"];
const SVG = "http://www.w3.org/2000/svg";
const W = 320;
const LEFT = 36;
const RIGHT = 10;
const PANEL_H = 84;
const PANEL_GAP = 22;
const AXIS_H = 18;
const TOP = 18;
const RAIN_H = 34;
const FIRE_H = 14;

function svg<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number> = {}, text?: string): SVGElementTagNameMap[K] {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  if (text !== undefined) el.textContent = text;
  return el;
}

function db(value: number): string {
  return `${value.toFixed(1)} dB`;
}

function mean(values: number[]): number {
  return values.reduce((a, b) => a + b, 0) / values.length;
}

// The dry season as the pipeline defines it from the rainfall record (pipeline/season.py),
// read from validation.json so the card measures the fall the same way the map does.
interface SeasonRule {
  startFrom: string; // earliest day a start pass may fall on
  lastDry: string; // last dry day before the rain came back
  // The validation.json keys the two dates were read from. The reading marks the phrase that
  // rests on each as [[key|phrase]], which chip.ts turns into a chip that shows the entry.
  startKey: string;
  lastDryKey: string;
  numbers: Record<string, NumberEntry | undefined>;
}

const PAIR_DAYS = 14; // as in pipeline/season.py: the second start pass must follow within this

// A plain sentence on HH for one orbit, by the pipeline's rule (pipeline/drying/drydown.py):
// the start passes (the first pass on or after the dry start, and the next if it follows
// within 14 days) against the last two later passes before the rain, and then what the first
// pass after the rain did. The passes are chosen by date first, as the pipeline does, and only
// then read: if one of them has no data here, the card says so and does not fall back on
// other dates, which would be a different measurement from the one the map shows.
function reading(passes: Pass[], orbit: string, rule: SeasonRule): string | null {
  const first = passes.findIndex((p) => p.date >= rule.startFrom);
  if (first < 0) return null;
  const start = [passes[first]];
  const next = passes[first + 1];
  if (next && (parseDay(next.date).getTime() - parseDay(passes[first].date).getTime()) / 86_400_000 <= PAIR_DAYS) start.push(next);
  const late = passes.filter((p, i) => p.date <= rule.lastDry && i > first + start.length - 1).slice(-2);
  if (late.length < 2) return null;
  const name = orbit.charAt(0).toUpperCase() + orbit.slice(1);
  const levels = (group: Pass[]): number[] | null => (group.every((p) => p.hh !== null) ? group.map((p) => p.hh as number) : null);
  const startValues = levels(start);
  const lateValues = levels(late);
  if (!startValues || !lateValues) return `${name} pass: not enough data at this place for a reading (a pass it is measured from is missing).`;
  const lateLevel = mean(lateValues);
  const span = `between the [[${rule.startKey}|dry start in ${monthName(start[0].date)}]] and ${monthName(late[late.length - 1].date)}`;
  const fall = Math.round((mean(startValues) - lateLevel) * 10) / 10;
  let text = fall >= 0.1 ? `${name} pass: HH fell ${fall.toFixed(1)} dB ${span}` : `${name} pass: HH did not fall ${span}`;
  const after = passes.find((p) => p.date > rule.lastDry);
  if (after && after.hh !== null) {
    const rise = Math.round((after.hh - lateLevel) * 10) / 10;
    const day = `${parseDay(after.date).getUTCDate()} ${monthName(after.date)}`;
    text += rise >= 0.1 ? `, then rose ${rise.toFixed(1)} dB on the first pass [[${rule.lastDryKey}|after the rain]] (${day})` : `, and had not risen on the first pass [[${rule.lastDryKey}|after the rain]] (${day})`;
  }
  return `${text}.`;
}

/** Extra pieces of the place card, supplied by chart/actions.ts. */
export interface PlaceParts {
  /** Built for each place and shown between the heading and the chart. */
  actions?: (lon: number, lat: number) => HTMLElement;
  /** One element shown at the bottom of the panel, with or without a place. */
  footer?: HTMLElement;
}

/** Draws the chart in `root` whenever the map is clicked. `onOpen` runs when a place is picked. */
export function createPlaceChart(root: HTMLElement, map: MapLibreMap, overlays: Overlays, onOpen: () => void): PlaceChart {
  return new PlaceChart(root, map, overlays, onOpen);
}

export class PlaceChart {
  private sites: Promise<Site[]> | undefined;
  private marker: Marker | undefined;
  private request = 0;
  private drawn: (() => void) | undefined;
  private pickListeners: (() => void)[] = [];
  private parts: PlaceParts = {};
  private rules: Promise<Record<string, NumberEntry> | null> | undefined;
  /** The place on show, or null. Read by the link to this view. */
  place: { lon: number; lat: number } | null = null;

  constructor(
    private root: HTMLElement,
    private map: MapLibreMap,
    private overlays: Overlays,
    private onOpen: () => void,
  ) {
    this.hint();
    map.on("click", (event) => void this.pick(event.lngLat.lng, event.lngLat.lat));
    overlays.onChange(() => this.drawn?.());
  }

  private hint(): void {
    this.root.classList.remove("has-data");
    this.root.replaceChildren(
      h("h2", { text: "Place" }),
      h("p", { class: "note", text: "Click the map to see how the radar signal changed at that place over the season." }),
      ...(this.parts.footer ? [this.parts.footer] : []),
    );
  }

  setParts(parts: PlaceParts): void {
    this.parts = parts;
    if (!this.place) this.hint();
  }

  /** Calls `fn` whenever a place is picked or the card is closed. */
  onPick(fn: () => void): void {
    this.pickListeners.push(fn);
  }

  private setPlace(place: { lon: number; lat: number } | null): void {
    this.place = place;
    for (const fn of this.pickListeners) fn();
  }

  /** Closes the place card and takes its marker off the map. */
  close(): void {
    this.marker?.remove();
    this.marker = undefined;
    this.drawn = undefined;
    this.request += 1;
    this.hint();
    this.setPlace(null);
  }

  private loadSites(): Promise<Site[]> {
    this.sites ??= (async () => {
      const index = await fetchJson<Record<string, SiteFiles>>("series/index.json");
      const out: Site[] = [];
      for (const files of Object.values(index ?? {})) {
        const meta = await fetchJson<SeriesMeta>(files.series);
        if (meta && Array.isArray(meta.bands) && Array.isArray(meta.bounds)) out.push({ meta, files });
      }
      return out;
    })();
    return this.sites;
  }

  private static cell(meta: SeriesMeta, lon: number, lat: number): number | null {
    const [west, , , north] = meta.bounds;
    const col = Math.floor((lon - west) / meta.cell_deg);
    const row = Math.floor((north - lat) / meta.cell_deg);
    return col >= 0 && col < meta.cols && row >= 0 && row < meta.rows ? row * meta.cols + col : null;
  }

  private static passes(meta: SeriesMeta, bin: Uint8Array, cell: number): Pass[] {
    const byKey = new Map<string, Pass>();
    meta.bands.forEach((band, k) => {
      const byte = bin[k * meta.rows * meta.cols + cell];
      const value = byte === undefined || byte === meta.nodata ? null : byte * meta.scale + meta.offset;
      const key = `${band.date}|${band.track}`;
      const pass = byKey.get(key) ?? { date: band.date, track: band.track, hh: null, hv: null };
      if (band.pol === "hh") pass.hh = value;
      if (band.pol === "hv") pass.hv = value;
      byKey.set(key, pass);
    });
    return [...byKey.values()].sort((a, b) => a.date.localeCompare(b.date));
  }

  /** Shows the chart for a place, as a click on the map does. */
  async pick(lon: number, lat: number): Promise<void> {
    const request = (this.request += 1);
    this.root.scrollTop = 0;
    this.setPlace({ lon, lat });
    this.marker ??= new Marker({ element: h("div", { class: "place-marker" }) });
    this.marker.setLngLat([lon, lat]).addTo(this.map);
    const where = `${Math.abs(lat).toFixed(3)} ${lat < 0 ? "S" : "N"}, ${Math.abs(lon).toFixed(3)} ${lon < 0 ? "W" : "E"}`;
    const closeButton = h("button", { type: "button", class: "text-button small", text: "Close" });
    closeButton.addEventListener("click", () => this.close());
    const body = h("div", { class: "place-body" }, h("p", { class: "note", text: "Loading the radar series." }));
    this.drawn = undefined;
    this.root.classList.add("has-data");
    this.root.replaceChildren(h("div", { class: "panel-head" }, h("h2", { text: "Place" }), h("span", { class: "where", text: where }), closeButton),
      ...(this.parts.actions ? [this.parts.actions(lon, lat)] : []),
      body,
      ...(this.parts.footer ? [this.parts.footer] : []),
    );
    this.onOpen();

    const sites = await this.loadSites();
    if (request !== this.request) return;
    if (!sites.length) {
      body.replaceChildren(h("p", { class: "note", text: "The radar series is not loaded yet, so there is no chart." }));
      return;
    }
    let passes: Pass[] = [];
    let site: Site | undefined;
    let cellIndex = -1;
    for (const candidate of sites) {
      const cell = PlaceChart.cell(candidate.meta, lon, lat);
      if (cell === null) continue;
      candidate.bin ??= fetch(asset(candidate.files.bin))
        .then((res) => (res.ok ? res.arrayBuffer() : null))
        .then((buffer) => (buffer ? new Uint8Array(buffer) : null))
        .catch(() => null);
      const bin = await candidate.bin;
      if (request !== this.request) return;
      if (!bin) continue;
      const found = PlaceChart.passes(candidate.meta, bin, cell);
      if (found.some((p) => p.hh !== null || p.hv !== null)) {
        passes = found;
        site = candidate;
        cellIndex = cell;
        break;
      }
    }
    if (!site) {
      body.replaceChildren(h("p", { class: "note", text: "There is no radar series at this place. Click inside the study area." }));
      return;
    }
    let rain: Record<string, number> | null = null;
    if (site.files.rain) {
      site.rain ??= fetchJson<Record<string, number>>(site.files.rain);
      rain = await site.rain;
      if (request !== this.request) return;
    }
    // Fire dates exist only once track 3 has exported them. null means "not loaded", [] means "none here".
    let fires: string[] | null = null;
    if (site.files.fires) {
      site.fires ??= fetchJson<Record<string, string[]>>(site.files.fires);
      const byCell = await site.fires;
      if (request !== this.request) return;
      if (byCell) fires = [...(byCell[String(cellIndex)] ?? [])].sort();
    }
    // The dry start and the last dry day of this site, from the numbers file.
    this.rules ??= fetchJson<Record<string, NumberEntry>>("validation.json");
    const numbers = await this.rules;
    if (request !== this.request) return;
    const startKey = `start_passes_from_${site.meta.site}`;
    const lastDryKey = `last_dry_day_${site.meta.site}`;
    const startFrom = numbers?.[startKey]?.value;
    const lastDry = numbers?.[lastDryKey]?.value;
    const isDay = (value: unknown): value is string => typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);
    const rule = numbers && isDay(startFrom) && isDay(lastDry) ? { startFrom, lastDry, startKey, lastDryKey, numbers } : null;
    this.draw(body, passes, [...new Set(site.meta.bands.map((b) => b.track))], rain, fires, rule);
  }

  private draw(body: HTMLElement, passes: Pass[], tracks: string[], rain: Record<string, number> | null, fires: string[] | null, rule: SeasonRule | null): void {
    const orbitOf = (track: string): string => this.overlays.layers.find((l) => l.track === track && l.orbit)?.orbit ?? `track ${track}`;
    const color = (track: string): string => TRACK_COLORS[tracks.indexOf(track) % TRACK_COLORS.length];

    // Without the season dates there is no agreed start to measure from, so no sentence is made up.
    const lines = rule ? tracks.map((t) => reading(passes.filter((p) => p.track === t), orbitOf(t), rule)).filter((t): t is string => Boolean(t)) : [];
    // A place that burned brightens for a different reason than a place that got wet again,
    // so the fire days are said next to the reading, not only drawn under the chart.
    if (fires?.length) {
      const span = fires.length === 1 ? `on ${formatDay(fires[0])}` : `on ${fires.length} days, ${formatDay(fires[0])} to ${formatDay(fires[fires.length - 1])}`;
      lines.push(`Fire was detected here ${span}.`);
    }
    // The two phrases that rest on a date from validation.json become chips; the rest is plain text.
    const readingBox = h("div", { class: "reading" }, ...lines.map((t) => h("p", {}, withChips(t, rule?.numbers ?? {}))));

    const legend = h("div", { class: "chart-legend" });
    for (const t of tracks) {
      const key = h("span", { class: "line-key" });
      key.style.background = color(t);
      const name = orbitOf(t);
      legend.append(h("span", { class: "legend-item" }, key, `${name.charAt(0).toUpperCase()}${name.slice(1)} pass, track ${t}`));
    }

    // Shared time axis; one panel per polarisation, both with the same span in decibels.
    const t0 = parseDay(passes[0].date).getTime();
    const t1 = parseDay(passes[passes.length - 1].date).getTime();
    const x = (iso: string): number => LEFT + ((parseDay(iso).getTime() - t0) / Math.max(1, t1 - t0)) * (W - LEFT - RIGHT);
    const pols = (["hh", "hv"] as const).filter((pol) => passes.some((p) => p[pol] !== null));
    const ranges = pols.map((pol) => {
      const values = passes.map((p) => p[pol]).filter((v): v is number => v !== null);
      return [Math.min(...values), Math.max(...values)];
    });
    const span = Math.max(2, ...ranges.map(([lo, hi]) => Math.ceil((hi - lo) * 1.15)));
    const rows = pols.length + (fires ? 1 : 0) + (rain ? 1 : 0);
    const height = TOP + pols.length * PANEL_H + (fires ? FIRE_H : 0) + (rain ? RAIN_H : 0) + (rows - 1) * PANEL_GAP + AXIS_H;
    const fireTop = TOP + pols.length * (PANEL_H + PANEL_GAP);
    const rainTop = fireTop + (fires ? FIRE_H + PANEL_GAP : 0);
    const fireDays = (fires ?? []).filter((day) => parseDay(day).getTime() >= t0 && parseDay(day).getTime() <= t1);
    const chart = svg("svg", { viewBox: `0 0 ${W} ${height}`, class: "chart", role: "img", tabindex: 0, "aria-label": "HH and HV backscatter over the season at the clicked place, for both orbits. Use the arrow keys to read single passes." });

    const months: string[] = [];
    for (let d = new Date(Date.UTC(new Date(t0).getUTCFullYear(), new Date(t0).getUTCMonth() + 1, 1)); d.getTime() <= t1; d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1))) {
      months.push(d.toISOString().slice(0, 10));
    }
    const panelTop = (k: number): number => TOP + k * (PANEL_H + PANEL_GAP);
    const scales: ((v: number) => number)[] = [];
    pols.forEach((pol, k) => {
      const top = panelTop(k);
      const mid = (ranges[k][0] + ranges[k][1]) / 2;
      const lo = Math.round(mid - span / 2);
      const y = (v: number): number => top + PANEL_H - ((v - lo) / span) * PANEL_H;
      scales.push(y);
      chart.append(svg("text", { x: 0, y: top - 6, class: "chart-title" }, `${pol.toUpperCase()} brightness, dB`));
      for (const tick of [lo, lo + span / 2, lo + span]) {
        chart.append(svg("line", { x1: LEFT, x2: W - RIGHT, y1: y(tick), y2: y(tick), class: "grid" }));
        chart.append(svg("text", { x: LEFT - 6, y: y(tick) + 4, class: "tick", "text-anchor": "end" }, String(Math.round(tick * 10) / 10)));
      }
      for (const m of months) {
        chart.append(svg("line", { x1: x(m), x2: x(m), y1: top + PANEL_H, y2: top + PANEL_H + 4, class: "grid" }));
      }
      for (const t of tracks) {
        const pts = passes.filter((p) => p.track === t);
        let path = "";
        let pen = false;
        for (const p of pts) {
          const v = p[pol];
          if (v === null) {
            pen = false; // a pass without data breaks the line
            continue;
          }
          path += `${pen ? "L" : "M"}${x(p.date).toFixed(1)},${y(v).toFixed(1)}`;
          pen = true;
        }
        chart.append(svg("path", { d: path, fill: "none", stroke: color(t), "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));
        for (const p of pts) {
          const v = p[pol];
          if (v !== null) chart.append(svg("circle", { cx: x(p.date), cy: y(v), r: 4, fill: color(t), class: "dot" }));
        }
      }
    });

    if (fires) {
      chart.append(svg("text", { x: 0, y: fireTop - 6, class: "chart-title" }, fireDays.length ? "Days with a fire detection here" : "No fire detection here this season"));
      chart.append(svg("line", { x1: LEFT, x2: W - RIGHT, y1: fireTop + FIRE_H, y2: fireTop + FIRE_H, class: "grid" }));
      for (const day of fireDays) {
        chart.append(svg("rect", { x: x(day) - 1.5, y: fireTop, width: 3, height: FIRE_H, class: "fire" }));
      }
    }

    if (rain) {
      const top = rainTop;
      const days = Object.entries(rain).filter(([day]) => parseDay(day).getTime() >= t0 && parseDay(day).getTime() <= t1);
      const most = Math.max(1, ...days.map(([, mm]) => mm));
      chart.append(svg("text", { x: 0, y: top - 6, class: "chart-title" }, "Rain over the whole study box, mm per day"));
      chart.append(svg("line", { x1: LEFT, x2: W - RIGHT, y1: top + RAIN_H, y2: top + RAIN_H, class: "grid" }));
      chart.append(svg("text", { x: LEFT - 6, y: top + 8, class: "tick", "text-anchor": "end" }, String(Math.round(most))));
      for (const [day, mm] of days) {
        if (mm > 0) chart.append(svg("line", { x1: x(day), x2: x(day), y1: top + RAIN_H, y2: top + RAIN_H - (mm / most) * RAIN_H, class: "rain" }));
      }
    }

    // One time axis for all panels: the month names sit under the last one.
    for (const m of months) {
      chart.append(svg("text", { x: x(m), y: height - 4, class: "tick", "text-anchor": "middle" }, monthName(m).slice(0, 3)));
    }

    // The two dates the reading is measured between, so the sentence can be checked by eye.
    if (rule) {
      const marks: [string, string][] = [
        [rule.startFrom, "dry start"],
        [new Date(parseDay(rule.lastDry).getTime() + 86_400_000).toISOString().slice(0, 10), "rain"],
      ];
      for (const [day, label] of marks) {
        const at = parseDay(day).getTime();
        if (at < t0 || at > t1) continue;
        chart.append(svg("line", { x1: x(day), x2: x(day), y1: TOP, y2: panelTop(pols.length - 1) + PANEL_H, class: "season-mark" }));
        chart.append(svg("text", { x: x(day) + 3, y: TOP + 9, class: "season-mark-label" }, label));
      }
    }

    // Reading single passes: a hairline that snaps to the nearest pass, by pointer or arrow keys.
    const bottom = panelTop(pols.length - 1) + PANEL_H;
    const sliderLine = svg("line", { y1: TOP, y2: bottom, class: "slider-line" });
    const hair = svg("line", { y1: TOP, y2: bottom, class: "hair" });
    const rings = pols.map(() => svg("circle", { r: 6, class: "ring" }));
    chart.append(sliderLine, hair, ...rings);
    const readout = h("p", { class: "readout", "aria-live": "polite" });
    let focus = -1;
    const show = (index: number): void => {
      focus = index;
      const p = passes[index];
      hair.style.display = p ? "" : "none";
      rings.forEach((ring, k) => {
        const v = p ? p[pols[k]] : null;
        ring.style.display = v === null ? "none" : "";
        if (p && v !== null) {
          ring.setAttribute("cx", String(x(p.date)));
          ring.setAttribute("cy", String(scales[k](v)));
          ring.setAttribute("stroke", color(p.track));
        }
      });
      if (!p) {
        readout.textContent = "Point at the chart, or use the arrow keys, to read a single pass.";
        return;
      }
      hair.setAttribute("x1", String(x(p.date)));
      hair.setAttribute("x2", String(x(p.date)));
      const values = pols.map((pol) => `${pol.toUpperCase()} ${p[pol] === null ? "no data" : db(p[pol] as number)}`).join(", ");
      const burning = fireDays.includes(p.date) ? ". A fire was detected here that day" : "";
      readout.replaceChildren(h("strong", { text: values }), ` on ${formatDay(p.date)}, ${orbitOf(p.track)} pass${burning}`);
    };
    const nearest = (clientX: number): number => {
      const box = chart.getBoundingClientRect();
      const at = ((clientX - box.left) / box.width) * W;
      let best = 0;
      passes.forEach((p, k) => {
        if (Math.abs(x(p.date) - at) < Math.abs(x(passes[best].date) - at)) best = k;
      });
      return best;
    };
    chart.addEventListener("pointermove", (event) => show(nearest(event.clientX)));
    chart.addEventListener("pointerdown", (event) => show(nearest(event.clientX)));
    chart.addEventListener("pointerleave", (event) => {
      if (event.pointerType === "mouse") show(-1);
    });
    chart.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      const move = event.key === "ArrowRight" ? 1 : -1;
      show(Math.min(passes.length - 1, Math.max(0, focus < 0 ? (move > 0 ? 0 : passes.length - 1) : focus + move)));
    });
    show(-1);

    // The pass the season slider is on, when the map is stepping through passes.
    this.drawn = (): void => {
      const step = this.overlays.step;
      sliderLine.style.display = step ? "" : "none";
      if (step) {
        const at = Math.min(W - RIGHT, Math.max(LEFT, x(step.date)));
        sliderLine.setAttribute("x1", String(at));
        sliderLine.setAttribute("x2", String(at));
      }
    };
    this.drawn();

    const tableRows = passes.map((p) =>
      h("tr", {}, h("td", { text: formatDay(p.date) }), h("td", { text: orbitOf(p.track) }), ...pols.map((pol) => h("td", { class: "num", text: p[pol] === null ? "" : (p[pol] as number).toFixed(1) }))),
    );
    const table = h(
      "details",
      { class: "chart-table" },
      h("summary", { text: "Show the values as a table" }),
      h("table", {}, h("thead", {}, h("tr", {}, h("th", { text: "Pass" }), h("th", { text: "Orbit" }), ...pols.map((pol) => h("th", { class: "num", text: `${pol.toUpperCase()}, dB` })))), h("tbody", {}, ...tableRows)),
    );

    body.replaceChildren(
      readingBox,
      legend,
      chart,
      readout,
      table,
      h("p", { class: "note", text: "Brightness is the average of the cell you clicked, with the scene-wide shift of each pass removed. It shows change in the radar signal, not a water level." }),
    );
  }
}
