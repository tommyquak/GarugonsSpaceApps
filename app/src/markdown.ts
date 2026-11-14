// Written with Super Intelligence (SI) assistance.
// A small Markdown renderer for the project's own documents: headings, paragraphs, lists,
// tables, bold, code and links. It builds DOM nodes from text and never sets raw HTML.
import { h } from "./dom";

const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)\s]+\)|https?:\/\/[^\s|)]+)/g;

function link(text: string, href: string): HTMLElement {
  return h("a", { href, target: "_blank", rel: "noopener", text });
}

function inline(text: string): (Node | string)[] {
  return text.split(INLINE).map((part) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) return h("strong", {}, ...inline(part.slice(2, -2)));
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) return h("code", { text: part.slice(1, -1) });
    const named = /^\[([^\]]+)\]\(([^)\s]+)\)$/.exec(part);
    if (named) return /^https?:/.test(named[2]) ? link(named[1], named[2]) : named[1];
    if (/^https?:\/\//.test(part)) {
      const href = part.replace(/[.,;]+$/, "");
      return h("span", {}, link(href, href), part.slice(href.length));
    }
    return part;
  });
}

function cells(line: string): string[] {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
}

export function renderMarkdown(text: string, headingShift = 0): DocumentFragment {
  const out = document.createDocumentFragment();
  const lines = text.replace(/\r/g, "").split("\n");
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i += 1;
      continue;
    }
    const heading = /^(#{1,5})\s+(.*)$/.exec(line);
    if (heading) {
      const level = Math.min(6, heading[1].length + headingShift);
      out.append(h(`h${level}` as "h2", {}, ...inline(heading[2])));
      i += 1;
      continue;
    }
    if (line.trim().startsWith("|") && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1] ?? "")) {
      const head = h("tr", {}, ...cells(line).map((c) => h("th", { scope: "col" }, ...inline(c))));
      const body = h("tbody");
      i += 2;
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        body.append(h("tr", {}, ...cells(lines[i]).map((c) => h("td", {}, ...inline(c)))));
        i += 1;
      }
      out.append(h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, head), body)));
      continue;
    }
    const item = /^\s*([-*]|\d+\.)\s+(.*)$/.exec(line);
    if (item) {
      const list = h(/\d/.test(item[1]) ? "ol" : "ul");
      while (i < lines.length) {
        const next = /^\s*([-*]|\d+\.)\s+(.*)$/.exec(lines[i]);
        if (!next) break;
        list.append(h("li", {}, ...inline(next[2])));
        i += 1;
      }
      out.append(list);
      continue;
    }
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,5}\s|\s*([-*]|\d+\.)\s|\s*\|)/.test(lines[i])) {
      para.push(lines[i].trim());
      i += 1;
    }
    if (para.length) out.append(h("p", {}, ...inline(para.join(" "))));
    else i += 1;
  }
  return out;
}

// The text under one "## Title" heading, up to the next heading of the same level.
export function section(text: string, title: string): string | null {
  const lines = text.replace(/\r/g, "").split("\n");
  const start = lines.findIndex((l) => l.trim().toLowerCase() === `## ${title}`.toLowerCase());
  if (start < 0) return null;
  let end = lines.findIndex((l, k) => k > start && /^##?\s/.test(l));
  if (end < 0) end = lines.length;
  return lines.slice(start + 1, end).join("\n").trim();
}
