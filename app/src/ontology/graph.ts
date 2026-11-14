// Written with Super Intelligence (SI) assistance.
// Draws the evidence graph in SVG: four columns, left to right, Sources, Observations, States,
// Action, with a curved link wherever the ontology says one thing feeds another. With a block
// the nodes carry its values and the links that carried evidence for its action are lit;
// without one the same drawing is the schema of the vocabulary.
//
// Pulses travel along the lit links, sources first, then observations, then states, to show
// which way the information flows. Clicking a node opens its details: its rule, the
// thresholds it uses, what it is built from and what it feeds, each of which can be clicked
// in turn.
import { h } from "../dom";
import { WIDE } from "../view";
import { buildGraph, formatValue, namedIn, ruleTerms, sentences, yesNo, type BlockProps, type GraphEdge, type GraphNode, type Ontology } from "./model";

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
  const g = svg("g", { class: classes.join(" "), "data-key": node.key, tabindex: 0, role: "button", "aria-label": `${describe(node)} Press Enter for details.`, transform: `translate(${box.x}, ${box.y})` });
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

const LINK_WORDS: Record<GraphEdge["kind"], [string, string]> = {
  measures: ["Measured by", "Measures"],
  supports: ["Built from", "Used by"],
  leads: ["Needs", "Leads to"],
  strengthens: ["Counts for more with", "Adds to the agreement of"],
};

/**
 * The graph for a block, or the schema of the vocabulary when `block` is null. The details of
 * a clicked node go into `side` when one is given, else under the graph.
 */
export function drawGraph(ontology: Ontology, block: BlockProps | null, color: (action: string) => string, side?: HTMLElement): HTMLElement {
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
  const pulseLayer = svg("g", { "aria-hidden": "true" });
  const drawn: { edge: GraphEdge; el: SVGPathElement; pulse?: SVGPathElement }[] = [];
  // Dim links first, so the lit ones lie on top.
  for (const edge of [...graph.edges].sort((a, b) => Number(a.lit) - Number(b.lit))) {
    const from = boxes.get(edge.from);
    const to = boxes.get(edge.to);
    if (!from || !to) continue;
    const el = drawEdge(edge, from, to);
    // A pulse on every link that carries information: all of them in the schema, the lit ones for a block.
    let pulse: SVGPathElement | undefined;
    if (edge.lit) {
      pulse = svg("path", { class: `g-pulse stage-${from.node.column}`, d: el.getAttribute("d") ?? "", pathLength: 100 });
      pulseLayer.append(pulse);
    }
    drawn.push({ edge, el, pulse });
    edgeLayer.append(el);
  }
  root.append(edgeLayer, pulseLayer);

  const rest = block
    ? "Point at a box to read it. Click it for its rule, its numbers and what it connects to."
    : "Point at a box to read it. Click it for its rule, its thresholds and what it connects to.";
  const detail = h("p", { class: "graph-detail", "aria-live": "polite", text: rest });
  let pinned: Box | null = null;
  let selected: Box | null = null;
  const show = (box: Box | null): void => {
    for (const { edge, el, pulse } of drawn) {
      const hot = Boolean(box) && (edge.from === box?.node.key || edge.to === box?.node.key);
      el.classList.toggle("is-hot", hot);
      pulse?.classList.toggle("is-hot", hot);
    }
    root.classList.toggle("has-focus", Boolean(box));
    for (const other of boxes.values()) {
      other.el?.classList.toggle("is-active", other === box);
      other.el?.classList.toggle("is-selected", other === selected);
    }
    if (!box) {
      detail.textContent = rest;
      return;
    }
    const type = box.node.kind === "condition" ? "Extra condition" : COLUMNS[box.node.column].type;
    detail.replaceChildren(h("strong", { text: `${type}: ${box.node.title}. ` }), sentences(box.node.detail));
  };

  // The details of one node, opened by a click. Every related node in it is a button to that node.
  const inspector = side ?? h("aside", {});
  inspector.classList.add("graph-inspect");
  const thresholds = ontology.thresholds ?? {};
  const thresholdNames = Object.keys(thresholds).filter((name) => name !== "note");
  type Related = { box: Box; note: string };
  const related = (heading: string, items: Related[]): HTMLElement | null => {
    if (!items.length) return null;
    const list = h("ul", { class: "inspect-links" });
    for (const { box, note } of items) {
      const button = h("button", { type: "button", class: `inspect-link is-${box.node.kind}` }, h("span", { text: box.node.title }), note ? h("em", { text: note }) : null);
      button.addEventListener("click", () => select(box));
      list.append(h("li", {}, button));
    }
    return h("div", { class: "inspect-part" }, h("h4", { text: heading }), list);
  };
  const stateOf = (node: GraphNode): string =>
    node.kind === "state" && node.truth !== undefined ? yesNo(node.truth) : node.kind === "observation" && block && node.value ? node.value : "";
  const fillInspector = (box: Box | null): void => {
    if (!box) {
      inspector.replaceChildren(
        h("p", { class: "inspect-empty", text: "Click a box to see its rule, the numbers it uses and what it connects to." }),
        h("p", { class: "inspect-note", text: "A screening result from one season. No ground measurements." }),
      );
      return;
    }
    const { node } = box;
    const type = node.kind === "condition" ? "Extra condition" : COLUMNS[node.column].type;
    const close = h("button", { type: "button", class: "text-button small", text: "Close", "aria-label": "Close the details" });
    close.addEventListener("click", () => select(null));
    const parts: (HTMLElement | null)[] = [h("div", { class: "inspect-head" }, h("span", { class: `inspect-kind is-${node.kind}`, text: type }), close), h("h3", { class: "inspect-title", text: node.title })];
    const verdict = stateOf(node);
    if (verdict) parts.push(h("p", { class: "inspect-value" }, "This block: ", h("strong", { text: verdict })));
    else if (node.kind === "observation" && node.value) parts.push(h("p", { class: "inspect-value", text: `Unit: ${node.value}` }));
    if (node.chosen !== undefined) parts.push(h("p", { class: "inspect-value", text: node.chosen ? `The class of this block. ${node.note ?? ""}` : "Not the class of this block." }));
    if (node.sub) parts.push(h("p", { class: "inspect-value", text: node.sub }));
    if (node.rule) {
      parts.push(h("div", { class: "inspect-part" }, h("h4", { text: "Rule" }), h("code", { class: "inspect-rule", text: node.rule })));
      const used = namedIn(node.rule, thresholdNames);
      if (used.length) {
        const rows = used.map((name) => h("div", {}, h("dt", { text: name }), h("dd", { text: String(thresholds[name]) })));
        parts.push(h("div", { class: "inspect-part" }, h("h4", { text: "Thresholds" }), h("dl", { class: "inspect-terms" }, ...rows), h("p", { class: "inspect-note", text: "Choices made on the day of the first results, not taken from a reference." })));
      }
    }
    // What the file says about it, without the lines already shown above.
    const said = node.detail.filter((line) => !/^(Rule|This block|Unit|Provider|Measured by|Stronger if):/.test(line) && !/action of this block/.test(line));
    if (said.length) parts.push(h("p", { class: "inspect-text", text: sentences(said) }));
    for (const kind of ["measures", "supports", "leads", "strengthens"] as const) {
      const item = (key: string, negated: boolean): Related | null => {
        const other = boxes.get(key);
        if (!other) return null;
        return { box: other, note: [negated ? "must be false" : "", stateOf(other.node)].filter(Boolean).join(", ") };
      };
      const into = drawn.filter((d) => d.edge.kind === kind && d.edge.to === node.key).map((d) => item(d.edge.from, d.edge.negated));
      const out = drawn.filter((d) => d.edge.kind === kind && d.edge.from === node.key).map((d) => item(d.edge.to, d.edge.negated));
      parts.push(related(LINK_WORDS[kind][0], into.filter((x): x is Related => x !== null)));
      parts.push(related(LINK_WORDS[kind][1], out.filter((x): x is Related => x !== null)));
    }
    inspector.replaceChildren(...parts.filter((el): el is HTMLElement => el !== null));
    inspector.scrollTop = 0;
  };
  function select(box: Box | null): void {
    selected = box === selected ? null : box;
    fillInspector(selected);
    show(selected);
  }
  fillInspector(null);
  root.addEventListener("click", (event) => {
    if (event.target === root) select(null); // a click on the empty part of the drawing
  });

  for (const box of boxes.values()) {
    const el = drawNode(box, schema, color);
    box.el = el;
    el.addEventListener("pointerenter", () => show(box));
    el.addEventListener("pointerleave", () => show(pinned ?? selected));
    el.addEventListener("click", () => select(box));
    el.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        select(box);
      }
    });
    el.addEventListener("focus", () => {
      pinned = box;
      show(box);
    });
    el.addEventListener("blur", () => {
      if (pinned === box) pinned = null;
      show(pinned ?? selected);
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
  return h("div", { class: "graph" }, h("div", { class: "graph-scroll" }, root), keys, detail, side ? null : inspector, asList(ontology, block));
}
