import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { findNames, unknownNames, labelText, partOf, nameLabel, nameEntries, whatIs, namePair } from "../src/names.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/names.v1.json`, "utf8"));

test("names are found exactly as core/names.py finds them", () => {
  for (const c of V.find) assert.deepEqual(findNames(c.text), c.expect, c.text);
  for (const c of V.unknown) assert.deepEqual(unknownNames(c.text), c.expect, c.text);
});
test("every label reads as core/names.py says, both ways round", () => {
  for (const c of V.labels) {
    assert.equal(labelText(c.name), c.brand_first, c.name);
    assert.equal(labelText(c.name, undefined, "plain_first"), c.plain_first, c.name);
    assert.equal(partOf(c.name), c.part_of, c.name);
  }
});
test("a label carries the plain word; plain words first swaps the order", () => {
  assert.equal(nameLabel("LynkStat", undefined, "label", "brand_first"), '<span class="lname lname-label" data-lname="LynkStat"><span class="lnm">LynkStat</span> <span class="lpl">Analytics</span></span>');
  assert.ok(nameLabel("LynkStat", undefined, "label", "plain_first").includes('<span class="lpl">Analytics</span> <span class="lnm">LynkStat</span>'));
  assert.ok(nameLabel("LynkStat", undefined, "compact").includes('title="Analytics"'));
  assert.deepEqual(namePair("LynkAcc", undefined, "plain_first"), { main: "Accounting", sub: "LynkAcc" });
});
test("search finds a product by its plain word or what it does", () => {
  const e = nameEntries(undefined, "brand_first");
  assert.ok(e.some((x) => x.title === "LynkAcc (Accounting)" && x.keywords.includes("Accounting")));
  assert.ok(e.find((x) => x.title.startsWith("LynkStat"))!.subtitle.includes("profit"));
  assert.equal(whatIs("LynkStat"), "LynkStat (Analytics): See your sales, profit and trends in one view.");
});
test("a word the page does not carry is never shown in English on another language's screen", () => {
  const french = (k: string) => (k === "nm_stat" ? "Analyses" : k);   // the page has plain words but no descriptions
  assert.equal(whatIs("LynkStat", french), "LynkStat (Analyses)");
});
