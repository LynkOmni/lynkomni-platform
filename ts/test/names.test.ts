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

// ---------------------------------------------------------------- the 15 improvements (v0.81.0)
import { iconOf, spokenOf, speakable, similarOf, checkPlain, explainText, paperLines, nowCalled, forFamily, compareHtml, welcomeCard, namesIndexHtml, renameNotices, nameAsked, takeNameAsks, familiar, nameOpened, setKeepBrackets, namesFocusOf } from "../src/names.js";

test("marks, spoken forms and similar names are those of core/names.py", () => {
  for (const c of V.labels) {
    assert.equal(iconOf(c.name), c.icon, c.name);
    assert.equal(spokenOf(c.name), c.spoken, c.name);
    assert.deepEqual(similarOf(c.name), c.similar, c.name);
  }
  for (const c of V.speakable) assert.equal(speakable(c.text), c.expect, c.text);
});
test("messages, paper and the plain-word check agree with core/names.py", () => {
  for (const c of V.explain) { assert.equal(explainText(c.text), c.expect, c.text); assert.equal(explainText(c.text, undefined, "plain_first"), c.plain_first, c.text); }
  for (const c of V.paper) assert.deepEqual(paperLines(c.lines, undefined, c.width), c.expect, c.lines.join("|"));
  for (const c of V.check_plain) assert.deepEqual(checkPlain(c.word), c.expect, c.word);
  for (const c of V.now_called) assert.equal(nowCalled(c.old), c.expect, c.old);
  assert.equal(forFamily("lynkstat"), "LynkStat");
});
test("an old name still finds the new one, and look-alike names are compared side by side", () => {
  const e = nameEntries(undefined, "brand_first");
  assert.ok(e.some((x) => x.keywords.includes("LynkDash") && x.title === "LynkDash is now LynkStat."));
  assert.ok(e.some((x) => x.id === "name-compare:move" && x.subtitle === "LynkMotion, LynkTrace, LynkGuard, LynkSentry"));
  const c = compareHtml("LynkMotion");
  assert.ok(c.includes("LynkGuard") && c.includes("Which one do I need?"));
  assert.equal(namesFocusOf("open:compare-move"), "compare-move");
  assert.equal(namesFocusOf("help:article:names"), "");
  assert.equal(namesFocusOf("open:somewhere"), null);
});
test("the welcome card shows once; Names A to Z lists every name; a rename notice shows only to older accounts", () => {
  const say = (k: string) => k;
  assert.ok(welcomeCard("LynkQueue", say, [{ label: "Places", act: "hub:queue_places" }], { act: "nmw" }).includes('data-act="nmw:queue"'));
  assert.equal((namesIndexHtml().match(/<li id="name-/g) ?? []).length, V.labels.length);
  assert.ok(renameNotices(say, "2026-10-01", { act: "nmr" }).includes("LynkDash"));
  assert.equal(renameNotices(say, "2026-11-20", { act: "nmr" }), "");
});
test("brackets step back after ten openings unless kept; confusion is counted as totals only", () => {
  for (let i = 0; i < 10; i++) nameOpened("LynkSurvey");
  assert.equal(familiar("LynkSurvey"), true);
  setKeepBrackets(true); assert.equal(familiar("LynkSurvey"), false); setKeepBrackets(false);
  nameAsked("LynkStat", "note"); nameAsked("LynkStat", "compare");
  assert.deepEqual(takeNameAsks(), { stat: 2 });
  assert.deepEqual(takeNameAsks(), {});
});
