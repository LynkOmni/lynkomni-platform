/** LynkAssist Ask and Resolve in the help button (MASTER UPDATE, master blueprint section 54; build section 1).
 *  The rules are services/assist_register.py's, carried in parts.generated.ts and checked by contract/vectors/parts.v1.json:
 *  an action outside the register never runs, the asker's own role decides, A runs, B needs Confirm, C needs a fresh check and
 *  Confirm, D is prepared for a person or the licensed partner; answers go by class (open, personal, verified, by role, never).
 *  Offline layer 1 is the signed knowledge pack (tools/assist/knowledge_pack.py), rebuilt here from the same words and checked
 *  entry by entry against the Python pack. The parts: "Fix this", the Ask box, the Confirm or Deny card and the receipt with Undo. */
import { ASSIST, FAMILIES, KP_STATES, PRODUCT_PAGES } from "./parts.generated.js";
import { esc } from "./shell.js";
import type { Icon, T } from "./shell.js";

type Cls = "A" | "B" | "C" | "D";
interface Action { area: string; class: Cls; roles: string[]; limits: { per_day: number; max_minor?: number | null }; touches: string[]; undo: string | null }
const ACTIONS: Record<string, Action> = ASSIST.actions;
const ORDER: Cls[] = ["A", "B", "C", "D"];
export interface Ask { role: string; done_today?: number; amount_minor?: number; confirmed?: boolean; fresh_check?: boolean; switched_off?: string[]; country?: string; ask_owner_first?: string[]; standing?: string[] }
export type Needs = "none" | "confirm" | "fresh_check" | "ask_owner" | "hand_over" | "refused";
export interface Decision { run: boolean; needs: Needs; class: Cls | null; why: string; undo?: string | null }

/** Same rule as services/assist_register.decide. 'why' is a word key for "Why did this happen?". */
export function decide(actionId: string, a: Ask): Decision {
  const x = ACTIONS[actionId];
  if (!x) return { run: false, needs: "refused", class: null, why: "as_why_not_registered" };
  const off = new Set(a.switched_off ?? []);
  if (off.has(actionId) || off.has(x.area) || off.has(`country:${a.country ?? null}`)) return { run: false, needs: "refused", class: null, why: "as_why_switched_off" };
  if (!x.roles.includes(a.role)) return { run: false, needs: "refused", class: null, why: "as_why_role" };
  let cls = x.class;
  const lim = x.limits;
  if ((a.done_today ?? 0) >= lim.per_day || (a.amount_minor !== undefined && lim.max_minor != null && a.amount_minor > lim.max_minor)) cls = ORDER[Math.min(ORDER.indexOf(cls) + 1, 3)]!;
  if (x.touches.some((t) => ASSIST.only_hand_over.includes(t))) cls = "D";
  if (cls === "D") return { run: false, needs: "hand_over", class: "D", why: "as_why_hand_over" };
  if (cls === "B" && a.role !== "owner" && (a.ask_owner_first ?? []).includes(actionId)) return { run: false, needs: "ask_owner", class: "B", why: "as_why_ask_owner" };
  if (cls === "C" && !a.fresh_check) return { run: false, needs: "fresh_check", class: "C", why: "as_why_fresh_check" };
  if ((cls === "B" || cls === "C") && !a.confirmed && !(cls === "B" && (a.standing ?? []).includes(actionId))) return { run: false, needs: "confirm", class: cls, why: "as_why_confirm" };
  return { run: true, needs: "none", class: cls, why: "as_why_allowed", undo: x.undo };
}
/** Same rule as services/assist_register.answer. */
export function answer(topic: string, a: { signed_in?: boolean; fresh_check?: boolean; role?: string }): { answer: boolean; class: number | null; why: string } {
  const t = ASSIST.topics[topic];
  if (!t) return { answer: false, class: null, why: "as_why_unknown" };
  const c = t.class;
  if (c === 5) return { answer: false, class: 5, why: "as_why_never" };
  if (c >= 2 && !a.signed_in) return { answer: false, class: c, why: "as_why_sign_in" };
  if (c === 3 && !a.fresh_check) return { answer: false, class: 3, why: "as_why_fresh_check" };
  if (c === 4 && !(t.roles ?? []).includes(a.role ?? "")) return { answer: false, class: 4, why: "as_why_role" };
  return { answer: true, class: c, why: "as_why_allowed" };
}

// ---------------------------------------------------------------- offline layer 1: the knowledge pack
export interface Entry { id: string; topic: string; q: string; a: string; source: string }
const fillIn = (s: string, v: Record<string, string>) => s.replace(/\{(\w+)\}/g, (_, k) => v[k] ?? `{${k}}`);
const title = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
/** The pack's entries in one language, from that language's shell words: the same entries, in the same order, as the Python pack. */
export function buildPack(w: Record<string, string>): Entry[] {
  const out: Entry[] = [];
  for (const [fam, name, tiers, prices] of FAMILIES) {
    const plans = tiers.map((t, i) => `${title(t)} $${prices[i]}`).join(", ");
    out.push({ id: `price-${fam}`, topic: "price", q: fillIn(w["kp_price_q"] ?? "", { name }), a: fillIn(w["kp_price_a"] ?? "", { name, plans }), source: "services/billing.py" });
    const page = PRODUCT_PAGES[fam];
    if (page) {
      const where = page.startsWith("/") ? `lynkomni.com${page}` : page.replace("https://", "");
      out.push({ id: `where-${fam}`, topic: "how_to", q: fillIn(w["kp_where_q"] ?? "", { name }), a: fillIn(w["kp_where_a"] ?? "", { name, page: where }), source: "catalog/products.v1.json" });
    }
  }
  for (const s of KP_STATES) out.push({ id: `state-${s}`, topic: "status_word", q: fillIn(w["kp_state_q"] ?? "", { state: w[`st_${s}`] ?? s }), a: w[`kp_state_${s}`] ?? "", source: "the five user states" });
  return out;
}
/** Words, plus three-letter pieces, so the search also works in languages written without spaces (same as the Python pack). */
export function tokens(text: string): Set<string> {
  const t = Array.from(text).map((c) => (/[\p{L}\p{N}]/u.test(c) ? c.toLowerCase() : " ")).join("");
  const out = new Set(t.split(/\s+/).filter((w) => Array.from(w).length > 1));
  const flat = Array.from(t.replace(/ /g, ""));
  for (let i = 0; i + 2 < flat.length; i++) out.add(flat.slice(i, i + 3).join(""));
  return out;
}
export function lookup(pack: Entry[], query: string): Entry[] {
  const q = tokens(query);
  const scored = pack.map((e) => { const et = tokens(e.q); let s = 0; for (const x of q) if (et.has(x)) s++; return [s, e] as const; });
  return scored.sort((a, b) => b[0] - a[0]).filter(([s]) => s > 0).slice(0, 3).map(([, e]) => e);
}

// ---------------------------------------------------------------- the parts on screen
/** "Fix this": on any screen with a problem, one button that hands the problem to Ask and Resolve with the screen's context. */
export const fixThis = (problem: string, t: T, icon: Icon): string => `<button type="button" class="secondary fixthis" data-act="assist:fix:${esc(problem)}">${icon("product-assist")}<span>${esc(t("as_fix_this"))}</span></button>`;
/** The Ask box in the help panel: answers come from the signed pack on this device when offline, and say so. */
export function askBox(o: { query: string; results: Entry[]; online: boolean; builtOn: string }, t: T, icon: Icon): string {
  const res = o.query ? (o.results.length ? `<ul class="asres">${o.results.map((e) => `<li><strong>${esc(e.q)}</strong><p>${esc(e.a)}</p></li>`).join("")}</ul>` : `<p class="muted">${esc(t("as_no_answer"))}</p>`) : "";
  const src = o.query && o.results.length ? `<p class="note">${icon(o.online ? "ui-sync" : "ui-offline")}<span>${esc(o.online ? t("as_from_lynkomni") : t("as_from_device", { date: o.builtOn }))}</span></p>` : "";
  return `<div class="askbox"><label for="asIn" class="mlabel">${esc(t("as_ask_title"))}</label><div class="cmd-input">${icon("product-assist")}<input id="asIn" type="search" value="${esc(o.query)}" placeholder="${esc(t("as_ask_hint"))}" autocomplete="off"></div>${res}${src}<p class="suggested">${esc(t("suggested_by_assist"))}</p></div>`;
}
/** The Confirm or Deny card: what LynkAssist will do, why it asks, and two equal buttons. Class C first asks for the fresh check. */
export function confirmCard(o: { what: string; d: Decision; amount?: string }, t: T, icon: Icon): string {
  const needs = o.d.needs;
  const body = needs === "fresh_check" ? `<button type="button" class="primary" data-act="assist:check">${icon("ui-lock")}<span>${esc(t("as_check_first"))}</span></button>`
    : needs === "confirm" ? `<div class="actions"><button type="button" class="primary" data-act="assist:confirm">${esc(t("as_confirm"))}</button><button type="button" class="secondary" data-act="assist:deny">${esc(t("as_deny"))}</button></div>`
    : needs === "ask_owner" ? `<button type="button" class="secondary" data-act="assist:askowner">${esc(t("as_ask_owner"))}</button>`
    : needs === "hand_over" ? `<button type="button" class="secondary" data-act="support:chat">${icon("product-chat")}<span>${esc(t("as_hand_over"))}</span></button>` : "";
  return `<div class="confirmcard" role="group" aria-label="${esc(t("as_card_title"))}"><p class="mlabel">${esc(t("as_card_title"))}</p><p class="aswhat">${esc(o.what)}${o.amount ? ` <strong>${esc(o.amount)}</strong>` : ""}</p><p class="note">${icon("ui-info")}<span>${esc(t(o.d.why))}</span></p>${body}<p class="suggested">${esc(t("suggested_by_assist"))}</p></div>`;
}
/** The receipt after LynkAssist did something: what was done, Undo while it can be undone, and "Why did this happen?". */
export function receipt(o: { what: string; undoable: boolean; secondsLeft: number }, t: T, icon: Icon): string {
  return `<div class="asreceipt" role="status">${icon("ui-check")}<span>${esc(t("as_done", { what: o.what }))}</span>${o.undoable && o.secondsLeft > 0 ? `<button type="button" class="link" data-act="assist:undo">${icon("ui-undo")}<span>${esc(t("undo"))}</span></button>` : ""}<button type="button" class="link" data-act="assist:why">${esc(t("as_why_happened"))}</button></div>`;
}
