import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { PeopleHub, afterPaymentRating, counterCard, devicesCard, lynkNames, receptionCard, setupCard, surveyCard } from "../src/peoplehub.js";
import { AttendDesk, atDoor, checkInsView, peopleView, registerView, reportsView, visitorsView } from "../src/attenddesk.js";
import type { AtLook, AtPlan, AtTier } from "../src/attenddesk.js";
import { DEVICES } from "../src/interfaces.generated.js";
import { MIN_GROUP } from "../src/survey.js";

/** NEW UPDATE 4, section 3: the one people engine behind the Business app hub, the LynkPOS door, reception and counter and the
 *  rating after payment. Events carry no PIN, IDCN, face, finger, phone number or position; every choice is a button. */
const t = (k: string, v: Record<string, string | number> = {}): string => k + (Object.keys(v).length ? JSON.stringify(v) : "");
const match = (s: string, re: RegExp, m?: string): void => assert.ok(re.test(s), m ?? `${s.slice(0, 120)} should match ${re}`);
const noMatch = (s: string, re: RegExp, m?: string): void => assert.ok(!re.test(s), m ?? `${s.slice(0, 120)} should not match ${re}`);
const icon = (id: string): string => `<i data-icon="${id}"></i>`;
const SECRET = /pin|idcn_value|phone|position|lat|lng|face_data|finger_data/i;
const LOOK: AtLook = { t, icon, clock: () => "09:00", money: (c) => `$${(c / 100).toFixed(2)}`, online: true, partner: false, mayManage: true };
const PLAN = (price: number, people: number, extra: number | null, devices: number | null): AtPlan => ({ price_usd: price, people_included: people, extra_person_cents: extra, branches: null, managers: null, door_devices: devices });
const PLANS: Record<AtTier, AtPlan> = { free: PLAN(0, 15, null, 2), plus: PLAN(49.5, 50, 150, null), pro: PLAN(95, 50, 250, null), max: PLAN(179, 50, 400, null) };
/** Every event a screen writes must be a contract version 6 event: a known type, from an allowed origin, with its required fields,
 *  no field the contract does not have, and only values the contract lists. */
const CONTRACT = JSON.parse(readFileSync(new URL("../../../contract/event-payloads.v6.json", import.meta.url).pathname, "utf8")).events as Record<string, { origins: string[]; payload: { required?: string[]; properties: Record<string, { enum?: unknown[]; items?: { enum?: unknown[] } }> } }>;
function inContract(log: { type: string; payload: Record<string, unknown>; origin?: string }[]): void {
  for (const e of log) {
    const c = CONTRACT[e.type]; if (!c) throw new Error(`${e.type} is not a contract event`);
    assert.ok(c.origins.includes(e.origin ?? "device"), `${e.type} from ${e.origin ?? "device"}`);
    for (const r of c.payload.required ?? []) assert.ok(r in e.payload, `${e.type} needs ${r}`);
    for (const [k, v] of Object.entries(e.payload)) {
      const prop = c.payload.properties[k]; if (!prop) throw new Error(`${e.type} must not carry ${k}`);
      if (prop.enum) assert.ok(prop.enum.includes(v), `${e.type}.${k} = ${String(v)}`);
      if (prop.items?.enum) for (const x of v as unknown[]) assert.ok(prop.items.enum.includes(x), `${e.type}.${k} has ${String(x)}`);
    }
  }
}
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
  noMatch(atDoor(h.att, LOOK), new RegExp(eric.idcn), "the IDCN is never drawn");
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

test("every event the people screens write is a contract version 6 event", () => {
  const { h, log } = hub(); const ctx = { online: true, redraw: () => undefined, language: "en" };
  const eric = h.members.find((m) => m.set === "idcn")!, aline = h.members.find((m) => m.set === "finger_idcn")!;
  for (const d of eric.pin) h.doorDigit(d); for (const d of eric.idcn) h.doorDigit(d); h.pickChecker(aline.name); h.doorIdcn(); h.doorReset();
  for (const d of aline.pin) h.doorDigit(d); for (let i = 0; i < 3; i++) h.doorReader("fail"); for (let i = 0; i < 5; i++) { for (const d of "000001") h.doorDigit(d); h.pickChecker(eric.name); h.doorIdcn(); }
  assert.equal(aline.pinState, "blocked");
  h.act("ph:issue", ctx); const c = h.counters[0]!; h.callNext(c.id); h.sendTo(c.id, "PAY"); h.callNext(c.id); h.finish(c.id, "served"); h.counterState(c.id, "paused"); h.rate(4, "pos", "en");
  inContract(log);
});

test("LynkAttend dashboard: registration in order, a PIN only from LynkOmni and only online, never easy, never twice", () => {
  const log: { type: string; payload: Record<string, unknown>; origin?: string }[] = [];
  const d = new AttendDesk((type, payload, origin) => { log.push({ type, payload, origin }); }, PLANS); const ctx = { online: true, partner: false };
  d.startDraft(); d.input("at:name", "Amina K."); d.input("at:idnum", "DYY87HIO");
  assert.equal(d.register(), false); assert.equal(d.note, "ppl_at_too_few", "fewer than 4 digits: another ID document");
  d.input("at:idnum", "R4279"); d.act("at:set:face_idcn", ctx); assert.ok(d.register());
  const p = d.people.at(-1)!; assert.equal(p.idcn, "427900");
  assert.equal(d.confirm(p.id), false, "not before the person agrees");
  assert.equal(d.agree(p.id, "full_id_number", "427900"), false, "the full ID number, not the IDCN");
  assert.ok(d.agree(p.id, "full_id_number", "R4279")); assert.equal(d.confirm(p.id), false, "not before the face is enrolled");
  d.readers.face = false; assert.equal(d.enrol(p.id, "face"), false); d.readers.face = true; assert.ok(d.enrol(p.id, "face")); assert.ok(d.confirm(p.id));
  assert.equal(d.createPin(p.id, false), false, "PINs are created by the cloud: not offline");
  assert.ok(d.createPin(p.id, true)); match(p.pin, /^\d{6}$/);
  assert.equal(d.sendPin(p.id, "text", true, false), "coming_soon"); assert.equal(d.sendPin(p.id, "email", true, false), "sent");
  const pins = new Set(d.people.map((x) => x.pin)); assert.equal(pins.size, d.people.length);
  noMatch(peopleView(d, LOOK), new RegExp(p.pin), "hidden until Show"); d.act(`at:open:${p.id}`, ctx); d.act(`at:show:${p.id}`, ctx); match(peopleView(d, LOOK), new RegExp(p.pin));
  assert.equal(log.filter((e) => e.type === "AttendancePinShown").length, 1, "every Show is recorded");
  match(registerView(d, LOOK), /data-item="send_pin"/);
  inContract(log);
  for (const e of log) noMatch(JSON.stringify(e.payload), new RegExp(`${p.pin}|427900|R4279|Amina`));
});

test("LynkAttend dashboard: flags, hand check-in, missed check-out, visitors, requests and the Free limit", () => {
  const log: { type: string; payload: Record<string, unknown>; origin?: string }[] = []; let now = new Date(2026, 10, 18, 8, 0).getTime();
  const d = new AttendDesk((type, payload, origin) => { log.push({ type, payload, origin }); }, PLANS, () => now); const ctx = { online: true, partner: false };
  const [aline, eric, grace] = d.people as [typeof d.people[0], typeof d.people[0], typeof d.people[0]];
  d.doorDir("out"); for (const x of eric.pin) d.doorDigit(x); assert.equal(d.door.note, "ppl_at_not_in");
  d.doorDir("in"); for (const x of eric.pin) d.doorDigit(x); for (const x of eric.idcn) d.doorDigit(x); d.pickChecker(aline.name); d.doorIdcn();
  assert.deepEqual(eric.flags, ["checker_not_checked_in"]); assert.equal(d.messages.length, 1); d.notMe(eric.rec!);
  assert.deepEqual(d.recs[0]!.flags, ["checker_not_checked_in", "not_me"]);
  d.doorReset(); for (const x of eric.pin) d.doorDigit(x); assert.equal(d.door.note, "ppl_at_already_in");
  assert.equal(d.byHand(grace.id, ""), false); assert.ok(d.byHand(grace.id, "all_means_failed")); assert.deepEqual(grace.flags, ["by_hand"]);
  assert.equal(d.markNoCheckOut(18 * 60), 0); assert.equal(d.markNoCheckOut(19 * 60), 2, "2 hours after the 17:00 shift end");
  assert.ok(d.fixCheckOut(eric.rec!)); assert.equal(d.recs.find((r) => r.id === eric.rec)!.old.length, 1, "the old line is kept");
  match(checkInsView(d, LOOK), /ppl_flag_no_check_out/);
  d.vdraft = { name: "Visitor", host: aline.id, doc: "none", guardian: false }; assert.ok(d.visitorIn());
  assert.equal(d.visitors[0]!.state, "waiting_for_manager"); d.decideVisitor(d.visitors[0]!.id, "allow"); assert.equal(d.visitors[0]!.state, "inside");
  d.openFire(); assert.equal(d.fire!.staff.length + d.fire!.visitors.length, 2); match(visitorsView(d, LOOK), /ppl_at_fire_count/);
  d.ask(aline.id, "delete_my_details"); d.daysPass(25); assert.equal(d.requests[0]!.reminded, 3); assert.ok(d.person(aline.id));
  const used = d.group().used; d.daysPass(5); assert.equal(d.person(aline.id), undefined, "deleted by itself after 30 days"); assert.equal(d.group().used, used, "the PIN is never given again");
  match(reportsView(d, LOOK), /ppl_at_did_details_deleted/);
  d.tier = "free"; d.people.length = 0; for (let i = 0; i < 15; i++) { d.startDraft(); d.input("at:name", `P${i}`); d.input("at:idnum", `ID${1000 + i}`); assert.ok(d.register()); }
  d.startDraft(); d.input("at:name", "One more"); d.input("at:idnum", "ID9999"); assert.equal(d.register(), false); assert.equal(d.note, "ppl_at_limit");
  void ctx; now += 1; inContract(log);
});
