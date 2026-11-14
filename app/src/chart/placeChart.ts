// Written with Super Intelligence (SI) assistance.
// The click-a-place chart: HH and HV over the season for both orbits, with daily rain
// and fire dates under it. Plain DOM and SVG, no chart library.
//
// Wiring it to the map takes three lines:
//
//   import { createPlaceChart } from "./chart/placeChart";
//   const chart = createPlaceChart(panelElement, { base: import.meta.env.BASE_URL, sites: ["west", "east"] });
//   map.on("click", (e) => chart.show(e.lngLat.lng, e.lngLat.lat));

import "./placeChart.css";
import { PlaceData, type Line, type Place } from "./data";

export interface PlaceChartOptions {
  base: string; // site root with a trailing slash, for example import.meta.env.BASE_URL
  sites: string[]; // for example ["west", "east"]
  onClose?: () => void;
}

export interface PlaceChart {
  /** Draws the chart for a point. Resolves to false when the point is outside every site. */
  show(lon: number, lat: number): Promise<boolean>;
  hide(): void;
  /** True when a time series file was found. Use it to decide whether to offer the chart at all. */
  available(): Promise<boolean>;
}

const DAY = 86_400_000;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const ORBIT: Record<string, string> = { "125": "dawn", "010": "dawn", "061": "dusk", "119": "dusk" };

const day = (date: string) => Date.parse(`${date}T00:00:00Z`);
const shortDate = (date: string) => `${Number(date.slice(8, 10))} ${MONTHS[Number(date.slice(5, 7)) - 1]}`;
const signed = (value: number, digits = 1) => value.toFixed(digits).replace("-", "−");
const escapeHtml = (text: string) =>
  text.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

function coordinates(lon: number, lat: number): string {
  return `${Math.abs(lat).toFixed(3)}° ${lat < 0 ? "S" : "N"}, ${Math.abs(lon).toFixed(3)}° ${lon < 0 ? "W" : "E"}`;
}

function lineName(line: Line): string {
  const orbit = ORBIT[line.track];
  return `${line.pol.toUpperCase()}, track ${line.track}${orbit ? ` (${orbit})` : ""}`;
}

/** Tick values that cover lo to hi with a step of 1, 2 or 5 dB. */
function ticks(lo: number, hi: number, most: number): number[] {
  const step = [1, 2, 5, 10, 20].find((s) => (hi - lo) / s <= most) ?? 50;
  const out: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(v);
  return out;
}

export function createPlaceChart(root: HTMLElement, options: PlaceChartOptions): PlaceChart {
  const data = new PlaceData(options.base, options.sites);
  root.classList.add("pc");
  root.hidden = true;
  root.innerHTML = `
    <div class="pc-head">
      <div><div class="pc-title"></div><div class="pc-sub"></div></div>
      <button class="pc-close" type="button" aria-label="Close the chart">×</button>
    </div>
    <div class="pc-body"></div>`;
  const title = root.querySelector<HTMLElement>(".pc-title")!;
  const sub = root.querySelector<HTMLElement>(".pc-sub")!;
  const body = root.querySelector<HTMLElement>(".pc-body")!;
  let current: Place | null = null;
  let request = 0;

  const hide = () => {
    request++;
    current = null;
    root.hidden = true;
    options.onClose?.();
  };
  root.querySelector(".pc-close")!.addEventListener("click", hide);

  // Redraw at the real width so the text keeps its size on a phone.
  let drawnWidth = 0;
  new ResizeObserver(() => {
    if (current && Math.abs(body.clientWidth - drawnWidth) > 4) draw(current);
  }).observe(body);

  function message(text: string) {
    body.innerHTML = `<p class="pc-note">${escapeHtml(text)}</p>`;
  }

  function draw(place: Place) {
    drawnWidth = body.clientWidth;
    const points = place.lines.flatMap((line) => line.points);
    if (points.length === 0) {
      message("No radar data at this place.");
      return;
    }
    const width = Math.max(260, drawnWidth);
    const left = 34, right = 8;
    const top = 8, radarH = 150, fireH = 16, rainH = 56, gap = 6, axisH = 18;
    const fireY = top + radarH + gap;
    const rainY = fireY + fireH + gap;
    const height = rainY + rainH + axisH;

    const t0 = day(place.season[0]) - 4 * DAY;
    const t1 = day(place.season[1]) + 4 * DAY;
    const x = (ms: number) => left + ((ms - t0) / (t1 - t0)) * (width - left - right);
    const dbs = points.map((p) => p.db);
    const lo = Math.floor(Math.min(...dbs) - 0.5), hi = Math.ceil(Math.max(...dbs) + 0.5);
    const y = (db: number) => top + ((hi - db) / (hi - lo)) * radarH;
    const rain = place.rain.filter((r) => day(r.date) >= t0 && day(r.date) <= t1);
    const rainMax = Math.ceil(Math.max(10, ...rain.map((r) => r.mm)) / 10) * 10;
    const fires = place.fires.filter((d) => day(d) >= t0 && day(d) <= t1);

    let svg = `<svg class="pc-svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" role="img" aria-label="Radar brightness, rain and fire over the season at ${coordinates(place.lon, place.lat)}">`;
    // Month grid, shared by the three panels.
    const start = new Date(t0);
    for (let m = Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 1); m <= t1; ) {
      const d = new Date(m);
      svg += `<line class="pc-grid" x1="${x(m)}" x2="${x(m)}" y1="${top}" y2="${rainY + rainH}"/>`;
      if (x(m) < width - right - 14) svg += `<text class="pc-tick" x="${x(m) + 3}" y="${height - 5}">${MONTHS[d.getUTCMonth()]}</text>`;
      m = Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1);
    }
    for (const v of ticks(lo, hi, 5)) {
      svg += `<line class="pc-grid" x1="${left}" x2="${width - right}" y1="${y(v)}" y2="${y(v)}"/>`;
      svg += `<text class="pc-tick" x="${left - 4}" y="${y(v) + 3}" text-anchor="end">${signed(v, 0)}</text>`;
    }
    svg += `<text class="pc-axis" x="${left + 3}" y="${top + 9}">dB</text>`;
    for (const line of place.lines) {
      const cls = `pc-${line.pol} pc-t${place.lines.filter((l) => l.pol === line.pol).indexOf(line)}`;
      const path = line.points.map((p, i) => `${i ? "L" : "M"}${x(day(p.date)).toFixed(1)} ${y(p.db).toFixed(1)}`).join("");
      svg += `<path class="pc-line ${cls}" d="${path}"/>`;
      for (const p of line.points) svg += `<circle class="pc-dot ${cls}" cx="${x(day(p.date)).toFixed(1)}" cy="${y(p.db).toFixed(1)}" r="2.6"/>`;
    }
    // Fire dates.
    svg += `<text class="pc-axis" x="${left - 4}" y="${fireY + 11}" text-anchor="end">fire</text>`;
    svg += `<line class="pc-grid" x1="${left}" x2="${width - right}" y1="${fireY + fireH / 2}" y2="${fireY + fireH / 2}"/>`;
    for (const d of fires) svg += `<rect class="pc-fire" x="${(x(day(d)) - 1.5).toFixed(1)}" y="${fireY + 1}" width="3" height="${fireH - 2}"><title>Fire detected on ${shortDate(d)}</title></rect>`;
    // Daily rain.
    svg += `<text class="pc-tick" x="${left - 4}" y="${rainY + 9}" text-anchor="end">${Math.round(rainMax)}</text>`;
    svg += `<text class="pc-axis" x="${left + 3}" y="${rainY + 9}">mm of rain per day</text>`;
    svg += `<text class="pc-tick" x="${left - 4}" y="${rainY + rainH}" text-anchor="end">0</text>`;
    svg += `<line class="pc-base" x1="${left}" x2="${width - right}" y1="${rainY + rainH}" y2="${rainY + rainH}"/>`;
    const bar = Math.max(1, (width - left - right) / ((t1 - t0) / DAY) - 0.5);
    for (const r of rain) {
      const h = (r.mm / rainMax) * rainH;
      if (h > 0.2) svg += `<rect class="pc-rain" x="${(x(day(r.date)) - bar / 2).toFixed(1)}" y="${(rainY + rainH - h).toFixed(1)}" width="${bar.toFixed(1)}" height="${h.toFixed(1)}"/>`;
    }
    svg += `<line class="pc-cursor" y1="${top}" y2="${rainY + rainH}" hidden/>`;
    svg += `<rect class="pc-hit" x="${left}" y="${top}" width="${width - left - right}" height="${rainY + rainH - top}"/></svg>`;

    const key = place.lines
      .map((line) => {
        const cls = `pc-${line.pol} pc-t${place.lines.filter((l) => l.pol === line.pol).indexOf(line)}`;
        return `<span class="pc-key"><svg width="22" height="8"><path class="pc-line ${cls}" d="M1 4H21"/><circle class="pc-dot ${cls}" cx="11" cy="4" r="2.6"/></svg>${escapeHtml(lineName(line))}</span>`;
      })
      .join("");
    const notes = [
      rain.length ? "" : "Rain data is not loaded yet.",
      fires.length ? "" : "No fire detection is recorded for this place.",
    ].filter(Boolean).join(" ");
    body.innerHTML = `<div class="pc-keys">${key}</div>${svg}<div class="pc-read" aria-live="polite"></div>` +
      `<p class="pc-note">Radar: backscatter averaged over about 250 m. Rain: daily mean over the whole study box, not this place. ${notes}</p>`;

    // Touch or hover: read the values of the nearest radar pass.
    const read = body.querySelector<HTMLElement>(".pc-read")!;
    const cursor = body.querySelector<SVGLineElement>(".pc-cursor")!;
    const svgEl = body.querySelector<SVGSVGElement>(".pc-svg")!;
    const passDates = [...new Set(points.map((p) => p.date))].sort();
    const rainOn = new Map(rain.map((r) => [r.date, r.mm]));
    const readAt = (clientX: number) => {
      const box = svgEl.getBoundingClientRect();
      const ms = t0 + ((clientX - box.left - left) / (width - left - right)) * (t1 - t0);
      const date = passDates.reduce((best, d) => (Math.abs(day(d) - ms) < Math.abs(day(best) - ms) ? d : best));
      cursor.setAttribute("x1", String(x(day(date))));
      cursor.setAttribute("x2", String(x(day(date))));
      cursor.removeAttribute("hidden");
      const parts = place.lines.flatMap((line) => {
        const p = line.points.find((q) => q.date === date);
        return p ? [`${line.pol.toUpperCase()} ${signed(p.db)} dB (track ${line.track})`] : [];
      });
      const mm = rainOn.get(date);
      if (mm !== undefined) parts.push(`rain ${mm.toFixed(1)} mm`);
      if (fires.includes(date)) parts.push("fire detected");
      read.textContent = `${shortDate(date)}: ${parts.join(", ")}`;
    };
    const hit = body.querySelector<SVGRectElement>(".pc-hit")!;
    hit.addEventListener("pointermove", (e) => readAt(e.clientX));
    hit.addEventListener("pointerdown", (e) => readAt(e.clientX));
    read.textContent = "Touch the chart to read a radar pass.";
  }

  return {
    available: () => data.available(),
    hide,
    async show(lon, lat) {
      const mine = ++request;
      let place: Place | null;
      try {
        place = await data.at(lon, lat);
      } catch (error) {
        if (mine !== request) return true;
        current = null;
        title.textContent = coordinates(lon, lat);
        sub.textContent = "";
        root.hidden = false;
        message("The time series could not be loaded. Check the connection and click again.");
        console.error(error);
        return true;
      }
      if (mine !== request) return true; // a newer click won
      if (!place) {
        if (!root.hidden) hide();
        return false;
      }
      current = place;
      title.textContent = coordinates(lon, lat);
      sub.textContent = `Radar brightness, ${shortDate(place.season[0])} to ${shortDate(place.season[1])} ${place.season[1].slice(0, 4)}`;
      root.hidden = false;
      draw(place);
      return true;
    },
  };
}
