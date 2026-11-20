import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { certainty, work, needsNotAdviser, mayAct, remember, recall, effectiveLimit, bulk, guard, planMove, laterOk, warning, askAbout, gate, languageReady, skillLevel } from "../src/assisttrust.js";
import { TRUST } from "../src/assisttrust.generated.js";
import { CHAT } from "../src/chat.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/assist-trust.v1.json`, "utf8"));

test("how sure, the working and the adviser line agree with the Python reference (ASSIST UPDATE)", () => {
  for (const c of V.certainty) assert.equal(certainty(c.o), c.expect, JSON.stringify(c.o));
  for (const c of V.work) assert.deepEqual(work(c.parts), c.expect, JSON.stringify(c.parts));
  for (const [t, want] of Object.entries(V.adviser)) assert.equal(needsNotAdviser(TRUST, t), want, t);
});
test("content is never obeyed and memory stays under control", () => {
  for (const [s, want] of Object.entries(V.sources)) assert.deepEqual(mayAct(TRUST, s), want, s);
  for (const c of V.memory) assert.deepEqual(remember(TRUST, CHAT, { kind: c.kind, scope: c.scope, text: c.text, ctx_scope: c.ctx, memory_on: c.on, asked: c.asked, sensitive: c.sensitive, count: c.count, code_words: V.words }), c.expect, JSON.stringify(c));
  for (const c of V.recall) assert.deepEqual(recall(TRUST, V.items, c.scope, c.role), c.expect, JSON.stringify(c));
});
test("previews, limits, the second approver, pause, practice and plans agree", () => {
  for (const c of V.limits) assert.equal(effectiveLimit(c.r, c.o), c.expect, JSON.stringify(c));
  for (const [n, want] of Object.entries(V.bulk)) assert.deepEqual(bulk(TRUST, Number(n)), want, n);
  for (const c of V.guard) assert.deepEqual(guard(TRUST, c.g), c.expect, JSON.stringify(c.g));
  for (const c of V.plans) assert.equal(planMove(TRUST, c.from, c.to), c.expect, JSON.stringify(c));
  for (const [d, want] of Object.entries(V.later)) assert.equal(laterOk(TRUST, Number(d)), want, d);
});
test("warnings, Ask about this and the quality gates agree", () => {
  for (const c of V.warnings) assert.deepEqual(warning(TRUST, c.check, c.o), c.expect, JSON.stringify(c));
  for (const c of V.ask) assert.deepEqual(askAbout(TRUST, c.t, c.rows), c.expect, JSON.stringify(c));
  for (const c of V.gate) assert.deepEqual(gate(TRUST, c.before, c.after), c.expect, JSON.stringify(c));
  for (const c of V.language) assert.equal(languageReady(TRUST, c.x[0], c.x[1], c.x[2]), c.expect, JSON.stringify(c.x));
  for (const c of V.skill) assert.equal(skillLevel(TRUST, c.x[0], c.x[1], c.x[2]), c.expect, JSON.stringify(c.x));
});
