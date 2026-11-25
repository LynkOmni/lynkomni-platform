/** LynkProject's rules (SIX SERVICES UPDATE, master blueprint 69.4, 69.11 and 69.12; build section 4B): the TypeScript port of
 *  core/project.py, checked against contract/vectors/project.v1.json. The register travels in ts/src/project.generated.ts
 *  (python3 tools/project_vectors.py). Durations are whole days, time whole minutes, money integer minor units. */

export interface ProjectRegister {
  moves: Record<string, string[]>;
  finished: string[];
  my_work: { week_days: number; buckets: string[] };
  workload: { default_week_minutes: number };
  time: { max_entry_minutes: number };
  guests: { see: string[] };
  assist: { may: string[]; never: string[] };
  tiers: Record<string, string[]>;
  [k: string]: unknown;
}
export interface Task { id: string; state?: string; waits_on?: string[]; days?: number; due?: number | null; owner?: string }
const finished = (P: ProjectRegister, t: Task): boolean => P.finished.includes(t.state ?? "");

// ---- states and waiting --------------------------------------------------------------------------------------------------------
export const taskMoveOk = (P: ProjectRegister, from: string, to: string): boolean => (P.moves[from] ?? []).includes(to);
export function taskBlockers(task: Task, tasks: readonly Task[]): string[] {
  const by = new Map(tasks.map((t) => [t.id, t]));
  return (task.waits_on ?? []).filter((b) => by.has(b) && by.get(b)!.state !== "done" && by.get(b)!.state !== "cancelled");
}
export const taskDoneOk = (P: ProjectRegister, task: Task, tasks: readonly Task[]): boolean => taskMoveOk(P, task.state ?? "todo", "done") && taskBlockers(task, tasks).length === 0;
export function waitOk(deps: Record<string, string[]>, a: string, b: string): boolean {
  if (a === b) return false;
  const seen = new Set<string>(), stack = [b];
  while (stack.length) {
    const x = stack.pop()!;
    if (x === a) return false;
    if (seen.has(x)) continue;
    seen.add(x); stack.push(...(deps[x] ?? []));
  }
  return true;
}
export function projectSchedule(tasks: readonly Task[]): { start: Record<string, number>; finish: Record<string, number>; length: number; critical: string[] } {
  const by = new Map(tasks.map((t) => [t.id, t])), order: string[] = [], mark = new Map<string, number>();
  const visit = (i: string): void => {
    if (mark.get(i) === 2) return;
    mark.set(i, 1);
    for (const d of by.get(i)!.waits_on ?? []) if (by.has(d)) visit(d);
    mark.set(i, 2); order.push(i);
  };
  for (const t of tasks) visit(t.id);
  const es: Record<string, number> = {}, ef: Record<string, number> = {};
  for (const i of order) { es[i] = Math.max(0, ...(by.get(i)!.waits_on ?? []).filter((d) => by.has(d)).map((d) => ef[d]!)); ef[i] = es[i]! + (by.get(i)!.days ?? 0); }
  const length = Math.max(0, ...Object.values(ef));
  const after: Record<string, string[]> = Object.fromEntries(tasks.map((t) => [t.id, [] as string[]]));
  for (const t of tasks) for (const d of t.waits_on ?? []) if (d in after) after[d]!.push(t.id);
  const lf: Record<string, number> = {};
  for (const i of [...order].reverse()) { const n = after[i]!.map((x) => lf[x]! - (by.get(x)!.days ?? 0)); lf[i] = n.length ? Math.min(...n) : length; }
  return { start: Object.fromEntries(tasks.map((t) => [t.id, es[t.id]!])), finish: Object.fromEntries(tasks.map((t) => [t.id, ef[t.id]!])), length,
    critical: tasks.filter((t) => lf[t.id] === ef[t.id]).map((t) => t.id) };
}

// ---- late, at risk and My work -------------------------------------------------------------------------------------------------
export const lateTasks = (P: ProjectRegister, tasks: readonly Task[], today: number): string[] =>
  tasks.filter((t) => !finished(P, t) && t.due != null && t.due < today).map((t) => t.id);
export function atRiskTasks(P: ProjectRegister, tasks: readonly Task[], today: number): string[] {
  const lateIds = new Set(lateTasks(P, tasks, today)), by = new Map(tasks.map((t) => [t.id, t])), out: string[] = [];
  for (const t of tasks) {
    if (finished(P, t) || lateIds.has(t.id) || t.due == null) continue;
    for (const b of taskBlockers(t, tasks)) {
      const bt = by.get(b)!;
      if (lateIds.has(b) || (bt.due != null && bt.due + (t.days ?? 0) > t.due)) { out.push(t.id); break; }
    }
  }
  return out;
}
export function myWork(P: ProjectRegister, tasks: readonly Task[], person: string, today: number): Record<string, string[]> {
  const out: Record<string, string[]> = Object.fromEntries(P.my_work.buckets.map((b) => [b, [] as string[]]));
  for (const t of tasks) {
    if (t.owner !== person || finished(P, t)) continue;
    const d = t.due;
    const b = d == null ? "no_date" : d < today ? "overdue" : d === today ? "today" : d < today + P.my_work.week_days ? "this_week" : "later";
    out[b]!.push(t.id);
  }
  return out;
}
export function workloadFor(P: ProjectRegister, planned: Record<string, number>, leaveHalfDays: Record<string, number> = {}, weekMinutes: Record<string, number> = {}): Record<string, { planned: number; can: number; over: number }> {
  const out: Record<string, { planned: number; can: number; over: number }> = {};
  for (const p of Object.keys(planned).sort()) {
    const can = Math.max(0, (weekMinutes[p] ?? P.workload.default_week_minutes) - 240 * (leaveHalfDays[p] ?? 0));
    out[p] = { planned: planned[p]!, can, over: Math.max(0, planned[p]! - can) };
  }
  return out;
}

// ---- time and money ------------------------------------------------------------------------------------------------------------
export const timeEntryOk = (P: ProjectRegister, minutes: unknown): boolean => Number.isInteger(minutes) && (minutes as number) > 0 && (minutes as number) <= P.time.max_entry_minutes;
export const timeApproveOk = (logger: string, approver: string | null | undefined): boolean => !!approver && logger !== approver;
export interface TimeEntry { id: string; minutes: number; rate: number; approved?: boolean; billable?: boolean; billed?: boolean }
export function billableTime(entries: readonly TimeEntry[]): { ids: string[]; minutes: number; amount: number } {
  const pick = entries.filter((e) => e.approved && e.billable && !e.billed);
  return { ids: pick.map((e) => e.id), minutes: pick.reduce((a, e) => a + e.minutes, 0),
    amount: pick.reduce((a, e) => a + Number((2n * BigInt(e.minutes) * BigInt(e.rate) + 60n) / 120n), 0) };
}
export function projectMoney(budget: number, costs: readonly number[], invoiced: number): { spent: number; left: number; over: number; profit: number } {
  const spent = costs.reduce((a, b) => a + b, 0);
  return { spent, left: budget - spent, over: Math.max(0, spent - budget), profit: invoiced - spent };
}
export function milestoneVariance(baseline: Record<string, number>, current: Record<string, number>): Record<string, number> {
  return Object.fromEntries(Object.keys(baseline).sort().filter((k) => k in current).map((k) => [k, current[k]! - baseline[k]!]));
}
export function sprintStats(items: readonly { points: number; done_day?: number | null }[], days: number): { velocity: number; burndown: number[] } {
  const total = items.reduce((a, i) => a + i.points, 0);
  return { velocity: items.filter((i) => i.done_day != null).reduce((a, i) => a + i.points, 0),
    burndown: Array.from({ length: days }, (_, k) => total - items.filter((i) => i.done_day != null && i.done_day <= k + 1).reduce((a, i) => a + i.points, 0)) };
}

// ---- who sees what -------------------------------------------------------------------------------------------------------------
export const guestSees = (P: ProjectRegister, part: string, invitedTo: readonly string[], project: string): boolean => invitedTo.includes(project) && P.guests.see.includes(part);
export const fieldPlaceOk = (onShift: boolean, agreed: boolean): boolean => onShift && agreed;
export const pjAssistMay = (P: ProjectRegister, action: string): boolean => P.assist.may.includes(action) && !P.assist.never.includes(action);
export function pjTierHas(P: ProjectRegister, tier: string, feature: string): boolean {
  const order = ["free", "plus", "pro", "max"], i = order.indexOf(tier);
  return i >= 0 && order.slice(0, i + 1).some((t) => (P.tiers[t] ?? []).includes(feature));
}
