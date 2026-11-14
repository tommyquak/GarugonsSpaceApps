// Written with Super Intelligence (SI) assistance.
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./style.css";
import { baseStyle } from "./basemaps";
import { PlaceChart } from "./chart";
import { loadLayers, unionBounds } from "./data";
import { buildDocs } from "./docs";
import { byId } from "./dom";
import { Overlays } from "./overlays";
import { buildPanel } from "./panel";
import { buildSeason } from "./season";
import { buildStory } from "./story";
import { viewPadding } from "./view";

async function start(): Promise<void> {
  const layers = await loadLayers();
  buildDocs(byId("btn-limits"), byId("btn-about"), layers);
  const sources = [...new Set(layers.map((l) => l.source).filter(Boolean))];

  const map = new maplibregl.Map({
    container: "map",
    style: baseStyle,
    center: [114.0, -2.8],
    zoom: 9,
    minZoom: 4,
    maxZoom: 13,
    attributionControl: false,
  });
  map.addControl(new maplibregl.AttributionControl({ customAttribution: sources }), "bottom-right");
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");

  // Start on the data, clear of the panels. Without layers the map stays on the study area.
  const extent = unionBounds(layers);
  if (extent) map.fitBounds(extent, { padding: viewPadding(), animate: false });

  await map.once("load");
  const overlays = new Overlays(map, layers);
  buildPanel(byId("panel-layers"), map, overlays);
  const season = buildSeason(byId("season"), overlays);

  // On a phone the panels share one bottom sheet, one at a time. A wide screen ignores the tab.
  const sheet = byId("sheet");
  const tabs = ["layers", "place", "story"];
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
  new PlaceChart(byId("panel-place"), map, overlays, () => setTab("place"));
}

void start();
