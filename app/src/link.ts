// Written with Super Intelligence (SI) assistance.
// Link to this view (docs/DESIGN.md): the address bar always holds the map position, the
// layers that are on, the radar pass and the chosen place, so a view can be sent to someone.
//
//   #v=9.2/-2.8000/114.0000&l=dried_west,dried_east&d=2026-10-28.061&p=-2.7630,114.1870
//
//   v  zoom / latitude / longitude of the map centre
//   l  ids of the whole-season layers that are switched on ("-" when none is)
//   d  date and track of the radar pass on show; absent for the whole season
//   p  latitude, longitude of the place whose chart is open; absent when none is
//
// A part that is missing or cannot be read is ignored and the default stays.
import type { Map as MapLibreMap } from "maplibre-gl";
import type { PlaceChart } from "./chart/placeChart";
import type { Overlays } from "./overlays";

interface View {
  zoom: number;
  lat: number;
  lon: number;
}

export interface LinkState {
  view?: View;
  layers?: string[];
  pass?: { date: string; track: string };
  place?: { lat: number; lon: number };
}

const inRange = (lat: number, lon: number): boolean => Math.abs(lat) <= 90 && Math.abs(lon) <= 180;

function numbers(text: string, separator: string, count: number): number[] | null {
  const parts = text.split(separator);
  if (parts.length !== count || parts.some((p) => p.trim() === "")) return null;
  const values = parts.map(Number);
  return values.every(Number.isFinite) ? values : null;
}

/** Reads the part of an address after "#". Never throws. */
export function parseLink(hash: string): LinkState {
  const state: LinkState = {};
  const params = new URLSearchParams(hash.replace(/^#/, ""));
  const v = numbers(params.get("v") ?? "", "/", 3);
  if (v && v[0] >= 0 && v[0] <= 24 && inRange(v[1], v[2])) state.view = { zoom: v[0], lat: v[1], lon: v[2] };
  const l = params.get("l");
  if (l !== null) state.layers = l === "-" ? [] : l.split(",").filter(Boolean);
  const d = /^(\d{4}-\d{2}-\d{2})\.(\w+)$/.exec(params.get("d") ?? "");
  if (d) state.pass = { date: d[1], track: d[2] };
  const p = numbers(params.get("p") ?? "", ",", 2);
  if (p && inRange(p[0], p[1])) state.place = { lat: p[0], lon: p[1] };
  return state;
}

/** Writes a state as the part of an address after "#". */
export function formatLink(state: LinkState): string {
  const parts: string[] = [];
  if (state.view) parts.push(`v=${state.view.zoom.toFixed(2)}/${state.view.lat.toFixed(4)}/${state.view.lon.toFixed(4)}`);
  if (state.layers) parts.push(`l=${state.layers.length ? state.layers.map(encodeURIComponent).join(",") : "-"}`);
  if (state.pass) parts.push(`d=${state.pass.date}.${encodeURIComponent(state.pass.track)}`);
  if (state.place) parts.push(`p=${state.place.lat.toFixed(4)},${state.place.lon.toFixed(4)}`);
  return `#${parts.join("&")}`;
}

/** Restores the view named in the address, then keeps the address in step with the app. */
export function bindLink(map: MapLibreMap, overlays: Overlays, chart: PlaceChart): void {
  const apply = (state: LinkState): void => {
    if (state.view) map.jumpTo({ center: [state.view.lon, state.view.lat], zoom: state.view.zoom });
    // Layer ids the app does not know are dropped; a list with none it knows changes nothing.
    const known = state.layers?.filter((id) => overlays.statics.some((entry) => entry.id === id));
    if (known && (known.length > 0 || state.layers?.length === 0)) {
      const wanted = new Set(known);
      for (const entry of overlays.statics) {
        if (overlays.on.has(entry.id) !== wanted.has(entry.id)) overlays.setLayer(entry.id, wanted.has(entry.id));
      }
    }
    if (state.pass) {
      const index = overlays.steps.findIndex((s) => s.date === state.pass?.date && s.track === state.pass?.track);
      if (index >= 0) overlays.setStep(index);
    } else if (overlays.mode === "pass") {
      overlays.setMode("season");
    }
    const at = chart.place;
    if (state.place && !(at && at.lat.toFixed(4) === state.place.lat.toFixed(4) && at.lon.toFixed(4) === state.place.lon.toFixed(4))) {
      void chart.pick(state.place.lon, state.place.lat);
    }
  };

  const current = (): string => {
    const centre = map.getCenter();
    const step = overlays.step;
    return formatLink({
      view: { zoom: map.getZoom(), lat: centre.lat, lon: centre.lng },
      layers: overlays.statics.filter((entry) => overlays.on.has(entry.id)).map((entry) => entry.id),
      pass: step ? { date: step.date, track: step.track } : undefined,
      place: chart.place ?? undefined,
    });
  };

  // replaceState: moving the map must not fill the Back button with a step per move.
  const write = (): void => {
    const hash = current();
    if (hash !== window.location.hash) window.history.replaceState(null, "", hash);
  };

  if (window.location.hash.length > 1) apply(parseLink(window.location.hash));
  map.on("moveend", write);
  overlays.onChange(write);
  chart.onPick(write);
  // Someone pasted another link into the same tab, or edited the address by hand.
  window.addEventListener("hashchange", () => {
    if (window.location.hash === current()) return;
    apply(parseLink(window.location.hash));
    write(); // puts back whatever the pasted address left out or got wrong
  });
  write();
}
