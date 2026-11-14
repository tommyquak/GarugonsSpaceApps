// Written with Super Intelligence (SI) assistance.
// The opening story: seven beats that say what the problem is and what this map adds, before the
// tools appear. Five are real pictures (ground photographs and satellite images, credited from
// story/credits.json); the last two are the live map itself. It plays once on a first visit,
// can be skipped at any moment, and is replayed from "Story" in the header.
//
// Motion is kept to fades (in, between beats, out) and a thin line that fills while a beat
// shows. Under reduced motion nothing fades and nothing advances by itself.
//
// Sound is off until asked for. The clips are made by app/scripts/make_story_voice.py.
import type { Map as MapLibreMap } from "maplibre-gl";
import type { ActionsView } from "./actions";
import { asset, fetchJson } from "./data";
import { h } from "./dom";
import type { Overlays } from "./overlays";
import { reducedMotion, viewPadding } from "./view";

const BEAT_MS = 6500;
const SHORTEST_MS = 4500; // with sound, a beat still stays long enough to look at
const VOICE_LEAD_MS = 900; // the picture settles before the voice starts
const AFTER_VOICE_MS = 2100; // and the last word has room before the next beat
const FADE_MS = 450;
const SECOND_AT = 0.36; // how far into a two-picture beat the second picture takes over

interface Credit {
  author: string;
  licence: string;
  date: string;
  kind: string;
}

interface Beat {
  /** A file under story/, or a view of the live map. */
  image?: string;
  /** A second picture that takes over part way through the beat, with its own line under the heading. */
  then?: { image: string; sub: string };
  map?: "season" | "check";
  head: string;
  sub: (numbers: Numbers) => string;
  /** Colours to name under the text, for the map beats. */
  key?: { color: string; label: string }[];
}

type Numbers = Record<string, { value: number | string } | undefined>;

const percent = (numbers: Numbers, key: string): string | null => {
  const value = numbers[key]?.value;
  return typeof value === "number" ? `${Math.round(value * 100)}%` : null;
};

const BEATS: Beat[] = [
  { image: "fire", head: "Every dry season, drained peat in Borneo burns.", sub: () => "Sebangau, Central Kalimantan, September 2019." },
  {
    image: "canal",
    head: "Canals dug in the 1990s still drain it, and fire keeps coming back.",
    sub: (n) => {
      const share = percent(n, "fire_repeat_share_on_peat_west");
      return share
        ? `In our western study area, ${share} of this year's fire on peat fell on land that had burned in 2015, 2019 or 2023.`
        : "A drainage canal of the Mega Rice Project, Central Kalimantan.";
    },
  },
  {
    image: "smoke",
    head: "From space, a camera sees smoke. NISAR's radar sees the ground through it.",
    sub: () => "Southern Borneo on 19 September 2026, in true colour.",
    then: { image: "radar", sub: "The Sebangau area on 14 September 2026 by L-band radar: rivers, canals and forest edges." },
  },
  {
    image: "open",
    head: "A wetter surface sends back a stronger echo. As open peat dries, the echo falls.",
    sub: () => "A fall is a sign of drying, not a measurement of the water table. Clearing and farming can cause it too.",
  },
  {
    image: "burnt",
    head: "Dry peat is the peat that burns. It also sinks, and gives up its carbon.",
    sub: () => "Sebangau after fire, September 2019. Smoke from peat fires reaches cities across the region.",
  },
  {
    map: "season",
    head: "Through the dry season the radar echo fell along the canals, and fire built up on the same open peat.",
    sub: () => "Closed forest held steady.",
    key: [
      { color: "#bd8a4a", label: "The radar echo fell" },
      { color: "#de3626", label: "Fire detected" },
    ],
  },
  {
    map: "check",
    head: "The first rain brought the radar echo back on most land. On some, it did not.",
    sub: () => "There the ground still looks different from the start of the season, which can mean burnt vegetation or peat that is still dry. That is where a field team should look first.",
    key: [
      { color: "#ff3b30", label: "Fire on several days, and the vegetation echo is still low" },
      { color: "#ff9f0a", label: "No fire, and the ground echo is still low" },
      { color: "#f2d98a", label: "The echo is back near where it started" },
    ],
  },
];

export interface Opening {
  play(): void;
  /** Called with true when the story starts and false when it ends. */
  onRun(fn: (running: boolean) => void): void;
}

export function buildOpening(map: MapLibreMap, overlays: Overlays, actions: ActionsView, extent: [number, number, number, number] | null, stopSeason: () => void): Opening {
  let root: HTMLElement | null = null;
  const watchers: ((running: boolean) => void)[] = [];
  let credits: Record<string, Credit> = {};
  let numbers: Numbers = {};
  void fetchJson<Record<string, Credit>>("story/credits.json").then((found) => (credits = found ?? {}));
  void fetchJson<Numbers>("validation.json").then((found) => (numbers = found ?? {}));
  // Fetched ahead, so the first beat does not open on an empty frame.
  for (const beat of BEATS) {
    if (beat.image) new Image().src = asset(`story/${beat.image}.jpg`);
  }

  function play(): void {
    if (root) return;
    const app = document.getElementById("app");
    if (!app) return;
    const still = reducedMotion();
    let index = -1;
    let timer = 0;
    let swap = 0;
    let lead = 0;
    let second = 0;
    let front = 0;
    let sound = false;
    const voice = new Audio();
    voice.preload = "auto";

    const layers = [h("img", { class: "op-img", alt: "" }), h("img", { class: "op-img", alt: "" })];
    // One line per beat; each is also a way to jump to that beat.
    const bars = BEATS.map((beat, k) => {
      const bar = h("button", { type: "button", class: "op-bar", "aria-label": `Part ${k + 1} of ${BEATS.length}: ${beat.head}` }, h("i"));
      bar.addEventListener("click", () => show(k));
      return bar;
    });
    const head = h("h2", { class: "op-head" });
    const sub = h("p", { class: "op-sub" });
    const key = h("div", { class: "op-key" });
    const credit = h("p", { class: "op-credit" });
    const soundButton = h("button", { type: "button", class: "text-button op-sound", "aria-pressed": "false", text: "Sound off" });
    const skip = h("button", { type: "button", class: "text-button op-skip", text: "Skip" });
    const back = h("button", { type: "button", class: "text-button", text: "Back" });
    const withSound = h("button", { type: "button", class: "text-button", text: "Play with sound" });
    const next = h("button", { type: "button", class: "text-button op-next" });
    const text = h("div", { class: "op-text", "aria-live": "polite" }, head, sub, key);
    const made = h(
      "div",
      { id: "opening", role: "dialog", "aria-modal": "true", "aria-label": "Opening story" },
      h("div", { class: "op-media" }, ...layers),
      h("div", { class: "op-shade op-shade-image" }),
      h("div", { class: "op-shade op-shade-map" }),
      h("div", { class: "op-top" }, h("div", { class: "op-bars", role: "group", "aria-label": "Parts of the story" }, ...bars), soundButton, skip),
      h("div", { class: "op-foot" }, text, h("div", { class: "op-side" }, h("div", { class: "op-nav" }, back, withSound, next), credit)),
    );
    root = made;

    const showMap = (view: "season" | "check"): void => {
      // The caption takes the left of a wide view and the bottom of a narrow one; the map is framed in the rest.
      const wide = window.innerWidth >= 900;
      const room = wide
        ? { top: 96, bottom: 110, left: Math.min(760, Math.round(window.innerWidth * 0.5)), right: 40 }
        : { top: 80, bottom: Math.round(window.innerHeight * 0.52), left: 16, right: 16 };
      if (extent) map.fitBounds(extent, { padding: room, animate: false });
      if (view === "season") {
        actions.apply([], null);
        overlays.setPassFire(true);
        // The last dry-season pass but one: the fall near its deepest, before the rain.
        overlays.setStep(Math.max(0, overlays.steps.length - 3));
      } else {
        overlays.setMode("season");
        actions.apply(["map"], null);
      }
    };

    const creditOf = (image: string | undefined, onMap: boolean): string => {
      const by = image ? credits[image] : undefined;
      return by ? `${by.kind === "photograph" ? "Photo" : "Image"}: ${by.author}, ${by.date.slice(0, 4)}. ${by.licence}.` : onMap ? "The live map: NISAR, NASA FIRMS, Sentinel-2 mosaic 2016." : "";
    };
    const picture = (image: string): void => {
      front = 1 - front;
      layers[front].src = asset(`story/${image}.jpg`);
      layers[front].classList.add("is-on");
      layers[1 - front].classList.remove("is-on");
    };
    // The second picture of a beat takes over after `ms`, with its own line and credit.
    const follow = (beat: Beat, ms: number): void => {
      const then = beat.then;
      if (!then) return;
      window.clearTimeout(second);
      second = window.setTimeout(() => {
        picture(then.image);
        sub.textContent = then.sub;
        credit.textContent = creditOf(then.image, false);
      }, ms);
    };

    const fill = (beat: Beat): void => {
      head.textContent = beat.head;
      sub.textContent = beat.sub(numbers);
      key.replaceChildren(
        ...(beat.key ?? []).map((item) => {
          const swatch = h("span", { class: "act-swatch", "aria-hidden": "true" });
          swatch.style.background = item.color;
          return h("span", { class: "op-key-item" }, swatch, item.label);
        }),
      );
      credit.textContent = creditOf(beat.image, Boolean(beat.map));
    };

    // The line of the current beat fills over the time the beat will stay.
    const run = (ms: number): void => {
      window.clearTimeout(timer);
      const bar = bars[index];
      bar.classList.remove("is-now");
      bar.style.setProperty("--beat", `${ms}ms`);
      void bar.offsetWidth;
      bar.classList.add("is-now");
      timer = window.setTimeout(() => show(index + 1), ms);
    };

    function show(to: number): void {
      window.clearTimeout(timer);
      window.clearTimeout(swap);
      window.clearTimeout(lead);
      window.clearTimeout(second);
      voice.pause();
      const first = index < 0;
      index = Math.max(0, Math.min(BEATS.length - 1, to));
      const beat = BEATS[index];
      const lastBeat = index === BEATS.length - 1;
      made.classList.toggle("is-map", Boolean(beat.map));
      if (beat.image) {
        picture(beat.image);
      } else if (beat.map) {
        showMap(beat.map);
      }
      // The words fade out, change, and fade back in.
      if (first || still) fill(beat);
      else {
        made.classList.add("is-swap");
        swap = window.setTimeout(() => {
          fill(beat);
          made.classList.remove("is-swap");
        }, 260);
      }
      bars.forEach((bar, k) => {
        bar.classList.toggle("is-done", k < index || (k === index && (still || lastBeat)));
        bar.classList.remove("is-now");
      });
      back.disabled = index === 0;
      withSound.hidden = sound || index !== 0;
      next.textContent = lastBeat ? "Open the map" : "Next";
      if (sound) {
        const started = performance.now();
        voice.src = asset(`story/voice/beat-${index + 1}.mp3`);
        voice.onloadedmetadata = () => {
          if (!Number.isFinite(voice.duration)) return;
          if (!still && !lastBeat) run(Math.max(SHORTEST_MS, VOICE_LEAD_MS + voice.duration * 1000 + AFTER_VOICE_MS));
          follow(beat, VOICE_LEAD_MS + voice.duration * 1000 * SECOND_AT); // as the second sentence begins
        };
        voice.onended = () => {
          // The clock above already moves on; this only covers a clip whose length was not known.
          if (!still && !lastBeat && !bars[index].classList.contains("is-now")) run(Math.max(AFTER_VOICE_MS, SHORTEST_MS - (performance.now() - started)));
        };
        // No sound after all (blocked or missing): carry on silently at the usual pace.
        lead = window.setTimeout(() => {
          void voice.play().catch(() => {
            if (!still && !lastBeat) run(BEAT_MS);
          });
        }, VOICE_LEAD_MS);
      } else {
        // A beat with two pictures stays longer, and changes picture part way.
        const stay = beat.then ? BEAT_MS * 1.45 : BEAT_MS;
        if (!still && !lastBeat) run(stay);
        follow(beat, stay * SECOND_AT + 900);
      }
    }

    const setSound = (on: boolean): void => {
      sound = on;
      soundButton.setAttribute("aria-pressed", String(on));
      soundButton.textContent = on ? "Sound on" : "Sound off";
      if (!on) voice.pause();
      show(index); // the beat starts again, with or without its voice
    };

    const close = (): void => {
      window.clearTimeout(timer);
      window.clearTimeout(swap);
      window.clearTimeout(lead);
      window.clearTimeout(second);
      voice.pause();
      document.removeEventListener("keydown", onKey, true);
      document.removeEventListener("visibilitychange", onHide);
      root = null;
      // Whatever beat it was left on, the story ends on the map made for a first look: that is
      // set up underneath first, then the story fades away over it.
      overlays.setMode("season");
      actions.apply(["map"], null);
      if (extent) map.fitBounds(extent, { padding: viewPadding(), animate: false });
      app.classList.remove("is-story");
      app.removeAttribute("inert");
      made.classList.remove("is-in");
      window.setTimeout(() => made.remove(), still ? 0 : FADE_MS);
      for (const fn of watchers) fn(false);
      document.getElementById("btn-actions")?.focus({ preventScroll: true });
    };

    const onKey = (event: KeyboardEvent): void => {
      if (event.key === "Escape") close();
      else if (event.key === "ArrowRight") index === BEATS.length - 1 ? close() : show(index + 1);
      else if (event.key === "ArrowLeft") show(index - 1);
      else return;
      event.preventDefault();
    };
    const onHide = (): void => {
      if (document.hidden) {
        window.clearTimeout(timer); // a hidden tab does not run the story on
        window.clearTimeout(lead);
        voice.pause();
      } else if (index < BEATS.length - 1) show(index);
    };

    skip.addEventListener("click", close);
    back.addEventListener("click", () => show(index - 1));
    next.addEventListener("click", () => (index === BEATS.length - 1 ? close() : show(index + 1)));
    soundButton.addEventListener("click", () => setSound(!sound));
    withSound.addEventListener("click", () => setSound(true));
    document.addEventListener("keydown", onKey, true);
    document.addEventListener("visibilitychange", onHide);

    stopSeason();
    for (const fn of watchers) fn(true);
    app.classList.add("is-story");
    app.setAttribute("inert", "");
    document.body.append(made);
    show(0);
    void made.offsetWidth;
    made.classList.add("is-in"); // fades in over the app
    next.focus({ preventScroll: true });
  }

  return { play, onRun: (fn) => void watchers.push(fn) };
}
