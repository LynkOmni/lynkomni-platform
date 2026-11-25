import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { sharedBaseRole, sharedMay, binnable, purgeDue, mayAudit, calendarSources, sharedSettle } from "../src/shared.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/shared.v1.json`, "utf8"));
const attempt = (f: () => unknown) => { try { return { value: f() }; } catch { return { error: true }; } };

test("the shared parts agree with the Python reference (CONNECT UPDATE 71.3)", () => {
  for (const c of V.base_role) assert.deepEqual(attempt(() => sharedBaseRole(c.a[0], c.a[1])), c.expect, JSON.stringify(c.a));
  for (const c of V.may) assert.deepEqual(attempt(() => sharedMay(c.a[0], c.a[1], c.a[2], c.a[3])), c.expect, JSON.stringify(c.a));
  for (const c of V.binnable) assert.equal(binnable(c.a), c.expect, c.a);
  for (const c of V.purge_due) assert.equal(purgeDue(c.a[0], c.a[1]), c.expect, JSON.stringify(c.a));
  for (const c of V.may_audit) assert.equal(mayAudit(c.a), c.expect, c.a);
  for (const c of V.settle) assert.deepEqual(attempt(() => sharedSettle(c.a[0], c.a[1], c.a[2])), c.expect, JSON.stringify(c.a));
  assert.deepEqual(calendarSources((s) => V.built[s]), V.calendar_sources);
});
