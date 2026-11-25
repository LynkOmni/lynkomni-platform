/** The MASTER UPDATE section 3 parts on every Business app device (terminal, tablet, kitchen screen, scanner, phone):
 *  staff sign-in with each person's own PIN (also offline), the duress PIN's quiet limited view, staff PINs reset on the spot,
 *  offline limits by role with a manager's PIN on the same device, LynkAssist's offline behaviour, banners on device screens and
 *  the device's own bell, breadcrumbs, and the card screens ("Get a card" and the card group words).
 *  The rules are identity/device_access.py's, services/assist_business.py's and services/card_groups.py's; the numbers come from
 *  parts.generated.ts and are checked by contract/vectors/parts.v1.json. The PINs here are a sample: a real device keeps only a
 *  slow salted hash in its encrypted database, never the PIN. */
import { ASSIST, CAN_MANAGE, CARD_FORM, CARD_GROUP_NAMES, CARD_TIER_WORD, CARD_WORD, DURESS_VIEW, MESSAGES, OFFLINE_LIMITS } from "./parts.generated.js";
import { afterWrong, pinPad, pinProblem } from "./signin.js";
import { noticeHtml } from "./errorbox.js";
import { banner, priorityOf } from "./notify.js";
import type { Line } from "./notify.js";
import { buildPack, decide } from "./assist.js";
import type { Ask, Decision, Entry as KEntry } from "./assist.js";
import { breadcrumbBar, trail, wireCrumbs } from "./breadcrumbs.js";
import { esc } from "./shell.js";
import type { Icon, T } from "./shell.js";

export type Act = "void" | "refund" | "discount";
const LIMIT_KEY: Record<Act, "void_minor" | "refund_minor" | "discount_bps"> = { void: "void_minor", refund: "refund_minor", discount: "discount_bps" };

/** Whether this act, this big, needs a manager's PIN on the same device (identity/device_access.py needs_manager). */
export function needsManager(role: string, act: Act, amount: number, limits = OFFLINE_LIMITS): boolean {
  const lim = limits[role]?.[LIMIT_KEY[act]];
  return lim !== null && lim !== undefined && amount > lim;
}
export const mayManage = (byRole: string, targetRole: string): boolean => (CAN_MANAGE[byRole] ?? []).includes(targetRole);
export const DURESS_SCREENS: readonly string[] = DURESS_VIEW;

export interface Staff { person: string; name: string; role: string; pin: string; duress?: string }
export type SignIn = { ok: true; view: "full" | "limited"; role: string } | { ok: false; reason: "wrong" | "wait" | "hard_locked" | "unknown" | "locked_by_owner"; left?: number; seconds?: number };

/** One device's staff and their PIN locks: each person their own PIN, waits after wrong tries, a hard lock that never wipes,
 *  and a duress PIN that opens the limited view (which looks like a quiet till) while the alert leaves silently. */
export class StaffLock {
  wrong = new Map<string, number>();
  waitUntil = new Map<string, number>();
  hard = new Set<string>();
  remoteLocked = false;
  alerts: { person: string; at: number; sentBy: string | null }[] = [];
  constructor(public staff: Staff[]) {}
  find(person: string): Staff | undefined { return this.staff.find((s) => s.person === person); }
  signIn(person: string, pin: string, now: number): SignIn {
    if (this.remoteLocked) return { ok: false, reason: "locked_by_owner" };
    const s = this.find(person);
    if (!s) return { ok: false, reason: "unknown" };
    if (this.hard.has(person)) return { ok: false, reason: "hard_locked" };
    if (s.duress && pin === s.duress) { this.alerts.push({ person, at: now, sentBy: null }); return { ok: true, view: "limited", role: s.role }; }
    const until = this.waitUntil.get(person) ?? 0;
    if (now < until) return { ok: false, reason: "wait", seconds: Math.ceil((until - now) / 1000) };
    if (pin === s.pin) { this.wrong.set(person, 0); return { ok: true, view: "full", role: s.role }; }
    const n = (this.wrong.get(person) ?? 0) + 1;
    this.wrong.set(person, n);
    const w = afterWrong(n);
    if (w === "locked") { this.hard.add(person); return { ok: false, reason: "hard_locked" }; }
    if (w) this.waitUntil.set(person, now + w * 1000);
    return { ok: false, reason: "wrong", left: 10 - n };
  }
  /** The owner or a manager resets a staff member's PIN on the spot, also offline; never the owner's own PIN. */
  reset(by: string, byPin: string, person: string, newPin: string): "ok" | "not_allowed" | "wrong_pin" | "bad_pin" {
    const b = this.find(by), s = this.find(person);
    if (!b || !s || s.role === "owner" || !mayManage(b.role, s.role)) return "not_allowed";
    if (b.pin !== byPin) return "wrong_pin";
    if (pinProblem(newPin)) return "bad_pin";
    s.pin = newPin; delete s.duress; this.wrong.set(person, 0); this.waitUntil.delete(person); this.hard.delete(person);
    return "ok";
  }
  /** A manager (or the owner), not the same person, approves an act above the limit with their own PIN on this device. */
  approve(person: string, manager: string, pin: string): boolean {
    const m = this.find(manager);
    return !!m && manager !== person && (m.role === "manager" || m.role === "owner") && m.pin === pin;
  }
  /** Waiting alerts leave by the first path that appears; nothing calls the police by itself. */
  pathsOut(available: string[]): number {
    const path = ["text", "nearby_device", "internet"].find((p) => available.includes(p));
    if (!path) return 0;
    let n = 0;
    for (const a of this.alerts) if (!a.sentBy) { a.sentBy = path; n++; }
    return n;
  }
}

/** The staff lock of every shared staff device (owner rule 2026-11-24: a staff PIN with a duress PIN wherever staff share a device;
 *  catalog/emulators.v1.json user "needed" or "optional", tests/test_staff_lock.py). One part draws the lock screen (who is using
 *  this device, then their own PIN on the shared pad with pictures and a tone per key), shows who is signed in with Lock, locks after
 *  two minutes without use, and on the duress PIN opens the device's quiet limited view while the alert leaves silently by the first
 *  path out. Wrong PINs make the person wait, then lock that PIN; nothing is ever deleted. "optional": the screen works without
 *  anyone signed in (the kitchen screen) and a person may sign in. */
export interface GateHooks { t: T; icon: Icon; device: string; online: () => boolean; redraw: () => void;
  emit: (type: string, payload: Record<string, unknown>, origin?: "device" | "server") => void; raise?: (kind: string, title: string) => void }
export class StaffGate {
  who: string; picking = false; pin = ""; signed = false; limited = false; idle = false; last = Date.now(); pictures = false; sound = true; open: boolean;
  constructor(public lock: StaffLock, private h: GateHooks, public optional = false, public idleMs = 120_000) {
    this.who = lock.staff[0]?.person ?? ""; this.open = optional;
  }
  /** The person signed in, if any. */
  me(): Staff | undefined { return this.signed ? this.lock.find(this.who) : undefined; }
  role(): string { return this.me()?.role ?? ""; }
  private waitLeft(): number { return Math.max(0, Math.ceil(((this.lock.waitUntil.get(this.who) ?? 0) - Date.now()) / 1000)); }
  /** The lock screen (when open is false the screen shows only this). */
  view(cls = "dk-gate"): string {
    const { t, icon } = this.h;
    if (this.picking) return `<div class="${cls}">${staffPicker(this.lock.staff, t, icon)}</div>`;
    const s = this.lock.find(this.who);
    const pad = pinPad({ entered: this.pin.length, length: Math.max(4, this.pin.length), wrong: this.lock.wrong.get(this.who) ?? 0, waitLeft: this.waitLeft(), pictures: this.pictures, sound: this.sound, title: t("dk_pin_for", { name: s?.name ?? "" }) }, t, icon);
    const sample = this.lock.staff.map((x) => `${t(`role_${x.role}`)} ${x.pin}`).join(", ");
    return `<div class="${cls}"><p class="dk-who">${icon("ui-user")}<span>${esc(s?.name ?? "")} · ${esc(t(`role_${s?.role ?? "cashier"}`))}</span><button type="button" class="dk-link" data-act="staff:change">${esc(t("dk_change"))}</button>${this.optional ? `<button type="button" class="dk-link" data-act="gate:cancel">${esc(t("back"))}</button>` : ""}</p>
      ${this.idle ? noticeHtml(t, { level: "info", cls: "dk-note", text: t("locked_idle") }) : ""}${this.lock.hard.has(this.who) ? noticeHtml(t, { level: "error", cls: "dk-note", text: t("dk_hard_locked"), how: t("fd_ask_manager") }) : ""}
      ${pad}<p class="dk-note">${esc(t("dk_own_pin"))}</p><p class="dk-note">${esc(t("dk_pin_sample", { list: sample }))}</p>
</div>`;
  }
  /** Who is serving, with Lock; on an optional screen with nobody signed in, Staff sign-in. */
  whoRow(): string {
    const { t, icon } = this.h, me = this.me();
    if (!me) return this.optional ? `<div class="dk-whorow"><button type="button" class="dk-link" data-act="gate:signin">${icon("ui-user")}<span>${esc(t("dk_sign_in"))}</span></button></div>` : "";
    return `<div class="dk-whorow"><span>${icon("ui-user")}<span>${esc(me.name)} · ${esc(t(`role_${me.role}`))}</span></span><button type="button" class="dk-link" data-act="gate:lock">${icon("ui-lock")}<span>${esc(t("dk_lock"))}</span></button></div>`;
  }
  /** Lock now (Lock, or two minutes without use). On an optional screen this signs the person out and the screen stays. */
  lockNow(idle = false): void {
    this.signed = false; this.limited = false; this.pin = ""; this.picking = false; this.idle = idle && !this.optional; this.open = this.optional;
  }
  /** Every act goes through here first: true when the gate handled it (while locked, nothing else runs). */
  act(a: string): boolean {
    this.last = Date.now();
    const [k = "", x = "", y = ""] = a.split(":");
    if (k === "gate") {
      if (x === "lock") this.lockNow(false);
      else if (x === "signin") { this.open = false; this.idle = false; }
      else if (x === "cancel" && this.optional) { this.open = true; this.pin = ""; this.picking = false; }
      this.h.redraw(); return true;
    }
    if (this.open) return false;
    if (k === "staff" && x === "change") { this.picking = true; this.pin = ""; this.h.redraw(); return true; }
    if (k === "staff" && x === "pick") { this.who = y; this.picking = false; this.pin = ""; this.h.redraw(); return true; }
    if (k !== "pin") return true;
    if (x === "pictures") this.pictures = !this.pictures;
    else if (x === "sound") this.sound = !this.sound;
    else if (x === "clear") this.pin = this.pin.slice(0, -1);
    else if (/^\d$/.test(x)) { if (this.pin.length < 8) this.pin += x; }
    else if (x === "ok" && this.pin) this.tryPin();
    this.h.redraw(); return true;
  }
  private tryPin(): void {
    const pin = this.pin; this.pin = "";
    const r = this.lock.signIn(this.who, pin, Date.now());
    if (r.ok) {
      this.signed = true; this.open = true; this.idle = false; this.limited = r.view === "limited"; this.last = Date.now();
      const n = this.lock.pathsOut(this.h.online() ? ["internet"] : []);
      for (let i = 0; i < n; i++) this.h.emit("DuressSignalled", { device_id: this.h.device, person: this.who, path: "internet", at: Date.now() }, "server");
    } else if (r.reason === "hard_locked") { this.h.emit("DeviceHardLocked", { device: this.h.device }); this.h.raise?.("device_hard_locked", this.h.t("dk_hard_locked")); }
  }
  /** Typed digits, Backspace and Enter on the lock screen. */
  key(e: KeyboardEvent): boolean {
    this.last = Date.now();
    if (this.open || this.picking || e.ctrlKey || e.metaKey || e.altKey) return false;
    const k = /^\d$/.test(e.key) ? e.key : e.key === "Backspace" ? "clear" : e.key === "Enter" && this.pin ? "ok" : "";
    if (!k) return false;
    e.preventDefault(); this.act(`pin:${k}`); return true;
  }
  /** Call on every timer tick: true when the screen should redraw (it locked by itself, or a wait is counting down). */
  tick(busy = false): boolean {
    if (this.signed && !busy && Date.now() - this.last > this.idleMs) { this.lockNow(true); return true; }
    return !this.open && this.waitLeft() > 0;
  }
  /** The sample cashier (first person) signed in at once: for the panel's state buttons. */
  signInFirst(): void { this.who = this.lock.staff[0]?.person ?? ""; this.signed = true; this.open = true; this.limited = false; this.idle = false; this.last = Date.now(); }
}

/** The staff picker and PIN pad of a device's lock screen. */
export function staffPicker(staff: Staff[], t: T, icon: Icon): string {
  return `<div class="dk-staff" role="group" aria-label="${esc(t("dk_who"))}"><h2>${esc(t("dk_who"))}</h2><ul>${staff.map((s) => `<li><button type="button" data-act="staff:pick:${esc(s.person)}">${icon("ui-user")}<span>${esc(s.name)}</span><span class="dk-role">${esc(t(`role_${s.role}`))}</span></button></li>`).join("")}</ul><p class="dk-note">${esc(t("dk_own_pin"))}</p></div>`;
}
export function staffPin(name: string, entered: number, wrong: number, waitLeft: number, t: T, icon: Icon): string {
  return pinPad({ entered, length: Math.max(4, entered), wrong, waitLeft, pictures: false, sound: true, title: t("dk_pin_for", { name }) }, t, icon);
}

/** LynkAssist without a network (offline layer 2): what the register says each action does offline. */
export type Offline = "device" | "queue" | "cloud_check" | "never";
export const offlineOf = (actionId: string): Offline => ASSIST.actions[actionId]?.offline ?? "never";
export type OfflineDecision = Omit<Decision, "needs"> & { offline?: Offline; needs: Decision["needs"] | "prepare_for_later" | "wait_for_network" };
/** The same answer as services/assist_business.py decide(): online it is the register's; offline device fixes run, cloud
 *  actions queue sealed, identity checks wait and partner or person work is prepared to send later. */
export function decideOffline(actionId: string, ask: Ask, online: boolean): OfflineDecision {
  const d = decide(actionId, ask);
  if (online || d.needs === "refused" || !ASSIST.actions[actionId]) return d;
  const mode = offlineOf(actionId);
  if (mode === "never" || d.needs === "hand_over") return { ...d, run: false, needs: "prepare_for_later", why: "as_why_later" };
  if (mode === "cloud_check") return { ...d, run: false, needs: "wait_for_network", why: "as_why_network" };
  return { ...d, offline: mode };
}
/** Never shown inside a payment, a cash count, a void or a signature. */
export const NEVER_INSIDE = ["payment", "cash_count", "void", "signature"] as const;
export const assistAllowedOn = (screen: string): boolean => !(NEVER_INSIDE as readonly string[]).includes(screen);

/** Banners on a device screen: high and critical lines not yet acknowledged, newest first, at most two. */
export function deviceBanners(lines: Line[], t: T, icon: Icon): string {
  const shown = lines.filter((l) => !l.acknowledged && !l.read && (priorityOf(l.kind) === "critical" || priorityOf(l.kind) === "high")).sort((a, b) => b.at - a.at).slice(0, 2);
  return shown.length ? `<div class="dk-banners">${shown.map((l) => banner(l, t, icon)).join("")}</div>` : "";
}
/** The device's own bell while offline: one line per kind and record, a count when it repeats. */
export function raiseLocal(lines: Line[], kind: string, title: string, at: number, record?: string): Line[] {
  if (!MESSAGES.kinds[kind]) throw new Error(`${kind} is not in the message register`);
  const same = lines.find((l) => l.kind === kind && l.record === record && !l.read);
  if (same) { same.count = (same.count ?? 1) + 1; same.at = at; same.seen = false; return lines; }
  return [{ nid: `local-${lines.length + 1}-${kind}`, kind, title, at, record, count: 1, read: false, seen: false }, ...lines];
}

/** The up key on a device keyboard follows the trail's parent step (wired once per page). */
let crumbsWired = false;
export function wireDeviceCrumbs(): void { if (crumbsWired || typeof document === "undefined") return; crumbsWired = true; wireCrumbs(document); }
/** Breadcrumbs on a device screen, from the address map; compact on small screens. No sideways list inside a device screen. */
export function deviceCrumbs(path: string, label: (p: string) => string, compact: boolean, t: T): string {
  let steps: string[] = [];
  try { steps = trail("app.lynkomni.com", path); } catch { return ""; }
  const norm = (p: string): string => p.replace(/^[a-z.]+\.lynkomni\.com/, "") || "/";   // "/" and "app.lynkomni.com/" are the same place: Home has no trail
  steps = steps.filter((p, i) => steps.findIndex((q) => norm(q) === norm(p)) === i);
  wireDeviceCrumbs();
  return steps.length > 1 ? breadcrumbBar(steps.map((p) => ({ path: p, label: label(p) })), compact, t) : "";
}

/** The card group words on card screens: "LynkDyna Pro", and PREPAID, DEBIT or CREDIT as printed on the card. */
export const cardName = (group: string, tier: string): string => `${CARD_GROUP_NAMES[group] ?? group} ${CARD_TIER_WORD[tier] ?? tier}`;
export const cardWord = (group: string): string => CARD_WORD[group] ?? group.toUpperCase();
export const cardFormFields = (group: string): string[] => CARD_FORM[group] ?? [];

/** The offline knowledge pack (LynkAssist layer 1) in the device's language, rebuilt only when the language changes. */
let kcache: { lang: string; entries: KEntry[] } | null = null;
export function knowledgeFor(i18n: Record<string, { texts: Record<string, string> }>, lang: string): KEntry[] {
  const l = i18n[lang] ? lang : "en";
  if (!kcache || kcache.lang !== l) kcache = { lang: l, entries: buildPack({ ...(i18n["en"]?.texts ?? {}), ...(i18n[l]?.texts ?? {}) }) };
  return kcache.entries;
}
