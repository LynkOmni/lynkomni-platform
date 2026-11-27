/** LynkDriver rules in TypeScript (port of core/drivers.py, proved by contract/vectors/drivers.v1.json): one pack for every kind of
 *  hardware, strongly enforced updates (security now, required in 3 days, normal in 7), and past the deadline the hardware pauses
 *  and its virtual device takes over, so a sale is never blocked. */
export interface DriverRelease { version: string; kind: "security" | "required" | "normal"; released_at: number }
export interface DriverKind { id: string; connections: string[]; virtual: string | null; certified_by?: string; no_stand_in?: string; standards?: string[]; file_instead: string | null }
export type DriverHwState = "connected" | "not_connected" | "needs_update" | "overdue" | "not_working";
export interface DriverRegister { pack: DriverRelease & { name: string; signed: string }; previous: DriverRelease[]; update_days: Record<string, number>; where: { online: string; offline: string }; kinds: DriverKind[]; roles: Record<string, { kind: string; ways: string[]; stand_in?: string }>; states: DriverHwState[]; ladder: string[]; speed_targets_ms: Record<string, number>; conditions: Record<string, { state: DriverHwState; warning: string | null; kinds?: string[]; connections?: string[] }>; stand_in_states: DriverHwState[]; future: { interface_version: number; retire_notice_months: number; never_dropped_while_used: boolean; new_kinds_by_register_only: boolean } }
export interface DriverState { state: "not_installed" | "current" | "available" | "overdue"; latest: string; deadline: number | null; kind?: string; hardware: "on" | "virtual" }
const DAY = 86400;
const ver = (s: string): number[] => s.split(".").map(Number);
const newer = (a: string, b: string): boolean => { const x = ver(a), y = ver(b); for (let i = 0; i < Math.max(x.length, y.length); i++) { const d = (x[i] ?? 0) - (y[i] ?? 0); if (d) return d > 0; } return false; };

export function driverReleases(r: DriverRegister): DriverRelease[] {
  return [...r.previous, { version: r.pack.version, kind: r.pack.kind, released_at: r.pack.released_at }].sort((a, b) => (newer(a.version, b.version) ? 1 : newer(b.version, a.version) ? -1 : 0));
}
export function driverState(r: DriverRegister, installed: string | null, now: number): DriverState {
  if (installed === null) return { state: "not_installed", latest: r.pack.version, deadline: null, hardware: "virtual" };
  const missing = driverReleases(r).filter((x) => newer(x.version, installed));
  if (!missing.length) return { state: "current", latest: r.pack.version, deadline: null, hardware: "on" };
  const due = (x: DriverRelease): number => x.released_at + (r.update_days[x.kind] ?? 0) * DAY;
  const first = missing.reduce((a, b) => (due(b) < due(a) ? b : a));
  const deadline = due(first);
  return now >= deadline ? { state: "overdue", latest: r.pack.version, deadline, kind: first.kind, hardware: "virtual" } : { state: "available", latest: r.pack.version, deadline, kind: first.kind, hardware: "on" };
}
export const needsInstall = (r: DriverRegister, kinds: string[], installed: string | null): string[] => (installed !== null ? [] : kinds.filter((k) => r.kinds.some((x) => x.id === k)));
export const driverFallback = (r: DriverRegister, kind: string): string | null => r.kinds.find((x) => x.id === kind)?.virtual ?? null;
/** The hardware kind that fills a role (DRIVER UPDATE D43: screens ask for a role, never a device). */
export const roleKind = (r: DriverRegister, role: string): string | null => r.roles[role]?.kind ?? null;
/** The next way in when a step of the ladder fails (D18); null after the last. */
export function ladderNext(r: DriverRegister, step: string): string | null { const i = r.ladder.indexOf(step); return i >= 0 && i + 1 < r.ladder.length ? (r.ladder[i + 1] ?? null) : null; }
export interface RoleStatus { role: string; kind: string; state: DriverHwState; warning: string | null; stand_in: string | null; next: string | null }
/** What a device shows for one piece of hardware in one condition (DRIVER UPDATE D12, D13, D18): its state, any warning and the
 *  stand-in that takes over, or by hand when none can. A sale is never blocked by any of them. */
export function roleStatus(r: DriverRegister, role: string, condition: string): RoleStatus {
  const kind = roleKind(r, role) ?? role;
  const c = r.conditions[condition] ?? { state: "connected" as DriverHwState, warning: null };
  const down = r.stand_in_states.includes(c.state);
  const v = r.roles[role]?.stand_in ?? r.kinds.find((x) => x.id === kind)?.virtual ?? null;
  return { role, kind, state: c.state, warning: c.warning, stand_in: down ? v : null, next: down ? (v ? "stand_in" : "by_hand") : null };
}
/** The conditions a tester can give this piece: paper only runs out in printers, a battery only runs low in wireless ones. */
export function conditionsFor(r: DriverRegister, role: string): string[] {
  const k = r.kinds.find((x) => x.id === (roleKind(r, role) ?? role));
  if (!k) return [];
  return Object.entries(r.conditions).filter(([, v]) => (!v.kinds || v.kinds.includes(k.id)) && (!v.connections || v.connections.some((c) => k.connections.includes(c)))).map(([c]) => c);
}
