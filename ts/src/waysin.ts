/** Sign-up, sign-in, the ways to prove it's you, the account protections, the Can't sign in? hub and every reset (section 4C
 *  points 3 and 5): the rules of core/ways_in.py, checked against contract/vectors/ways-in.v1.json. The register comes from
 *  ts/src/waysin.generated.ts (tools/waysin_vectors.py). LynkOmni has no passwords and uses no outside company here. */
import { WAYS_IN } from "./waysin.generated.js";

const WI_HOUR = 3600, WI_DAY = 86400;
interface Way { id: string; kind: string; strength: number }
const WI_WAYS = WAYS_IN.ways as unknown as readonly Way[];
const byStrength = (a: Way, b: Way): number => b.strength - a.strength;
const inList = (list: readonly string[], x: string): boolean => list.includes(x);

// ---- sign-up -------------------------------------------------------------------------------------------------------------
/** The next sign-up step after the steps already done, in the fixed order; null when every step is done. */
export function signUpNext(done: readonly string[]): string | null {
  for (const s of WAYS_IN.sign_up.steps) if (!done.includes(s)) return s;
  return null;
}
/** Sign-up is online only and limited per device and per network each hour; no picture puzzles. [ok, why] */
export function mayStartSignUp(online: boolean, deviceHour: number, networkHour: number): [boolean, string | null] {
  const a = WAYS_IN.sign_up.abuse;
  if (!online) return [false, WAYS_IN.sign_up.offline_says];
  if (deviceHour >= a.per_device_hour) return [false, "device_limit"];
  if (networkHour >= a.per_network_hour) return [false, "network_limit"];
  return [true, null];
}
/** null when the legal name (as on the ID document) is acceptable, else why. */
export function legalNameProblem(name: string): string | null {
  const n = (name ?? "").split(/\s+/u).filter(Boolean).join(" ");
  const l = WAYS_IN.sign_up.legal_name;
  if ([...n].length < l.min) return "too_short";
  if ([...n].length > l.max) return "too_long";
  if (/\p{Nd}/u.test(n)) return "no_digits";
  return null;
}
/** An account opened on a basic phone is limited until an email is added. */
export const basicPhoneAllows = (act: string, hasEmail: boolean): boolean => hasEmail || !inList(WAYS_IN.basic.limited, act);

// ---- sign-in -------------------------------------------------------------------------------------------------------------
/** username, email or phone, read from what the person typed (one box takes all three). */
export function identifierKind(text: string): "username" | "email" | "phone" {
  const t = (text ?? "").trim();
  if (t.includes("@")) return "email";
  const digits = [...t].filter((c) => /\p{Nd}/u.test(c)).length;
  if (t.startsWith("+") || (digits >= 6 && digits >= [...t.replace(/ /g, "")].length - 1)) return "phone";
  return "username";
}
/** The ways this person can sign in with, strongest first; strongest protection mode keeps only passkeys and keys. */
export function signInWays(has: readonly string[], strongest = false): string[] {
  let order = WI_WAYS.filter((w) => (w.kind === "sign_in" || w.kind === "code") && has.includes(w.id));
  if (strongest) order = order.filter((w) => inList(WAYS_IN.protections.strongest_mode.only, w.id));
  return [...order].sort(byStrength).map((w) => w.id);
}
/** The extra checks a person has turned on, strongest first. */
export const extraChecks = (has: readonly string[]): string[] => WI_WAYS.filter((w) => w.kind === "extra" && has.includes(w.id)).sort(byStrength).map((w) => w.id);
/** A code lasts 5 minutes and only works on the device that asked for it. */
export function sentCodeValid(sentAt: number, now: number, askingDevice: string, device: string): boolean {
  const c = WAYS_IN.sign_in.codes;
  return now - sentAt <= c.lifetime_s && (!c.only_asking_device || askingDevice === device);
}
/** Offline sign-in only on a device already signed in online with that account, within its role's days. [ok, why] */
export function offlineSignIn(knownDevice: boolean, role: string, daysOffline: number): [boolean, string | null] {
  if (!knownDevice) return [false, "sign_in_online_first"];
  const days = (WAYS_IN.offline.back_online_days as Record<string, number>)[role] ?? 7;
  if (daysOffline > days) return [false, "go_online"];
  return [true, null];
}

// ---- protections ---------------------------------------------------------------------------------------------------------
export interface SignInPlace { country: string; at: number }
/** Why a sign-in looks unusual: a new country, a journey too fast between two countries, or many tries. Countries only. */
export function unusual(history: readonly SignInPlace[], attempt: SignInPlace, tries = 0): string[] {
  const u = WAYS_IN.protections.unusual, out: string[] = [];
  if (history.length && !history.some((h) => h.country === attempt.country)) out.push("new_country");
  const last = history.length ? history.reduce((a, b) => (b.at > a.at ? b : a)) : null;
  if (last && last.country !== attempt.country && attempt.at - last.at < u.journey_hours * WI_HOUR) out.push("impossible_journey");
  if (tries >= u.many_tries) out.push("many_tries");
  return out;
}
export const countryAllowed = (lock: readonly string[], country: string): boolean => !lock.length || lock.includes(country);
export const oldDevice = (lastUsed: number, now: number): boolean => now - lastUsed >= WAYS_IN.protections.old_devices_days * WI_DAY;
export const sessionHours = (remember: boolean): number => (remember ? WAYS_IN.protections.remember_device.remembered_days * 24 : WAYS_IN.protections.remember_device.not_remembered_hours);
export function antiPhishingProblem(word: string): string | null {
  const w = [...(word ?? "").trim()], a = WAYS_IN.protections.anti_phishing_word;
  if (w.length < a.min) return "too_short";
  if (w.length > a.max) return "too_long";
  return null;
}
export function backupCodesLeftNote(left: number): string | null {
  if (left <= 0) return "none_left";
  return left <= WAYS_IN.backup_codes.remind_at ? "make_new" : null;
}
/** The security checkup: every item still missing, in the register's order. */
export const checkup = (have: Record<string, boolean>): string[] => WAYS_IN.protections.checkup.items.filter((i) => !have[i]);

// ---- recovery ------------------------------------------------------------------------------------------------------------
export interface RecoveryWay { id: string; wait_h: number; cancellable?: boolean; staff_approvals?: number; with?: string }
/** The ways back in this person actually has, strongest first, each with its wait in hours. */
export const recoveryWays = (has: readonly string[]): RecoveryWay[] => (WAYS_IN.recovery.ways as unknown as readonly RecoveryWay[]).filter((w) => has.includes(w.id)).map((w) => ({ ...w }));
export const neverAllowed = (way: string): boolean => inList(WAYS_IN.recovery.never, way);
/** For 24 hours after a recovery: no payouts, payout changes, downloads, card changes or contact changes. */
export const restrictedAfterRecovery = (act: string, recoveredAt: number | null, now: number): boolean =>
  recoveredAt !== null && inList(WAYS_IN.recovery.restricted, act) && now - recoveredAt < WAYS_IN.recovery.restricted_h * WI_HOUR;
export const contactsConfirmed = (confirmations: readonly string[], contacts: readonly string[]): boolean =>
  new Set(confirmations.filter((c) => contacts.includes(c))).size >= WAYS_IN.recovery_contacts.confirm_min;
export function contactsProblem(contacts: readonly string[]): string | null {
  const n = new Set(contacts).size, rc = WAYS_IN.recovery_contacts;
  if (n < rc.min) return "too_few";
  if (n > rc.max) return "too_many";
  return null;
}
export const toStrongest = (failed: number): boolean => failed >= WAYS_IN.recovery.failed_attempts_to_strongest;

// ---- resets --------------------------------------------------------------------------------------------------------------
interface ResetRule { what: string; who: readonly string[]; where: string; never?: boolean; never_own?: boolean }
const WI_RESETS = WAYS_IN.resets as unknown as readonly ResetRule[];
/** Who may reset what, online or offline. [ok, why] */
export function mayReset(what: string, by: string, own = false, online = true): [boolean, string | null] {
  const r = WI_RESETS.find((x) => x.what === what);
  if (!r) return [false, "unknown"];
  if (r.never) return [false, "never"];
  if (!r.who.includes(by)) return [false, "not_allowed"];
  if (r.never_own && own) return [false, "not_own"];
  if (!online && r.where === "online") return [false, "go_online"];
  return [true, null];
}

// ---- point 4: the phone owner check (only where deep identity is needed) ---------------------------------------------------
export interface OwnerOutcome { result: "go" | "fix" | "stop" | "wait"; fixes: string[]; until: number | null }
const WI_OWNER = WAYS_IN.phone_owner;
/** Only the activities in the register need the real owner of the number; everyday use never does. */
export const ownerCheckNeeded = (activity: string): boolean => inList(WI_OWNER.activities, activity);
/** The mobile network where it offers the check (a business by its registered name where supported), else the ID document check. */
export function ownerCheckMethod(networkReady: boolean, business = false, registeredNameSupported = false): string {
  if (networkReady && (!business || registeredNameSupported)) return business ? "registered_name" : "network";
  return business ? "owner_id_document" : "id_document";
}
/** What the network's answer means; a recent SIM change makes the activity wait, whatever the answer. */
export function ownerCheckOutcome(answer: string, simChangedAt: number | null, now: number): OwnerOutcome {
  const wait = WI_OWNER.sim_swap_wait_hours * WI_HOUR;
  if (simChangedAt !== null && now - simChangedAt < wait) return { result: "wait", fixes: [], until: simChangedAt + wait };
  const result = (WI_OWNER.answers as Record<string, string>)[answer] as OwnerOutcome["result"] | undefined;
  if (!result) throw new Error("unknown answer");
  const fixes = result === "fix" ? [...WI_OWNER.partial_fixes] : result === "stop" ? [...WI_OWNER.no_match_fixes] : [];
  return { result, fixes, until: null };
}
/** A match is kept for a time for the same number; a new number or a SIM change since the match asks again. */
export function ownerMatchValid(matchedAt: number | null, now: number, numberChanged = false, simChangedAt: number | null = null): boolean {
  if (matchedAt === null || numberChanged) return false;
  if (simChangedAt !== null && simChangedAt > matchedAt) return false;
  return now - matchedAt < WI_OWNER.match_valid_days * WI_DAY;
}
