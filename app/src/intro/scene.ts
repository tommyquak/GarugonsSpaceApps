// Written with Super Intelligence (SI) assistance.
// The operations room around the wall screen, drawn in code: no image files and no
// third-party assets. It is a made-up room.
//
// The room box is 1/START_SCALE times the size of the app, and the app sits in a hole in its
// back wall. In the room's own 1000 x 1000 drawing units that hole is the square from
// (320, 240) to (680, 600); intro.css places the box so the hole lies exactly over #app.
//
// Greys only. The warm, blue and violet families belong to the map (docs/DESIGN.md). The
// console screens carry plain shapes, never digits, axes or anything that reads as a result.
// The four side screens on the wall are the exception: wall.ts lays the real ontology over
// them, read from the app's own data files, with the class colours the map uses.

import { fillWall } from "./wall";

type Kind = "lines" | "grid" | "ring" | "bands";
const KINDS: Kind[] = ["lines", "grid", "bands", "ring"];
const n = (value: number): string => value.toFixed(1);

/** One lit screen with a few grey shapes on it. `seed` only varies the pattern. */
function monitor(x: number, y: number, w: number, h: number, kind: Kind, seed: number): string {
  const pad = Math.min(w, h) * 0.12;
  const ix = x + pad;
  const iy = y + pad;
  const iw = w - 2 * pad;
  const ih = h - 2 * pad;
  let shapes = "";
  if (kind === "lines") {
    for (let k = 0; k < 5; k++) {
      const share = 0.4 + 0.12 * ((k * 7 + seed * 3) % 5);
      shapes += `<rect x="${n(ix)}" y="${n(iy + (k * ih) / 5)}" width="${n(iw * share)}" height="${n(ih / 11)}" fill-opacity="${k === 0 ? 0.8 : 0.45}"/>`;
    }
  } else if (kind === "grid") {
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 4; c++) {
        const opacity = 0.2 + 0.2 * ((c + r * 2 + seed) % 3);
        shapes += `<rect x="${n(ix + (c * iw) / 4)}" y="${n(iy + (r * ih) / 3)}" width="${n(iw / 4.6)}" height="${n(ih / 3.6)}" fill-opacity="${n(opacity)}"/>`;
      }
    }
  } else if (kind === "bands") {
    shapes += `<rect x="${n(ix)}" y="${n(iy)}" width="${n(iw)}" height="${n(ih * 0.5)}" fill-opacity="0.3"/>`;
    shapes += `<rect x="${n(ix)}" y="${n(iy + ih * 0.6)}" width="${n(iw * 0.62)}" height="${n(ih * 0.14)}" fill-opacity="0.6"/>`;
    shapes += `<rect x="${n(ix)}" y="${n(iy + ih * 0.84)}" width="${n(iw * 0.4)}" height="${n(ih * 0.14)}" fill-opacity="0.4"/>`;
  } else {
    shapes += `<ellipse cx="${n(x + w / 2)}" cy="${n(iy + ih * 0.42)}" rx="${n(iw * 0.26)}" ry="${n(ih * 0.36)}" fill="none" stroke="#9aa3ad" stroke-opacity="0.7" stroke-width="3"/>`;
    shapes += `<rect x="${n(ix + iw * 0.2)}" y="${n(iy + ih * 0.9)}" width="${n(iw * 0.6)}" height="${n(ih / 11)}" fill-opacity="0.45"/>`;
  }
  return (
    `<rect x="${n(x - 3)}" y="${n(y - 3)}" width="${n(w + 6)}" height="${n(h + 6)}" fill="#07090b"/>` +
    `<rect x="${n(x)}" y="${n(y)}" width="${n(w)}" height="${n(h)}" fill="#232a32"/>` +
    `<g fill="#9aa3ad">${shapes}</g>`
  );
}

/** A row of console screens, left to right. */
function row(x0: number, step: number, count: number, y: number, w: number, h: number, seed: number): string {
  let out = "";
  for (let k = 0; k < count; k++) out += monitor(x0 + k * step, y, w, h, KINDS[(k + seed) % KINDS.length], k + seed);
  return out;
}

const HOLE = "M320 240H680V600H320Z";

const ROOM = `
<svg class="intro-layer" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true">
  <defs>
    <radialGradient id="intro-dim" cx="0.5" cy="0.42" r="0.75">
      <stop offset="0.35" stop-color="#000" stop-opacity="0"/>
      <stop offset="1" stop-color="#000" stop-opacity="0.62"/>
    </radialGradient>
  </defs>
  <path fill="#12151a" fill-rule="evenodd" d="M0 0H1000V1000H0Z ${HOLE}"/>
  <path fill="#0c0f12" d="M0 0H1000L920 80H80Z"/>
  <path fill="#0f1215" d="M0 0L80 80V660L0 760Z"/>
  <path fill="#0f1215" d="M1000 0L920 80V660L1000 760Z"/>
  <path fill="#0a0c0f" d="M0 760L80 660H920L1000 760V1000H0Z"/>
  <path fill="#161a1f" fill-rule="evenodd" d="M80 80H920V660H80Z ${HOLE}"/>
  <path fill="#2a3038" d="M300 30H460L450 52H310Z M540 30H700L690 52H550Z"/>
  <path fill="#e9e6df" fill-opacity="0.06" fill-rule="evenodd" d="M286 206H714V634H286Z ${HOLE}"/>
  <path fill="#e9e6df" fill-opacity="0.045" d="M330 660H670L770 1000H230Z"/>
  ${monitor(118, 262, 172, 150, "lines", 1)}
  ${monitor(118, 440, 172, 140, "grid", 2)}
  ${monitor(710, 262, 172, 150, "ring", 0)}
  ${monitor(710, 440, 172, 140, "bands", 3)}
  <rect x="314" y="234" width="372" height="372" fill="none" stroke="#2a3038" stroke-width="12"/>
  <rect x="307" y="227" width="386" height="386" fill="none" stroke="#07090b" stroke-width="3"/>
  ${row(150, 90, 8, 646, 66, 54, 0)}
  <path fill="#0b0d10" d="M120 700H880L900 730H100Z"/>
  <path stroke="#2a3038" stroke-width="2" d="M120 700H880"/>
  <path fill="url(#intro-dim)" fill-rule="evenodd" d="M0 0H1000V1000H0Z ${HOLE}"/>
</svg>`;

const NEAR = `
<svg class="intro-layer" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true">
  ${row(56, 130, 7, 722, 104, 80, 1)}
  <path fill="#090b0d" d="M30 802H970L990 850H10Z"/>
  <path stroke="#2a3038" stroke-width="2" d="M30 802H970"/>
  ${row(18, 196, 5, 880, 176, 130, 2)}
</svg>`;

// Someone at a console, seen from behind: head, shoulders and a chair back. Not a likeness.
function person(left: number, top: number, width: number, height: number): string {
  return `
<svg class="intro-person" style="left:${left}%;top:${top}%;width:${width}%;height:${height}%" viewBox="0 0 120 150" preserveAspectRatio="xMidYMax meet" aria-hidden="true">
  <g stroke="#e9e6df" stroke-opacity="0.22" stroke-width="2" stroke-linejoin="round">
    <path fill="#0b0d10" d="M18 150Q20 86 60 80Q100 86 102 150Z"/>
    <circle fill="#0b0d10" cx="60" cy="52" r="24"/>
    <rect fill="#050607" x="22" y="96" width="76" height="60" rx="14"/>
  </g>
</svg>`;
}

// Signs name the made-up team and the real source of the radar data, in words only.
const SIGN = `
<div class="intro-sign">
  <strong>Team Garugons</strong>
  <span>Peatland observation room</span>
  <span>Data source: NASA-ISRO NISAR L-band radar</span>
</div>`;

export interface Scene {
  /** Everything drawn around the app. Goes inside the stage, after #app. */
  room: HTMLElement;
  /** The near consoles, which pass the camera faster than the walls do. */
  foreground: HTMLElement[];
  /** A clear button lying over the wall screen, so the screen itself can be clicked. */
  screen: HTMLButtonElement;
}

export function buildScene(): Scene {
  const room = document.createElement("div");
  room.className = "intro-room";
  room.setAttribute("aria-hidden", "true");
  // Fixed text from this file.
  room.innerHTML =
    ROOM +
    SIGN +
    person(73.5, 62.5, 7, 10) +
    person(19, 62.5, 7, 10) +
    `<div class="intro-layer intro-fg">${NEAR}${person(27, 71, 12, 15)}${person(60, 71, 12, 15)}</div>` +
    `<button type="button" class="intro-screen" tabindex="-1"></button>`;
  void fillWall(room);
  const screen = room.querySelector<HTMLButtonElement>(".intro-screen");
  if (!screen) throw new Error("intro: no screen");
  return { room, foreground: [...room.querySelectorAll<HTMLElement>(".intro-fg")], screen };
}
