/** LynkDriver rules in TypeScript (port of core/drivers.py, proved by contract/vectors/drivers.v1.json): one pack for every kind of
 *  hardware, strongly enforced updates (security now, required in 3 days, normal in 7), and past the deadline the hardware pauses
 *  and its virtual device takes over, so a sale is never blocked. */
export interface DriverRelease { version: string; kind: "security" | "required" | "normal"; released_at: number }
export interface DriverKind { id: string; connections: string[]; virtual: string | null; certified_by?: string }
export interface DriverRegister { pack: DriverRelease & { name: string; signed: string }; previous: DriverRelease[]; update_days: Record<string, number>; where: { online: string; offline: string }; kinds: DriverKind[] }
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
