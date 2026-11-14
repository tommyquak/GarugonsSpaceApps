// Written with Super Intelligence (SI) assistance.
// Story mode: three steps, Dry, Burn and Rewet. Each one frames the map, switches the right
// layers on and says in two sentences what is on screen.
import type { Map as MapLibreMap } from "maplibre-gl";
import { formatDay, unionBounds, type LayerEntry } from "./data";
import { h } from "./dom";
import type { Overlays } from "./overlays";
import { reducedMotion, viewPadding } from "./view";

interface StoryStep {
  title: string;
  site: string | null; // the site to frame, or null for everything
  apply(): void;
  text(): string;
}

export interface Story {
  open(): void;
  isOpen(): boolean;
}

export function buildStory(
  root: HTMLElement,
  button: HTMLElement,
  map: MapLibreMap,
  overlays: Overlays,
  hooks: { stopPlayback(): void; onOpen(): void; onClose(): void },
): Story {
  const statics = overlays.statics;
  const fire = statics.filter((l) => l.kind === "fire");
  const recovery = statics.filter((l) => l.kind === "recovery");
  const only = (kinds: string[]): void => {
    for (const l of statics) {
      if (l.kind === "season" || l.kind === "fire" || l.kind === "recovery") overlays.setLayer(l.id, kinds.includes(l.kind));
    }
  };

  const steps: StoryStep[] = [
    {
      title: "Dry",
      site: null,
      apply: () => {
        only(["season"]);
        overlays.setMode("season");
      },
      text: () =>
        "Colour marks land where the L-band radar signal (HH) fell over the dry season on both orbits. A deeper red means a larger fall; it shows where to look and does not measure the water table.",
    },
    {
      title: "Burn",
      site: "east",
      apply: () => {
        only(["season", "fire"]);
        overlays.setMode("season");
      },
      text: () =>
        fire.length
          ? "Black marks land with a fire detection this year, from NASA FIRMS, on peat and off it. Compare it with the nearby radar echo fall; the map does not predict where fire will start."
          : "The fire layer is not loaded yet. When it is, this step will show this year's NASA FIRMS fire detections next to areas where the radar echo fell, on peat and off it.",
    },
    {
      title: "Rewet",
      site: "west",
      apply: () => {
        if (recovery.length) {
          only(["recovery"]);
          overlays.setMode("season");
        } else {
          only(["season"]); // hidden while a single pass is shown, back when the user leaves it
          if (overlays.steps.length) overlays.setStep(overlays.steps.length - 1);
        }
      },
      text: () => {
        const last = overlays.steps[overlays.steps.length - 1];
        if (recovery.length) {
          return "Blue marks land where the HH radar signal rose across the first rain. This shows a change in radar echo, not a measured water level.";
        }
        return last
          ? `The recovery layer is not loaded yet, so this is the latest radar pass, on ${formatDay(last.date)}. Land still coloured is still darker than at the start of the season.`
          : "The recovery layer is not loaded yet. When it is, this step will show where the radar signal rose again after the rain.";
      },
    },
  ];

  let current = -1;
  const tabs = steps.map((step, k) => {
    const tab = h("button", { type: "button", class: "text-button step", text: step.title });
    tab.addEventListener("click", () => go(k));
    return tab;
  });
  const text = h("p", { class: "story-text", "aria-live": "polite" });
  const back = h("button", { type: "button", class: "text-button small", text: "Back" });
  const next = h("button", { type: "button", class: "text-button small", text: "Next" });
  const close = h("button", { type: "button", class: "text-button small", text: "Close" });
  back.addEventListener("click", () => go(current - 1));
  next.addEventListener("click", () => go(current + 1));
  root.replaceChildren(
    h("div", { class: "panel-head" }, h("h2", { text: "Story" }), h("span", { class: "where" }), close),
    h("div", { class: "story-steps", role: "group", "aria-label": "Story steps" }, ...tabs),
    text,
    h("div", { class: "story-nav" }, back, next),
  );

  function frame(site: string | null): void {
    const pool: LayerEntry[] = overlays.layers.filter((l) => site === null || l.site === site);
    const bounds = unionBounds(pool.length ? pool : overlays.layers);
    if (bounds) map.fitBounds(bounds, { padding: viewPadding(), duration: reducedMotion() ? 0 : 1800, essential: true });
  }

  function go(index: number): void {
    current = Math.min(steps.length - 1, Math.max(0, index));
    hooks.stopPlayback();
    const step = steps[current];
    step.apply();
    frame(step.site);
    text.textContent = step.text();
    tabs.forEach((tab, k) => tab.setAttribute("aria-pressed", String(k === current)));
    back.disabled = current === 0;
    next.disabled = current === steps.length - 1;
  }

  const setOpen = (open: boolean): void => {
    root.hidden = !open;
    button.setAttribute("aria-pressed", String(open));
    if (open) {
      hooks.onOpen();
      go(current < 0 ? 0 : current);
    } else {
      hooks.onClose();
    }
  };
  button.addEventListener("click", () => setOpen(root.hidden));
  close.addEventListener("click", () => {
    setOpen(false);
    button.focus();
  });
  root.hidden = true;
  return { open: () => setOpen(true), isOpen: () => !root.hidden };
}
