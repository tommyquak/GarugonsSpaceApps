// Written with Super Intelligence (SI) assistance.
import { AttributionControl, LngLat, Map as MapLibreMap, NavigationControl, ScaleControl, setWorkerUrl } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import "maplibre-gl/dist/maplibre-gl.css";
import "./style.css";
import { buildActions } from "./actions";
import { baseStyle } from "./basemaps";
import { bindPlaceActions } from "./chart/actions";
import { createPlaceChart } from "./chart/placeChart";
import { loadLayers, unionBounds } from "./data";
import { buildDocs } from "./docs";
import { bindLink } from "./link";
import { byId } from "./dom";
import { Overlays } from "./overlays";
import { buildPanel } from "./panel";
import { buildSeason } from "./season";
import { buildStory } from "./story";
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

  const story = buildStory(byId("panel-story"), byId("btn-story"), map, overlays, {
    stopPlayback: season.stop,
    onOpen: () => setTab("story"),
    onClose: () => setTab(""),
  });
  byId("tab-layers").addEventListener("click", () => toggleTab("layers"));
  byId("tab-place").addEventListener("click", () => toggleTab("place"));
  byId("tab-story").addEventListener("click", () => (story.isOpen() ? toggleTab("story") : story.open()));
  setTab("");
  const chart = createPlaceChart(byId("panel-place"), map, overlays, () => setTab("place"));
  bindPlaceActions(byId("panel-place"), map, overlays, chart);
  const actions = await buildActions(map, chart, { setTab });
  // Last, so that a link someone was sent restores its view over the defaults set above.
  bindLink(map, overlays, chart, actions);
}

void start();
