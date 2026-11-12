/** LynkAttend, LynkQueue and LynkSurvey on the Business app devices (NEW UPDATE 4, master blueprint 63.7; build section 3):
 *  setup (Just me, One place, Many places), Add a device with a one-time Lynk Code, today's attendance, the door, reception and
 *  counter, and the rating after payment. One shared engine for every device, drawn from the rules (attendance.ts, queue.ts,
 *  survey.ts) and the shared parts (peopleparts.ts); the words are "ppl_" keys in web/shell.
 *
 *  Everything here works offline: a check-in, a ticket and an answer are written to the device's log at once and sent when the
 *  link is back (the five user states). A PIN, an IDCN, a face, a finger or a phone number never leaves this module in an event.
 *  Device names come only from the device register (catalog/devices.v1.json, lynk_name). Every choice is a real button, so the
 *  screens work by touch and by keys alone. */
import { esc } from "./shell.js";
import type { Icon, T } from "./shell.js";
import { newId, randomBytes } from "./emulator.js";
import { door, idcn, isEasyPin, IDCN_LENGTH, IDCN_TRIES, PIN_LENGTH, PIN_TRIES_BEFORE_PAUSE, checkerFlags } from "./attendance.js";
import type { AttendSet, DoorOut } from "./attendance.js";
import { CALLS_BEFORE_MISSED, CAPACITY, code, nextCode, pickNext, reserveBlock, index, waitMinutes, ticketNumber } from "./queue.js";
import { canShow, margin, MIN_GROUP } from "./survey.js";
import { idcnEntry, quickRating, rateUs, ticketCard } from "./peopleparts.js";
import type { DeviceRegister } from "./interfaces.js";

export const PEOPLE_SERVICES = ["attendance", "queue", "survey"] as const;
export type PeopleService = (typeof PEOPLE_SERVICES)[number];
export const SETUPS = ["just_me", "one_place", "many_places"] as const;
export type Setup = (typeof SETUPS)[number];
export type Emit = (type: string, payload: Record<string, unknown>, origin?: "device" | "server") => void;
type St = "queued" | "sent" | "accepted" | "confirmed" | "failed";

/** The ecosystem names from the device register, in register order. A name whose every device has no touch version only shows
 *  (LynkDScreen): it can call tickets but takes no answers, so it is offered for LynkQueue only. */
export function lynkNames(reg: DeviceRegister, service: PeopleService): string[] {
  const names = [...new Set(reg.devices.map((d) => d.lynk_name).filter((n): n is string => !!n))];
  const showsOnly = (n: string): boolean => reg.devices.filter((d) => d.lynk_name === n).every((d) => d.touch === null && d.non_touch !== null && d.non_touch.startsWith("tv."));
  return names.filter((n) => service === "queue" || !showsOnly(n));
}

/** A one-time pairing code: a Lynk Code (queue.ts alphabet), never a number someone could guess from the last one. */
const pairCode = (): string => { const b = randomBytes(4); return code(((b[0]! << 22) ^ (b[1]! << 14) ^ (b[2]! << 6) ^ b[3]!) % CAPACITY); };

interface Member { id: string; name: string; set: AttendSet; pin: string; idcn: string; state: "not_yet" | "in" | "out"; means: string; at: number; flags: string[]; backup: string | null }
interface Ticket { id: string; section: string; code: string; seq: number; priority: boolean; state: "waiting" | "called" | "served" | "missed"; calls: number; counter: string | null; at: number }
interface Counter { id: string; n: number; state: "open" | "paused" | "closed"; serving: string | null }
interface Section { code: string; key: string; last: string | null; block: { first: string; last: string } | null }
interface Door { step: "pin" | "check" | "done"; pin: string; pinFails: number; member: Member | null; attempts: ("ok" | "fail")[]; broken: string[]; typed: string; checker: string | null; out: DoorOut | null; note: string }

export class PeopleHub {
  readonly placeId = newId();
  readonly deviceId = newId();
  readonly surveyId = newId();
  setup: Record<PeopleService, Setup> = { attendance: "one_place", queue: "one_place", survey: "one_place" };
  paired: { service: PeopleService; name: string; code: string; state: St }[] = [];
  pairPick: Record<PeopleService, string> = { attendance: "", queue: "", survey: "" };
  /** Sandbox people (their PINs and IDCNs are sample values printed in the emulator's help, never real). */
  members: Member[] = [
    { name: "Aline", set: "finger_idcn" as AttendSet, pin: "482913", id: "305571" },
    { name: "Eric", set: "idcn" as AttendSet, pin: "739154", id: "120480" },
    { name: "Grace", set: "face_idcn" as AttendSet, pin: "561840", id: "774209" },
    { name: "Joseph", set: "idcn" as AttendSet, pin: "205937", id: "918366" },
  ].map((m) => ({ id: newId(), name: m.name, set: m.set, pin: m.pin, idcn: idcn(m.id) ?? "000000", state: "not_yet" as const, means: "", at: 0, flags: [], backup: null }));
  sections: Section[] = [{ code: "SRV", key: "ppl_sec_srv", last: null, block: null }, { code: "PAY", key: "ppl_sec_pay", last: null, block: null }, { code: "CLT", key: "ppl_sec_clt", last: null, block: null }];
  tickets: Ticket[] = [];
  counters: Counter[] = [1, 2].map((n) => ({ id: newId(), n, state: "open" as const, serving: null }));
  servedSincePriority = 0;
  afterPayment = true;
  /** Sandbox answers so the results can be shown (labelled "Sandbox" wherever they appear). */
  ratings: number[] = [5, 4, 4, 5, 3, 4, 5, 2, 4, 5, 4, 4];
  door: Door = PeopleHub.freshDoor();
  section = "SRV";
  priority = false;
  lastTicket: string | null = null;
  constructor(private emit: Emit, private now: () => number = Date.now) {
    for (const s of this.sections) s.block = reserveBlock(null);          // the cloud reserves a block of codes per section and device
    for (const [i, sec] of ["SRV", "SRV", "PAY"].entries()) this.issue(sec, i === 1, "reception", true);
  }
  static freshDoor(): Door { return { step: "pin", pin: "", pinFails: 0, member: null, attempts: [], broken: [], typed: "", checker: null, out: null, note: "" }; }

  // ---- setup and devices ----------------------------------------------------------------------------------------------------
  pair(service: PeopleService, name: string, online: boolean, redraw: () => void): void {
    if (!name) return;
    const p = { service, name, code: pairCode(), state: (online ? "sent" : "queued") as St };
    this.paired.unshift(p);
    if (online) setTimeout(() => { p.state = "confirmed"; redraw(); }, 1500);   // the sandbox device types the code
  }
  onlineAgain(redraw: () => void): void { for (const p of this.paired) if (p.state === "queued") { p.state = "sent"; setTimeout(() => { p.state = "confirmed"; redraw(); }, 1500); } }

  // ---- LynkAttend --------------------------------------------------------------------------------------------------------
  inCount(): number { return this.members.filter((m) => m.state === "in").length; }
  doorDigit(d: string): void {
    const D = this.door;
    if (D.step === "pin" && D.pin.length < PIN_LENGTH) { D.pin += d; D.note = ""; if (D.pin.length === PIN_LENGTH) this.doorPin(); }
    else if (D.step === "check" && D.out?.means === "idcn" && D.typed.length < IDCN_LENGTH) D.typed += d;
  }
  doorBack(): void { const D = this.door; if (D.step === "pin") D.pin = D.pin.slice(0, -1); else if (D.step === "check") D.typed = D.typed.slice(0, -1); }
  private doorPin(): void {
    const D = this.door, m = isEasyPin(D.pin) ? undefined : this.members.find((x) => x.pin === D.pin);
    D.pin = "";
    if (!m) { D.pinFails += 1; D.note = D.pinFails >= PIN_TRIES_BEFORE_PAUSE ? "ppl_door_paused" : "ppl_door_pin_wrong"; return; }
    D.member = m; D.step = "check"; D.attempts = []; D.broken = []; D.typed = ""; D.checker = null; D.out = door(m.set, [], []);
  }
  /** The reader's answer for face or finger (on the emulator, the sandbox reader buttons). */
  doorReader(result: "ok" | "fail" | "not_working"): void {
    const D = this.door; if (D.step !== "check" || !D.out || D.out.means === "idcn" || !D.out.means) return;
    if (result === "not_working") D.broken.push(D.out.means); else D.attempts.push(result);
    this.doorRun();
  }
  doorIdcn(): void {
    const D = this.door; if (D.step !== "check" || D.out?.means !== "idcn" || D.typed.length !== IDCN_LENGTH || !D.checker || !D.member) return;
    D.attempts.push(D.typed === D.member.idcn ? "ok" : "fail"); D.typed = "";
    this.doorRun();
  }
  idcnTriesLeft(): number | null {
    const D = this.door; if (!D.out || D.out.means !== "idcn") return null;
    const used = D.out.steps.filter((s) => s.means === "idcn" && s.result === "fail").length;
    return used ? IDCN_TRIES - used : null;
  }
  private doorRun(): void {
    const D = this.door, m = D.member!; D.out = door(m.set, D.attempts, D.broken);
    if (D.out.result === "waiting") return;
    D.step = "done";
    if (D.out.result === "pin_blocked") { this.emit("AttendancePinBlocked", { member_id: m.id, reason: "idcn_failed" }); return; }
    if (D.out.result === "see_manager") return;
    const checker = D.checker ? this.members.find((x) => x.name === D.checker) ?? null : null;
    const flags = D.out.means === "idcn" ? checkerFlags(checker?.state === "in") : [];
    const base: Record<string, unknown> = { record_id: newId(), member_id: m.id, device_id: this.deviceId, means: D.out.means };
    if (D.out.backup_from) base["backup_from"] = D.out.backup_from;
    if (checker) base["checker_id"] = checker.id;
    if (flags.length) base["flags"] = flags;
    if (m.state === "in") this.emit("CheckedOut", { ...base, minutes: Math.max(0, Math.round((this.now() - m.at) / 60000)) });
    else this.emit("CheckedIn", base);
    m.state = m.state === "in" ? "out" : "in"; m.means = D.out.means ?? ""; m.at = this.now(); m.flags = flags; m.backup = D.out.backup_from;
  }
  doorReset(): void { this.door = PeopleHub.freshDoor(); }
  /** The checker chosen in the IDCN step (the select of peopleparts idcnEntry, data-act "ppl:checker"); never the person themself. */
  pickChecker(name: string): void { const m = this.door.member; this.door.checker = name && m && name !== m.name && this.members.some((x) => x.name === name) ? name : null; }

  // ---- LynkQueue ---------------------------------------------------------------------------------------------------------
  issue(section: string, priority: boolean, via: "reception" | "kiosk" | "smartphone", quiet = false): Ticket | null {
    const s = this.sections.find((x) => x.code === section); if (!s || !s.block) return null;
    const c = nextCode(s.last);
    if (c === null || index(c) > index(s.block.last)) return null;            // this device's block is used up: the cloud gives the next
    s.last = c;
    const tk: Ticket = { id: newId(), section, code: c, seq: this.tickets.length + 1, priority, state: "waiting", calls: 0, counter: null, at: this.now() };
    this.tickets.push(tk); this.lastTicket = tk.id;
    if (!quiet) this.emit("TicketIssued", { ticket_id: tk.id, place_id: this.placeId, section, code: c, via, priority, device_id: this.deviceId });
    return tk;
  }
  codesLeft(section: string): number { const s = this.sections.find((x) => x.code === section); return s?.block ? index(s.block.last) - (s.last === null ? index(s.block.first) - 1 : index(s.last)) : 0; }
  waiting(section?: string): Ticket[] { return this.tickets.filter((t) => t.state === "waiting" && (!section || t.section === section)); }
  order(): string[] {
    const ids: string[] = [], left = this.waiting().map((t) => ({ id: t.id, seq: t.seq, priority: t.priority })); let since = this.servedSincePriority;
    while (left.length) { const id = pickNext(left, since, 0); if (!id) break; ids.push(id); const i = left.findIndex((x) => x.id === id); since = left[i]!.priority ? 0 : since + 1; left.splice(i, 1); }
    return ids;
  }
  openCounters(): number { return this.counters.filter((c) => c.state === "open").length; }
  callNext(counterId: string): Ticket | null {
    const c = this.counters.find((x) => x.id === counterId); if (!c || c.state !== "open" || c.serving) return null;
    const id = pickNext(this.waiting().map((t) => ({ id: t.id, seq: t.seq, priority: t.priority })), this.servedSincePriority, 0);
    const tk = this.tickets.find((t) => t.id === id); if (!tk) return null;
    tk.state = "called"; tk.calls = 1; tk.counter = c.id; c.serving = tk.id;
    this.servedSincePriority = tk.priority ? 0 : this.servedSincePriority + 1;
    this.emit("TicketCalled", { ticket_id: tk.id, counter_id: c.id, call: 1, by_number: true });
    return tk;
  }
  callAgain(counterId: string): void {
    const c = this.counters.find((x) => x.id === counterId), tk = this.tickets.find((t) => t.id === c?.serving);
    if (!c || !tk || tk.calls >= CALLS_BEFORE_MISSED) return;
    tk.calls += 1; this.emit("TicketCalled", { ticket_id: tk.id, counter_id: c.id, call: tk.calls, by_number: true });
  }
  finish(counterId: string, how: "served" | "missed"): void {
    const c = this.counters.find((x) => x.id === counterId), tk = this.tickets.find((t) => t.id === c?.serving);
    if (!c || !tk || (how === "missed" && tk.calls < CALLS_BEFORE_MISSED)) return;
    tk.state = how; c.serving = null;
    this.emit(how === "served" ? "TicketServed" : "TicketMissed", how === "served" ? { ticket_id: tk.id, counter_id: c.id } : { ticket_id: tk.id });
  }
  sendTo(counterId: string, to: string): void {
    const c = this.counters.find((x) => x.id === counterId), tk = this.tickets.find((t) => t.id === c?.serving);
    if (!c || !tk || to === tk.section || !this.sections.some((s) => s.code === to)) return;
    tk.section = to; tk.state = "waiting"; tk.calls = 0; tk.counter = null; c.serving = null;
    this.emit("TicketSentTo", { ticket_id: tk.id, to_section: to });
  }
  counterState(counterId: string, state: Counter["state"]): void {
    const c = this.counters.find((x) => x.id === counterId); if (!c || c.state === state || (state !== "open" && c.serving)) return;
    c.state = state; this.emit("CounterStateChanged", { counter_id: c.id, place_id: this.placeId, state });
  }
  view(tk: Ticket, t: T): { section: string; sectionName: string; code: string; place: number | null; waitMinutes: number | null; counter: string | null } {
    const sec = this.sections.find((s) => s.code === tk.section), place = tk.state === "waiting" ? this.order().indexOf(tk.id) + 1 : null;
    const c = this.counters.find((x) => x.id === tk.counter);
    return { section: tk.section, sectionName: t(sec?.key ?? ""), code: tk.code, place, waitMinutes: place ? waitMinutes(place, 4, this.openCounters()) : null, counter: tk.state === "called" && c ? t("ppl_counter_n", { n: c.n }) : null };
  }

  // ---- LynkSurvey --------------------------------------------------------------------------------------------------------
  rate(n: number, way: "pos" | "kiosk", language: string): boolean {
    if (!this.afterPayment || !Number.isInteger(n) || n < 1 || n > 5) return false;
    this.ratings.push(n);
    this.emit("SurveyAnswered", { answer_id: newId(), survey_id: this.surveyId, version: 1, way, device_id: this.deviceId, language, answers: [{ q: "after_payment", number: n }] });
    return true;
  }
  results(): { n: number; avgTenths: number; goodPercent: number; marginTenths: number | null } | null {
    const n = this.ratings.length; if (!canShow(n)) return null;
    const good = Math.round((this.ratings.filter((r) => r >= 4).length * 100) / n);
    return { n, avgTenths: Math.round((this.ratings.reduce((a, b) => a + b, 0) * 10) / n), goodPercent: good, marginTenths: margin(good, n) };
  }

  // ---- act: every control of these screens is a button whose data-act starts with "ph:" ------------------------------------
  act(a: string, ctx: { online: boolean; redraw: () => void; language: string }): boolean {
    if (!a.startsWith("ph:")) return false;
    const [, k = "", v = "", w = ""] = a.split(":");
    switch (k) {
      case "setup": { const [svc, s] = [v as PeopleService, w as Setup]; if ((PEOPLE_SERVICES as readonly string[]).includes(svc) && (SETUPS as readonly string[]).includes(s)) this.setup[svc] = s; break; }
      case "pick": if ((PEOPLE_SERVICES as readonly string[]).includes(v)) this.pairPick[v as PeopleService] = w; break;
      case "pair": if ((PEOPLE_SERVICES as readonly string[]).includes(v)) this.pair(v as PeopleService, this.pairPick[v as PeopleService], ctx.online, ctx.redraw); break;
      case "section": if (this.sections.some((s) => s.code === v)) this.section = v; break;
      case "priority": this.priority = !this.priority; break;
      case "issue": this.issue(this.section, this.priority, "reception"); this.priority = false; break;
      case "call": this.callNext(v); break;
      case "again": this.callAgain(v); break;
      case "served": this.finish(v, "served"); break;
      case "missed": this.finish(v, "missed"); break;
      case "sendto": this.sendTo(v, w); break;
      case "counter": this.counterState(v, w === "paused" || w === "closed" ? w : "open"); break;
      case "afterpay": this.afterPayment = !this.afterPayment; break;
      case "reader": this.doorReader(v === "ok" ? "ok" : v === "fail" ? "fail" : "not_working"); break;
      case "idcn": this.doorIdcn(); break;
      case "digit": if (/^\d$/.test(v)) this.doorDigit(v); break;
      case "doorback": this.doorBack(); break;
      case "doornext": this.doorReset(); break;
      case "rate": this.rate(Number(v), "pos", ctx.language); break;
      default: return false;
    }
    return true;
  }
}

// ---- drawing: shared cards for the Business app hub and the device screens ------------------------------------------------
const pressed = (on: boolean): string => `aria-pressed="${on}"`;
const chipOf = (s: St, t: T, icon: Icon): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;

/** Just me, One place, Many places: the same prices and rules, only how the screens are laid out changes. */
export function setupCard(h: PeopleHub, svc: PeopleService, t: T): string {
  return `<div class="card ph-setup" role="group" aria-labelledby="phS-${svc}"><h2 id="phS-${svc}">${esc(t("ppl_setup_title"))}</h2><div class="ph-choices">${SETUPS.map((s) =>
    `<button type="button" class="ph-choice" data-act="ph:setup:${svc}:${s}" ${pressed(h.setup[svc] === s)}><strong>${esc(t(`ppl_setup_${s}`))}</strong><span>${esc(t(`ppl_setup_${s}_help`))}</span></button>`).join("")}</div>
    <p class="sub">${esc(t("ppl_setup_note"))}</p></div>`;
}
/** Add a device: pick an ecosystem device, get a one-time code to type on it. */
export function devicesCard(h: PeopleHub, svc: PeopleService, reg: DeviceRegister, t: T, icon: Icon, mayAdd: boolean): string {
  const names = lynkNames(reg, svc), mine = h.paired.filter((p) => p.service === svc);
  const last = mine[0];
  return `<div class="card ph-devices" role="group" aria-labelledby="phD-${svc}"><h2 id="phD-${svc}">${esc(t("ppl_add_device"))}</h2><p class="sub">${esc(t("ppl_pair_pick"))}</p>
    <div class="ph-choices small">${names.map((n) => `<button type="button" class="ph-choice" data-act="ph:pick:${svc}:${esc(n)}" ${pressed(h.pairPick[svc] === n)} ${mayAdd ? "" : "disabled"}><strong>${esc(n)}</strong></button>`).join("")}</div>
    <button type="button" class="primary inline" data-act="ph:pair:${svc}" ${mayAdd && h.pairPick[svc] ? "" : "disabled"}>${esc(t("ppl_get_code"))}</button>${mayAdd ? "" : `<p class="sub">${esc(t("ppl_owner_manager_only"))}</p>`}
    ${last && last.state !== "confirmed" ? `<p class="ph-code" role="status">${esc(t("ppl_pair_code"))} <strong dir="ltr">${esc(last.code)}</strong></p>` : ""}
    <ul class="list">${mine.length ? mine.map((p) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(p.name)}</span></span>${chipOf(p.state, t, icon)}</div></li>`).join("") : `<li><p class="sub">${esc(t("ppl_paired_none"))}</p></li>`}</ul>
    <p class="sub">${esc(t("ppl_pair_note"))}</p></div>`;
}
/** Today at the door: who is in, how they checked in, any backup or flag said in words. */
export function attendanceToday(h: PeopleHub, t: T, clock: (ms: number) => string): string {
  return `<div class="card"><h2>${esc(t("ppl_today"))} · ${esc(t("ppl_in_count", { n: h.inCount(), of: h.members.length }))}</h2><ul class="list">${h.members.map((m) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(m.name)}</span>
    <span class="sub">${esc(t(`ppl_state_${m.state}`))}${m.at ? ` · ${esc(clock(m.at))} · ${esc(t(`ppl_means_${m.means}`))}` : ""}${m.backup ? ` · ${esc(t("ppl_backup"))}` : ""}${m.flags.map((f) => ` · ${esc(t(`ppl_flag_${f}`))}`).join("")}</span></span></div></li>`).join("")}</ul></div>`;
}
/** Where the door runs: every device that can take a PIN (from the register). */
export const doorWhere = (reg: DeviceRegister, t: T): string => `<p class="sub">${esc(t("ppl_door_where", { devices: lynkNames(reg, "attendance").join(", ") }))}</p>`;

export function sectionsCard(h: PeopleHub, t: T): string {
  return `<div class="card"><h2>${esc(t("ppl_sections"))}</h2><ul class="list">${h.sections.map((s) => `<li><div class="rowbtn static"><span class="main"><span class="nm"><span dir="ltr">${esc(s.code)}</span> · ${esc(t(s.key))}</span>
    <span class="sub">${esc(t("ppl_waiting_n", { n: h.waiting(s.code).length }))} · ${esc(t("ppl_codes_left", { n: h.codesLeft(s.code) }))}</span></span></div></li>`).join("")}</ul></div>`;
}
/** Reception: pick the section, mark priority if needed, give the ticket (works offline from this device's block of codes). */
export function receptionCard(h: PeopleHub, t: T, icon: Icon): string {
  const tk = h.tickets.find((x) => x.id === h.lastTicket);
  return `<div class="card ph-reception" role="group" aria-labelledby="phR"><h2 id="phR">${esc(t("ppl_reception_title"))}</h2><div class="ph-choices small">${h.sections.map((s) =>
    `<button type="button" class="ph-choice" data-act="ph:section:${s.code}" ${pressed(h.section === s.code)}><strong>${esc(t(s.key))}</strong><span dir="ltr">${esc(s.code)}</span></button>`).join("")}</div>
    <button type="button" class="ph-toggle" data-act="ph:priority" ${pressed(h.priority)}>${h.priority ? icon("ui-check") : ""}<span>${esc(t("ppl_priority"))}</span></button>
    <button type="button" class="primary inline" data-act="ph:issue">${esc(t("ppl_issue"))}</button>${tk ? ticketCard(h.view(tk, t), t, icon) : ""}<p class="sub">${esc(t("ppl_works_offline"))}</p></div>`;
}
/** A counter: open, pause or close; Call next (the fair order: staff never choose); call again up to 3 times; served, missed or sent on. */
export function counterCard(h: PeopleHub, counterId: string, t: T, icon: Icon): string {
  const c = h.counters.find((x) => x.id === counterId); if (!c) return "";
  const tk = h.tickets.find((x) => x.id === c.serving);
  const states = (["open", "paused", "closed"] as const).map((s) => `<button type="button" class="ph-choice" data-act="ph:counter:${c.id}:${s}" ${pressed(c.state === s)} ${tk && s !== "open" ? "disabled" : ""}><strong>${esc(t(`ppl_counter_${s}`))}</strong></button>`).join("");
  const serving = tk ? `${ticketCard(h.view(tk, t), t, icon)}<p class="sub">${esc(t("ppl_calls_n", { n: tk.calls, of: CALLS_BEFORE_MISSED }))}</p><div class="ph-row">
      <button type="button" class="primary" data-act="ph:served:${c.id}">${esc(t("ppl_served"))}</button><button type="button" class="ghost" data-act="ph:again:${c.id}" ${tk.calls >= CALLS_BEFORE_MISSED ? "disabled" : ""}>${esc(t("ppl_call_again"))}</button>
      <button type="button" class="ghost" data-act="ph:missed:${c.id}" ${tk.calls >= CALLS_BEFORE_MISSED ? "" : "disabled"}>${esc(t("ppl_missed"))}</button></div>
      <div class="ph-row">${h.sections.filter((s) => s.code !== tk.section).map((s) => `<button type="button" class="ghost small" data-act="ph:sendto:${c.id}:${s.code}">${esc(t("ppl_send_to", { section: t(s.key) }))}</button>`).join("")}</div>`
    : `<button type="button" class="primary inline" data-act="ph:call:${c.id}" ${c.state === "open" && h.waiting().length ? "" : "disabled"}>${esc(t("ppl_call_next"))}</button>${h.waiting().length ? "" : `<p class="sub">${esc(t("ppl_no_one_waiting"))}</p>`}`;
  return `<div class="card ph-counter" role="group" aria-labelledby="phC-${c.n}"><h2 id="phC-${c.n}">${esc(t("ppl_counter_n", { n: c.n }))}</h2><div class="ph-choices small">${states}</div>${serving}</div>`;
}
/** Waiting now, in the fair order, with the place and the estimate each person sees. */
export function waitingCard(h: PeopleHub, t: T): string {
  const order = h.order();
  return `<div class="card"><h2>${esc(t("ppl_waiting_n", { n: order.length }))}</h2><ol class="list">${order.map((id) => { const tk = h.tickets.find((x) => x.id === id)!; const v = h.view(tk, t);
    return `<li><div class="rowbtn static"><span class="main"><span class="nm" dir="ltr">${esc(ticketNumber(tk.section, tk.code))}</span><span class="sub">${esc(v.sectionName)}${tk.priority ? ` · ${esc(t("ppl_priority_short"))}` : ""} · ${esc(t("ppl_place", { n: String(v.place ?? "") }))}</span></span></div></li>`; }).join("")}</ol>
    ${order.length ? "" : `<p class="sub">${esc(t("ppl_no_one_waiting"))}</p>`}</div>`;
}
/** The rating after payment: the switch, the preview customers see, and the results (never fewer than 5 answers). */
export function surveyCard(h: PeopleHub, t: T, maySet: boolean): string {
  const r = h.results();
  const fmt = (tenths: number): string => (tenths / 10).toFixed(1);
  return `<div class="card ph-survey"><button type="button" class="ph-toggle" data-act="ph:afterpay" ${pressed(h.afterPayment)} ${maySet ? "" : "disabled"}><span>${esc(t("ppl_after_payment"))}</span><strong>${esc(t(h.afterPayment ? "ppl_on" : "ppl_off"))}</strong></button>
    <p class="sub">${esc(t("ppl_after_payment_help"))}</p></div>
    <div class="card"><h2>${esc(t("ppl_results"))} <span class="tag">${esc(t("ppl_sandbox_answers"))}</span></h2>${r ? `<p><strong>${esc(t("ppl_average", { avg: fmt(r.avgTenths) }))}</strong></p>
      <p>${esc(t("ppl_good_share", { share: r.goodPercent, margin: fmt(r.marginTenths ?? 0) }))}</p><p class="sub">${esc(t("ppl_answers_n", { n: r.n }))}</p>` : `<p class="sub">${esc(t("ppl_too_few", { n: MIN_GROUP }))}</p>`}</div>`;
}
/** The rating on the customer's screen after a confirmed payment: buttons on a touch screen, the QR on a screen that only shows. */
export function afterPaymentRating(h: PeopleHub, touch: boolean, chosen: number | null, t: T, icon: Icon): string {
  if (!h.afterPayment) return "";
  return `<div class="ph-rate">${touch ? quickRating(t("ppl_rate_title"), chosen, t) : rateUs(icon, t)}</div>`;
}
/** The door on a LynkPOS or a LynkKiosk: PIN, then the person's set (face or finger first, IDCN last with a checker). */
export function doorScreen(h: PeopleHub, t: T, icon: Icon, clock: (ms: number) => string): string {
  const D = h.door, m = D.member;
  if (D.step === "pin") return `<div class="ph-door"><h2>${esc(t("ppl_door_pin"))}</h2><div class="dots" role="img" aria-label="${esc(t("ppl_digits_typed", { n: D.pin.length, of: PIN_LENGTH }))}">${Array.from({ length: PIN_LENGTH }, (_, i) => `<i class="${i < D.pin.length ? "on" : ""}"></i>`).join("")}</div>
    ${D.note ? `<p class="note" role="alert">${esc(t(D.note))}</p>` : ""}<p class="sub">${esc(t("ppl_door_offline"))}</p></div>`;
  if (D.step === "done" && D.out) {
    const ok = D.out.result === "in";
    const msg = ok ? t(m!.state === "in" ? "ppl_door_welcome" : "ppl_door_bye", { name: m!.name, time: clock(m!.at) }) : t(D.out.result === "pin_blocked" ? "ppl_door_blocked" : "ppl_door_see_manager");
    return `<div class="ph-door done">${icon(ok ? "ui-check" : "ui-warning", "bigcheck")}<h2 role="status">${esc(msg)}</h2>${ok && D.out.backup_from ? `<p class="sub">${esc(t("ppl_backup"))}</p>` : ""}
      ${m!.flags.map((f) => `<p class="sub">${esc(t(`ppl_flag_${f}`))}</p>`).join("")}<button type="button" class="primary" data-act="ph:doornext">${esc(t("ppl_next_person"))}</button></div>`;
  }
  const means = D.out?.means;
  if (means === "idcn") return `<div class="ph-door">${idcnEntry({ typed: D.typed.length, checkers: h.members.map((x) => x.name), me: m!.name, chosen: D.checker, triesLeft: h.idcnTriesLeft() }, t)}
    <button type="button" class="primary" data-act="ph:idcn" ${D.typed.length === IDCN_LENGTH && D.checker ? "" : "disabled"}>${esc(t("ppl_check_in"))}</button></div>`;
  return `<div class="ph-door"><h2>${esc(t(means === "face" ? "ppl_door_face" : "ppl_door_finger"))}</h2>${icon(means === "face" ? "ui-user" : "ui-lock", "bigcheck")}
    <p class="sub">${esc(t("ppl_reader_sandbox"))}</p><div class="ph-row"><button type="button" class="primary" data-act="ph:reader:ok">${esc(t("ppl_reader_ok"))}</button>
    <button type="button" class="ghost" data-act="ph:reader:fail">${esc(t("ppl_reader_fail"))}</button><button type="button" class="ghost" data-act="ph:reader:broken">${esc(t("ppl_reader_broken"))}</button></div></div>`;
}
