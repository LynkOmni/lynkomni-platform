import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { canRun, codeValid, countsFor, deliveryWays, downgrade, fitScreen, hardwareAdvice, inUse, mayConnect, newCode, reapprovalDue, requestState, slots, tones } from "../src/emulators.js";
import { EMULATOR_REGISTER as R } from "../src/emulators.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/emulators.v1.json`, "utf8"));
const CONNS = [
  { device: "d1", emulator: "pos.merchant_phone", connected: true }, { device: "d1", emulator: "rewards.till", connected: true },
  { device: "d2", emulator: "pos.counter_tablet", connected: true }, { device: "d3", emulator: "pos.terminal", connected: true, practice: true },
  { device: "d4", emulator: "queue.board", connected: true }, { device: "d5", emulator: "pos.kitchen_screen", connected: false },
];

test("counting and the plan agree with the Python reference", () => {
  for (const [id, fam] of Object.entries(V.counts_for)) assert.equal(countsFor(R, id), fam, id);
  for (const [fam, n] of Object.entries(V.in_use)) assert.equal(inUse(R, fam, CONNS), n, fam);
  for (const c of V.may_connect) assert.deepEqual(mayConnect(R, c.limit, c.family, CONNS, c.new, c.extra), c.result, JSON.stringify(c));
  for (const c of V.downgrade) assert.deepEqual(downgrade(R, c.limit, c.family, CONNS), c.result, JSON.stringify(c));
  assert.equal(slots(R, "lynkpos", "free"), 1);
  assert.equal(R.extra_slot_cents, 200);
});
test("codes work once, expire, and are Lynk Codes", () => {
  for (const c of V.code_valid) assert.equal(codeValid(R, c.issued, c.now, c.used), c.valid, JSON.stringify(c));
  for (const c of V.new_code) assert.equal(newCode(c.n), c.code, String(c.n));
});
test("the check before assigning and the hardware helper agree", () => {
  for (const c of V.can_run) assert.deepEqual(canRun(R, c.emulator, c.caps), c.result, `${c.emulator} ${JSON.stringify(c.caps)}`);
  for (const c of V.hardware) assert.deepEqual(hardwareAdvice(R, c.kind, c.os), c.advice, `${c.kind} on ${c.os}`);
});
test("key tones, the delivery menu, states, re-approval and screen fit agree", () => {
  for (const c of V.tones) assert.deepEqual(tones(c.manager, c.user, c.customer_facing, c.silent, c.quiet_hours, c.vibrates), c.result, JSON.stringify(c));
  for (const c of V.delivery) assert.deepEqual(deliveryWays(c.caps, c.online, c.printer_ready, c.customer_known, c.contact_given), c.ways, JSON.stringify(c));
  for (const [step, s] of Object.entries(V.request_state)) assert.equal(requestState(step), s, step);
  for (const c of V.reapproval_due) assert.equal(reapprovalDue(R, c.last, c.today), c.due, JSON.stringify(c));
  for (const c of V.fit) assert.deepEqual(fitScreen(R, c.screen[0], c.screen[1], c.design[0], c.design[1]), c.result, JSON.stringify(c));
});
