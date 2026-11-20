/** LynkAssist's trust layer (ASSIST UPDATE, master blueprint 75; build section 4 step C3a): the TypeScript port of
 *  core/assist_trust.py, checked against contract/vectors/assist-trust.v1.json. The register travels in
 *  ts/src/assisttrust.generated.ts (python3 tools/assist_trust_vectors.py). Rules are enforced here, never by the AI's judgement. */
import type { ChatRegister } from "./chat.js";
import { mask } from "./chat.js";

export interface TrustRegister {
  certainty: { levels: string[]; words: Record<string, string> };
  not_adviser: { topics: string[]; words: string };
  unconfirmed: { words: string };
  content: { instruction_sources: string[]; content_sources: string[] };
  memory: { kinds: string[]; scopes: string[]; sensitive_unless_asked: string[]; max_items: number; role_rank: Record<string, number> };
  safety: {
    preview_classes: string[]; bulk: { from: number; sample: number };
    second_approver: { items_over: number; amount_over_minor: number; approver_roles: string[] };
    plans: { states: string[]; next: Record<string, string[]> }; later: { max_days: number }; outcomes: string[];
  };
  warnings: { pace: Record<string, number>; never_in: string[]; checks: Record<string, { service: string; words: string; fix: string; build_section: string }> };
  ask_about: { targets: string[]; max_rows: number; hold_ms: number };
  quality: { metrics: Record<string, "up" | "down">; max_drop_bp: number; language_bar: { min_samples: number; solved_alone_min_bp: number; wrong_max_bp: number };
    new_skill: { starts: string; act_after: { runs: number; accepted_min_bp: number; wrong_max_bp: number } }; first_words_ms: number };
  [k: string]: unknown;
}
export type Sure = "certain" | "likely" | "not_sure" | "dont_know";

// ---- better answers --------------------------------------------------------------------------------------------------------
export function certainty(o: { sources?: number; estimate?: boolean; missing?: boolean; disagree?: boolean; unconfirmed?: boolean; checked?: boolean }): Sure {
  if ((o.sources ?? 0) <= 0) return "dont_know";
  if (o.disagree || o.unconfirmed || o.checked === false) return "not_sure";
  if (o.estimate || o.missing) return "likely";
  return "certain";
}
export interface Work { ok: boolean; total: number | null; currency: string | null; checked: boolean; why: string }
/** A figure from its parts: integer minor units of one currency, added up twice in two orders; a figure that fails is never shown. */
export function work(parts: readonly { minor: unknown; currency?: string }[]): Work {
  const no = (why: string): Work => ({ ok: false, total: null, currency: null, checked: false, why });
  if (!parts.length) return no("no_records");
  const curs = new Set(parts.map((p) => p.currency));
  if (curs.size !== 1) return no("mixed_currencies");
  if (parts.some((p) => typeof p.minor !== "number" || !Number.isSafeInteger(p.minor))) return no("not_whole_minor_units");
  const vals = parts.map((p) => p.minor as number);
  let first = 0; for (const v of vals) first += v;
  let second = 0; for (let i = vals.length - 1; i >= 0; i--) second += vals[i]!;
  if (first !== second) return no("checks_differ");
  return { ok: true, total: first, currency: [...curs][0] ?? null, checked: true, why: "worked_out_twice" };
}
export const needsNotAdviser = (T: TrustRegister, topic: string): boolean => T.not_adviser.topics.includes(topic);

// ---- cannot be tricked -----------------------------------------------------------------------------------------------------
export function mayAct(T: TrustRegister, source: string): { ok: boolean; why: string } {
  if (T.content.instruction_sources.includes(source)) return { ok: true, why: "person" };
  return { ok: false, why: T.content.content_sources.includes(source) ? "content_not_instructions" : "unknown_source" };
}

// ---- memory with control ---------------------------------------------------------------------------------------------------
export function remember(T: TrustRegister, C: ChatRegister, o: { kind: string; scope: string; text: string; ctx_scope: string; memory_on?: boolean; asked?: boolean; sensitive?: readonly string[]; count?: number; code_words?: readonly string[] }): { keep: boolean; why: string } {
  const m = T.memory;
  if (o.memory_on === false) return { keep: false, why: "memory_off" };
  if (!m.kinds.includes(o.kind) || !m.scopes.includes(o.scope) || o.scope !== o.ctx_scope) return { keep: false, why: "kept_apart" };
  if (mask(C, o.text, o.code_words ?? []).found.length) return { keep: false, why: "never_secrets" };
  if ((o.sensitive ?? []).some((s) => m.sensitive_unless_asked.includes(s)) && !o.asked) return { keep: false, why: "sensitive_not_asked" };
  if ((o.count ?? 0) >= m.max_items) return { keep: false, why: "full" };
  return { keep: true, why: "kept" };
}
export function recall(T: TrustRegister, items: readonly { id: string; scope: string; role_min?: string }[], scope: string, role: string): string[] {
  const rank = T.memory.role_rank, mine = rank[role] ?? 0;
  return items.filter((i) => i.scope === scope && (rank[i.role_min ?? "cashier"] ?? 0) <= mine).map((i) => i.id);
}

// ---- doing things safely ---------------------------------------------------------------------------------------------------
export function effectiveLimit(registerLimit: number | null | undefined, ownerLimit: number | null | undefined): number | null {
  const vals = [registerLimit, ownerLimit].filter((v): v is number => v !== null && v !== undefined);
  return vals.length ? Math.min(...vals) : null;
}
export function bulk(T: TrustRegister, items: number): { sample: number; show_all: boolean } {
  const b = T.safety.bulk;
  return { sample: items >= b.from ? Math.min(b.sample, items) : items, show_all: items < b.from };
}
export function isBig(T: TrustRegister, items = 0, amountMinor?: number | null, ownerAmount?: number | null): boolean {
  const s = T.safety.second_approver;
  const limit = effectiveLimit(s.amount_over_minor, ownerAmount) ?? s.amount_over_minor;
  return items > s.items_over || (amountMinor !== undefined && amountMinor !== null && amountMinor > limit);
}
export interface GuardIn { register_needs: string; register_run: boolean; cls: string | null; source?: string; paused?: boolean; role_off?: boolean; practice?: boolean; confirmed?: boolean;
  items?: number; amount_minor?: number | null; max_items?: number | null; max_amount_minor?: number | null; owner_amount?: number | null; asker?: string | null; approver?: string | null; approver_role?: string | null }
export interface GuardOut { outcome: string; why: string; sample: number; show_all: boolean }
/** The first step still to do for one action, after the register's own decision. */
export function guard(T: TrustRegister, g: GuardIn): GuardOut {
  const items = g.items ?? 0;
  const out = (outcome: string, why: string): GuardOut => ({ outcome, why, ...bulk(T, items) });
  const src = mayAct(T, g.source ?? "person");
  if (!src.ok) return out("content_not_instructions", src.why);
  if (g.paused) return out("paused", "lynkassist_actions_paused");
  if (g.role_off) return out("role_off", "owner_switched_off_for_role");
  const amt = g.amount_minor ?? null;
  if ((g.max_items != null && items > g.max_items) || (g.max_amount_minor != null && amt !== null && amt > g.max_amount_minor)) return out("over_limit", "over_owner_limit");
  if (["refused", "hand_over", "ask_owner", "fresh_check"].includes(g.register_needs)) return out("register", g.register_needs);
  if (g.cls !== null && T.safety.preview_classes.includes(g.cls) && !g.confirmed) return out("preview", "before_and_after_first");
  if (isBig(T, items, amt, g.owner_amount ?? null)) {
    const s = T.safety.second_approver;
    if (g.approver == null || g.approver === g.asker || !s.approver_roles.includes(g.approver_role ?? "")) return out("second_approver", "another_person_confirms");
  }
  if (g.practice) return out("practice", "nothing_real_changes");
  if (!g.register_run && g.register_needs !== "confirm") return out("register", g.register_needs);
  return out("run", "allowed");
}
export const planMove = (T: TrustRegister, from: string, to: string): boolean => (T.safety.plans.next[from] ?? []).includes(to);
export const laterOk = (T: TrustRegister, days: number): boolean => days > 0 && days <= T.safety.later.max_days;

// ---- help before being asked -----------------------------------------------------------------------------------------------
export function warning(T: TrustRegister, check: string, o: { screen?: string; shown_today?: number; pace?: string; told?: boolean; fine?: boolean } = {}): { show: boolean; why: string; words?: string; fix?: string } {
  const w = T.warnings, c = w.checks[check];
  if (!c) return { show: false, why: "not_registered" };
  if (w.never_in.includes(o.screen ?? "home")) return { show: false, why: "protected_screen" };
  if (o.told || o.fine) return { show: false, why: "told_once" };
  if ((o.shown_today ?? 0) >= (w.pace[o.pace ?? "normal"] ?? w.pace["normal"] ?? 5)) return { show: false, why: "daily_limit" };
  return { show: true, why: "show", words: c.words, fix: c.fix };
}
export function askAbout(T: TrustRegister, target: string, rows = 1): { ok: boolean; why: string } {
  const a = T.ask_about;
  if (!a.targets.includes(target)) return { ok: false, why: "not_a_target" };
  if (target === "rows" && !(rows >= 1 && rows <= a.max_rows)) return { ok: false, why: "too_many_rows" };
  return { ok: true, why: "ask" };
}

// ---- quality you can measure -----------------------------------------------------------------------------------------------
export function gate(T: TrustRegister, before: Record<string, number>, after: Record<string, number>): { pass: boolean; worse: string[] } {
  const worse: string[] = [];
  for (const [m, dir] of Object.entries(T.quality.metrics)) {
    const b = before[m], a = after[m];
    if (b === undefined || a === undefined) continue;
    if ((dir === "up" ? b - a : a - b) > T.quality.max_drop_bp) worse.push(m);
  }
  return { pass: !worse.length, worse };
}
export function languageReady(T: TrustRegister, samples: number, solvedAloneBp: number, wrongBp: number): boolean {
  const b = T.quality.language_bar;
  return samples >= b.min_samples && solvedAloneBp >= b.solved_alone_min_bp && wrongBp <= b.wrong_max_bp;
}
export function skillLevel(T: TrustRegister, runs: number, acceptedBp: number, wrongBp: number): string {
  const a = T.quality.new_skill.act_after;
  return runs >= a.runs && acceptedBp >= a.accepted_min_bp && wrongBp <= a.wrong_max_bp ? "act" : T.quality.new_skill.starts;
}
