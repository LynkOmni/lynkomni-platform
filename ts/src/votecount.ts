/** LynkVote's counting methods (VOTE UPDATE, master blueprint 68.5; section 4 step E1): the TypeScript port of core/vote_count.py,
 *  checked against contract/vectors/vote.v1.json. Whole numbers and exact fractions only (BigInt); ties broken by the published
 *  draw (SHA-256 of the vote's seed and each candidate's id); "what if" is always labelled and never the official result. */
import { hex, sha256 } from "./votecrypto.js";
import { VOTE } from "./vote.generated.js";

// ---- exact fractions ---------------------------------------------------------------------------------------------------------
const gcd = (a: bigint, b: bigint): bigint => { a = a < 0n ? -a : a; b = b < 0n ? -b : b; while (b) [a, b] = [b, a % b]; return a; };
export class Frac {
  readonly n: bigint; readonly d: bigint;
  constructor(n: bigint | number, d: bigint | number = 1n) {
    let nn = BigInt(n), dd = BigInt(d);
    if (dd === 0n) throw new Error("division by zero");
    if (dd < 0n) { nn = -nn; dd = -dd; }
    const g = gcd(nn, dd) || 1n; this.n = nn / g; this.d = dd / g;
  }
  add(o: Frac): Frac { return new Frac(this.n * o.d + o.n * this.d, this.d * o.d); }
  sub(o: Frac): Frac { return new Frac(this.n * o.d - o.n * this.d, this.d * o.d); }
  mul(o: Frac): Frac { return new Frac(this.n * o.n, this.d * o.d); }
  div(o: Frac): Frac { return new Frac(this.n * o.d, this.d * o.n); }
  cmp(o: Frac): number { const x = this.n * o.d, y = o.n * this.d; return x < y ? -1 : x > y ? 1 : 0; }
  floor(): bigint { const q = this.n / this.d; return this.n < 0n && q * this.d !== this.n ? q - 1n : q; }
  pair(): [number, number] { return [Number(this.n), Number(this.d)]; }
}
const F = (n: bigint | number, d: bigint | number = 1n): Frac => new Frac(n, d);
type Score = number | Frac;
const cmpScore = (a: Score, b: Score): number => (a instanceof Frac || b instanceof Frac ? (a instanceof Frac ? a : F(a)).cmp(b instanceof Frac ? b : F(b)) : a - b);

// ---- the published draw --------------------------------------------------------------------------------------------------------
const lotKey = (seed: string, c: string): string => hex(sha256(new TextEncoder().encode(`${seed}|${c}`)));
const strCmp = (a: string, b: string): number => (a < b ? -1 : a > b ? 1 : 0);
export const lots = (cands: readonly string[], seed: string): string[] =>
  [...cands].sort((a, b) => strCmp(lotKey(seed, a), lotKey(seed, b)) || strCmp(a, b));
function best(scores: Record<string, Score>, cands: readonly string[], seed: string, n = 1): string[] {
  const order = lots(cands, seed);
  return [...cands].sort((a, b) => -cmpScore(scores[a]!, scores[b]!) || order.indexOf(a) - order.indexOf(b)).slice(0, n);
}
function worst(scores: Record<string, Score>, cands: readonly string[], seed: string): string {
  const order = lots(cands, seed);
  return [...cands].sort((a, b) => cmpScore(scores[a]!, scores[b]!) || order.indexOf(b) - order.indexOf(a))[0]!;
}
const zeros = (cands: readonly string[]): Record<string, number> => Object.fromEntries(cands.map((c) => [c, 0]));

// ---- one mark ----------------------------------------------------------------------------------------------------------------
export function plurality(ballots: readonly string[], cands: readonly string[], seats = 1, seed = "") {
  const counts = zeros(cands); for (const b of ballots) if (b in counts) counts[b]!++;
  return { counts, winners: best(counts, cands, seed, seats) };
}
export function twoRound(ballots: readonly string[], cands: readonly string[], seed = "") {
  const r = plurality(ballots, cands, 1, seed), valid = Object.values(r.counts).reduce((a, b) => a + b, 0), top = best(r.counts, cands, seed, 2);
  return r.counts[top[0]!]! * 2 > valid ? { counts: r.counts, winners: [top[0]!], second_round: null } : { counts: r.counts, winners: [] as string[], second_round: top };
}
export function approval(ballots: readonly string[][], cands: readonly string[], seats = 1, seed = "") {
  const counts = zeros(cands); for (const b of ballots) for (const c of new Set(b)) if (c in counts) counts[c]!++;
  return { counts, winners: best(counts, cands, seed, seats) };
}
export function weighted(ballots: readonly [string, number][], cands: readonly string[], seats = 1, seed = "") {
  const counts = zeros(cands); for (const [c, w] of ballots) if (c in counts && w > 0) counts[c]! += w;
  return { counts, winners: best(counts, cands, seed, seats) };
}
export function cumulative(ballots: readonly Record<string, number>[], cands: readonly string[], points: number, seats = 1, seed = "") {
  const counts = zeros(cands); let refused = 0;
  for (const b of ballots) {
    const e = Object.entries(b);
    if (e.some(([c, v]) => v < 0 || !(c in counts)) || e.reduce((s, [, v]) => s + v, 0) > points) { refused++; continue; }
    for (const [c, v] of e) counts[c]! += v;
  }
  return { counts, winners: best(counts, cands, seed, seats), refused };
}
export function quadratic(ballots: readonly Record<string, number>[], cands: readonly string[], credits: number, seed = "") {
  const counts = zeros(cands); let refused = 0;
  for (const b of ballots) {
    const e = Object.entries(b);
    if (e.some(([c, v]) => v < 0 || !(c in counts)) || e.reduce((s, [, v]) => s + v * v, 0) > credits) { refused++; continue; }
    for (const [c, v] of e) counts[c]! += v;
  }
  return { counts, winners: best(counts, cands, seed, 1), refused };
}
export function score(ballots: readonly Record<string, number>[], cands: readonly string[], top: number, seats = 1, seed = "") {
  const counts = zeros(cands);
  for (const b of ballots) for (const c of cands) { const v = b[c] ?? 0; if (v < 0 || v > top) throw new Error("a score outside the scale"); counts[c]! += v; }
  return { counts, winners: best(counts, cands, seed, seats) };
}
export function star(ballots: readonly Record<string, number>[], cands: readonly string[], top: number, seed = "") {
  const s = score(ballots, cands, top, 2, seed), [a, b] = s.winners as [string, string];
  const pa = ballots.filter((x) => (x[a] ?? 0) > (x[b] ?? 0)).length, pb = ballots.filter((x) => (x[b] ?? 0) > (x[a] ?? 0)).length;
  const win = pa !== pb ? (pa > pb ? a : b) : s.counts[a] !== s.counts[b] ? (s.counts[a]! > s.counts[b]! ? a : b) : lots([a, b], seed)[0]!;
  return { counts: s.counts, finalists: [a, b], preferred: { [a]: pa, [b]: pb }, winners: [win] };
}
export function majorityJudgment(ballots: readonly Record<string, number>[], cands: readonly string[], _grades: number, seed = "") {
  const key = (c: string): number[] => {
    const g = ballots.filter((b) => c in b).map((b) => b[c]!).sort((x, y) => x - y), out: number[] = [];
    while (g.length) out.push(g.splice(Math.floor((g.length - 1) / 2), 1)[0]!);
    return out;
  };
  const keys = Object.fromEntries(cands.map((c) => [c, key(c)])), order = lots(cands, seed);
  const lex = (a: number[], b: number[]): number => { for (let i = 0; i < Math.min(a.length, b.length); i++) if (a[i] !== b[i]) return b[i]! - a[i]!; return a.length - b.length; };
  const ranking = [...cands].sort((a, b) => lex(keys[a]!, keys[b]!) || order.indexOf(a) - order.indexOf(b));
  return { medians: Object.fromEntries(cands.map((c) => [c, keys[c]!.length ? keys[c]![0]! : null])), winners: [ranking[0]!], ranking };
}
export function budget(ballots: readonly Record<string, number>[], projects: Record<string, number>, total: number, seed = "") {
  const ids = Object.keys(projects), pts = zeros(ids);
  for (const b of ballots) for (const [p, v] of Object.entries(b)) if (p in pts && v > 0) pts[p]! += v;
  let left = total; const funded: string[] = [];
  for (const p of best(pts, ids, seed, ids.length)) if (pts[p]! > 0 && projects[p]! <= left) { funded.push(p); left -= projects[p]!; }
  return { points: pts, funded, left };
}
export function yesNo(ballots: readonly string[], majority = "simple", members: number | null = null, quorum: number | null = null, custom: [number, number] | null = null) {
  const y = ballots.filter((b) => b === "yes").length, n = ballots.filter((b) => b === "no").length, a = ballots.filter((b) => b === "abstain").length;
  if (quorum !== null && y + n + a < quorum) return { yes: y, no: n, abstain: a, quorum_met: false, passed: false };
  let ok: boolean;
  if (majority === "simple") ok = y > n;
  else if (majority === "absolute") ok = members !== null && y * 2 > members;
  else if (majority === "two_thirds") ok = y + n > 0 && y * 3 >= 2 * (y + n);
  else if (majority === "custom") ok = y + n > 0 && y * custom![1] >= custom![0] * (y + n);
  else throw new Error("unknown majority");
  return { yes: y, no: n, abstain: a, quorum_met: true, passed: ok };
}

// ---- ranked ballots ----------------------------------------------------------------------------------------------------------
const clean = (ballots: readonly string[][], cands: readonly string[]): string[][] =>
  ballots.map((b) => { const seen = new Set<string>(), r: string[] = []; for (const c of b) if (cands.includes(c) && !seen.has(c)) { seen.add(c); r.push(c); } return r; });
export function irv(ballots: readonly string[][], cands: readonly string[], seed = "") {
  const bs = clean(ballots, cands), left = [...cands], rounds: Record<string, number>[] = [];
  for (;;) {
    const counts = zeros(left);
    for (const b of bs) { const top = b.find((c) => c in counts); if (top !== undefined) counts[top]!++; }
    const active = Object.values(counts).reduce((s, v) => s + v, 0);
    rounds.push({ ...counts });
    const b0 = best(counts, left, seed)[0]!;
    if (counts[b0]! * 2 > active || left.length === 1) return { rounds, winners: [b0] };
    left.splice(left.indexOf(worst(counts, left, seed)), 1);
  }
}
export function stv(ballots: readonly string[][], cands: readonly string[], seats: number, seed = "") {
  const bs: [string[], Frac][] = clean(ballots, cands).filter((b) => b.length).map((b) => [b, F(1)]);
  const quota = Math.floor(bs.length / (seats + 1)) + 1, hopeful = [...cands], elected: string[] = [], rounds: Record<string, [number, number]>[] = [];
  while (elected.length < seats) {
    if (hopeful.length + elected.length <= seats) { elected.push(...best(zeros(hopeful), hopeful, seed, hopeful.length)); break; }
    const piles: Record<string, [string[], Frac][]> = Object.fromEntries(hopeful.map((c) => [c, []]));
    for (const b of bs) { const top = b[0].find((c) => c in piles); if (top !== undefined) piles[top]!.push(b); }
    const totals: Record<string, Frac> = Object.fromEntries(hopeful.map((c) => [c, piles[c]!.reduce((s, b) => s.add(b[1]), F(0))]));
    rounds.push(Object.fromEntries(hopeful.map((c) => [c, totals[c]!.pair()])));
    const top = best(totals, hopeful, seed)[0]!;
    if (totals[top]!.cmp(F(quota)) >= 0) {
      elected.push(top); hopeful.splice(hopeful.indexOf(top), 1);
      const keep = totals[top]!.sub(F(quota)).div(totals[top]!);
      for (const b of piles[top]!) b[1] = b[1].mul(keep);
    } else hopeful.splice(hopeful.indexOf(worst(totals, hopeful, seed)), 1);
  }
  return { quota, rounds, winners: elected };
}
export function borda(ballots: readonly string[][], cands: readonly string[], seed = "") {
  const n = cands.length, pts = zeros(cands);
  for (const b of clean(ballots, cands)) b.forEach((c, i) => { pts[c]! += n - 1 - i; });
  return { counts: pts, winners: best(pts, cands, seed) };
}
export function bucklin(ballots: readonly string[][], cands: readonly string[], seed = "") {
  const bs = clean(ballots, cands), n = ballots.length, counts = zeros(cands), rounds: Record<string, number>[] = [];
  for (let k = 0; k < cands.length; k++) {
    for (const b of bs) if (k < b.length) counts[b[k]!]!++;
    rounds.push({ ...counts });
    const b0 = best(counts, cands, seed)[0]!;
    if (counts[b0]! * 2 > n) return { rounds, winners: [b0] };
  }
  return { rounds, winners: [best(counts, cands, seed)[0]!] };
}
function pairwise(ballots: readonly string[][], cands: readonly string[]): Record<string, Record<string, number>> {
  const d: Record<string, Record<string, number>> = Object.fromEntries(cands.map((a) => [a, Object.fromEntries(cands.filter((b) => b !== a).map((b) => [b, 0]))]));
  for (const r of clean(ballots, cands)) {
    const pos = new Map(r.map((c, i) => [c, i]));
    for (const a of cands) for (const b of cands) if (a !== b && pos.has(a) && (!pos.has(b) || pos.get(a)! < pos.get(b)!)) d[a]![b]!++;
  }
  return d;
}
export function rankedPairs(ballots: readonly string[][], cands: readonly string[], seed = "") {
  const d = pairwise(ballots, cands), order = lots(cands, seed);
  const pairs: [string, string, number][] = [];
  for (const a of cands) for (const b of cands) if (a !== b && d[a]![b]! > d[b]![a]!) pairs.push([a, b, d[a]![b]! - d[b]![a]!]);
  pairs.sort((p, q) => q[2] - p[2] || d[q[0]]![q[1]]! - d[p[0]]![p[1]]! || order.indexOf(p[0]) - order.indexOf(q[0]) || order.indexOf(p[1]) - order.indexOf(q[1]));
  const locked: Record<string, Set<string>> = Object.fromEntries(cands.map((c) => [c, new Set<string>()]));
  const reaches = (x: string, y: string): boolean => { const stack = [x], seen = new Set<string>(); while (stack.length) { const n = stack.pop()!; if (n === y) return true; if (!seen.has(n)) { seen.add(n); stack.push(...locked[n]!); } } return false; };
  for (const [a, b] of pairs) if (!reaches(b, a)) locked[a]!.add(b);
  const beaten = new Set(cands.flatMap((a) => [...locked[a]!])), sources = cands.filter((c) => !beaten.has(c));
  return { pairwise: d, locked: cands.flatMap((a) => [...locked[a]!].sort((x, y) => order.indexOf(x) - order.indexOf(y)).map((b) => [a, b])), winners: [lots(sources, seed)[0]!] };
}
export function schulze(ballots: readonly string[][], cands: readonly string[], seed = "") {
  const d = pairwise(ballots, cands);
  const p: Record<string, Record<string, number>> = Object.fromEntries(cands.map((a) => [a, Object.fromEntries(cands.filter((b) => b !== a).map((b) => [b, d[a]![b]! > d[b]![a]! ? d[a]![b]! : 0]))]));
  for (const i of cands) for (const j of cands) { if (i === j) continue; for (const k of cands) { if (k === i || k === j) continue; p[j]![k] = Math.max(p[j]![k]!, Math.min(p[j]![i]!, p[i]![k]!)); } }
  const wins = Object.fromEntries(cands.map((a) => [a, cands.filter((b) => b !== a && p[a]![b]! > p[b]![a]!).length]));
  return { pairwise: d, paths: p, winners: [best(wins, cands, seed)[0]!], ranking: best(wins, cands, seed, cands.length) };
}

// ---- seats for party lists ---------------------------------------------------------------------------------------------------
function passing(votes: Record<string, number>, thresholdBp: number): Record<string, number> {
  const total = Object.values(votes).reduce((s, v) => s + v, 0);
  return Object.fromEntries(Object.entries(votes).filter(([, v]) => v * 10000 >= thresholdBp * total));
}
export function highestAverages(votes: Record<string, number>, seats: number, divisor: (k: number) => Frac, thresholdBp = 0, seed = ""): Record<string, number> {
  const ok = passing(votes, thresholdBp), got = zeros(Object.keys(votes)), ids = Object.keys(ok), order = lots(ids, seed);
  for (let s = 0; s < seats && ids.length; s++) {
    const q = (p: string): Frac => F(ok[p]!).div(divisor(got[p]!));
    const win = [...ids].sort((a, b) => -q(a).cmp(q(b)) || order.indexOf(a) - order.indexOf(b))[0]!;
    got[win]!++;
  }
  return got;
}
export const dhondt = (votes: Record<string, number>, seats: number, thresholdBp = 0, seed = "") => ({ seats: highestAverages(votes, seats, (k) => F(k + 1), thresholdBp, seed) });
export const sainteLague = (votes: Record<string, number>, seats: number, thresholdBp = 0, seed = "") => ({ seats: highestAverages(votes, seats, (k) => F(2 * k + 1), thresholdBp, seed) });
export function modifiedSainteLague(votes: Record<string, number>, seats: number, thresholdBp = 0, seed = "") {
  const [n, d] = VOTE.methods.modified_sainte_lague.first_divisor as [number, number];
  return { seats: highestAverages(votes, seats, (k) => (k === 0 ? F(n, d) : F(2 * k + 1)), thresholdBp, seed) };
}
export function largestRemainder(votes: Record<string, number>, seats: number, quota = "hare", thresholdBp = 0, seed = "") {
  const ok = passing(votes, thresholdBp), ids = Object.keys(ok), total = ids.reduce((s, p) => s + ok[p]!, 0), got = zeros(Object.keys(votes));
  if (!ids.length || total === 0) return { seats: got, quota: null };
  const q = quota === "hare" ? F(total, seats) : quota === "droop" ? F(Math.floor(total / (seats + 1)) + 1) : F(total, seats + 2);
  const rem: Record<string, Frac> = {}, order = lots(ids, seed);
  for (const p of ids) { const whole = Number(F(ok[p]!).div(q).floor()); got[p] = whole; rem[p] = F(ok[p]!).sub(F(whole).mul(q)); }
  const left = seats - Object.values(got).reduce((s, v) => s + v, 0);
  const byRem = [...ids].sort((a, b) => -rem[a]!.cmp(rem[b]!) || order.indexOf(a) - order.indexOf(b));
  for (const p of byRem.slice(0, Math.max(left, 0))) got[p]!++;
  for (const p of [...byRem].reverse()) { if (Object.values(got).reduce((s, v) => s + v, 0) <= seats) break; if (got[p]! > 0) got[p]!--; }
  return { seats: got, quota: q.pair() };
}
