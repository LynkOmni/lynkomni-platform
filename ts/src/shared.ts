/** The parts every service shares (CONNECT UPDATE 71.3; section 4 row 71.9 step 2): the rules of core/shared.py, checked against
 *  contract/vectors/shared.v1.json. The register comes from ts/src/shared.generated.ts (tools/shared_vectors.py). */
import { SHARED } from "./shared.generated.js";

const SH_DAY = 86400;
type Maps = Record<string, Record<string, string>>;

/** The base role a service's role maps to (owner, manager, accountant, auditor or staff). */
export function sharedBaseRole(kind: string, role: string): string {
  if ((SHARED.roles.base as readonly string[]).includes(role)) return role;
  const m = (SHARED.roles.maps as unknown as Maps)[kind] ?? {};
  const r = m[role];
  if (r === undefined) throw new RangeError(`${kind} role ${role} is not mapped`);
  return r;
}
/** Whether a service's role may do something in an area, through its base role's permissions. */
export function sharedMay(kind: string, role: string, area: string, permission: string): boolean {
  const perms = (SHARED.base as unknown as Record<string, Record<string, readonly string[]>>)[sharedBaseRole(kind, role)] ?? {};
  return (perms[area] ?? []).includes(permission);
}
export const binnable = (kind: string): boolean => kind in SHARED.bin.kinds;
export const purgeDue = (binnedAt: number, now: number): boolean => now - binnedAt >= SHARED.bin.keep_days * SH_DAY;
export const mayAudit = (role: string): boolean => (SHARED.audit_roles as readonly string[]).includes(role);
/** The calendar sources a section's progress allows. */
export const calendarSources = (built: (section: string) => boolean): string[] => SHARED.calendar.filter((s) => built(s.build_section)).map((s) => s.id);

// ---- one set of offline clash rules (CONNECT UPDATE 71.3; core/shared.py settle) ------------------------------------------
export interface OfflineChange { device: string; hlc: number; accepted: number; fields: Record<string, unknown> }
export interface Settled { rule: string; keep: string[]; fields: Record<string, unknown> | null; lost: string[]; flag: boolean }
const clashKinds = SHARED.clash.kinds as Record<string, string>;
const clashSafest = SHARED.clash.safest as Record<string, readonly string[]>;
/** The published rule for a kind of record; an unknown kind is an error. */
export function clashRule(kind: string): string { const r = clashKinds[kind]; if (!r) throw new Error(`unknown kind ${kind}`); return r; }
const shLess = (a: [number, string], b: [number, string]): boolean => a[0] < b[0] || (a[0] === b[0] && a[1] < b[1]);
/** Settle two offline changes to the same record by the same rule as the cloud. */
export function sharedSettle(kind: string, a: OfflineChange, b: OfflineChange): Settled {
  const rule = clashRule(kind);
  if (rule === "never_offline") throw new Error(`${kind} is never changed offline`);
  if (rule === "append") return { rule, keep: ["a", "b"], fields: null, lost: [], flag: false };
  if (rule === "first_wins") { const first = !shLess([b.accepted, b.device], [a.accepted, a.device]) ? "a" : "b"; return { rule, keep: [first], fields: null, lost: [first === "a" ? "b" : "a"], flag: true }; }
  if (rule === "safest_wins") {
    const order = clashSafest[kind] ?? []; const va = String(a.fields["state"]), vb = String(b.fields["state"]);
    const win = order.indexOf(va) <= order.indexOf(vb) ? va : vb;
    return { rule, keep: [win === va ? "a" : "b"], fields: { state: win }, lost: va === vb ? [] : ["state"], flag: false };
  }
  const aLater = shLess([b.hlc, b.device], [a.hlc, a.device]);
  const late = aLater ? a : b, early = aLater ? b : a;
  const merged: Record<string, unknown> = { ...early.fields }; const lost: string[] = [];
  for (const [f, v] of Object.entries(late.fields)) { if (f in early.fields && early.fields[f] !== v) lost.push(f); merged[f] = v; }
  lost.sort();
  const sorted = Object.fromEntries(Object.keys(merged).sort().map((k) => [k, merged[k]]));
  return { rule, keep: ["a", "b"], fields: sorted, lost, flag: lost.some((f) => (SHARED.clash.flag_fields as readonly string[]).includes(f)) };
}
