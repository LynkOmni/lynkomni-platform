/** LynkAcc's rules (OFFICE UPDATE, master blueprint 66.2; section 4 step D1): the TypeScript port of core/books.py, checked
 *  against contract/vectors/books.v1.json. The register and the chart travel in ts/src/books.generated.ts
 *  (python3 tools/books_vectors.py). Money is integer minor units; every split adds up exactly; rounding half away from zero,
 *  worked out in BigInt so large amounts agree with the Python reference. */

export interface Account { name: string; type: string; group: string; contra?: boolean; intercompany?: boolean }
export interface BooksRegister {
  bills: { moves: Record<string, Record<string, string>>; approval: { up_to_minor: number | null; roles: string[] }[] };
  expenses: { card_match_days: number };
  closing: { checklist: string[]; year_end_account: string };
  two_person: { kinds: string[] };
  bank: { match_days: number };
  statements: { cash_flow_groups: Record<string, string[]> };
  group: { intercompany_accounts: string[] };
  dimensions: { kinds: string[] };
  entity_tools: Record<string, string[]>;
  [k: string]: unknown;
}
export type Line = [string, number, number];

const CASH_BY_METHOD: Record<string, string> = { cash: "1000", bank: "1020", mobile_money: "1030", cheque: "1040" };
const ADDED = ["sales", "import"];

// ---- integer arithmetic ------------------------------------------------------------------------------------------------------
function rdBig(n: bigint, d: bigint): bigint {
  if (d <= 0n) throw new Error("divide by a positive number");
  const a = n < 0n ? -n : n;
  const q = (2n * a + d) / (2n * d);
  return n < 0n ? -q : q;
}
const big = (x: number): bigint => BigInt(x);
/** n / d rounded half away from zero (d > 0). */
export const roundDiv = (n: number, d: number): number => Number(rdBig(big(n), big(d)));
/** a * b / d, rounded half away from zero, without losing precision. */
export const mulDiv = (a: number, b: number, d: number): number => Number(rdBig(big(a) * big(b), big(d)));

export function split(total: number, parts: number): number[] {
  if (parts <= 0) return [];
  const abs = Math.abs(total), base = Math.floor(abs / parts), rem = abs - base * parts, sign = total < 0 ? -1 : 1;
  return Array.from({ length: parts }, (_, i) => sign * (base + (i < rem ? 1 : 0)));
}
export function allocate(total: number, weights: readonly number[]): number[] {
  const w = weights.reduce((a, b) => a + b, 0);
  if (!weights.length || w <= 0) return [];
  const out = weights.slice(0, -1).map((x) => mulDiv(total, x, w));
  return [...out, total - out.reduce((a, b) => a + b, 0)];
}

// ---- tax ---------------------------------------------------------------------------------------------------------------------
/** A rate written as a decimal string ("0.18", "18%", "0.075") as integer basis points, read exactly; finer than a basis point is refused. */
export function rateBp(rate: string | number): number {
  let t = String(rate).trim();
  const pct = t.endsWith("%");
  t = t.replace(/%+$/, "").trim();
  const dot = t.indexOf("."), whole = dot < 0 ? t : t.slice(0, dot), frac = dot < 0 ? "" : t.slice(dot + 1);
  if (!(whole || frac) || !/^\d*$/.test(whole) || !/^\d*$/.test(frac) || (whole === "" && frac === "")) throw new Error(`not a rate: ${rate}`);
  const places = pct ? 2 : 4;
  if (frac.replace(/0+$/, "").length > places) throw new Error(`rate finer than a basis point: ${rate}`);
  const f = (frac + "0".repeat(places)).slice(0, places);
  return parseInt(whole || "0", 10) * 10 ** places + parseInt(f || "0", 10);
}
export interface Tax { kind: string; rate_bp: number }
export function taxLine(amount: number, taxes: readonly Tax[], included = false) {
  const rates = taxes.filter((t) => ADDED.includes(t.kind)).map((t) => t.rate_bp);
  const R = rates.reduce((a, b) => a + b, 0);
  let net: number, shares: number[];
  if (included && R) { net = mulDiv(amount, 10000, 10000 + R); shares = allocate(amount - net, rates); }
  else { net = amount; shares = rates.map((r) => mulDiv(net, r, 10000)); }
  let i = 0;
  const out = taxes.map((t) => ADDED.includes(t.kind) ? { kind: t.kind, rate_bp: t.rate_bp, amount: shares[i++]!, charged: true }
    : { kind: t.kind, rate_bp: t.rate_bp, amount: mulDiv(net, t.rate_bp, 10000), charged: false });
  const total = net + out.filter((t) => t.charged).reduce((a, t) => a + t.amount, 0);
  const withheld = out.filter((t) => t.kind === "withholding").reduce((a, t) => a + t.amount, 0);
  const reverse = out.filter((t) => t.kind === "reverse_charge").reduce((a, t) => a + t.amount, 0);
  return { net, taxes: out, total, withheld, to_pay: total - withheld, reverse_charge: reverse };
}

// ---- bills to pay ------------------------------------------------------------------------------------------------------------
export const billMove = (B: BooksRegister, state: string, action: string): string | null => B.bills.moves[state]?.[action] ?? null;
export function approvers(B: BooksRegister, amount: number, rules?: BooksRegister["bills"]["approval"]): string[] {
  for (const r of rules ?? B.bills.approval) if (r.up_to_minor === null || amount <= r.up_to_minor) return [...r.roles];
  return [];
}
export const mayApprove = (preparer: string | null, approver: string | null | undefined): boolean => approver != null && approver !== preparer;

export interface ItemLine { sku: string; qty: number; price_minor?: number }
export function match3(po: readonly ItemLine[], received: readonly ItemLine[], bill: readonly ItemLine[], toleranceBp = 0) {
  const bySku = (lines: readonly ItemLine[]): Map<string, { qty: number; price: number }> => {
    const m = new Map<string, { qty: number; price: number }>();
    for (const l of lines) { const o = m.get(l.sku) ?? { qty: 0, price: l.price_minor ?? 0 }; o.qty += l.qty; m.set(l.sku, o); }
    return m;
  };
  const p = bySku(po), r = bySku(received), b = bySku(bill);
  const issues: { sku: string; issue: string }[] = [];
  for (const [sku, l] of b) {
    const pp = p.get(sku), rr = r.get(sku);
    if (!pp) { issues.push({ sku, issue: "not_ordered" }); continue; }
    if (!rr) { issues.push({ sku, issue: "not_received" }); continue; }
    if (l.qty > rr.qty || l.qty > pp.qty) issues.push({ sku, issue: "qty_over" });
    if (big(l.price) * 10000n > big(pp.price) * big(10000 + toleranceBp)) issues.push({ sku, issue: "price_over" });
  }
  return { ok: !issues.length, issues };
}
export const earlyDiscount = (amount: number, rateBp: number, withinDays: number, paidAfterDays: number): number =>
  paidAfterDays >= 0 && paidAfterDays <= withinDays ? mulDiv(amount, rateBp, 10000) : 0;

// ---- staff spending ----------------------------------------------------------------------------------------------------------
export const mileage = (kmThousandths: number, rate: number): number => mulDiv(kmThousandths, rate, 1000);
export const allowance = (days: number, rate: number): number => days * rate;
export interface Dated { id: string; amount: number; day: number; ref?: string }
export function cardMatch(B: BooksRegister, spends: readonly Dated[], receipts: readonly Dated[], days?: number) {
  const lim = days ?? B.expenses.card_match_days;
  const used = new Set<number>(), matched: [string, string][] = [], missing: string[] = [];
  for (const s of spends) {
    let best: [number, number] | null = null;
    receipts.forEach((r, i) => {
      if (used.has(i) || r.amount !== s.amount) return;
      const gap = Math.abs(r.day - s.day);
      if (gap <= lim && (best === null || gap < best[0])) best = [gap, i];
    });
    if (best === null) missing.push(s.id);
    else { const i = (best as [number, number])[1]; used.add(i); matched.push([s.id, receipts[i]!.id]); }
  }
  return { matched, missing };
}

// ---- assets and loans --------------------------------------------------------------------------------------------------------
export function depreciation(cost: number, residual: number, years: number, method = "straight_line", rateBp = 0): number[] {
  if (years <= 0 || residual > cost) return [];
  if (method === "straight_line") {
    const base = Math.floor((cost - residual) / years), out = Array<number>(years).fill(base);
    out[years - 1] = out[years - 1]! + (cost - residual) - base * years;
    return out;
  }
  if (method === "reducing_balance") {
    let book = cost; const out: number[] = [];
    for (let y = 0; y < years; y++) {
      const amt = y === years - 1 ? book - residual : Math.min(mulDiv(book, rateBp, 10000), book - residual);
      out.push(amt); book -= amt;
    }
    return out;
  }
  throw new Error("unknown method");
}
export function disposal(cost: number, soFar: number, proceeds: number, method = "bank"): Line[] {
  const lines: Line[] = [];
  if (proceeds) lines.push([CASH_BY_METHOD[method] ?? "1020", proceeds, 0]);
  if (soFar) lines.push(["1510", soFar, 0]);
  lines.push(["1500", 0, cost]);
  const diff = proceeds + soFar - cost;
  if (diff > 0) lines.push(["4200", 0, diff]); else if (diff < 0) lines.push(["6900", -diff, 0]);
  return lines;
}
export interface LoanRow { month: number; payment: number; interest: number; principal: number; balance: number }
export function loanSchedule(principal: number, annualBp: number, months: number): LoanRow[] {
  if (months <= 0) return [];
  const rows: LoanRow[] = [];
  let bal = principal;
  if (annualBp === 0) {
    split(principal, months).forEach((part, i) => { bal -= part; rows.push({ month: i + 1, payment: part, interest: 0, principal: part, balance: bal }); });
    return rows;
  }
  const a = big(annualBp), b = 120000n, g = (b + a) ** big(months);
  const payment = Number(rdBig(big(principal) * a * g, b * (g - b ** big(months))));
  for (let m = 1; m <= months; m++) {
    const interest = Number(rdBig(big(bal) * a, b));
    const princ = m === months ? bal : payment - interest;
    bal -= princ;
    rows.push({ month: m, payment: princ + interest, interest, principal: princ, balance: bal });
  }
  return rows;
}
export function loanLines(row: LoanRow, method = "bank"): Line[] {
  const lines: Line[] = [["2600", row.principal, 0]];
  if (row.interest) lines.push(["6600", row.interest, 0]);
  lines.push([CASH_BY_METHOD[method] ?? "1020", 0, row.payment]);
  return lines;
}

// ---- dates, repeating and reversing ------------------------------------------------------------------------------------------
const parse = (s: string): [number, number, number] => { const [y, m, d] = s.split("-").map(Number); return [y!, m!, d!]; };
const iso = (y: number, m: number, d: number): string => `${String(y).padStart(4, "0")}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
export const daysInMonth = (y: number, m: number): number => new Date(Date.UTC(y, m, 0)).getUTCDate();
/** A date as a whole day number, and back (UTC, so no time zone moves a day). */
export const dayNumber = (s: string): number => { const [y, m, d] = parse(s); return Math.round(Date.UTC(y, m - 1, d) / 86400000); };
export const fromDayNumber = (n: number): string => { const t = new Date(n * 86400000); return iso(t.getUTCFullYear(), t.getUTCMonth() + 1, t.getUTCDate()); };
const addDays = (s: string, n: number): string => { const [y, m, d] = parse(s); const t = new Date(Date.UTC(y, m - 1, d + n)); return iso(t.getUTCFullYear(), t.getUTCMonth() + 1, t.getUTCDate()); };
export function repeatDates(start: string, every: string, count: number): string[] {
  if (every === "week") return Array.from({ length: count }, (_, i) => addDays(start, 7 * i));
  const step = ({ month: 1, quarter: 3, year: 12 } as Record<string, number>)[every];
  if (!step) throw new Error("unknown repeat");
  const [y0, m0, d0] = parse(start), end = d0 === daysInMonth(y0, m0);
  return Array.from({ length: count }, (_, i) => {
    const mm = m0 - 1 + step * i, y = y0 + Math.floor(mm / 12), m = (mm % 12) + 1, last = daysInMonth(y, m);
    return iso(y, m, end ? last : Math.min(d0, last));
  });
}
export const reversalDate = (date: string): string => addDays(date, 1);
export const reverse = (lines: readonly Line[]): Line[] => lines.map(([a, dr, cr]) => [a, cr, dr]);
export const mayPost = (date: string, lock?: string | null): boolean => lock == null || date > lock;
export const twoPerson = (B: BooksRegister, kind: string, preparer: string, approver?: string | null): { needed: boolean; ok: boolean } =>
  B.two_person.kinds.includes(kind) ? { needed: true, ok: approver != null && approver !== preparer } : { needed: false, ok: true };
export const closeMissing = (B: BooksRegister, done: readonly string[]): string[] => B.closing.checklist.filter((c) => !done.includes(c));
export function yearEndLines(B: BooksRegister, chart: Record<string, Account>, tb: Record<string, number>): Line[] {
  const lines: Line[] = []; let profit = 0;
  for (const acct of Object.keys(tb).sort()) {
    const bal = tb[acct]!, t = chart[acct]!.type;
    if (!bal || (t !== "income" && t !== "expense")) continue;
    if (t === "income") { lines.push(bal > 0 ? [acct, bal, 0] : [acct, 0, -bal]); profit += bal; }
    else { lines.push(bal > 0 ? [acct, 0, bal] : [acct, -bal, 0]); profit -= bal; }
  }
  const keep = B.closing.year_end_account;
  if (profit > 0) lines.push([keep, 0, profit]); else if (profit < 0) lines.push([keep, -profit, 0]);
  return lines;
}

// ---- banks -------------------------------------------------------------------------------------------------------------------
export function bankMatch(B: BooksRegister, lines: readonly Dated[], items: readonly Dated[], days?: number) {
  const lim = days ?? B.bank.match_days;
  const used = new Set<number>(), matched: [string, string][] = [], unmatched: string[] = [];
  for (const ln of lines) {
    let best: [number, number, number] | null = null;
    items.forEach((it, i) => {
      if (used.has(i) || it.amount !== ln.amount) return;
      const gap = Math.abs(it.day - ln.day);
      if (gap > lim) return;
      const ref = !!it.ref && (ln.ref ?? "").includes(it.ref);
      const key: [number, number, number] = [ref ? 0 : 1, gap, i];
      if (best === null || key[0] < best[0] || (key[0] === best[0] && (key[1] < best[1] || (key[1] === best[1] && key[2] < best[2])))) best = key;
    });
    if (best === null) unmatched.push(ln.id);
    else { const i = (best as [number, number, number])[2]; used.add(i); matched.push([ln.id, items[i]!.id]); }
  }
  return { matched, unmatched };
}

// ---- statements --------------------------------------------------------------------------------------------------------------
const groupSum = (chart: Record<string, Account>, tb: Record<string, number>, group: string): number =>
  Object.entries(tb).reduce((s, [a, b]) => chart[a]!.group === group ? s + (chart[a]!.contra ? -b : b) : s, 0);
export function statements(chart: Record<string, Account>, tb: Record<string, number>) {
  const g = (x: string): number => groupSum(chart, tb, x);
  const income = g("income"), other = g("other_income"), cos = g("cost_of_sales"), exp = g("expense");
  const profit = income + other - cos - exp;
  const cash = g("cash"), cur = g("current_asset"), noncur = g("non_current_asset");
  const lc = g("current_liability"), ln = g("non_current_liability"), eq = g("equity");
  const assets = cash + cur + noncur, liabilities = lc + ln;
  return { income, other_income: other, cost_of_sales: cos, gross: income - cos, expenses: exp, profit, cash, current_assets: cur, non_current_assets: noncur, assets,
    current_liabilities: lc, non_current_liabilities: ln, liabilities, equity: eq, equity_with_profit: eq + profit, balanced: assets === liabilities + eq + profit };
}
export interface Entry { lines: readonly Line[] }
export function trialBalance(chart: Record<string, Account>, entries: readonly Entry[]): Record<string, number> {
  const tb: Record<string, number> = {};
  for (const e of entries) for (const [a, dr, cr] of e.lines) {
    const acc = chart[a]!, debitNormal = (acc.type === "asset" || acc.type === "expense") !== !!acc.contra;
    tb[a] = (tb[a] ?? 0) + (debitNormal ? dr - cr : cr - dr);
  }
  return tb;
}
export function cashFlow(B: BooksRegister, chart: Record<string, Account>, entries: readonly Entry[]) {
  const groups = B.statements.cash_flow_groups;
  const out = { operating: 0, investing: 0, financing: 0, net: 0 };
  for (const e of entries) {
    const move = e.lines.reduce((s, [a, dr, cr]) => chart[a]!.group === "cash" ? s + dr - cr : s, 0);
    if (!move) continue;
    const others = new Set(e.lines.map(([a]) => chart[a]!.group).filter((g) => g !== "cash"));
    let kind: "operating" | "investing" | "financing" = "operating";
    for (const k of ["investing", "financing"] as const) if ((groups[k] ?? []).some((g) => others.has(g))) { kind = k; break; }
    out[kind] += move;
  }
  out.net = out.operating + out.investing + out.financing;
  return out;
}
export function equityChanges(chart: Record<string, Account>, opening: number, entries: readonly Entry[]) {
  const st = statements(chart, trialBalance(chart, entries));
  return { opening, profit: st.profit, contributions: st.equity, closing: opening + st.profit + st.equity };
}

// ---- currencies and stock ----------------------------------------------------------------------------------------------------
export interface OpenItem { id: string; foreign_minor: number; booked_minor: number; side: "owed_to_us" | "we_owe" }
export function revalue(items: readonly OpenItem[], num: number, den: number) {
  let rec = 0, pay = 0;
  const out = items.map((it) => {
    const nw = mulDiv(it.foreign_minor, num, den), diff = nw - it.booked_minor;
    if (it.side === "owed_to_us") rec += diff; else pay += diff;
    return { id: it.id, new_minor: nw, gain: it.side === "owed_to_us" ? diff : -diff };
  });
  const lines: Line[] = [];
  if (rec) lines.push(rec > 0 ? ["1100", rec, 0] : ["1100", 0, -rec]);
  if (pay) lines.push(pay > 0 ? ["2000", 0, pay] : ["2000", -pay, 0]);
  const g = rec - pay;
  if (g > 0) lines.push(["4400", 0, g]); else if (g < 0) lines.push(["6700", -g, 0]);
  return { items: out, gain: g, lines };
}
export interface Move { kind: "in" | "out"; qty: number; unit_cost_minor?: number; extra_minor?: number }
export function stockCost(moves: readonly Move[], method = "fifo") {
  const batches: [number, number][] = [];
  let totalQ = 0, totalV = 0, cogs = 0, short = 0;
  const outs: number[] = [];
  for (const mv of moves) {
    if (mv.kind === "in") {
      const v = mulDiv(mv.qty, mv.unit_cost_minor ?? 0, 1000) + (mv.extra_minor ?? 0);
      batches.push([mv.qty, v]); totalQ += mv.qty; totalV += v; continue;
    }
    let want = mv.qty, cost = 0;
    if (method === "average") {
      const take = Math.min(want, totalQ);
      const part = take === totalQ ? totalV : totalQ ? mulDiv(totalV, take, totalQ) : 0;
      totalQ -= take; totalV -= part; cost = part; short += want - take;
    } else {
      while (want && batches.length) {
        const [q, v] = batches[0]!, take = Math.min(want, q), part = take === q ? v : mulDiv(v, take, q);
        cost += part; want -= take;
        if (take === q) batches.shift(); else batches[0] = [q - take, v - part];
      }
      short += want;
      totalQ = batches.reduce((s, b) => s + b[0], 0); totalV = batches.reduce((s, b) => s + b[1], 0);
    }
    cogs += cost; outs.push(cost);
  }
  return { cogs, outs, qty: totalQ, value: totalV, short };
}

// ---- groups ------------------------------------------------------------------------------------------------------------------
export interface GroupEntity { id: string; tb: Record<string, number>; num: number; den: number; share_bp?: number }
export function consolidate(B: BooksRegister, chart: Record<string, Account>, entities: readonly GroupEntity[], intercompanySales = 0) {
  const combined: Record<string, number> = {};
  let others = 0;
  for (const en of entities) {
    const t: Record<string, number> = {};
    for (const [a, b] of Object.entries(en.tb)) t[a] = mulDiv(b, en.num, en.den);
    for (const [a, b] of Object.entries(t)) combined[a] = (combined[a] ?? 0) + b;
    if ((en.share_bp ?? 10000) < 10000) others += mulDiv(statements(chart, t).equity_with_profit, 10000 - en.share_bp!, 10000);
  }
  const [a, b] = B.group.intercompany_accounts as [string, string];
  const difference = (combined[a] ?? 0) - (combined[b] ?? 0);
  delete combined[a]; delete combined[b];
  if (intercompanySales) { combined["4000"] = (combined["4000"] ?? 0) - intercompanySales; combined["5000"] = (combined["5000"] ?? 0) - intercompanySales; }
  const tb: Record<string, number> = {};
  for (const k of Object.keys(combined).sort()) if (combined[k]) tb[k] = combined[k]!;
  return { tb, difference, others_share: others };
}
export interface GroupInvoice { from: string; to: string; number: string; lines: unknown[]; total_minor: number; currency: string }
export const mirror = (inv: GroupInvoice) => ({ supplier: inv.from, entity: inv.to, ref: inv.number, lines: inv.lines, total_minor: inv.total_minor,
  currency: inv.currency, source: "group_mirror", state: "awaiting_approval" });

// ---- splitting the books and kinds of entity ---------------------------------------------------------------------------------
export const dimsOk = (B: BooksRegister, dims: Record<string, unknown>): boolean => Object.keys(dims).every((k) => B.dimensions.kinds.includes(k));
export const fundSpendOk = (fund: { restricted?: boolean; purpose?: string }, purpose: string): boolean => !fund.restricted || fund.purpose === purpose;
export const available = (budget: number, committed: number, spent: number): number => budget - committed - spent;
export function budgetVsActual(budgets: Record<string, number>, actuals: Record<string, number>) {
  return [...new Set([...Object.keys(budgets), ...Object.keys(actuals)])].sort().map((k) => {
    const b = budgets[k] ?? 0, a = actuals[k] ?? 0;
    return { key: k, budget: b, actual: a, diff: a - b, used_bp: b > 0 ? mulDiv(a, 10000, b) : null };
  });
}
export const entityTools = (B: BooksRegister, kind: string): string[] => [...(B.entity_tools[kind] ?? [])];
