// Written with Super Intelligence (SI) assistance.
// The object card of one block: what was decided, how sure, where it is, and why, with the
// actions a person can take from here. The words come from the ontology and the block itself.
import { h } from "../dom";
import type { BlockProps, Ontology } from "./model";

export interface CardHooks {
  /** The colour of an action on the map. */
  color(action: string): string;
  /** How many blocks share the action of this block, in the list its rank counts in. */
  ranked(block: BlockProps): number;
  openChart(block: BlockProps): void;
  fly(block: BlockProps): void;
  /** The address of the current view, for "Copy link". */
  link(): string;
}

/** Copies a text and says so on the button for a moment. */
export function copyButton(label: string, text: () => string, small = true): HTMLButtonElement {
  const button = h("button", { type: "button", class: `text-button${small ? " small" : ""}`, text: label });
  button.addEventListener("click", () => {
    const value = text();
    const done = (ok: boolean): void => {
      button.textContent = ok ? "Copied" : "Copy failed";
      window.setTimeout(() => {
        button.textContent = label;
      }, 1600);
    };
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(value).then(
        () => done(true),
        () => done(false),
      );
      return;
    }
    // Older browsers and pages without a secure origin: a hidden field and the copy command.
    const field = h("textarea", { class: "offscreen", "aria-hidden": "true" });
    field.value = value;
    document.body.append(field);
    field.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch {
      ok = false;
    }
    field.remove();
    done(ok);
  });
  return button;
}

export function where(lat: number, lon: number, digits = 5): string {
  return `${Math.abs(lat).toFixed(digits)} ${lat < 0 ? "S" : "N"}, ${Math.abs(lon).toFixed(digits)} ${lon < 0 ? "W" : "E"}`;
}

export function buildCard(ontology: Ontology, block: BlockProps, hooks: CardHooks): HTMLElement {
  const action = ontology.actions.find((a) => a.id === block.action);
  const title = action?.title ?? block.action;
  const swatch = h("span", { class: "act-swatch", "aria-hidden": "true" });
  swatch.style.background = hooks.color(block.action);

  const chips = h("div", { class: "chips" });
  if (block.confidence) {
    chips.append(h("span", { class: `chip chip-${block.confidence}`, title: ontology.confidence?.rule ?? "", text: `Agreement: ${block.confidence}` }));
  }
  if (block.rank !== null && block.rank !== undefined) {
    chips.append(h("span", { class: "chip", title: "Ordered inside this class and site by the size of the fall in HH. A bigger fall is not a grade of the land.", text: `${block.rank} of ${hooks.ranked(block)} in ${title}` }));
  }
  chips.append(h("span", { class: "chip", text: `Site: ${block.site}` }));

  const chartButton = h("button", { type: "button", class: "text-button small", text: "Open place chart" });
  chartButton.addEventListener("click", () => hooks.openChart(block));
  const flyButton = h("button", { type: "button", class: "text-button small", text: "Fly here" });
  flyButton.addEventListener("click", () => hooks.fly(block));

  return h(
    "div",
    { class: "block-card" },
    h("h3", { class: "object-title" }, swatch, title),
    chips,
    h(
      "div",
      { class: "object-id" },
      h("span", {}, h("code", { text: block.id }), ` ${where(block.lat, block.lon)}`),
      copyButton("Copy", () => `${block.id}, ${block.lat.toFixed(5)}, ${block.lon.toFixed(5)}`),
    ),
    action?.advice ? h("p", { class: "object-advice", text: action.advice }) : null,
    h("h4", { text: "Why" }),
    h("ul", { class: "object-reasons" }, ...block.reasons.map((reason) => h("li", { text: reason }))),
    h("div", { class: "place-actions" }, chartButton, flyButton, copyButton("Copy link", hooks.link)),
    ontology.caveat ? h("p", { class: "note", text: ontology.caveat }) : null,
  );
}

/** The text beside the schema: what the words mean, the thresholds, the confidence rule and the caveat. */
export function buildVocabulary(ontology: Ontology): HTMLElement {
  const box = h("div", { class: "block-card" });
  if (ontology.about) box.append(h("p", { class: "object-advice", text: ontology.about }));
  if (ontology.caveat) box.append(h("p", { class: "object-caveat", text: ontology.caveat }));

  const types = Object.entries(ontology.object_types ?? {});
  if (types.length) {
    box.append(h("h4", { text: "Kinds of thing" }), h("dl", { class: "object-terms" }, ...types.flatMap(([name, meaning]) => [h("dt", { text: name }), h("dd", { text: meaning })])));
  }

  const thresholds = Object.entries(ontology.thresholds ?? {});
  const values = thresholds.filter(([, value]) => typeof value === "number");
  if (values.length) {
    box.append(
      h("h4", { text: "Thresholds" }),
      h("dl", { class: "object-terms is-values" }, ...values.flatMap(([name, value]) => [h("dt", {}, h("code", { text: name })), h("dd", { text: String(value) })])),
    );
    for (const [, value] of thresholds) {
      if (typeof value === "string") box.append(h("p", { class: "note", text: value }));
    }
  }

  const confidence = ontology.confidence;
  if (confidence?.rule) {
    box.append(h("h4", { text: confidence.label ?? "Agreement" }), h("p", { class: "object-advice", text: confidence.rule }));
    const extra = Object.entries(confidence.extra_conditions ?? {});
    if (extra.length) box.append(h("dl", { class: "object-terms" }, ...extra.flatMap(([name, rule]) => [h("dt", {}, h("code", { text: name })), h("dd", { text: rule })])));
  }
  return box;
}
