// Written with Super Intelligence (SI) assistance.
// The vocabulary of blocks/ontology.json (docs/FUSION.md) and the logic that turns it, with or
// without one block, into the nodes and links of the evidence graph. Nothing is drawn here.
//
//   Source -> Observation   the observation names its source
//   Observation -> State    the state lists the observation under "needs"
//   State -> Action         the action's rule names the state, plainly or after "not"
//   State -> Action         the action lists it under "stronger_if": it adds to the confidence

export interface Ontology {
  about?: string;
  object_types?: Record<string, string>;
  link_types?: { from: string; to: string; name: string }[];
  sources: { id: string; title: string; provider?: string }[];
  observations: { id: string; source: string; unit?: string; title: string }[];
  thresholds?: Record<string, number | string>;
  states: { id: string; title: string; needs: string[]; rule: string; why?: string }[];
  actions: { id: string; title: string; rule: string; advice?: string; stronger_if?: string[] }[];
  confidence?: { label?: string; rule?: string; extra_conditions?: Record<string, string> };
  caveat?: string;
}

// The properties of one block (docs/DATA_CONTRACT.md section 6).
export interface BlockProps {
  id: string;
  site: string;
  lon: number;
  lat: number;
  action: string;
  confidence: string | null;
  rank: number | null;
  fall_db: number | null;
  obs: Record<string, number | null>;
  states: Record<string, boolean | null>;
  reasons: string[];
}

export function isOntology(value: unknown): value is Ontology {
  const o = value as Ontology | null;
  return Boolean(o && Array.isArray(o.sources) && Array.isArray(o.observations) && Array.isArray(o.states) && Array.isArray(o.actions));
}

export type NodeKind = "source" | "observation" | "state" | "condition" | "action";

export interface GraphNode {
  key: string; // kind and id, unique in the graph
  kind: NodeKind;
  column: number; // 0 sources, 1 observations, 2 states, 3 actions
  title: string;
  /** A second, quieter line: the provider of a source. */
  sub?: string;
  /** Rule text, drawn in the node in the schema view and read out on hover or focus. */
  rule?: string;
  /** The value of an observation for the block, or its unit in the schema view. */
  value?: string;
  /** Whether a state holds for the block. Undefined without a block. */
  truth?: boolean | null;
  /** The action of the block. */
  chosen?: boolean;
  /** An action the block did not get. */
  dimmed?: boolean;
  /** Under the chosen action: the confidence of the block. */
  note?: string;
  /** The id of an action, for its colour. */
  action?: string;
  /** Lines for the details line under the graph. */
  detail: string[];
}

export interface GraphEdge {
  from: string;
  to: string;
  kind: "measures" | "supports" | "leads" | "strengthens";
  /** The rule needs the state to be false. */
  negated: boolean;
  /** Carried evidence for the chosen action. Always true in the schema view. */
  lit: boolean;
}

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

/** The states an action's rule names, each with whether it must be false. "everything else" names none. */
export function ruleTerms(rule: string, stateIds: string[]): { state: string; negated: boolean }[] {
  const terms: { state: string; negated: boolean }[] = [];
  let negated = false;
  for (const word of rule.split(/[^A-Za-z0-9_]+/).filter(Boolean)) {
    if (stateIds.includes(word)) {
      terms.push({ state: word, negated });
      negated = false;
    } else {
      // "not" flips the next state; any other word ("and") ends its reach.
      negated = word === "not" ? !negated : false;
    }
  }
  return terms;
}

/** The ids from a list that appear as whole words in a piece of rule text. */
export function namedIn(text: string, ids: string[]): string[] {
  const words = new Set(text.split(/[^A-Za-z0-9_]+/));
  return ids.filter((id) => words.has(id));
}

/** A value with its unit: decibels to one decimal, shares as percent, null as "no data". */
export function formatValue(unit: string | undefined, value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "no data";
  if (unit === "dB") return `${value.toFixed(1)} dB`;
  if (unit === "share") return `${Math.round(value * 100)}%`;
  if (unit === "m") return `${Math.round(value).toLocaleString("en")} m`;
  if (unit === "days") return `${Math.round(value)} ${Math.round(value) === 1 ? "day" : "days"}`;
  return unit ? `${value} ${unit}` : String(value);
}

/** Joins the detail lines of a node into sentences. */
export function sentences(lines: string[]): string {
  return lines.map((line) => `${line.replace(/[.\s]+$/, "")}.`).join(" ");
}

export function yesNo(value: boolean | null | undefined): string {
  return value === true ? "Yes" : value === false ? "No" : "no data";
}

// An id as words, for the two extra conditions, which have no title in the file.
function words(id: string): string {
  const text = id.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Builds the graph. With a block it carries the block's values and which links were used. */
export function buildGraph(ontology: Ontology, block: BlockProps | null): Graph {
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const stateIds = ontology.states.map((s) => s.id);
  const obsIds = ontology.observations.map((o) => o.id);
  const extras = ontology.confidence?.extra_conditions ?? {};
  const chosen = block ? ontology.actions.find((a) => a.id === block.action) : undefined;

  for (const source of ontology.sources) {
    nodes.push({ key: `source:${source.id}`, kind: "source", column: 0, title: source.title, sub: source.provider, detail: source.provider ? [`Provider: ${source.provider}`] : [] });
  }

  for (const obs of ontology.observations) {
    const source = ontology.sources.find((s) => s.id === obs.source);
    const value = block ? formatValue(obs.unit, block.obs[obs.id]) : (obs.unit ?? "");
    nodes.push({
      key: `observation:${obs.id}`,
      kind: "observation",
      column: 1,
      title: obs.title,
      value,
      detail: [...(block ? [`This block: ${value}`] : obs.unit ? [`Unit: ${obs.unit}`] : []), ...(source ? [`Measured by: ${source.title}`] : [])],
    });
    if (source) edges.push({ from: `source:${source.id}`, to: `observation:${obs.id}`, kind: "measures", negated: false, lit: !block });
  }

  // States in an order that follows the observations they need, so the links cross less.
  const middle = (needs: string[]): number => {
    const at = needs.map((id) => obsIds.indexOf(id)).filter((i) => i >= 0);
    return at.length ? at.reduce((a, b) => a + b, 0) / at.length : obsIds.length;
  };
  const stateNodes: { order: number; node: GraphNode; needs: string[] }[] = [];
  for (const state of ontology.states) {
    const truth = block ? (block.states[state.id] ?? null) : undefined;
    stateNodes.push({
      order: middle(state.needs),
      needs: state.needs,
      node: {
        key: `state:${state.id}`,
        kind: "state",
        column: 2,
        title: state.title,
        rule: state.rule,
        truth,
        detail: [...(block ? [`This block: ${yesNo(truth)}`] : []), `Rule: ${state.rule}`, ...(state.why ? [state.why] : [])],
      },
    });
  }
  // The extra conditions of the confidence rule. The blocks file does not say whether they hold.
  for (const [id, rule] of Object.entries(extras)) {
    const needs = namedIn(rule, obsIds);
    stateNodes.push({
      order: middle(needs),
      needs,
      node: {
        key: `condition:${id}`,
        kind: "condition",
        column: 2,
        title: words(id),
        rule,
        detail: [`Rule: ${rule}`, "An extra condition of the confidence rule. The blocks file does not record whether it holds for a block."],
      },
    });
  }
  stateNodes.sort((a, b) => a.order - b.order);
  for (const { node, needs } of stateNodes) {
    nodes.push(node);
    for (const id of needs) {
      if (obsIds.includes(id)) edges.push({ from: `observation:${id}`, to: node.key, kind: "supports", negated: false, lit: !block });
    }
  }

  // The chosen action first, the others under it.
  const actions = chosen ? [chosen, ...ontology.actions.filter((a) => a !== chosen)] : ontology.actions;
  for (const action of actions) {
    const isChosen = action === chosen;
    const key = `action:${action.id}`;
    const stronger = action.stronger_if ?? [];
    nodes.push({
      key,
      kind: "action",
      column: 3,
      title: action.title,
      rule: action.rule,
      action: action.id,
      chosen: block ? isChosen : undefined,
      dimmed: block ? !isChosen : undefined,
      note: isChosen && block?.confidence ? `Agreement: ${block.confidence}` : undefined,
      detail: [
        ...(block ? [isChosen ? "The action of this block." : "Not the action of this block."] : []),
        `Rule: ${action.rule}`,
        ...(action.advice ? [action.advice] : []),
        ...(stronger.length ? [`Stronger if: ${stronger.join(", ")}`] : []),
      ],
    });
    for (const term of ruleTerms(action.rule, stateIds)) {
      const truth = block?.states[term.state];
      const lit = !block || (isChosen && typeof truth === "boolean" && truth !== term.negated);
      edges.push({ from: `state:${term.state}`, to: key, kind: "leads", negated: term.negated, lit });
    }
    for (const id of stronger) {
      if (stateIds.includes(id)) {
        edges.push({ from: `state:${id}`, to: key, kind: "strengthens", negated: false, lit: !block || (isChosen && block.states[id] === true) });
      } else if (id in extras) {
        edges.push({ from: `condition:${id}`, to: key, kind: "strengthens", negated: false, lit: !block });
      }
    }
  }

  if (block) {
    // Evidence flows back: a state that was used lights the observations under it, and they their sources.
    const used = new Set(edges.filter((e) => e.lit).map((e) => e.from));
    for (const e of edges) {
      if (e.kind === "supports" && used.has(e.to)) {
        const value = block.obs[e.from.slice("observation:".length)];
        e.lit = value !== null && value !== undefined;
      }
    }
    const usedObs = new Set(edges.filter((e) => e.kind === "supports" && e.lit).map((e) => e.from));
    for (const e of edges) {
      if (e.kind === "measures") e.lit = usedObs.has(e.to);
    }
  }
  return { nodes, edges };
}
