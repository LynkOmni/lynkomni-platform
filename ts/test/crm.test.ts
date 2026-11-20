import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { kindsFor, relationOk, fieldLimit, fieldValueOk, requiredMissing, segment, stageMove, closeOk, forecast, leadScore, maySee, visibleFields,
  caseDue, caseLate, timeline, normalise, duplicates, merge, consentOk, requestDue, sensitiveAllowed } from "../src/crm.js";
import { CRM as C } from "../src/crm.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/crm.v1.json`, "utf8"));

test("record kinds, relations, fields and segments agree with the Python reference (OFFICE UPDATE 66.4)", () => {
  for (const c of V.kinds) assert.deepEqual(kindsFor(C, c.e, c.own), c.expect, JSON.stringify(c));
  for (const c of V.relations) assert.equal(relationOk(C, c.r, c.e), c.expect, JSON.stringify(c));
  for (const [t, want] of Object.entries(V.limits)) assert.equal(fieldLimit(C, t), want, t);
  for (const c of V.values) assert.equal(fieldValueOk(c.t, c.v), c.expect, JSON.stringify(c));
  for (const c of V.required) assert.deepEqual(requiredMissing(c.f, c.v), c.expect);
  for (const c of V.segments) assert.deepEqual(segment(V.records, c.c), c.expect, JSON.stringify(c.c));
});
test("pipelines, forecast, lead scores and access", () => {
  for (const c of V.moves) assert.equal(stageMove(C, c.from, c.to), c.expect);
  for (const c of V.close) assert.equal(closeOk(C, c.s, c.r), c.expect);
  for (const c of V.forecast) assert.deepEqual(forecast(C, c.d, c.c), c.expect);
  for (const c of V.scores) assert.deepEqual(leadScore(C, c.s), c.expect);
  for (const c of V.see) assert.equal(maySee(C, V.viewers[c.v], V.rows[c.r], c.vis ?? undefined), c.expect, JSON.stringify(c));
  for (const c of V.hidden) assert.deepEqual(visibleFields([{ id: "a" }, { id: "salary", hidden_from: ["staff", "manager"] }, { id: "b", hidden_from: ["staff"] }], c.role), c.expect);
});
test("cases, the full picture, clean records, consent and data requests", () => {
  for (const c of V.cases) { assert.equal(caseDue(C, c.o, c.p, c.pause, c.own), c.due); assert.equal(caseLate(C, c.now, c.o, c.p, c.ans, c.pause, c.own), c.late); }
  for (const c of V.timeline) assert.deepEqual(timeline(C, V.items, c.links, c.roles), c.expect, JSON.stringify(c));
  for (const [s, want] of Object.entries(V.normalise)) assert.equal(normalise(s), want, s);
  assert.deepEqual(duplicates(V.people), V.duplicates);
  assert.deepEqual(V.duplicates.map((g: string[]) => merge(V.people.filter((p: { id: string }) => g.includes(p.id)))), V.merge);
  for (const c of V.consent) assert.equal(consentOk(V.consents, c.ch, c.mk), c.expect, JSON.stringify(c));
  for (const c of V.due) assert.equal(requestDue(C, c.d, V.packs[c.p]), c.expect);
  for (const c of V.sensitive) assert.equal(sensitiveAllowed(C, c.k, c.e, V.packs[c.p]), c.expect, JSON.stringify(c));
});
