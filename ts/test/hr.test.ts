import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { hrVisibleFields, hrSpecialAllowed, onPayroll, leaveMinimum, carryOver, leaveBalance, leaveRequestOk, hrMayApprove, leaveClashes, absenceCounts,
  hrChecklist, finalPayReady, probationEnd, expiryStage, reviewShown, payChangeOk, overtimeMinutes, overtimePay, payrollFigures, hrHeadcount,
  hrCaseMaySee, hrCaseDeadline, hrCaseNext, hrAssistMay, hrTierHas, hrDay, hrIso } from "../src/hr.js";
import { HR as H } from "../src/hr.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/hr.v1.json`, "utf8"));
const P = (k: string) => V.packs[k];

test("records, special details and leave agree with the Python reference (SIX SERVICES UPDATE 69.3)", () => {
  for (const c of V.fields) assert.deepEqual(hrVisibleFields(H, c.role, c.self), c.expect, JSON.stringify(c));
  for (const c of V.special) assert.equal(hrSpecialAllowed(H, c.k, P(c.p)), c.expect, JSON.stringify(c));
  for (const [k, want] of Object.entries(V.payroll_kinds)) assert.equal(onPayroll(H, k), want, k);
  for (const c of V.minimum) assert.equal(leaveMinimum(c.k, P(c.p)), c.expect, JSON.stringify(c));
  for (const c of V.carry) assert.equal(carryOver(H, c.r, c.cap ?? undefined), c.expect, JSON.stringify(c));
  for (const c of V.balance) assert.equal(leaveBalance(c.e, c.t, c.c), c.expect);
  for (const c of V.request) assert.equal(leaveRequestOk(H, c.k, c.h, c.b), c.expect, JSON.stringify(c));
  for (const c of V.approve) assert.equal(hrMayApprove(c.a, c.b), c.expect, JSON.stringify(c));
  for (const c of V.clashes) assert.deepEqual(leaveClashes(H, c.n, V.away, V.days, c.share ?? undefined), c.expect, JSON.stringify(c));
  assert.deepEqual(absenceCounts(V.absence.in), V.absence.expect);
});
test("joining, leaving, probation, expiry, reviews and pay", () => {
  for (const c of V.checklists) assert.deepEqual(hrChecklist(H, c.k, c.d), c.expect, JSON.stringify(c));
  for (const c of V.final_pay) assert.equal(finalPayReady(c.d), c.expect);
  for (const c of V.probation) assert.equal(probationEnd(H, c.s, c.m ?? undefined), c.expect, JSON.stringify(c));
  for (const c of V.expiry) assert.equal(expiryStage(H, c.e, c.t), c.expect, JSON.stringify(c));
  for (const c of V.reviews) assert.equal(reviewShown(H, c.k, c.n), c.expect, JSON.stringify(c));
  for (const c of V.pay) assert.equal(payChangeOk(c.p, c.a, c.i, c.b, c.s), c.expect, JSON.stringify(c));
  for (const c of V.overtime) { assert.equal(overtimeMinutes(H, c.w, P(c.p)), c.min); assert.equal(overtimePay(H, c.min, c.h, P(c.p)), c.pay, JSON.stringify(c)); }
  for (const c of V.payroll) assert.deepEqual(payrollFigures(H, V.staff, P(c.p)), c.expect, c.p);
  for (const c of V.headcount) assert.deepEqual(hrHeadcount(c.pos, c.b), c.expect);
});
test("cases, LynkAssist, tiers and dates", () => {
  for (const c of V.case_see) assert.equal(hrCaseMaySee(H, c.r, c.n), c.expect, JSON.stringify(c));
  for (const c of V.case_steps) { assert.equal(hrCaseDeadline(H, c.s, 20000), c.deadline, c.s); assert.equal(hrCaseNext(H, c.s), c.next, c.s); }
  for (const [a, want] of Object.entries(V.assist)) assert.equal(hrAssistMay(H, a), want, a);
  for (const c of V.tiers) assert.equal(hrTierHas(H, c.t, c.f), c.expect, JSON.stringify(c));
  for (const c of V.dates) { assert.equal(hrDay(c.iso), c.day, c.iso); assert.equal(hrIso(c.day), c.back, c.iso); }
});
