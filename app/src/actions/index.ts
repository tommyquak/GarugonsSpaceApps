// Written with Super Intelligence (SI) assistance.
// The Actions view (docs/DESIGN.md, "Act"; docs/FUSION.md): the fused 1 km blocks coloured by the
// action recommended for them, flat or as columns, a legend and a ranked list, and for one block
// the object card with its evidence graph. Everything it says is read from public/blocks.
//
//   const actions = await buildActions(map, chart, { setTab });
//   bindLink(map, overlays, chart, actions);
//
// When public/blocks is absent the buttons stay hidden and the rest of the app is unchanged.
import type { Map as MapLibreMap } from "maplibre-gl";
import type { PlaceChart } from "../chart/placeChart";
import { byId, h } from "../dom";
import { buildEvidencePanel } from "../ontology/panel";
import { reducedMotion, WIDE } from "../view";
import { actionColor, CONFIDENCE_LEVELS, confidenceStrength, NO_ACTION } from "./colors";
import { openStore, type BlockStore } from "./data";
import { BlockLayer, METRES_PER_DB } from "./layer";
import { buildList } from "./list";

const PITCH = 55;
const BEARING = -18;
const FLY_ZOOM = 11.5;

/** What the link to this view needs from the Actions view (link.ts). */
export interface ActionsView {
  /** The open parts: "map", "3d", "list" and "how". */
  parts(): string[];
  /** The id of the selected block, or null. */
  block(): string | null;
  apply(parts: string[], block: string | null): void;
  onChange(fn: () => void): void;
}

const absent: ActionsView = { parts: () => [], block: () => null, apply: () => undefined, onChange: () => undefined };

export async function buildActions(map: MapLibreMap, chart: PlaceChart, hooks: { setTab(tab: string): void }): Promise<ActionsView> {
  const found = await openStore();
  if (!found) return absent;
  const store: BlockStore = found;
  const ontology = store.ontology;
  const sheet = byId("sheet");
  const app = byId("app");
  const panel = byId("panel-actions");
  const actionsButton = byId("btn-actions");
  const howButton = byId("btn-how");
  const tabButton = byId("tab-actions");
  const wide = (): boolean => window.matchMedia(WIDE).matches;

  let on = false;
  let columns = false;
  let listOpen = false;
  let how = false;
  let blockId: string | null = null;
  const listeners: (() => void)[] = [];
  const changed = (): void => {
    for (const fn of listeners) fn();
  };

  const layer = new BlockLayer(map, store);

  // ---- The drawer with the object card and the evidence graph ----
  const drawer = buildEvidencePanel(sheet, ontology, {
    color: actionColor,
    ranked: (block) => store.count(block.action, block.site),
    openChart: (block) => {
      drawer.setFolded(true); // the chart and the drawer do not fit on the screen together
      void chart.pick(block.lon, block.lat);
    },
    fly: (block) => fly(block.lon, block.lat),
    link: () => window.location.href,
    onClose: (mode) => (mode === "schema" ? setHow(false) : void select(null)),
    onLayout: () => {
      const open = drawer.mode !== null && !drawer.folded;
      sheet.classList.toggle("drawer-open", open);
      app.classList.toggle("has-drawer", open);
      // The panels beside the open drawer end above it.
      app.style.setProperty("--drawer-h", `${Math.round(drawer.height())}px`);
    },
  });
  // The folded drawer sits just over the season slider, whose height changes with its text.
  const season = byId("season");
  const overSeason = (): void => {
    const box = season.getBoundingClientRect();
    if (box.height) app.style.setProperty("--over-season", `${Math.round(app.getBoundingClientRect().bottom - box.top + 8)}px`);
  };
  new ResizeObserver(overSeason).observe(season);
  overSeason();
  // On a phone one sheet shows at a time: opening a tab folds the drawer down to its title.
  new MutationObserver(() => {
    if (!wide() && sheet.dataset.tab) drawer.setFolded(true);
  }).observe(sheet, { attributes: true, attributeFilter: ["data-tab"] });

  function fly(lon: number, lat: number): void {
    // Frame the block in the part of the map that the drawer and the left column leave free.
    const offset: [number, number] = wide() ? [130, -drawer.height() / 2] : [0, 0];
    map.easeTo({ center: [lon, lat], zoom: Math.max(map.getZoom(), FLY_ZOOM), offset, duration: reducedMotion() ? 0 : 1400, essential: true });
  }

  // ---- The panel: legend, 3D switch and ranked list ----
  const status = h("span", { class: "where" });
  const closeButton = h("button", { type: "button", class: "text-button small", text: "Close" });
  const legendTab = h("button", { type: "button", class: "text-button small", text: "Legend" });
  const listTab = h("button", { type: "button", class: "text-button small", text: "Ranked list" });
  const columnsInput = h("input", { type: "checkbox", role: "switch" });
  const columnsSwitch = h("label", { class: "switch" }, columnsInput, h("span", { class: "knob" }), h("span", { class: "switch-text", text: "3D" }));

  const legend = h("div", { class: "act-legend" });
  for (const action of ontology.actions) {
    const none = action.id === NO_ACTION;
    const swatch = h("span", { class: `act-swatch${none ? " is-none" : ""}`, "aria-hidden": "true" });
    if (!none) swatch.style.background = actionColor(action.id);
    // Each action can be switched off, so a reader can look at one kind of block at a time.
    const toggle = none ? null : h("input", { type: "checkbox", class: "act-toggle", checked: true, "aria-label": `Show ${action.title} blocks` });
    const item = h(
      "div",
      { class: "act-legend-item" },
      h("label", { class: "act-legend-head" }, toggle, swatch, h("strong", { text: action.title }), h("span", { class: "act-legend-count", text: `${store.count(action.id).toLocaleString("en")} blocks` })),
      action.advice ? h("p", { text: action.advice }) : null,
    );
    toggle?.addEventListener("change", () => {
      layer.setActionShown(action.id, toggle.checked);
      item.classList.toggle("is-off", !toggle.checked);
    });
    // Fire is most of the classed blocks and hides the rest, so it starts switched off. Its count stays in view.
    if (toggle && action.id === "fire_detected") {
      toggle.checked = false;
      layer.setActionShown(action.id, false);
      item.classList.add("is-off");
    }
    legend.append(item);
  }
  const strengths = h("div", { class: "act-strengths", title: ontology.confidence?.rule ?? "" }, h("span", { text: ontology.confidence?.label ?? "Agreement" }));
  for (const level of CONFIDENCE_LEVELS) {
    const swatch = h("span", { class: "act-swatch is-level", "aria-hidden": "true" });
    swatch.style.opacity = String(confidenceStrength(level));
    strengths.append(h("span", { class: "act-strength" }, swatch, level));
  }
  const heightNote = h("p", { class: "note", text: `Height shows how far HH fell, in dB: ${METRES_PER_DB.toLocaleString("en")} m of column for each dB.` });
  const howLink = h("button", { type: "button", class: "text-button small", text: "How it decides" });
  const legendBox = h(
    "div",
    {},
    legend,
    strengths,
    h("p", { class: "note", text: "A stronger colour means more of the conditions for that class hold. It is a count, not a probability. Blocks without a class are a faint grid when you zoom in. The other layers are dimmed while this view is open." }),
    heightNote,
    ontology.caveat ? h("p", { class: "note", text: ontology.caveat }) : null,
    h("div", { class: "place-actions" }, howLink),
  );
  const listBox = h("div", { class: "act-list" });
  panel.replaceChildren(
    h("div", { class: "panel-head" }, h("h2", { text: "Where to check" }), status, closeButton),
    h("div", { class: "act-bar" }, h("div", { class: "act-tabs", role: "group", "aria-label": "Parts of the Where to check panel" }, legendTab, listTab), columnsSwitch),
    legendBox,
    listBox,
  );
  // The list opens on the site nearest the middle of the map.
  const siteInView = (): string => {
    const centre = map.getCenter();
    const away = (b: number[]): number => Math.hypot((b[0] + b[2]) / 2 - centre.lng, (b[1] + b[3]) / 2 - centre.lat);
    return [...store.sites].sort((a, b) => away(a.bounds) - away(b.bounds))[0].id;
  };
  const list = buildList(listBox, store, siteInView, (id) => void select(id, true));

  // ---- State ----
  // Blocks are read site by site, and only for the sites on screen.
  const asked = new Set<string>();
  const renderStatus = (): void => {
    status.textContent = on && [...asked].some((id) => !store.isLoaded(id)) ? "Loading the blocks" : "";
  };
  const loadInView = (): void => {
    if (!on) return;
    const view = map.getBounds();
    for (const site of store.sites) {
      const [west, south, east, north] = site.bounds;
      if (west <= view.getEast() && east >= view.getWest() && south <= view.getNorth() && north >= view.getSouth()) {
        asked.add(site.id);
        void store.load(site.id);
      }
    }
    renderStatus();
  };
  store.onLoad(renderStatus);
  map.on("moveend", loadInView);

  const render = (): void => {
    panel.hidden = !on;
    actionsButton.setAttribute("aria-pressed", String(on));
    howButton.setAttribute("aria-pressed", String(how));
    legendTab.setAttribute("aria-pressed", String(!listOpen));
    listTab.setAttribute("aria-pressed", String(listOpen));
    legendBox.hidden = listOpen;
    listBox.hidden = !listOpen;
    columnsInput.checked = columns;
    heightNote.hidden = !columns;
  };

  function setOn(value: boolean): void {
    if (on === value) return;
    on = value;
    layer.setShown(on);
    if (!on) {
      setColumns(false);
      void select(null);
    }
    render();
    loadInView();
    if (on && listOpen) list.refresh();
    changed();
  }

  // Columns need a tilted camera, and a tilted camera may be turned; the flat map may not.
  function setColumns(value: boolean, animate = true): void {
    if (columns === value) return;
    columns = value;
    layer.setColumns(columns);
    for (const handler of [map.dragRotate, map.touchPitch]) {
      if (columns) handler.enable();
      else handler.disable();
    }
    if (columns) {
      map.touchZoomRotate.enableRotation();
      map.keyboard.enableRotation();
    } else {
      map.touchZoomRotate.disableRotation();
      map.keyboard.disableRotation();
    }
    const camera = columns ? { pitch: PITCH, bearing: BEARING } : { pitch: 0, bearing: 0 };
    if (!animate || reducedMotion()) map.jumpTo(camera);
    else map.easeTo({ ...camera, duration: 1200, essential: true });
    render();
    changed();
  }

  function setList(value: boolean): void {
    if (listOpen === value) return;
    listOpen = value;
    render();
    if (listOpen) list.refresh();
    changed();
  }

  function setHow(value: boolean): void {
    if (how === value) return;
    how = value;
    const feature = blockId ? store.get(blockId) : undefined;
    if (how) {
      drawer.showSchema();
      if (!wide()) hooks.setTab("");
    } else if (feature) drawer.showBlock(feature.properties);
    else drawer.hide();
    render();
    changed();
  }

  /** Selects a block by id, or none. The blocks of its site are fetched first when needed. */
  async function select(id: string | null, flyThere = false): Promise<void> {
    if (id === blockId && (id === null || store.get(id))) {
      if (id && !flyThere) drawer.setFolded(false); // a second click on the block brings the card back
      else if (id) fly(store.get(id)?.properties.lon ?? 0, store.get(id)?.properties.lat ?? 0);
      return;
    }
    blockId = id;
    changed();
    const site = id ? store.siteOf(id) : null;
    if (id && site) await store.load(site);
    if (blockId !== id) return; // another block was picked while this one loaded
    const feature = id ? store.get(id) : undefined;
    if (id && !feature) {
      blockId = null; // an id the data does not have
      changed();
    }
    layer.select(feature ?? null);
    list.setSelected(feature ? id : null);
    if (feature) {
      if (!on) setOn(true);
      how = false;
      // A drawer the reader folded stays folded while they step through blocks.
      const keepFolded = drawer.mode === "block" && drawer.folded;
      drawer.showBlock(feature.properties);
      if (keepFolded) drawer.setFolded(true);
      else if (!wide()) hooks.setTab("");
      if (flyThere) fly(feature.properties.lon, feature.properties.lat);
      render();
    } else if (!how) {
      drawer.hide();
    }
  }

  // ---- Controls ----
  actionsButton.addEventListener("click", () => {
    setOn(!on);
    if (on) hooks.setTab("actions");
  });
  tabButton.addEventListener("click", () => {
    if (!on) setOn(true);
    hooks.setTab(sheet.dataset.tab === "actions" ? "" : "actions");
  });
  closeButton.addEventListener("click", () => {
    setOn(false);
    if (sheet.dataset.tab === "actions") hooks.setTab("");
    (wide() ? actionsButton : tabButton).focus();
  });
  howButton.addEventListener("click", () => setHow(!how));
  howLink.addEventListener("click", () => setHow(true));
  legendTab.addEventListener("click", () => setList(false));
  listTab.addEventListener("click", () => setList(true));
  columnsInput.addEventListener("change", () => setColumns(columnsInput.checked));

  // A click that lands on a block selects it and goes no further, so the place chart does not
  // open as well; any other click reaches the map as before. Listening in the capture phase on
  // the map's own container is what lets this run first.
  const container = map.getCanvasContainer();
  let down: { x: number; y: number } | null = null;
  container.addEventListener("pointerdown", (event) => (down = { x: event.clientX, y: event.clientY }), true);
  container.addEventListener(
    "click",
    (event) => {
      if (!on || (down && Math.hypot(event.clientX - down.x, event.clientY - down.y) > 4)) return; // off, or the end of a drag
      const box = map.getCanvas().getBoundingClientRect();
      const id = layer.hit([event.clientX - box.left, event.clientY - box.top]);
      if (!id) return;
      event.stopPropagation();
      void select(id);
    },
    true,
  );

  for (const el of [actionsButton, howButton, tabButton]) el.hidden = false;
  render();

  return {
    parts: () => [...(on ? ["map"] : []), ...(on && columns ? ["3d"] : []), ...(on && listOpen ? ["list"] : []), ...(how ? ["how"] : [])],
    block: () => blockId,
    apply(parts, block) {
      const want = new Set(parts);
      setOn(want.has("map") || block !== null);
      setColumns(on && want.has("3d"), false);
      setList(want.has("list"));
      if (on && listOpen && !wide()) hooks.setTab("actions");
      void select(block).then(() => setHow(want.has("how")));
    },
    onChange(fn) {
      listeners.push(fn);
    },
  };
}
