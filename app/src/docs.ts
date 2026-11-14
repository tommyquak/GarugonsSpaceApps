// Written with Super Intelligence (SI) assistance.
// The Limits and About dialogs. Their text is read from the repo's own documents at build time
// (docs/LIMITS.md and the root README.md), and numbers come from validation.json.
import limitsText from "../../docs/LIMITS.md?raw";
import readmeText from "../../README.md?raw";
import { baseStyle } from "./basemaps";
import { numberChip } from "./chip";
import { fetchJson, type LayerEntry } from "./data";
import { h } from "./dom";
import { canReplayIntro, playIntro } from "./intro";
import { renderMarkdown, section } from "./markdown";

interface NumberEntry {
  value: number | string;
  unit?: string;
  site?: string;
  status?: string;
  note?: string;
}

function dialog(title: string): { root: HTMLDialogElement; body: HTMLElement } {
  const close = h("button", { type: "button", class: "text-button", text: "Close" });
  const body = h("div", { class: "doc" });
  const root = h("dialog", { class: "sheet-dialog", "aria-label": title }, h("div", { class: "dialog-head" }, h("h2", { text: title }), close), body);
  close.addEventListener("click", () => root.close());
  root.addEventListener("click", (event) => {
    if (event.target === root) root.close(); // a click on the backdrop
  });
  document.body.append(root);
  return { root, body };
}

function sourceList(layers: LayerEntry[]): HTMLElement {
  const list = h("ul");
  for (const source of new Set(layers.map((l) => l.source).filter(Boolean))) {
    list.append(h("li", { text: `Map layers: ${source}` }));
  }
  for (const source of Object.values(baseStyle.sources)) {
    if ("attribution" in source && source.attribution) {
      const item = h("li", { text: "Basemap: " });
      const credit = h("span");
      credit.innerHTML = source.attribution; // fixed text from basemaps.ts
      item.append(credit);
      list.append(item);
    }
  }
  list.append(h("li", { text: "Map library: MapLibre GL JS" }));
  return list;
}

async function numbers(): Promise<HTMLElement> {
  const box = h("div");
  const all = await fetchJson<Record<string, NumberEntry>>("validation.json");
  if (!all) {
    box.append(h("p", { text: "The numbers file is not loaded yet." }));
    return box;
  }
  const entries = Object.entries(all);
  const final = entries.filter(([, n]) => n.status === "final");
  if (final.length) {
    const body = h("tbody");
    for (const [key, n] of final) {
      body.append(h("tr", {}, h("td", { text: key.replace(/_/g, " ") }), h("td", {}, numberChip(key, n)), h("td", { text: n.unit ?? "" }), h("td", { text: n.site ?? "" })));
    }
    const head = h("tr", {}, ...["Number", "Value", "Unit", "Site"].map((t) => h("th", { scope: "col", text: t })));
    box.append(h("p", { text: "Select a value to see which entry it was read from, how it was checked and which script computed it." }));
    box.append(h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, head), body)));
  }
  const waiting = entries.length - final.length;
  if (waiting > 0) {
    box.append(h("p", { text: `${final.length ? "" : "No number has passed its final check yet, so none is shown. "}${waiting} ${waiting === 1 ? "number is" : "numbers are"} still being checked.` }));
  }
  return box;
}

export function buildDocs(limitsButton: HTMLElement, aboutButton: HTMLElement, layers: LayerEntry[]): void {
  const limits = dialog("Limits");
  limits.body.append(renderMarkdown(limitsText.replace(/^#\s.*\n/, ""), 1));
  limitsButton.addEventListener("click", () => limits.root.showModal());

  const about = dialog("About");
  const what = section(readmeText, "What it is");
  if (what) about.body.append(renderMarkdown(what, 1));
  about.body.append(h("h3", { text: "Data" }));
  const data = section(readmeText, "Data");
  if (data) about.body.append(renderMarkdown(data, 1));
  about.body.append(h("h3", { text: "On this map" }), sourceList(layers));
  const checked = h("div");
  about.body.append(h("h3", { text: "Checked numbers" }), checked);
  const si = section(readmeText, "Use of Super Intelligence (SI)");
  if (si) about.body.append(h("h3", { text: "Use of Super Intelligence (SI)" }), renderMarkdown(si, 1));
  // The animated explainer of the radar echoes: a page of its own, for those who want it.
  about.body.append(h("p", {}, h("a", { href: "explainer/", target: "_blank", rel: "noopener", text: "How the radar sees a peat dry season (animation)" })));
  if (canReplayIntro()) {
    const replay = h("button", { type: "button", class: "text-button", text: "Replay intro" });
    replay.addEventListener("click", () => {
      about.root.close();
      playIntro();
    });
    about.body.append(h("p", {}, replay));
  }
  let filled = false;
  aboutButton.addEventListener("click", () => {
    if (!filled) {
      filled = true;
      void numbers().then((el) => checked.append(el));
    }
    about.root.showModal();
  });
}
