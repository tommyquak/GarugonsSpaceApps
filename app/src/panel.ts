// Written with Super Intelligence (SI) assistance.
// The layer panel: a switch per layer, the legend, opacity and the basemap choice.
import type { Map as MapLibreMap } from "maplibre-gl";
import { BASEMAPS } from "./basemaps";
import { rampColor, type LayerEntry, type Ramp } from "./data";
import { h } from "./dom";
import type { Overlays } from "./overlays";

function trim(value: number): string {
  return String(Math.round(value * 10) / 10);
}

function legend(entry: LayerEntry, ramp: Ramp): HTMLElement {
  const stops: string[] = [];
  const parts = 12;
  for (let i = 0; i <= parts; i += 1) {
    const value = ramp.shown_from + ((ramp.full_at - ramp.shown_from) * i) / parts;
    stops.push(`${rampColor(ramp, value)} ${((100 * i) / parts).toFixed(1)}%`);
  }
  const bar = h("div", { class: "legend-bar", role: "img", "aria-label": "Colour ramp from a small fall to a large fall" });
  bar.style.background = `linear-gradient(to right, ${stops.join(", ")})`;
  const middle = (ramp.shown_from + ramp.full_at) / 2;
  return h(
    "div",
    { class: "legend" },
    h("h3", { text: `Fall in HH brightness, ${entry.unit ?? "dB"}` }),
    bar,
    h(
      "div",
      { class: "legend-ticks" },
      h("span", { text: trim(ramp.shown_from) }),
      h("span", { text: trim(middle) }),
      h("span", { text: `${trim(ramp.full_at)}+` }),
    ),
    h("p", { class: "note", text: "Smaller falls and places without data are left clear." }),
  );
}

export function buildPanel(root: HTMLElement, map: MapLibreMap, overlays: Overlays): void {
  root.replaceChildren(h("h2", { text: "Layers" }));

  if (!overlays.layers.length) {
    root.append(h("p", { class: "note", text: "No layers were found. The map shows the basemap only." }));
  }

  const switches = new Map<string, HTMLInputElement>();
  const list = h("div", { class: "switches" });
  for (const entry of overlays.statics) {
    const input = h("input", { type: "checkbox", role: "switch" });
    input.addEventListener("change", () => overlays.setLayer(entry.id, input.checked));
    switches.set(entry.id, input);
    const swatch = entry.color ? h("span", { class: "swatch" }) : null;
    if (swatch && entry.color) swatch.style.borderColor = entry.color;
    list.append(h("label", { class: "switch" }, input, h("span", { class: "knob" }), h("span", { class: "switch-text", text: entry.title }), swatch));
  }
  root.append(list);
  const hiddenNote = h("p", { class: "note", text: "Whole-season layers are hidden while you step through single passes." });
  root.append(hiddenNote);

  const withRamp = overlays.layers.find((l) => l.ramp);
  if (withRamp?.ramp) root.append(legend(withRamp, withRamp.ramp));

  const opacity = h("input", { type: "range", min: 0, max: 100, step: 5, id: "opacity" });
  opacity.addEventListener("input", () => overlays.setOpacity(Number(opacity.value) / 100));
  root.append(h("div", { class: "field" }, h("label", { class: "field-title", for: "opacity", text: "Layer opacity" }), opacity));

  const basemaps = h("fieldset", { class: "field" }, h("legend", { class: "field-title", text: "Basemap" }));
  for (const base of BASEMAPS) {
    const input = h("input", { type: "radio", name: "basemap", value: base.id, checked: base.id === BASEMAPS[0].id });
    input.addEventListener("change", () => {
      for (const other of BASEMAPS) {
        map.setLayoutProperty(`basemap-${other.id}`, "visibility", other.id === base.id ? "visible" : "none");
      }
    });
    basemaps.append(h("label", { class: "radio" }, input, h("span", { text: base.title })));
  }
  root.append(basemaps);

  const render = (): void => {
    for (const entry of overlays.statics) {
      const input = switches.get(entry.id);
      if (!input) continue;
      input.checked = overlays.on.has(entry.id);
      input.disabled = overlays.mode === "pass" && entry.kind === "season";
    }
    hiddenNote.hidden = overlays.mode !== "pass";
    opacity.value = String(Math.round(overlays.opacity * 100));
  };
  overlays.onChange(render);
  render();
}
