/** The office side of gift cards, store credit, deposits, matching and payment costs (SERVICES UPDATE 67.2 and 67.8; section 4
 *  step F, row 67.17): the TypeScript port of core/office_money.py, checked against contract/vectors/office-money.v1.json. The
 *  register's numbers travel in ts/src/officemoney.generated.ts (python3 tools/office_money_vectors.py). Whole minor units only. */
import { WINDOW_DAYS, LATE_AFTER_DAYS } from "./officemoney.generated.js";

const whole = (...v: unknown[]): void => {
  if (!v.every((x) => typeof x === "number" && Number.isInteger(x))) throw new Error("whole minor units only");
};
const day = (t: string): number => {
  const [y, m, d] = t.split("-").map(Number);
  return Date.UTC(y!, m! - 1, d!) / 86400000;
};

export type Move = { id: string; kind: "issue" | "spend"; amount: number };
export function balances(moves: readonly Move[]): { held: Record<string, number>; overdrawn: string[] } {
  const held: Record<string, number> = {}, over: string[] = [];
  for (const mv of moves) {
    whole(mv.amount);
    if (mv.amount <= 0) throw new Error("an amount is more than nothing");
    held[mv.id] = (held[mv.id] ?? 0) + (mv.kind === "issue" ? 1 : -1) * mv.amount;
    if (held[mv.id]! < 0 && !over.includes(mv.id)) over.push(mv.id);
  }
  return { held, overdrawn: over };
}

export function depositLeft(taken: number, settled: readonly number[]): number {
  whole(taken, ...settled);
  const left = taken - settled.reduce((a, b) => a + b, 0);
  if (taken <= 0 || settled.some((a) => a <= 0) || left < 0) throw new Error("a deposit settles at most what it holds");
  return left;
}

export type Pay = { ref: string; amount: number; currency: string; on: string };
export type Target = { kind: string; id: string; ref?: string; amount: number; currency: string; on: string };
export type Matched = { matched: [string, string, string][]; suggested: [string, string, string][]; unmatched: string[] };
export function match(payments: readonly Pay[], targets: readonly Target[], windowDays: number | null = null): Matched {
  const w = windowDays ?? WINDOW_DAYS;
  const open = [...targets];
  const out: Matched = { matched: [], suggested: [], unmatched: [] };
  const byRef = new Map<string, Target>();
  for (const t of open) if (t.ref) byRef.set(t.ref, t);
  const rest: Pay[] = [];
  for (const p of payments) {
    whole(p.amount);
    const t = byRef.get(p.ref);
    if (t && open.includes(t) && t.amount === p.amount && t.currency === p.currency) {
      out.matched.push([p.ref, t.kind, t.id]); open.splice(open.indexOf(t), 1);
    } else rest.push(p);
  }
  for (const p of rest) {
    const c = open.filter((t) => t.amount === p.amount && t.currency === p.currency && Math.abs(day(p.on) - day(t.on)) <= w);
    if (c.length === 1) { out.suggested.push([p.ref, c[0]!.kind, c[0]!.id]); open.splice(open.indexOf(c[0]!), 1); }
    else out.unmatched.push(p.ref);
  }
  return out;
}

export type CostLine = { ref: string; on: string; currency: string; amount: number; provider_fee: number; lynkomni_part: number };
export type Month = { month: string; currency: string; payments: number; amount: number; provider_fee: number; lynkomni_part: number };
export function costs(lines: readonly CostLine[]): { payments: { ref: string; cost: number; net: number }[]; months: Month[] } {
  const per: { ref: string; cost: number; net: number }[] = [], months = new Map<string, Month>();
  for (const l of lines) {
    whole(l.amount, l.provider_fee, l.lynkomni_part);
    if (l.provider_fee < 0 || l.lynkomni_part < 0 || l.provider_fee + l.lynkomni_part > l.amount) throw new Error("costs are never negative and never more than the payment");
    const cost = l.provider_fee + l.lynkomni_part;
    per.push({ ref: l.ref, cost, net: l.amount - cost });
    const key = `${l.on.slice(0, 7)}|${l.currency}`;
    const mo = months.get(key) ?? { month: l.on.slice(0, 7), currency: l.currency, payments: 0, amount: 0, provider_fee: 0, lynkomni_part: 0 };
    mo.payments += 1; mo.amount += l.amount; mo.provider_fee += l.provider_fee; mo.lynkomni_part += l.lynkomni_part;
    months.set(key, mo);
  }
  return { payments: per, months: [...months.keys()].sort().map((k) => months.get(k)!) };
}

export type Payout = { id: string; expected_on: string; amount: number; currency: string };
export function payouts(scheduled: readonly Payout[], arrived: Record<string, string>, today: string): (Payout & { state: string })[] {
  return [...scheduled].sort((a, b) => (a.expected_on === b.expected_on ? (a.id < b.id ? -1 : a.id > b.id ? 1 : 0) : a.expected_on < b.expected_on ? -1 : 1)).map((p) => {
    whole(p.amount);
    const state = p.id in arrived ? "arrived" : day(today) - day(p.expected_on) > LATE_AFTER_DAYS ? "late" : "expected";
    return { ...p, state };
  });
}
