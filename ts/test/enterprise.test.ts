import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { flowSteps, flowMayApprove, roleProblems, splitCharges, mayDelete, dataRegion, suspendedBy, parseAmount, parseDate, moveInCheck } from "../src/enterprise.js";
import { ENTERPRISE as E } from "../src/enterprise.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/enterprise.v1.json`, "utf8"));

test("approval flows, own roles, charges, keeping and region agree with the Python reference (OFFICE UPDATE 66.5)", () => {
  for (const c of V.steps) assert.deepEqual(flowSteps(E, V.flow, c.amount, c.dept), c.expect, JSON.stringify(c));
  for (const c of V.approve) assert.deepEqual(flowMayApprove(V.approve_steps, c.approvals, "u1", c.who, c.role, c.away), c.expect, JSON.stringify(c));
  for (const c of V.roles) assert.deepEqual(roleProblems(E, c.perms, c.apart), c.expect, JSON.stringify(c));
  for (const c of V.split) assert.deepEqual(splitCharges(c.t, c.s), c.expect);
  for (const c of V.delete) assert.equal(mayDelete(c.age, c.policy, c.law, c.held), c.expect, JSON.stringify(c));
  for (const c of V.region) assert.equal(dataRegion(c.choice, c.pack), c.expect, JSON.stringify(c));
  assert.equal(suspendedBy(E, 600), V.suspended);
});
test("Move in reads amounts and dates exactly and reports every problem (OFFICE UPDATE 66.6)", () => {
  for (const c of V.amounts) assert.equal(parseAmount(c.t, c.d), c.expect, JSON.stringify(c));
  for (const c of V.dates) assert.equal(parseDate(c.t, c.f), c.expect, JSON.stringify(c));
  for (const c of V.checks) assert.deepEqual(moveInCheck(E, c.kind, c.header, c.rows, c.decimals ?? 2, "iso", c.known ?? null, c.accounts ?? null), c.expect, c.kind);
});
