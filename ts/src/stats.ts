/** LynkStat's additions (SERVICES UPDATE, master blueprint 67.5; section 4 step D4b): the TypeScript port of core/stats.py,
 *  checked against contract/vectors/stats.v1.json. The register travels in ts/src/stats.generated.ts (python3 tools/stats_vectors.py).
 *  Estimates are always labelled; own measures are formulas of figures, never code; small groups stay hidden. */
import { mulDiv, repeatDates, dayNumber, fromDayNumber } from "./books.js";

export interface StatsRegister {
  cohorts: { max_months: number };
  what_if: { default_elasticity_bp: number };
  measures: { max_terms: number; figures: string[] };
  freshness: { max_age_minutes: Record<string, number> };
  public: { min_group: number };
  [k: string]: unknown;
}
const monthIndex = (month: string): number => { const [y, m] = month.split("-").map(Number); return y! * 12 + m! - 1; };
const monthName = (i: number): string => `${String(Math.floor(i / 12)).padStart(4, "0")}-${String((i % 12) + 1).padStart(2, "0")}`;

// ---- groups over time --------------------------------------------------------------------------------------------------------
export function cohorts(S: StatsRegister, purchases: readonly { customer: string; month: string }[]) {
  const first = new Map<string, number>(), months = new Map<string, Set<number>>();
  for (const p of purchases) {
    const i = monthIndex(p.month);
    first.set(p.customer, Math.min(first.get(p.customer) ?? i, i));
    if (!months.has(p.customer)) months.set(p.customer, new Set());
    months.get(p.customer)!.add(i);
  }
  if (!first.size) return [];
  let last = -Infinity;
  for (const s of months.values()) for (const i of s) last = Math.max(last, i);
  return [...new Set(first.values())].sort((a, b) => a - b).map((start) => {
    const members = [...first.entries()].filter(([, f]) => f === start).map(([c]) => c);
    const span = Math.min(last - start, S.cohorts.max_months);
    const back = Array.from({ length: span }, (_, k) => members.filter((c) => months.get(c)!.has(start + k + 1)).length);
    return { month: monthName(start), size: members.length, back };
  });
}

// ---- what if -----------------------------------------------------------------------------------------------------------------
export interface Base { units: number; price_minor: number; unit_cost_minor: number; staff_minor: number }
export function whatIf(S: StatsRegister, base: Base, changes: { price_bp?: number; cost_bp?: number; staff_hours_bp?: number }, elasticityBp: number | null = null) {
  const e = elasticityBp ?? S.what_if.default_elasticity_bp;
  const pb = changes.price_bp ?? 0, cb = changes.cost_bp ?? 0, sb = changes.staff_hours_bp ?? 0;
  let units = base.units + Number((() => { const n = BigInt(base.units) * BigInt(pb) * BigInt(e), d = 100000000n; const a = n < 0n ? -n : n, q = (2n * a + d) / (2n * d); return n < 0n ? -q : q; })());
  const price = base.price_minor + mulDiv(base.price_minor, pb, 10000);
  const cost = base.unit_cost_minor + mulDiv(base.unit_cost_minor, cb, 10000);
  const staff = base.staff_minor + mulDiv(base.staff_minor, sb, 10000);
  units = Math.max(units, 0);
  const revenue = units * price;
  return { units, revenue, profit: revenue - units * cost - staff, estimate: true as const };
}

// ---- your own measures -------------------------------------------------------------------------------------------------------
type MeasureTok = ["n", bigint] | ["f", string] | ["o", string];
function measureTokens(expr: string): MeasureTok[] {
  const out: MeasureTok[] = [];
  const re = /\s*(?:(\d+)|([a-z_]+)|(.))/gy;
  let m: RegExpExecArray | null;
  re.lastIndex = 0;
  while (re.lastIndex < expr.length && (m = re.exec(expr)) !== null) {
    if (m[0] === "") break;
    if (m[1] !== undefined) out.push(["n", BigInt(m[1])]);
    else if (m[2] !== undefined) out.push(["f", m[2]]);
    else if (m[3] !== undefined && m[3].trim()) { if (!"+-*/()".includes(m[3])) throw new Error(`not allowed: ${m[3]}`); out.push(["o", m[3]]); }
  }
  return out;
}
export function measureNames(S: StatsRegister, expr: string): string[] {
  const toks = measureTokens(expr);
  const terms = toks.filter((t) => t[0] === "n" || t[0] === "f").length;
  if (terms === 0 || terms > S.measures.max_terms) throw new Error("a measure has between 1 and the most terms allowed");
  const names = [...new Set(toks.filter((t) => t[0] === "f").map((t) => t[1] as string))].sort();
  const unknown = names.filter((n) => !S.measures.figures.includes(n));
  if (unknown.length) throw new Error("unknown figures: " + unknown.join(", "));
  measureRun(toks, {});
  return names;
}
const MEASURE_SAFE = BigInt(Number.MAX_SAFE_INTEGER); // a result beyond it shows nothing
function measureRun(toks: MeasureTok[], figures: Record<string, number>): number | null {
  let pos = 0, zero = false;
  const peek = (): MeasureTok | undefined => toks[pos];
  const is = (t: MeasureTok | undefined, o: string): boolean => !!t && t[0] === "o" && t[1] === o;
  const rd = (n: bigint, d: bigint): bigint => { const a = n < 0n ? -n : n, q = (2n * a + d) / (2n * d); return n < 0n ? -q : q; };
  const atom = (): bigint => {
    const t = toks[pos++];
    if (!t) throw new Error("the measure ends too soon");
    if (is(t, "(")) { const v = expr(); if (!is(toks[pos++], ")")) throw new Error("a bracket is not closed"); return v; }
    if (is(t, "-")) return -atom();
    if (t[0] === "n") return t[1] as bigint;
    if (t[0] === "f") return BigInt(figures[t[1] as string] ?? 0);
    throw new Error("unexpected sign");
  };
  const term = (): bigint => {
    let v = atom();
    while (is(peek(), "*") || is(peek(), "/")) {
      const op = (toks[pos++] as MeasureTok)[1], r = atom();
      if (op === "*") v = v * r;
      else if (r === 0n) { zero = true; v = 0n; }                 // read on, so a broken formula is still refused
      else v = rd(r > 0n ? v : -v, r < 0n ? -r : r);
    }
    return v;
  };
  const expr = (): bigint => {
    let v = term();
    while (is(peek(), "+") || is(peek(), "-")) { const op = (toks[pos++] as MeasureTok)[1], r = term(); v = op === "+" ? v + r : v - r; }
    return v;
  };
  const v = expr();
  if (pos < toks.length) throw new Error("unexpected end");
  return zero || v > MEASURE_SAFE || v < -MEASURE_SAFE ? null : Number(v);
}
export function evaluate(S: StatsRegister, expr: string, figures: Record<string, number>): number | null {
  measureNames(S, expr);
  return measureRun(measureTokens(expr), figures);
}

// ---- scope, freshness, exports, goals, public reports ------------------------------------------------------------------------
export function scope<R extends { branch?: string | null }>(rows: readonly R[], viewer: { role: string; branch?: string | null }, rules: Record<string, string>): R[] {
  const r = rules[viewer.role] ?? "all", b = viewer.branch ?? null;
  return rows.filter((x) => r === "all" || (b !== null && x.branch === b));
}
export const freshness = (S: StatsRegister, updatedMinute: number, nowMinute: number, kind: string, expected: readonly string[], present: readonly string[]) => {
  const age = nowMinute - updatedMinute;
  return { age_minutes: age, stale: age > S.freshness.max_age_minutes[kind]!, missing: expected.filter((s) => !present.includes(s)) };
};
export const exportDates = (start: string, every: string, count: number): string[] =>
  every === "day" ? Array.from({ length: count }, (_, i) => fromDayNumber(dayNumber(start) + i)) : repeatDates(start, every, count);
export function goal(actual: number, target: number, elapsedBp: number): { progress_bp: number | null; on_track: boolean | null } {
  if (target <= 0) return { progress_bp: null, on_track: null };
  const p = mulDiv(actual, 10000, target);
  return { progress_bp: p, on_track: p >= elapsedBp };
}
export const publicTable = (S: StatsRegister, groups: readonly { group: string; n: number; value: number }[]) =>
  groups.map((g) => ({ group: g.group, n: g.n >= S.public.min_group ? g.n : null, value: g.n >= S.public.min_group ? g.value : null }));
