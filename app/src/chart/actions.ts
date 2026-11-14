// Written with Super Intelligence (SI) assistance.
// The three actions of the place card (docs/DESIGN.md, "Explore"), plus the list they feed:
//
//   Fly down      tilts the camera low over the place and circles it slowly
//   Ground look   a small second map of NASA optical imagery of the same spot on a chosen day
//   Add to list   pins the place to "My places", kept in this browser, with CSV and GeoJSON export
import { Map as MapLibreMap, Marker } from "maplibre-gl";
import { formatDay } from "../data";
import { h } from "../dom";
import type { Overlays } from "../overlays";
import { reducedMotion } from "../view";
import type { PlaceChart } from "./placeChart";

interface Saved {
  lat: number;
  lon: number;
  added: string; // YYYY-MM-DD
}

const STORE = "dry-season-waltz.places";
const FLY_ZOOM = 13.5;
const FLY_PITCH = 60;
const TURN_DEG_PER_S = 5;
const LOOK_ZOOM = 9; // the finest level of the daily VIIRS image, about 250 m
const LOOK_FIRST_DAY = "2026-05-01";
// GIBS WMTS in Web Mercator: zoom, row (y), column (x). One true-colour image per day.
const lookTiles = (day: string): string =>
  `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/${day}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`;

const key = (p: { lat: number; lon: number }): string => `${p.lat.toFixed(4)},${p.lon.toFixed(4)}`;
const where = (p: { lat: number; lon: number }): string =>
  `${Math.abs(p.lat).toFixed(3)} ${p.lat < 0 ? "S" : "N"}, ${Math.abs(p.lon).toFixed(3)} ${p.lon < 0 ? "W" : "E"}`;
const isoDay = (date: Date): string => date.toISOString().slice(0, 10);
const shiftDay = (day: string, by: number): string => isoDay(new Date(Date.parse(`${day}T00:00:00Z`) + by * 86_400_000));

function loadSaved(): Saved[] {
  try {
    const list: unknown = JSON.parse(window.localStorage.getItem(STORE) ?? "[]");
    if (!Array.isArray(list)) return [];
    return list.filter(
      (p): p is Saved => typeof p?.lat === "number" && typeof p?.lon === "number" && Math.abs(p.lat) <= 90 && Math.abs(p.lon) <= 180 && typeof p?.added === "string",
    );
  } catch {
    return []; // storage switched off or holding something else: start with an empty list
  }
}

function download(name: string, type: string, text: string): void {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = h("a", { href: url, download: name });
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Adds the actions to the place card and the "My places" list under it. */
export function bindPlaceActions(root: HTMLElement, map: MapLibreMap, overlays: Overlays, chart: PlaceChart): void {
  let saved = loadSaved();
  const pins = new Map<string, Marker>();

  // ---- Fly down ----
  let flying = false;
  let frame = 0;
  const stopTurning = (): void => {
    window.cancelAnimationFrame(frame);
    frame = 0;
  };
  const flyDown = (place: { lon: number; lat: number }): void => {
    flying = true;
    const view = { center: [place.lon, place.lat] as [number, number], zoom: Math.min(map.getMaxZoom(), FLY_ZOOM), pitch: FLY_PITCH };
    if (reducedMotion()) {
      map.jumpTo(view); // the tilted view without the flight or the circling
      return;
    }
    let taken = false; // the user took the camera during the flight
    const take = (): void => {
      taken = true;
    };
    map.once("dragstart", take);
    map.once("wheel", take);
    map.flyTo({ ...view, duration: 3500, essential: true });
    map.once("moveend", () => {
      map.off("dragstart", take);
      map.off("wheel", take);
      if (!flying || taken) return;
      let last = performance.now();
      const turn = (now: number): void => {
        map.setBearing(map.getBearing() + ((now - last) / 1000) * TURN_DEG_PER_S);
        last = now;
        frame = window.requestAnimationFrame(turn);
      };
      frame = window.requestAnimationFrame(turn);
    });
  };
  const flatten = (): void => {
    if (!flying) return;
    flying = false;
    stopTurning();
    map.easeTo({ pitch: 0, bearing: 0, duration: reducedMotion() ? 0 : 1200, essential: true });
  };
  // Any touch of the map hands the camera back; the view stays tilted until "Back to the flat map".
  for (const event of ["dragstart", "wheel", "touchstart", "dblclick"] as const) map.on(event, stopTurning);

  // ---- Ground look ----
  let look: MapLibreMap | null = null;
  const closeLook = (): void => {
    look?.remove();
    look = null;
  };
  const yesterday = (): string => shiftDay(isoDay(new Date()), -1);
  const clampDay = (day: string): string => (day < LOOK_FIRST_DAY ? LOOK_FIRST_DAY : day > yesterday() ? yesterday() : day);

  function buildLook(place: { lon: number; lat: number }): HTMLElement {
    const start = clampDay(overlays.step?.date ?? overlays.steps[overlays.steps.length - 1]?.date ?? yesterday());
    const date = h("input", { type: "date", min: LOOK_FIRST_DAY, max: yesterday(), value: start, "aria-label": "Day of the optical image" });
    const before = h("button", { type: "button", class: "text-button small", text: "Day before" });
    const after = h("button", { type: "button", class: "text-button small", text: "Day after" });
    const frameEl = h("div", { class: "look-map", role: "img" });
    const caption = h("p", { class: "note", "aria-live": "polite" });
    const box = h(
      "div",
      { class: "look" },
      h("div", { class: "look-row" }, before, date, after),
      frameEl,
      caption,
      h("p", {
        class: "note",
        text: "NASA GIBS: VIIRS true colour from Suomi NPP, one image a day at about 250 m. On most dry-season days it shows cloud or smoke. That is why this map uses radar, which sees through both.",
      }),
    );
    const show = (day: string): void => {
      const value = clampDay(day);
      date.value = value;
      before.disabled = value <= LOOK_FIRST_DAY;
      after.disabled = value >= yesterday();
      caption.textContent = `Optical image of ${formatDay(value)}. The ring marks the place.`;
      frameEl.setAttribute("aria-label", `Satellite photograph of the area around the place on ${formatDay(value)}`);
      if (!look) return;
      if (look.getLayer("optical")) look.removeLayer("optical");
      if (look.getSource("optical")) look.removeSource("optical");
      look.addSource("optical", { type: "raster", tiles: [lookTiles(value)], tileSize: 256, maxzoom: LOOK_ZOOM });
      look.addLayer({ id: "optical", type: "raster", source: "optical", paint: { "raster-fade-duration": 0 } });
    };
    date.addEventListener("change", () => date.value && show(date.value));
    before.addEventListener("click", () => show(shiftDay(date.value, -1)));
    after.addEventListener("click", () => show(shiftDay(date.value, 1)));
    // The map needs its box in the page before it can size itself.
    window.requestAnimationFrame(() => {
      if (!frameEl.isConnected) return;
      const small = new MapLibreMap({
        container: frameEl,
        style: { version: 8, sources: {}, layers: [{ id: "background", type: "background", paint: { "background-color": "#0d1013" } }] },
        center: [place.lon, place.lat],
        zoom: LOOK_ZOOM,
        interactive: false,
        attributionControl: false,
      });
      look = small;
      new Marker({ element: h("div", { class: "place-marker" }) }).setLngLat([place.lon, place.lat]).addTo(small);
      void small.once("load").then(() => {
        if (look === small) show(date.value);
      });
    });
    show(start);
    return box;
  }

  // ---- My places ----
  const list = h("ul", { class: "places-list" });
  const footer = h(
    "section",
    { class: "my-places", "aria-label": "My places" },
    h("h3", { text: "My places" }),
    list,
    h("p", { class: "note", text: "Kept in this browser only." }),
  );
  const csvButton = h("button", { type: "button", class: "text-button small", text: "Export CSV" });
  const geoButton = h("button", { type: "button", class: "text-button small", text: "Export GeoJSON" });
  footer.append(h("div", { class: "place-actions" }, csvButton, geoButton));
  csvButton.addEventListener("click", () =>
    download("my_places.csv", "text/csv", ["latitude,longitude,added", ...saved.map((p) => `${p.lat.toFixed(5)},${p.lon.toFixed(5)},${p.added}`)].join("\n") + "\n"),
  );
  geoButton.addEventListener("click", () =>
    download(
      "my_places.geojson",
      "application/geo+json",
      JSON.stringify(
        {
          type: "FeatureCollection",
          features: saved.map((p) => ({
            type: "Feature",
            geometry: { type: "Point", coordinates: [Number(p.lon.toFixed(5)), Number(p.lat.toFixed(5))] },
            properties: { added: p.added },
          })),
        },
        null,
        1,
      ) + "\n",
    ),
  );

  let renderActions: () => void = () => undefined;
  const renderPlaces = (): void => {
    root.classList.toggle("has-places", saved.length > 0);
    footer.hidden = saved.length === 0;
    list.replaceChildren(
      ...saved.map((p) => {
        const go = h("button", { type: "button", class: "place-link", text: where(p) });
        go.addEventListener("click", () => {
          flatten();
          map.easeTo({ center: [p.lon, p.lat], duration: reducedMotion() ? 0 : 800, essential: true });
          void chart.pick(p.lon, p.lat);
        });
        const remove = h("button", { type: "button", class: "text-button small", text: "Remove", "aria-label": `Remove ${where(p)} from my places` });
        remove.addEventListener("click", () => setSaved(saved.filter((q) => key(q) !== key(p))));
        return h("li", {}, go, remove);
      }),
    );
    const keep = new Set(saved.map(key));
    for (const [k, pin] of pins) {
      if (!keep.has(k)) {
        pin.remove();
        pins.delete(k);
      }
    }
    for (const p of saved) {
      if (!pins.has(key(p))) pins.set(key(p), new Marker({ element: h("div", { class: "place-pin" }) }).setLngLat([p.lon, p.lat]).addTo(map));
    }
  };
  const setSaved = (next: Saved[]): void => {
    saved = next;
    try {
      window.localStorage.setItem(STORE, JSON.stringify(saved));
    } catch {
      // Storage is off or full: the list still works until the page is closed.
    }
    renderPlaces();
    renderActions();
  };

  // ---- The row of buttons in the card ----
  chart.setParts({
    footer,
    actions: (lon, lat) => {
      const place = { lon, lat };
      const flyButton = h("button", { type: "button", class: "text-button small" });
      const lookButton = h("button", { type: "button", class: "text-button small", "aria-expanded": "false", text: "Ground look" });
      const saveButton = h("button", { type: "button", class: "text-button small" });
      const lookSlot = h("div", {});
      renderActions = (): void => {
        flyButton.textContent = flying ? "Back to the flat map" : "Fly down";
        flyButton.setAttribute("aria-pressed", String(flying));
        const isSaved = saved.some((p) => key(p) === key(place));
        saveButton.textContent = isSaved ? "Remove from list" : "Add to list";
        saveButton.setAttribute("aria-pressed", String(isSaved));
      };
      flyButton.addEventListener("click", () => {
        if (flying) flatten();
        else flyDown(place);
        renderActions();
      });
      lookButton.addEventListener("click", () => {
        const open = lookButton.getAttribute("aria-expanded") !== "true";
        lookButton.setAttribute("aria-expanded", String(open));
        closeLook();
        lookSlot.replaceChildren(...(open ? [buildLook(place)] : []));
      });
      saveButton.addEventListener("click", () => {
        const isSaved = saved.some((p) => key(p) === key(place));
        setSaved(isSaved ? saved.filter((p) => key(p) !== key(place)) : [...saved, { lat, lon, added: isoDay(new Date()) }]);
      });
      renderActions();
      return h("div", {}, h("div", { class: "place-actions" }, flyButton, lookButton, saveButton), lookSlot);
    },
  });

  // A new place or a closed card ends the flight and the ground look of the old one.
  chart.onPick(() => {
    closeLook();
    if (flying && !chart.place) flatten();
    else if (flying) {
      flying = false;
      stopTurning();
    }
  });
  renderPlaces();
}
