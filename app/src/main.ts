// Written with Super Intelligence (SI) assistance.
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./style.css";
import { baseStyle } from "./basemaps";
import { loadLayers, unionBounds } from "./data";
import { buildDocs } from "./docs";
import { byId } from "./dom";
import { Overlays } from "./overlays";
import { buildPanel } from "./panel";
import { buildSeason } from "./season";

// Room the floating panels take on a wide screen, so views are framed in the free part of the map.
export function viewPadding(): { top: number; bottom: number; left: number; right: number } {
  const wide = window.matchMedia("(min-width: 700px)").matches;
  return wide ? { top: 24, bottom: 130, left: 300, right: 24 } : { top: 16, bottom: 16, left: 16, right: 16 };
}

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
  buildSeason(byId("season"), overlays);
}

void start();
