// Written with Super Intelligence (SI) assistance.
// "How it was measured": the method of the season view, drawn beside the map and tied to the
// slider. One chart on a shared time axis shows the radar echo on open peat that fell (the two
// orbits as two lines) against closed forest, the fire building up, and the daily rain with the
// dry season marked. A line follows the pass on show, and a sentence says what part that pass
// plays in the measurement. The curves are measurements (season/season.json, written by
// app/scripts/make_season_data.py); nothing here is typed by hand.
import { fetchJson, formatDay, parseDay } from "./data";
import { h } from "./dom";
import type { Overlays } from "./overlays";

type Role = "before" | "start" | "between" | "late" | "after";

interface SeasonPass {
  date: string;
  track: string;
  orbit: string;
  role: Role;
  open: number;
  forest: number;
}

interface SeasonData {
  start: string;
  end: string;
  dry: { first: string; last: string; start_from: string };
  fell_km2: number;
  forest_km2: number;
  passes: SeasonPass[];
  rain: number[];
  fire_km2: number[];
  sources: string;
}

const SVG = "http://www.w3.org/2000/svg";
const W = 320;
const LEFT = 30;
const RIGHT = 8;
const ECHO = { top: 16, height: 118 };
const FIRE = { top: 158, height: 44 };
const RAIN = { top: 226, height: 40 };
const H = 290;
const OPEN_COLOR = "#e0bd7c";
const FOREST_COLOR = "#7fc8a0";
const FIRE_COLOR = "#de3626";
const RAIN_COLOR = "#5aa7e8";

const ROLE_TEXT: Record<Role, string> = {
  before: "Before the dry start. Rain was still falling, so this pass is not used as the starting level.",
  start: "A start pass. The start passes of each orbit set the level every later pass is compared with.",
  between: "Compared with the start, after taking away what closed forest did on the same day. The dawn and dusk orbits look from opposite sides and should agree.",
  late: "One of the last two dry passes of its orbit. Their mean, minus the start, is the fall the map shows, kept only where both orbits agree.",
  after: "The first pass after the rain returned. What rose again and what did not decides the levels in Where to check.",
};

function svg<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number> = {}, text?: string): SVGElementTagNameMap[K] {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  if (text !== undefined) el.textContent = text;
  return el;
}

const signed = (value: number): string => `${value > 0 ? "+" : value < 0 ? "−" : ""}${Math.abs(value).toFixed(1)}`;

/** Builds the panel into `root`. It stays empty if the measurements file is missing. */
export async function buildMeasure(root: HTMLElement, overlays: Overlays): Promise<void> {
  const data = await fetchJson<SeasonData>("season/season.json");
  if (!data?.passes?.length) {
    root.hidden = true;
    return;
  }
  const t0 = parseDay(data.start).getTime();
  const t1 = parseDay(data.end).getTime();
  const x = (iso: string): number => LEFT + ((parseDay(iso).getTime() - t0) / (t1 - t0)) * (W - LEFT - RIGHT);
  const xDay = (k: number): number => LEFT + (k / (data.rain.length - 1)) * (W - LEFT - RIGHT);
  const low = Math.min(-1, ...data.passes.map((p) => p.open));
  const high = Math.max(0.5, ...data.passes.map((p) => p.open));
  const yEcho = (db: number): number => ECHO.top + ((high - db) / (high - low)) * ECHO.height;
  const fireMax = Math.max(1, ...data.fire_km2);
  const rainMax = Math.max(1, ...data.rain);

  const chart = svg("svg", { class: "measure-chart", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "The season as it was measured: the radar echo on open peat and on closed forest, fire so far, and daily rain" });
  const text = (xAt: number, yAt: number, words: string, cls = "m-label", anchor = "start"): SVGTextElement => svg("text", { x: xAt, y: yAt, class: cls, "text-anchor": anchor }, words);

  // The dry season by the rainfall rule, as a band through all three rows.
  chart.append(svg("rect", { x: x(data.dry.first), y: ECHO.top, width: x(data.dry.last) - x(data.dry.first), height: RAIN.top + RAIN.height - ECHO.top, class: "m-dry" }));

  // Row 1: the radar echo against the dry start.
  for (const db of [0, -1]) {
    chart.append(svg("line", { x1: LEFT, x2: W - RIGHT, y1: yEcho(db), y2: yEcho(db), class: "m-grid" }));
    chart.append(text(LEFT - 5, yEcho(db) + 3.5, db === 0 ? "0" : "−1", "m-tick", "end"));
  }
  chart.append(text(LEFT, ECHO.top - 5, "Radar echo against the dry start, dB", "m-title"));
  const forestLine = data.passes.filter((p) => p.orbit === "dawn").map((p, i) => `${i ? "L" : "M"}${x(p.date).toFixed(1)} ${yEcho(p.forest).toFixed(1)}`).join("");
  chart.append(svg("path", { d: forestLine, class: "m-line", stroke: FOREST_COLOR }));
  for (const orbit of ["dawn", "dusk"]) {
    const line = data.passes.filter((p) => p.orbit === orbit).map((p, i) => `${i ? "L" : "M"}${x(p.date).toFixed(1)} ${yEcho(p.open).toFixed(1)}`).join("");
    chart.append(svg("path", { d: line, class: `m-line${orbit === "dusk" ? " is-dusk" : ""}`, stroke: OPEN_COLOR }));
  }
  // Labels sit where the lines leave room: the forest's over the middle of the season, the
  // open peat's in the lower left, under the part of the curve that has not yet fallen.
  chart.append(text(x(data.dry.first) + 64, yEcho(0) - 5, "closed forest, the yardstick", "m-note is-forest"));
  chart.append(text(LEFT + 4, yEcho(low) - 4, "open peat that fell", "m-note is-open"));

  // Row 2: fire so far.
  chart.append(text(LEFT, FIRE.top - 5, "Fire detected on peat so far", "m-title"));
  const yFire = (km2: number): number => FIRE.top + FIRE.height - (km2 / fireMax) * FIRE.height;
  chart.append(svg("path", { d: `M${LEFT} ${FIRE.top + FIRE.height}` + data.fire_km2.map((v, k) => `L${xDay(k).toFixed(1)} ${yFire(v).toFixed(1)}`).join("") + `L${W - RIGHT} ${FIRE.top + FIRE.height}Z`, class: "m-area", fill: FIRE_COLOR }));
  chart.append(text(W - RIGHT, FIRE.top - 5, `${Math.round(fireMax).toLocaleString("en")} km\u00b2 by November`, "m-tick", "end"));

  // Row 3: daily rain.
  chart.append(text(LEFT, RAIN.top - 5, "Rain, mm a day", "m-title"));
  const bar = (W - LEFT - RIGHT) / data.rain.length;
  for (const [k, mm] of data.rain.entries()) {
    if (mm <= 0) continue;
    const tall = (mm / rainMax) * RAIN.height;
    chart.append(svg("rect", { x: (xDay(k) - bar / 2).toFixed(1), y: (RAIN.top + RAIN.height - tall).toFixed(1), width: Math.max(bar * 0.8, 0.8).toFixed(2), height: tall.toFixed(1), fill: RAIN_COLOR }));
  }
  chart.append(text(x(data.dry.first) + 3, RAIN.top + 9, "dry season", "m-note"));

  // Months along the bottom.
  const month = new Date(t0);
  month.setUTCDate(1);
  for (month.setUTCMonth(month.getUTCMonth() + 1); month.getTime() < t1; month.setUTCMonth(month.getUTCMonth() + 1)) {
    const iso = month.toISOString().slice(0, 10);
    chart.append(svg("line", { x1: x(iso), x2: x(iso), y1: RAIN.top + RAIN.height, y2: RAIN.top + RAIN.height + 4, class: "m-grid" }));
    chart.append(text(x(iso) + 3, RAIN.top + RAIN.height + 14, month.toLocaleString("en", { month: "short", timeZone: "UTC" }), "m-tick"));
  }

  // The line that follows the pass on show.
  const head = svg("line", { y1: ECHO.top, y2: RAIN.top + RAIN.height, class: "m-head" });
  chart.append(head);

  // One point per pass: its shape says what part it plays, and a click goes to that pass.
  const points = data.passes.map((p) => {
    const strong = p.role === "start" || p.role === "late";
    const dot = svg("circle", { cx: x(p.date), cy: yEcho(p.open), r: strong ? 4 : 3, class: `m-point is-${p.role}`, tabindex: 0, role: "button", "aria-label": `${formatDay(p.date)}, ${p.orbit} pass: ${signed(p.open)} dB. Show this pass.` });
    dot.append(svg("title", {}, `${formatDay(p.date)}, ${p.orbit} pass`));
    const go = (): void => {
      const index = overlays.steps.findIndex((s) => s.date === p.date && s.track === p.track);
      if (index >= 0) overlays.setStep(index);
    };
    dot.addEventListener("click", go);
    dot.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        go();
      }
    });
    chart.append(dot);
    return dot;
  });

  const now = h("p", { class: "measure-now", "aria-live": "polite" });
  const role = h("p", { class: "measure-role" });
  const key = h(
    "div",
    { class: "measure-key" },
    h("span", {}, h("i", { class: "m-key-dot is-strong" }), "start and late passes"),
    h("span", {}, h("i", { class: "m-key-line" }), "dawn"),
    h("span", {}, h("i", { class: "m-key-line is-dusk" }), "dusk"),
  );
  root.replaceChildren(
    h("div", { class: "panel-head" }, h("h2", { text: "How it was measured" })),
    chart,
    key,
    now,
    role,
    h("p", { class: "note", text: `Medians over ${data.fell_km2.toLocaleString("en")} km² of western peat that fell on both orbits, and ${data.forest_km2.toLocaleString("en")} km² of closed forest. Forest is zero by construction: every pass is shifted so that it holds still.` }),
  );

  const render = (): void => {
    const step = overlays.step;
    const at = step ? data.passes.findIndex((p) => p.date === step.date && p.track === step.track) : -1;
    points.forEach((dot, k) => dot.classList.toggle("is-now", k === at));
    if (at < 0) {
      head.style.display = "none"; // not the visibility attribute: that would show through a hidden panel
      now.textContent = "The whole season. The fall on the map is the late passes minus the start passes.";
      role.textContent = "Press play, drag the slider or click a point to follow the measurement pass by pass.";
      return;
    }
    const p = data.passes[at];
    head.style.display = "";
    head.setAttribute("x1", String(x(p.date)));
    head.setAttribute("x2", String(x(p.date)));
    const day = Math.round((parseDay(p.date).getTime() - t0) / 86_400_000);
    const burnt = data.fire_km2[Math.max(0, Math.min(data.fire_km2.length - 1, day))];
    now.textContent = `${formatDay(p.date)}, ${p.orbit} orbit. Open peat that fell: ${signed(p.open)} dB. Closed forest: ${signed(p.forest)} dB. Fire so far: ${Math.round(burnt).toLocaleString("en")} km².`;
    role.textContent = ROLE_TEXT[p.role];
  };
  overlays.onChange(render);
  render();
}
