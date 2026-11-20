/** LynkCRM's rules (OFFICE UPDATE, master blueprint 66.4; section 4 step D3): the TypeScript port of core/crm.py, checked against
 *  contract/vectors/crm.v1.json. The register travels in ts/src/crm.generated.ts (python3 tools/crm_vectors.py).
 *  Contact details are vault references only; lead scores are labelled suggestions. */
import { mulDiv, dayNumber, fromDayNumber } from "./books.js";

export interface CrmRegister {
  kinds: Record<string, string[]>;
  relations: { kinds: string[] };
  fields: { limits: Record<string, number | null> };
  pipelines: { default_chance_bp: Record<string, number>; moves: Record<string, string[]>; reasons: Record<string, string[]> };
  lead_score: { signals: Record<string, number> };
  access: { default: string };
  cases: { priorities: Record<string, number> };
  timeline: { sources: string[] };
  data_requests: { default_days: number };
  sensitive: { kinds: string[] };
  [k: string]: unknown;
}
type Val = string | number | boolean | null | undefined | unknown[];
export interface CrmRecord { id: string; fields?: Record<string, Val>; tags?: string[] }
export interface Cond { field?: string; op: string; value?: unknown }

// ---- who is recorded ---------------------------------------------------------------------------------------------------------
export function kindsFor(C: CrmRegister, entityKind: string, own: readonly string[] = []): string[] {
  const base = C.kinds[entityKind] ?? [];
  return [...base, ...own.filter((k) => !base.includes(k))];
}
export const relationOk = (C: CrmRegister, relation: string, entityKind: string): boolean =>
  C.relations.kinds.includes(relation) && (relation !== "guardian_of" || entityKind === "school");
export const fieldLimit = (C: CrmRegister, tier: string): number | null => (tier in C.fields.limits ? C.fields.limits[tier]! : 0);
export function fieldValueOk(ftype: string, value: unknown): boolean {
  if (value === null || value === undefined) return true;
  switch (ftype) {
    case "text": return typeof value === "string" && [...value].length <= 500;
    case "number": case "money": return typeof value === "number" && Number.isInteger(value);
    case "date": return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);
    case "yes_no": return typeof value === "boolean";
    case "choice": return typeof value === "string" && value !== "";
    default: return false;
  }
}
export const requiredMissing = (fields: readonly { id: string; required?: boolean }[], values: Record<string, unknown>): string[] =>
  fields.filter((f) => f.required && (values[f.id] === null || values[f.id] === undefined || values[f.id] === "" || (Array.isArray(values[f.id]) && (values[f.id] as unknown[]).length === 0))).map((f) => f.id);

// ---- segments ----------------------------------------------------------------------------------------------------------------
function cond(r: CrmRecord, c: Cond): boolean {
  const op = c.op, want = c.value;
  if (op === "has_tag") return (r.tags ?? []).includes(want as string);
  const v = r.fields?.[c.field ?? ""];
  if (op === "missing") return v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0);
  if (v === null || v === undefined) return false;
  if (op === "eq") return v === want;
  if (op === "neq") return v !== want;
  if (op === "in") return Array.isArray(want) && want.includes(v);
  if (op === "contains") return typeof v === "string" && typeof want === "string" && v.toLowerCase().includes(want.toLowerCase());
  if (typeof v === "boolean" || (typeof v !== "number" && typeof v !== "string") || typeof v !== typeof want) return false;
  const a = v as number | string, b = want as number | string;
  return op === "gt" ? a > b : op === "gte" ? a >= b : op === "lt" ? a < b : op === "lte" ? a <= b : false;
}
export const segment = (records: readonly CrmRecord[], conditions: readonly Cond[]): string[] => records.filter((r) => conditions.every((c) => cond(r, c))).map((r) => r.id);

// ---- selling -----------------------------------------------------------------------------------------------------------------
export const stageMove = (C: CrmRegister, from: string, to: string): boolean => (C.pipelines.moves[from] ?? []).includes(to);
export const closeOk = (C: CrmRegister, stage: string, reason: string | null): boolean =>
  stage !== "won" && stage !== "lost" ? true : (C.pipelines.reasons[stage] ?? []).includes(reason ?? "");
export function forecast(C: CrmRegister, deals: readonly { id: string; amount: number; stage: string }[], chances: Record<string, number> = {}) {
  const ch: Record<string, number> = { ...C.pipelines.default_chance_bp, ...chances };
  const rows = deals.filter((d) => d.stage !== "won" && d.stage !== "lost").map((d) => ({ id: d.id, weighted: mulDiv(d.amount, ch[d.stage]!, 10000) }));
  return { deals: rows, total: rows.reduce((s, r) => s + r.weighted, 0) };
}
export function leadScore(C: CrmRegister, signals: readonly string[]): { score: number; suggestion: true } {
  const s = signals.reduce((a, x) => a + (C.lead_score.signals[x] ?? 0), 0);
  return { score: Math.max(0, Math.min(100, s)), suggestion: true };
}

// ---- access ------------------------------------------------------------------------------------------------------------------
export interface Viewer { id: string; role: string; team?: string | null }
export function maySee(C: CrmRegister, viewer: Viewer, record: { owner?: string | null; team?: string | null }, visibility?: string): boolean {
  const vis = visibility ?? C.access.default;
  if (viewer.role === "owner" || vis === "all") return true;
  if (record.owner === viewer.id) return true;
  if (vis === "own") return viewer.role === "manager" && record.team != null && record.team === viewer.team;
  return record.team != null && record.team === viewer.team;
}
export const visibleFields = (fields: readonly { id: string; hidden_from?: string[] }[], role: string): string[] =>
  fields.filter((f) => !(f.hidden_from ?? []).includes(role)).map((f) => f.id);

// ---- service -----------------------------------------------------------------------------------------------------------------
export const caseDue = (C: CrmRegister, openedHour: number, priority: string, pausedHours = 0, ownHours: number | null = null): number =>
  openedHour + (ownHours ?? C.cases.priorities[priority]!) + pausedHours;
export const caseLate = (C: CrmRegister, nowHour: number, openedHour: number, priority: string, answered = false, pausedHours = 0, ownHours: number | null = null): boolean =>
  !answered && nowHour > caseDue(C, openedHour, priority, pausedHours, ownHours);

// ---- the one full picture ----------------------------------------------------------------------------------------------------
export function timeline(C: CrmRegister, items: readonly { source: string; at: string; id: string }[], linksOn: readonly string[], roleSources: readonly string[] | null = null): string[] {
  return items.filter((i) => C.timeline.sources.includes(i.source) && linksOn.includes(i.source) && (roleSources === null || roleSources.includes(i.source)))
    .sort((a, b) => (a.at < b.at ? 1 : a.at > b.at ? -1 : a.id < b.id ? 1 : a.id > b.id ? -1 : 0)).map((i) => i.id);
}

// ---- clean records -----------------------------------------------------------------------------------------------------------
export const normalise = (s: string | null | undefined): string =>
  (s ?? "").normalize("NFKD").replace(/\p{Mn}/gu, "").toLowerCase().split(/\s+/u).filter(Boolean).join(" ");
export interface Person { id: string; email?: string; phone_fp?: string; name?: string; org?: string; created: string; updated?: string;
  fields?: Record<string, Val>; tags?: string[]; activities?: string[] }
export function matchKeys(r: Person): string[] {
  const keys: string[] = [];
  if (r.email) keys.push("e:" + r.email.trim().toLowerCase());
  if (r.phone_fp) keys.push("p:" + r.phone_fp);
  if (r.name) keys.push("n:" + normalise(r.name) + "|" + normalise(r.org ?? ""));
  return keys;
}
export function duplicates(records: readonly Person[]): string[][] {
  const parent = new Map<string, string>(records.map((r) => [r.id, r.id]));
  const find = (x: string): string => { while (parent.get(x) !== x) { parent.set(x, parent.get(parent.get(x)!)!); x = parent.get(x)!; } return x; };
  const first = new Map<string, string>();
  for (const r of records) for (const k of matchKeys(r)) {
    if (first.has(k)) { const a = find(first.get(k)!), b = find(r.id); if (a !== b) parent.set(b, a); }
    else first.set(k, r.id);
  }
  const groups = new Map<string, string[]>();
  for (const r of records) { const g = find(r.id); groups.set(g, [...(groups.get(g) ?? []), r.id]); }
  return [...groups.values()].filter((g) => g.length > 1);
}
const cmp = (a: string, b: string): number => (a < b ? -1 : a > b ? 1 : 0);
export function merge(records: readonly Person[]) {
  const recs = [...records].sort((a, b) => cmp(a.created, b.created) || cmp(a.id, b.id));
  const fields: Record<string, Val> = {};
  for (const r of [...records].sort((a, b) => cmp(a.updated ?? a.created, b.updated ?? b.created) || cmp(a.id, b.id)))
    for (const [k, v] of Object.entries(r.fields ?? {})) if (!(v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0))) fields[k] = v;
  const sorted: Record<string, Val> = {};
  for (const k of Object.keys(fields).sort()) sorted[k] = fields[k];
  return { id: recs[0]!.id, merged: recs.slice(1).map((r) => r.id), tags: [...new Set(records.flatMap((r) => r.tags ?? []))].sort(),
    fields: sorted, activities: records.flatMap((r) => r.activities ?? []).sort() };
}

// ---- consent, data requests, sensitive records -------------------------------------------------------------------------------
export function consentOk(consents: readonly { channel: string; basis: string; withdrawn?: boolean }[], channel: string, marketing = false): boolean {
  const mine = consents.filter((c) => c.channel === channel);
  const last = mine[mine.length - 1];
  if (!last || last.withdrawn) return false;
  return !marketing || last.basis === "asked";
}
export interface CrmPack { office?: { crm?: { request_days?: number | null; sensitive_allowed?: Record<string, boolean | null> | null } | null; [k: string]: unknown } | null; [k: string]: unknown }
export const requestDue = (C: CrmRegister, received: string, pack?: CrmPack | null): string =>
  fromDayNumber(dayNumber(received) + (pack?.office?.crm?.request_days || C.data_requests.default_days));
export function sensitiveAllowed(C: CrmRegister, kind: string, entityKind: string, pack?: CrmPack | null): boolean {
  if (!C.sensitive.kinds.includes(kind)) return true;
  if ((kind === "children" && entityKind === "school") || (kind === "citizens" && entityKind === "public_body")) return true;
  return pack?.office?.crm?.sensitive_allowed?.[kind] === true;
}
