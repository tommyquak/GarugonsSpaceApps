// Written with Super Intelligence (SI) assistance.
// Number chips: a figure read from validation.json, shown as a small button. A click, a tap or the
// keyboard opens a small card beside it that says which entry it was read from, whether it is final,
// what it means and which script computed it. The point is the rule in docs/DESIGN.md: every number
// comes from validation.json, and a reader can see that it does.
//
// The card is a native popover: it floats in the top layer, so it never shifts the table or gets
// clipped by a scrolling box. It follows its number on scroll and resize, and closes on Close,
// a click elsewhere or Escape.
// Browsers without popovers get the same card opening in place under the number.
import "./chip.css";
import { h } from "./dom";

export interface NumberEntry {
  value: number | string;
  unit?: string;
  site?: string;
  status?: string;
  note?: string;
  made_by?: string;
}

const REPO = "https://github.com/tommyquak/GarugonsSpaceApps/blob/main/";
const GAP = 6;
const EDGE = 8;

const STATUS: Record<string, string> = {
  final: "Final: recomputed separately by a second team member.",
  exploratory: "Exploratory: computed by the pipeline, not yet recomputed by a second team member.",
};

const POPOVER = typeof HTMLElement !== "undefined" && "popover" in HTMLElement.prototype;
let counter = 0;
let shown: { button: HTMLElement; card: HTMLElement } | null = null;

if (POPOVER) {
  // The card is fixed to the window, so it follows its number when a dialog scrolls or the window resizes,
  // and closes only when its number has left the window.
  const follow = (event?: Event) => {
    if (!shown || (event && shown.card.contains(event.target as Node))) return;
    const at = shown.button.getBoundingClientRect();
    if (at.bottom < 0 || at.top > window.innerHeight) shown.card.hidePopover();
    else place(shown.button, shown.card);
  };
  document.addEventListener("scroll", follow, true);
  window.addEventListener("resize", () => follow());
  // Escape closes the open card and nothing else, even inside a dialog that Escape would also close.
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !shown) return;
    event.preventDefault();
    event.stopPropagation();
    shown.card.hidePopover();
  }, true);
}

export function formatValue(entry: NumberEntry): string {
  return typeof entry.value === "number" ? entry.value.toLocaleString("en", { maximumFractionDigits: 4 }) : String(entry.value);
}

/** Put the card under its number, or above it when there is no room below, inside the window. */
function place(button: HTMLElement, card: HTMLElement): void {
  const at = button.getBoundingClientRect();
  const width = card.offsetWidth;
  const height = card.offsetHeight;
  const left = Math.min(Math.max(EDGE, at.left), window.innerWidth - width - EDGE);
  const below = at.bottom + GAP;
  const top = below + height <= window.innerHeight - EDGE ? below : Math.max(EDGE, at.top - height - GAP);
  card.style.left = `${Math.round(left)}px`;
  card.style.top = `${Math.round(top)}px`;
}

/** A chip for one validation.json entry. `text` replaces the shown value, for use inside a sentence. */
export function numberChip(key: string, entry: NumberEntry, text?: string): HTMLElement {
  const id = `num-chip-${++counter}`;
  const value = text ?? formatValue(entry);
  const button = h("button", {
    type: "button",
    class: "num-chip",
    "aria-expanded": "false",
    "aria-controls": id,
    "aria-label": `${value}${entry.unit ? ` ${entry.unit}` : ""}: where this number comes from`,
    text: value,
  });

  const facts = h("dl");
  const fact = (term: string, detail: Node | string) => facts.append(h("dt", { text: term }), h("dd", {}, detail));
  fact("Entry", h("code", { text: key }));
  fact("Value", `${formatValue(entry)}${entry.unit ? ` ${entry.unit}` : ""}${entry.site ? `, ${entry.site}` : ""}`);
  if (entry.note) fact("Means", entry.note);
  if (entry.made_by) fact("Computed by", h("a", { href: REPO + entry.made_by, target: "_blank", rel: "noopener", text: entry.made_by }));
  const close = h("button", { type: "button", class: "num-chip-close", "aria-label": "Close", text: "Close" });
  const status = entry.status ?? "exploratory";
  const card = h(
    "div",
    { class: "num-chip-note", id, role: "dialog", "aria-label": `Where ${value} comes from` },
    h("div", { class: "num-chip-head" }, h("p", { class: "num-chip-status", text: STATUS[status] ?? `Status: ${status}.` }), close),
    facts,
  );

  if (POPOVER) {
    card.setAttribute("popover", "auto"); // one open at a time, Escape and a click elsewhere close it
    button.setAttribute("popovertarget", id);
    close.setAttribute("popovertarget", id);
    close.setAttribute("popovertargetaction", "hide");
    card.addEventListener("toggle", (event) => {
      const open = (event as ToggleEvent).newState === "open";
      button.setAttribute("aria-expanded", String(open));
      if (open) {
        shown = { button, card };
        place(button, card);
        close.focus({ preventScroll: true });
      } else {
        if (shown?.card === card) shown = null;
        // After Escape or Close, put the keyboard back on the number, not at the top of the dialog.
        const now = document.activeElement;
        if (!now || now === document.body || now.tagName === "DIALOG" || card.contains(now)) button.focus({ preventScroll: true });
      }
    });
  } else {
    card.hidden = true;
    const set = (open: boolean) => {
      card.hidden = !open;
      button.setAttribute("aria-expanded", String(open));
    };
    button.addEventListener("click", () => set(card.hidden));
    close.addEventListener("click", () => {
      set(false);
      button.focus();
    });
  }
  return h("span", { class: "num-chip-wrap" }, button, card);
}

/**
 * A sentence with chips in it: every `[[key|shown text]]` becomes a chip for that validation.json entry,
 * the rest stays plain text. A key that is not in `numbers` keeps its shown text, without a chip.
 * Use it where a sentence is set with textContent today: `el.replaceChildren(withChips(text, numbers))`.
 */
export function withChips(text: string, numbers: Record<string, NumberEntry | undefined>): DocumentFragment {
  const out = document.createDocumentFragment();
  let at = 0;
  for (const match of text.matchAll(/\[\[([^|\]]+)\|([^\]]+)\]\]/g)) {
    out.append(text.slice(at, match.index));
    const entry = numbers[match[1]];
    out.append(entry ? numberChip(match[1], entry, match[2]) : match[2]);
    at = (match.index ?? 0) + match[0].length;
  }
  out.append(text.slice(at));
  return out;
}
