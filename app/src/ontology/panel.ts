// Written with Super Intelligence (SI) assistance.
// The evidence drawer: one component with two modes. With a block it shows the object card and
// the evidence graph of that block; without one it shows the schema of the vocabulary, reached
// from "How it decides". It can be folded down to its title bar to give the map back.
import { h } from "../dom";
import { buildCard, buildVocabulary, type CardHooks } from "./card";
import { drawGraph } from "./graph";
import type { BlockProps, Ontology } from "./model";

export interface EvidencePanel {
  showBlock(block: BlockProps): void;
  showSchema(): void;
  hide(): void;
  setFolded(folded: boolean): void;
  readonly folded: boolean;
  readonly mode: "block" | "schema" | null;
  /** Height on screen, 0 when hidden: the map is framed above it. */
  height(): number;
}

export interface PanelHooks extends CardHooks {
  /** The close button was pressed in this mode. */
  onClose(mode: "block" | "schema"): void;
  /** The drawer opened, closed, folded or unfolded. */
  onLayout(): void;
}

export function buildEvidencePanel(parent: HTMLElement, ontology: Ontology, hooks: PanelHooks): EvidencePanel {
  const kind = h("span", { class: "object-type" });
  const title = h("h2", { class: "drawer-title" });
  const foldButton = h("button", { type: "button", class: "text-button small" });
  const closeButton = h("button", { type: "button", class: "text-button small", text: "Close" });
  const body = h("div", { class: "drawer-body" });
  const root = h("section", { id: "drawer", class: "card", hidden: true }, h("div", { class: "drawer-head" }, kind, title, foldButton, closeButton), body);
  parent.prepend(root); // first in the phone's bottom sheet; on a wide screen it floats over the map
  new ResizeObserver(() => hooks.onLayout()).observe(root);

  let mode: "block" | "schema" | null = null;
  let folded = false;
  let heading = "";
  let summary = ""; // said after the heading while the drawer is folded

  const render = (): void => {
    root.hidden = mode === null;
    root.classList.toggle("is-folded", folded);
    root.classList.toggle("is-schema", mode === "schema");
    body.hidden = folded;
    title.textContent = folded && summary ? `${heading}: ${summary}` : heading;
    foldButton.textContent = folded ? "Show graph" : "Hide graph";
    foldButton.setAttribute("aria-expanded", String(!folded));
    hooks.onLayout();
  };
  const fill = (next: "block" | "schema", name: string, text: string, more: string, ...parts: HTMLElement[]): void => {
    mode = next;
    folded = false;
    heading = text;
    summary = more;
    kind.textContent = name;
    root.setAttribute("aria-label", `${name}: ${heading}`);
    body.replaceChildren(...parts);
    body.scrollTop = 0;
    render();
  };

  foldButton.addEventListener("click", () => {
    folded = !folded;
    render();
  });
  closeButton.addEventListener("click", () => {
    if (mode) hooks.onClose(mode);
  });
  root.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && mode) hooks.onClose(mode);
  });

  return {
    showBlock(block) {
      const action = ontology.actions.find((a) => a.id === block.action)?.title ?? block.action;
      fill("block", "Block", block.id, block.confidence ? `${action}, ${block.confidence} confidence` : action, buildCard(ontology, block, hooks), drawGraph(ontology, block, hooks.color));
    },
    showSchema() {
      fill("schema", "Vocabulary", "How it decides", "", buildVocabulary(ontology), drawGraph(ontology, null, hooks.color));
    },
    hide() {
      mode = null;
      body.replaceChildren();
      render();
    },
    setFolded(value) {
      if (folded === value || mode === null) return;
      folded = value;
      render();
    },
    get folded() {
      return folded;
    },
    get mode() {
      return mode;
    },
    height: () => (mode === null ? 0 : root.getBoundingClientRect().height),
  };
}
