// Written with Super Intelligence (SI) assistance.
// A small legend on the map itself, so the meaning of the colours is in view without opening a
// panel. It shows the ramp of the fall in HH, with fire while the season slider is showing it;
// while the "Where to check" view is open it shows the colours of the blocks instead.
import { rampColor, type LayerEntry } from "./data";
import { h } from "./dom";
import type { Overlays } from "./overlays";

export interface LegendRows {
  title: string;
  rows: { color: string; label: string }[];
  note: string;
}

export interface MapLegend {
  /** The colours of the blocks while that view is open, or null for the fall in HH. */
  setBlocks(view: LegendRows | null): void;
}

export function buildMapLegend(parent: HTMLElement, layers: LayerEntry[], overlays: Overlays): MapLegend {
  const root = h("aside", { id: "map-legend", class: "card", "aria-label": "Legend of the map" });
  parent.append(root);
  const entry = layers.find((l) => l.kind === "season" && l.ramp) ?? layers.find((l) => l.ramp);

  const fall = (): HTMLElement[] => {
    if (!entry?.ramp) return [];
    const ramp = entry.ramp;
    const stops: string[] = [];
    for (let i = 0; i <= 8; i++) stops.push(`${rampColor(ramp, ramp.shown_from + ((ramp.full_at - ramp.shown_from) * i) / 8)} ${(12.5 * i).toFixed(1)}%`);
    const bar = h("div", { class: "legend-bar", role: "img", "aria-label": "Colour ramp from a small fall to a large fall" });
    bar.style.background = `linear-gradient(to right, ${stops.join(", ")})`;
    const unit = entry.unit ?? "dB";
    const fireOn = (overlays.mode === "pass" && overlays.hasPassFire && overlays.passFire) || overlays.statics.some((l) => l.kind === "fire" && overlays.isShown(l));
    const fireColor = layers.find((l) => l.kind === "fire" || l.kind === "fire-until")?.color ?? "#de3626";
    const swatch = h("span", { class: "act-swatch", "aria-hidden": "true" });
    swatch.style.background = fireColor;
    const parts: (HTMLElement | null)[] = [
      h("h3", { text: "How far the radar echo fell" }),
      bar,
      h("div", { class: "legend-ticks" }, h("span", { text: `${ramp.shown_from} ${unit}, a little` }), h("span", { text: `${ramp.full_at} ${unit} or more` })),
      fireOn ? h("div", { class: "map-legend-row" }, swatch, h("span", { text: overlays.mode === "pass" ? "Fire detected up to this date" : "Fire detected" })) : null,
      h("p", { class: "note", text: "Darker is a bigger fall in HH over the dry season. It is not a grade of the land." }),
    ];
    return parts.filter((el): el is HTMLElement => el !== null);
  };

  let blocks: LegendRows | null = null;
  const api: MapLegend = {
    setBlocks(view) {
      blocks = view;
      if (!view) {
        root.replaceChildren(...fall());
        root.hidden = !entry?.ramp;
        return;
      }
      const rows = view.rows.map((row) => {
        const swatch = h("span", { class: "act-swatch", "aria-hidden": "true" });
        swatch.style.background = row.color;
        return h("div", { class: "map-legend-row" }, swatch, h("span", { text: row.label }));
      });
      root.replaceChildren(h("h3", { text: view.title }), ...rows, h("p", { class: "note", text: view.note }));
      root.hidden = false;
    },
  };
  api.setBlocks(null);
  overlays.onChange(() => {
    if (!blocks) api.setBlocks(null); // the fire row follows the slider and the layer switches
  });
  return api;
}
