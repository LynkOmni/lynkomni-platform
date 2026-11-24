/** LynkAssist's trust parts on screen (ASSIST UPDATE, master blueprint 75; section 4 step C3b), drawn from the trust register
 *  (catalog/assist-trust.v1.json through ts/src/assisttrust.ts):
 *    - an answer with how sure it is (a chip with its word and icon, never colour alone), the working behind a figure (the records
 *      and the sum, worked out twice), the "not an adviser" line and the "unconfirmed rule" line;
 *    - the before-and-after preview with a sample when many things change, who will be told, a warning line, practice mode, and
 *      the second approver when the change is big;
 *    - a warning line with Fix or It is fine; "Ask about this" on a figure;
 *    - the owner's controls: Pause LynkAssist actions, what each role may do, the second-approver amount, how many warnings a day,
 *      and the memory card (what it remembers, Forget, Remember that…, memory off).
 *  No DOM here: parts return HTML strings and the host binds data-act and data-in. Words come from web/assist (prefix at_). */
import type { TrustRegister, Work, Sure, GuardOut } from "./assisttrust.js";

export type T = (key: string, vars?: Record<string, string | number>) => string;
export type Icon = (id: string, cls?: string) => string;
const laEsc = (s: string): string => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const LA_SURE_ICON: Record<Sure, string> = { certain: "ui-check", likely: "ui-info", not_sure: "ui-warning", dont_know: "ui-info" };

export interface LaLook { t: T; icon: Icon; money: (minor: number, currency: string) => string }

/** How sure an answer is: an icon and its word. */
export function sureHtml(TR: TrustRegister, look: LaLook, level: Sure): string {
  return `<span class="at-sure at-${level}">${look.icon(LA_SURE_ICON[level])}<span>${laEsc(look.t(TR.certainty.words[level] ?? level))}</span></span>`;
}

/** The working behind a figure: the records and the sum (worked out twice), or why the figure is not shown. */
export function workingHtml(look: LaLook, w: Work, parts: readonly { label: string; minor: number }[]): string {
  if (!w.ok) return `<p class="at-note">${look.icon("ui-warning")}<span>${laEsc(look.t("at_not_shown"))}</span></p>`;
  const cur = w.currency ?? "";
  return `<details class="at-working"><summary>${laEsc(look.t("at_how_worked_out"))}</summary><ul>${parts.slice(0, 50).map((p) => `<li><span>${laEsc(p.label)}</span><span>${laEsc(look.money(p.minor, cur))}</span></li>`).join("")}</ul>
    <p class="at-total"><span>${laEsc(look.t("at_total"))}</span><strong>${laEsc(look.money(w.total ?? 0, cur))}</strong></p><p class="at-note">${look.icon("ui-check")}<span>${laEsc(look.t("at_checked_twice"))}</span></p></details>`;
}

export interface Answer { title: string; value?: string; text?: string; sure: Sure; working?: { w: Work; parts: readonly { label: string; minor: number }[] }; notAdviser?: boolean; unconfirmed?: boolean }
/** An answer card: LynkAssist named, the figure, how sure, the working and the honesty lines. */
export function answerHtml(TR: TrustRegister, look: LaLook, a: Answer, act = "la"): string {
  return `<div class="card at-answer" role="region" aria-label="${laEsc(look.t("at_answer_label"))}"><p class="at-who">${look.icon("product-assist")}<span>${laEsc(look.t("at_assist_name"))}</span></p>
    <h3>${laEsc(a.title)}</h3>${a.value ? `<p class="at-value">${laEsc(a.value)}</p>` : ""}${a.text ? `<p>${laEsc(a.text)}</p>` : ""}${sureHtml(TR, look, a.sure)}
    ${a.working ? workingHtml(look, a.working.w, a.working.parts) : ""}${a.notAdviser ? `<p class="at-note">${look.icon("ui-info")}<span>${laEsc(look.t(TR.not_adviser.words))}</span></p>` : ""}
    ${a.unconfirmed ? `<p class="at-note">${look.icon("ui-warning")}<span>${laEsc(look.t(TR.unconfirmed.words))}</span></p>` : ""}
    <button class="ghost inline" data-act="${act}:close">${laEsc(look.t("at_close"))}</button></div>`;
}

/** A warning at the right moment: one line, Fix or It is fine. */
export function warningLineHtml(look: LaLook, words: string, vars: Record<string, string | number>, check: string, act = "la"): string {
  return `<div class="at-warn" role="status">${look.icon("ui-warning")}<span>${laEsc(look.t(words, vars))}</span><span class="at-acts"><button data-act="${act}:fix:${laEsc(check)}">${laEsc(look.t("at_fix"))}</button><button data-act="${act}:fine:${laEsc(check)}">${laEsc(look.t("at_fine"))}</button></span></div>`;
}

export interface Preview {
  action: string; rows: readonly { label: string; before: string; after: string }[]; items: number; cost: string; told: string;
  guard: GuardOut; practice?: boolean; approverRole?: string;
  /** the host's own lines under the table (an editable new value and its warning line) */
  extraHtml?: string;
}
/** The before-and-after preview: what changes (a sample of 5 when many change), what it costs, who will be told; then Confirm or
 *  Deny, or the second approver when the change is big; practice mode says nothing real changes. */
export function previewHtml(look: LaLook, p: Preview, act = "la"): string {
  const g = p.guard;
  const rows = p.rows.slice(0, g.sample);
  const head = g.show_all ? "" : `<p class="at-note">${look.icon("ui-info")}<span>${laEsc(look.t("at_sample", { n: p.items, shown: rows.length }))}</span></p>`;
  const end = g.outcome === "second_approver" ? `<p class="at-note">${look.icon("ui-user")}<span>${laEsc(look.t("at_second_approver", { role: look.t(`at_role_${p.approverRole ?? "owner"}`) }))}</span></p>
      <div class="at-acts"><button class="primary" data-act="${act}:askapprover">${laEsc(look.t("at_ask_approver"))}</button><button class="ghost" data-act="${act}:deny">${laEsc(look.t("at_deny"))}</button></div>`
    : `<div class="at-acts"><button class="primary" data-act="${act}:confirm">${laEsc(look.t(p.practice ? "at_confirm_practice" : "at_confirm"))}</button><button class="ghost" data-act="${act}:deny">${laEsc(look.t("at_deny"))}</button></div>`;
  return `<div class="card at-preview" data-item="assist_preview"><h2>${laEsc(look.t("at_preview_title"))}</h2><p>${laEsc(p.action)}</p>${head}
    <table class="at-table"><thead><tr><th scope="col">${laEsc(look.t("at_what"))}</th><th scope="col">${laEsc(look.t("at_before"))}</th><th scope="col">${laEsc(look.t("at_after"))}</th></tr></thead>
    <tbody>${rows.map((r) => `<tr><th scope="row">${laEsc(r.label)}</th><td>${laEsc(r.before)}</td><td>${laEsc(r.after)}</td></tr>`).join("")}</tbody></table>
    <dl class="at-facts"><dt>${laEsc(look.t("at_cost"))}</dt><dd>${laEsc(p.cost)}</dd><dt>${laEsc(look.t("at_told"))}</dt><dd>${laEsc(p.told)}</dd></dl>
    ${p.extraHtml ?? ""}${p.practice ? `<p class="at-note">${look.icon("ui-info")}<span>${laEsc(look.t("at_practice_note"))}</span></p>` : ""}${end}</div>`;
}

/** The answer when the trust layer stops an action: paused, switched off for the role, over the owner's limit, or text it read. */
export function stoppedHtml(look: LaLook, outcome: string): string {
  return `<p class="info at-stopped" role="status">${look.icon("ui-lock")}<span>${laEsc(look.t(`at_stopped_${outcome}`))}</span></p>`;
}

/** "Ask about this" on a figure: a button for keyboards and buttons-only screens; press and hold does the same (host binds it). */
export function askButtonHtml(look: LaLook, target: string, id: string): string {
  return `<button class="at-ask" data-act="la:ask:${laEsc(target)}:${laEsc(id)}" aria-label="${laEsc(look.t("at_ask_about"))}">${look.icon("product-assist")}<span>${laEsc(look.t("at_ask_short"))}</span></button>`;
}

export interface Controls {
  owner: boolean; paused: boolean; roles: readonly string[]; areas: readonly string[]; off: ReadonlySet<string>;
  approverAmount: string; pace: string; memoryOn: boolean; memory: readonly { id: string; text: string }[]; draft: string;
  areaLabel: (area: string) => string;
}
/** The owner's controls for LynkAssist. Staff see them, greyed, with who may change them. */
export function controlsHtml(TR: TrustRegister, look: LaLook, c: Controls): string {
  const dis = c.owner ? "" : " disabled";
  const sw = (key: string, on: boolean, label: string): string => `<label class="switch"><span>${laEsc(label)}</span><input type="checkbox" data-in="${laEsc(key)}"${on ? " checked" : ""}${dis}></label>`;
  return `<div class="card" data-item="pause_actions"><h2>${laEsc(look.t("at_pause_title"))}</h2>${sw("la:pause", c.paused, look.t("at_pause"))}<p class="sub">${laEsc(look.t("at_pause_note"))}</p></div>
    <div class="card" data-item="role_permissions"><h2>${laEsc(look.t("at_roles_title"))}</h2><p class="sub">${laEsc(look.t("at_roles_note"))}</p>
      ${c.roles.map((r) => `<fieldset class="at-role"><legend>${laEsc(look.t(`at_role_${r}`))}</legend>${c.areas.map((a) => sw(`la:role:${r}:${a}`, !c.off.has(`${r}:${a}`), c.areaLabel(a))).join("")}</fieldset>`).join("")}</div>
    <div class="card" data-item="second_approver"><h2>${laEsc(look.t("at_approver_title"))}</h2><label class="field"><span>${laEsc(look.t("at_approver_amount"))}</span>
      <input id="atApprover" aria-label="${laEsc(look.t("at_approver_amount"))}" data-in="la:approver" type="number" inputmode="numeric" min="0" value="${laEsc(c.approverAmount)}" placeholder="${laEsc(look.t("at_hint_amount"))}"${dis}></label>
      <p class="sub">${laEsc(look.t("at_approver_note", { items: TR.safety.second_approver.items_over }))}</p></div>
    <div class="card" data-item="warning_pace"><h2>${laEsc(look.t("at_pace_title"))}</h2><div class="at-pace" role="group" aria-label="${laEsc(look.t("at_pace_title"))}">${Object.keys(TR.warnings.pace).map((p) => `<button data-act="la:pace:${p}" aria-pressed="${c.pace === p}">${laEsc(look.t(`at_pace_${p}`))}</button>`).join("")}</div></div>
    <div class="card" data-item="memory"><h2>${laEsc(look.t("at_memory_title"))}</h2>${sw("la:memory", c.memoryOn, look.t("at_memory_on"))}
      ${c.memory.length ? `<ul class="list">${c.memory.map((m) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${laEsc(m.text)}</span></span><button class="ghost small" data-act="la:forget:${laEsc(m.id)}">${laEsc(look.t("at_forget"))}</button></div></li>`).join("")}</ul>` : `<p class="sub">${laEsc(look.t("at_memory_empty"))}</p>`}
      <label class="field"><span>${laEsc(look.t("at_remember"))}</span><input id="atRemember" aria-label="${laEsc(look.t("at_remember"))}" data-in="la:remember" value="${laEsc(c.draft)}" placeholder="${laEsc(look.t("at_hint_remember"))}"${c.memoryOn ? "" : ' disabled data-why="at_remember_off"'}></label>
      <button class="ghost inline" data-act="la:remember"${c.memoryOn ? "" : " disabled"}>${laEsc(look.t("at_remember_save"))}</button><p class="sub">${laEsc(look.t("at_memory_note"))}</p></div>`;
}

// ---- LynkAssist across services (CONNECT UPDATE 71.6, section 4 row 71.9 step 3): usage meter, morning brief, questions across
//      services, saved questions and plans; the rules run in the cloud (services/assist_connect.py) ----
export const ACROSS_KINDS = ["week", "owed", "due_soon"] as const;
export const PLAN_GOALS = ["chase_overdue", "month_end"] as const;
const AX_PART_WORD: Record<string, string> = { sales: "at_part_sales", payments: "at_part_payments", owed: "at_part_owed", overdue: "at_part_overdue",
  bills: "at_part_bills", due_today: "at_part_due_today", drafts: "at_part_drafts", needs_person: "at_part_needs_person" };
const AX_KIND_WORD: Record<string, string> = { week: "at_q_week", owed: "at_q_owed", due_soon: "at_q_due_soon" };
const AX_GOAL_WORD: Record<string, string> = { chase_overdue: "at_goal_chase_overdue", month_end: "at_goal_month_end" };
export interface Across {
  used: number; limit: number | null;
  brief: { on: boolean; parts: Record<string, number>; hidden: boolean };
  answer: { kind: string; parts: Record<string, { count: number; source: string }>; hidden: boolean } | null;
  saved: readonly string[]; plan: { goal: string; steps: number } | null;
  owner: boolean; name: (family: string) => string;
}
const partsHtml = (look: LaLook, parts: Record<string, number>): string =>
  `<ul class="at-parts">${Object.entries(parts).map(([k, n]) => `<li>${laEsc(look.t(AX_PART_WORD[k] ?? "at_sample_word", { n }))}</li>`).join("")}</ul>`;

export function acrossHtml(look: LaLook, c: Across): string {
  const usage = c.limit === null ? look.t("at_usage_none", { used: c.used }) : look.t("at_usage", { used: c.used, limit: c.limit });
  const ans = c.answer ? `<div class="at-answer" role="status"><strong>${laEsc(look.t(AX_KIND_WORD[c.answer.kind] ?? "at_sample_word"))}</strong><ul class="at-parts">${Object.entries(c.answer.parts).map(([k, v]) =>
      `<li>${laEsc(look.t(AX_PART_WORD[k] ?? "at_sample_word", { n: v.count }))} · <span class="sub">${laEsc(look.t("at_from", { service: c.name(v.source) }))}</span></li>`).join("")}</ul>
      ${c.answer.hidden ? `<p class="sub">${laEsc(look.t("at_part_hidden"))}</p>` : ""}${c.saved.includes(c.answer.kind) ? `<p class="sub">${laEsc(look.t("at_saved"))}</p>` : `<button class="ghost inline" data-act="la:save:${laEsc(c.answer.kind)}">${laEsc(look.t("at_save_daily"))}</button>`}</div>` : "";
  return `<div class="card" data-item="usage_meter"><h2>${laEsc(look.t("at_usage_title"))}</h2><p>${laEsc(usage)} · <span class="sub">${laEsc(look.t("at_sample_word"))}</span></p></div>
    <div class="card" data-item="morning_brief"><h2>${laEsc(look.t("at_brief_title"))}</h2><label class="switch"><span>${laEsc(look.t("at_brief_on"))}</span><input type="checkbox" data-in="la:brief"${c.brief.on ? " checked" : ""}></label>
      <p class="sub">${laEsc(look.t("at_brief_note"))}</p>${c.brief.on ? `${partsHtml(look, c.brief.parts)}${c.brief.hidden ? `<p class="sub">${laEsc(look.t("at_part_hidden"))}</p>` : ""}<p class="sub">${laEsc(look.t("at_sample_word"))}</p>` : ""}</div>
    <div class="card" data-item="ask_across"><h2>${laEsc(look.t("at_across_title"))}</h2><div class="at-kinds">${ACROSS_KINDS.map((k) => `<button class="ghost inline" data-act="la:across:${k}">${laEsc(look.t(AX_KIND_WORD[k] ?? "at_sample_word"))}</button>`).join("")}</div>${ans}</div>
    <div class="card" data-item="assist_plan"><h2>${laEsc(look.t("at_plan_title"))}</h2><p class="sub">${laEsc(look.t("at_plan_note"))}</p><div class="at-kinds">${PLAN_GOALS.map((g) => `<button class="ghost inline" data-act="la:plan:${g}"${c.owner ? "" : " disabled"}>${laEsc(look.t(AX_GOAL_WORD[g] ?? "at_sample_word"))}</button>`).join("")}</div>
      ${c.plan ? `<p role="status">${laEsc(look.t(AX_GOAL_WORD[c.plan.goal] ?? "at_sample_word"))}: ${laEsc(look.t("at_plan_steps", { n: c.plan.steps }))}</p>` : ""}</div>`;
}
