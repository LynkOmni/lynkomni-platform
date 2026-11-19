import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { canRun, cheaperTier, codeValid, countsFor, deliveryWays, downgrade, fitScreen, hardwareAdvice, inUse, mayConnect, newCode, reapprovalDue, requestState, slots, tones } from "../src/emulators.js";
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
  for (const c of V.cheaper_tier) assert.equal(cheaperTier(R, c.family, c.tier, c.extras), c.next, JSON.stringify(c));
  assert.equal(R.extra_cents["lynkpos"], 800);
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

test("keys of different kinds sound different, like a real device (owner, 19 November 2026)", async () => {
  const { soundForAct } = await import("../src/keytones.js");
  const { KEY_TONE } = await import("../src/signin.js");
  const S = R.sounds;
  // every number key has its own keypad pair, the same pairs the PIN pad uses, and no two keys share one
  const pairs = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"].map((d) => S.keypad?.[d]);
  for (const [i, p] of pairs.entries()) assert.deepEqual(p, KEY_TONE[String(i)], `key ${i}`);
  assert.equal(new Set(pairs.map((p) => String(p))).size, 10);
  // every kind a key can be has its own tone and vibration in the tokens
  for (const k of ["key", "confirm", "cancel", "clear", "nav", "tab", "toggle_on", "toggle_off", "scan", "printer", "pin_same", "error", "paid"]) {
    assert.ok(S.tones[k]?.length, `tone ${k}`); assert.ok(S.vibrate[k], `vibration ${k}`);
  }
  assert.ok(S.vibrate["digit"]);
  const tonesOf = new Set(["confirm", "cancel", "clear", "nav", "tab", "toggle_on", "toggle_off", "key"].map((k) => JSON.stringify(S.tones[k])));
  assert.equal(tonesOf.size, 8, "no two kinds share a tone");
  // the actions each emulator uses
  assert.equal(soundForAct("d5"), "digit:5"); assert.equal(soundForAct("pin:0"), "digit:0"); assert.equal(soundForAct("at:digit:7"), "digit:7");
  assert.equal(soundForAct("star"), "digit:*"); assert.equal(soundForAct("hash"), "digit:#"); assert.equal(soundForAct("d00"), "digit:0");
  assert.equal(soundForAct("enter"), "confirm"); assert.equal(soundForAct("call"), "confirm"); assert.equal(soundForAct("pin:ok"), "confirm");
  assert.equal(soundForAct("clear"), "clear"); assert.equal(soundForAct("pin:clear"), "clear");
  assert.equal(soundForAct("cancel"), "cancel"); assert.equal(soundForAct("end"), "cancel");
  assert.equal(soundForAct("nav:up"), "nav"); assert.equal(soundForAct("pad:left"), "nav"); assert.equal(soundForAct("menu"), "nav"); assert.equal(soundForAct("soft:left"), "nav");
  assert.equal(soundForAct("tab:home"), "tab");
  assert.equal(soundForAct("x", { pressed: false }), "toggle_on"); assert.equal(soundForAct("x", { pressed: true }), "toggle_off");
  assert.equal(soundForAct("reprint"), "printer"); assert.equal(soundForAct("add:p1"), "key");
  // a PIN, door code or ID number follows the manager's choice: per key, or one same tone so nobody nearby can tell keys apart
  assert.equal(soundForAct("d4", { privateEntry: true, pinTones: "same" }), "pin_same");
  assert.equal(soundForAct("d4", { privateEntry: true, pinTones: "per_key" }), "digit:4");
  assert.equal(soundForAct("d4", { privateEntry: false, pinTones: "same" }), "digit:4");
});
