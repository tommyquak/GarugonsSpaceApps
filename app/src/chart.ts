// Written with Super Intelligence (SI) assistance.
// Click a place: reads the time series of that cell (docs/DATA_CONTRACT.md section 4) and draws
// HH and HV over the season for both orbits, with a plain reading of what HH did.
import maplibregl, { type Map as MapLibreMap } from "maplibre-gl";
import { asset, fetchJson, formatDay, monthName, parseDay } from "./data";
import { h } from "./dom";
import type { Overlays } from "./overlays";

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
}

interface Site {
  meta: SeriesMeta;
  files: SiteFiles;
  bin?: Promise<Uint8Array | null>;
  rain?: Promise<Record<string, number> | null>;
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

// A plain sentence on HH for one orbit: start of the season against its lowest later level,
// each taken as the mean of two passes, and what the last pass did after that.
function reading(passes: Pass[], orbit: string): string | null {
  const v = passes.filter((p) => p.hh !== null).map((p) => ({ date: p.date, hh: p.hh as number }));
  if (v.length < 4) return null;
  const start = mean([v[0].hh, v[1].hh]);
  let low = Infinity;
  let lowAt = 3;
  for (let i = 3; i < v.length; i += 1) {
    const level = mean([v[i - 1].hh, v[i].hh]);
    if (level < low) {
      low = level;
      lowAt = i;
    }
  }
  const name = orbit.charAt(0).toUpperCase() + orbit.slice(1);
  const fall = Math.round((start - low) * 10) / 10;
  if (fall < 0.1) return `${name} pass: HH did not fall below its ${monthName(v[0].date)} level.`;
  let text = `${name} pass: HH fell ${fall.toFixed(1)} dB from ${monthName(v[0].date)} to ${monthName(v[lowAt].date)}`;
  const last = v[v.length - 1];
  const rise = Math.round((last.hh - low) * 10) / 10;
  if (lowAt < v.length - 1 && rise >= 0.1) text += `, then rose ${rise.toFixed(1)} dB by ${monthName(last.date)}`;
  return `${text}.`;
}

export class PlaceChart {
  private sites: Promise<Site[]> | undefined;
  private marker: maplibregl.Marker | undefined;
  private request = 0;
  private drawn: (() => void) | undefined;

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
    this.root.replaceChildren(h("h2", { text: "Place" }), h("p", { class: "note", text: "Click the map to see how the radar signal changed at that place over the season." }));
  }

  private close(): void {
    this.marker?.remove();
    this.marker = undefined;
    this.drawn = undefined;
    this.request += 1;
    this.hint();
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

  private async pick(lon: number, lat: number): Promise<void> {
    const request = (this.request += 1);
    this.marker ??= new maplibregl.Marker({ element: h("div", { class: "place-marker" }) });
    this.marker.setLngLat([lon, lat]).addTo(this.map);
    const where = `${Math.abs(lat).toFixed(3)} ${lat < 0 ? "S" : "N"}, ${Math.abs(lon).toFixed(3)} ${lon < 0 ? "W" : "E"}`;
    const closeButton = h("button", { type: "button", class: "text-button small", text: "Close" });
    closeButton.addEventListener("click", () => this.close());
    const body = h("div", { class: "place-body" }, h("p", { class: "note", text: "Loading the radar series." }));
    this.drawn = undefined;
    this.root.classList.add("has-data");
    this.root.replaceChildren(h("div", { class: "panel-head" }, h("h2", { text: "Place" }), h("span", { class: "where", text: where }), closeButton), body);
    this.onOpen();

    const sites = await this.loadSites();
    if (request !== this.request) return;
    if (!sites.length) {
      body.replaceChildren(h("p", { class: "note", text: "The radar series is not loaded yet, so there is no chart." }));
      return;
    }
    let passes: Pass[] = [];
    let site: Site | undefined;
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
    this.draw(body, passes, [...new Set(site.meta.bands.map((b) => b.track))], rain);
  }

  private draw(body: HTMLElement, passes: Pass[], tracks: string[], rain: Record<string, number> | null): void {
    const orbitOf = (track: string): string => this.overlays.layers.find((l) => l.track === track && l.orbit)?.orbit ?? `track ${track}`;
    const color = (track: string): string => TRACK_COLORS[tracks.indexOf(track) % TRACK_COLORS.length];

    const lines = tracks.map((t) => reading(passes.filter((p) => p.track === t), orbitOf(t))).filter((t): t is string => Boolean(t));
    const readingBox = h("div", { class: "reading" }, ...lines.map((t) => h("p", { text: t })));

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
    const rows = pols.length + (rain ? 1 : 0);
    const height = TOP + pols.length * PANEL_H + (rain ? RAIN_H : 0) + (rows - 1) * PANEL_GAP + AXIS_H;
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

    if (rain) {
      const top = panelTop(pols.length);
      const days = Object.entries(rain).filter(([day]) => parseDay(day).getTime() >= t0 && parseDay(day).getTime() <= t1);
      const most = Math.max(1, ...days.map(([, mm]) => mm));
      chart.append(svg("text", { x: 0, y: top - 6, class: "chart-title" }, "Rain, mm per day"));
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
      readout.replaceChildren(h("strong", { text: values }), ` on ${formatDay(p.date)}, ${orbitOf(p.track)} pass`);
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
