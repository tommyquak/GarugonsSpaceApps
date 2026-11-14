// Written with Super Intelligence (SI) assistance.
// The season slider: steps through the radar passes in date order, both orbits interleaved.
import { passLabel } from "./data";
import { h } from "./dom";
import type { Overlays } from "./overlays";

const STEP_MS = 900;
const ICON_PLAY = '<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M4 2.5v11l9-5.5z" fill="currentColor"/></svg>';
const ICON_PAUSE = '<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M3.5 2.5h3v11h-3zM9.5 2.5h3v11h-3z" fill="currentColor"/></svg>';

export interface Season {
  stop(): void;
}

export function buildSeason(root: HTMLElement, overlays: Overlays): Season {
  const steps = overlays.steps;
  if (!steps.length) {
    root.hidden = true;
    return { stop: () => undefined };
  }
  const last = steps.length - 1;
  let timer: number | undefined;
  let playing = false;
  let loaded = 0;
  let preload: Promise<void> | undefined;

  const playButton = h("button", { type: "button", class: "icon-button" });
  const slider = h("input", { type: "range", min: 0, max: last, step: 1, value: 0, "aria-label": "Radar pass" });
  const wholeButton = h("button", { type: "button", class: "text-button", text: "Whole season" });
  const label = h("div", { class: "season-label", "aria-live": "polite" });
  const detail = h("div", { class: "season-detail" });
  root.replaceChildren(
    h("div", { class: "season-row" }, playButton, slider, wholeButton),
    h("div", { class: "season-text" }, label, detail),
  );

  const ensurePreload = (): Promise<void> => {
    preload ??= overlays.preloadPasses((done) => {
      loaded = done;
      render();
    });
    return preload;
  };

  const stop = (): void => {
    playing = false;
    window.clearInterval(timer);
    timer = undefined;
    render();
  };

  const play = async (): Promise<void> => {
    playing = true;
    render();
    await ensurePreload();
    if (!playing) return;
    if (overlays.mode !== "pass" || overlays.stepIndex >= last) overlays.setStep(0);
    timer = window.setInterval(() => {
      if (overlays.stepIndex >= last) stop();
      else overlays.setStep(overlays.stepIndex + 1);
    }, STEP_MS);
  };

  playButton.addEventListener("click", () => (playing ? stop() : void play()));
  slider.addEventListener("input", () => {
    if (playing) stop();
    void ensurePreload();
    overlays.setStep(Number(slider.value));
  });
  wholeButton.addEventListener("click", () => {
    if (playing) stop();
    overlays.setMode("season");
  });

  function render(): void {
    const total = steps.reduce((n, s) => n + s.layers.length, 0);
    const waiting = playing && loaded < total;
    playButton.innerHTML = playing ? ICON_PAUSE : ICON_PLAY;
    playButton.setAttribute("aria-label", playing ? "Pause" : "Play the season pass by pass");
    playButton.title = playing ? "Pause" : "Play the season";
    wholeButton.hidden = overlays.mode !== "pass";
    root.classList.toggle("is-pass", overlays.mode === "pass");
    if (overlays.mode === "pass") {
      const step = steps[overlays.stepIndex];
      slider.value = String(overlays.stepIndex);
      slider.setAttribute("aria-valuetext", passLabel(step));
      label.textContent = passLabel(step);
      detail.textContent = `Radar pass ${overlays.stepIndex + 1} of ${steps.length}. Colour: fall in HH since the start of the season.`;
    } else {
      label.textContent = "Whole dry season";
      detail.textContent = `Press play or drag the slider to step through ${steps.length} radar passes.`;
    }
    if (waiting) detail.textContent = `Loading radar passes, ${loaded} of ${total}.`;
  }

  overlays.onChange(render);
  render();
  return { stop };
}
