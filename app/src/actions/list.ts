// Written with Super Intelligence (SI) assistance.
// The ranked list: the blocks of one action, largest fall in HH first, with filters, a count and
// export as CSV and GeoJSON. Only the rows in view are in the page, so a long list stays smooth.
import { h } from "../dom";
import { where } from "../ontology/card";
import { formatValue } from "../ontology/model";
import { actionColor, CONFIDENCE_LEVELS, NO_ACTION } from "./colors";
import type { BlockFeature, BlockStore } from "./data";

const ROW_H = 54;
const SPARE_ROWS = 6;

export interface RankedList {
  /** Rebuilds the rows after blocks have arrived or the panel has opened. */
  refresh(): void;
  /** Marks the row of the selected block. */
  setSelected(id: string | null): void;
}

function download(name: string, type: string, text: string): void {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = h("a", { href: url, download: name });
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function cell(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "1" : "0";
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

// The columns of the pipeline's own blocks_<site>.csv, so an export opens the same way.
function toCsv(rows: BlockFeature[]): string {
  const first = rows[0]?.properties;
  const obs = Object.keys(first?.obs ?? {});
  const states = Object.keys(first?.states ?? {});
  const head = ["id", "action", "confidence", "rank", "lon", "lat", "fall_db", ...obs, ...states.map((s) => `is_${s}`)];
  const lines = rows.map(({ properties: p }) =>
    [p.id, p.action, p.confidence, p.rank, p.lon, p.lat, p.fall_db, ...obs.map((k) => p.obs[k]), ...states.map((k) => p.states[k])].map(cell).join(","),
  );
  return [head.join(","), ...lines].join("\n") + "\n";
}

function select(label: string, options: [string, string][]): { field: HTMLElement; input: HTMLSelectElement } {
  const input = h("select", { class: "act-select" }, ...options.map(([value, text]) => h("option", { value, text })));
  return { field: h("label", { class: "act-field" }, h("span", { text: label }), input), input };
}

/** `firstSite` is the site the list opens on: ranks count inside one site, so the list shows one site at a time. */
export function buildList(root: HTMLElement, store: BlockStore, firstSite: () => string, onPick: (id: string) => void): RankedList {
  const ontology = store.ontology;
  const actions = ontology.actions.filter((a) => a.id !== NO_ACTION);
  const canal = ontology.states.find((s) => s.id === "near_canal");

  const action = select("Class", actions.map((a) => [a.id, a.title]));
  const confidence = select("Agreement", [["", "Any"], ...CONFIDENCE_LEVELS.map((c): [string, string] => [c, c.charAt(0).toUpperCase() + c.slice(1)])]);
  const near = select(canal?.title ?? "Near a canal", [
    ["", "Any"],
    ["yes", "Yes"],
    ["no", "No"],
  ]);
  const site = select("Site", store.sites.map((s) => [s.id, s.id.charAt(0).toUpperCase() + s.id.slice(1)]));
  let sitePicked = false;
  // The list opens on "Fell, and still low after the rain", the class a field check is most for, when the data has it.
  if (actions.some((a) => a.id === "fell_still_low")) action.input.value = "fell_still_low";

  const count = h("p", { class: "act-count", "aria-live": "polite" });
  const csvButton = h("button", { type: "button", class: "text-button small", text: "Export CSV" });
  const geoButton = h("button", { type: "button", class: "text-button small", text: "Export GeoJSON" });
  const inner = h("div", { class: "act-rows-inner" });
  const viewport = h("div", { class: "act-rows", role: "group", "aria-label": "Ranked blocks" }, inner);
  root.replaceChildren(
    h("div", { class: "act-filters" }, action.field, confidence.field, near.field, site.field),
    h("div", { class: "act-count-row" }, count, csvButton, geoButton),
    viewport,
    h("p", { class: "note", text: "Fall is how far HH fell over the dry season, in dB. A bigger fall is not a grade of the land." }),
  );

  let rows: BlockFeature[] = [];
  let selected: string | null = null;
  let first = -1;
  let last = -1;

  const filter = (): void => {
    if (!sitePicked) site.input.value = firstSite();
    sitePicked = true;
    const here = site.input.value;
    rows = store.features(here).filter(({ properties: p }) => {
      if (p.action !== action.input.value) return false;
      if (confidence.input.value && p.confidence !== confidence.input.value) return false;
      if (near.input.value && (p.states.near_canal === true) !== (near.input.value === "yes")) return false;
      return true;
    });
    rows.sort((a, b) => (a.properties.rank ?? Infinity) - (b.properties.rank ?? Infinity));
    const waiting = !store.isLoaded(here);
    const title = actions.find((a) => a.id === action.input.value)?.title ?? "";
    count.textContent = waiting ? "Loading the blocks." : `${rows.length.toLocaleString("en")} ${rows.length === 1 ? "block" : "blocks"} in ${title}, ${here}`;
    csvButton.disabled = geoButton.disabled = rows.length === 0;
    inner.style.height = `${rows.length * ROW_H}px`;
    first = last = -1;
    viewport.scrollTop = 0;
    draw();
    if (waiting) void store.load(here);
  };

  const row = (index: number): HTMLElement => {
    const p = rows[index].properties;
    const came = p.states.still_low === true ? "still low after the rain" : p.states.still_low === false ? "back near the start after the rain" : "no data after the rain";
    const dot = h("span", { class: `act-dot is-${p.confidence ?? "none"}`, "aria-hidden": "true" });
    dot.style.background = actionColor(p.action);
    const button = h(
      "button",
      { type: "button", class: "act-row", "aria-current": p.id === selected ? "true" : null },
      h("span", { class: "act-rank", text: String(p.rank ?? "") }),
      h(
        "span",
        { class: "act-row-text" },
        h("span", { class: "act-row-main" }, h("strong", { text: formatValue("dB", p.fall_db) }), dot, h("span", { title: "Agreement", text: p.confidence ?? "" })),
        h("span", { class: "act-row-sub", text: came }),
        h("span", { class: "act-row-sub", text: where(p.lat, p.lon, 3) }),
      ),
    );
    button.style.top = `${index * ROW_H}px`;
    button.dataset.id = p.id;
    button.addEventListener("click", () => onPick(p.id));
    return button;
  };

  // Puts in the page only the rows near the visible part of the list.
  const draw = (): void => {
    const from = Math.max(0, Math.floor(viewport.scrollTop / ROW_H) - SPARE_ROWS);
    const to = Math.min(rows.length - 1, Math.ceil((viewport.scrollTop + (viewport.clientHeight || 6 * ROW_H)) / ROW_H) + SPARE_ROWS);
    if (from === first && to === last) return;
    first = from;
    last = to;
    const items: HTMLElement[] = [];
    for (let i = from; i <= to; i += 1) items.push(row(i));
    inner.replaceChildren(...items);
  };

  let frame = 0;
  viewport.addEventListener("scroll", () => {
    if (frame) return;
    frame = window.requestAnimationFrame(() => {
      frame = 0;
      draw();
    });
  });
  for (const input of [action.input, confidence.input, near.input, site.input]) input.addEventListener("change", filter);
  store.onLoad((loaded) => {
    if (loaded === site.input.value && !root.hidden) filter();
  });

  const name = (): string => `blocks_${action.input.value}_${site.input.value}`;
  csvButton.addEventListener("click", () => download(`${name()}.csv`, "text/csv", toCsv(rows)));
  geoButton.addEventListener("click", () =>
    download(`${name()}.geojson`, "application/geo+json", JSON.stringify({ type: "FeatureCollection", caveat: ontology.caveat, features: rows }) + "\n"),
  );

  return {
    refresh: filter,
    setSelected(id) {
      selected = id;
      for (const el of inner.children) {
        if ((el as HTMLElement).dataset.id === id) el.setAttribute("aria-current", "true");
        else el.removeAttribute("aria-current");
      }
    },
  };
}
