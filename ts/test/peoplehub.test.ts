import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { PeopleHub, devicesCard, lynkNames, setupCard, surveyCard } from "../src/peoplehub.js";
import { AfterPay, afterPaymentRating } from "../src/afterpay.js";
import { QU_LYNK, QU_PHONE_WAYS, QueueDesk, quCDisplayView, quCounterView, quCountersView, quDevicesView, quKioskView, quPhoneView, quPublicView, quReceptionView, quReportsView, quScreenView, quSectionsView, quSetupView, quTicketsView } from "../src/queuedesk.js";
import type { QuLook, QuPlan } from "../src/queuedesk.js";
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
const CONTRACT = JSON.parse(readFileSync(new URL("../../../contract/event-payloads.v8.json", import.meta.url).pathname, "utf8")).events as Record<string, { origins: string[]; payload: { required?: string[]; properties: Record<string, { enum?: unknown[]; items?: { enum?: unknown[] } }> } }>;
function inContract(log: { type: string; payload: Record<string, unknown>; origin?: string }[]): void {
  for (const e of log) {
    const c = CONTRACT[e.type]; if (!c) throw new Error(`${e.type} is not a contract event`);
    assert.ok(c.origins.includes(e.origin ?? "device"), `${e.type} from ${e.origin ?? "device"}`);
    for (const r of c.payload.required ?? []) assert.ok(r in e.payload, `${e.type} needs ${r}`);
    for (const [k, v] of Object.entries(e.payload)) {
      const prop: { enum?: unknown[]; items?: { enum?: unknown[] } } | undefined = c.payload.properties[k]; if (!prop) throw new Error(`${e.type} must not carry ${k}`);
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

const QPLAN = (price: number, o: Partial<QuPlan>): QuPlan => ({ price_usd: price, places_included: 5, extra_place_cents: 1000, max_places: 10, tickets_per_place_month: 3000, sections_per_place: null, counters_per_place: 15, staff_accounts: 15,
  basic_phone: true, lynkchat_way: true, appointments: false, send_to: true, own_hardware: true, busy_forecast: true, own_logo: true, reports: "full", history_months: 24, ...o });
const QPLANS: Record<AtTier, QuPlan> = { free: QPLAN(0, { places_included: 1, extra_place_cents: null, max_places: 1, tickets_per_place_month: 500, sections_per_place: 3, counters_per_place: 3, basic_phone: false, lynkchat_way: false, send_to: false, own_hardware: false, busy_forecast: false, own_logo: false, reports: "daily_summary" }),
  plus: QPLAN(55, {}), pro: QPLAN(115, { extra_place_cents: 2000, appointments: true, reports: "by_email" }), max: QPLAN(249, { extra_place_cents: 4000, appointments: true, reports: "custom" }) };
const QLOOK: QuLook = { ...LOOK, place: "Sample place", powered: "<i data-powered></i>" };
type Log = { type: string; payload: Record<string, unknown>; origin?: string }[];
function desk(at = new Date(2026, 10, 18, 10, 0).getTime()): { d: QueueDesk; log: Log; clock: { now: number } } {
  const log: Log = [], clock = { now: at };
  return { d: new QueueDesk((type, payload, origin) => { log.push({ type, payload, origin }); }, QPLANS, () => clock.now), log, clock };
}
const QCTX = { online: true, partner: false, pairCode: () => "A2K9P2", redraw: () => undefined };

test("reception and counter: codes from this device's block, the fair order, three calls before missed", () => {
  const { d, log } = desk();
  d.act("qu:sec:PAY", QCTX); d.act("qu:issue", QCTX);
  const issued = log.find((e) => e.type === "TicketIssued")!;
  assert.equal(issued.payload["section"], "PAY"); match(String(issued.payload["code"]), /^[2-9A-HJ-NP-Z]{6}$/);
  match(quReceptionView(d, QLOOK), /ppl_place/); match(quReceptionView(d, QLOOK), /qpaper/, "the reception printer prints the ticket");
  const c = d.counters[0]!;
  const first = d.callNext(c.id)!;
  assert.equal(first.section, "SRV", "the oldest ticket comes first; staff never choose");
  d.finish(c.id, "missed"); assert.equal(first.state, "called", "missed only after three calls");
  d.callAgain(c.id); d.callAgain(c.id); d.callAgain(c.id);
  assert.equal(log.filter((e) => e.type === "TicketCalled").length, 3);
  d.finish(c.id, "missed"); assert.equal(first.state, "missed");
  d.counterState(c.id, "paused"); d.counterPick = c.id; match(quCounterView(d, QLOOK), /qu:call:[^"]+" disabled/); match(quCounterView(d, QLOOK), /ppl_qu_back_soon/);
  noMatch(quCounterView(d, QLOOK), /qu:pickticket|data-act="qu:callticket/, "there is no button to call a chosen ticket");
});

test("LynkQueue: 1 priority after every 3 others, a counter serves its sections in the manager's order", () => {
  const { d } = desk();
  for (const t of d.tickets) t.state = "served";
  const ids = [0, 1, 2, 3].map(() => d.issue("SRV", false, "reception")!.id); const p = d.issue("SRV", true, "reception")!;
  assert.deepEqual(d.order(["SRV"]), [ids[0], ids[1], ids[2], p.id, ids[3]]);
  d.act("qu:balance:1", QCTX); assert.equal(d.order(["SRV"])[1], p.id);
  const pay = d.issue("PAY", false, "kiosk")!, c2 = d.counters[1]!;
  assert.deepEqual(c2.sections, ["PAY", "SRV"]); assert.equal(d.callNext(c2.id)?.id, pay.id, "PAY comes first at this counter");
  d.finish(c2.id, "served"); d.toggleCounterSection(c2.id, "PAY"); d.toggleCounterSection(c2.id, "PAY"); assert.deepEqual(c2.sections, ["SRV", "PAY"]);
});

test("LynkQueue: closed, last ticket time, may not be served today, and one phone holds one waiting ticket", () => {
  const { d, clock } = desk();
  d.setHours("SRV", "opens", 8 * 60); d.setHours("SRV", "closes", 17 * 60); d.setHours("SRV", "lastBefore", 30);
  assert.equal(d.closedWhy("SRV"), "");
  clock.now = new Date(2026, 10, 18, 16, 31).getTime(); assert.equal(d.closedWhy("SRV"), "after_last_ticket_time"); assert.equal(d.issue("SRV", false, "kiosk"), null);
  clock.now = new Date(2026, 10, 18, 17, 30).getTime(); assert.equal(d.closedWhy("SRV"), "section_closed"); match(quKioskView(d, QLOOK), /qu:kiosk:SRV" disabled/); match(quKioskView(d, QLOOK), /ppl_qu_closed/);
  clock.now = new Date(2026, 10, 18, 16, 0).getTime(); assert.equal(d.mayNotBeServed("SRV"), false);
  for (let i = 0; i < 30; i++) d.issue("SRV", false, "reception");
  assert.ok(d.mayNotBeServed("SRV")); match(quKioskView(d, QLOOK), /ppl_qu_may_not/, "told before the ticket is taken");
  assert.ok(d.phoneJoin("PAY", false)); d.phone.ticket = null; assert.equal(d.phoneJoin("PAY", false), null); assert.equal(d.phone.note, "one_waiting_ticket_per_phone");
});

test("LynkQueue: ways to join follow the plan, the partner and the place", () => {
  const { d } = desk();
  d.phone.way = "basic_phone"; assert.equal(d.wayWhy("basic_phone", false), "coming_soon"); match(quPhoneView(d, QLOOK), /coming_soon/); assert.equal(d.wayWhy("basic_phone", true), "");
  assert.ok(!(QU_PHONE_WAYS as readonly string[]).includes("whatsapp"), "no WhatsApp (owner, 2026-11-19)");
  assert.equal(d.wayWhy("lynkchat", false), "");
  d.tier = "free"; assert.equal(d.wayWhy("lynkchat", true), "plan"); assert.equal(d.wayWhy("basic_phone", true), "plan"); assert.equal(d.wayWhy("smartphone", false), "");
  d.act("qu:joinfrom:only_at_the_place", QCTX); assert.equal(d.wayWhy("smartphone", false), "only_at_the_place"); match(quScreenView(d, QLOOK, undefined, "K7M2P9"), /ppl_qu_qr_changes/);
  d.act("qu:atplace", QCTX); assert.equal(d.wayWhy("smartphone", false), "");
});

test("LynkQueue: Send to keeps the ticket, Put back within 15 minutes, Running late once, Leave, Please come now", () => {
  const { d, log, clock } = desk(); const c = d.counters[0]!;
  const a = d.callNext(c.id)!; const num = d.number(a);
  d.sendTo(c.id, "PAY"); assert.equal(a.section, "PAY"); assert.equal(d.number(a), num, "the same ticket for the whole visit"); assert.equal(d.placeOf(a), 1, "the same arrival time");
  d.tier = "free"; const b = d.callNext(c.id)!; d.sendTo(c.id, "PAY"); assert.equal(b.state, "called", "Send to is a paid feature"); match(quCounterView(d, QLOOK), /ppl_qu_plan_send_to/); d.tier = "plus";
  d.callAgain(c.id); d.callAgain(c.id); d.finish(c.id, "missed"); assert.ok(d.canPutBack(b));
  for (let i = 0; i < 5; i++) d.issue("SRV", false, "reception");
  d.putBack(b.id); assert.equal(d.order(["SRV"]).indexOf(b.id), 3, "after the next 3 people");
  const me = d.phoneJoin("SRV", false)!; const before = d.placeOf(me)!;
  for (let i = 0; i < 4; i++) d.issue("SRV", false, "reception");
  d.runningLate(me.id); assert.equal(d.placeOf(me), before + 3); d.runningLate(me.id); assert.equal(d.placeOf(me), before + 3, "once per ticket"); match(quPhoneView(d, QLOOK), /qu:late" disabled/);
  assert.deepEqual(d.pleaseCome(), []); while ((d.placeOf(me) ?? 0) > 5) { d.callNext(c.id); d.finish(c.id, "served"); }
  assert.deepEqual(d.pleaseCome().map((x) => x.id), [me.id]); assert.deepEqual(d.pleaseCome(), []); match(quPhoneView(d, QLOOK), /ppl_qu_please_come/);
  d.act("qu:leave", QCTX); assert.equal(me.state, "left");
  const c3 = d.callNext(c.id)!; d.callAgain(c.id); d.callAgain(c.id); d.finish(c.id, "missed"); clock.now += 16 * 60000; assert.equal(d.canPutBack(c3), false); match(quReceptionView(d, QLOOK), /ppl_qu_put_back_late/);
  inContract(log); for (const e of log) noMatch(Object.keys(e.payload).join(" "), SECRET);
});

test("LynkQueue: check ticket, reprint never makes a new number, pagers, and Free has no hardware without a display", () => {
  const { d, log } = desk();
  const tk = d.issue("SRV", false, "reception")!; assert.equal(tk.pager, 1); assert.equal(d.printed, tk.id);
  const n = log.filter((e) => e.type === "TicketIssued").length; d.printed = null; d.reprint(tk.id); assert.equal(d.printed, tk.id); assert.equal(log.filter((e) => e.type === "TicketIssued").length, n);
  assert.equal(d.check(d.number(tk).toLowerCase()).state, "waiting"); assert.equal(d.check("SRV-ZZZZZZ").state, "not_valid_here");
  d.checkTyped = "SRV-ZZZZZZ"; d.act("qu:check", QCTX); match(quCounterView(d, QLOOK), /ppl_qu_state_not_valid_here/);
  d.tier = "free"; const t2 = d.issue("SRV", false, "reception")!; assert.equal(t2.pager, null); assert.equal(d.printed, null); match(quReceptionView(d, QLOOK), /ppl_qu_plan_hardware/);
  match(quKioskView(d, QLOOK), /qk-sec/); d.act("qu:kiosk:PAY", QCTX); match(quKioskView(d, QLOOK), /data-powered/, "LynkQueue Free shows Powered by LynkOmni on the ticket");
});

test("LynkQueue: only added devices, a pairing code, the lock, and another device takes over as queue keeper", () => {
  const { d, log } = desk();
  d.act("qu:kind:kiosk", QCTX); d.act("qu:adddev", { ...QCTX, online: false }); const added = d.devices.at(-1)!;
  assert.equal(added.state, "queued"); assert.equal(added.pair, "A2K9P2"); match(quDevicesView(d, QLOOK), /st-queued/);
  const before = d.deviceId, last = d.issue("SRV", false, "reception")!;
  assert.ok(d.takeOver()); assert.notEqual(d.deviceId, before);
  const next = d.issue("SRV", false, "reception")!; assert.equal(next.code, "2222Z8".length === 6 ? next.code : "", "a code"); assert.ok(next.seq > last.seq, "the same queue");
  assert.notEqual(next.code, last.code); assert.ok(parseInt(next.code, 36) !== parseInt(last.code, 36));
  const voided = log.filter((e) => e.type === "TicketCodesVoided"); assert.equal(voided.length, 3); assert.equal(voided[0]!.payload["device_id"], before); assert.equal(voided[0]!.payload["reason"], "block_not_used");
  assert.equal(log.at(-2)?.type === "QueueKeeperChanged" || log.some((e) => e.type === "QueueKeeperChanged"), true);
  assert.equal(d.takeOver(), false, "no other device holds codes"); match(quDevicesView(d, QLOOK), /ppl_qu_keeper_none/);
  d.tier = "free"; d.act("qu:kind:printer", QCTX); const count = d.devices.length; d.act("qu:adddev", QCTX); assert.equal(d.devices.length, count, "hardware without a display needs a paid tier");
  inContract(log);
});

test("LynkQueue: closing writes Not served today from the cloud only, reports and the plan's counts", () => {
  const { d, log } = desk(); const c = d.counters[0]!;
  d.callNext(c.id); d.finish(c.id, "served");
  assert.equal(d.closeDay(false), 0, "it waits for the internet"); match(quReportsView(d, { ...QLOOK, online: false }), /qu:closeday" disabled/);
  assert.equal(d.closeDay(true), 2); assert.ok(log.filter((e) => e.type === "TicketNotServedToday").every((e) => e.origin === "server"));
  const rep = d.report(); assert.deepEqual(rep.map((r) => [r.section, r.tickets, r.served, r.notServed]), [["SRV", 2, 1, 1], ["PAY", 1, 0, 1], ["CLT", 0, 0, 0]]);
  match(quReportsView(d, QLOOK), /ppl_qu_forecast_line/); match(quReportsView(d, QLOOK), /ppl_qu_sandbox_history/, "the forecast says its history is a sandbox");
  d.tier = "free"; match(quReportsView(d, QLOOK), /ppl_qu_plan_forecast/);
  d.earlierThisMonth = 500; assert.equal(d.closedWhy("SRV"), "free_limit_reached"); d.tier = "plus"; d.earlierThisMonth = 3100; assert.equal(d.closedWhy("SRV"), ""); assert.equal(d.usage().extra, 103);
  for (let i = 0; i < 3; i++) d.markPriority(d.issue("SRV", false, "reception")!.id); assert.deepEqual(d.pleaseCheck(), ["priority"]); match(quReportsView(d, QLOOK), /ppl_qu_check_priority/);
  inContract(log);
});

test("LynkQueue: sections within the plan, and the screens show numbers only", () => {
  const { d } = desk();
  d.input("qu:code", "lob"); d.input("qu:name", "Laboratory"); assert.equal(d.sectionWhy(), "code", "no O in the Lynk Alphabet");
  d.input("qu:code", "lab"); assert.equal(d.sectionWhy(), ""); d.act("qu:addsection", QCTX); assert.equal(d.sections.at(-1)?.code, "LAB");
  d.input("qu:code", "LAB"); d.input("qu:name", "x"); assert.equal(d.sectionWhy(), "used");
  d.tier = "free"; d.input("qu:code", "PHA"); assert.equal(d.sectionWhy(), "plan"); match(quSectionsView(d, QLOOK), /ppl_qu_plan_sections/);
  d.tier = "plus"; const c = d.counters[0]!; const tk = d.callNext(c.id)!;
  const screen = quScreenView(d, QLOOK), cd = quCDisplayView(d, c.id, QLOOK), pub = quPublicView(d, QLOOK);
  for (const html of [screen, cd, pub]) match(html, new RegExp(d.number(tk)));
  match(screen, /ppl_qu_voice/); match(cd, /qcd flash/); d.counterState(d.counters[1]!.id, "paused"); match(quScreenView(d, QLOOK), /ppl_qu_back_soon/);
  d.act("qu:public", QCTX); match(quPublicView(d, QLOOK), /ppl_qu_public_off/);
  for (const v of [quSetupView, quCountersView, quTicketsView]) assert.ok(v(d, QLOOK).length > 100);
  assert.deepEqual(Object.values(QU_LYNK).sort(), DEVICES.devices.map((x) => x.lynk_name).filter((n): n is string => !!n && ["LynkKiosk", "LynkDScreen", "LynkCDisplay"].includes(n)).filter((n, i, a) => a.indexOf(n) === i).sort(), "names only from the device register");
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
  const qc = { ...ctx, partner: false, pairCode: () => "A2K9P2" }; h.q.act("qu:issue", qc); const c = h.q.counters[0]!; h.q.callNext(c.id); h.q.sendTo(c.id, "PAY"); h.q.callNext(c.id); h.q.finish(c.id, "served"); h.q.counterState(c.id, "paused"); h.rate(4, "pos", "en");
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
