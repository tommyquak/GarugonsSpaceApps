// Written with Super Intelligence (SI) assistance.
// The blocks on the map: one GeoJSON source per site, drawn flat (a fill coloured by action,
// stronger where the confidence is higher) or as columns whose height is the fall in HH. In the
// at-a-glance view the same blocks are coloured by level instead (levels.ts), and a column's
// height is its level too, so that colour and height say the same thing. The block under
// the pointer lights up and the pointer becomes a hand, flat and as columns, so it is plain
// that a block can be clicked.
// As columns in the at-a-glance view, the blocks of a level that touch are drawn as one shape
// with slightly rounded corners (merged.ts). The blocks stay underneath, unseen, so that the
// pointer still finds a block, and the block under the pointer or selected is drawn on top.
import type { ExpressionSpecification, GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";
import { actionColor, confidenceStrength, CONFIDENCE_LEVELS, NONE_COLOR, NO_ACTION, solidColor } from "./colors";
import type { BlockFeature, BlockStore } from "./data";
import { LEVELS, levelOf } from "./levels";
import { levelShapes } from "./merged";

/** Metres of column per decibel of fall in HH. */
export const METRES_PER_DB = 1200;
const ANCHOR = "z-marks"; // blocks sit over the colour layers and under the outlines (basemaps.ts)
const SELECTED = "blocks-selected";
const VEIL = "blocks-veil";
const LIT = "blocks-lit"; // the hovered and the selected block, as columns over the rounded shapes
const COLUMN_OPACITY = 0.92;
const GRID_FROM_ZOOM = 10.5;
const HOVER_COLOR = "#ece8df"; // the ink of the interface: a hovered block reads as a control

const isSelected: ExpressionSpecification = ["boolean", ["feature-state", "selected"], false];
const isHovered: ExpressionSpecification = ["boolean", ["feature-state", "hover"], false];

// A "match" expression from a list of cases; the style types cannot follow one built at run time.
function match(input: unknown, cases: [string, string | number][], otherwise: string | number): ExpressionSpecification {
  return ["match", input, ...cases.flat(), otherwise] as unknown as ExpressionSpecification;
}

// A value per level, for a paint property.
function byLevel<T extends string | number>(pick: (level: (typeof LEVELS)[number]) => T): ExpressionSpecification {
  const lowest = LEVELS[LEVELS.length - 1];
  return ["match", ["get", "level"], ...LEVELS.slice(0, -1).flatMap((level) => [level.id, pick(level)]), pick(lowest)] as unknown as ExpressionSpecification;
}

const acted: ExpressionSpecification = ["!=", ["get", "action"], NO_ACTION];
const notActed: ExpressionSpecification = ["==", ["get", "action"], NO_ACTION];

export class BlockLayer {
  private sites = new Set<string>();
  private shown = false;
  private columns = false;
  private selected: BlockFeature | null = null;
  private hidden = new Set<string>();   // actions switched off in the legend
  private glance = true;                // coloured by level, not by class
  private hovered: { source: string; id: string } | null = null;

  constructor(
    private map: MapLibreMap,
    private store: BlockStore,
  ) {
    // A dark veil over the basemap and the colour layers, so the blocks are the brightest thing on the map.
    map.addLayer({ id: VEIL, type: "background", layout: { visibility: "none" }, paint: { "background-color": "#0d1013", "background-opacity": 0.55 } }, ANCHOR);
    map.addSource(LIT, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({
      id: LIT,
      type: "fill-extrusion",
      source: LIT,
      layout: { visibility: "none" },
      paint: { "fill-extrusion-color": ["get", "color"], "fill-extrusion-height": ["get", "height"], "fill-extrusion-base": 0, "fill-extrusion-opacity": 1 },
    });
    map.addSource(SELECTED, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({ id: `${SELECTED}-edge`, type: "line", source: SELECTED, paint: { "line-color": "#0d1013", "line-width": 5.5, "line-opacity": 0.85 } });
    map.addLayer({ id: `${SELECTED}-line`, type: "line", source: SELECTED, paint: { "line-color": "#ffffff", "line-width": 2.5 } });
    // The block under the pointer, at most once per frame.
    let frame = 0;
    let at: [number, number] | null = null;
    map.on("mousemove", (event) => {
      at = [event.point.x, event.point.y];
      if (!frame) {
        frame = requestAnimationFrame(() => {
          frame = 0;
          if (at) this.hover(at);
        });
      }
    });
    map.on("mouseout", () => {
      at = null;
      this.setHovered(null);
    });
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
    // The map needs five properties only; the card and the list read the rest from the store.
    const data = {
      type: "FeatureCollection" as const,
      features: features.map((f) => ({
        type: "Feature" as const,
        geometry: f.geometry,
        properties: { id: f.properties.id, action: f.properties.action, confidence: f.properties.confidence, fall_db: f.properties.fall_db, level: levelOf(f.properties) },
      })),
    };
    this.map.addSource(id, { type: "geojson", data, promoteId: "id" });
    const { color, strength, solid, height } = this.paints();

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
          "fill-extrusion-color": ["case", isSelected, "#ffffff", isHovered, HOVER_COLOR, solid],
          "fill-extrusion-height": height,
          "fill-extrusion-base": 0,
          "fill-extrusion-opacity": COLUMN_OPACITY,
        },
      },
      ANCHOR,
    );
    // The same blocks joined into one rounded shape per level, for the 3D at-a-glance view.
    const shapes = levelShapes(data.features.filter((f) => f.properties.level > 0).map((f) => ({ ring: f.geometry.coordinates[0], level: f.properties.level })));
    this.map.addSource(`${id}-shapes`, { type: "geojson", data: { type: "FeatureCollection", features: shapes } });
    this.map.addLayer(
      {
        id: `${id}-shapes`,
        type: "fill-extrusion",
        source: `${id}-shapes`,
        paint: {
          "fill-extrusion-color": byLevel((l) => l.solid),
          "fill-extrusion-height": byLevel((l) => l.height),
          "fill-extrusion-base": 0,
          "fill-extrusion-opacity": COLUMN_OPACITY,
        },
      },
      ANCHOR,
    );
    this.applyMode();
    this.mark(this.selected, true);
    this.sync();
  }

  /** Colour, opacity, column colour and column height of a block, by level or by class and agreement. */
  private paints(): { color: ExpressionSpecification; strength: ExpressionSpecification; solid: ExpressionSpecification; height: ExpressionSpecification } {
    if (this.glance) return { color: byLevel((l) => l.color), strength: byLevel((l) => l.strength), solid: byLevel((l) => l.solid), height: byLevel((l) => l.height) };
    const actions = this.store.ontology.actions.map((a) => a.id).filter((a) => a !== NO_ACTION);
    return {
      color: match(["get", "action"], actions.map((a) => [a, actionColor(a)]), NONE_COLOR),
      strength: match(["coalesce", ["get", "confidence"], ""], CONFIDENCE_LEVELS.map((level) => [level, confidenceStrength(level)]), confidenceStrength(null)),
      solid: match(
        ["concat", ["get", "action"], "|", ["coalesce", ["get", "confidence"], ""]],
        actions.flatMap((a) => CONFIDENCE_LEVELS.map((level): [string, string] => [`${a}|${level}`, solidColor(a, level)])),
        NONE_COLOR,
      ),
      // By class the height is the fall in HH. A block that did not fall still gets a thin slab, so its colour is on the map.
      height: ["*", METRES_PER_DB, ["max", 0.05, ["coalesce", ["get", "fall_db"], 0]]],
    };
  }

  /** Repaints and refilters every site for the current way of colouring. */
  private applyMode(): void {
    const { color, strength, solid, height } = this.paints();
    // The classes switched off in the legend only apply when the blocks are coloured by class.
    const filter: ExpressionSpecification = !this.glance && this.hidden.size ? ["all", acted, ["!", ["in", ["get", "action"], ["literal", [...this.hidden]]]]] : acted;
    for (const site of this.sites) {
      const fill = `blocks-${site}-fill`;
      const columns = `blocks-${site}-columns`;
      if (this.map.getLayer(fill)) {
        this.map.setPaintProperty(fill, "fill-color", ["case", isHovered, HOVER_COLOR, color]);
        this.map.setPaintProperty(fill, "fill-opacity", ["case", isHovered, 0.95, strength]);
        this.map.setFilter(fill, filter);
      }
      if (this.map.getLayer(columns)) {
        this.map.setPaintProperty(columns, "fill-extrusion-color", ["case", isSelected, "#ffffff", isHovered, HOVER_COLOR, solid]);
        this.map.setPaintProperty(columns, "fill-extrusion-height", height);
        this.map.setFilter(columns, filter);
      }
    }
  }

  /** Colours the blocks by level (true) or by class and agreement (false). */
  setGlance(on: boolean): void {
    this.glance = on;
    this.applyMode();
    this.sync();
  }

  /** Lights the classed block at a point of the map canvas, and shows a hand over it. */
  private hover(point: [number, number]): void {
    if (!this.shown) {
      this.setHovered(null);
      return;
    }
    const layers = [...this.sites].flatMap((s) => [`blocks-${s}-fill`, `blocks-${s}-columns`]).filter((id) => this.map.getLayer(id));
    const found = layers.length ? this.map.queryRenderedFeatures(point, { layers })[0] : undefined;
    const id = found?.properties?.id;
    this.setHovered(found && typeof id === "string" ? { source: found.source, id } : null);
  }

  private setHovered(next: { source: string; id: string } | null): void {
    if (next?.id === this.hovered?.id) return;
    if (this.hovered && this.map.getSource(this.hovered.source)) this.map.setFeatureState(this.hovered, { hover: false });
    this.hovered = next;
    if (next) this.map.setFeatureState(next, { hover: true });
    this.light();
    this.map.getCanvas().style.cursor = next ? "pointer" : "";
  }

  private mark(feature: BlockFeature | null, selected: boolean): void {
    if (!feature || !this.sites.has(feature.properties.site)) return;
    this.map.setFeatureState({ source: `blocks-${feature.properties.site}`, id: feature.properties.id }, { selected });
  }

  /** The hovered and the selected block as columns of their own, which the rounded shapes would otherwise hide. */
  private light(): void {
    const column = (block: BlockFeature | null | undefined, color: string) => {
      const level = block ? LEVELS.find((l) => l.id === levelOf(block.properties)) : undefined;
      return block && level ? [{ type: "Feature" as const, geometry: block.geometry, properties: { color, height: level.height + 30 } }] : [];
    };
    const hovered = this.hovered && this.hovered.id !== this.selected?.properties.id ? this.store.get(this.hovered.id) : null;
    const source = this.map.getSource(LIT) as GeoJSONSource | undefined;
    void source?.setData({ type: "FeatureCollection", features: [...column(hovered, HOVER_COLOR), ...column(this.selected, "#ffffff")] });
  }

  private sync(): void {
    const show = (id: string, on: boolean): void => {
      if (this.map.getLayer(id)) this.map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
    };
    // Rounded shapes only as columns in the at-a-glance view; flat, and by class, the blocks are drawn as they are.
    const rounded = this.shown && this.columns && this.glance;
    for (const site of this.sites) {
      show(`blocks-${site}-rest`, this.shown);
      show(`blocks-${site}-grid`, this.shown);
      show(`blocks-${site}-fill`, this.shown && !this.columns);
      show(`blocks-${site}-columns`, this.shown && this.columns);
      show(`blocks-${site}-shapes`, rounded);
      // Under the shapes the block columns are not painted, but they are still what the pointer finds.
      if (this.map.getLayer(`blocks-${site}-columns`)) this.map.setPaintProperty(`blocks-${site}-columns`, "fill-extrusion-opacity", rounded ? 0 : COLUMN_OPACITY);
    }
    show(LIT, rounded);
    show(VEIL, this.shown);
    show(`${SELECTED}-edge`, this.shown);
    show(`${SELECTED}-line`, this.shown);
  }

  setShown(on: boolean): void {
    if (!on) this.setHovered(null);
    this.shown = on;
    this.sync();
  }

  setColumns(on: boolean): void {
    this.columns = on;
    this.sync();
  }

  /** Shows or hides every block of one action, flat and as columns. */
  setActionShown(action: string, on: boolean): void {
    if (on) this.hidden.delete(action);
    else this.hidden.add(action);
    this.applyMode();
  }

  isActionShown(action: string): boolean {
    return !this.hidden.has(action);
  }

  /** Outlines one block, or none. */
  select(feature: BlockFeature | null): void {
    this.mark(this.selected, false);
    this.selected = feature;
    this.mark(feature, true);
    this.light();
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
