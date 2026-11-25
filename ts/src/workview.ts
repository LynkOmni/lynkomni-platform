/** LynkHR, LynkProject and LynkFiles on screen (SIX SERVICES UPDATE 69.3, 69.4 and 69.7; build section 4B step 4): LynkHR at
 *  app.lynkomni.com/hr, LynkProject at /project and LynkFiles at /files, in the browser and inside the Business app. Every page is
 *  drawn from the real rules (hr.ts, project.ts, files.ts) with the shared page parts (pagekit.ts); figures are computed, never
 *  typed, and the sample records are labelled Sample. Words live in web/work (prefix wk_). No DOM here: pages return HTML strings
 *  and the host binds data-act (wk:...) and data-in (wk:...).
 *  Rules kept on screen: LynkAssist never decides about a person; health, family and union details only where the law allows;
 *  the person always sees their own record; nobody approves their own leave, pay change or time; a clash is shown, never a refusal;
 *  peer and upward answers show only from 3; cases are seen only by HR and the named investigator; a task is done only when what it
 *  waits on is done; a guest never sees money; billable time is billed once; a signer signs the version they saw; a share link
 *  always ends; each approval step is answered by its named approver, in order. */
import type { NavRegister } from "./navigation.js";
import { listToolbarHtml, saveBarHtml } from "./pagekit.js";
import { noticeHtml } from "./errorbox.js";
import { HR } from "./hr.generated.js";
import { hrVisibleFields, leaveBalance, leaveClashes, leaveRequestOk, hrMayApprove, hrChecklist, finalPayReady, reviewShown, payChangeOk, payrollFigures, hrCaseMaySee, expiryStage, hrAssistMay } from "./hr.js";
import type { HrRegister } from "./hr.js";
import { PROJECT } from "./project.generated.js";
import { taskMoveOk, taskDoneOk, projectSchedule, lateTasks, atRiskTasks, myWork, workloadFor, timeApproveOk, billableTime, projectMoney, guestSees, sprintStats } from "./project.js";
import type { ProjectRegister, Task } from "./project.js";
import { FILES } from "./files.generated.js";
import { nextSigners, signRequestState, shareOpen } from "./files.js";
import type { FilesRegister } from "./files.js";

type Tf = (key: string, vars?: Record<string, string | number>) => string;
export type WorkService = "lynkhr" | "lynkproject" | "lynkfiles";
export const WORK_SERVICES: readonly WorkService[] = ["lynkhr", "lynkproject", "lynkfiles"];
export const WORK_PATHS: Record<WorkService, string> = { lynkhr: "/hr", lynkproject: "/project", lynkfiles: "/files" };
export interface WorkCtx {
  t: Tf; money: (minor: number) => string; icon: (id: string) => string; chip: (state: "queued" | "sent" | "accepted" | "confirmed" | "failed") => string;
  nav: NavRegister; today: string;
}
/** Each service's pages in the register's slots (overview, list, reports, settings). */
export const WORK_PAGES: Record<WorkService, readonly { id: string; slot: string }[]> = {
  lynkhr: [{ id: "hr_people", slot: "overview" }, { id: "hr_record", slot: "list" }, { id: "hr_leave", slot: "list" }, { id: "hr_joining", slot: "list" },
    { id: "hr_reviews", slot: "list" }, { id: "hr_pay", slot: "reports" }, { id: "hr_cases", slot: "list" }, { id: "hr_expiry", slot: "reports" }],
  lynkproject: [{ id: "pj_projects", slot: "overview" }, { id: "pj_board", slot: "list" }, { id: "pj_mywork", slot: "list" }, { id: "pj_timeline", slot: "reports" },
    { id: "pj_time", slot: "list" }, { id: "pj_changes", slot: "list" }, { id: "pj_guests", slot: "settings" }],
  lynkfiles: [{ id: "fl_files", slot: "overview" }, { id: "fl_signing", slot: "list" }, { id: "fl_approvals", slot: "list" }, { id: "fl_requests", slot: "list" }, { id: "fl_sharing", slot: "settings" }],
};
const WKH = HR as unknown as HrRegister, PJ = PROJECT as unknown as ProjectRegister, FL = FILES as unknown as FilesRegister;
export const wkEsc = (s: unknown): string => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
const WK_DAY = 20417;                    // the sample's "today" as a day number (tasks count days from here)

interface Staff { id: string; name: string; kind: string; role: string; salary: number }
interface Leave { id: string; staff: string; kind: string; half: number; first: string; last: string; state: string }

export class WorkView {
  staff: Staff[] = [
    { id: "LOSTF-1001", name: "wk_sample_staff_1", kind: "permanent", role: "manager", salary: 450000 },
    { id: "LOSTF-1002", name: "wk_sample_staff_2", kind: "part_time", role: "staff", salary: 220000 },
    { id: "LOSTF-1003", name: "wk_sample_staff_3", kind: "volunteer", role: "staff", salary: 0 },
    { id: "LOSTF-1004", name: "wk_sample_staff_4", kind: "contractor", role: "staff", salary: 300000 },
  ];
  leave: Leave[] = [
    { id: "l1", staff: "LOSTF-1002", kind: "annual", half: 4, first: "2026-12-01", last: "2026-12-02", state: "asked" },
    { id: "l2", staff: "LOSTF-1001", kind: "sick", half: 2, first: "2026-11-20", last: "2026-11-20", state: "approved" },
  ];
  joining: string[] = ["contract_signed", "documents"]; leaving: string[] = ["notice_recorded"];
  viewAs = "manager"; payApproved = false; leaveNote = "";
  tasks: Task[] = [
    { id: "LOTSK-1", state: "done", days: 3, due: WK_DAY - 2, owner: "u1" }, { id: "LOTSK-2", state: "doing", days: 5, waits_on: ["LOTSK-1"], due: WK_DAY - 1, owner: "u1" },
    { id: "LOTSK-3", state: "todo", days: 2, waits_on: ["LOTSK-2"], due: WK_DAY + 3, owner: "u2" }, { id: "LOTSK-4", state: "waiting", days: 1, waits_on: ["LOTSK-3"], due: WK_DAY + 6, owner: "u1" },
  ];
  titles: Record<string, string> = { "LOTSK-1": "wk_sample_task_1", "LOTSK-2": "wk_sample_task_2", "LOTSK-3": "wk_sample_task_3", "LOTSK-4": "wk_sample_task_4" };
  time = [{ id: "t1", by: "u2", minutes: 90, rate: 15000, approved: false, billable: true, billed: false }, { id: "t2", by: "u2", minutes: 45, rate: 15000, approved: false, billable: false, billed: false }];
  sheetState = "open"; billedNote = ""; changes = [{ id: "c1", by: "u2", cost: 50000, days: 3, state: "raised" }];
  signers = ["wk_signer_1", "wk_signer_2"]; signed: string[] = ["wk_signer_1"]; routeStep = 1; routeState = "waiting"; requestStateNow = "asked";
  linkStopped = false;
  constructor(private c: WorkCtx) {}

  private t = (k: string, v?: Record<string, string | number>): string => this.c.t(k, v);
  private sample(): string { return `<p class="of-sample">${this.c.icon("ui-info")}<span>${wkEsc(this.t("wk_sample_note"))}</span></p>`; }
  private head(page: string, rule?: string): string { return `<h1>${wkEsc(this.title(page))}</h1>${this.sample()}${rule ? `<p class="note">${wkEsc(this.t(rule))}</p>` : ""}`; }
  private m(n: number): string { return wkEsc(this.c.money(n)); }
  private rows(cells: readonly (readonly string[])[], head: readonly string[]): string {
    return `<table class="of-table of-stack"><thead><tr>${head.map((h) => `<th>${wkEsc(this.t(h))}</th>`).join("")}</tr></thead><tbody>${cells.map((r) =>
      `<tr>${r.map((c, i) => `<td${head[i] ? ` data-label="${wkEsc(this.t(head[i]!))}"` : ""}>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  }
  private btn(label: string, act: string, primary = false): string { return `<button class="${primary ? "primary" : "secondary"}" data-act="${wkEsc(act)}">${wkEsc(this.t(label))}</button>`; }
  private why(k: string, v?: Record<string, string | number>): string { return `<span class="of-why">${wkEsc(this.t(k, v))}</span>`; }
  private nm(id: string): string { const s = this.staff.find((x) => x.id === id); return s ? wkEsc(this.t(s.name)) : wkEsc(id); }
  pages(s: WorkService): readonly { id: string; slot: string }[] { return WORK_PAGES[s]; }
  title(page: string): string { return this.t(`wk_page_${page}`); }
  note(): string { return `<p class="note" role="note">${this.c.icon("ui-info")} ${wkEsc(this.t("wk_works_everywhere"))}</p>`; }

  draw(s: WorkService, page: string): string {
    void s;
    switch (page) {
      case "hr_people": return this.hrPeople();
      case "hr_record": return this.hrRecord();
      case "hr_leave": return this.hrLeave();
      case "hr_joining": return this.hrJoining();
      case "hr_reviews": return this.hrReviews();
      case "hr_pay": return this.hrPay();
      case "hr_cases": return this.hrCases();
      case "hr_expiry": return this.hrExpiry();
      case "pj_projects": return this.pjProjects();
      case "pj_board": return this.pjBoard();
      case "pj_mywork": return this.pjMyWork();
      case "pj_timeline": return this.pjTimeline();
      case "pj_time": return this.pjTime();
      case "pj_changes": return this.pjChanges();
      case "pj_guests": return this.pjGuests();
      case "fl_files": return this.flFiles();
      case "fl_signing": return this.flSigning();
      case "fl_approvals": return this.flApprovals();
      case "fl_requests": return this.flRequests();
      default: return this.flSharing();
    }
  }

  // ---- LynkHR ------------------------------------------------------------------------------------------------------------------
  private hrPeople(): string {
    const rows = this.staff.map((x) => [`${this.nm(x.id)}<br><span class="of-why">${wkEsc(x.id)}</span>`, wkEsc(this.t(`wk_worker_${x.kind}`)), wkEsc(this.t(`wk_role_${x.role}`)),
      WKH.on_payroll.includes(x.kind) ? wkEsc(this.t("wk_on_payroll")) : this.why("wk_not_on_payroll")]);
    return `${this.head("hr_people", "wk_people_rule")}${listToolbarHtml(this.t, { hint: this.t("wk_hint_person"), chips: [], inputId: "wkSearch" })}${this.rows(rows, ["wk_col_person", "wk_col_kind", "wk_col_role", "wk_col_payroll"])}
      <p class="note">${wkEsc(this.t("wk_assist_never"))}</p>`;
  }
  private hrRecord(): string {
    const x = this.staff[1]!, self = this.viewAs === "self";
    const shown = hrVisibleFields(WKH, self ? "staff" : this.viewAs, self);
    const vals: Record<string, string> = { role: this.t(`wk_role_${x.role}`), worker_kind: this.t(`wk_worker_${x.kind}`), start_date: "2025-03-01", branch: this.t("wk_sample_branch"),
      department: this.t("wk_sample_department"), manager: this.nm("LOSTF-1001"), salary: this.c.money(x.salary), pay_grade: "B2" };
    const roles = ["owner", "hr", "manager", "staff", "self"];
    return `${this.head("hr_record", "wk_record_rule")}<label class="of-field" for="wkViewAs"><span>${wkEsc(this.t("wk_view_as"))}</span><select id="wkViewAs" data-in="wk:viewas">${roles.map((r) =>
      `<option value="${r}"${r === this.viewAs ? " selected" : ""}>${wkEsc(this.t(`wk_viewer_${r}`))}</option>`).join("")}</select></label>
      <h2>${this.nm(x.id)}</h2>${this.rows(Object.keys(vals).filter((k) => shown.includes(k)).map((k) => [wkEsc(this.t(`wk_field_${k}`)), wkEsc(vals[k])]), ["wk_col_field", "wk_col_value"])}
      <p class="note">${wkEsc(this.t(shown.includes("salary") ? "wk_record_pay_seen" : "wk_record_pay_hidden"))}</p>
      ${self ? this.btn("wk_ask_correction", "wk:correct") : ""}`;
  }
  private hrLeave(): string {
    const bal = leaveBalance(20, 6, 4);
    const away: Record<string, number> = { "2026-12-01": 1, "2026-12-02": 1 };
    const clash = leaveClashes(WKH, 3, away, ["2026-12-01", "2026-12-02"]);
    const rows = this.leave.map((q) => [this.nm(q.staff), wkEsc(this.t(`wk_leave_${q.kind}`)), wkEsc(this.t("wk_half_days", { n: q.half })), `${wkEsc(q.first)} → ${wkEsc(q.last)}`,
      q.state === "asked" ? `${hrMayApprove(q.staff, "LOSTF-1001") ? this.btn("wk_approve", `wk:leave:${q.id}:approved`, true) + this.btn("wk_decline", `wk:leave:${q.id}:declined`) : this.why("wk_not_own")}`
        : `${this.c.chip(q.state === "approved" ? "confirmed" : "failed")} ${wkEsc(this.t(`wk_state_${q.state}`))}`]);
    return `${this.head("hr_leave", "wk_leave_rule")}<p>${wkEsc(this.t("wk_balance", { n: bal, entitled: 20, taken: 6, carried: 4 }))}</p>
      ${leaveRequestOk(WKH, "annual", 30, bal) ? "" : `<p class="note">${wkEsc(this.t("wk_over_balance"))}</p>`}
      ${clash.length ? noticeHtml(this.t, { level: "warning", text: this.t("wk_clash", { days: clash.join(", ") }) }) : ""}
      ${this.rows(rows, ["wk_col_person", "wk_col_kind", "wk_col_amount", "wk_col_dates", "wk_col_state"])}${this.leaveNote ? `<p class="note" role="status">${wkEsc(this.leaveNote)}</p>` : ""}`;
  }
  private hrJoining(): string {
    const j = hrChecklist(WKH, "joining", this.joining), l = hrChecklist(WKH, "leaving", this.leaving);
    const list = (kind: string, done: readonly string[]): string => `<ul class="rows">${(WKH.checklists[kind] ?? []).map((i) => `<li><span>${wkEsc(this.t(`wk_step_${i.id}`))}${i.must ? ` · ${wkEsc(this.t("wk_must"))}` : ""}</span>${done.includes(i.id)
      ? `${this.c.chip("confirmed")}` : this.btn("wk_mark_done", `wk:step:${kind}:${i.id}`)}</li>`).join("")}</ul>`;
    return `${this.head("hr_joining", "wk_checklist_rule")}<h2>${wkEsc(this.t("wk_joining", { done: j.done, total: j.total }))}</h2>${list("joining", this.joining)}
      <h2>${wkEsc(this.t("wk_leaving", { done: l.done, total: l.total }))}</h2>${list("leaving", this.leaving)}
      <p class="note">${wkEsc(this.t(finalPayReady(this.leaving) ? "wk_final_pay_ready" : "wk_final_pay_waits"))}</p>`;
  }
  private hrReviews(): string {
    const counts: [string, number][] = [["self", 1], ["manager", 1], ["peer", 2], ["upward", 4], ["lesson_observation", 1]];   // a school's lesson observation (80.15): named, never anonymous
    return `${this.head("hr_reviews", "wk_reviews_rule")}${this.rows(counts.map(([k, n]) => [wkEsc(this.t(`wk_review_${k}`)), reviewShown(WKH, k, n) ? wkEsc(this.t("wk_answers", { n })) : this.why("wk_hidden_below", { n: WKH.reviews.min_answers })]), ["wk_col_kind", "wk_col_answers"])}
      <p class="note">${wkEsc(this.t(hrAssistMay(WKH, "summarise_review") ? "wk_assist_summary" : "wk_assist_never"))}</p>`;
  }
  private hrPay(): string {
    const figs = payrollFigures(WKH, this.staff.map((x) => ({ id: x.id, kind: x.kind, salary: x.salary, week_minutes: x.id === "LOSTF-1002" ? 2700 : 0, hourly_minor: 1800 })));
    const ok = payChangeOk("hr1", "owner", 60000, 50000, this.payApproved ? "director1" : null);
    return `${this.head("hr_pay", "wk_pay_rule")}${this.rows(figs.map((f) => [this.nm(f.id), this.m(f.gross), this.m(f.overtime)]), ["wk_col_person", "wk_col_gross", "wk_col_overtime"])}
      <p>${wkEsc(this.t("wk_payroll_total", { amount: this.c.money(figs.reduce((a, f) => a + f.gross, 0)) }))}</p><p class="note">${wkEsc(this.t("wk_payroll_draft"))}</p>
      <div class="of-form"><h2>${wkEsc(this.t("wk_pay_review"))}</h2><p>${wkEsc(this.t("wk_pay_over_budget", { amount: this.c.money(60000), budget: this.c.money(50000) }))}</p>
      ${ok ? `<p class="note" role="status">${this.c.chip("confirmed")} ${wkEsc(this.t("wk_pay_approved"))}</p>` : saveBarHtml({ label: this.t("wk_second_approve"), act: "wk:pay2" })}</div>`;
  }
  private hrCases(): string {
    const may = hrCaseMaySee(WKH, this.viewAs === "self" ? "staff" : this.viewAs, false);
    const roles = ["owner", "hr", "manager", "staff"];
    return `${this.head("hr_cases", "wk_cases_rule")}<label class="of-field" for="wkCaseAs"><span>${wkEsc(this.t("wk_view_as"))}</span><select id="wkCaseAs" data-in="wk:viewas">${roles.map((r) =>
      `<option value="${r}"${r === this.viewAs ? " selected" : ""}>${wkEsc(this.t(`wk_viewer_${r}`))}</option>`).join("")}</select></label>
      ${may ? this.rows([[wkEsc(this.t("wk_case_grievance")), wkEsc(this.t("wk_case_step_fact_finding")), "2026-12-04"], [wkEsc(this.t("wk_case_concern")), wkEsc(this.t("wk_case_step_opened")), "2026-11-30"]], ["wk_col_kind", "wk_col_step", "wk_col_due"])
        : `<div class="of-empty"><p>${wkEsc(this.t("wk_cases_hidden"))}</p></div>`}`;
  }
  private hrExpiry(): string {
    const docs: [string, string, string][] = [["LOSTF-1001", "work_permit", "2026-12-02"], ["LOSTF-1002", "licence", "2026-12-24"], ["LOSTF-1004", "contract", "2026-11-20"], ["LOSTF-1003", "medical_certificate", "2027-06-01"], ["LOSTF-1002", "teaching_licence", "2027-01-15"]];
    return `${this.head("hr_expiry", "wk_expiry_rule")}${this.rows(docs.map(([p, k, d]) => { const st = expiryStage(WKH, d, this.c.today);
      return [this.nm(p), wkEsc(this.t(`wk_doc_${k}`)), wkEsc(d), st === "expired" ? `${this.c.chip("failed")} ${wkEsc(this.t("wk_expired"))}` : st === null ? wkEsc(this.t("wk_not_yet")) : wkEsc(this.t("wk_days_left", { n: st }))]; }),
      ["wk_col_person", "wk_col_document", "wk_col_ends", "wk_col_reminder"])}`;
  }

  // ---- LynkProject -------------------------------------------------------------------------------------------------------------
  private pjProjects(): string {
    const money = projectMoney(500000, [120000, 90000], 22500);
    return `${this.head("pj_projects", "wk_projects_rule")}${this.rows([[wkEsc(this.t("wk_sample_project")), wkEsc(this.t("wk_tasks_count", { done: this.tasks.filter((x) => x.state === "done").length, n: this.tasks.length })),
      this.m(money.spent), this.m(money.left), this.m(money.profit)]], ["wk_col_project", "wk_col_tasks", "wk_col_spent", "wk_col_left", "wk_col_profit"])}
      <p class="note">${wkEsc(this.t("wk_over_shown"))}</p>`;
  }
  private pjBoard(): string {
    const cols = ["todo", "doing", "waiting", "done"];
    const card = (x: Task): string => { const canDone = taskDoneOk(PJ, x, this.tasks);
      return `<div class="card"><strong>${wkEsc(this.t(this.titles[x.id]!))}</strong><span class="of-why">${wkEsc(x.id)}</span>
        ${x.state !== "done" ? (canDone ? this.btn("wk_mark_task_done", `wk:task:${x.id}:done`, true) : this.why("wk_waits_on")) : ""}
        ${x.state === "todo" && taskMoveOk(PJ, "todo", "doing") ? this.btn("wk_start", `wk:task:${x.id}:doing`) : ""}</div>`; };
    return `${this.head("pj_board", "wk_board_rule")}<div class="of-board">${cols.map((c) => `<div class="of-col"><h2>${wkEsc(this.t(`wk_task_${c}`))}</h2>${this.tasks.filter((x) => x.state === c).map(card).join("")}</div>`).join("")}</div>`;
  }
  private pjMyWork(): string {
    const w = myWork(PJ, this.tasks, "u1", WK_DAY), late = lateTasks(PJ, this.tasks, WK_DAY), risk = atRiskTasks(PJ, this.tasks, WK_DAY);
    const load = workloadFor(PJ, { u1: 2700, u2: 1200 }, { u2: 2 });
    return `${this.head("pj_mywork")}${PJ.my_work.buckets.map((b) => `<h2>${wkEsc(this.t(`wk_bucket_${b}`))}</h2>${(w[b] ?? []).length ? `<ul class="rows">${(w[b] ?? []).map((id) => `<li><span>${wkEsc(this.t(this.titles[id]!))}</span>${late.includes(id) ? `${this.c.chip("failed")} ${wkEsc(this.t("wk_late"))}` : risk.includes(id) ? wkEsc(this.t("wk_at_risk")) : ""}</li>`).join("")}</ul>` : `<p class="of-why">${wkEsc(this.t("wk_nothing_here"))}</p>`}`).join("")}
      <h2>${wkEsc(this.t("wk_workload"))}</h2>${this.rows(Object.entries(load).map(([p, v]) => [wkEsc(p), wkEsc(this.t("wk_hours", { n: Math.round(v.planned / 60) })), wkEsc(this.t("wk_hours", { n: Math.round(v.can / 60) })), v.over ? `<strong>${wkEsc(this.t("wk_hours", { n: Math.round(v.over / 60) }))}</strong>` : "0"]),
        ["wk_col_person", "wk_col_planned", "wk_col_can", "wk_col_over"])}`;
  }
  private pjTimeline(): string {
    const sch = projectSchedule(this.tasks), sp = sprintStats([{ points: 3, done_day: 1 }, { points: 5, done_day: 3 }, { points: 8, done_day: null }], 5);
    return `${this.head("pj_timeline", "wk_timeline_rule")}${this.rows(this.tasks.map((x) => [wkEsc(this.t(this.titles[x.id]!)), String(sch.start[x.id]), String(sch.finish[x.id]),
      sch.critical.includes(x.id) ? `<strong>${wkEsc(this.t("wk_critical"))}</strong>` : ""]), ["wk_col_task", "wk_col_start_day", "wk_col_finish_day", "wk_col_critical"])}
      <p>${wkEsc(this.t("wk_length", { n: sch.length }))}</p><p>${wkEsc(this.t("wk_velocity", { n: sp.velocity, left: sp.burndown[sp.burndown.length - 1]! }))}</p>`;
  }
  private pjTime(): string {
    const b = billableTime(this.time);
    const rows = this.time.map((e) => [wkEsc(e.by), wkEsc(this.t("wk_minutes", { n: e.minutes })), wkEsc(this.t(e.billable ? "wk_billable" : "wk_not_billable")), e.billed ? wkEsc(this.t("wk_billed")) : e.approved ? `${this.c.chip("confirmed")} ${wkEsc(this.t("wk_approved"))}` : `${this.c.chip("sent")} ${wkEsc(this.t("wk_waiting_approval"))}`]);
    return `${this.head("pj_time", "wk_time_rule")}${this.rows(rows, ["wk_col_person", "wk_col_time", "wk_col_billable", "wk_col_state"])}
      ${this.sheetState === "open" ? `${timeApproveOk("u2", "u1") ? this.btn("wk_approve_sheet", "wk:sheet", true) : ""}${this.why("wk_not_own_time")}` : ""}
      ${b.ids.length ? `<p>${wkEsc(this.t("wk_to_bill", { amount: this.c.money(b.amount), n: b.minutes }))}</p>${this.btn("wk_bill_time", "wk:bill", true)}` : ""}${this.billedNote ? `<p class="note" role="status">${wkEsc(this.billedNote)}</p>` : ""}`;
  }
  private pjChanges(): string {
    return `${this.head("pj_changes", "wk_changes_rule")}${this.rows(this.changes.map((c) => [wkEsc(this.t("wk_change_cost", { amount: this.c.money(c.cost) })), wkEsc(this.t("wk_change_days", { n: c.days })),
      c.state === "raised" ? this.btn("wk_accept", `wk:change:${c.id}:accepted`, true) + this.btn("wk_refuse", `wk:change:${c.id}:refused`) : `${this.c.chip(c.state === "accepted" ? "confirmed" : "failed")} ${wkEsc(this.t(`wk_state_${c.state}`))}`]),
      ["wk_col_cost", "wk_col_days", "wk_col_state"])}`;
  }
  private pjGuests(): string {
    const parts = ["tasks", "files", "comments", "milestones", "budget", "costs", "time_rates", "other_projects"];
    return `${this.head("pj_guests", "wk_guests_rule")}${this.rows(parts.map((p) => [wkEsc(this.t(`wk_part_${p}`)), guestSees(PJ, p, ["p1"], "p1") ? `${this.c.chip("confirmed")} ${wkEsc(this.t("wk_shown"))}` : `${this.c.chip("failed")} ${wkEsc(this.t("wk_never_shown"))}`]),
      ["wk_col_part", "wk_col_guest"])}`;
  }

  // ---- LynkFiles ---------------------------------------------------------------------------------------------------------------
  private flFiles(): string {
    const rows: [string, string, number, boolean][] = [["wk_file_contract", "LOSTF-1002", 2, false], ["wk_file_bill", "LOINV-1003", 1, false], ["wk_file_minutes", "LOPRJ-1001", 3, true]];
    return `${this.head("fl_files", "wk_files_rule")}${listToolbarHtml(this.t, { hint: this.t("wk_hint_file"), chips: [], inputId: "wkFileSearch" })}${this.rows(rows.map(([k, rec, v, hold]) => [wkEsc(this.t(k)), wkEsc(rec), wkEsc(this.t("wk_versions", { n: v })),
      hold ? `<strong>${wkEsc(this.t("wk_legal_hold"))}</strong>` : ""]), ["wk_col_document", "wk_col_record", "wk_col_versions", "wk_col_hold"])}`;
  }
  private flSigning(): string {
    const state = signRequestState(this.signers, this.signed), next = nextSigners(FL, "in_order", this.signers, this.signed);
    return `${this.head("fl_signing", "wk_signing_rule")}${this.rows(this.signers.map((s, i) => [String(i + 1), wkEsc(this.t(s)), this.signed.includes(s) ? `${this.c.chip("confirmed")} ${wkEsc(this.t("wk_signed"))}` : next.includes(s) ? `${this.c.chip("sent")} ${wkEsc(this.t("wk_their_turn"))}` : wkEsc(this.t("wk_waiting"))]),
      ["wk_col_order", "wk_col_signer", "wk_col_state"])}<p>${wkEsc(this.t(`wk_request_${state}`))}</p>`;
  }
  private flApprovals(): string {
    const approvers = ["wk_approver_1", "wk_approver_2"];
    return `${this.head("fl_approvals", "wk_approvals_rule")}${this.rows(approvers.map((a, i) => [String(i + 1), wkEsc(this.t(a)), i + 1 < this.routeStep || this.routeState === "approved" ? `${this.c.chip("confirmed")} ${wkEsc(this.t("wk_approved"))}` : i + 1 === this.routeStep && this.routeState === "waiting" ? this.btn("wk_approve", "wk:route", true) : wkEsc(this.t("wk_waiting"))]),
      ["wk_col_order", "wk_col_approver", "wk_col_state"])}`;
  }
  private flRequests(): string {
    const st = this.requestStateNow;
    return `${this.head("fl_requests", "wk_requests_rule")}${this.rows([[wkEsc(this.t("wk_doc_id_document")), this.nm("LOSTF-1002"), "2026-12-01", `${this.c.chip(st === "checked" ? "confirmed" : st === "received" ? "accepted" : "sent")} ${wkEsc(this.t(`wk_req_${st}`))}`]],
      ["wk_col_document", "wk_col_person", "wk_col_due", "wk_col_state"])}${st === "asked" ? this.btn("wk_mark_received", "wk:req:received") : st === "received" ? this.btn("wk_mark_checked", "wk:req:checked", true) : ""}`;
  }
  private flSharing(): string {
    const now = 1000;
    const links = [{ id: "s1", until: 5000, password_set: true, stopped: this.linkStopped }, { id: "s2", until: 500 }];
    return `${this.head("fl_sharing", "wk_sharing_rule")}${this.rows(links.map((l) => { const [ok, why] = shareOpen(l, now, l.password_set ? true : null);
      return [wkEsc(this.t(l.password_set ? "wk_link_password" : "wk_link_plain")), ok ? `${this.c.chip("confirmed")} ${wkEsc(this.t("wk_link_open"))}` : `${this.c.chip("failed")} ${wkEsc(this.t(`wk_link_${why}`))}`,
        ok ? this.btn("wk_stop_link", `wk:stop:${l.id}`) : ""]; }), ["wk_col_link", "wk_col_state", "wk_col_action"])}`;
  }

  /** A button on a work page; returns true when it was one. */
  act(a: string): boolean {
    if (!a.startsWith("wk:")) return false;
    const [, k = "", v = "", w = ""] = a.split(":");
    if (k === "leave") { const q = this.leave.find((x) => x.id === v); if (q && q.state === "asked" && hrMayApprove(q.staff, "LOSTF-1001")) { q.state = w; this.leaveNote = this.t(`wk_leave_${w}_note`); } }
    else if (k === "step") { const list = v === "joining" ? this.joining : this.leaving; if (!list.includes(w)) list.push(w); }
    else if (k === "pay2") this.payApproved = true;
    else if (k === "task") { const x = this.tasks.find((y) => y.id === v); if (x && taskMoveOk(PJ, x.state ?? "todo", w) && (w !== "done" || taskDoneOk(PJ, x, this.tasks))) x.state = w; }
    else if (k === "sheet") { for (const e of this.time) e.approved = true; this.sheetState = "approved"; }
    else if (k === "bill") { const b = billableTime(this.time); for (const e of this.time) if (b.ids.includes(e.id)) e.billed = true; this.billedNote = this.t("wk_billed_note", { amount: this.c.money(b.amount) }); }
    else if (k === "change") { const c = this.changes.find((x) => x.id === v); if (c && c.by !== "u1") c.state = w; }
    else if (k === "route") { if (this.routeStep < 2) this.routeStep += 1; else this.routeState = "approved"; }
    else if (k === "req") this.requestStateNow = v;
    else if (k === "stop") this.linkStopped = true;
    else if (k === "correct") this.leaveNote = this.t("wk_correction_note");
    return true;
  }
  input(key: string, value: string): boolean {
    if (key === "wk:viewas") { this.viewAs = value; return true; }
    return key.startsWith("wk:");
  }
  reset(): void { this.leaveNote = ""; this.billedNote = ""; }
}
