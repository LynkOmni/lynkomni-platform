/** LynkInv's rules (OFFICE UPDATE, master blueprint 66.3; section 4 step D2a): the TypeScript port of core/invoices.py, checked
 *  against contract/vectors/invoices.v1.json. The register travels in ts/src/invoices.generated.ts (python3 tools/invoices_vectors.py).
 *  Built on LynkAcc's rules (ts/src/books.ts). Money is integer minor units; quantities integer thousandths. */
import { roundDiv, mulDiv, split, allocate, taxLine, repeatDates, daysInMonth, dayNumber, fromDayNumber, type Tax } from "./books.js";

export interface InvoicesRegister {
  documents: Record<string, { id: string; posts: boolean; from: string[]; word: string; only_where?: string }>;
  moves: Record<string, Record<string, string>>;
  terms: { library: Record<string, number | string>; default: string };
  reminders: { steps: { step: string; after_due_days: number }[]; before_due_days: number };
  ageing: { buckets: { id: string; up_to: number | null }[] };
  instalments: { max: number };
  approval: { default_over_minor: number };
  languages: { max_on_one: number };
  keeping: { default_years: number };
  [k: string]: unknown;
}
export interface Pack { flags?: Record<string, unknown>; office?: { late_fees?: { allowed?: boolean | null; max_rate_bp_year?: number | null; fixed_fee_minor?: number | null };
  e_invoice?: { required?: boolean | null }; keep_years?: number | null; [k: string]: unknown } | null; [k: string]: unknown }

// ---- documents and states ----------------------------------------------------------------------------------------------------
export function docAllowed(I: InvoicesRegister, kind: string, pack?: Pack | null): boolean {
  const d = I.documents[kind];
  if (!d) return false;
  return !d.only_where || (pack?.office as Record<string, unknown> | undefined)?.[d.only_where] === true;
}
export function mayMake(I: InvoicesRegister, from: string | null, to: string, pack?: Pack | null): boolean {
  const d = I.documents[to];
  if (!d || !docAllowed(I, to, pack)) return false;
  return from === null || d.from.includes(from);
}
export const invMove = (I: InvoicesRegister, state: string, action: string): string | null => I.moves[state]?.[action] ?? null;
export const labelWord = (pack?: Pack | null): string => pack?.flags?.["tax_invoice_confirmed"] === true ? "iv_doc_tax_invoice" : "iv_doc_invoice";

// ---- terms and totals --------------------------------------------------------------------------------------------------------
export function dueDate(I: InvoicesRegister, issued: string, term?: string): string {
  const t = I.terms.library[term ?? I.terms.default];
  const [y, m] = issued.split("-").map(Number) as [number, number];
  const pad = (n: number): string => String(n).padStart(2, "0");
  if (t === "eom") return `${String(y).padStart(4, "0")}-${pad(m)}-${pad(daysInMonth(y, m))}`;
  if (t === "eonm") { const ny = y + (m === 12 ? 1 : 0), nm = (m % 12) + 1; return `${String(ny).padStart(4, "0")}-${pad(nm)}-${pad(daysInMonth(ny, nm))}`; }
  if (typeof t !== "number") throw new Error("unknown term");
  return fromDayNumber(dayNumber(issued) + t);
}
export interface InvLine { qty: number; unit_minor: number; discount_minor?: number; taxes?: Tax[] }
export function totals(lines: readonly InvLine[], taxes: readonly Tax[] = [], included = false, discountBp = 0) {
  const out: ReturnType<typeof taxLine>[] = [];
  let net = 0, total = 0, withheld = 0, reverse = 0;
  const byKind: Record<string, number> = {};
  for (const ln of lines) {
    let amount = mulDiv(ln.qty, ln.unit_minor, 1000) - (ln.discount_minor ?? 0);
    amount -= mulDiv(amount, discountBp, 10000);
    const t = taxLine(amount, ln.taxes ?? taxes, included);
    out.push(t);
    net += t.net; total += t.total; withheld += t.withheld; reverse += t.reverse_charge;
    for (const x of t.taxes) byKind[x.kind] = (byKind[x.kind] ?? 0) + x.amount;
  }
  const sorted: Record<string, number> = {};
  for (const k of Object.keys(byKind).sort()) sorted[k] = byKind[k]!;
  return { lines: out, net, taxes: sorted, total, withheld, to_pay: total - withheld, reverse_charge: reverse };
}
export function creditCheck(limit: number | null, openBalance: number, newTotal: number): { warn: boolean; over_by: number } {
  if (limit === null) return { warn: false, over_by: 0 };
  const over = openBalance + newTotal - limit;
  return { warn: over > 0, over_by: Math.max(over, 0) };
}
export const needsApproval = (I: InvoicesRegister, total: number, overMinor?: number | null, preparer?: string | null, named: readonly string[] = []): boolean =>
  total > (overMinor ?? I.approval.default_over_minor) || (preparer != null && named.includes(preparer));

// ---- getting paid on time ----------------------------------------------------------------------------------------------------
export function reminderDue(I: InvoicesRegister, due: string, today: string, sent: readonly string[] = [], promise: string | null = null, disputed = false): string | null {
  const r = I.reminders;
  if (disputed || (promise !== null && today <= promise)) return null;
  const late = dayNumber(today) - dayNumber(due);
  if (late < 0) return -late <= r.before_due_days && !sent.includes("before") ? "before" : null;
  const reached = r.steps.filter((s) => late >= s.after_due_days).map((s) => s.step);
  const last = reached[reached.length - 1];
  return last !== undefined && !sent.includes(last) ? last : null;
}
export function lateFee(amount: number, daysLate: number, pack?: Pack | null, ownerRateBp: number | null = null): { allowed: boolean; fee: number } {
  const lf = pack?.office?.late_fees ?? {};
  if (lf.allowed !== true || daysLate <= 0) return { allowed: lf.allowed === true, fee: 0 };
  let rate = lf.max_rate_bp_year ?? 0;
  if (ownerRateBp !== null) rate = Math.min(rate, ownerRateBp);
  return { allowed: true, fee: (lf.fixed_fee_minor ?? 0) + Number((() => { const n = BigInt(amount) * BigInt(rate) * BigInt(daysLate), d = 3650000n;
    const a = n < 0n ? -n : n, q = (2n * a + d) / (2n * d); return n < 0n ? -q : q; })()) };
}
export interface OpenInv { id: string; outstanding: number; due: string }
export function ageing(I: InvoicesRegister, items: readonly OpenInv[], today: string) {
  const totalsBy: Record<string, number> = {};
  for (const b of I.ageing.buckets) totalsBy[b.id] = 0;
  const rows = items.map((it) => {
    const late = Math.max(dayNumber(today) - dayNumber(it.due), 0);
    const bid = I.ageing.buckets.find((b) => b.up_to === null || late <= b.up_to)!.id;
    totalsBy[bid] = totalsBy[bid]! + it.outstanding;
    return { id: it.id, bucket: bid, days_late: late };
  });
  return { totals: totalsBy, items: rows };
}
export function applyPayment(amount: number, invoices: readonly OpenInv[], order: readonly string[] | null = null) {
  let todo = invoices.filter((i) => i.outstanding > 0);
  if (order && order.length) {
    const pos = new Map(order.map((k, n) => [k, n] as const));
    todo = todo.filter((i) => pos.has(i.id)).sort((a, b) => pos.get(a.id)! - pos.get(b.id)!);
  } else {
    todo = [...todo].sort((a, b) => (a.due < b.due ? -1 : a.due > b.due ? 1 : a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  }
  let left = amount;
  const used: { id: string; amount: number; paid: boolean }[] = [];
  for (const i of todo) {
    if (left <= 0) break;
    const take = Math.min(left, i.outstanding);
    used.push({ id: i.id, amount: take, paid: take === i.outstanding });
    left -= take;
  }
  return { used, credit_balance: left };
}
export function instalments(I: InvoicesRegister, total: number, count: number, start: string, every = "month"): { date: string; amount: number }[] {
  if (count <= 0 || count > I.instalments.max) return [];
  const dates = repeatDates(start, every, count), parts = split(total, count);
  return dates.map((d, i) => ({ date: d, amount: parts[i]! }));
}

// ---- ways to bill ------------------------------------------------------------------------------------------------------------
export function prorate(oldPrice: number, newPrice: number, periodDays: number, daysLeft: number): number {
  if (periodDays <= 0 || daysLeft < 0 || daysLeft > periodDays) throw new Error("days left must be within the period");
  return mulDiv(newPrice - oldPrice, daysLeft, periodDays);
}
export interface Band { up_to: number | null; unit_minor: number }
export function usage(qty: number, bands: readonly Band[], mode = "graduated"): number {
  if (!bands.length || qty <= 0) return 0;
  if (mode === "per_unit") return mulDiv(qty, bands[0]!.unit_minor, 1000);
  if (mode === "volume") { const band = bands.find((b) => b.up_to === null || qty <= b.up_to)!; return mulDiv(qty, band.unit_minor, 1000); }
  let amount = 0, low = 0;
  for (const b of bands) {
    const top = b.up_to === null ? qty : Math.min(qty, b.up_to);
    if (top > low) amount += mulDiv(top - low, b.unit_minor, 1000);
    if (b.up_to === null || qty <= b.up_to) break;
    low = b.up_to;
  }
  return amount;
}
export function stages(total: number, sharesBp: readonly number[]): number[] {
  if (sharesBp.reduce((a, b) => a + b, 0) !== 10000) throw new Error("stage shares must add up to 10000");
  return allocate(total, sharesBp);
}
export const retainerDraw = (balance: number, amount: number) => { const used = Math.min(balance, amount); return { used, left: balance - used, to_invoice: amount - used }; };

// ---- currency, rounding, e-invoices, keeping, languages ----------------------------------------------------------------------
export const toBase = (amount: number, num: number, den: number): number => mulDiv(amount, num, den);
export function cashRound(amount: number, step: number): { amount: number; rounding: number } {
  if (step <= 1) return { amount, rounding: 0 };
  const r = roundDiv(amount, step) * step;
  return { amount: r, rounding: r - amount };
}
export const eInvoiceRequired = (pack?: Pack | null): boolean | null => pack?.office?.e_invoice?.required ?? null;
export const keepYears = (I: InvoicesRegister, pack?: Pack | null): number => pack?.office?.keep_years || I.keeping.default_years;
export const languagesOk = (I: InvoicesRegister, langs: readonly string[]): boolean => langs.length >= 1 && langs.length <= I.languages.max_on_one && new Set(langs).size === langs.length;
