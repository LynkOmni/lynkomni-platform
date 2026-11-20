import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { cohorts, whatIf, measureNames, evaluate, scope, freshness, exportDates, goal, publicTable } from "../src/stats.js";
import { STATS as S } from "../src/stats.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/stats.v1.json`, "utf8"));
const attempt = (f: () => unknown) => { try { return { value: f() }; } catch { return { error: true }; } };

test("groups over time, what if and own measures agree with the Python reference (SERVICES UPDATE 67.5)", () => {
  for (const c of V.cohorts) assert.deepEqual(cohorts(S, c.buys), c.expect);
  for (const c of V.what_if) assert.deepEqual(whatIf(S, c.base, c.changes, c.e), c.expect, JSON.stringify(c));
  for (const c of V.measures) {
    assert.deepEqual(attempt(() => measureNames(S, c.expr)), c.names, c.expr);
    assert.deepEqual(attempt(() => evaluate(S, c.expr, V.figures)), c.value, c.expr);
  }
});
test("scope, freshness, exports, goals and public reports agree with the Python reference", () => {
  for (const c of V.scope) assert.deepEqual(scope(V.rows, c.viewer, c.rules), c.expect);
  for (const c of V.freshness) assert.deepEqual(freshness(S, c.u, c.n, c.k, ["till-1", "till-2", "web"], ["till-1"]), c.expect);
  for (const c of V.exports) assert.deepEqual(exportDates(c.start, c.every, c.count), c.expect, JSON.stringify(c));
  for (const c of V.goals) assert.deepEqual(goal(c.a, c.t, c.e), c.expect, JSON.stringify(c));
  assert.deepEqual(publicTable(S, [{ group: "north", n: 12, value: 400 }, { group: "south", n: 4, value: 90 }, { group: "east", n: 5, value: 0 }]), V.public);
});
test("an estimate is always labelled and a small group is never shown", () => {
  assert.equal(whatIf(S, { units: 1, price_minor: 1, unit_cost_minor: 0, staff_minor: 0 }, {}).estimate, true);
  assert.equal(publicTable(S, [{ group: "x", n: S.public.min_group - 1, value: 1 }])[0]!.value, null);
});
