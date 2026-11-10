/** The MASTER UPDATE section 3 parts on every Business app device (terminal, tablet, kitchen screen, scanner, phone):
 *  staff sign-in with each person's own PIN (also offline), the duress PIN's quiet limited view, staff PINs reset on the spot,
 *  offline limits by role with a manager's PIN on the same device, LynkAssist's offline behaviour, banners on device screens and
 *  the device's own bell, breadcrumbs, and the card screens ("Get a card" and the card group words).
 *  The rules are identity/device_access.py's, services/assist_business.py's and services/card_groups.py's; the numbers come from
 *  parts.generated.ts and are checked by contract/vectors/parts.v1.json. The PINs here are a sample: a real device keeps only a
 *  slow salted hash in its encrypted database, never the PIN. */
import { ASSIST, CAN_MANAGE, CARD_FORM, CARD_GROUP_NAMES, CARD_TIER_WORD, CARD_WORD, DURESS_VIEW, MESSAGES, OFFLINE_LIMITS } from "./parts.generated.js";
import { afterWrong, pinPad, pinProblem } from "./signin.js";
import { banner, priorityOf } from "./notify.js";
import type { Line } from "./notify.js";
import { buildPack, decide } from "./assist.js";
import type { Ask, Decision, Entry as KEntry } from "./assist.js";
import { breadcrumbBar, trail } from "./breadcrumbs.js";
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

/** Breadcrumbs on a device screen, from the address map; compact on small screens. */
export function deviceCrumbs(path: string, label: (p: string) => string, compact: boolean, t: T): string {
  let steps: string[] = [];
  try { steps = trail("app.lynkomni.com", path); } catch { return ""; }
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
