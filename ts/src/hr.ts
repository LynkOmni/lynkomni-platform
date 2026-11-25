/** LynkHR's rules (SIX SERVICES UPDATE, master blueprint 69.3, 69.11 and 69.12; build section 4B): the TypeScript port of
 *  core/hr.py, checked against contract/vectors/hr.v1.json. The register travels in ts/src/hr.generated.ts
 *  (python3 tools/hr_vectors.py). Leave is counted in half days; money is integer minor units; nothing decides about a person. */

export interface HrRegister {
  on_payroll: string[];
  fields: { always: string[]; sensitive: Record<string, string[]>; special: string[]; self_sees: string[] };
  leave: { kinds: string[]; default_half_days: Record<string, number | null>; carry_cap_half_days: number; max_away_share_bp: number };
  checklists: Record<string, { id: string; must: boolean }[]>;
  probation_months_default: number;
  expiry: { remind_days_before: number[] };
  reviews: { kinds: string[]; anonymous: string[]; min_answers: number };
  pay: { overtime: { weekly_minutes_threshold: number; multiplier_bp: number } };
  cases: { see: string[]; steps: string[]; days_per_step: Record<string, number> };
  assist: { may: string[]; never: string[] };
  tiers: Record<string, string[]>;
  [k: string]: unknown;
}
type Pack = { office?: { hr?: Record<string, unknown> } } | null | undefined;
const packHr = (p: Pack): Record<string, unknown> => p?.office?.hr ?? {};
const MS = 86400000;
/** A date as a whole day number (days since 1970-01-01), the same as core/hr.py day(). */
export const hrDay = (iso: string): number => Math.round(Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10)) / MS);
export const hrIso = (n: number): string => new Date(n * MS).toISOString().slice(0, 10);
/** a × b × c / d rounded half up, in whole numbers (BigInt, never a float). */
const mulHalfUp = (a: number, b: number, c: number, d: number): number => { const n = BigInt(a) * BigInt(b) * BigInt(c), q = BigInt(d); return Number((2n * n + q) / (2n * q)); };

// ---- records -------------------------------------------------------------------------------------------------------------------
export function hrVisibleFields(H: HrRegister, role: string, isSelf = false): string[] {
  const out = [...H.fields.always];
  for (const [name, roles] of Object.entries(H.fields.sensitive)) if (roles.includes(role) || (isSelf && H.fields.self_sees.includes(name))) out.push(name);
  return out;
}
export function hrSpecialAllowed(H: HrRegister, kind: string, pack: Pack): boolean {
  if (!H.fields.special.includes(kind)) return true;
  return ((packHr(pack)["special_allowed"] ?? {}) as Record<string, unknown>)[kind] === true;
}
export const onPayroll = (H: HrRegister, kind: string): boolean => H.on_payroll.includes(kind);

// ---- leave ---------------------------------------------------------------------------------------------------------------------
export function leaveMinimum(kind: string, pack: Pack): number | null {
  const v = ((packHr(pack)["leave_half_days"] ?? {}) as Record<string, unknown>)[kind];
  return Number.isInteger(v) ? (v as number) : null;
}
export const hasBalance = (H: HrRegister, kind: string): boolean => !(kind in H.leave.default_half_days) || H.leave.default_half_days[kind] !== null;
export const carryOver = (H: HrRegister, remaining: number, cap?: number): number => Math.max(0, Math.min(remaining, cap ?? H.leave.carry_cap_half_days));
export const leaveBalance = (entitled: number, taken: number, carried = 0): number => carried + entitled - taken;
export function leaveRequestOk(H: HrRegister, kind: string, halfDays: number, balance: number): boolean {
  if (!H.leave.kinds.includes(kind) || halfDays <= 0) return false;
  return !hasBalance(H, kind) ? true : halfDays <= balance;
}
export const hrMayApprove = (asker: string, approver: string | null | undefined): boolean => !!approver && asker !== approver;
export function leaveClashes(H: HrRegister, teamSize: number, awayByDay: Record<string, number>, days: readonly string[], shareBp?: number): string[] {
  const share = shareBp ?? H.leave.max_away_share_bp;
  return days.filter((d) => ((awayByDay[d] ?? 0) + 1) * 10000 > share * teamSize);
}
export function absenceCounts(records: readonly { kind: string }[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const r of records) out[r.kind] = (out[r.kind] ?? 0) + 1;
  return Object.fromEntries(Object.entries(out).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
}

// ---- joining and leaving -------------------------------------------------------------------------------------------------------
export function hrChecklist(H: HrRegister, kind: string, done: readonly string[]): { done: number; total: number; musts_left: string[] } {
  const items = H.checklists[kind] ?? [];
  return { done: items.filter((i) => done.includes(i.id)).length, total: items.length, musts_left: items.filter((i) => i.must && !done.includes(i.id)).map((i) => i.id) };
}
export const finalPayReady = (done: readonly string[]): boolean => ["notice_recorded", "equipment_back", "access_closed"].every((x) => done.includes(x));
export function probationEnd(H: HrRegister, start: string, months?: number): string {
  const m0 = +start.slice(5, 7) - 1 + (months ?? H.probation_months_default), y = +start.slice(0, 4) + Math.floor(m0 / 12), m = (m0 % 12) + 1;
  const last = new Date(Date.UTC(y, m, 0)).getUTCDate(), d = Math.min(+start.slice(8, 10), last);
  return `${String(y).padStart(4, "0")}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}
export function expiryStage(H: HrRegister, expiry: string, today: string): "expired" | number | null {
  const left = hrDay(expiry) - hrDay(today);
  if (left < 0) return "expired";
  const steps = H.expiry.remind_days_before.filter((s) => left <= s);
  return steps.length ? Math.min(...steps) : null;
}

// ---- reviews and pay -----------------------------------------------------------------------------------------------------------
export function reviewShown(H: HrRegister, kind: string, answers: number): boolean {
  if (!H.reviews.kinds.includes(kind)) return false;
  return H.reviews.anonymous.includes(kind) ? answers >= H.reviews.min_answers : answers > 0;
}
export function payChangeOk(proposer: string, approver: string, increaseTotal: number, budget: number, secondApprover?: string | null): boolean {
  if (!hrMayApprove(proposer, approver)) return false;
  if (increaseTotal <= budget) return true;
  return !!secondApprover && secondApprover !== proposer && secondApprover !== approver;
}
export const overtimeMinutes = (H: HrRegister, weekMinutes: number, pack?: Pack): number =>
  Math.max(0, weekMinutes - ((packHr(pack)["overtime_weekly_minutes"] as number | undefined) ?? H.pay.overtime.weekly_minutes_threshold));
export const overtimePay = (H: HrRegister, minutes: number, hourlyMinor: number, pack?: Pack): number =>
  mulHalfUp(minutes, hourlyMinor, (packHr(pack)["overtime_multiplier_bp"] as number | undefined) ?? H.pay.overtime.multiplier_bp, 60 * 10000);
export interface StaffPay { id: string; kind: string; salary?: number; allowances?: number[]; week_minutes?: number; hourly_minor?: number; commission?: number; advance_repaid?: number }
export function payrollFigures(H: HrRegister, staff: readonly StaffPay[], pack?: Pack): { id: string; gross: number; overtime: number; deductions: number }[] {
  return staff.filter((s) => onPayroll(H, s.kind)).map((s) => {
    const ot = overtimePay(H, overtimeMinutes(H, s.week_minutes ?? 0, pack), s.hourly_minor ?? 0, pack);
    return { id: s.id, gross: (s.salary ?? 0) + (s.allowances ?? []).reduce((a, b) => a + b, 0) + ot + (s.commission ?? 0), overtime: ot, deductions: s.advance_repaid ?? 0 };
  });
}
export function hrHeadcount(positions: readonly { yearly_cost: number }[], budget: number): { total: number; over: number } {
  const total = positions.reduce((a, p) => a + p.yearly_cost, 0);
  return { total, over: Math.max(0, total - budget) };
}

// ---- cases ---------------------------------------------------------------------------------------------------------------------
export const hrCaseMaySee = (H: HrRegister, role: string, named = false): boolean => H.cases.see.includes(role) || (role === "owner" && named);
export const hrCaseDeadline = (H: HrRegister, step: string, started: number): number | null => (step in H.cases.days_per_step ? started + H.cases.days_per_step[step]! : null);
export function hrCaseNext(H: HrRegister, step: string): string | null { const i = H.cases.steps.indexOf(step); return i >= 0 && i + 1 < H.cases.steps.length ? H.cases.steps[i + 1]! : null; }

// ---- LynkAssist and tiers ------------------------------------------------------------------------------------------------------
export const hrAssistMay = (H: HrRegister, action: string): boolean => H.assist.may.includes(action) && !H.assist.never.includes(action);
export function hrTierHas(H: HrRegister, tier: string, feature: string): boolean {
  const order = ["free", "plus", "pro", "max"], i = order.indexOf(tier);
  return i >= 0 && order.slice(0, i + 1).some((t) => (H.tiers[t] ?? []).includes(feature));
}
