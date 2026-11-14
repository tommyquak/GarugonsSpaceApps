// Written with Super Intelligence (SI) assistance.
// The four side screens on the wall of the intro room show the real ontology, not decoration:
// the sources, the decision graph, how many 1 km blocks fell in each class, and one rule
// spelled out. Everything is read from blocks/ontology.json and blocks/index.json, the same
// files the "How it decides" view uses, so the wall cannot drift from the app.
//
// It loads on its own and never holds the intro up. If a file is missing, the grey shapes
// drawn by scene.ts stay as they are.
//
// The screens are displays, not controls: the one way into the dashboard is the main screen,
// so that every visitor comes in through the opening story.
import { actionColor, NO_ACTION } from "../actions/colors";
import { fetchJson } from "../data";
import { buildGraph, isOntology, ruleTerms, type Ontology } from "../ontology/model";

interface BlockIndex {
  sites: { id: string; blocks: number; actions: Record<string, number> }[];
}

// The side screens, in the room's own box: left, top, width, height in percent (scene.ts draws
// them at these places in its 1000 by 1000 units).
const SCREENS = { sources: [11.8, 26.2, 17.2, 15], graph: [11.8, 44, 17.2, 14], classes: [71, 26.2, 17.2, 15], rule: [71, 44, 17.2, 14] } as const;
const W = 240;
const H = 130;
const INK = "#e9e6df";
const MUTED = "#9aa3ad";
const FAINT = "#5b6570";

const esc = (text: string): string => text.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c] ?? c);
const clip = (text: string, most: number): string => (text.length > most ? text.slice(0, most - 1).trimEnd() + "…" : text);
const heading = (text: string): string => `<text x="10" y="17" font-size="9" letter-spacing="1.2" fill="${MUTED}">${esc(text.toUpperCase())}</text>`;

/** One screen: an SVG of fixed proportions laid over a grey monitor. */
function screen(name: keyof typeof SCREENS, label: string, body: string): HTMLElement {
  const [left, top, width, height] = SCREENS[name];
  const el = document.createElement("div");
  el.className = "intro-wall";
  el.dataset.screen = name; // intro.css moves the screen to its place in the photo room
  el.style.cssText = `left:${left}%;top:${top}%;width:${width}%;height:${height}%`;
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${esc(label)}" font-family="inherit">${body}</svg>`;
  return el;
}

/** The datasets everything starts from. */
function sources(ontology: Ontology): string {
  const step = (H - 30) / Math.max(ontology.sources.length, 1);
  const rows = ontology.sources.map((source, k) => {
    const y = 34 + k * step;
    return (
      `<circle cx="14" cy="${y - 3.5}" r="3" fill="${INK}" fill-opacity="0.75"/>` +
      `<text x="24" y="${y}" font-size="10" fill="${INK}">${esc(clip(source.title, 40))}</text>`
    );
  });
  return heading("Sources") + rows.join("");
}

/** The whole decision graph, small: sources, observations, states, classes, and their links. */
function graph(ontology: Ontology): string {
  const built = buildGraph(ontology, null);
  const columns = [0, 1, 2, 3].map((column) => built.nodes.filter((node) => node.column === column));
  const at = new Map<string, [number, number]>();
  columns.forEach((nodes, column) => {
    nodes.forEach((node, k) => at.set(node.key, [22 + column * 65, 16 + ((k + 0.5) * (H - 40)) / nodes.length]));
  });
  let out = "";
  for (const edge of built.edges) {
    const from = at.get(edge.from);
    const to = at.get(edge.to);
    if (!from || !to) continue;
    const mid = (from[0] + to[0]) / 2;
    out += `<path d="M${from[0] + 5} ${from[1]}C${mid} ${from[1]} ${mid} ${to[1]} ${to[0] - 5} ${to[1]}" fill="none" stroke="${MUTED}" stroke-opacity="${edge.kind === "strengthens" ? 0.18 : 0.4}" stroke-width="0.8"${edge.negated ? ' stroke-dasharray="3 2"' : ""}/>`;
  }
  for (const node of built.nodes) {
    const place = at.get(node.key);
    if (!place) continue;
    const fill = node.kind === "action" ? actionColor(node.action ?? NO_ACTION) : INK;
    out += `<rect x="${place[0] - 5}" y="${place[1] - 2.6}" width="10" height="5.2" rx="1.6" fill="${fill}" fill-opacity="${node.kind === "action" ? 1 : 0.8}"/>`;
  }
  ["sources", "observations", "states", "classes"].forEach((name, column) => {
    out += `<text x="${22 + column * 65}" y="${H - 8}" font-size="8.5" text-anchor="middle" fill="${MUTED}">${name}</text>`;
  });
  return out;
}

/** How many 1 km blocks fell in each class, over every site. */
function classes(ontology: Ontology, index: BlockIndex): string {
  const count = (id: string): number => index.sites.reduce((sum, site) => sum + (site.actions[id] ?? 0), 0);
  const shown = ontology.actions.filter((action) => action.id !== NO_ACTION);
  const most = Math.max(1, ...shown.map((action) => count(action.id)));
  const step = (H - 34) / Math.max(shown.length, 1);
  const rows = shown.map((action, k) => {
    const y = 36 + k * step;
    const n = count(action.id);
    return (
      `<text x="10" y="${y}" font-size="10" fill="${INK}">${esc(clip(action.title, 34))}</text>` +
      `<text x="${W - 10}" y="${y}" font-size="10" text-anchor="end" fill="${INK}">${n.toLocaleString("en-GB")}</text>` +
      `<rect x="10" y="${y + 5}" width="${W - 20}" height="5" rx="2.5" fill="${FAINT}" fill-opacity="0.35"/>` +
      `<rect x="10" y="${y + 5}" width="${Math.max(3, ((W - 20) * n) / most)}" height="5" rx="2.5" fill="${actionColor(action.id)}"/>`
    );
  });
  return heading("1 km blocks by class") + rows.join("");
}

/**
 * One rule from the decision table, as an example: the class first, then the states that must be
 * true for a block to get it, then the ones that must not be.
 */
function rule(ontology: Ontology): string {
  const action = ontology.actions.find((a) => a.id === "fell_still_low") ?? ontology.actions.find((a) => a.id !== NO_ACTION);
  if (!action) return "";
  const titles = new Map(ontology.states.map((state) => [state.id, state.title]));
  const terms = ruleTerms(action.rule, [...titles.keys()]);
  const needed = terms.filter((term) => !term.negated);
  const barred = terms.filter((term) => term.negated);
  const lines = 2 + needed.length + (barred.length ? 1 + barred.length : 0); // the class, a label, the states, a label, the states
  const step = Math.min(15, (H - 30) / Math.max(lines, 1));
  const size = Math.min(10, step * 0.72);
  let y = 22 + step;
  let out = heading("How a block gets its class: one example");
  out +=
    `<rect x="12" y="${y - 7.5}" width="8" height="8" rx="2" fill="${actionColor(action.id)}"/>` +
    `<text x="26" y="${y}" font-size="${size}" font-weight="600" fill="${INK}">${esc(clip(action.title, 38))}</text>`;
  const label = (text: string): void => {
    y += step;
    out += `<text x="12" y="${y}" font-size="${size * 0.88}" fill="${MUTED}">${esc(text)}</text>`;
  };
  const state = (id: string): void => {
    y += step;
    out += `<text x="20" y="${y}" font-size="${size}" fill="${INK}">${esc(clip(titles.get(id) ?? id, 38))}</text>`;
  };
  label(needed.length === 1 ? "A 1 km block gets this class when this is true" : "A 1 km block gets this class when all of these are true");
  needed.forEach((term) => state(term.state));
  if (barred.length) {
    label(barred.length === 1 ? "and this is not" : "and none of these is");
    barred.forEach((term) => state(term.state));
  }
  return out;
}

/** Puts the ontology on the wall of `room` once its two files have loaded. Never throws. */
export async function fillWall(room: HTMLElement): Promise<void> {
  try {
    const [ontology, index] = await Promise.all([fetchJson<unknown>("blocks/ontology.json"), fetchJson<BlockIndex>("blocks/index.json")]);
    if (!isOntology(ontology) || !room.isConnected) return;
    const front = room.querySelector(".intro-fg");
    const add = (el: HTMLElement): void => void (front ? room.insertBefore(el, front) : room.append(el));
    add(screen("sources", "The data sources the classes are built from", sources(ontology)));
    add(screen("graph", "The decision graph: sources, observations, states and classes", graph(ontology)));
    add(screen("rule", "How a block gets its class: one rule from the decision table, as an example", rule(ontology)));
    if (index?.sites?.length) add(screen("classes", "Number of 1 km blocks in each class", classes(ontology, index)));
  } catch {
    // The grey shapes stay.
  }
}
