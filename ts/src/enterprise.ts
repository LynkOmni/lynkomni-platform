/** The large-organisation set and the Move in tool (OFFICE UPDATE, master blueprint 66.5 and 66.6; section 4 step D4a): the
 *  TypeScript port of core/enterprise.py, checked against contract/vectors/enterprise.v1.json. The register travels in
 *  ts/src/enterprise.generated.ts (python3 tools/enterprise_vectors.py). These rules only ever make LynkOmni do less. */
import { allocate } from "./books.js";

export interface EnterpriseRegister {
  areas: string[];
  approval_flows: { max_steps: number };
  roles: { base: Record<string, Record<string, string[]>>; kept_apart: [string, string][] };
  directory: { suspend_within_minutes: number };
  move_in: { kinds: Record<string, { columns: string[]; required: string[] }>; max_rows: number };
  [k: string]: unknown;
}
const ACCOUNT_TYPES = ["asset", "liability", "equity", "income", "expense"];

// ---- approval flows ----------------------------------------------------------------------------------------------------------
export interface Step { role: string; from_minor?: number; department?: string | null; stand_in?: string | null }
export function flowSteps(E: EnterpriseRegister, flow: readonly Step[], amount: number, department: string | null = null): Step[] {
  if (flow.length > E.approval_flows.max_steps) throw new Error("too many steps");
  return flow.filter((s) => amount >= (s.from_minor ?? 0) && (s.department == null || s.department === department));
}
export function mayApprove(steps: readonly Step[], approvals: readonly { who: string }[], preparer: string, who: string, role: string, mainAway = false): { ok: boolean; why: string } {
  const n = approvals.length;
  if (n >= steps.length) return { ok: false, why: "no_step_left" };
  if (who === preparer) return { ok: false, why: "preparer" };
  if (approvals.some((a) => a.who === who)) return { ok: false, why: "already_approved" };
  const step = steps[n]!;
  if (role === step.role) return { ok: true, why: "step" };
  if (mainAway && step.stand_in && role === step.stand_in) return { ok: true, why: "stand_in" };
  return { ok: false, why: "wrong_role" };
}

// ---- own roles ---------------------------------------------------------------------------------------------------------------
export function roleProblems(E: EnterpriseRegister, perms: Record<string, string[]>, keptApart = true): { area: string; problem: string; permission?: string }[] {
  const owner = E.roles.base["owner"]!;
  const out: { area: string; problem: string; permission?: string }[] = [];
  for (const area of Object.keys(perms).sort()) {
    if (!E.areas.includes(area)) { out.push({ area, problem: "unknown_area" }); continue; }
    for (const p of perms[area]!) if (!(owner[area] ?? []).includes(p)) out.push({ area, problem: "more_than_owner", permission: p });
    if (keptApart) for (const [a, b] of E.roles.kept_apart) if (perms[area]!.includes(a) && perms[area]!.includes(b)) out.push({ area, problem: "kept_apart", permission: `${a}+${b}` });
  }
  return out;
}
export const can = (perms: Record<string, string[]>, area: string, permission: string): boolean => (perms[area] ?? []).includes(permission);

// ---- charges, holds, keeping, region -----------------------------------------------------------------------------------------
export function splitCharges(total: number, shares: Record<string, number>): Record<string, number> {
  const keys = Object.keys(shares).sort();
  if (keys.reduce((s, k) => s + shares[k]!, 0) !== 10000) throw new Error("shares must add up to 10000");
  const parts = allocate(total, keys.map((k) => shares[k]!));
  const out: Record<string, number> = {};
  keys.forEach((k, i) => { out[k] = parts[i]!; });
  return out;
}
export const mayChange = (held: boolean): boolean => !held;
export const mayDelete = (ageDays: number, policyDays: number | null, lawDays: number | null, held = false): boolean => !held && ageDays >= Math.max(policyDays ?? 0, lawDays ?? 0);
export const dataRegion = (choice: string | null, pack?: { office?: { crm?: { data_region?: string | null } | null } | null } | null): string | null =>
  pack?.office?.crm?.data_region || choice;
export const suspendedBy = (E: EnterpriseRegister, removedMinute: number): number => removedMinute + E.directory.suspend_within_minutes;

// ---- Move in -----------------------------------------------------------------------------------------------------------------
const THOUSANDS = /^-?\d{1,3}(,\d{3})+(\.\d+)?$/;
export function parseAmount(text: unknown, decimals: number): number | null {
  let t = String(text ?? "").trim().replace(/[  _]/g, "");
  if (!t) return null;
  if (THOUSANDS.test(t)) t = t.replace(/,/g, "");
  else if (t.includes(",") && !t.includes(".") && t.split(",").length === 2) t = t.replace(",", ".");
  if (!/^-?\d+(\.\d+)?$/.test(t)) return null;
  const neg = t.startsWith("-");
  const body = t.replace(/^-/, ""), dot = body.indexOf(".");
  const whole = dot < 0 ? body : body.slice(0, dot), frac = dot < 0 ? "" : body.slice(dot + 1);
  if (frac.length > decimals) return null;
  const v = BigInt(whole) * 10n ** BigInt(decimals) + BigInt((frac + "0".repeat(decimals)).slice(0, decimals) || "0");
  const n = Number(neg ? -v : v);
  return n === 0 ? 0 : n;
}
const realDate = (y: number, m: number, d: number): string | null => {
  if (m < 1 || m > 12 || d < 1 || y < 1) return null;
  const t = new Date(Date.UTC(y, m - 1, d));
  if (t.getUTCFullYear() !== y || t.getUTCMonth() !== m - 1 || t.getUTCDate() !== d) return null;
  return `${String(y).padStart(4, "0")}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
};
export function parseDate(text: unknown, fmt = "iso"): string | null {
  const t = String(text ?? "").trim();
  if (fmt === "iso") { const m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(t); return m ? realDate(+m[1]!, +m[2]!, +m[3]!) : null; }
  const m = /^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})$/.exec(t);
  if (!m) return null;
  const a = +m[1]!, b = +m[2]!, y = +m[3]!;
  return fmt === "day_first" ? realDate(y, b, a) : realDate(y, a, b);
}
export interface CheckError { row: number; column: string; issue: string }
export function check(E: EnterpriseRegister, kind: string, header: readonly string[], rows: readonly (readonly unknown[])[], decimals = 2, dateFormat = "iso",
  known: Record<string, readonly string[]> | null = null, accounts: readonly string[] | null = null) {
  const spec = E.move_in.kinds[kind]!;
  const errors: CheckError[] = [];
  let totals: Record<string, number> = {};
  const seen = new Set<string>();
  const missing = spec.required.filter((c) => !header.includes(c));
  for (const c of missing) errors.push({ row: 0, column: c, issue: "missing_column" });
  if (missing.length) return { ok: false, count: rows.length, errors, totals };
  if (rows.length > E.move_in.max_rows) return { ok: false, count: rows.length, errors: [{ row: 0, column: "", issue: "too_many_rows" }], totals };
  const idx = new Map(header.map((c, i) => [c, i] as const));
  const get = (r: readonly unknown[], c: string): string => { const i = idx.get(c); return i !== undefined && i < r.length ? String(r[i] ?? "") : ""; };
  let debit = 0, credit = 0, amount = 0;
  const refCol = ({ chart: "code", customers: "ref", suppliers: "ref", open_invoices: "number", open_bills: "ref", voters: "ref" } as Record<string, string>)[kind];
  rows.forEach((r, i) => {
    const n = i + 1;
    for (const c of spec.required) if (get(r, c).trim() === "") errors.push({ row: n, column: c, issue: "required_empty" });
    if (refCol) { const ref = get(r, refCol).trim(); if (ref && seen.has(ref)) errors.push({ row: n, column: refCol, issue: "duplicate_ref" }); seen.add(ref); }
    if (kind === "voters" && get(r, "weight").trim() && !/^[1-9][0-9]{0,8}$/.test(get(r, "weight").trim())) errors.push({ row: n, column: "weight", issue: "bad_weight" });
    if (kind === "chart" && get(r, "type").trim() && !ACCOUNT_TYPES.includes(get(r, "type"))) errors.push({ row: n, column: "type", issue: "unknown_type" });
    if (kind === "opening_balances") {
      const acct = get(r, "account").trim();
      if (acct && accounts !== null && !accounts.includes(acct)) errors.push({ row: n, column: "account", issue: "unknown_account" });
      const d = get(r, "debit").trim() ? parseAmount(get(r, "debit"), decimals) : 0;
      const c = get(r, "credit").trim() ? parseAmount(get(r, "credit"), decimals) : 0;
      if (d === null || c === null || d < 0 || c < 0) errors.push({ row: n, column: d === null || (d ?? 0) < 0 ? "debit" : "credit", issue: "bad_amount" });
      else if (Boolean(d) === Boolean(c)) errors.push({ row: n, column: "debit", issue: "one_side_only" });
      else { debit += d; credit += c; }
    }
    for (const c of ["issued_on", "due_on", "received_on"]) if (idx.has(c) && get(r, c).trim() && parseDate(get(r, c), dateFormat) === null) errors.push({ row: n, column: c, issue: "bad_date" });
    if (kind === "open_invoices" || kind === "open_bills") {
      const a = parseAmount(get(r, "amount"), decimals);
      if (a === null || a <= 0) { if (get(r, "amount").trim()) errors.push({ row: n, column: "amount", issue: "bad_amount" }); }
      else amount += a;
      const [whoCol, whoKind] = kind === "open_invoices" ? ["customer_ref", "customers"] : ["supplier_ref", "suppliers"];
      const who = get(r, whoCol).trim();
      if (who && known !== null && !(known[whoKind] ?? []).includes(who)) errors.push({ row: n, column: whoCol, issue: "unknown_ref" });
    }
  });
  if (kind === "opening_balances") { totals = { debit, credit }; if (debit !== credit) errors.push({ row: 0, column: "", issue: "not_balanced" }); }
  if (kind === "open_invoices" || kind === "open_bills") totals = { amount };
  return { ok: !errors.length, count: rows.length, errors, totals };
}
