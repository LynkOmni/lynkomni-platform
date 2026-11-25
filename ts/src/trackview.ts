/** How a tracker looks on every screen (owner request 9 November 2026): the business app, the rider's phone, the account site and
 *  the customer's tracking page all draw a tracker from ts/src/tracking.ts with this one function, so a step reads the same
 *  everywhere. The chip uses only the five states; the steps say what happened, newest at the bottom; the promised time, a missed
 *  promise and live progress (a share of the trip, never a position) show only when the engine has them. */
import { noticeHtml, type Notice } from "./errorbox.js";
import type { View, StepView, TowerRow, Exception, Risk } from "./tracking.js";

export interface TrackLook {
  t: (key: string, vars?: Record<string, string | number>) => string;
  esc: (s: string) => string;
  icon: (id: string) => string;
  /** a time of day in the viewer's time zone, from an ISO-8601 UTC text */
  time: (iso: string) => string;
  chip: (state: View["state"]) => string;
}

/** The live part of a tracker: the promised time (or the missed promise) and the share of the trip done. */
export function trackEta(v: View, o: TrackLook): string {
  // a child is a full view only on the customer's tracker; elsewhere it is a summary (kind, record, state, step) with no live part
  const hasLive = (x: View | null | undefined): boolean => !!x && !x.ended && (!!x.eta || typeof x.progress === "number");
  const live: View | null = hasLive(v) ? v : ((v.children as (View | null)[]).find(hasLive) ?? null);
  if (!live) return "";
  const eta = live.eta ? `<p class="trk-eta${live.late ? " late" : ""}" role="status">${o.icon(live.late ? "ui-warning" : "ui-info")}<span>${o.esc(live.late ? o.t("trk_late", { time: o.time(live.eta) }) : o.t("trk_eta", { time: o.time(live.eta) }))}</span></p>` : "";
  const pct = typeof live.progress !== "number" ? null : Math.round(live.progress * 100);
  const bar = pct === null ? "" : `<div class="trk-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}" aria-label="${o.esc(o.t("trk_progress", { pct }))}"><i style="inline-size:${pct}%"></i></div><p class="trk-pct">${o.esc(o.t("trk_progress", { pct }))}</p>`;
  return eta + bar;
}

function stepHtml(s: StepView, o: TrackLook): string {
  const cls = s.current ? "current" : s.done ? "done" : "todo";
  const mark = s.done ? o.icon(s.state === "failed" ? "ui-warning" : "ui-check") : "";
  return `<li class="trk-step ${cls}${s.state === "failed" && s.done ? " failed" : ""}" data-step="${o.esc(s.id)}"${s.current ? ' aria-current="step"' : ""}><span class="trk-dot" aria-hidden="true">${mark}</span><span class="trk-word">${o.esc(o.t(s.label))}</span>${s.at && s.done ? `<span class="trk-at">${o.esc(o.time(s.at))}</span>` : ""}</li>`;
}

/** One tracker: its name, the state chip, the live part and the steps. `title` replaces the kind's name (an order number, say). */
export function trackerHtml(v: View, o: TrackLook, title?: string): string {
  return `<section class="trk" data-kind="${o.esc(v.kind)}" data-item="timeline"><header class="trk-head"><h3>${o.esc(title ?? o.t(v.label))}</h3>${o.chip(v.state)}</header>
    ${trackEta(v, o)}<ol class="trk-steps">${v.steps.map((s) => stepHtml(s, o)).join("")}</ol></section>`;
}

/** A short line for a list ("On the way" on a home screen): the kind or title, the current step and the chip. */
export function trackerLine(v: View, o: TrackLook, title: string, act: string): string {
  const cur = v.steps.find((s) => s.current) ?? v.steps.filter((s) => s.done).pop();
  return `<li><button class="rowbtn trk-line" data-act="${o.esc(act)}"><span class="main"><span class="nm">${o.esc(title)}</span><span class="sub">${o.esc(cur ? o.t(cur.label) : o.t(v.label))}${v.late ? ` · ${o.esc(o.t("trk_late_short"))}` : ""}</span></span>${o.chip(v.state)}</button></li>`;
}

// ---- the control tower (TRACKING UPDATE 72.4, section 4 row 72.9): what is on the way, what needs a person, a scan and own steps ----
export interface TowerLook extends TrackLook {
  /** the item's name on screen (an order number, say): never a customer's name, address or phone number */
  name: (kind: string, record: string) => string;
}
const RISKS: readonly Risk[] = ["late", "at_risk", "on_time"];
const RISK_WORD: Record<Risk, string> = { late: "trk_late_short", at_risk: "trk_risk_at_risk", on_time: "trk_risk_on_time" };
const WHY_WORD: Record<Exception["why"], string> = { clash: "trk_why_clash", failed: "trk_failed", stuck: "trk_why_stuck", late: "trk_late_short", at_risk: "trk_risk_at_risk", waiting_on_customer: "trk_why_waiting_on_customer" };

/** The counts by risk and the list of items on the way, riskiest first. Risk is always a word beside its icon, never colour alone. */
export function towerHtml(tower: { rows: TowerRow[]; counts: Record<Risk, number>; total: number }, o: TowerLook, practice: ReadonlySet<string> = new Set()): string {
  const counts = `<ul class="trk-counts" role="list">${RISKS.map((r) => `<li class="trk-count r-${r}"><strong>${tower.counts[r]}</strong><span>${o.esc(o.t(RISK_WORD[r]))}</span></li>`).join("")}</ul>`;
  const rank = (r: Risk | null): number => (r === null ? 3 : RISKS.indexOf(r));
  const rows = [...tower.rows].sort((a, b) => rank(a.risk) - rank(b.risk));
  const body = rows.length ? `<ul class="rows trk-tower">${rows.map((x) => `<li data-kind="${o.esc(x.kind)}"><span class="trk-main"><span class="trk-nm">${o.esc(o.name(x.kind, x.record))}</span><span class="trk-sub">${o.esc(o.t(`trk_k_${x.kind}`))} · ${o.esc(o.t(`trk_${x.step}`))}${x.since ? ` · ${o.esc(o.t("trk_since", { time: o.time(x.since) }))}` : ""}${practice.has(x.record) ? ` · ${o.esc(o.t("trk_practice"))}` : ""}</span></span>${x.risk ? `<span class="trk-risk r-${x.risk}">${o.icon(x.risk === "on_time" ? "ui-check" : "ui-warning")}<span>${o.esc(o.t(RISK_WORD[x.risk]))}</span></span>` : ""}</li>`).join("")}</ul>`
    : `<p class="note trk-empty">${o.icon("ui-info")}<span>${o.esc(o.t("trk_none"))}</span></p>`;
  return `<section class="trk-panel" data-item="tower"><h2>${o.esc(o.t("trk_on_the_way"))}</h2><p class="note">${o.esc(o.t("trk_tower_intro", { n: tower.total }))}</p>${counts}${body}</section>`;
}

/** What needs a person: two endings that clash, failed, stuck, late, at risk and waiting for the customer, each with its reason. */
export function exceptionsHtml(list: readonly Exception[], o: TowerLook): string {
  const body = list.length ? `<ul class="rows trk-needs">${list.map((x) => `<li data-why="${o.esc(x.why)}"><span class="trk-main"><span class="trk-nm">${o.esc(o.name(x.kind, x.record))}</span><span class="trk-sub">${o.esc(o.t(`trk_k_${x.kind}`))} · ${o.esc(o.t(`trk_${x.step}`))}</span></span><span class="trk-why">${o.icon(x.why === "waiting_on_customer" ? "ui-info" : "ui-warning")}<span>${o.esc(o.t(WHY_WORD[x.why]))}</span></span></li>`).join("")}</ul>`
    : `<p class="note trk-empty">${o.icon("ui-check")}<span>${o.esc(o.t("trk_all_clear"))}</span></p>`;
  return `<section class="trk-panel" data-item="needs"><h2>${o.esc(o.t("trk_needs_you"))}</h2>${body}</section>`;
}

/** Mark a step by scanning the code on an item (or choosing it): the result says why a scan was refused, in words. */
export function scanHtml(items: readonly { kind: string; record: string }[], steps: readonly string[], o: TowerLook, sel: { item: string; step: string; proof: string; result: { ok: boolean; why: string[] } | null }): string {
  const opt = (v: string, label: string, cur: string): string => `<option value="${o.esc(v)}"${v === cur ? " selected" : ""}>${o.esc(label)}</option>`;
  const [kind = "", rec = ""] = sel.item.split("|");
  const item = o.name(kind, rec), stepName = o.t(`trk_${sel.step}`);
  // Section 4C point 2: each refusal says where (the field it is about), what and why with the real names, and how to fix it.
  const why = (w: string): Notice => {
    if (w.startsWith("after:")) {
      const e = w.slice(6), earlier = o.t(`trk_${e}`), text = o.t("trk_scan_why_after", { item, step: stepName, earlier });
      return steps.includes(e) ? { level: "error", text, field: "trkStep", id: "trkScanMsg", fix: { label: o.t("trk_scan_fix_after", { step: earlier }), act: `trk:pick:${e}` } }
        : { level: "error", text, field: "trkStep", id: "trkScanMsg", how: o.t("trk_scan_how_wait", { step: earlier }) };
    }
    if (w === "ended") return { level: "error", text: o.t("trk_scan_why_ended", { item }), field: "trkItem", id: "trkScanMsg", fix: { label: o.t("trk_scan_fix_item"), focus: "trkItem" } };
    if (w === "needs_proof") return { level: "error", text: o.t("trk_scan_why_needs_proof", { step: stepName }), field: "trkProof", id: "trkScanMsg", fix: { label: o.t("trk_scan_fix_proof"), focus: "trkProof" } };
    if (w === "cloud_only") return { level: "error", text: o.t("trk_scan_why_cloud_only", { step: stepName }), field: "trkStep", id: "trkScanMsg", fix: { label: o.t("trk_scan_fix_step"), focus: "trkStep" } };
    return { level: "error", text: o.t("trk_scan_why_not_scannable", { step: stepName }), field: "trkStep", id: "trkScanMsg", fix: { label: o.t("trk_scan_fix_step"), focus: "trkStep" } };
  };
  const res = sel.result ? (sel.result.ok ? noticeHtml(o.t, { level: "success", text: o.t("trk_scan_ok") })
    : sel.result.why.length ? noticeHtml(o.t, why(sel.result.why[0] as string)) : "") : "";
  return `<section class="trk-panel" data-item="scan"><h2>${o.esc(o.t("trk_scan"))}</h2><div class="trk-form">
    <label class="trk-field" for="trkItem"><span>${o.esc(o.t("trk_scan_item"))}</span><select id="trkItem" data-in="trk:item">${items.map((x) => opt(`${x.kind}|${x.record}`, `${o.name(x.kind, x.record)} · ${o.t(`trk_k_${x.kind}`)}`, sel.item)).join("")}</select></label>
    <label class="trk-field" for="trkStep"><span>${o.esc(o.t("trk_scan_step"))}</span><select id="trkStep" data-in="trk:step">${steps.map((s) => opt(s, o.t(`trk_${s}`), sel.step)).join("")}</select></label>
    <label class="trk-field" for="trkProof"><span>${o.esc(o.t("trk_scan_proof"))}</span><select id="trkProof" data-in="trk:proof">${opt("", o.t("trk_proof_none"), sel.proof)}${opt("code", o.t("trk_proof_code"), sel.proof)}${opt("signature", o.t("trk_proof_signature"), sel.proof)}</select></label>
    <button class="primary" data-act="trk:scan">${o.esc(o.t("trk_scan_go"))}</button></div>${res}</section>`;
}

/** A business's own extra steps for one kind (at most `max`): they sit beside LynkOmni's steps and never replace them. */
export function extraStepsHtml(kind: string, steps: readonly { id: string; label: string }[], max: number, o: TowerLook, draft: string): string {
  const full = steps.length >= max;
  return `<section class="trk-panel" data-item="extra"><h2>${o.esc(o.t("trk_extra"))}</h2><p class="note">${o.esc(o.t("trk_extra_intro", { n: max, kind: o.t(`trk_k_${kind}`) }))}</p>
    ${steps.length ? `<ul class="rows">${steps.map((s) => `<li><span>${o.esc(s.label)}</span><button class="secondary" data-act="trk:drop:${o.esc(s.id)}">${o.esc(o.t("trk_extra_remove"))}</button></li>`).join("")}</ul>` : ""}
    ${full ? `<p class="note">${o.esc(o.t("trk_extra_full"))}</p>` : `<div class="trk-form"><label class="trk-field" for="trkExtra"><span>${o.esc(o.t("trk_extra_name"))}</span><input id="trkExtra" data-in="trk:extra" maxlength="40" value="${o.esc(draft)}" placeholder="${o.esc(o.t("hint_step"))}"></label>
    <button class="secondary" data-act="trk:add"${draft.trim() ? "" : ` disabled data-why="${o.esc(o.t("trk_extra_name_first"))}"`}>${o.esc(o.t("trk_extra_add"))}</button></div>`}</section>`;
}
