import { test } from "node:test";
import assert from "node:assert/strict";
import { listToolbarHtml, recordHeaderHtml, saveBarHtml, RECORD_TABS } from "../src/pagekit.js";
import { NAV } from "../src/navigation.generated.js";

const t = (k: string): string => `[${k}]`;
test("a record header has its name, one main button and the same four tabs (73.6)", () => {
  const html = recordHeaderHtml(NAV, t, { title: "Invoice LOINV-1", main: { label: "Send", act: "send" } });
  assert.deepEqual([...html.matchAll(/data-act="rtab:([a-z]+)"/g)].map((m) => m[1]), [...RECORD_TABS]);
  assert.equal((html.match(/class="primary pk-main"/g) ?? []).length, 1, "one main button");
  assert.ok(/aria-selected="true">\[nv_details\]/.test(html), "Details is open first");
  const many = recordHeaderHtml(NAV, t, { title: "x", tabs: ["a", "b", "c", "d", "e", "f", "g", "h"], tabLabel: (id) => id });
  assert.equal([...many.matchAll(/role="tab"/g)].length, 7, "at most seven tabs, the rest under More");
  assert.ok(/\[nv_more\]/.test(many));
});
test("the list toolbar keeps the search label visible and marks the chip that is on", () => {
  const html = listToolbarHtml(t, { hint: "e.g. LOINV-0042", chips: [{ id: "all", label: "All", on: true }, { id: "late", label: "Late" }] });
  assert.ok(/<span>\[nv_search\]<\/span><input/.test(html), "a visible label, never only a hint");
  assert.ok(/placeholder="e.g. LOINV-0042"/.test(html), "an example as the hint");
  assert.ok(/data-act="filter:all" aria-pressed="true"/.test(html));
  assert.ok(/data-act="filter:late" aria-pressed="false"/.test(html));
});
test("the save bar escapes its words and can be disabled", () => {
  assert.ok(/disabled/.test(saveBarHtml({ label: "<Save>", act: "save", disabled: true })));
  assert.ok(/&lt;Save&gt;/.test(saveBarHtml({ label: "<Save>", act: "save" })));
});
