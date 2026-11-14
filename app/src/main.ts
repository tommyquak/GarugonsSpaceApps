// Written with Super Intelligence (SI) assistance.
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./style.css";
import { baseStyle } from "./basemaps";

const map = new maplibregl.Map({
  container: "map",
  style: baseStyle,
  center: [114.0, -2.8],
  zoom: 9,
  minZoom: 4,
  maxZoom: 13,
  attributionControl: false,
});

map.addControl(new maplibregl.AttributionControl({ compact: false }), "bottom-right");
map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-right");
