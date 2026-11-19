/** The Emulator Panel (EMULATOR UPDATE, master blueprint section 70; build section 3A): the one place where a manager gives
 *  emulators to devices, sees every device, emulator and user live, and connects or disconnects them. The overall panel lives in
 *  the business settings (app.lynkomni.com/business/emulators); inside a service it shows that service's emulators (the service
 *  path plus /emulators); the Storefront side is the same panel under /external.
 *
 *  The rules are ts/src/emulators.ts (the port of core/emulators.py): only connected staff emulators count against the plan, a till
 *  that runs several services counts once, customer-facing screens and practice mode are free, an extra slot is the locked price in
 *  services/billing.py. The cloud alone connects, disconnects, locks and swaps (contract v7), so the manager's taps here are
 *  requests shown with the five user states. A PIN, a position or a person's name is never in an event: the place shown is the
 *  branch. The devices here are sandbox devices, labelled so. */
import { esc } from "./shell.js";
import type { Icon, T } from "./shell.js";
import { newId } from "./emulator.js";
import { canRun, cheaperTier, countsFor, inUse, mayConnect, newCode, slots } from "./emulators.js";
import type { Caps, Connection, EmulatorRegister, Limit } from "./emulators.js";

type St = "queued" | "sent" | "accepted" | "confirmed" | "failed";
export type Emit = (type: string, payload: Record<string, unknown>, origin?: "device" | "server") => void;
export interface PanelLook {
  t: T; icon: Icon; online: boolean; mayManage: boolean; tier: string;
  /** The family's product name (from the catalog, through the build). */
  familyName: (family: string) => string;
  clock: (ms: number) => string;
  money: (cents: number) => string;
  /** The control that opens a service's own panel (its address), or the overall one for null. */
  go?: (family: string | null) => string;
}
export interface PanelEm { id: string; state: "connected" | "disconnected" | "disconnect_sent" | "request_sent"; practice: boolean; user: string | null; since: number; unsent: number }
export interface PanelDevice {
  id: string; name: string; lynk: string; os: string; branch: string; caps: Caps; online: boolean; battery: number | null; unsent: number;
  printer: "ready" | "paper_low" | "out_of_paper" | "not_connected" | null; morning: "passed" | "failed" | null; lost: boolean; reapprove: boolean; tag: string;
  ems: PanelEm[]; sandbox: true;
}
export interface PanelOffer { id: string; emulator: string; code: string; link: string; issued: number; state: St; reason: string }
export interface PanelHistory { at: number; what: string; device: string; emulator: string; user: string | null }

const DAY_MS = 86_400_000;
const LOW_BATTERY = 15, MANY_UNSENT = 50;

export class EmulatorPanelDesk {
  devices: PanelDevice[] = [];
  offers: PanelOffer[] = [];
  history: PanelHistory[] = [];
  extra: Record<string, number> = {};
  /** Day passes bought today per family (one more staff device for an event or a market day, any tier). */
  passes: Record<string, number> = {};
  /** The manager's default key tones per device (70.6). */
  tones: Record<string, { tones: boolean; vibration: boolean; volume: string; user_may_change: boolean; pin_same_tone: boolean }> = {};
  pick = "";
  open = "";
  filter = "";
  service: string | null = null;
  side: "internal" | "external" = "internal";
  viewing: Record<string, St> = {};
  why: Record<string, string[]> = {};
  private n = 0;
  constructor(readonly reg: EmulatorRegister, private emit: Emit, private now: () => number = Date.now) {
    const t0 = this.now();
    const add = (name: string, lynk: string, os: string, caps: Caps, ems: [string, string | null][], h: Partial<PanelDevice> = {}): void => {
      const id = newId();
      this.devices.push({ id, name, lynk, os, branch: "main", caps, online: true, battery: 80, unsent: 0, printer: null, morning: "passed", lost: false, reapprove: false, tag: "", sandbox: true, ...h,
        ems: ems.map(([e, u]) => ({ id: e, state: "connected", practice: false, user: u, since: t0 - 3 * 3600_000, unsent: 0 })) });
      this.tones[id] = { tones: true, vibration: true, volume: "medium", user_may_change: !ems.some(([e]) => this.find(e)?.user === "none"), pin_same_tone: false };
    };
    add("Counter 1", "LynkPOS", "android", { short_side: 480, touch: true, keys: true, camera: true, speaker: true, device_print: true, hardware: ["receipt_printer", "cash_drawer"] }, [["pos.terminal", "Ama"], ["rewards.till", "Ama"]], { printer: "ready" });
    add("Kitchen", "LynkTab", "android", { short_side: 800, touch: true, speaker: true }, [["pos.kitchen_screen", null]], { battery: 12 });
    this.devices[1]!.ems[0]!.state = "disconnected";                                  // the free plan has one staff device: the kitchen waits for a bigger plan
    add("Waiting room", "LynkDScreen", "tv", { short_side: 1080, keys: true, speaker: true }, [["queue.board", null]]);
    add("Spare phone", "LynkMobile", "android", { short_side: 390, touch: true, camera: true, speaker: true }, [], { online: false, unsent: 7 });
  }
  find(id: string): EmulatorRegister["emulators"][number] | undefined { return this.reg.emulators.find((e) => e.id === id); }
  /** The emulators this panel offers: built ones, of this service when it is a service's panel. */
  choices(): string[] { return this.reg.emulators.filter((e) => !e.planned && (!this.service || e.service === this.service || e.shared_with === this.service)).map((e) => e.id); }
  conns(): Connection[] { return this.devices.flatMap((d) => d.ems.map((e) => ({ device: d.id, emulator: e.id, connected: e.state === "connected" || e.state === "disconnect_sent", practice: e.practice }))); }
  limit(family: string): Limit { return slots(this.reg, family, this.tier); }
  tier = "free";
  /** In use against the plan, per counted family, and the free customer-facing screens. */
  usage(): { family: string; used: number; limit: Limit; extra: number }[] {
    const fams = [...new Set(this.reg.emulators.filter((e) => !e.planned).map((e) => countsFor(this.reg, e.id)).filter((f): f is string => !!f))];   // families with emulators built so far
    return fams.filter((f) => !this.service || f === this.service).map((f) => ({ family: f, used: inUse(this.reg, f, this.conns()), limit: this.limit(f), extra: (this.extra[f] ?? 0) + (this.passes[f] ?? 0) }));
  }
  freeScreens(): number { return this.devices.reduce((n, d) => n + d.ems.filter((e) => e.state === "connected" && countsFor(this.reg, e.id) === null).length, 0); }
  dev(id: string): PanelDevice | undefined { return this.devices.find((d) => d.id === id); }
  private log(what: string, d: PanelDevice, emulator = "", user: string | null = null): void { this.history.unshift({ at: this.now(), what, device: d.name, emulator, user }); }

  /** Add a device: a QR code, a 6-character Lynk Code and a link that work once and expire (the cloud writes EmulatorOffered). */
  offer(online: boolean, redraw: () => void): PanelOffer | null {
    if (!this.pick) return null;
    const code = newCode((this.now() / 1000 + ++this.n * 7919) >>> 0);
    const o: PanelOffer = { id: newId(), emulator: this.pick, code, link: `https://app.lynkomni.com/business/emulators?code=${code}`, issued: this.now(), state: online ? "sent" : "queued", reason: "" };
    this.offers.unshift(o);
    if (online) this.emit("EmulatorOffered", { assignment_id: o.id, emulator: o.emulator, way: "code", expires_in_minutes: this.reg.code_minutes }, "server");
    if (online) setTimeout(() => { this.sandboxAccept(o); redraw(); }, 1500);       // the sandbox device scans the code and taps Accept
    return o;
  }
  /** The sandbox device answers: a new LynkMobile accepts, then the cloud connects it if the plan has room (else failed, plan_limit). */
  sandboxAccept(o: PanelOffer): void {
    if (o.state !== "sent") return;
    const e = this.find(o.emulator), lynk = e?.devices[0] ?? "LynkMobile", keysOnly = e?.touch === false;
    const d: PanelDevice = { id: newId(), name: `${lynk} ${this.devices.length + 1}`, lynk, os: lynk === "LynkDScreen" ? "tv" : "android", branch: "main",
      caps: { short_side: Math.max(390, e?.min_short_side_px ?? 0), touch: !keysOnly, keys: keysOnly || lynk === "LynkPOS", camera: !keysOnly, speaker: true }, online: true,
      battery: keysOnly ? null : 64, unsent: 0, printer: null, morning: null, lost: false, reapprove: false, tag: "", ems: [], sandbox: true };
    const chk = canRun(this.reg, o.emulator, { ...d.caps, os: d.os });
    if (!chk.ok) { o.state = "failed"; o.reason = chk.refused ?? ""; return; }
    o.state = "accepted";
    const fam = countsFor(this.reg, o.emulator) ?? "";
    const [ok, why] = mayConnect(this.reg, this.limit(fam), fam, this.conns(), { device: d.id, emulator: o.emulator }, (this.extra[fam] ?? 0) + (this.passes[fam] ?? 0));
    if (!ok) { o.state = "failed"; o.reason = why ?? ""; return; }
    this.devices.push(d); this.tones[d.id] = { tones: true, vibration: true, volume: "medium", user_may_change: this.find(o.emulator)?.user !== "none", pin_same_tone: false };
    d.ems.push({ id: o.emulator, state: "connected", practice: false, user: null, since: this.now(), unsent: 0 });
    this.emit("EmulatorConnected", { assignment_id: o.id, device_id: d.id, emulator: o.emulator }, "server");
    o.state = "confirmed"; this.log("connected", d, o.emulator);
  }
  /** Guided setup ("Set up my queue"): one offer for each of the service's built emulators, walked through one by one. */
  guided(service: string, online: boolean, redraw: () => void): number {
    const ids = this.reg.emulators.filter((e) => e.service === service && !e.planned && !e.shared_with).map((e) => e.id);
    for (const id of ids) { this.pick = id; this.offer(online, redraw); }
    return ids.length;
  }
  connect(devId: string, em: string, practice = false): { state: St; reason?: string } {
    const d = this.dev(devId); if (!d) return { state: "failed", reason: "no_such_device" };
    if (d.lost) return { state: "failed", reason: "device_lost_or_removed" };
    if (d.reapprove) return { state: "failed", reason: "reapproval_needed" };
    const fam = countsFor(this.reg, em) ?? "";
    const [ok, why] = mayConnect(this.reg, this.limit(fam), fam, this.conns().filter((c) => !(c.device === devId && c.emulator === em)), { device: devId, emulator: em, practice }, (this.extra[fam] ?? 0) + (this.passes[fam] ?? 0));
    if (!ok) return { state: "failed", reason: why ?? "plan_limit" };
    const e = d.ems.find((x) => x.id === em);
    if (e) { e.state = "connected"; e.practice = practice; e.since = this.now(); } else d.ems.push({ id: em, state: "connected", practice, user: null, since: this.now(), unsent: 0 });
    const p: Record<string, unknown> = { assignment_id: newId(), device_id: d.id, emulator: em }; if (practice) p["practice"] = true;
    this.emit("EmulatorConnected", p, "server"); this.log(practice ? "practice" : "connected", d, em);
    return { state: "confirmed" };
  }
  /** Safe disconnect: the device first sends its unsent records; offline, it is "sent" until the device next reaches the cloud. */
  disconnect(devId: string, em: string): St {
    const d = this.dev(devId), e = d?.ems.find((x) => x.id === em); if (!d || !e) return "failed";
    if (!d.online) { e.state = "disconnect_sent"; e.unsent = d.unsent; return "sent"; }
    e.state = "disconnected"; e.user = null;
    this.emit("EmulatorDisconnected", { device_id: d.id, emulator: em, reason: "manager", unsent: 0 }, "server"); this.log("disconnected", d, em);
    return "confirmed";
  }
  /** The device came back: a disconnect made while it was offline lands now, after its records. */
  backOnline(devId: string): void {
    const d = this.dev(devId); if (!d) return;
    d.online = true;
    for (const e of d.ems) if (e.state === "disconnect_sent") { e.state = "disconnected"; e.user = null; this.emit("EmulatorDisconnected", { device_id: d.id, emulator: e.id, reason: "manager", unsent: d.unsent }, "server"); this.log("disconnected", d, e.id); }
    d.unsent = 0;
  }
  lost(devId: string, found = false): void {
    const d = this.dev(devId); if (!d) return;
    d.lost = !found; const p: Record<string, unknown> = { device_id: d.id }; if (found) p["found"] = true;
    this.emit("DeviceMarkedLost", p, "server"); this.log(found ? "found" : "lost", d);
  }
  approve(devId: string): void {
    const d = this.dev(devId); if (!d || !d.reapprove) return;
    d.reapprove = false; this.emit("DeviceApprovedAgain", { device_id: d.id }, "server"); this.log("approved", d);
  }
  /** The daily check: a device not seen for the register's days needs approving again (here the sandbox spare phone). */
  notSeen(devId: string, days: number): void {
    const d = this.dev(devId); if (!d || days < this.reg.reapprove_days) return;
    d.reapprove = true; this.emit("EmulatorReapprovalNeeded", { device_id: d.id, days }, "server");
  }
  swap(fromId: string, toId: string, em: string): St {
    const a = this.dev(fromId), b = this.dev(toId), e = a?.ems.find((x) => x.id === em); if (!a || !b || !e || a === b) return "failed";
    this.emit("EmulatorSwapStarted", { from_device_id: a.id, to_device_id: b.id, emulator: em }, "server");
    a.ems = a.ems.filter((x) => x !== e); b.ems.push({ ...e, since: this.now() }); this.tones[b.id] = { ...(this.tones[a.id] ?? this.tones[b.id]!) };
    this.emit("EmulatorSwapped", { from_device_id: a.id, to_device_id: b.id, emulator: em }, "server"); this.log("swapped", b, em);
    return "confirmed";
  }
  /** One more staff device for the locked monthly price, on paid tiers only. */
  /** A day pass: one more staff device today, on any tier (the price is the register's, from services/billing.py). */
  buyPass(family: string): boolean {
    if (typeof this.limit(family) !== "number") return false;
    this.passes[family] = (this.passes[family] ?? 0) + 1; return true;
  }
  /** The next tier, when it costs less than this one with the extra devices bought (said, never applied by itself). */
  cheaper(family: string): string | null { return cheaperTier(this.reg, family, this.tier, this.extra[family] ?? 0); }
  buyExtra(family: string): boolean {
    if (this.tier === "free" || this.reg.extra_cents[family] === undefined || !this.usage().some((u) => u.family === family && typeof u.limit === "number")) return false;
    this.extra[family] = (this.extra[family] ?? 0) + 1; return true;
  }
  setTone(devId: string, key: "tones" | "vibration" | "user_may_change" | "pin_same_tone" | "volume", value: boolean | string): void {
    const s = this.tones[devId]; if (!s) return;
    if (key === "volume") { if (["low", "medium", "high"].includes(String(value))) s.volume = String(value); } else s[key] = Boolean(value);
    this.emit("EmulatorSettingsChanged", { device_id: devId, tones: s.tones, vibration: s.vibration, volume: s.volume, pin_same_tone: s.pin_same_tone, by: "manager" }, "server");
  }
  /** See the screen to help: only with the user's consent, never during a payment, cash count, signature or PIN. */
  view(devId: string, busy: boolean): St {
    const d = this.dev(devId); if (!d) return "failed";
    const was = this.viewing[devId];
    if (busy) { this.viewing[devId] = "failed"; this.emit("ScreenViewChanged", { device_id: devId, change: "refused", viewer: "manager" }, "server"); return "failed"; }
    if (!was || was === "failed") { this.viewing[devId] = "sent"; return "sent"; }                                       // asked the user
    if (was === "sent") { this.viewing[devId] = "confirmed"; this.emit("ScreenViewChanged", { device_id: devId, change: "started", viewer: "manager", consent_id: newId() }, "server"); return "confirmed"; }
    delete this.viewing[devId]; this.emit("ScreenViewChanged", { device_id: devId, change: "ended", viewer: "manager" }, "server"); return "confirmed";
  }
  /** Why a device needs a look, in plain words (LynkAssist's "Why?"). */
  reasons(d: PanelDevice): string[] {
    const r: string[] = [];
    if (d.printer === "out_of_paper" || d.printer === "paper_low") r.push("printer");
    if (d.battery !== null && d.battery <= LOW_BATTERY) r.push("battery");
    if (d.unsent >= MANY_UNSENT) r.push("unsent");
    if (d.morning === "failed") r.push("morning_check");
    if (!d.online) r.push("offline");
    if (d.reapprove) r.push("reapproval");
    if (d.lost) r.push("lost");
    return r;
  }
  /** The state a person sees for a device's emulator (the five states only). */
  emState(e: PanelEm): St { return e.state === "connected" ? "confirmed" : e.state === "disconnected" ? "failed" : "sent"; }

  act(a: string, ctx: { online: boolean; busy: boolean; redraw: () => void }): boolean {
    if (!a.startsWith("emp:")) return false;
    const [, k = "", v = "", w = ""] = a.split(":");
    switch (k) {
      case "pick": this.pick = this.choices().includes(v) ? v : ""; break;
      case "add": this.offer(ctx.online, ctx.redraw); break;
      case "guided": this.guided(v, ctx.online, ctx.redraw); break;
      case "open": this.open = this.open === v ? "" : v; break;
      case "connect": this.connect(v, w); break;
      case "practice": this.connect(v, w, true); break;
      case "disconnect": this.disconnect(v, w); break;
      case "back": this.backOnline(v); break;
      case "lost": this.lost(v); break;
      case "found": this.lost(v, true); break;
      case "approve": this.approve(v); break;
      case "notseen": this.notSeen(v, this.reg.reapprove_days); break;
      case "swap": this.swap(v, w, this.dev(v)?.ems[0]?.id ?? ""); break;
      case "extra": this.buyExtra(v); break;
      case "pass": this.buyPass(v); break;
      case "tone": { const [key, val] = w.split("="); if (key) this.setTone(v, key as "tones", val === "on" ? true : val === "off" ? false : val ?? ""); break; }
      case "view": this.view(v, ctx.busy); break;
      case "why": this.why[v] = this.why[v] ? [] : this.reasons(this.dev(v)!); if (!this.why[v]?.length) delete this.why[v]; break;
      case "service": this.service = v || null; this.pick = ""; break;
      case "side": this.side = v === "external" ? "external" : "internal"; break;
      default: return false;
    }
    return true;
  }
}

// ---- drawing -------------------------------------------------------------------------------------------------------------
const empPressed = (on: boolean): string => `aria-pressed="${on}"`;
const empChip = (s: St, t: T, icon: Icon): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const emName = (id: string, t: T): string => t(`emk_em_${id.replace(".", "_")}`);

/** The address this panel lives at (the overall panel, or a service's path plus /emulators; Storefront side by the /external rule). */
export function panelPath(service: string | null, side: "internal" | "external", servicePath: (family: string) => string): string {
  const base = service ? `${servicePath(service)}/emulators` : "/business/emulators";
  return side === "external" ? `/external${base}` : base;
}

export function usageCard(P: EmulatorPanelDesk, L: PanelLook): string {
  const t = L.t, u = P.usage();
  const row = (x: { family: string; used: number; limit: Limit; extra: number }): string => {
    const lim = x.limit === "own_units" ? t("emp_own_units") : x.limit === null ? t("emp_unlimited") : t("emp_of", { used: x.used, limit: x.limit + x.extra });
    const full = typeof x.limit === "number" && x.used >= x.limit + x.extra;
    return `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(L.familyName(x.family))}</span><span class="sub">${esc(x.limit === "own_units" ? lim : `${t("emp_in_use", { n: x.used })} · ${lim}`)}</span></span>
      ${full && L.mayManage ? `<span class="emp-buy">${L.tier !== "free" && P.reg.extra_cents[x.family] !== undefined ? `<button type="button" class="ghost small" data-act="emp:extra:${x.family}">${esc(t("emp_buy_extra", { price: L.money(P.reg.extra_cents[x.family]!) }))}</button>` : ""}<button type="button" class="ghost small" data-act="emp:pass:${x.family}">${esc(t("emp_day_pass", { price: L.money(P.reg.day_pass_cents) }))}</button></span>` : full ? `<span class="tag">${esc(t("emp_full"))}</span>` : ""}
      ${P.cheaper(x.family) ? `<p class="sub emp-hint" role="status">${esc(t("emp_cheaper", { tier: t(`tier_${P.cheaper(x.family)}`) }))}</p>` : ""}</div></li>`;
  };
  return `<div class="card emp-usage" data-item="emp_usage"><h2>${esc(t("emp_plan_title"))}</h2><ul class="list">${u.map(row).join("")}</ul>
    <p class="sub">${esc(t("emp_free_screens", { n: P.freeScreens() }))}</p><p class="sub">${esc(t("emp_count_rule"))}</p>${L.tier === "free" ? `<p class="sub">${esc(t("emp_extra_plus_pro"))}</p>` : ""}<p class="sub">${esc(t("emp_day_pass_note", { days: P.reg.day_pass_max_days }))}</p></div>`;
}

export function addCard(P: EmulatorPanelDesk, L: PanelLook): string {
  const t = L.t, last = P.offers[0];
  const own = (svc: string): number => P.reg.emulators.filter((e) => e.service === svc && !e.planned && !e.shared_with).length;
  const services = [...new Set(P.choices().map((id) => P.find(id)?.service ?? ""))].filter((svc) => svc && own(svc) > 1);    // "Set up my queue": services with several screens
  return `<div class="card emp-add" data-item="emp_add" role="group" aria-labelledby="empA"><h2 id="empA">${esc(t("emp_add_title"))}</h2><p class="sub">${esc(t("emp_add_pick"))}</p>
    <div class="emk-choices">${P.choices().map((id) => `<button type="button" class="emk-choice" data-act="emp:pick:${id}" ${empPressed(P.pick === id)} ${L.mayManage ? "" : "disabled"}><strong>${esc(emName(id, L.t))}</strong><span>${esc(L.familyName(P.find(id)?.shared_with ?? P.find(id)?.service ?? ""))}</span></button>`).join("")}</div>
    <button type="button" class="primary inline" data-act="emp:add" ${L.mayManage && P.pick ? "" : "disabled"}>${esc(t("emp_add_device"))}</button>
    ${last ? `<div class="emp-offer" role="status"><span class="qr" aria-hidden="true">${L.icon("ui-qr", "qrbig")}</span><div><p>${esc(t("emp_code"))} <strong dir="ltr">${esc(last.code)}</strong></p>
      <p class="sub" dir="ltr">${esc(last.link)}</p><p class="sub">${esc(t("emp_code_once", { m: P.reg.code_minutes }))}</p><p>${empChip(last.state, t, L.icon)} ${last.reason ? esc(t(`emp_reason_${last.reason}`)) : ""}</p></div></div>` : ""}
    ${L.mayManage ? `<div class="emp-guided">${services.map((s) => `<button type="button" class="ghost small" data-act="emp:guided:${s}">${esc(t("emp_guided", { service: L.familyName(s) }))}</button>`).join("")}</div>` : `<p class="sub">${esc(t("emp_owner_manager_only"))}</p>`}
    <p class="sub">${esc(t("emp_other_ways"))}</p></div>`;
}

export function liveCard(P: EmulatorPanelDesk, L: PanelLook): string {
  const t = L.t, q = P.filter.trim().toLowerCase();
  const list = P.devices.filter((d) => (!P.service || d.ems.some((e) => P.find(e.id)?.service === P.service || P.find(e.id)?.shared_with === P.service) || !d.ems.length) && (!q || d.name.toLowerCase().includes(q)));
  const health = (d: PanelDevice): string => [t(d.online ? "emp_online" : "emp_offline"), d.battery !== null ? t("emp_battery", { n: d.battery }) : "", d.unsent ? t("emp_unsent", { n: d.unsent }) : "",
    d.printer ? t(`emp_printer_${d.printer}`) : ""].filter(Boolean).join(" · ");
  const row = (d: PanelDevice): string => {
    const open = P.open === d.id, warn = P.reasons(d).length > 0;
    const ems = d.ems.map((e) => `<li class="emp-em"><span class="nm">${esc(emName(e.id, t))}</span>${e.practice ? ` <span class="tag">${esc(t("emk_practice"))}</span>` : ""}${e.user ? ` <span class="sub">${esc(t("emp_user_since", { user: e.user, at: L.clock(e.since) }))}</span>` : ""}
      ${empChip(P.emState(e), t, L.icon)} <span class="sub">${esc(t(`emp_state_${e.state}`, { n: e.unsent }))}</span>
      ${open && L.mayManage ? (e.state === "connected" || e.state === "disconnect_sent" ? `<button type="button" class="ghost small" data-act="emp:disconnect:${d.id}:${e.id}" ${e.state === "connected" ? "" : "disabled"}>${esc(t("emp_disconnect"))}</button>`
        : `<button type="button" class="ghost small" data-act="emp:connect:${d.id}:${e.id}">${esc(t("emp_connect"))}</button>`) : ""}</li>`).join("");
    const others = P.devices.filter((x) => x.id !== d.id && !x.lost);
    const actions = open && L.mayManage ? `<div class="emp-actions">
      ${d.lost ? `<button type="button" class="ghost small" data-act="emp:found:${d.id}">${esc(t("emp_found"))}</button>` : `<button type="button" class="ghost small" data-act="emp:lost:${d.id}">${esc(t("emp_mark_lost"))}</button>`}
      ${d.reapprove ? `<button type="button" class="primary small" data-act="emp:approve:${d.id}">${esc(t("emp_approve_again"))}</button>` : ""}
      ${d.ems[0] && others[0] ? `<button type="button" class="ghost small" data-act="emp:swap:${d.id}:${others[0].id}">${esc(t("emp_swap_to", { name: others[0].name }))}</button>` : ""}
      ${P.pick && !d.ems.some((e) => e.id === P.pick) ? `<button type="button" class="ghost small" data-act="emp:connect:${d.id}:${P.pick}">${esc(t("emp_connect_here", { emulator: emName(P.pick, t) }))}</button>
        <button type="button" class="ghost small" data-act="emp:practice:${d.id}:${P.pick}">${esc(t("emp_practice_here"))}</button>` : ""}
      ${d.ems.length ? `<button type="button" class="ghost small" data-act="emp:view:${d.id}">${esc(t(P.viewing[d.id] === "confirmed" ? "emp_view_end" : "emp_view"))}</button>${P.viewing[d.id] ? ` ${empChip(P.viewing[d.id]!, t, L.icon)} <span class="sub">${esc(t(`emp_view_${P.viewing[d.id]}`))}</span>` : ""}` : ""}
      ${!d.online ? `<button type="button" class="ghost small" data-act="emp:back:${d.id}">${esc(t("emp_sandbox_back_online"))}</button>` : ""}
      ${!d.reapprove ? `<button type="button" class="ghost small" data-act="emp:notseen:${d.id}">${esc(t("emp_sandbox_not_seen"))}</button>` : ""}
      ${tonesHtml(P, d, L)}</div>` : "";
    return `<li class="emp-dev${warn ? " warn" : ""}"><button type="button" class="rowbtn" data-act="emp:open:${d.id}" aria-expanded="${open}"><span class="main"><span class="nm">${esc(d.name)} · ${esc(d.lynk)}</span>
      <span class="sub">${esc(health(d))}${d.lost ? ` · ${esc(t("emp_lost"))}` : ""}${d.reapprove ? ` · ${esc(t("emp_needs_approval"))}` : ""}</span></span>${L.icon(open ? "ui-chevron-down" : "ui-chevron-right", "ic fwd")}</button>
      ${warn ? `<button type="button" class="ghost small" data-act="emp:why:${d.id}">${esc(t("emp_why"))}</button>` : ""}${P.why[d.id] ? `<ul class="emp-why" role="status">${P.why[d.id]!.map((w) => `<li>${esc(t(`emp_why_${w}`))}</li>`).join("")}</ul>` : ""}
      <ul class="emp-ems">${ems || `<li class="sub">${esc(t("emp_no_emulators"))}</li>`}</ul>${actions}</li>`;
  };
  return `<div class="card emp-live" data-item="emp_live"><h2>${esc(t("emp_live_title"))} <span class="tag">${esc(t("emp_sandbox"))}</span></h2>
    <label class="field"><span>${esc(t("emp_search"))}</span><input type="search" data-in="emp_filter" value="${esc(P.filter)}" autocomplete="off"></label>
    <ul class="list emp-list">${list.map(row).join("") || `<li class="sub">${esc(t("emp_none_found"))}</li>`}</ul><p class="sub">${esc(t("emp_branch_only"))}</p></div>`;
}

function tonesHtml(P: EmulatorPanelDesk, d: PanelDevice, L: PanelLook): string {
  const t = L.t, s = P.tones[d.id]; if (!s) return "";
  const tog = (k: "tones" | "vibration" | "user_may_change" | "pin_same_tone", label: string): string =>
    `<button type="button" class="emk-toggle" data-act="emp:tone:${d.id}:${k}=${s[k] ? "off" : "on"}" ${empPressed(s[k])}><span>${esc(label)}</span><strong>${esc(t(s[k] ? "emk_on" : "emk_off"))}</strong></button>`;
  return `<div class="emp-tones" role="group" aria-label="${esc(t("emk_key_tones"))}">${tog("tones", t("emk_key_tones"))}${tog("vibration", t("emk_vibration"))}
    <div class="emk-row"><span>${esc(t("emk_volume"))}</span>${["low", "medium", "high"].map((v) => `<button type="button" class="ghost small" data-act="emp:tone:${d.id}:volume=${v}" ${empPressed(s.volume === v)}>${esc(t(`emk_vol_${v}`))}</button>`).join("")}</div>
    ${tog("user_may_change", t("emp_user_may_change"))}${tog("pin_same_tone", t("emp_pin_same"))}</div>`;
}

export function historyCard(P: EmulatorPanelDesk, L: PanelLook): string {
  const t = L.t;
  return `<div class="card emp-history" data-item="emp_history"><h2>${esc(t("emp_history"))}</h2><ul class="list">${P.history.slice(0, 8).map((h) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(t(`emp_did_${h.what}`))} · ${esc(h.device)}</span>
    <span class="sub">${esc(L.clock(h.at))}${h.emulator ? ` · ${esc(emName(h.emulator, t))}` : ""}</span></span></div></li>`).join("") || `<li class="sub">${esc(t("emp_history_none"))}</li>`}</ul><p class="sub">${esc(t("emp_history_note"))}</p></div>`;
}

/** The whole panel: the service filter (overall panel only), the plan, Add a device, the live list and the history. */
export function panelView(P: EmulatorPanelDesk, L: PanelLook, overall: boolean, path: string): string {
  const t = L.t;
  const fams = [...new Set(P.reg.emulators.filter((e) => !e.planned).map((e) => e.service))];
  const filter = overall || P.service ? `<div class="emp-filter" role="group" aria-label="${esc(t("emp_services"))}"><button type="button" class="ghost small" data-act="${L.go ? L.go(null) : "emp:service:"}" ${empPressed(!P.service)}>${esc(t("emp_all_services"))}</button>${fams.map((f) =>
    `<button type="button" class="ghost small" data-act="${L.go ? L.go(f) : `emp:service:${f}`}" ${empPressed(P.service === f)}>${esc(L.familyName(f))}</button>`).join("")}</div>` : "";
  return `<p class="sub emp-path" dir="ltr">app.lynkomni.com${esc(path)}</p><p class="sub">${esc(t("emp_intro"))}</p>${filter}${usageCard(P, L)}${addCard(P, L)}${liveCard(P, L)}${historyCard(P, L)}`;
}

export const PANEL_DAY_MS = DAY_MS;
