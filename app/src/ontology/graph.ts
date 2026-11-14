// Written with Super Intelligence (SI) assistance.
// Draws the evidence graph in SVG: four columns, left to right, Sources, Observations, States,
// Action, with a curved link wherever the ontology says one thing feeds another. With a block
// the nodes carry its values and the links that carried evidence for its action are lit;
// without one the same drawing is the schema of the vocabulary.
import { h } from "../dom";
import { WIDE } from "../view";
import { buildGraph, formatValue, ruleTerms, sentences, yesNo, type BlockProps, type GraphEdge, type GraphNode, type Ontology } from "./model";

const SVG = "http://www.w3.org/2000/svg";
const SANS = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";

// Left edge and width of each column, in drawing units (one unit is a pixel at full size).
const COLUMNS = [
  { x: 0, w: 176, title: "Sources", type: "Source" },
  { x: 216, w: 336, title: "Observations", type: "Observation" },
  { x: 592, w: 196, title: "States", type: "State" },
  { x: 828, w: 152, title: "Action", type: "Action" },
];
const WIDTH = 980;
const HEAD = 26; // room for the column titles
const GAP = 6;
const PAD_X = 10;
const PAD_Y = 7;
const STRIPE = 3;
const LINE = 15;
const SMALL = 13;
const PILL_W = 36;

function svg<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number> = {}, text?: string): SVGElementTagNameMap[K] {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  if (text !== undefined) el.textContent = text;
  return el;
}

let pen: CanvasRenderingContext2D | null | undefined;

function textWidth(text: string, size: number, weight: number, mono = false): number {
  if (pen === undefined) pen = document.createElement("canvas").getContext("2d");
  if (!pen) return text.length * size * (mono ? 0.62 : 0.56);
  pen.font = `${weight} ${size}px ${mono ? MONO : SANS}`;
  return pen.measureText(text).width;
}

// Breaks a text into lines no wider than `width`, at spaces.
function wrap(text: string, width: number, size: number, weight: number, mono = false): string[] {
  const lines: string[] = [];
  let line = "";
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const next = line ? `${line} ${word}` : word;
    if (line && textWidth(next, size, weight, mono) > width) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines;
}

interface Box {
  node: GraphNode;
  x: number;
  y: number;
  w: number;
  h: number;
  title: string[];
  sub: string[];
  rule: string[];
  el?: SVGGElement;
}

// Works out the lines and the height of one node card.
function measure(node: GraphNode, schema: boolean): Box {
  const column = COLUMNS[node.column];
  const inner = column.w - STRIPE - 2 * PAD_X;
  let titleWidth = inner;
  const strong = node.kind === "action" && !node.dimmed;
  if (node.kind === "observation" && node.value) titleWidth -= textWidth(node.value, 13, 650) + 10;
  if (node.kind === "state" && !schema) titleWidth -= PILL_W + 8;
  const title = wrap(node.title, titleWidth, strong ? 13 : 12, strong || node.kind === "source" ? 600 : 500);
  const sub = node.sub ? wrap(node.sub, inner, 11, 400) : node.note ? [node.note] : [];
  // Rule text sits inside the node in the schema view, and always for the two extra conditions.
  const showRule = node.rule && (schema || node.kind === "condition");
  const rule = showRule ? wrap(node.rule ?? "", inner, 10.5, 400, true) : [];
  const height = 2 * PAD_Y + title.length * LINE + sub.length * SMALL + rule.length * SMALL + (rule.length ? 3 : 0);
  return { node, x: column.x, y: 0, w: column.w, h: Math.max(height, 30), title, sub, rule };
}

function describe(node: GraphNode): string {
  const kind = node.kind === "condition" ? "Extra condition" : COLUMNS[node.column].type;
  const verdict = node.kind === "state" && node.truth !== undefined ? `: ${yesNo(node.truth)}` : node.kind === "observation" && node.value ? `: ${node.value}` : "";
  const chosen = node.chosen ? " (the action of this block)" : node.dimmed ? " (not chosen)" : "";
  return `${kind}: ${node.title}${verdict}${chosen}. ${sentences(node.detail)}`;
}

function drawNode(box: Box, schema: boolean, color: (action: string) => string): SVGGElement {
  const { node } = box;
  const classes = ["g-node", `g-${node.kind}`, node.chosen ? "is-chosen" : "", node.dimmed ? "is-dimmed" : "", node.truth === true ? "is-yes" : ""].filter(Boolean);
  const g = svg("g", { class: classes.join(" "), "data-key": node.key, tabindex: 0, role: "img", "aria-label": describe(node), transform: `translate(${box.x}, ${box.y})` });
  // The browser's own tooltip: the rule of a state or an action, else the full title.
  g.append(svg("title", {}, node.rule ? `${node.title}. Rule: ${node.rule}` : node.title));
  g.append(svg("rect", { class: "g-card", x: 0.5, y: 0.5, width: box.w - 1, height: box.h - 1, rx: 6 }));
  const stripe = svg("rect", { class: "g-stripe", x: 0.5, y: 0.5, width: node.chosen ? STRIPE + 3 : STRIPE, height: box.h - 1, rx: 1.5 });
  if (node.action && (node.chosen || schema)) stripe.style.fill = color(node.action);
  g.append(stripe);

  const left = STRIPE + PAD_X + (node.chosen ? 3 : 0);
  let y = PAD_Y + 11;
  for (const line of box.title) {
    g.append(svg("text", { class: "g-title", x: left, y }, line));
    y += LINE;
  }
  for (const line of box.sub) {
    g.append(svg("text", { class: "g-sub", x: left, y: y - 1 }, line));
    y += SMALL;
  }
  if (box.rule.length) y += 3;
  for (const line of box.rule) {
    g.append(svg("text", { class: "g-rule", x: left, y: y - 1 }, line));
    y += SMALL;
  }
  if (node.kind === "observation" && node.value) {
    const none = node.value === formatValue(undefined, null);
    g.append(svg("text", { class: `g-value${schema || none ? " is-quiet" : ""}`, x: box.w - PAD_X, y: box.h / 2 + 4.5, "text-anchor": "end" }, node.value));
  }
  if (node.kind === "state" && !schema) {
    const px = box.w - PAD_X - PILL_W;
    const py = box.h / 2 - 9;
    g.append(svg("rect", { class: "g-pill", x: px, y: py, width: PILL_W, height: 18, rx: 9 }));
    g.append(svg("text", { class: "g-pill-text", x: px + PILL_W / 2, y: py + 13, "text-anchor": "middle" }, node.truth === null ? "?" : yesNo(node.truth)));
  }
  return g;
}

// A curved link from the right side of one card to the left side of the next.
function drawEdge(edge: GraphEdge, from: Box, to: Box): SVGPathElement {
  const x1 = from.x + from.w;
  const y1 = from.y + from.h / 2;
  const x2 = to.x;
  const y2 = to.y + to.h / 2;
  const bend = (x2 - x1) * 0.5;
  const classes = ["g-edge", `from-${from.node.kind}`, `is-${edge.kind}`, edge.lit ? "is-lit" : "", edge.negated ? "is-negated" : ""].filter(Boolean);
  return svg("path", { class: classes.join(" "), "data-from": edge.from, "data-to": edge.to, d: `M${x1} ${y1} C${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}` });
}

// The same content as a nested list: the text alternative, and the way to read it on a phone.
function asList(ontology: Ontology, block: BlockProps | null): HTMLElement {
  const stateIds = ontology.states.map((s) => s.id);
  const obsItem = (id: string): HTMLElement | null => {
    const obs = ontology.observations.find((o) => o.id === id);
    if (!obs) return null;
    const source = ontology.sources.find((s) => s.id === obs.source);
    const value = block ? `: ${formatValue(obs.unit, block.obs[obs.id])}` : obs.unit ? ` (${obs.unit})` : "";
    return h("li", { text: `${obs.title}${value}. Source: ${source ? `${source.title}, ${source.provider ?? ""}` : obs.source}` });
  };
  // Each state is told in full once, with its observations and their sources under it;
  // elsewhere it is named with its answer only.
  const told = new Set<string>();
  const stateItem = (id: string, need: string, full: boolean): HTMLElement | null => {
    const state = ontology.states.find((s) => s.id === id);
    if (!state) return null;
    const verdict = block ? `: ${yesNo(block.states[state.id]).toLowerCase()}` : "";
    const after = need ? ` ${need}` : ".";
    if (!full || told.has(id)) return h("li", {}, h("strong", { text: `${state.title}${verdict}` }), after);
    told.add(id);
    const item = h("li", {}, h("strong", { text: `${state.title}${verdict}` }), `${after} Rule: ${state.rule}. ${state.why ?? ""}`);
    const under = state.needs.map(obsItem).filter((el): el is HTMLElement => el !== null);
    if (under.length) item.append(h("ul", {}, ...under));
    return item;
  };
  const actionItem = (action: Ontology["actions"][number], lead: string, full: boolean): HTMLElement => {
    const item = h("li", {}, h("strong", { text: `${lead}${action.title}` }), `. Rule: ${action.rule}. ${action.advice ?? ""}`);
    const terms = ruleTerms(action.rule, stateIds);
    const under = [
      ...terms.map((t) => stateItem(t.state, t.negated ? "(the rule needs this to be false)." : "(the rule needs this to be true).", full)),
      ...(action.stronger_if ?? []).filter((id) => !terms.some((t) => t.state === id)).map((id) => {
        const extra = ontology.confidence?.extra_conditions?.[id];
        return stateIds.includes(id) ? stateItem(id, "(adds to the agreement count when true).", full) : extra ? h("li", { text: `${id}: ${extra} (adds to the confidence when true).` }) : null;
      }),
    ].filter((el): el is HTMLElement => el !== null);
    if (under.length) item.append(h("ul", {}, ...under));
    return item;
  };
  const list = h("ul");
  const chosen = block ? ontology.actions.find((a) => a.id === block.action) : undefined;
  if (chosen) list.append(actionItem(chosen, "Action of this block: ", true));
  for (const action of ontology.actions) {
    if (action !== chosen) list.append(actionItem(action, block ? "Not chosen: " : "", false));
  }
  // The states not told yet, so the list is complete even where no rule used one.
  const rest = stateIds.filter((id) => !told.has(id)).map((id) => stateItem(id, "", true)).filter((el): el is HTMLElement => el !== null);
  if (rest.length) list.append(h("li", {}, h("strong", { text: block ? "The other states of this block" : "The states" }), h("ul", {}, ...rest)));
  // Open from the start on a narrow screen, where the drawing has to be scrolled sideways.
  const open = !window.matchMedia(WIDE).matches;
  return h("details", { class: "graph-text", open }, h("summary", { text: block ? "Read the evidence as a list" : "Read the vocabulary as a list" }), list);
}

function key(text: string, sample: string): HTMLElement {
  const item = h("span", { class: "graph-key" });
  item.innerHTML = `<svg viewBox="0 0 26 8" width="26" height="8" aria-hidden="true"><path class="${sample}" d="M1 4H25"/></svg>`;
  item.append(text);
  return item;
}

/** The graph for a block, or the schema of the vocabulary when `block` is null. */
export function drawGraph(ontology: Ontology, block: BlockProps | null, color: (action: string) => string): HTMLElement {
  const schema = block === null;
  const graph = buildGraph(ontology, block);
  const boxes = new Map<string, Box>();
  const columns: Box[][] = COLUMNS.map(() => []);
  for (const node of graph.nodes) {
    const box = measure(node, schema);
    boxes.set(node.key, box);
    columns[node.column].push(box);
  }
  // Under the chosen action, a small heading separates the actions that were not chosen.
  const others = !schema && columns[3].some((b) => b.node.chosen) ? 22 : 0;
  const tall = (list: Box[], extra: number): number => list.reduce((sum, b) => sum + b.h, 0) + GAP * Math.max(0, list.length - 1) + extra;
  const height = Math.max(...columns.map((list, k) => tall(list, k === 3 ? others : 0)));
  columns.forEach((list, k) => {
    // Shorter columns are spread a little and centred, so the links run flatter.
    const extra = k === 3 ? others : 0;
    const spare = height - tall(list, extra);
    const gap = GAP + Math.min(22, spare / (list.length + 1));
    let y = HEAD + (height - (tall(list, extra) + (gap - GAP) * Math.max(0, list.length - 1))) / 2;
    for (const box of list) {
      box.y = Math.round(y);
      y += box.h + gap + (box.node.chosen ? others : 0);
    }
  });

  const total = HEAD + height + 4;
  const label = block ? `Evidence graph for block ${block.id}` : "Schema of the vocabulary: sources, observations, states and actions";
  const root = svg("svg", { class: `graph-svg${schema ? " is-schema" : ""}`, viewBox: `0 0 ${WIDTH} ${total}`, width: WIDTH, height: total, role: "group", "aria-label": label });
  COLUMNS.forEach((column, k) => {
    const head = svg("text", { class: "g-head", x: column.x + 1, y: 13 }, column.title);
    const meaning = ontology.object_types?.[column.type];
    if (meaning) head.append(svg("title", {}, meaning));
    root.append(head);
    // The name of the link into this column, from the file: "measures", "supports", "leads to".
    const link = ontology.link_types?.find((l) => l.to === column.type && l.from === COLUMNS[k - 1]?.type);
    if (link) root.append(svg("text", { class: "g-link-name", x: column.x - 8, y: 13, "text-anchor": "end" }, link.name));
  });
  const chosenBox = columns[3].find((b) => b.node.chosen);
  if (chosenBox && others) root.append(svg("text", { class: "g-sub", x: COLUMNS[3].x + 1, y: chosenBox.y + chosenBox.h + 17 }, "Not chosen"));

  const edgeLayer = svg("g", { "aria-hidden": "true" });
  const drawn: { edge: GraphEdge; el: SVGPathElement }[] = [];
  // Dim links first, so the lit ones lie on top.
  for (const edge of [...graph.edges].sort((a, b) => Number(a.lit) - Number(b.lit))) {
    const from = boxes.get(edge.from);
    const to = boxes.get(edge.to);
    if (!from || !to) continue;
    const el = drawEdge(edge, from, to);
    drawn.push({ edge, el });
    edgeLayer.append(el);
  }
  root.append(edgeLayer);

  const rest = block
    ? "Point at a node, tap it, or move to it with the Tab key, to read its rule and why it matters."
    : "Point at a node, tap it, or move to it with the Tab key, to read what it means.";
  const detail = h("p", { class: "graph-detail", "aria-live": "polite", text: rest });
  let pinned: Box | null = null;
  const show = (box: Box | null): void => {
    for (const { edge, el } of drawn) el.classList.toggle("is-hot", Boolean(box) && (edge.from === box?.node.key || edge.to === box?.node.key));
    for (const other of boxes.values()) other.el?.classList.toggle("is-active", other === box);
    if (!box) {
      detail.textContent = rest;
      return;
    }
    const type = box.node.kind === "condition" ? "Extra condition" : COLUMNS[box.node.column].type;
    detail.replaceChildren(h("strong", { text: `${type}: ${box.node.title}. ` }), sentences(box.node.detail));
  };
  for (const box of boxes.values()) {
    const el = drawNode(box, schema, color);
    box.el = el;
    el.addEventListener("pointerenter", () => show(box));
    el.addEventListener("pointerleave", () => show(pinned));
    el.addEventListener("focus", () => {
      pinned = box;
      show(box);
    });
    el.addEventListener("blur", () => {
      if (pinned === box) pinned = null;
      show(pinned);
    });
    root.append(el);
  }

  const keys = h(
    "div",
    { class: "graph-keys" },
    ...(block ? [key("carried evidence for this action", "g-edge is-lit from-state"), key("not used", "g-edge")] : []),
    key("the rule needs it to be false", `g-edge is-negated${schema ? " is-lit from-state" : ""}`),
    key("adds to the agreement count", `g-edge is-strengthens${schema ? " is-lit from-state" : ""}`),
  );
  return h("div", { class: "graph" }, h("div", { class: "graph-scroll" }, root), keys, detail, asList(ontology, block));
}
