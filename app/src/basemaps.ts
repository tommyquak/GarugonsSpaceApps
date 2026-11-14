// Written with Super Intelligence (SI) assistance.
// Open basemaps only: Sentinel-2 cloudless 2016 by EOX (CC BY 4.0), NASA GIBS Blue Marble and
// OpenStreetMap raster tiles. The Sentinel-2 mosaic is the default because it shows the ground
// at 10 m: rivers, canals, plantation blocks and forest edges under the colour layers.
import type { StyleSpecification } from "maplibre-gl";

export interface Basemap {
  id: string;
  title: string;
}

export const BASEMAPS: Basemap[] = [
  { id: "s2", title: "Sentinel-2 cloud-free, 2016" },
  { id: "osm", title: "OpenStreetMap" },
  { id: "bluemarble", title: "NASA Blue Marble" },
];

export const baseStyle: StyleSpecification = {
  version: 8,
  sources: {
    s2: {
      type: "raster",
      // EOX WMTS in Web Mercator: zoom, row (y), column (x). Only the 2016 mosaic is CC BY 4.0;
      // later years are non-commercial and are not used here.
      tiles: ["https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg"],
      tileSize: 256,
      maxzoom: 15,
      attribution:
        '<a href="https://cloudless.eox.at" target="_blank" rel="noopener">Sentinel-2 cloudless 2016</a> by EOX (contains modified Copernicus Sentinel data 2016), CC BY 4.0',
    },
    bluemarble: {
      type: "raster",
      // GIBS WMTS in Web Mercator. Note the order: zoom, row (y), column (x).
      tiles: [
        "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg",
      ],
      tileSize: 256,
      maxzoom: 8,
      attribution:
        '<a href="https://earthdata.nasa.gov/gibs" target="_blank" rel="noopener">NASA GIBS</a> Blue Marble',
    },
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      maxzoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
    },
  },
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#0d1013" } },
    {
      id: "basemap-s2",
      type: "raster",
      source: "s2",
      // Slightly muted so the colour layers stay the brightest thing on the map.
      paint: { "raster-brightness-max": 0.82, "raster-saturation": -0.25 },
    },
    {
      id: "basemap-bluemarble",
      type: "raster",
      source: "bluemarble",
      layout: { visibility: "none" },
      paint: { "raster-brightness-min": 0.1, "raster-brightness-max": 0.88, "raster-saturation": -0.35, "raster-contrast": -0.15 },
    },
    {
      id: "basemap-osm",
      type: "raster",
      source: "osm",
      layout: { visibility: "none" },
      paint: { "raster-brightness-max": 0.55, "raster-saturation": -0.7 },
    },
    // Empty anchors that fix the drawing order: colour layers go under z-fall, outlines under z-marks.
    { id: "z-fall", type: "background", layout: { visibility: "none" } },
    { id: "z-marks", type: "background", layout: { visibility: "none" } },
  ],
};
