// Written with Super Intelligence (SI) assistance.
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./style.css";
import { baseStyle } from "./basemaps";
import { loadLayers } from "./data";
import { byId } from "./dom";
import { Overlays } from "./overlays";
import { buildPanel } from "./panel";

async function start(): Promise<void> {
  const layers = await loadLayers();
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

  await map.once("load");
  const overlays = new Overlays(map, layers);
  buildPanel(byId("panel-layers"), map, overlays);
}

void start();
