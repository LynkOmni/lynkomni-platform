/** LynkQueue in full on a device (LynkQ; master blueprint section 63; build section 3B): the queue keeper and every screen around it.
 *  The same engine runs in the Business app (LynkMobile, LynkTab, LynkPC), on LynkPOS, LynkKiosk, LynkDScreen and LynkCDisplay; it
 *  mirrors the reference service (people/queue.py, people/keeper.py) and takes every rule from ts/src/queue.ts.
 *
 *  What never happens here: a name or a phone number on a ticket, a screen or in an event; staff choosing who comes next (Call
 *  next follows the fair order); a ticket code given twice; a device that was not added giving out or calling tickets; a ticket
 *  given when the section is closed. Everything in the building works without internet; "Not served today" and new blocks of
 *  codes are written by the cloud alone, so those wait for it. Words are "ppl_" keys in web/shell. */
import { hintFor } from "./hints.js";
import { esc } from "./shell.js";
import type { T } from "./shell.js";
import { newId, randomBelow } from "./emulator.js";
import { CALLS_BEFORE_MISSED, PLEASE_COME_AT, PRIORITY_BALANCE, PUT_BACK_AFTER, PUT_BACK_MINUTES, RUNNING_LATE_PLACES, CAPACITY, code, index, nextCode, pickNext, putBack, reserveBlock, runningLate, ticketNumber, validSection, waitMinutes, ALPHABET, CODE_LENGTH } from "./queue.js";
import { spoken, ticketCard } from "./peopleparts.js";
import type { AtEmit, AtLook, AtTier } from "./attenddesk.js";

/** A one-time pairing code: a Lynk Code (queue.ts alphabet), never a number someone could guess from the last one. */
/** The code in the changing QR of a place that lets people join "only at the place": one per few minutes, from the time alone. */
export const pairCodeAt = (bucket: number): string => code((Math.imul(bucket, 2654435761) >>> 0) % CAPACITY);
export const pairCode = (): string => Array.from({ length: CODE_LENGTH }, () => ALPHABET[randomBelow(ALPHABET.length)]!).join("");   // each letter drawn fairly

type QuSt = "queued" | "sent" | "accepted" | "confirmed" | "failed";
/** The plan numbers the screens show (services/billing.py FEATURES lynkqueue, passed in by the build; never typed here). */
export interface QuPlan { price_usd: number; places_included: number; extra_place_cents: number | null; max_places: number | null; tickets_per_place_month: number; sections_per_place: number | null;
  counters_per_place: number | null; staff_accounts: number | null; basic_phone: boolean; lynkchat_way: boolean; appointments: boolean; send_to: boolean; own_hardware: boolean; busy_forecast: boolean;
  own_logo: boolean; reports: string; history_months: number | null }
export const QU_SETUPS = ["just_me", "one_place", "many_places"] as const;
export const QU_VIAS = ["reception", "kiosk", "smartphone", "lynkchat", "basic_phone", "api", "appointment"] as const;
export type QuVia = (typeof QU_VIAS)[number];
export const QU_PHONE_WAYS = ["smartphone", "lynkchat", "basic_phone"] as const;
export type QuPhoneWay = (typeof QU_PHONE_WAYS)[number];
const QU_PARTNER_WAYS: readonly string[] = ["basic_phone"];                    // needs the people_messages partner in that country
export const QU_DEVICE_KINDS = ["reception", "counter", "kiosk", "screen", "counter_display", "printer", "counter_keypad", "call_button", "pager_set", "scanner"] as const;
export type QuKind = (typeof QU_DEVICE_KINDS)[number];
const QU_NO_DISPLAY: readonly string[] = ["printer", "counter_keypad", "call_button", "pager_set", "scanner"];   // run through LynkDriver; paid tiers
const QU_KEEPERS: readonly string[] = ["reception", "counter"];
/** The ecosystem names of the display devices (catalog/devices.v1.json lynk_names; the same in every language). */
export const QU_LYNK: Partial<Record<QuKind, string>> = { kiosk: "LynkKiosk", screen: "LynkDScreen", counter_display: "LynkCDisplay" };
export const QU_LONG_WAIT = 30, QU_PLEASE_CHECK = 3, QU_FLASH_MS = 6000, QU_PAGERS = 12;
const QU_HEALTH = ["ok", "offline", "paper_low", "battery_low"] as const;
type QuHealth = (typeof QU_HEALTH)[number];

/** Words that already exist are used again, so each thing has one name everywhere. */
const QU_DID: Record<string, string> = { priority: "ppl_priority_short", counter_open: "ppl_counter_open", counter_paused: "ppl_counter_paused", counter_closed: "ppl_counter_closed", called_again: "ppl_call_again", served: "ppl_served",
  missed: "ppl_missed", put_back: "ppl_qu_put_back", running_late: "ppl_qu_running_late", not_served_today: "ppl_qu_state_not_served_today" };
const QU_VIA_KEY: Record<string, string> = { reception: "ppl_reception_title", kiosk: "ppl_qu_kiosk", lynkchat: "ppl_at_way_lynkchat" };
const QU_STATE_KEY: Record<string, string> = { served: "ppl_served", missed: "ppl_missed" };
const QU_KIND_KEY: Record<string, string> = { reception: "ppl_reception_title", counter: "ppl_counter_title" };
export interface QuSection { code: string; key: string | null; name: string; opens: number; closes: number; lastBefore: number; avg: number; last: string | null; block: { first: string; last: string } | null }
export interface QuTicket { id: string; section: string; first: string; code: string; seq: number; priority: boolean; state: "waiting" | "called" | "served" | "missed" | "left" | "not_served_today"; calls: number;
  counter: string | null; at: number; via: QuVia; phone: boolean; lateUsed: boolean; missedAt: number | null; told: boolean; pager: number | null; calledAt: number | null; doneAt: number | null }
export interface QuCounter { id: string; n: number; state: "open" | "paused" | "closed"; serving: string | null; sections: string[] }
interface QuDevice { id: string; kind: QuKind; health: QuHealth; locked: boolean; pair: string | null; state: QuSt; standby: { first: string; last: string } | null }
interface QuLine { at: number; what: string; ticket: string | null; by: "staff" | "person" | "system" }
const QU_SEED: [string, string][] = [["SRV", "ppl_sec_srv"], ["PAY", "ppl_sec_pay"], ["CLT", "ppl_sec_clt"]];
/** SANDBOX history: tickets by hour on this weekday in past weeks, so the busy-hour forecast has something to read (labelled wherever shown). */
const QU_PAST: Record<string, number[]> = { SRV: [0, 0, 0, 0, 0, 0, 0, 0, 6, 14, 17, 15, 8, 5, 7, 9, 6, 2, 0, 0, 0, 0, 0, 0], PAY: [0, 0, 0, 0, 0, 0, 0, 0, 2, 4, 5, 4, 9, 10, 4, 3, 2, 1, 0, 0, 0, 0, 0, 0] };

export class QueueDesk {
  readonly placeId = newId();
  readonly staffId = newId();
  deviceId = newId();
  tier: AtTier = "plus";
  setup: (typeof QU_SETUPS)[number] = "one_place";
  joinFrom: "anywhere" | "only_at_the_place" = "anywhere";
  balance = PRIORITY_BALANCE;
  publicPage = true;
  sections: QuSection[] = [];
  counters: QuCounter[] = [];
  tickets: QuTicket[] = [];
  devices: QuDevice[] = [];
  history: QuLine[] = [];
  seq = 0;
  servedSincePriority = 0;
  /** Tickets this place gave earlier this month (the plan's count); the day the limit is reached still works until closing. */
  earlierThisMonth = 0;
  // what the screens are in the middle of
  section = "SRV";
  priority = false;
  lastTicket: string | null = null;
  printed: string | null = null;
  refused = "";
  counterPick = "";
  checkTyped = "";
  checked: { number: string; state: string } | null = null;
  draft = { code: "", name: "" };
  addKind: QuKind = "counter";
  kioskDone: string | null = null;
  phone = { way: "smartphone" as QuPhoneWay, atPlace: false, ticket: null as string | null, note: "" };
  priorityUses = { you: 0, others: 1 };
  putBackUses = { you: 0, others: 1 };
  voice: string[] = ["en"];
  /** LynkPOS and LynkKiosk print on their own built-in printer, on every tier. */
  ownPrinter = false;
  constructor(private emit: AtEmit, readonly plans: Record<AtTier, QuPlan>, private now: () => number = Date.now) {
    for (const [sc, key] of QU_SEED) this.sections.push({ code: sc, key, name: "", opens: 0, closes: 24 * 60, lastBefore: 0, avg: 4, last: null, block: reserveBlock(null) });
    this.counters = [{ id: newId(), n: 1, state: "open", serving: null, sections: ["SRV", "CLT"] }, { id: newId(), n: 2, state: "open", serving: null, sections: ["PAY", "SRV"] }];
    this.counterPick = this.counters[0]!.id;
    const second = reserveBlock(this.sections[0]!.block!.last);
    this.devices = [{ id: this.deviceId, kind: "reception", health: "ok", locked: false, pair: null, state: "confirmed", standby: null }, { id: newId(), kind: "counter", health: "ok", locked: false, pair: null, state: "confirmed", standby: second },
      { id: newId(), kind: "kiosk", health: "ok", locked: false, pair: null, state: "confirmed", standby: null }, { id: newId(), kind: "screen", health: "ok", locked: false, pair: null, state: "confirmed", standby: null },
      { id: newId(), kind: "counter_display", health: "ok", locked: false, pair: null, state: "confirmed", standby: null }, { id: newId(), kind: "printer", health: "ok", locked: false, pair: null, state: "confirmed", standby: null },
      { id: newId(), kind: "pager_set", health: "ok", locked: false, pair: null, state: "confirmed", standby: null }];
    for (const [i, sec] of ["SRV", "SRV", "PAY"].entries()) this.issue(sec, i === 1, "reception", false, true);
  }
  get plan(): QuPlan { return this.plans[this.tier]; }
  nowMs(): number { return this.now(); }
  minute(): number { const d = new Date(this.now()); return d.getHours() * 60 + d.getMinutes(); }
  sec(sc: string): QuSection | undefined { return this.sections.find((s) => s.code === sc); }
  tk(id: string | null): QuTicket | undefined { return this.tickets.find((t) => t.id === id); }
  number(tk: QuTicket): string { return ticketNumber(tk.first, tk.code); }
  private log(what: string, tk: QuTicket | null, by: QuLine["by"] = "staff"): void { this.history.unshift({ at: this.now(), what, ticket: tk ? this.number(tk) : null, by }); }
  /** Hardware without a display (printers, pagers and the rest) runs through LynkDriver on the paid tiers. */
  has(kind: QuKind): boolean { if (kind === "printer" && this.ownPrinter) return true; return (this.plan.own_hardware || !QU_NO_DISPLAY.includes(kind)) && this.devices.some((d) => d.kind === kind && !d.locked && d.state === "confirmed"); }

  // ---- getting a ticket -----------------------------------------------------------------------------------------------------
  /** Why no ticket can be given now, or "" when one can: closed, after the last ticket time, or LynkQueue Free's month is used up. */
  closedWhy(section: string): string {
    const s = this.sec(section), m = this.minute();
    if (!s || m < s.opens || m >= s.closes) return "section_closed";
    if (s.lastBefore > 0 && m >= s.closes - s.lastBefore) return "after_last_ticket_time";
    if (this.plan.extra_place_cents === null && this.earlierThisMonth >= this.plan.tickets_per_place_month) return "free_limit_reached";
    return "";
  }
  /** Told before the ticket is taken when the wait is longer than the time left before closing. */
  mayNotBeServed(section: string): boolean {
    const s = this.sec(section); if (!s) return false;
    const w = waitMinutes(this.waiting(section).length + 1, s.avg, Math.max(1, this.openCounters(section)));
    return w !== null && this.minute() + w > s.closes;
  }
  issue(section: string, priority: boolean, via: QuVia, phone = false, quiet = false): QuTicket | null {
    const s = this.sec(section); this.refused = "";
    if (!s || !s.block) { this.refused = "section_closed"; return null; }
    if (!quiet) { this.refused = this.closedWhy(section); if (this.refused) return null; }
    if (phone && this.tickets.some((t) => t.phone && t.section === section && t.state === "waiting")) { this.refused = "one_waiting_ticket_per_phone"; return null; }
    const c = nextCode(s.last);
    if (c === null || index(c) > index(s.block.last)) { this.refused = "no_codes_left_on_this_device"; return null; }     // the cloud gives the next block when online
    s.last = c; this.seq += 1;
    const tk: QuTicket = { id: newId(), section, first: section, code: c, seq: this.seq, priority, state: "waiting", calls: 0, counter: null, at: this.now(), via, phone, lateUsed: false, missedAt: null, told: false, pager: null, calledAt: null, doneAt: null };
    this.tickets.push(tk); this.lastTicket = tk.id;
    if (quiet) return tk;
    this.emit("TicketIssued", { ticket_id: tk.id, place_id: this.placeId, section, code: c, via, priority, device_id: this.deviceId });
    if (priority) { this.emit("TicketPriorityMarked", { ticket_id: tk.id, by: this.staffId }); this.priorityUses.you += 1; }
    if (via === "reception" || via === "kiosk") { this.printed = this.has("printer") || via === "kiosk" ? tk.id : null; if (via === "reception" && this.has("pager_set")) tk.pager = this.freePager(); }
    this.log("given", tk, via === "reception" ? "staff" : "person");
    return tk;
  }
  private freePager(): number | null { const used = new Set(this.tickets.filter((t) => t.pager !== null && (t.state === "waiting" || t.state === "called")).map((t) => t.pager)); for (let n = 1; n <= QU_PAGERS; n++) if (!used.has(n)) return n; return null; }
  codesLeft(section: string): number { const s = this.sec(section); return s?.block ? index(s.block.last) - (s.last === null ? index(s.block.first) - 1 : index(s.last)) : 0; }
  /** Reprint prints the same ticket again and never makes a new number. */
  reprint(id: string): void { const tk = this.tk(id); if (tk && this.has("printer")) { this.printed = tk.id; this.log("reprinted", tk); } }
  markPriority(id: string): void { const tk = this.tk(id); if (!tk || tk.state !== "waiting" || tk.priority) return; tk.priority = true; this.priorityUses.you += 1; this.emit("TicketPriorityMarked", { ticket_id: tk.id, by: this.staffId }); this.log("priority", tk); }

  // ---- the fair order -------------------------------------------------------------------------------------------------------
  waiting(section?: string): QuTicket[] { return this.tickets.filter((t) => t.state === "waiting" && (!section || t.section === section)); }
  /** The order Call next follows: for one section, for a counter's sections (in the order the manager set), or for the place. */
  order(sections?: readonly string[]): string[] {
    const ids: string[] = []; let since = this.servedSincePriority;
    for (const sc of sections ?? this.sections.map((s) => s.code)) {
      const left = this.waiting(sc).map((t) => ({ id: t.id, seq: t.seq, priority: t.priority }));
      while (left.length) { const id = pickNext(left, since, this.minute(), this.balance); if (!id) break; ids.push(id); const i = left.findIndex((x) => x.id === id); since = left[i]!.priority ? 0 : since + 1; left.splice(i, 1); }
    }
    return ids;
  }
  openCounters(section?: string): number { return this.counters.filter((c) => c.state === "open" && (!section || c.sections.includes(section))).length; }
  placeOf(tk: QuTicket): number | null { const i = this.order([tk.section]).indexOf(tk.id); return i < 0 ? null : i + 1; }
  waitOf(tk: QuTicket): number | null { const p = this.placeOf(tk), s = this.sec(tk.section); return p === null || !s ? null : waitMinutes(p, s.avg, Math.max(1, this.openCounters(tk.section))); }
  private reseq(tk: QuTicket, order: readonly string[]): void {
    const i = order.indexOf(tk.id), before = i > 0 ? this.tk(order[i - 1]!)!.seq : 0, after = i + 1 < order.length ? this.tk(order[i + 1]!)!.seq : before + 2;
    tk.seq = (before + after) / 2; if (i > 0) tk.priority = false;
  }

  // ---- the counter ----------------------------------------------------------------------------------------------------------
  counter(id: string): QuCounter | undefined { return this.counters.find((c) => c.id === id); }
  counterState(id: string, state: QuCounter["state"]): void {
    const c = this.counter(id); if (!c || c.state === state || (state !== "open" && c.serving)) return;
    c.state = state; this.emit("CounterStateChanged", { counter_id: c.id, place_id: this.placeId, state, by: this.staffId }); this.log(`counter_${state}`, null);
  }
  callNext(id: string): QuTicket | null {
    const c = this.counter(id); if (!c || c.state !== "open" || c.serving) return null;
    const tk = this.tk(this.order(c.sections)[0] ?? null); if (!tk) return null;
    tk.state = "called"; tk.calls = 1; tk.counter = c.id; tk.calledAt = this.now(); c.serving = tk.id;
    this.servedSincePriority = tk.priority ? 0 : this.servedSincePriority + 1;
    this.emit("TicketCalled", { ticket_id: tk.id, counter_id: c.id, call: 1, by_number: true }); this.log("called", tk);
    return tk;
  }
  private serving(id: string): [QuCounter, QuTicket] | null { const c = this.counter(id), tk = this.tk(c?.serving ?? null); return c && tk ? [c, tk] : null; }
  callAgain(id: string): void {
    const s = this.serving(id); if (!s || s[1].calls >= CALLS_BEFORE_MISSED) return;
    s[1].calls += 1; s[1].calledAt = this.now(); this.emit("TicketCalled", { ticket_id: s[1].id, counter_id: s[0].id, call: s[1].calls, by_number: true }); this.log("called_again", s[1]);
  }
  finish(id: string, how: "served" | "missed"): void {
    const s = this.serving(id); if (!s || (how === "missed" && s[1].calls < CALLS_BEFORE_MISSED)) return;
    const [c, tk] = s; tk.state = how; c.serving = null; tk.doneAt = this.now(); tk.pager = how === "served" ? null : tk.pager;
    if (how === "missed") tk.missedAt = this.minute();
    else { const sec = this.sec(tk.section), took = tk.calledAt ? (tk.doneAt - tk.calledAt) / 60000 : 0; if (sec && took > 0) sec.avg = Math.max(1, Math.round((sec.avg * 9 + took) / 10)); }   // the wait time learns by itself
    this.emit(how === "served" ? "TicketServed" : "TicketMissed", how === "served" ? { ticket_id: tk.id, counter_id: c.id } : { ticket_id: tk.id }); this.log(how, tk);
  }
  /** Send to: the same ticket and the same arrival time go on to another section (one ticket for the whole visit; paid tiers). */
  sendTo(id: string, to: string): void {
    const s = this.serving(id); if (!s || !this.plan.send_to || to === s[1].section || !this.sec(to)) return;
    const [c, tk] = s; tk.section = to; tk.state = "waiting"; tk.calls = 0; tk.counter = null; c.serving = null;
    this.emit("TicketSentTo", { ticket_id: tk.id, to_section: to }); this.log("sent_to", tk);
  }
  /** Within 15 minutes a missed ticket goes back in after the next 3 people (reception). */
  canPutBack(tk: QuTicket): boolean { return tk.state === "missed" && tk.missedAt !== null && this.minute() - tk.missedAt <= PUT_BACK_MINUTES && this.minute() >= tk.missedAt; }
  putBack(id: string): void {
    const tk = this.tk(id); if (!tk || !this.canPutBack(tk)) return;
    const o = putBack([...this.order([tk.section]), tk.id], tk.id, tk.missedAt ?? 0, this.minute()); if (!o) return;
    this.reseq(tk, o); tk.state = "waiting"; tk.calls = 0; tk.counter = null; this.putBackUses.you += 1;
    this.emit("TicketPutBack", { ticket_id: tk.id, by: this.staffId }); this.log("put_back", tk);
  }
  /** Check ticket: real, for this place and for today, or "Not valid here". */
  check(number: string): { number: string; state: string } {
    const [sec = "", cd = ""] = number.trim().toUpperCase().split("-");
    const tk = this.tickets.find((t) => t.first === sec && t.code === cd);
    return { number: number.trim().toUpperCase(), state: tk ? tk.state : "not_valid_here" };
  }

  // ---- the person on a phone ------------------------------------------------------------------------------------------------
  /** May this way be used: the plan, the country's partner and the place's choice. Returns "" or the reason. */
  wayWhy(way: QuPhoneWay, partner: boolean): string {
    if (way === "lynkchat" && !this.plan.lynkchat_way) return "plan";
    if (way === "basic_phone" && !this.plan.basic_phone) return "plan";
    if (QU_PARTNER_WAYS.includes(way) && !partner) return "coming_soon";
    if (this.joinFrom === "only_at_the_place" && !this.phone.atPlace) return "only_at_the_place";
    return "";
  }
  phoneJoin(section: string, partner: boolean): QuTicket | null {
    this.phone.note = this.wayWhy(this.phone.way, partner);
    if (this.phone.note) return null;
    const tk = this.issue(section, false, this.phone.way, true);
    this.phone.note = this.refused; if (tk) this.phone.ticket = tk.id;
    return tk;
  }
  runningLate(id: string): void {
    const tk = this.tk(id); if (!tk || tk.state !== "waiting" || tk.lateUsed) return;
    this.reseq(tk, runningLate(this.order([tk.section]), tk.id)); tk.lateUsed = true; this.emit("TicketRunningLate", { ticket_id: tk.id }); this.log("running_late", tk, "person");
  }
  leave(id: string): void { const tk = this.tk(id); if (!tk || tk.state !== "waiting") return; tk.state = "left"; tk.doneAt = this.now(); this.emit("TicketLeft", { ticket_id: tk.id }); this.log("left", tk, "person"); }
  /** "Please come now" when 5 people or fewer are ahead (people who joined by phone; told once each). */
  pleaseCome(): QuTicket[] { const out = this.tickets.filter((t) => t.state === "waiting" && t.phone && !t.told && (this.placeOf(t) ?? 99) <= PLEASE_COME_AT); for (const t of out) t.told = true; return out; }

  // ---- setup: sections, counters, devices -----------------------------------------------------------------------------------
  sectionWhy(): string {
    const c = this.draft.code.trim().toUpperCase();
    if (this.plan.sections_per_place !== null && this.sections.length >= this.plan.sections_per_place) return "plan";
    if (!validSection(c)) return "code"; if (this.sec(c)) return "used"; if (!this.draft.name.trim()) return "name";
    return "";
  }
  addSection(): void {
    if (this.sectionWhy()) return;
    const sc = this.draft.code.trim().toUpperCase();
    this.sections.push({ code: sc, key: null, name: this.draft.name.trim(), opens: 8 * 60, closes: 17 * 60, lastBefore: 30, avg: 4, last: null, block: reserveBlock(null) });
    this.draft = { code: "", name: "" }; this.log("section_added", null);
  }
  removeSection(sc: string): void { if (this.sections.length < 2 || this.tickets.some((t) => t.section === sc && (t.state === "waiting" || t.state === "called"))) return; this.sections = this.sections.filter((s) => s.code !== sc);
    for (const c of this.counters) { c.sections = c.sections.filter((x) => x !== sc); if (!c.sections.length) c.sections = [this.sections[0]!.code]; } if (this.section === sc) this.section = this.sections[0]!.code; this.log("section_removed", null); }
  setHours(sc: string, field: "opens" | "closes" | "lastBefore", minutes: number): void { const s = this.sec(sc); if (!s || !Number.isInteger(minutes) || minutes < 0 || minutes > 24 * 60) return; s[field] = minutes; if (s.closes <= s.opens) s.closes = Math.min(24 * 60, s.opens + 60); }
  canAddCounter(): boolean { return this.plan.counters_per_place === null || this.counters.length < this.plan.counters_per_place; }
  addCounter(): void { if (!this.canAddCounter()) return; this.counters.push({ id: newId(), n: this.counters.length + 1, state: "closed", serving: null, sections: [this.sections[0]!.code] }); this.log("counter_added", null); }
  /** A counter may serve several sections; pressing a section again moves it to the end, so the order is the manager's. */
  toggleCounterSection(id: string, sc: string): void {
    const c = this.counter(id); if (!c || !this.sec(sc) || c.serving) return;
    c.sections = c.sections.includes(sc) ? (c.sections.length > 1 ? c.sections.filter((x) => x !== sc) : c.sections) : [...c.sections, sc];
  }
  /** Add a device: it shows a pairing code and the manager types it; only an added device works. */
  addDevice(kind: QuKind, online: boolean, pairCode: () => string, redraw: () => void): void {
    if (QU_NO_DISPLAY.includes(kind) && !this.plan.own_hardware) return;
    const d: QuDevice = { id: newId(), kind, health: "ok", locked: false, pair: pairCode(), state: online ? "sent" : "queued", standby: null };
    this.devices.push(d); this.log("device_added", null);
    if (online) setTimeout(() => { d.state = "confirmed"; d.pair = null; redraw(); }, 1500);
  }
  onlineAgain(redraw: () => void): void { for (const d of this.devices) if (d.state === "queued") { d.state = "sent"; setTimeout(() => { d.state = "confirmed"; d.pair = null; redraw(); }, 1500); } }
  /** Lost or stolen: it can no longer give out or call tickets, and its unused codes are closed for good (the cloud writes that). */
  lock(id: string): void {
    const d = this.devices.find((x) => x.id === id); if (!d || d.locked || d.id === this.deviceId) return;
    d.locked = true; this.log("device_locked", null);
    if (d.standby) { for (const s of this.sections) this.emit("TicketCodesVoided", { place_id: this.placeId, device_id: d.id, section: s.code, first: d.standby.first, last: d.standby.last, reason: "device_locked" }, "server"); d.standby = null; }
  }
  setHealth(id: string, h: string): void { const d = this.devices.find((x) => x.id === id); if (d && (QU_HEALTH as readonly string[]).includes(h)) d.health = h as QuHealth; }
  keeper(): QuDevice | undefined { return this.devices.find((d) => d.id === this.deviceId); }
  standby(): QuDevice | undefined { return this.devices.find((d) => d.id !== this.deviceId && QU_KEEPERS.includes(d.kind) && !d.locked && d.state === "confirmed" && d.standby); }
  /** The queue keeper switched off: another added device takes over with the same queue and its own block of codes. */
  takeOver(): boolean {
    const next = this.standby(), old = this.keeper(); if (!next || !old || !next.standby) return false;
    for (const s of this.sections) {
      const first = nextCode(s.last);
      if (s.block && first && index(first) <= index(s.block.last)) this.emit("TicketCodesVoided", { place_id: this.placeId, device_id: old.id, section: s.code, first, last: s.block.last, reason: "block_not_used" });
      s.block = { ...next.standby }; s.last = index(s.block.first) > 0 ? code(index(s.block.first) - 1) : null;
    }
    old.health = "offline"; next.standby = null; this.deviceId = next.id;
    this.emit("QueueKeeperChanged", { place_id: this.placeId, device_id: next.id }); this.log("keeper_changed", null, "system");
    return true;
  }
  /** Closing: tickets still waiting are closed and marked "Not served today" (the cloud writes it, so it waits for the internet). */
  closeDay(online: boolean): number {
    if (!online) return 0;
    const left = this.tickets.filter((t) => t.state === "waiting" || t.state === "missed");
    for (const tk of left) { tk.state = "not_served_today"; tk.doneAt = this.now(); this.emit("TicketNotServedToday", { ticket_id: tk.id }, "server"); this.log("not_served_today", tk, "system"); }
    for (const c of this.counters) if (!c.serving) this.counterState(c.id, "closed");
    return left.length;
  }

  // ---- the manager: live view, reports, forecast, "Please check" ------------------------------------------------------------
  longestWait(section: string): number { const w = this.waiting(section); return w.length ? Math.floor((this.now() - Math.min(...w.map((t) => t.at))) / 60000) : 0; }
  report(): { section: string; tickets: number; served: number; missed: number; left: number; notServed: number; wait: number | null }[] {
    return this.sections.map((s) => { const all = this.tickets.filter((t) => t.first === s.code), called = all.filter((t) => t.calledAt !== null);
      return { section: s.code, tickets: all.length, served: all.filter((t) => t.state === "served").length, missed: all.filter((t) => t.state === "missed").length, left: all.filter((t) => t.state === "left").length,
        notServed: all.filter((t) => t.state === "not_served_today").length, wait: called.length ? Math.round(called.reduce((a, t) => a + ((t.calledAt ?? t.at) - t.at) / 60000, 0) / called.length) : null }; });
  }
  busiestHour(): number | null { const by = new Map<number, number>(); for (const t of this.tickets) { const h = new Date(t.at).getHours(); by.set(h, (by.get(h) ?? 0) + 1); } let best: number | null = null; for (const [h, n] of by) if (best === null || n > (by.get(best) ?? 0)) best = h; return best; }
  /** Busy hours tomorrow, from this place's own past days (here: the labelled sandbox history): hours with at least half of the busiest hour. */
  forecast(): { section: string; from: number; to: number }[] {
    if (!this.plan.busy_forecast) return [];
    const out: { section: string; from: number; to: number }[] = [];
    for (const s of this.sections) { const past = QU_PAST[s.code]; if (!past) continue; const top = Math.max(...past); const busy = past.map((n, h) => (n * 2 > top ? h : -1)).filter((h) => h >= 0); if (busy.length) out.push({ section: s.code, from: busy[0]!, to: busy[busy.length - 1]! + 1 }); }
    return out;
  }
  /** Priority or Put back used far more than the others do: only a flag, never an accusation. */
  pleaseCheck(): string[] { const out: string[] = []; for (const [k, u] of [["priority", this.priorityUses], ["put_back", this.putBackUses]] as const) if (u.you >= QU_PLEASE_CHECK && u.you >= QU_PLEASE_CHECK * u.others) out.push(k); return out; }
  /** What is billed: only a place that gave at least one ticket this month; on paid tiers extra tickets just cost more. */
  usage(): { tickets: number; included: number; extra: number } { const n = this.earlierThisMonth + this.tickets.length, inc = this.plan.tickets_per_place_month; return { tickets: n, included: inc, extra: this.plan.extra_place_cents === null ? 0 : Math.max(0, n - inc) }; }

  // ---- act: every control of these screens is a button whose data-act starts with "qu:" -----------------------------------
  act(a: string, ctx: { online: boolean; partner: boolean; pairCode: () => string; redraw: () => void }): boolean {
    if (!a.startsWith("qu:")) return false;
    const [, k = "", v = "", w = ""] = a.split(":");
    switch (k) {
      case "setup": if ((QU_SETUPS as readonly string[]).includes(v)) this.setup = v as (typeof QU_SETUPS)[number]; break;
      case "joinfrom": this.joinFrom = v === "only_at_the_place" ? v : "anywhere"; break;
      case "balance": { const n = Number(v); if (Number.isInteger(n) && n >= 1 && n <= 10) this.balance = n; break; }
      case "public": this.publicPage = !this.publicPage; break;
      case "sec": if (this.sec(v)) this.section = v; break;
      case "prio": this.priority = !this.priority; break;
      case "issue": this.issue(this.section, this.priority, "reception"); this.priority = false; break;
      case "give": this.issue(v, w === "p", "reception"); break;
      case "reprint": this.reprint(v); break;
      case "markprio": this.markPriority(v); break;
      case "putback": this.putBack(v); break;
      case "pick": if (this.counter(v)) this.counterPick = v; break;
      case "cstate": this.counterState(v, w === "paused" || w === "closed" ? w : "open"); break;
      case "call": this.callNext(v); break;
      case "again": this.callAgain(v); break;
      case "served": this.finish(v, "served"); break;
      case "missed": this.finish(v, "missed"); break;
      case "sendto": this.sendTo(v, w); break;
      case "check": this.checked = this.checkTyped.trim() ? this.check(this.checkTyped) : null; break;
      case "csec": this.toggleCounterSection(v, w); break;
      case "addcounter": this.addCounter(); break;
      case "addsection": this.addSection(); break;
      case "rmsection": this.removeSection(v); break;
      case "kind": if ((QU_DEVICE_KINDS as readonly string[]).includes(v)) this.addKind = v as QuKind; break;
      case "adddev": this.addDevice(this.addKind, ctx.online, ctx.pairCode, ctx.redraw); break;
      case "lock": this.lock(v); break;
      case "health": this.setHealth(v, w); break;
      case "takeover": this.takeOver(); break;
      case "closeday": this.closeDay(ctx.online); break;
      case "kiosk": { const tk = this.issue(v, false, "kiosk"); this.kioskDone = tk ? tk.id : null; break; }
      case "kioskdone": this.kioskDone = null; this.refused = ""; break;
      case "way": if ((QU_PHONE_WAYS as readonly string[]).includes(v)) { this.phone.way = v as QuPhoneWay; this.phone.note = ""; } break;
      case "atplace": this.phone.atPlace = !this.phone.atPlace; break;
      case "join": this.phoneJoin(v, ctx.partner); break;
      case "late": this.runningLate(this.phone.ticket ?? ""); break;
      case "leave": this.leave(this.phone.ticket ?? ""); this.phone.ticket = null; break;
      case "pnew": this.phone.ticket = null; this.phone.note = ""; break;
      default: return false;
    }
    return true;
  }
  /** Typed fields and selects ("qu:..."), so the screen can be redrawn without losing them. */
  input(k: string, v: string): boolean {
    const [p, f = "", c = ""] = k.split(":"); if (p !== "qu") return false;
    if (f === "code") this.draft.code = v.toUpperCase().slice(0, 3); else if (f === "name") this.draft.name = v.slice(0, 40); else if (f === "check") this.checkTyped = v.slice(0, 12);
    else if (f === "opens" || f === "closes" || f === "lastBefore") this.setHours(c, f, Number(v)); else if (f === "voice2") this.voice = v ? [this.voice[0] ?? "en", v] : [this.voice[0] ?? "en"];
    else return false;
    return true;
  }
}

// ---- drawing ----------------------------------------------------------------------------------------------------------------
/** What a queue screen needs beyond the shared look: the place's name, and the "Powered by LynkOmni" mark where the plan asks for it. */
export interface QuLook extends AtLook { place: string; powered: string; /** false on a device that prints on real paper beside the screen (LynkPOS, LynkKiosk): the ticket is not drawn on the screen too. */ paper?: boolean }
const quOn = (on: boolean): string => `aria-pressed="${on}"`;
const quOff = (off: boolean): string => (off ? "disabled" : "");
const quTag = (text: string, kind = ""): string => `<span class="tag ${kind}">${esc(text)}</span>`;
const quCard = (item: string, title: string, body: string): string => `<div class="card ph-card" data-item="${item}" role="group" aria-label="${esc(title)}"><h2>${esc(title)}</h2>${body}</div>`;
const quChip = (s: QuSt, L: AtLook): string => `<span class="chip st-${s}">${L.icon(`status-${s}`)}<span>${esc(L.t(`st_${s}`))}</span></span>`;
const quRow = (name: string, sub: string, end = ""): string => `<li><div class="rowbtn static"><span class="main"><span class="nm">${name}</span><span class="sub">${sub}</span></span>${end}</div></li>`;
const quHm = (m: number): string => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
export const quSecName = (s: QuSection | undefined, t: T): string => (s ? (s.key ? t(s.key) : s.name) : "");
const quNum = (d: QueueDesk, tk: QuTicket): string => `<span dir="ltr">${esc(d.number(tk))}</span>`;
const quKindName = (k: QuKind, t: T): string => QU_LYNK[k] ?? t(QU_KIND_KEY[k] ?? `ppl_qu_kind_${k}`);
const quVia = (v: string, t: T): string => t(QU_VIA_KEY[v] ?? `ppl_qu_via_${v}`);
const quState = (s: string, t: T): string => t(QU_STATE_KEY[s] ?? `ppl_qu_state_${s}`);
const quCounterName = (d: QueueDesk, id: string | null, t: T): string => { const c = d.counter(id ?? ""); return c ? t("ppl_counter_n", { n: c.n }) : ""; };
export function quView(d: QueueDesk, tk: QuTicket, t: T): { section: string; sectionName: string; code: string; place: number | null; waitMinutes: number | null; counter: string | null } {
  return { section: tk.first, sectionName: quSecName(d.sec(tk.section), t), code: tk.code, place: tk.state === "waiting" ? d.placeOf(tk) : null, waitMinutes: tk.state === "waiting" ? d.waitOf(tk) : null, counter: tk.state === "called" ? quCounterName(d, tk.counter, t) : null };
}
const quWhy = (why: string, d: QueueDesk, section: string, t: T): string => {
  const s = d.sec(section), name = quSecName(s, t);
  return why === "section_closed" ? t("ppl_qu_closed", { section: name, time: quHm(s?.opens ?? 0) }) : why === "after_last_ticket_time" ? t("ppl_qu_after_last", { section: name })
    : why === "free_limit_reached" ? t("ppl_qu_free_limit") : why === "one_waiting_ticket_per_phone" ? t("ppl_qu_one_per_phone") : why === "no_codes_left_on_this_device" ? t("ppl_qu_no_codes") : "";
};

/** The paper ticket: the place, the section, the number in large letters, its QR, the date and time, the place in the queue and the link to follow it. */
export function quPaper(d: QueueDesk, tk: QuTicket, L: QuLook): string {
  const p = d.placeOf(tk), w = d.waitOf(tk);
  return `<div class="qpaper" role="img" aria-label="${esc(L.t("ppl_qu_paper"))}: ${esc(spoken(tk.first, tk.code))}"><p class="qp-place">${esc(L.place)}</p><p class="qp-sec">${esc(quSecName(d.sec(tk.section), L.t))}</p>
    <p class="qp-num" dir="ltr">${esc(d.number(tk))}</p><span class="qp-qr" aria-hidden="true">${L.icon("ui-qr", "qrbig")}</span><p class="qp-time">${esc(L.clock(tk.at))}</p>
    ${p !== null ? `<p>${esc(L.t("ppl_place", { n: String(p) }))} ${w !== null ? esc(L.t("ppl_wait", { m: String(w) })) : ""}</p>` : ""}${tk.priority ? `<p>${esc(L.t("ppl_priority_short"))}</p>` : ""}
    <p class="qp-link">${esc(L.t("ppl_qu_follow"))}</p>${d.plan.own_logo ? "" : L.powered}</div>`;
}

/** Setup: the kind of place, where people may join from, the priority balance and the public queue page. */
export function quSetupView(d: QueueDesk, L: QuLook): string {
  const t = L.t, off = quOff(!L.mayManage), u = d.usage(), p = d.plan;
  const kinds = `<div class="ph-choices">${QU_SETUPS.map((s) => `<button type="button" class="ph-choice" data-act="qu:setup:${s}" ${quOn(d.setup === s)} ${off}><strong>${esc(t(`ppl_setup_${s}`))}</strong><span>${esc(t(`ppl_setup_${s}_help`))}</span></button>`).join("")}</div><p class="sub">${esc(t("ppl_setup_note"))}</p>`;
  const join = `<div class="ph-choices small">${(["anywhere", "only_at_the_place"] as const).map((j) => `<button type="button" class="ph-choice" data-act="qu:joinfrom:${j}" ${quOn(d.joinFrom === j)} ${off}><strong>${esc(t(`ppl_qu_join_${j}`))}</strong></button>`).join("")}</div>
    <p class="sub">${esc(t(d.joinFrom === "anywhere" ? "ppl_qu_join_anywhere_help" : "ppl_qu_join_only_help"))}</p>`;
  const bal = `<p>${esc(t("ppl_qu_balance", { n: d.balance }))}</p><div class="ph-row">${[1, 2, 3, 4, 5].map((n) => `<button type="button" class="ghost small" data-act="qu:balance:${n}" ${quOn(d.balance === n)} ${off}>${n}</button>`).join("")}</div><p class="sub">${esc(t("ppl_qu_balance_help"))}</p>`;
  const pub = `<button type="button" class="ph-toggle" data-act="qu:public" ${quOn(d.publicPage)} ${off}><span>${esc(t("ppl_qu_public"))}</span><strong>${esc(t(d.publicPage ? "ppl_on" : "ppl_off"))}</strong></button><p class="sub">${esc(t("ppl_qu_public_help"))}</p>`;
  const plan = `<p>${esc(t("ppl_qu_plan_line", { used: u.tickets, included: u.included }))}</p><p class="sub">${esc(t(p.extra_place_cents === null ? "ppl_qu_plan_free" : "ppl_qu_plan_paid", { price: L.money(200) }))}</p>
    <p class="sub">${esc(t("ppl_qu_plan_places", { n: p.places_included }))}${p.extra_place_cents === null ? "" : ` ${esc(t("ppl_qu_plan_extra_place", { price: L.money(p.extra_place_cents) }))}`}</p>`;
  return quCard("q_kind", t("ppl_setup_title"), kinds) + quCard("q_join_from", t("ppl_qu_join_from"), join) + quCard("q_balance", t("ppl_priority_short"), bal) + quCard("q_public_page", t("ppl_qu_public"), pub) + quCard("q_plan", t("ppl_qu_plan"), plan)
    + (L.mayManage ? "" : `<p class="sub">${esc(t("ppl_owner_manager_only"))}</p>`);
}
/** Sections: the 3-character code, the hours, the last ticket time, and adding one. */
export function quSectionsView(d: QueueDesk, L: QuLook): string {
  const t = L.t, off = quOff(!L.mayManage), why = d.sectionWhy();
  const hours = (s: QuSection, f: "opens" | "closes", label: string): string => `<label class="field small"><span>${esc(label)}</span><select data-in="qu:${f}:${s.code}" ${off}>${Array.from({ length: 25 }, (_, h) => h).filter((h) => (f === "opens" ? h < 24 : h > 0)).map((h) => `<option value="${h * 60}" ${s[f] === h * 60 ? "selected" : ""}>${quHm(h * 60)}</option>`).join("")}</select></label>`;
  const last = (s: QuSection): string => `<label class="field small"><span>${esc(t("ppl_qu_last_ticket"))}</span><select data-in="qu:lastBefore:${s.code}" ${off}>${[0, 15, 30, 60].map((m) => `<option value="${m}" ${s.lastBefore === m ? "selected" : ""}>${esc(m ? t("ppl_qu_min_before", { m }) : t("ppl_qu_at_closing"))}</option>`).join("")}</select></label>`;
  const rows = d.sections.map((s) => { const cw = d.closedWhy(s.code);
    return `<li class="ph-detail"><p class="nm"><span dir="ltr">${esc(s.code)}</span> · ${esc(quSecName(s, t))} ${cw === "section_closed" ? quTag(t("ppl_counter_closed"), "warn") : cw === "after_last_ticket_time" ? quTag(t("ppl_qu_no_new_tickets"), "warn") : ""}</p>
      <p class="sub">${esc(t("ppl_waiting_n", { n: d.waiting(s.code).length }))} · ${esc(t("ppl_qu_about_each", { m: s.avg }))} · ${esc(t("ppl_codes_left", { n: d.codesLeft(s.code) }))}</p>
      <div class="ph-row">${hours(s, "opens", t("ppl_qu_opens"))}${hours(s, "closes", t("ppl_qu_closes"))}${last(s)}</div>
      <button type="button" class="ghost small" data-act="qu:rmsection:${s.code}" ${quOff(!L.mayManage || d.sections.length < 2 || d.waiting(s.code).length > 0)}>${esc(t("ppl_qu_remove"))}</button></li>`; }).join("");
  const add = `<label class="field"><span>${esc(t("ppl_qu_code"))}</span><input id="quCode" data-in="qu:code" value="${esc(d.draft.code)}" maxlength="3" autocomplete="off" autocapitalize="characters" spellcheck="false" dir="ltr" ${off} placeholder="${esc(hintFor("code_short", t))}" aria-label="${esc(t("ppl_qu_code"))}"></label>
    <label class="field"><span>${esc(t("ppl_qu_name"))}</span><input id="quName" data-in="qu:name" value="${esc(d.draft.name)}" maxlength="40" autocomplete="off" ${off} placeholder="${esc(t("hint_section"))}" aria-label="${esc(t("ppl_qu_name"))}"></label>
    <button type="button" class="primary inline" data-act="qu:addsection" ${quOff(!L.mayManage || why !== "")}>${esc(t("ppl_qu_add_section"))}</button>
    <p class="sub" role="status">${esc(why === "plan" ? t("ppl_qu_plan_sections", { n: d.plan.sections_per_place ?? 0 }) : why === "used" ? t("ppl_qu_code_used") : t("ppl_qu_code_help"))}</p>`;
  return quCard("section_list", t("ppl_sections"), `<ul class="list">${rows}</ul>`) + quCard("add_section", t("ppl_qu_add_section"), add);
}
/** Counters: which sections each serves and in what order; adding one within the plan. */
export function quCountersView(d: QueueDesk, L: QuLook): string {
  const t = L.t, off = quOff(!L.mayManage);
  const rows = d.counters.map((c) => `<li class="ph-detail"><p class="nm">${esc(t("ppl_counter_n", { n: c.n }))} ${quTag(t(`ppl_counter_${c.state}`), c.state === "open" ? "" : "warn")}</p>
    <p class="sub">${esc(t("ppl_qu_serves", { sections: c.sections.join(", ") }))}${c.serving ? ` · ${esc(t("ppl_qu_serving"))} ${quNum(d, d.tk(c.serving)!)}` : ""}</p>
    <div class="ph-row">${d.sections.map((s) => `<button type="button" class="ghost small" data-act="qu:csec:${c.id}:${s.code}" ${quOn(c.sections.includes(s.code))} ${quOff(!L.mayManage || c.serving !== null)}><span dir="ltr">${esc(s.code)}</span></button>`).join("")}</div></li>`).join("");
  return quCard("counter_list", t("ppl_counters"), `<ul class="list">${rows}</ul><p class="sub">${esc(t("ppl_qu_counter_order"))}</p>
    <button type="button" class="primary inline" data-act="qu:addcounter" ${quOff(!L.mayManage || !d.canAddCounter())}>${esc(t("ppl_qu_add_counter"))}</button>${d.canAddCounter() ? "" : `<p class="sub">${esc(t("ppl_qu_plan_counters", { n: d.plan.counters_per_place ?? 0 }))}</p>`}`) + (off ? `<p class="sub">${esc(t("ppl_owner_manager_only"))}</p>` : "");
}
/** Tickets: the live view by section (waiting, longest wait, open counters, a suggestion), the fair order, and the history. */
export function quTicketsView(d: QueueDesk, L: QuLook): string {
  const t = L.t;
  const live = d.sections.map((s) => { const long = d.longestWait(s.code);
    return quRow(`<span dir="ltr">${esc(s.code)}</span> · ${esc(quSecName(s, t))}`, `${esc(t("ppl_waiting_n", { n: d.waiting(s.code).length }))} · ${esc(t("ppl_qu_longest", { m: long }))} · ${esc(t("ppl_qu_counters_open", { n: d.openCounters(s.code) }))}`)
      + (long > QU_LONG_WAIT ? `<li><p class="notice" role="status">${quTag("LynkAssist")} ${esc(t("ppl_qu_suggest_open", { section: s.code, m: QU_LONG_WAIT }))}</p></li>` : ""); }).join("");
  const order = d.order();
  const list = order.map((id) => { const tk = d.tk(id)!; return quRow(quNum(d, tk), `${esc(quSecName(d.sec(tk.section), t))}${tk.priority ? ` · ${esc(t("ppl_priority_short"))}` : ""} · ${esc(t("ppl_place", { n: String(d.placeOf(tk) ?? "") }))} · ${esc(quVia(tk.via, t))}${tk.pager ? ` · ${esc(t("ppl_qu_pager_n", { n: tk.pager }))}` : ""}`); }).join("");
  const hist = d.history.slice(0, 30).map((h) => quRow(`${esc(t(QU_DID[h.what] ?? `ppl_qu_did_${h.what}`))}${h.ticket ? ` · <span dir="ltr">${esc(h.ticket)}</span>` : ""}`, `${esc(L.clock(h.at))} · ${esc(t(`ppl_qu_by_${h.by}`))}`)).join("");
  return quCard("live_view", t("ppl_qu_live"), `<ul class="list">${live}</ul>`) + quCard("fair_order", t("ppl_waiting_now"), `<ol class="list">${list}</ol>${order.length ? "" : `<p class="sub">${esc(t("ppl_no_one_waiting"))}</p>`}<p class="sub">${esc(t("ppl_qu_fair"))}</p>`)
    + quCard("ticket_history", t("ppl_qu_history"), `<ul class="list">${hist}</ul><p class="sub">${esc(t("ppl_qu_history_note"))}</p>`);
}
/** Devices: every added device with its health, the queue keeper, Add device with the pairing code, and the lock for a lost one. */
export function quDevicesView(d: QueueDesk, L: QuLook): string {
  const t = L.t, off = !L.mayManage, sb = d.standby();
  const rows = d.devices.map((x) => { const isK = x.id === d.deviceId, paid = QU_NO_DISPLAY.includes(x.kind) && !d.plan.own_hardware;
    return `<li class="ph-detail"><p class="nm">${esc(quKindName(x.kind, t))} ${isK ? quTag(t("ppl_qu_keeper")) : ""} ${x.locked ? quTag(t("ppl_qu_locked"), "warn") : x.state !== "confirmed" ? quChip(x.state, L) : x.health === "ok" ? "" : quTag(t(`ppl_qu_health_${x.health}`), "warn")}</p>
      ${x.pair ? `<p class="ph-code" role="status">${esc(t("ppl_pair_code"))} <strong dir="ltr">${esc(x.pair)}</strong></p>` : ""}${paid ? `<p class="sub">${esc(t("ppl_qu_plan_hardware"))}</p>` : ""}
      <div class="ph-row">${x.locked || isK ? "" : `<button type="button" class="ghost small" data-act="qu:lock:${x.id}" ${quOff(off)}>${esc(t("ppl_qu_lock"))}</button>`}
      ${x.locked || x.state !== "confirmed" ? "" : QU_HEALTH.filter((h) => h === "ok" || h === "offline" || (h === "paper_low" && x.kind === "printer") || (h === "battery_low" && x.kind === "pager_set")).map((h) => `<button type="button" class="ghost small" data-act="qu:health:${x.id}:${h}" ${quOn(x.health === h)}>${esc(t(`ppl_qu_health_${h}`))}</button>`).join("")}</div></li>`; }).join("");
  const add = `<div class="ph-choices small">${QU_DEVICE_KINDS.map((k) => `<button type="button" class="ph-choice" data-act="qu:kind:${k}" ${quOn(d.addKind === k)} ${quOff(off || (QU_NO_DISPLAY.includes(k) && !d.plan.own_hardware))}><strong>${esc(quKindName(k, t))}</strong></button>`).join("")}</div>
    <button type="button" class="primary inline" data-act="qu:adddev" ${quOff(off)}>${esc(t("ppl_get_code"))}</button><p class="sub">${esc(t("ppl_pair_note"))} ${esc(t("ppl_qu_no_display_note"))}</p>${d.plan.own_hardware ? "" : `<p class="sub">${esc(t("ppl_qu_plan_hardware"))}</p>`}`;
  const keeper = `<p>${esc(t("ppl_qu_keeper_help"))}</p><button type="button" class="ghost inline" data-act="qu:takeover" ${quOff(!sb)}>${esc(t("ppl_qu_keeper_off"))}</button><p class="sub">${esc(t(sb ? "ppl_qu_keeper_standby" : "ppl_qu_keeper_none"))}</p>`;
  return quCard("device_list", t("ppl_qu_devices"), `<ul class="list">${rows}</ul><p class="sub">${esc(t("ppl_qu_health_note"))} ${quTag(t("ppl_qu_sandbox"))}</p>`) + quCard("queue_keeper", t("ppl_qu_keeper"), keeper) + quCard("q_add_device", t("ppl_add_device"), add)
    + (off ? `<p class="sub">${esc(t("ppl_owner_manager_only"))}</p>` : "");
}
/** Reports: today by section, the busiest hour, "Not served today", the forecast, "Please check", and closing the day. */
export function quReportsView(d: QueueDesk, L: QuLook): string {
  const t = L.t, rep = d.report(), busy = d.busiestHour(), fc = d.forecast(), pc = d.pleaseCheck(), u = d.usage();
  const table = `<ul class="list">${rep.map((r) => quRow(`<span dir="ltr">${esc(r.section)}</span> · ${esc(quSecName(d.sec(r.section), t))}`, `${esc(t("ppl_qu_r_tickets", { n: r.tickets }))} · ${esc(t("ppl_qu_r_served", { n: r.served }))} · ${esc(t("ppl_qu_r_missed", { n: r.missed }))} · ${esc(t("ppl_qu_r_left", { n: r.left }))} · ${esc(t("ppl_qu_r_not_served", { n: r.notServed }))}${r.wait === null ? "" : ` · ${esc(t("ppl_qu_r_wait", { m: r.wait }))}`}`)).join("")}</ul>
    ${busy === null ? "" : `<p>${esc(t("ppl_qu_busiest", { from: quHm(busy * 60), to: quHm((busy + 1) * 60) }))}</p>`}<p class="sub">${esc(t(`ppl_qu_reports_${d.plan.reports}`))}</p>`;
  const forecast = d.plan.busy_forecast ? `<ul class="list">${fc.map((f) => `<li><p>${esc(t("ppl_qu_forecast_line", { from: quHm(f.from * 60), to: quHm(f.to * 60), section: f.section }))}</p></li>`).join("")}</ul><p class="sub">${quTag(t("ppl_estimate"))} ${quTag(t("ppl_qu_sandbox_history"))} ${esc(t("ppl_qu_forecast_note"))}</p>` : `<p class="sub">${esc(t("ppl_qu_plan_forecast"))}</p>`;
  const check = pc.length ? pc.map((k) => `<p class="notice" role="status">${quTag(t("ppl_flag_warning_sign"), "warn")} ${esc(t(`ppl_qu_check_${k}`))}</p>`).join("") + `<p class="sub">${esc(t("ppl_qu_check_note"))}</p>` : `<p class="sub">${esc(t("ppl_qu_check_none"))}</p>`;
  const close = `<p>${esc(t("ppl_qu_close_help"))}</p><button type="button" class="primary inline" data-act="qu:closeday" ${quOff(!L.mayManage || !L.online)}>${esc(t("ppl_qu_close_day"))}</button>${L.online ? "" : `<p class="sub" role="status">${esc(t("ppl_qu_close_online"))}</p>`}`;
  const bill = `<p>${esc(t("ppl_qu_plan_line", { used: u.tickets, included: u.included }))}</p>${u.extra ? `<p>${esc(t("ppl_qu_extra_tickets", { n: u.extra }))}</p>` : ""}<p class="sub">${esc(t("ppl_qu_bill_note"))}</p>`;
  return quCard("today_report", t("ppl_today"), table) + quCard("busy_forecast", t("ppl_qu_forecast"), forecast) + quCard("please_check", t("ppl_flag_warning_sign"), check) + quCard("close_day", t("ppl_qu_close_day"), close) + quCard("q_billing_count", t("ppl_qu_plan"), bill);
}
/** Reception: New ticket, Priority, Reprint, Put back, pagers; the printed ticket comes out of the reception printer. */
export function quReceptionView(d: QueueDesk, L: QuLook): string {
  const t = L.t, tk = d.tk(d.lastTicket), why = d.closedWhy(d.section), missed = d.tickets.filter((x) => x.state === "missed");
  const pick = `<div class="ph-choices small">${d.sections.map((s) => `<button type="button" class="ph-choice" data-act="qu:sec:${s.code}" ${quOn(d.section === s.code)}><strong>${esc(quSecName(s, t))}</strong><span><span dir="ltr">${esc(s.code)}</span> · ${esc(t("ppl_waiting_n", { n: d.waiting(s.code).length }))}</span></button>`).join("")}</div>`;
  const warn = why ? `<p class="warn" role="alert">${esc(quWhy(why, d, d.section, t))}</p>` : d.mayNotBeServed(d.section) ? `<p class="notice" role="status">${esc(t("ppl_qu_may_not"))}</p>` : d.refused ? `<p class="warn" role="alert">${esc(quWhy(d.refused, d, d.section, t))}</p>` : "";
  const given = tk && tk.state === "waiting" ? `${ticketCard(quView(d, tk, t), t, L.icon)}${d.printed === tk.id ? `${L.paper === false ? "" : quPaper(d, tk, L)}<p class="sub" role="status">${esc(t("ppl_qu_printed"))}</p>` : `<p class="sub">${esc(t(d.plan.own_hardware ? "ppl_qu_no_printer" : "ppl_qu_plan_hardware"))}</p>`}
    ${tk.pager ? `<p role="status">${esc(t("ppl_qu_pager_out", { n: tk.pager }))}</p>` : ""}<div class="ph-row"><button type="button" class="ghost small" data-act="qu:reprint:${tk.id}" ${quOff(!d.has("printer"))}>${esc(t("ppl_qu_reprint"))}</button>
    <button type="button" class="ghost small" data-act="qu:markprio:${tk.id}" ${quOff(tk.priority)}>${esc(t("ppl_priority_short"))}</button></div>` : "";
  const back = missed.length ? `<ul class="list">${missed.map((m) => quRow(quNum(d, m), esc(t(d.canPutBack(m) ? "ppl_qu_put_back_help" : "ppl_qu_put_back_late", { n: PUT_BACK_AFTER, m: PUT_BACK_MINUTES })), `<button type="button" class="ghost small" data-act="qu:putback:${m.id}" ${quOff(!d.canPutBack(m))}>${esc(t("ppl_qu_put_back"))}</button>`)).join("")}</ul>` : `<p class="sub">${esc(t("ppl_qu_no_missed"))}</p>`;
  return quCard("new_ticket", t("ppl_reception_title"), `${pick}<button type="button" class="ph-toggle" data-act="qu:prio" ${quOn(d.priority)}>${d.priority ? L.icon("ui-check") : ""}<span>${esc(t("ppl_priority"))}</span></button>
    <button type="button" class="primary inline" data-act="qu:issue" ${quOff(why !== "")}>${esc(t("ppl_issue"))}</button>${warn}${given}<p class="sub">${esc(t("ppl_works_offline"))}</p>`) + quCard("put_back", t("ppl_qu_put_back"), back);
}
/** The counter: Open, Call next, Call again, Done, Send to, Missed, Pause, Close, and Check ticket. Staff never choose who comes. */
export function quCounterView(d: QueueDesk, L: QuLook): string {
  const t = L.t, c = d.counter(d.counterPick) ?? d.counters[0]; if (!c) return "";
  const tk = d.tk(c.serving), waiting = d.order(c.sections).length;
  const pick = d.counters.length > 1 ? `<div class="ph-choices small">${d.counters.map((x) => `<button type="button" class="ph-choice" data-act="qu:pick:${x.id}" ${quOn(x.id === c.id)}><strong>${esc(t("ppl_counter_n", { n: x.n }))}</strong></button>`).join("")}</div>` : "";
  const states = `<div class="ph-choices small">${(["open", "paused", "closed"] as const).map((s) => `<button type="button" class="ph-choice" data-act="qu:cstate:${c.id}:${s}" ${quOn(c.state === s)} ${quOff(tk !== undefined && s !== "open")}><strong>${esc(t(`ppl_counter_${s}`))}</strong></button>`).join("")}</div>`;
  const send = d.plan.send_to ? `<div class="ph-row">${d.sections.filter((s) => s.code !== tk?.section).map((s) => `<button type="button" class="ghost small" data-act="qu:sendto:${c.id}:${s.code}">${esc(t("ppl_send_to", { section: quSecName(s, t) }))}</button>`).join("")}</div>` : `<p class="sub">${esc(t("ppl_qu_plan_send_to"))}</p>`;
  const serving = tk ? `${ticketCard(quView(d, tk, t), t, L.icon)}<p class="sub">${esc(t("ppl_calls_n", { n: tk.calls, of: CALLS_BEFORE_MISSED }))}${tk.pager ? ` · ${esc(t("ppl_qu_pager_buzzed", { n: tk.pager }))}` : ""}</p><div class="ph-row">
      <button type="button" class="primary" data-act="qu:served:${c.id}">${esc(t("ppl_served"))}</button><button type="button" class="ghost" data-act="qu:again:${c.id}" ${quOff(tk.calls >= CALLS_BEFORE_MISSED)}>${esc(t("ppl_call_again"))}</button>
      <button type="button" class="ghost" data-act="qu:missed:${c.id}" ${quOff(tk.calls < CALLS_BEFORE_MISSED)}>${esc(t("ppl_missed"))}</button></div>${send}`
    : `<button type="button" class="primary inline" data-act="qu:call:${c.id}" ${quOff(c.state !== "open" || !waiting)}>${esc(t("ppl_call_next"))}</button><p class="sub">${esc(waiting ? t("ppl_waiting_n", { n: waiting }) : t("ppl_no_one_waiting"))} · ${esc(t("ppl_qu_serves", { sections: c.sections.join(", ") }))}</p>${c.state === "paused" ? `<p class="notice" role="status">${esc(t("ppl_qu_back_soon", { counter: t("ppl_counter_n", { n: c.n }) }))}</p>` : ""}`;
  const res = d.checked ? `<p class="${d.checked.state === "waiting" || d.checked.state === "called" ? "ok" : "warn"}" role="status"><span dir="ltr">${esc(d.checked.number)}</span>: ${esc(quState(d.checked.state, t))}</p>` : "";
  const check = `<label class="field"><span>${esc(t("ppl_qu_check_label"))}</span><input id="quCheck" data-in="qu:check" value="${esc(d.checkTyped)}" maxlength="12" autocomplete="off" autocapitalize="characters" spellcheck="false" dir="ltr"></label>
    <button type="button" class="ghost inline" data-act="qu:check">${esc(t("ppl_qu_check_ticket"))}</button>${res}<p class="sub">${esc(t(d.has("scanner") ? "ppl_qu_check_scan" : "ppl_qu_check_type"))}</p>`;
  return quCard("counter_buttons", t("ppl_counter_n", { n: c.n }), pick + states + serving + `<p class="sub">${esc(t("ppl_qu_fair"))}</p>`) + quCard("check_ticket", t("ppl_qu_check_ticket"), check);
}
/** LynkKiosk: press the section and take your ticket; the wait is shown before, "closed" and "may not be served today" are said. */
export function quKioskView(d: QueueDesk, L: QuLook): string {
  const t = L.t, done = d.tk(d.kioskDone);
  if (done) return `<div class="qkiosk done" role="status">${ticketCard(quView(d, done, t), t, L.icon)}${L.paper === false ? "" : quPaper(d, done, L)}<p>${esc(t("ppl_qu_take_ticket"))}</p><button type="button" class="primary inline" data-act="qu:kioskdone">${esc(t("ppl_next_person"))}</button></div>`;
  return `<div class="qkiosk"><p class="plabel">${esc(t("ppl_qu_kiosk_pick"))}</p>${d.sections.map((s) => { const why = d.closedWhy(s.code), n = d.waiting(s.code).length, w = waitMinutes(n + 1, s.avg, Math.max(1, d.openCounters(s.code)));
    return `<button type="button" class="qk-sec" data-act="qu:kiosk:${s.code}" ${quOff(why !== "")}><strong>${esc(quSecName(s, t))}</strong><span>${why ? esc(quWhy(why, d, s.code, t)) : `${esc(t("ppl_waiting_n", { n }))} · ${esc(t("ppl_wait", { m: String(w ?? 0) }))}`}</span>
      ${!why && d.mayNotBeServed(s.code) ? `<span class="warn">${esc(t("ppl_qu_may_not"))}</span>` : ""}</button>`; }).join("")}${d.refused ? `<p class="warn" role="alert">${esc(quWhy(d.refused, d, d.section, t))}</p>` : ""}<p class="sub">${esc(t("ppl_qu_kiosk_note"))}</p></div>`;
}
/** What the voice says for a call, in a language of the place: the number character by character, then the counter. */
export const quVoice = (d: QueueDesk, tk: QuTicket, t: T): string => t("ppl_qu_voice", { number: spoken(tk.first, tk.code), counter: quCounterName(d, tk.counter, t) });
/** LynkDScreen, the main calling screen: the tickets being called and their counters, "back soon", how many wait, and the QR to join. */
export function quScreenView(d: QueueDesk, L: QuLook, speak?: (lang: string) => T, qrCode = ""): string {
  const t = L.t, called = d.tickets.filter((x) => x.state === "called").sort((a, b) => (b.calledAt ?? 0) - (a.calledAt ?? 0)), top = called[0], now = d.nowMs();
  const flash = (x: QuTicket): string => ((x.calledAt ?? 0) > now - QU_FLASH_MS ? " flash" : "");
  const rows = called.map((x) => `<li class="qs-row${flash(x)}"><span class="qs-num" dir="ltr">${esc(d.number(x))}</span><span class="qs-arrow" aria-hidden="true">${L.icon("ui-chevron-right")}</span><span class="qs-counter">${esc(quCounterName(d, x.counter, t))}</span></li>`).join("");
  const paused = d.counters.filter((c) => c.state === "paused").map((c) => `<p class="qs-soon">${esc(t("ppl_qu_back_soon", { counter: t("ppl_counter_n", { n: c.n }) }))}</p>`).join("");
  const waits = d.sections.map((s) => `<li><span dir="ltr">${esc(s.code)}</span> <span>${esc(quSecName(s, t))}</span> <strong>${esc(t("ppl_waiting_n", { n: d.waiting(s.code).length }))}</strong></li>`).join("");
  const voice = top ? d.voice.map((l) => `<span lang="${esc(l)}">${esc(quVoice(d, top, speak ? speak(l) : t))}</span>`).join(" ") : "";
  return `<div class="qscreen"><h2 class="qs-title">${esc(t("ppl_qu_now_serving"))}</h2><ul class="qs-list" aria-live="polite">${rows || `<li class="qs-none">${esc(t("ppl_qu_none_called"))}</li>`}</ul>${paused}
    <ul class="qs-waits">${waits}</ul><div class="qs-join"><span class="qr" aria-hidden="true">${L.icon("ui-qr", "qrbig")}</span><div><p class="plabel">${esc(t("ppl_qu_scan_join"))}</p>${d.joinFrom === "only_at_the_place" ? `<p class="sub">${esc(t("ppl_qu_qr_changes"))} <span dir="ltr">${esc(qrCode)}</span></p>` : ""}</div></div>
    <p class="qs-voice" role="status">${top ? `${L.icon("ui-bell")} ${voice}` : ""}</p>${d.plan.own_logo ? "" : L.powered}</div>`;
}
/** LynkCDisplay, the small screen above one counter: the ticket being served there (it flashes when called), "back soon" or "closed". */
export function quCDisplayView(d: QueueDesk, counterId: string, L: QuLook): string {
  const t = L.t, c = d.counter(counterId) ?? d.counters[0]; if (!c) return "";
  const tk = d.tk(c.serving), fresh = tk && (tk.calledAt ?? 0) > d.nowMs() - QU_FLASH_MS;
  return `<div class="qcd${fresh ? " flash" : ""}" role="status"><p class="qcd-name">${esc(t("ppl_counter_n", { n: c.n }))}</p>${tk ? `<p class="qcd-num" dir="ltr" aria-label="${esc(spoken(tk.first, tk.code))}">${esc(d.number(tk))}</p>`
    : `<p class="qcd-state">${esc(c.state === "paused" ? t("ppl_qu_back_soon_short") : c.state === "closed" ? t("ppl_counter_closed") : t("ppl_qu_next_please"))}</p>`}</div>`;
}
/** The person's phone, with no app and no account: see the wait, join, then the ticket with Running late and Leave queue. */
export function quPhoneView(d: QueueDesk, L: QuLook): string {
  const t = L.t, tk = d.tk(d.phone.ticket), ph = d.phone;
  if (tk) {
    const p = d.placeOf(tk), come = tk.state === "waiting" && p !== null && p <= PLEASE_COME_AT;
    const msg = tk.state === "missed" ? t("ppl_qu_msg_missed", { m: PUT_BACK_MINUTES }) : tk.state === "served" ? t("ppl_qu_msg_served") : tk.state === "not_served_today" ? t("ppl_qu_state_not_served_today") : tk.section !== tk.first && tk.state === "waiting" ? t("ppl_qu_msg_next", { section: quSecName(d.sec(tk.section), t), n: p ?? 0 }) : come ? t("ppl_qu_please_come") : "";
    return `<div class="qphone">${ticketCard(quView(d, tk, t), t, L.icon)}${msg ? `<p class="notice" role="status">${esc(msg)}</p>` : ""}
      ${tk.state === "waiting" ? `<div class="ph-row"><button type="button" class="ghost" data-act="qu:late" ${quOff(tk.lateUsed)}>${esc(t("ppl_qu_running_late"))}</button><button type="button" class="ghost" data-act="qu:leave">${esc(t("ppl_qu_leave"))}</button></div>
      <p class="sub">${esc(t(tk.lateUsed ? "ppl_qu_late_used" : "ppl_qu_late_help", { n: RUNNING_LATE_PLACES }))}</p>` : `<button type="button" class="ghost inline" data-act="qu:pnew">${esc(t("ppl_qu_new_ticket"))}</button>`}<p class="sub">${esc(t("ppl_qu_phone_privacy"))}</p></div>`;
  }
  const why = d.wayWhy(ph.way, L.partner);
  const ways = `<div class="ph-choices small">${QU_PHONE_WAYS.map((w) => `<button type="button" class="ph-choice" data-act="qu:way:${w}" ${quOn(ph.way === w)}><strong>${esc(quVia(w, t))}</strong></button>`).join("")}</div>`;
  const note = why === "plan" ? t("ppl_qu_plan_way") : why === "coming_soon" ? t("coming_soon") : why === "only_at_the_place" ? t("ppl_qu_only_here") : ph.note ? quWhy(ph.note, d, d.section, t) : "";
  const secs = d.sections.map((s) => { const cw = d.closedWhy(s.code), n = d.waiting(s.code).length, w = waitMinutes(n + 1, s.avg, Math.max(1, d.openCounters(s.code)));
    return `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(quSecName(s, t))}</span><span class="sub">${cw ? esc(quWhy(cw, d, s.code, t)) : `${esc(t("ppl_waiting_n", { n }))} · ${esc(t("ppl_wait", { m: String(w ?? 0) }))}${d.mayNotBeServed(s.code) ? ` · ${esc(t("ppl_qu_may_not"))}` : ""}`}</span></span>
      <button type="button" class="primary small" data-act="qu:join:${s.code}" ${quOff(cw !== "" || why !== "")}>${esc(t("ppl_qu_join"))}</button></div></li>`; }).join("");
  return `<div class="qphone"><h2>${esc(L.place)}</h2>${ways}<p class="sub">${esc(t(`ppl_qu_way_${ph.way}`))}</p>${d.joinFrom === "only_at_the_place" ? `<button type="button" class="ph-toggle" data-act="qu:atplace" ${quOn(ph.atPlace)}><span>${esc(t("ppl_qu_at_place"))}</span><strong>${esc(t(ph.atPlace ? "ppl_on" : "ppl_off"))}</strong></button>` : ""}
    ${note ? `<p class="${why === "coming_soon" ? "notice" : "warn"}" role="status">${esc(note)}</p>` : ""}<ul class="list">${secs}</ul><p class="sub">${esc(t("ppl_qu_no_account"))}</p></div>`;
}
/** The public queue page on the place's Storefront: numbers only. "Now serving LAB-A2K9P2. 12 waiting. About 25 minutes." */
export function quPublicView(d: QueueDesk, L: QuLook): string {
  const t = L.t;
  if (!d.publicPage) return `<p class="sub">${esc(t("ppl_qu_public_off"))}</p>`;
  const rows = d.sections.map((s) => { const called = d.tickets.filter((x) => x.state === "called" && x.section === s.code), n = d.waiting(s.code).length, w = waitMinutes(n + 1, s.avg, Math.max(1, d.openCounters(s.code)));
    return quRow(esc(quSecName(s, t)), `${called.length ? `${esc(t("ppl_qu_now_serving"))} ${called.map((x) => quNum(d, x)).join(", ")} · ` : ""}${esc(t("ppl_waiting_n", { n }))} · ${esc(t("ppl_wait", { m: String(w ?? 0) }))}`); }).join("");
  const fc = d.forecast()[0];
  return `<div class="qpublic"><h2>${esc(L.place)}</h2><ul class="list">${rows}</ul>${fc ? `<p class="sub">${esc(t("ppl_qu_usual_busy", { from: quHm(fc.from * 60), to: quHm(fc.to * 60) }))} ${quTag(t("ppl_qu_sandbox_history"))}</p>` : ""}
    <p class="sub">${esc(t(d.joinFrom === "anywhere" ? "ppl_qu_public_join" : "ppl_qu_only_here"))}</p></div>`;
}
/** The staff's part beside a device that only follows (LynkDScreen, LynkCDisplay, the person's phone): reception gives tickets and
 *  each counter calls, calls again, finishes, pauses and opens, exactly as on the real reception and counter screens. */
export function quDriver(d: QueueDesk, L: QuLook): string {
  const t = L.t;
  const give = `<div class="tbtns">${d.sections.map((s) => `<button type="button" data-act="qu:give:${s.code}" ${quOff(d.closedWhy(s.code) !== "")}>+ <span dir="ltr">${esc(s.code)}</span></button>`).join("")}
    <button type="button" data-act="qu:give:${d.sections[0]?.code ?? ""}:p">+ ${esc(t("ppl_priority_short"))}</button></div>`;
  const counters = d.counters.map((c) => { const tk = d.tk(c.serving);
    return `<p class="tname">${esc(t("ppl_counter_n", { n: c.n }))}: ${tk ? `<span dir="ltr">${esc(d.number(tk))}</span>` : esc(t(`ppl_counter_${c.state}`))}</p><div class="tbtns">
      <button type="button" data-act="qu:call:${c.id}" ${quOff(c.state !== "open" || !!tk || !d.order(c.sections).length)}>${esc(t("ppl_call_next"))}</button>
      <button type="button" data-act="qu:again:${c.id}" ${quOff(!tk || tk.calls >= CALLS_BEFORE_MISSED)}>${esc(t("ppl_call_again"))}</button>
      <button type="button" data-act="qu:served:${c.id}" ${quOff(!tk)}>${esc(t("ppl_served"))}</button>
      <button type="button" data-act="qu:missed:${c.id}" ${quOff(!tk || tk.calls < CALLS_BEFORE_MISSED)}>${esc(t("ppl_missed"))}</button>
      <button type="button" data-act="qu:cstate:${c.id}:${c.state === "open" ? "paused" : "open"}" ${quOff(!!tk)}>${esc(t(c.state === "open" ? "ppl_counter_paused" : "ppl_counter_open"))}</button></div>`; }).join("");
  return `<h3>${esc(t("ppl_qu_driver"))}</h3><p class="sub">${esc(t("ppl_waiting_n", { n: d.waiting().length }))}</p>${give}${counters}`;
}
