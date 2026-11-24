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
