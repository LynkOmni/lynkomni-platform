import { test } from "node:test";
import assert from "node:assert/strict";
import { PeopleHub, afterPaymentRating, counterCard, devicesCard, doorScreen, lynkNames, receptionCard, setupCard, surveyCard } from "../src/peoplehub.js";
import { DEVICES } from "../src/interfaces.generated.js";
import { MIN_GROUP } from "../src/survey.js";

/** NEW UPDATE 4, section 3: the one people engine behind the Business app hub, the LynkPOS door, reception and counter and the
 *  rating after payment. Events carry no PIN, IDCN, face, finger, phone number or position; every choice is a button. */
const t = (k: string, v: Record<string, string | number> = {}): string => k + (Object.keys(v).length ? JSON.stringify(v) : "");
const match = (s: string, re: RegExp, m?: string): void => assert.ok(re.test(s), m ?? `${s.slice(0, 120)} should match ${re}`);
const noMatch = (s: string, re: RegExp, m?: string): void => assert.ok(!re.test(s), m ?? `${s.slice(0, 120)} should not match ${re}`);
const icon = (id: string): string => `<i data-icon="${id}"></i>`;
const SECRET = /pin|idcn_value|phone|position|lat|lng|face_data|finger_data/i;
function hub(): { h: PeopleHub; log: { type: string; payload: Record<string, unknown>; origin?: string }[] } {
  const log: { type: string; payload: Record<string, unknown>; origin?: string }[] = [];
  return { h: new PeopleHub((type, payload, origin) => { log.push({ type, payload, origin }); }), log };
}

test("device names come only from the register: a screen that only shows is offered for LynkQueue alone", () => {
  const all = [...new Set(DEVICES.devices.map((d) => d.lynk_name).filter(Boolean))];
  assert.deepEqual(lynkNames(DEVICES, "queue"), all);
  assert.ok(!lynkNames(DEVICES, "attendance").includes("LynkDScreen") && !lynkNames(DEVICES, "survey").includes("LynkDScreen"));
  assert.ok(lynkNames(DEVICES, "attendance").includes("LynkPOS"));
});

test("setup and Add a device: three ways, a one-time Lynk Code, owner or manager only", () => {
  const { h } = hub();
  assert.ok(h.act("ph:setup:queue:many_places", { online: true, redraw: () => undefined, language: "en" }));
  assert.equal(h.setup.queue, "many_places");
  h.act("ph:setup:queue:everything", { online: true, redraw: () => undefined, language: "en" });
  assert.equal(h.setup.queue, "many_places", "an unknown setup is ignored");
  match(setupCard(h, "queue", t), /aria-pressed="true"><strong>ppl_setup_many_places/);
  h.act("ph:pick:attendance:LynkKiosk", { online: false, redraw: () => undefined, language: "en" });
  h.act("ph:pair:attendance", { online: false, redraw: () => undefined, language: "en" });
  assert.equal(h.paired[0]?.state, "queued", "offline the code waits; it is never shown as confirmed");
  match(h.paired[0]?.code ?? "", /^[2-9A-HJ-NP-Z]{6}$/);
  match(devicesCard(h, "attendance", DEVICES, t, icon, false), /disabled/);
});

test("the door: PIN, then the person's set; IDCN needs a checker who is not the person; no secret in any event", () => {
  const { h, log } = hub();
  const eric = h.members.find((m) => m.set === "idcn")!, grace = h.members.find((m) => m.name !== eric.name)!;
  for (const d of "111111") h.doorDigit(d);
  assert.equal(h.door.note, "ppl_door_pin_wrong", "an easy or unknown PIN is refused");
  for (const d of eric.pin) h.doorDigit(d);
  assert.equal(h.door.out?.means, "idcn");
  noMatch(doorScreen(h, t, icon, () => "09:00"), new RegExp(eric.idcn), "the IDCN is never drawn");
  for (const d of eric.idcn) h.doorDigit(d);
  h.pickChecker(eric.name); assert.equal(h.door.checker, null, "a person never checks themself");
  h.pickChecker(grace.name); h.doorIdcn();
  assert.equal(h.door.out?.result, "in");
  const ev = log.find((e) => e.type === "CheckedIn")!;
  assert.deepEqual(Object.keys(ev.payload).sort(), ["checker_id", "device_id", "flags", "means", "member_id", "record_id"]);
  assert.deepEqual(ev.payload["flags"], ["checker_not_checked_in"]);
  for (const e of log) noMatch(JSON.stringify(e.payload), new RegExp(`${eric.pin}|${eric.idcn}`));
  for (const e of log) for (const k of Object.keys(e.payload)) noMatch(k, SECRET);
});

test("finger or face first, IDCN last: three failed reads fall back and are marked as a backup", () => {
  const { h, log } = hub();
  const aline = h.members.find((m) => m.set === "finger_idcn")!, eric = h.members.find((m) => m.name !== aline.name)!;
  for (const d of aline.pin) h.doorDigit(d);
  assert.equal(h.door.out?.means, "finger");
  for (let i = 0; i < 3; i++) h.doorReader("fail");
  assert.equal(h.door.out?.means, "idcn");
  for (const d of aline.idcn) h.doorDigit(d);
  h.pickChecker(eric.name); h.doorIdcn();
  assert.equal(log.at(-1)?.payload["backup_from"], "finger_failed");
});

test("reception and counter: codes from this device's block, the fair order, three calls before missed", () => {
  const { h, log } = hub();
  const ctx = { online: false, redraw: () => undefined, language: "en" };
  h.act("ph:section:PAY", ctx); h.act("ph:issue", ctx);
  const issued = log.find((e) => e.type === "TicketIssued")!;
  assert.equal(issued.payload["section"], "PAY"); match(String(issued.payload["code"]), /^[2-9A-HJ-NP-Z]{6}$/);
  match(receptionCard(h, t, icon), /ppl_place/);
  const c = h.counters[0]!;
  const first = h.callNext(c.id)!;
  assert.equal(first.section, "SRV", "the oldest ticket comes first; staff never choose");
  h.finish(c.id, "missed"); assert.equal(first.state, "called", "missed only after three calls");
  h.callAgain(c.id); h.callAgain(c.id); h.callAgain(c.id);
  assert.equal(log.filter((e) => e.type === "TicketCalled").length, 3);
  h.finish(c.id, "missed"); assert.equal(first.state, "missed");
  h.counterState(c.id, "paused"); match(counterCard(h, c.id, t, icon), /ph:call:[^"]+" disabled/);
});

test("the rating after payment: one answer per tap, results only from five answers, off means not shown", () => {
  const { h, log } = hub();
  h.ratings = [];
  match(surveyCard(h, t, true), new RegExp(`ppl_too_few\\{&quot;n&quot;:${MIN_GROUP}\\}`));
  for (const n of [5, 4, 4, 3, 5]) assert.ok(h.rate(n, "pos", "fr"));
  assert.equal(h.results()?.n, 5);
  assert.equal(log.filter((e) => e.type === "SurveyAnswered").length, 5);
  assert.deepEqual(log[0]?.payload["answers"], [{ q: "after_payment", number: 5 }]);
  assert.equal(h.rate(9, "pos", "fr"), false);
  match(afterPaymentRating(h, true, null, t, icon), /ppl:rate:1/);
  match(afterPaymentRating(h, false, null, t, icon), /ppl_rate_us/, "a screen that only shows gives the QR");
  h.afterPayment = false; assert.equal(afterPaymentRating(h, true, null, t, icon), "");
});
