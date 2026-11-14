// Written with Super Intelligence (SI) assistance.
// The blocks on the map: one GeoJSON source per site, drawn flat (a fill coloured by action,
// stronger where the confidence is higher) or as columns whose height is the fall in HH.
import type { ExpressionSpecification, GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";
import { actionColor, confidenceStrength, CONFIDENCE_LEVELS, NONE_COLOR, NO_ACTION, solidColor } from "./colors";
import type { BlockFeature, BlockStore } from "./data";

/** Metres of column per decibel of fall in HH. */
export const METRES_PER_DB = 1200;
const ANCHOR = "z-marks"; // blocks sit over the colour layers and under the outlines (basemaps.ts)
const SELECTED = "blocks-selected";
const VEIL = "blocks-veil";
const GRID_FROM_ZOOM = 10.5;

// A "match" expression from a list of cases; the style types cannot follow one built at run time.
function match(input: unknown, cases: [string, string | number][], otherwise: string | number): ExpressionSpecification {
  return ["match", input, ...cases.flat(), otherwise] as unknown as ExpressionSpecification;
}

const acted: ExpressionSpecification = ["!=", ["get", "action"], NO_ACTION];
const notActed: ExpressionSpecification = ["==", ["get", "action"], NO_ACTION];

export class BlockLayer {
  private sites = new Set<string>();
  private shown = false;
  private columns = false;
  private selected: BlockFeature | null = null;

  constructor(
    private map: MapLibreMap,
    private store: BlockStore,
  ) {
    // A dark veil over the basemap and the colour layers, so the blocks are the brightest thing on the map.
    map.addLayer({ id: VEIL, type: "background", layout: { visibility: "none" }, paint: { "background-color": "#0d1013", "background-opacity": 0.55 } }, ANCHOR);
    map.addSource(SELECTED, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({ id: `${SELECTED}-edge`, type: "line", source: SELECTED, paint: { "line-color": "#0d1013", "line-width": 5.5, "line-opacity": 0.85 } });
    map.addLayer({ id: `${SELECTED}-line`, type: "line", source: SELECTED, paint: { "line-color": "#ffffff", "line-width": 2.5 } });
    store.onLoad((site) => this.add(site));
    for (const site of store.sites) {
      if (store.isLoaded(site.id)) this.add(site.id);
    }
    this.sync();
  }

  private add(site: string): void {
    const features = this.store.features(site);
    if (this.sites.has(site) || !features.length) return;
    this.sites.add(site);
    const id = `blocks-${site}`;
    const actions = this.store.ontology.actions.map((a) => a.id).filter((a) => a !== NO_ACTION);
    // The map needs four properties only; the card and the list read the rest from the store.
    const data = {
      type: "FeatureCollection" as const,
      features: features.map((f) => ({
        type: "Feature" as const,
        geometry: f.geometry,
        properties: { id: f.properties.id, action: f.properties.action, confidence: f.properties.confidence, fall_db: f.properties.fall_db },
      })),
    };
    this.map.addSource(id, { type: "geojson", data, promoteId: "id" });

    const color = match(["get", "action"], actions.map((a) => [a, actionColor(a)]), NONE_COLOR);
    const strength = match(["coalesce", ["get", "confidence"], ""], CONFIDENCE_LEVELS.map((level) => [level, confidenceStrength(level)]), confidenceStrength(null));
    const solid = match(
      ["concat", ["get", "action"], "|", ["coalesce", ["get", "confidence"], ""]],
      actions.flatMap((a) => CONFIDENCE_LEVELS.map((level): [string, string] => [`${a}|${level}`, solidColor(a, level)])),
      NONE_COLOR,
    );

    // Blocks without an action: a faint grey grid once the map is close enough to pick one.
    this.map.addLayer({ id: `${id}-rest`, type: "fill", source: id, minzoom: GRID_FROM_ZOOM, filter: notActed, paint: { "fill-color": NONE_COLOR, "fill-opacity": 0.03 } }, ANCHOR);
    this.map.addLayer(
      { id: `${id}-grid`, type: "line", source: id, minzoom: GRID_FROM_ZOOM, filter: notActed, paint: { "line-color": NONE_COLOR, "line-width": 0.6, "line-opacity": 0.4 } },
      ANCHOR,
    );
    this.map.addLayer(
      { id: `${id}-fill`, type: "fill", source: id, filter: acted, paint: { "fill-color": color, "fill-opacity": strength, "fill-outline-color": "rgba(13, 16, 19, 0.6)" } },
      ANCHOR,
    );
    this.map.addLayer(
      {
        id: `${id}-columns`,
        type: "fill-extrusion",
        source: id,
        filter: acted,
        paint: {
          "fill-extrusion-color": ["case", ["boolean", ["feature-state", "selected"], false], "#ffffff", solid],
          // A block that did not fall still gets a thin slab, so its colour is on the map.
          "fill-extrusion-height": ["*", METRES_PER_DB, ["max", 0.05, ["coalesce", ["get", "fall_db"], 0]]],
          "fill-extrusion-base": 0,
          "fill-extrusion-opacity": 0.92,
        },
      },
      ANCHOR,
    );
    this.mark(this.selected, true);
    this.sync();
  }

  private mark(feature: BlockFeature | null, selected: boolean): void {
    if (!feature || !this.sites.has(feature.properties.site)) return;
    this.map.setFeatureState({ source: `blocks-${feature.properties.site}`, id: feature.properties.id }, { selected });
  }

  private sync(): void {
    const show = (id: string, on: boolean): void => {
      if (this.map.getLayer(id)) this.map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
    };
    for (const site of this.sites) {
      show(`blocks-${site}-rest`, this.shown);
      show(`blocks-${site}-grid`, this.shown);
      show(`blocks-${site}-fill`, this.shown && !this.columns);
      show(`blocks-${site}-columns`, this.shown && this.columns);
    }
    show(VEIL, this.shown);
    show(`${SELECTED}-edge`, this.shown);
    show(`${SELECTED}-line`, this.shown);
  }

  setShown(on: boolean): void {
    this.shown = on;
    this.sync();
  }

  setColumns(on: boolean): void {
    this.columns = on;
    this.sync();
  }

  /** Outlines one block, or none. */
  select(feature: BlockFeature | null): void {
    this.mark(this.selected, false);
    this.selected = feature;
    this.mark(feature, true);
    const source = this.map.getSource(SELECTED) as GeoJSONSource | undefined;
    void source?.setData({ type: "FeatureCollection", features: feature ? [{ type: "Feature", geometry: feature.geometry, properties: {} }] : [] });
  }

  /** The id of the block drawn at a point of the map canvas, or null. */
  hit(point: [number, number]): string | null {
    if (!this.shown) return null;
    const layers = [...this.sites].flatMap((s) => [`blocks-${s}-fill`, `blocks-${s}-columns`, `blocks-${s}-rest`]).filter((id) => this.map.getLayer(id));
    if (!layers.length) return null;
    const found = this.map.queryRenderedFeatures(point, { layers });
    const id = found[0]?.properties?.id;
    return typeof id === "string" ? id : null;
  }
}
