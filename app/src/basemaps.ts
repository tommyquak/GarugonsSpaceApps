// Written with Super Intelligence (SI) assistance.
// Open basemaps only: NASA GIBS (Blue Marble) and OpenStreetMap raster tiles.
import type { StyleSpecification } from "maplibre-gl";

export interface Basemap {
  id: string;
  title: string;
}

export const BASEMAPS: Basemap[] = [
  { id: "bluemarble", title: "NASA Blue Marble" },
  { id: "osm", title: "OpenStreetMap" },
];

export const baseStyle: StyleSpecification = {
  version: 8,
  sources: {
    bluemarble: {
      type: "raster",
      // GIBS WMTS in Web Mercator. Note the order: zoom, row (y), column (x).
      tiles: [
        "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg",
      ],
      tileSize: 256,
      maxzoom: 8,
      attribution:
        'Basemap: <a href="https://earthdata.nasa.gov/gibs" target="_blank" rel="noopener">NASA GIBS</a>, Blue Marble (NASA Earth Observatory)',
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
      id: "basemap-bluemarble",
      type: "raster",
      source: "bluemarble",
      paint: { "raster-brightness-max": 0.62, "raster-saturation": -0.45, "raster-contrast": 0.1 },
    },
    {
      id: "basemap-osm",
      type: "raster",
      source: "osm",
      layout: { visibility: "none" },
      paint: { "raster-brightness-max": 0.55, "raster-saturation": -0.7 },
    },
  ],
};
