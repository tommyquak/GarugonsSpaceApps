// Written with Super Intelligence (SI) assistance.
import { AttributionControl, LngLat, Map as MapLibreMap, NavigationControl, ScaleControl, setWorkerUrl } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import "maplibre-gl/dist/maplibre-gl.css";
import "@fontsource/ibm-plex-sans/latin-400.css";
import "@fontsource/ibm-plex-sans/latin-500.css";
import "@fontsource/ibm-plex-sans/latin-600.css";
import "./style.css";
import { buildActions } from "./actions";
import { baseStyle } from "./basemaps";
import { bindPlaceActions } from "./chart/actions";
import { createPlaceChart } from "./chart/placeChart";
import { loadLayers, unionBounds } from "./data";
import { buildDocs } from "./docs";
import { maybePlayIntro } from "./intro";
import { buildMapLegend } from "./maplegend";
import { bindLink } from "./link";
import { byId } from "./dom";
import { Overlays } from "./overlays";
import { buildPanel } from "./panel";
import { buildSeason } from "./season";
import { buildOpening } from "./opening";
import { viewPadding } from "./view";

// MapLibre runs part of its work in a web worker; this is the address of that file in the build.
setWorkerUrl(workerUrl);

// How far the map may be moved: the data extent and about half a degree around it, widened
// where the opening view needs more room (a tall phone screen shows more than that).
function studyLimits(map: MapLibreMap, extent: [number, number, number, number]): [number, number, number, number] {
  const pad = 0.5;
  const limits: [number, number, number, number] = [extent[0] - pad, extent[1] - pad, extent[2] + pad, extent[3] + pad];
  const camera = map.cameraForBounds(extent, { padding: viewPadding() });
  if (camera?.center && camera.zoom !== undefined) {
    const centre = LngLat.convert(camera.center);
    const box = map.getContainer().getBoundingClientRect();
    const degreesPerPixel = 360 / (512 * 2 ** camera.zoom); // near the equator, north-south as east-west
    const halfWide = (box.width / 2) * degreesPerPixel * 1.05;
    const halfTall = (box.height / 2) * degreesPerPixel * 1.05;
    limits[0] = Math.min(limits[0], centre.lng - halfWide);
    limits[1] = Math.min(limits[1], centre.lat - halfTall);
    limits[2] = Math.max(limits[2], centre.lng + halfWide);
    limits[3] = Math.max(limits[3], centre.lat + halfTall);
  }
  return limits;
}

async function start(): Promise<void> {
  const layers = await loadLayers();
  buildDocs(byId("btn-limits"), byId("btn-about"), layers);
  const sources = [...new Set(layers.map((l) => l.source).filter(Boolean))];

  const map = new MapLibreMap({
    container: "map",
    style: baseStyle,
    center: [114.0, -2.8],
    zoom: 9,
    minZoom: 4,
    maxZoom: 15,
    attributionControl: false,
  });
  map.addControl(new AttributionControl({ customAttribution: sources }), "bottom-right");
  map.addControl(new NavigationControl({ showCompass: false }), "top-right");
  map.addControl(new ScaleControl({ unit: "metric" }), "bottom-left");

  // Start on the data, clear of the panels. Without layers the map stays on the study area.
  const extent = unionBounds(layers);
  if (extent) {
    map.setMaxBounds(studyLimits(map, extent));
    map.fitBounds(extent, { padding: viewPadding(), animate: false });
    map.on("resize", () => map.setMaxBounds(studyLimits(map, extent)));
  }
  // The flat map keeps north up: no turning or tilting by drag, touch or keyboard. The 3D view
  // of the Actions panel switches these back on while it is open.
  map.dragRotate.disable();
  map.touchPitch.disable();
  map.touchZoomRotate.disableRotation();
  map.keyboard.disableRotation();

  await map.once("load");
  const overlays = new Overlays(map, layers);
  buildPanel(byId("panel-layers"), map, overlays);
  const season = buildSeason(byId("season"), overlays);

  // On a phone the panels share one bottom sheet, one at a time. A wide screen ignores the tab.
  const sheet = byId("sheet");
  const tabs = ["layers", "place", "story", "actions"];
  const setTab = (tab: string): void => {
    sheet.dataset.tab = tab;
    for (const name of tabs) byId(`tab-${name}`).setAttribute("aria-expanded", String(name === tab));
  };
  const toggleTab = (tab: string): void => setTab(sheet.dataset.tab === tab ? "" : tab);

  byId("tab-layers").addEventListener("click", () => toggleTab("layers"));
  byId("tab-place").addEventListener("click", () => toggleTab("place"));
  setTab("");
  const chart = createPlaceChart(byId("panel-place"), map, overlays, () => setTab("place"));
  bindPlaceActions(byId("panel-place"), map, overlays, chart);
  const legend = buildMapLegend(sheet, layers, overlays);
  const app = byId("app");
  const seasonButton = byId("btn-season");
  const exploreButton = byId("btn-explore");
  const actions = await buildActions(map, chart, {
    setTab,
    setLegend: (view) => legend.setBlocks(view),
    onShown: (on) => {
      overlays.setSuppressed(on);
      if (on) season.stop();
      seasonButton.setAttribute("aria-pressed", String(!on));
    },
  });
  seasonButton.addEventListener("click", () => actions.apply(actions.parts().filter((part) => part === "how"), null));
  // The opening story: replayed from "Story", and played once after a first-visit intro (below).
  const opening = buildOpening(map, overlays, actions, extent, season.stop);
  byId("btn-story").addEventListener("click", () => opening.play());
  byId("tab-story").addEventListener("click", () => opening.play());
  // The raw layers and the class colours are for people who want to dig: off until asked for.
  const setExplore = (on: boolean): void => {
    app.classList.toggle("is-explore", on);
    exploreButton.setAttribute("aria-pressed", String(on));
    if (!on && actions.parts().includes("class")) actions.apply(actions.parts().filter((part) => part !== "class"), actions.block());
  };
  exploreButton.addEventListener("click", () => setExplore(!app.classList.contains("is-explore")));
  // Last, so that a link someone was sent restores its view over the defaults set above.
  const shared = window.location.hash.length > 1;
  bindLink(map, overlays, chart, actions);
  setExplore(actions.parts().includes("class"));
  // Without a link, the map opens on the one view made for a first look.
  if (!shared && actions.parts().length === 0) actions.apply(["map"], null);
  // A visitor who came in through "Enter dashboard" gets the story once; "Skip to map", a wall
  // screen and a shared link all mean they chose where to go. The intro may end before or after
  // this point, so both the mark it leaves and its event are read.
  const afterIntro = (how: string | undefined): void => {
    if (how === "enter" && !shared) opening.play();
  };
  if (document.documentElement.dataset.introExit) afterIntro(document.documentElement.dataset.introExit);
  else window.addEventListener("intro:exit", () => afterIntro(document.documentElement.dataset.introExit), { once: true });
}

// Optional and never awaited: the map below starts whether or not the intro plays.
maybePlayIntro();
void start();
