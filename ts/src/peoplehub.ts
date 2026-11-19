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
import { newId } from "./emulator.js";
import { AttendDesk } from "./attenddesk.js";
import type { AtPlan, AtTier, Person } from "./attenddesk.js";
import { QueueDesk, pairCode } from "./queuedesk.js";
import type { QuPlan } from "./queuedesk.js";
import { SV_OPEN_PLAN, SurveyDesk } from "./surveydesk.js";
import type { SvPlan } from "./surveydesk.js";
import { canShow, margin, MIN_GROUP } from "./survey.js";
import type { DeviceRegister } from "./interfaces.js";

export const PEOPLE_SERVICES = ["attendance", "queue", "survey"] as const;
export type PeopleService = (typeof PEOPLE_SERVICES)[number];
export const SETUPS = ["just_me", "one_place", "many_places"] as const;
export type Setup = (typeof SETUPS)[number];
/** Plan numbers come from services/billing.py through the build; a device that was given none shows none. */
const NO_PLAN: AtPlan = { price_usd: 0, people_included: 0, extra_person_cents: null, branches: null, managers: null, door_devices: null };
const NO_PLANS: Record<AtTier, AtPlan> = { free: NO_PLAN, plus: NO_PLAN, pro: NO_PLAN, max: NO_PLAN };
const QU_NO_PLAN: QuPlan = { price_usd: 0, places_included: 1, extra_place_cents: 0, max_places: null, tickets_per_place_month: 0, sections_per_place: null, counters_per_place: null, staff_accounts: null, basic_phone: true, whatsapp_and_chat: true,
  appointments: true, send_to: true, own_hardware: true, busy_forecast: true, own_logo: true, reports: "full", history_months: null };
const QU_NO_PLANS: Record<AtTier, QuPlan> = { free: QU_NO_PLAN, plus: QU_NO_PLAN, pro: QU_NO_PLAN, max: QU_NO_PLAN };
export type Emit = (type: string, payload: Record<string, unknown>, origin?: "device" | "server") => void;
type St = "queued" | "sent" | "accepted" | "confirmed" | "failed";

/** The ecosystem names from the device register, in register order. A name whose every device has no touch version only shows
 *  (LynkDScreen): it can call tickets but takes no answers, so it is offered for LynkQueue only. */
export function lynkNames(reg: DeviceRegister, service: PeopleService): string[] {
  const names = [...new Set(reg.devices.map((d) => d.lynk_name).filter((n): n is string => !!n))];
  const showsOnly = (n: string): boolean => reg.devices.filter((d) => d.lynk_name === n).every((d) => d.touch === null && d.non_touch !== null && d.non_touch.startsWith("tv."));
  return names.filter((n) => service === "queue" || !showsOnly(n));
}


export class PeopleHub {
  readonly placeId = newId();
  readonly deviceId = newId();
  readonly surveyId = newId();
  setup: Record<PeopleService, Setup> = { attendance: "one_place", queue: "one_place", survey: "one_place" };
  paired: { service: PeopleService; name: string; code: string; state: St }[] = [];
  pairPick: Record<PeopleService, string> = { attendance: "", queue: "", survey: "" };
  /** LynkAttend's own engine (ts/src/attenddesk.ts): the people, the door, the records and the manager's dashboard. */
  readonly att: AttendDesk;
  get members(): Person[] { return this.att.people; }
  get door(): AttendDesk["door"] { return this.att.door; }
  /** LynkQueue's own engine (ts/src/queuedesk.ts): the queue keeper, reception, the counters and every screen around them. */
  readonly q: QueueDesk;
  /** LynkSurvey's own engine (ts/src/surveydesk.ts): building, answering on every device, results and the research tools. */
  readonly s: SurveyDesk;
  afterPayment = true;
  /** Sandbox answers so the results can be shown (labelled "Sandbox" wherever they appear). */
  ratings: number[] = [5, 4, 4, 5, 3, 4, 5, 2, 4, 5, 4, 4];
  constructor(private emit: Emit, private now: () => number = Date.now, plans: Record<AtTier, AtPlan> = NO_PLANS, quPlans: Record<AtTier, QuPlan> = QU_NO_PLANS,
              svPlans: Record<AtTier, SvPlan> = { free: SV_OPEN_PLAN, plus: SV_OPEN_PLAN, pro: SV_OPEN_PLAN, max: SV_OPEN_PLAN }) {
    this.att = new AttendDesk(emit, plans, now);
    this.q = new QueueDesk(emit, quPlans, now);
    this.s = new SurveyDesk(emit, svPlans, now);
  }

  // ---- setup and devices ----------------------------------------------------------------------------------------------------
  pair(service: PeopleService, name: string, online: boolean, redraw: () => void): void {
    if (!name) return;
    const p = { service, name, code: pairCode(), state: (online ? "sent" : "queued") as St };
    this.paired.unshift(p);
    if (online) setTimeout(() => { p.state = "confirmed"; redraw(); }, 1500);   // the sandbox device types the code
  }
  onlineAgain(redraw: () => void): void { for (const p of this.paired) if (p.state === "queued") { p.state = "sent"; setTimeout(() => { p.state = "confirmed"; redraw(); }, 1500); } }

  // ---- LynkAttend (the door runs in ts/src/attenddesk.ts; these keep the device screens' short names)
  inCount(): number { return this.att.inCount(); }
  doorDigit(d: string): void { this.att.doorDigit(d); }
  doorBack(): void { this.att.doorBack(); }
  doorReader(result: "ok" | "fail" | "not_working"): void { this.att.doorReader(result); }
  doorIdcn(): void { this.att.doorIdcn(); }
  doorReset(): void { this.att.doorReset(); }
  pickChecker(name: string): void { this.att.pickChecker(name); }
  idcnTriesLeft(): number | null { return this.att.idcnTriesLeft(); }

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
      case "afterpay": this.afterPayment = !this.afterPayment; break;
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

/** The rating after payment: the switch, the preview customers see, and the results (never fewer than 5 answers). */
export function surveyCard(h: PeopleHub, t: T, maySet: boolean): string {
  const r = h.results();
  const fmt = (tenths: number): string => (tenths / 10).toFixed(1);
  return `<div class="card ph-survey"><button type="button" class="ph-toggle" data-act="ph:afterpay" ${pressed(h.afterPayment)} ${maySet ? "" : "disabled"}><span>${esc(t("ppl_after_payment"))}</span><strong>${esc(t(h.afterPayment ? "ppl_on" : "ppl_off"))}</strong></button>
    <p class="sub">${esc(t("ppl_after_payment_help"))}</p></div>
    <div class="card"><h2>${esc(t("ppl_results"))} <span class="tag">${esc(t("ppl_sandbox_answers"))}</span></h2>${r ? `<p><strong>${esc(t("ppl_average", { avg: fmt(r.avgTenths) }))}</strong></p>
      <p>${esc(t("ppl_good_share", { share: r.goodPercent, margin: fmt(r.marginTenths ?? 0) }))}</p><p class="sub">${esc(t("ppl_answers_n", { n: r.n }))}</p>` : `<p class="sub">${esc(t("ppl_too_few", { n: MIN_GROUP }))}</p>`}</div>`;
}
