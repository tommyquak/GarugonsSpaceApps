// Written with Super Intelligence (SI) assistance.
// A skippable way in: the view opens on a made-up peatland observation room, and the large
// screen on its far wall is this app itself, shrunk. The view holds there until the visitor
// clicks that screen or "Enter dashboard"; then the camera moves through the screen and the
// room is thrown away. "Skip to map" does the same with no camera move. Clicking one of the
// side screens on the wall (wall.ts) moves the camera into that screen instead, then opens the
// view it shows.
//
// How it stays out of the map's way:
//   - #app and the room share one parent, the stage, and only the stage is scaled. The app is
//     never copied or redrawn, so what is on the wall screen is the live map.
//   - Nothing here calls the map, reads the layers or writes the address. main.ts starts the
//     map on its own, without waiting for this.
//   - Every way out (the end of the move, Skip, Escape, an error, the tab going to the
//     background during the move, a time limit on the move) runs the same finish(), which
//     leaves the page as if the intro had never run.
import { h } from "../dom";
import { parseLink } from "../link";
import { reducedMotion, WIDE } from "../view";
import { buildScene } from "./scene";
import "./intro.css";

const SEEN_KEY = "dsw-intro-seen";
const START_SCALE = 0.36; // used only if the value in intro.css cannot be read
const LINE = "Come see what this season\u2019s radar found over Borneo.";

let finishCurrent: (() => void) | null = null;

/** The stage is made once and kept: moving #app again later would move a live map. */
function stage(): HTMLElement | null {
  const existing = document.getElementById("intro-stage");
  if (existing) return existing;
  const app = document.getElementById("app");
  if (!app?.parentNode) return null;
  const made = h("div", { id: "intro-stage" });
  app.parentNode.insertBefore(made, app);
  made.append(app);
  return made;
}

/** A link someone was sent names a view; it opens on that view, with no intro in front. */
function hasSharedView(): boolean {
  const state = parseLink(window.location.hash);
  return Boolean(state.view || state.layers || state.pass || state.place);
}

/** True once per browser session. Without session storage the intro is not shown at all. */
function firstVisit(): boolean {
  try {
    if (window.sessionStorage.getItem(SEEN_KEY)) return false;
    window.sessionStorage.setItem(SEEN_KEY, "1");
    return true;
  } catch {
    return false;
  }
}

/** Whether "Replay intro" should be offered: not when the device asks for reduced motion. */
export function canReplayIntro(): boolean {
  return !reducedMotion() && typeof Element.prototype.animate === "function";
}

/** Called once at startup, before the map is made. Never throws and never waits. */
export function maybePlayIntro(): void {
  try {
    if (!stage()) return;
    if (hasSharedView() || !firstVisit()) return;
    playIntro();
  } catch {
    finishCurrent?.();
  }
}

/** Shows the intro now. Does nothing under reduced motion or while one is already up. */
export function playIntro(): void {
  if (finishCurrent || !canReplayIntro()) return;
  const root = stage();
  const app = document.getElementById("app");
  if (!root || !app) return;

  const animations: Animation[] = [];
  const enter = h("button", { type: "button", class: "text-button intro-enter", text: "Enter dashboard" });
  const skip = h("button", { type: "button", class: "text-button intro-skip", text: "Skip to map" });
  const line = h("p", { class: "intro-line", text: LINE });
  const card = h("div", { class: "intro-card" }, line, h("div", { class: "intro-buttons" }, enter, skip));
  const ui = h(
    "div",
    { class: "intro-ui", role: "dialog", "aria-modal": "true", "aria-label": "Introduction: a made-up observation room with this map on its wall screen" },
    h("p", { class: "intro-mark", text: "Illustrative scene, made with Super Intelligence (SI)" }),
    card,
  );
  let room: HTMLElement | null = null;
  let foreground: HTMLElement[] = [];
  let timer = 0;
  let moving = false;
  let openAfter: string | null = null; // the view a clicked wall screen leads to

  const onKey = (event: KeyboardEvent): void => {
    if (event.key === "Escape") {
      event.preventDefault();
      finish();
    } else if (event.key === "Tab") {
      // The two buttons are the only controls while the intro is up; focus stays on them.
      event.preventDefault();
      (document.activeElement === enter ? skip : enter).focus();
    }
  };
  const onHide = (): void => {
    if (document.hidden && moving) finish(); // a background tab pauses the move; do not strand the map
  };

  let done = false;
  function finish(): void {
    if (done) return;
    done = true;
    finishCurrent = null;
    window.clearTimeout(timer);
    document.removeEventListener("keydown", onKey, true);
    document.removeEventListener("visibilitychange", onHide);
    root?.classList.remove("intro-playing"); // the stage is back at full size
    for (const animation of animations) animation.cancel();
    room?.remove();
    ui.remove();
    app?.removeAttribute("inert");
    // The handoff: the story is one key press away. It is not opened here, because opening it
    // moves the map and switches layers.
    const story = ["btn-story", "tab-story"].map((id) => document.getElementById(id)).find((el) => el && el.offsetParent !== null);
    if (story) {
      story.focus({ preventScroll: true });
      story.classList.add("intro-ready");
      window.setTimeout(() => story.classList.remove("intro-ready"), 1700);
    }
    // A wall screen was clicked: press the header button for its view, as a visitor would.
    if (openAfter) {
      const ids = openAfter === "check" ? ["btn-actions", "tab-actions"] : ["btn-how", "btn-actions", "tab-actions"];
      const button = ids.map((id) => document.getElementById(id)).find((el) => el && el.offsetParent !== null);
      if (button && button.getAttribute("aria-pressed") !== "true") button.click();
    }
  }
  finishCurrent = finish;

  /** Where the camera starts: the scale of the stage and the point it is scaled about, both set in intro.css. */
  function startView(): { scale: number; x: number; y: number } {
    const style = window.getComputedStyle(root!);
    const scale = Number(style.getPropertyValue("--intro-scale")) || START_SCALE;
    const [x, y] = style.transformOrigin.split(" ").map(parseFloat);
    return { scale, x: Number.isFinite(x) ? x : window.innerWidth * 0.5, y: Number.isFinite(y) ? y : window.innerHeight * 0.375 };
  }

  /** The camera move into one side screen of the wall: it grows until it fills the view. */
  function goInto(wall: HTMLElement): void {
    if (done || moving) return;
    moving = true;
    try {
      const duration = 1300;
      const easing = "cubic-bezier(0.6, 0, 0.3, 1)";
      timer = window.setTimeout(finish, duration + 900); // the move can never outstay its time
      enter.disabled = true;
      skip.focus({ preventScroll: true });
      // The stage is scaled about a fixed point (intro.css). Scale it further and shift it, so
      // the middle of the clicked screen ends in the middle of the view.
      const box = wall.getBoundingClientRect();
      const view = { w: window.innerWidth, h: window.innerHeight };
      const origin = startView();
      const grow = Math.min(view.w / box.width, view.h / box.height) * 0.88;
      const dx = view.w / 2 - origin.x - grow * (box.left + box.width / 2 - origin.x);
      const dy = view.h / 2 - origin.y - grow * (box.top + box.height / 2 - origin.y);
      const push = root!.animate(
        [{ transform: `translate(0px, 0px) scale(${origin.scale})` }, { transform: `translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px) scale(${(origin.scale * grow).toFixed(4)})` }],
        { duration, easing, fill: "forwards" },
      );
      animations.push(push);
      animations.push(ui.animate([{ opacity: 1 }, { opacity: 0, offset: 0.4 }, { opacity: 0 }], { duration, fill: "forwards" }));
      // The screen has filled the view: dip to dark, swap the room for the app with that view open, and come back.
      push.addEventListener("finish", () => {
        const veil = h("div", { class: "intro-veil" });
        document.body.append(veil);
        const dip = veil.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 180, fill: "forwards" });
        const lift = (): void => {
          finish();
          const out = veil.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 380, fill: "forwards" });
          out.addEventListener("finish", () => veil.remove());
          window.setTimeout(() => veil.remove(), 600);
        };
        dip.addEventListener("finish", lift);
        window.setTimeout(() => !done && lift(), 400);
      });
    } catch {
      finish();
    }
  }

  /** The one camera move, through the wall screen. */
  function go(): void {
    if (done || moving) return;
    moving = true;
    try {
      const duration = window.matchMedia(WIDE).matches ? 1900 : 1500;
      const easing = "cubic-bezier(0.6, 0, 0.3, 1)";
      timer = window.setTimeout(finish, duration + 400); // the move can never outstay its time
      enter.disabled = true;
      skip.focus({ preventScroll: true });
      const push = root!.animate([{ transform: `scale(${startView().scale})` }, { transform: "scale(1)" }], { duration, easing, fill: "forwards" });
      animations.push(push);
      for (const el of foreground) {
        animations.push(el.animate([{ transform: "scale(1)", opacity: 1 }, { transform: "scale(2.4)", opacity: 0, offset: 0.75 }, { transform: "scale(2.4)", opacity: 0 }], { duration, easing, fill: "forwards" }));
      }
      animations.push(ui.animate([{ opacity: 1 }, { opacity: 0, offset: 0.5 }, { opacity: 0 }], { duration, fill: "forwards" }));
      push.addEventListener("finish", finish);
    } catch {
      finish();
    }
  }

  try {
    const scene = buildScene();
    room = scene.room;
    foreground = scene.foreground;

    app.setAttribute("inert", ""); // the map cannot be reached by key or pointer underneath
    root.classList.add("intro-playing");
    root.append(room);
    document.body.append(ui);

    enter.addEventListener("click", go);
    scene.screen.addEventListener("click", go);
    scene.room.addEventListener("click", (event) => {
      const wall = (event.target as Element | null)?.closest<HTMLElement>(".intro-wall");
      if (!wall) return;
      openAfter = wall.dataset.open ?? null;
      goInto(wall);
    });
    skip.addEventListener("click", finish);
    document.addEventListener("keydown", onKey, true);
    document.addEventListener("visibilitychange", onHide);
    enter.focus({ preventScroll: true });
  } catch {
    finish();
  }
}
