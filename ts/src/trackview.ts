/** How a tracker looks on every screen (owner request 9 November 2026): the business app, the rider's phone, the account site and
 *  the customer's tracking page all draw a tracker from ts/src/tracking.ts with this one function, so a step reads the same
 *  everywhere. The chip uses only the five states; the steps say what happened, newest at the bottom; the promised time, a missed
 *  promise and live progress (a share of the trip, never a position) show only when the engine has them. */
import type { View, StepView } from "./tracking.js";

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
