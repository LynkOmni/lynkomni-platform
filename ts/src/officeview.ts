/** The office services in a browser (OFFICE UPDATE 66.2 to 66.6 and SERVICES UPDATE 67.5; section 4 step D5): LynkAcc at
 *  app.lynkomni.com/accounting, LynkInv at /invoicing, LynkCRM at /crm and LynkStat at /analytics. Every page is drawn from the
 *  real rules (books.ts, invoices.ts, crm.ts, stats.ts) with the shared page parts (pagekit.ts: list toolbar, record header with
 *  the same tabs, save bar); figures shown are computed, never typed, and the sample records are labelled Sample. Words live in
 *  web/office (prefix of_). No DOM here: pages return HTML strings and the host binds data-act and data-in.
 *  Rules kept on screen: the person who enters a bill never approves it; nothing posts on or before the lock date; an issued
 *  invoice never changes (credit note instead); an electronic payment counts only when the provider confirms; a bank match and
 *  a lead score are suggestions; an estimate is always labelled; a measure that divides by zero shows nothing; a branch role
 *  sees only its branch; groups below the minimum are hidden. */
import type { NavRegister } from "./navigation.js";
import { listToolbarHtml, recordHeaderHtml, saveBarHtml } from "./pagekit.js";
import { BOOKS, CHART } from "./books.generated.js";
import { allocate, bankMatch, billMove, budgetVsActual, closeMissing, consolidate, depreciation, mayApprove, revalue, statements, stockCost, taxLine, trialBalance, twoPerson } from "./books.js";
import type { BooksRegister, Line } from "./books.js";
import { INVOICES } from "./invoices.generated.js";
import { ageing, creditCheck, docAllowed, instalments, needsApproval, reminderDue, stages, totals, usage } from "./invoices.js";
import type { InvoicesRegister } from "./invoices.js";
import { CRM } from "./crm.generated.js";
import { duplicates, fieldValueOk, forecast, kindsFor, maySee, merge, stageMove, visibleFields } from "./crm.js";
import { ENTERPRISE } from "./enterprise.generated.js";
import { check, flowSteps, roleProblems, splitCharges } from "./enterprise.js";
import type { EnterpriseRegister } from "./enterprise.js";
import type { CrmRegister } from "./crm.js";
import { STATS } from "./stats.generated.js";
import { cohorts, evaluate, freshness, goal, publicTable, whatIf } from "./stats.js";

type Tf = (key: string, vars?: Record<string, string | number>) => string;
export type OfficeService = "lynkacc" | "lynkinv" | "lynkcrm" | "lynkstat";
export const OFFICE_SERVICES: readonly OfficeService[] = ["lynkacc", "lynkinv", "lynkcrm", "lynkstat"];
export interface OfficeCtx {
  t: Tf; money: (minor: number) => string; icon: (id: string) => string; chip: (state: "queued" | "sent" | "accepted" | "confirmed" | "failed") => string;
  nav: NavRegister; role: string; user: string; today: string; taxBp: () => number;
  /** ADS UPDATE 79: the host's labelled ad slot for LynkStat Free (ts/src/ads.ts), or "" (no gap); drawn last on the overview. */
  ad?: () => string;
}
/** Each service's pages in the register's slots (overview, list, reports, automations, settings); records open from a list. */
export const OFFICE_PAGES: Record<OfficeService, readonly { id: string; slot: string }[]> = {
  lynkacc: [{ id: "acc_overview", slot: "overview" }, { id: "acc_bills", slot: "list" }, { id: "acc_claims", slot: "list" }, { id: "acc_assets", slot: "list" }, { id: "acc_bank", slot: "list" },
    { id: "acc_close", slot: "reports" }, { id: "acc_tax", slot: "reports" }, { id: "acc_currency", slot: "reports" }, { id: "acc_stock", slot: "reports" }, { id: "acc_groups", slot: "reports" },
    { id: "acc_entity", slot: "settings" }, { id: "ent_flows", slot: "settings" }, { id: "ent_roles", slot: "settings" }, { id: "ent_entities", slot: "settings" }, { id: "ent_movein", slot: "settings" }],
  lynkinv: [{ id: "inv_overview", slot: "overview" }, { id: "inv_list", slot: "list" }, { id: "inv_new", slot: "list" }, { id: "inv_documents", slot: "list" }, { id: "inv_credit", slot: "reports" }, { id: "inv_ways", slot: "settings" }, { id: "inv_einvoice", slot: "settings" }],
  lynkcrm: [{ id: "crm_list", slot: "overview" }, { id: "crm_orgs", slot: "list" }, { id: "crm_cases", slot: "list" }, { id: "crm_duplicates", slot: "list" }, { id: "crm_pipeline", slot: "reports" }, { id: "crm_fields", slot: "settings" }, { id: "crm_teams", slot: "settings" }],
  lynkstat: [{ id: "stat_overview", slot: "overview" }, { id: "stat_measures", slot: "list" }, { id: "stat_whatif", slot: "list" }, { id: "stat_cohorts", slot: "reports" }, { id: "stat_public", slot: "settings" }],
};
export const OFFICE_PATHS: Record<OfficeService, string> = { lynkacc: "/accounting", lynkinv: "/invoicing", lynkcrm: "/crm", lynkstat: "/analytics" };
const OF_B = BOOKS as unknown as BooksRegister, OF_I = INVOICES as unknown as InvoicesRegister, OF_C = CRM as unknown as CrmRegister, OF_E = ENTERPRISE as unknown as EnterpriseRegister;
const ofEsc = (s: string): string => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// ---- the sample business (labelled Sample on every page) -------------------------------------------------------------------------
const ENTRIES: { lines: Line[] }[] = [
  { lines: [["1000", 500000, 0], ["3000", 0, 500000]] },          // owner's money in
  { lines: [["1100", 820000, 0], ["4000", 0, 820000]] },          // invoices issued
  { lines: [["1020", 610000, 0], ["1100", 0, 610000]] },          // invoices paid to the bank
  { lines: [["5000", 300000, 0], ["1300", 0, 300000]] },          // cost of goods sold
  { lines: [["1300", 450000, 0], ["2000", 0, 450000]] },          // stock bought on credit
  { lines: [["6100", 120000, 0], ["1020", 0, 120000]] },          // rent
  { lines: [["6400", 45000, 0], ["1000", 0, 45000]] },            // phone and internet
];
interface Bill { id: string; supplier: string; total: number; state: string; preparer: string; due: string }
interface Inv { id: string; number: number; customer: string; total: number; paid: number; credited?: number; state: string; issued: string; due: string; lines: { name: string; qty: number; unit: number }[] }
interface Person { id: string; name: string; email?: string; phone?: string; created: string; owner: string; team: string; tags: string[]; consent: boolean }
interface Deal { id: string; customer: string; amount: number; stage: string }

export class OfficeView {
  bills: Bill[] = [
    { id: "b1", supplier: "of_sample_supplier_1", total: 450000, state: "awaiting_approval", preparer: "u-amina", due: "2026-11-28" },
    { id: "b2", supplier: "of_sample_supplier_2", total: 120000, state: "approved", preparer: "u-jean", due: "2026-11-25" },
    { id: "b3", supplier: "of_sample_supplier_3", total: 45000, state: "draft", preparer: "u-owner", due: "2026-12-05" },
  ];
  invoices: Inv[] = [
    { id: "LOINV-1001", number: 1, customer: "c1", total: 250000, paid: 250000, state: "paid", issued: "2026-09-01", due: "2026-09-15", lines: [{ name: "of_sample_item_1", qty: 5000, unit: 50000 }] },
    { id: "LOINV-1002", number: 2, customer: "c2", total: 320000, paid: 100000, state: "part_paid", issued: "2026-10-02", due: "2026-10-16", lines: [{ name: "of_sample_item_2", qty: 2000, unit: 160000 }] },
    { id: "LOINV-1003", number: 3, customer: "c1", total: 180000, paid: 0, state: "overdue", issued: "2026-08-10", due: "2026-08-24", lines: [{ name: "of_sample_item_1", qty: 3600, unit: 50000 }] },
    { id: "LOINV-1004", number: 4, customer: "c3", total: 70000, paid: 0, state: "issued", issued: "2026-11-15", due: "2026-11-29", lines: [{ name: "of_sample_item_3", qty: 1000, unit: 70000 }] },
  ];
  people: Person[] = [
    { id: "LOCST-1001", name: "of_sample_customer_1", email: "amina@example.com", created: "2025-03-02", owner: "u-amina", team: "north", tags: ["of_tag_regular"], consent: true },
    { id: "LOCST-1002", name: "of_sample_customer_2", phone: "0788000222", created: "2025-07-19", owner: "u-jean", team: "south", tags: [], consent: false },
    { id: "LOCST-1003", name: "of_sample_customer_3", email: "office@example.org", created: "2026-01-11", owner: "u-amina", team: "north", tags: ["of_tag_organisation"], consent: true },
    { id: "LOCST-1004", name: "of_sample_customer_1", email: "AMINA@example.com ", created: "2026-10-30", owner: "u-jean", team: "south", tags: [], consent: false },
  ];
  deals: Deal[] = [{ id: "d1", customer: "LOCST-1001", amount: 400000, stage: "new" }, { id: "d2", customer: "LOCST-1003", amount: 900000, stage: "proposal" }, { id: "d3", customer: "LOCST-1002", amount: 150000, stage: "qualified" }];
  bank = [{ id: "s1", amount: 610000, day: 20402, ref: "LOINV-1001" }, { id: "s2", amount: -120000, day: 20405, ref: "" }, { id: "s3", amount: -9900, day: 20406, ref: "" }];
  book = [{ id: "e1", amount: 610000, day: 20401, ref: "LOINV-1001" }, { id: "e2", amount: -120000, day: 20405, ref: "" }];
  closed: string[] = ["invoices_issued", "bills_entered"];
  lockDate = ""; lockAsked = false;
  matched: string[] = [];
  billFilter = "all"; invFilter = "all"; crmFilter = "all"; query = "";
  record = ""; tab = "details";
  draft = { customer: "c1", name: "", qty: "", price: "" };
  merged: { kept: string; gone: string } | null = null;
  measure = "(sales - cost_of_sales) * 100 / sales"; whatif = { price: "10", cost: "0", staff: "0" };
  issuedNote = ""; crediting = false; credit = { amount: "", reason: "" }; creditNote = "";
  constructor(private c: OfficeCtx) {}

  private t = (k: string, v?: Record<string, string | number>): string => this.c.t(k, v);
  private sample(): string { return `<p class="of-sample">${this.c.icon("ui-info")}<span>${ofEsc(this.t("of_sample_note"))}</span></p>`; }
  private empty(word: string, next: string, act: string): string { return `<div class="of-empty"><p>${ofEsc(this.t(word))}</p><button class="secondary" data-act="${ofEsc(act)}">${ofEsc(this.t(next))}</button></div>`; }
  private name(k: string): string { return k.startsWith("of_") ? this.t(k) : k; }
  pages(s: OfficeService): readonly { id: string; slot: string }[] { return OFFICE_PAGES[s]; }
  title(page: string): string { return this.t(`of_page_${page}`); }
  /** The line under the address bar: the office services work fully in any signed-in browser. */
  browserNote(): string { return `<p class="note" role="note">${this.c.icon("ui-info")} ${ofEsc(this.t("of_works_in_browser"))}</p>`; }

  draw(s: OfficeService, page: string): string {
    const body = this.record ? (s === "lynkinv" ? this.invoiceRecord() : s === "lynkcrm" ? this.personRecord() : "") : "";
    if (body) return body;
    switch (page) {
      case "acc_overview": return this.accOverview();
      case "acc_bills": return this.accBills();
      case "acc_bank": return this.accBank();
      case "acc_close": return this.accClose();
      case "inv_overview": return this.invOverview();
      case "inv_list": return this.invList();
      case "inv_new": return this.invNew();
      case "crm_list": return this.crmList();
      case "crm_duplicates": return this.crmDuplicates();
      case "crm_pipeline": return this.crmPipeline();
      case "acc_claims": return this.accClaims();
      case "acc_assets": return this.accAssets();
      case "acc_tax": return this.accTax();
      case "acc_currency": return this.accCurrency();
      case "acc_stock": return this.accStock();
      case "acc_groups": return this.accGroups();
      case "acc_entity": return this.accEntity();
      case "ent_flows": return this.entFlows();
      case "ent_roles": return this.entRoles();
      case "ent_entities": return this.entEntities();
      case "ent_movein": return this.entMoveIn();
      case "inv_documents": return this.invDocuments();
      case "inv_credit": return this.invCredit();
      case "inv_ways": return this.invWays();
      case "inv_einvoice": return this.invEInvoice();
      case "crm_orgs": return this.crmOrgs();
      case "crm_cases": return this.crmCases();
      case "crm_fields": return this.crmFields();
      case "crm_teams": return this.crmTeams();
      case "stat_overview": return this.statOverview();
      case "stat_measures": return this.statMeasures();
      case "stat_whatif": return this.statWhatIf();
      case "stat_cohorts": return this.statCohorts();
      case "stat_public": return this.statPublic();
      default: return "";
    }
  }


  // ---- OFFICE UPDATE 66.2 to 66.6 in full (section 4 row 66.10): every page from the real rules, sample data labelled Sample ----
  claims = [{ id: "cl1", who: "of_sample_staff_1", what: "of_claim_travel", total: 38000, state: "submitted", by: "u-amina" }, { id: "cl2", who: "of_sample_staff_2", what: "of_claim_meal", total: 12500, state: "approved", by: "u-jean" }];
  entityKind = "business";
  private head(page: string): string { return `<h1>${ofEsc(this.title(page))}</h1>${this.sample()}`; }
  private rows(cells: readonly (readonly string[])[], head?: readonly string[]): string {
    return `<table class="of-table">${head ? `<thead><tr>${head.map((h) => `<th>${ofEsc(this.t(h))}</th>`).join("")}</tr></thead>` : ""}<tbody>${cells.map((r) => `<tr>${r.map((c, i) => `<td${i > 0 && /^[-\d]/.test(c) ? ' class="of-num"' : ""}>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  }
  private m(n: number): string { return ofEsc(this.c.money(n)); }
  private accClaims(): string {
    const rows = this.claims.map((c) => [ofEsc(this.t(c.who)), ofEsc(this.t(c.what)), this.m(c.total), `${this.c.chip(c.state === "approved" ? "confirmed" : "sent")} ${ofEsc(this.t(`of_claim_${c.state}`))}`,
      c.state === "submitted" ? (mayApprove(c.by, this.c.user) ? `<button class="primary" data-act="of:claim:${c.id}">${ofEsc(this.t("of_do_approve"))}</button>` : `<span class="of-why">${ofEsc(this.t("of_not_own_bill"))}</span>`) : ""]);
    return `${this.head("acc_claims")}${this.rows(rows, ["of_col_who", "of_col_what", "of_col_amount", "of_col_state", "of_col_action"])}<p class="note">${ofEsc(this.t("of_claims_rule"))}</p>`;
  }
  private accAssets(): string {
    const cost = 1200000, residual = 200000, years = 4, per = depreciation(cost, residual, years);
    let left = cost;
    const rows = per.map((d, i) => { left -= d; return [ofEsc(this.t("of_year_n", { n: i + 1 })), this.m(d), this.m(left)]; });
    return `${this.head("acc_assets")}<p>${ofEsc(this.t("of_asset_line", { name: this.t("of_sample_asset"), cost: this.c.money(cost), years }))}</p>${this.rows(rows, ["of_col_year", "of_col_charge", "of_col_book_value"])}<p class="note">${ofEsc(this.t("of_assets_rule"))}</p>`;
  }
  private accTax(): string {
    const bp = this.c.taxBp();
    const line = taxLine(100000, [{ kind: "sales", rate_bp: bp }, { kind: "withholding", rate_bp: 300 }]);
    const rows = line.taxes.map((x) => [ofEsc(this.t(`of_tax_${x.kind}`)), ofEsc(`${(x.rate_bp / 100).toFixed(2)}%`), this.m(x.amount)]);
    return `${this.head("acc_tax")}${this.rows([[ofEsc(this.t("of_net")), "", this.m(line.net)], ...rows, [ofEsc(this.t("of_customer_pays")), "", this.m(line.to_pay)]], ["of_col_line", "of_col_rate", "of_col_amount"])}<p class="note">${ofEsc(this.t("of_tax_rule"))}</p>`;
  }
  private accCurrency(): string {
    const r = revalue([{ id: "LOINV-2001", foreign_minor: 10000, booked_minor: 1300000, side: "owed_to_us" }], 135, 1);
    return `${this.head("acc_currency")}${this.rows([["LOINV-2001", this.m(1300000), this.m(r.items[0]!.new_minor), this.m(r.gain)]], ["of_col_record", "of_col_booked", "of_col_today", "of_col_gain"])}<p class="note">${ofEsc(this.t("of_currency_rule"))}</p>`;
  }
  private accStock(): string {
    const moves = [{ kind: "in" as const, qty: 10000, unit_cost_minor: 1000 }, { kind: "in" as const, qty: 10000, unit_cost_minor: 1200 }, { kind: "out" as const, qty: 12000 }];
    const rows = ((OF_B as unknown as { stock: { methods: string[] } }).stock.methods).map((mth: string) => { const r = stockCost(moves, mth); return [ofEsc(this.t(`of_stock_${mth}`)), this.m(r.cogs), this.m(r.value)]; });
    return `${this.head("acc_stock")}${this.rows(rows, ["of_col_method", "of_col_cogs", "of_col_value"])}<p class="note">${ofEsc(this.t("of_stock_rule"))}</p>`;
  }
  private accGroups(): string {
    const split = allocate(300000, [5000, 3000, 2000]);
    const depts = ["of_dept_shop", "of_dept_kitchen", "of_dept_office"];
    const bva = budgetVsActual({ of_dept_shop: 160000, of_dept_kitchen: 80000, of_dept_office: 60000 }, { of_dept_shop: split[0]!, of_dept_kitchen: split[1]!, of_dept_office: split[2]! });
    const rows = depts.map((d) => { const x = bva.find((r) => r.key === d); return [ofEsc(this.t(d)), this.m(x?.budget ?? 0), this.m(x?.actual ?? 0), this.m(x?.diff ?? 0)]; });
    return `${this.head("acc_groups")}<p>${ofEsc(this.t("of_groups_split", { total: this.c.money(300000) }))}</p>${this.rows(rows, ["of_col_department", "of_col_budget", "of_col_actual", "of_col_difference"])}<p class="note">${ofEsc(this.t("of_groups_rule"))}</p>`;
  }
  private accEntity(): string {
    const kinds = Object.keys(OF_B.entity_tools as Record<string, string[]>);
    const tools = (OF_B.entity_tools as Record<string, string[]>)[this.entityKind] ?? [];
    return `${this.head("acc_entity")}<label class="of-field" for="ofEntity"><span>${ofEsc(this.t("of_entity_kind"))}</span><select id="ofEntity" data-in="of:entity">${kinds.map((k) => `<option value="${ofEsc(k)}"${k === this.entityKind ? " selected" : ""}>${ofEsc(this.t(`of_entity_${k}`))}</option>`).join("")}</select></label>
      <ul class="of-list">${tools.map((x) => `<li>${ofEsc(this.t(`of_tool_${x}`))}</li>`).join("")}</ul><p class="note">${ofEsc(this.t("of_entity_rule"))}</p>`;
  }
  private entFlows(): string {
    const flow = [{ role: "manager", from_minor: 0 }, { role: "accountant", from_minor: 500000 }, { role: "owner", from_minor: 2000000 }];
    const rows = [100000, 800000, 2500000].map((a) => [this.m(a), flowSteps(OF_E, flow, a).map((st) => ofEsc(this.t(`of_role_${st.role}`))).join(" → ")]);
    return `${this.head("ent_flows")}${this.rows(rows, ["of_col_amount", "of_col_steps"])}<p class="note">${ofEsc(this.t("of_flows_rule"))}</p>`;
  }
  private entRoles(): string {
    const ok = roleProblems(OF_E, { acc: ["view", "prepare"], inv: ["view"] });
    const bad = roleProblems(OF_E, { acc: ["view", "prepare", "approve"] });
    const line = (key: string, probs: readonly unknown[]): string[] => [ofEsc(this.t(key)), `${this.c.chip(probs.length ? "failed" : "confirmed")} ${ofEsc(this.t(probs.length ? "of_role_kept_apart" : "of_role_fine"))}`];
    return `${this.head("ent_roles")}${this.rows([line("of_role_sample_clerk", ok), line("of_role_sample_both", bad)], ["of_col_role", "of_col_check"])}<p class="note">${ofEsc(this.t("of_roles_rule"))}</p>`;
  }
  private entEntities(): string {
    const a = { id: "e1", tb: { "1000": 900000, "3000": -500000, "4000": -600000, "5000": 200000 }, num: 1, den: 1 };
    const b = { id: "e2", tb: { "1000": 300000, "3000": -200000, "4000": -150000, "5000": 50000 }, num: 1, den: 1 };
    const c = consolidate(OF_B, CHART, [a, b]) as { statements?: { profit: number }; profit?: number; combined?: Record<string, number> };
    const profit = (x: Record<string, number>): number => statements(CHART, x).profit;
    const charges = splitCharges(90000, { of_dept_shop: 5000, of_dept_kitchen: 3000, of_dept_office: 2000 });
    return `${this.head("ent_entities")}${this.rows([[ofEsc(this.t("of_entity_main")), this.m(profit(a.tb))], [ofEsc(this.t("of_entity_branch")), this.m(profit(b.tb))], [`<strong>${ofEsc(this.t("of_entity_group"))}</strong>`, this.m(c.combined ? profit(c.combined) : profit(a.tb) + profit(b.tb))]], ["of_col_entity", "of_col_profit"])}
      <h2>${ofEsc(this.t("of_charges"))}</h2>${this.rows(Object.entries(charges).map(([d, v]) => [ofEsc(this.t(d)), this.m(v)]), ["of_col_department", "of_col_amount"])}<p class="note">${ofEsc(this.t("of_entities_rule"))}</p>`;
  }
  private entMoveIn(): string {
    const r = check(OF_E, "customers", ["ref", "name", "email"], [["C1", "of_sample_customer_1", "a@example.com"], ["C1", "of_sample_customer_2", ""], ["C3", "", ""]]) as { ok: boolean; count: number; errors: { row: number; column: string; issue: string }[] };
    const rows = r.errors.map((e) => [String(e.row), ofEsc(e.column), ofEsc(this.t(`of_issue_${e.issue}`))]);
    return `${this.head("ent_movein")}<p>${this.c.chip(r.ok ? "confirmed" : "failed")} ${ofEsc(this.t(r.ok ? "of_movein_ok" : "of_movein_errors", { n: r.errors.length, rows: r.count }))}</p>${this.rows(rows, ["of_col_row", "of_col_column", "of_col_problem"])}<p class="note">${ofEsc(this.t("of_movein_rule"))}</p>`;
  }
  private invDocuments(): string {
    const docs = Object.keys(OF_I.documents);
    const rows = docs.map((d) => { const ok = docAllowed(OF_I, d, null); return [ofEsc(this.t(`of_doc_${d}`)), `${this.c.chip(ok ? "confirmed" : "queued")} ${ofEsc(this.t(ok ? "of_doc_ready" : "of_doc_country"))}`]; });
    return `${this.head("inv_documents")}${this.rows(rows, ["of_col_document", "of_col_state"])}<p class="note">${ofEsc(this.t("of_documents_rule"))}</p>`;
  }
  private invCredit(): string {
    const open = this.invoices.filter((i) => i.total > i.paid).map((i) => ({ id: i.id, due: i.due, outstanding: i.total - i.paid }));
    const ag = ageing(OF_I, open, this.c.today);
    const cc = creditCheck(500000, 320000, 250000) as { warn: boolean; over_by: number };
    const rem = open.map((o) => [ofEsc(o.id), this.m(o.outstanding), ofEsc(this.t(`of_reminder_${String(reminderDue(OF_I, o.due, this.c.today) ?? "none")}`))]);
    return `${this.head("inv_credit")}${this.rows(OF_I.ageing.buckets.map((b) => [ofEsc(this.t(`of_bucket_${b.id}`)), this.m(ag.totals[b.id] ?? 0)]), ["of_col_bucket", "of_col_amount"])}
      ${this.rows(rem, ["of_col_record", "of_col_amount", "of_col_reminder"])}<p class="of-why">${ofEsc(this.t(cc.warn ? "of_credit_warn" : "of_credit_ok", { over: this.c.money(cc.over_by) }))}</p><p class="note">${ofEsc(this.t("of_credit_rule"))}</p>`;
  }
  private invWays(): string {
    const ins = instalments(OF_I, 300000, 3, this.c.today) as { date: string; amount: number }[];
    const st = stages(900000, [3000, 4000, 3000]);
    const use = usage(1500, [{ up_to: 1000, unit_minor: 100 }, { up_to: null, unit_minor: 80 }]);
    return `${this.head("inv_ways")}<h2>${ofEsc(this.t("of_way_instalments"))}</h2>${this.rows(ins.map((x) => [ofEsc(x.date), this.m(x.amount)]), ["of_col_date", "of_col_amount"])}
      <h2>${ofEsc(this.t("of_way_stages"))}</h2>${this.rows(st.map((v, i) => [ofEsc(this.t("of_stage_n", { n: i + 1 })), this.m(v)]), ["of_col_stage", "of_col_amount"])}
      <h2>${ofEsc(this.t("of_way_usage"))}</h2><p>${ofEsc(this.t("of_usage_line", { amount: this.c.money(use) }))}</p><p class="note">${ofEsc(this.t("of_ways_rule"))}</p>`;
  }
  private invEInvoice(): string {
    return `${this.head("inv_einvoice")}<p>${this.c.chip("queued")} ${ofEsc(this.t("of_einvoice_off"))}</p><p class="note">${ofEsc(this.t("of_einvoice_rule"))}</p>`;
  }
  private crmOrgs(): string {
    const kinds = kindsFor(OF_C, this.entityKind) as string[];
    const rels = (OF_C.relations as { kinds: string[] }).kinds;
    return `${this.head("crm_orgs")}<h2>${ofEsc(this.t("of_record_kinds"))}</h2><ul class="of-list">${kinds.map((k) => `<li>${ofEsc(this.t(`of_kind_${k}`))}</li>`).join("")}</ul>
      <h2>${ofEsc(this.t("of_relations"))}</h2><ul class="of-list">${rels.filter((r) => r !== "guardian_of").map((r) => `<li>${ofEsc(this.t(`of_rel_${r}`))}</li>`).join("")}</ul><p class="note">${ofEsc(this.t("of_orgs_rule"))}</p>`;
  }
  private crmCases(): string {
    const pr = (OF_C.cases as { priorities: Record<string, number> }).priorities;
    const cases = [{ id: "LOCASE-1001", p: "high", age: 10 }, { id: "LOCASE-1002", p: "normal", age: 30 }, { id: "LOCASE-1003", p: "urgent", age: 1 }];
    const rows = cases.map((c) => { const late = c.age > (pr[c.p] ?? 24); return [ofEsc(c.id), ofEsc(this.t(`of_prio_${c.p}`)), ofEsc(this.t("of_hours", { n: pr[c.p] ?? 24 })), `${this.c.chip(late ? "failed" : "sent")} ${ofEsc(this.t(late ? "of_case_late" : "of_case_on_time"))}`]; });
    return `${this.head("crm_cases")}${this.rows(rows, ["of_col_case", "of_col_priority", "of_col_promise", "of_col_state"])}<p class="note">${ofEsc(this.t("of_cases_rule"))}</p>`;
  }
  private crmFields(): string {
    const fields: [string, string, unknown][] = [["of_field_birthday", "date", "2026-02-30"], ["of_field_size", "choice", "M"], ["of_field_deposit", "money", 12.5], ["of_field_members", "number", 4]];
    const rows = fields.map(([n, ty, v]) => [ofEsc(this.t(n)), ofEsc(this.t(`of_ftype_${ty}`)), ofEsc(String(v)), `${this.c.chip(fieldValueOk(ty, v) ? "confirmed" : "failed")} ${ofEsc(this.t(fieldValueOk(ty, v) ? "of_field_ok" : "of_field_bad"))}`]);
    return `${this.head("crm_fields")}${this.rows(rows, ["of_col_field", "of_col_type", "of_col_value", "of_col_check"])}<p class="note">${ofEsc(this.t("of_fields_rule"))}</p>`;
  }
  private crmTeams(): string {
    const viewers = [{ key: "of_role_owner", v: { user: "u-owner", role: "owner", team: null } }, { key: "of_role_manager", v: { user: "u-mgr", role: "manager", team: "north" } }, { key: "of_role_staff", v: { user: "u-jean", role: "staff", team: "south" } }];
    const rows = viewers.map((x) => [ofEsc(this.t(x.key)), String(this.people.filter((p) => maySee(OF_C, x.v as never, { owner: p.owner, team: p.team })).length)]);
    return `${this.head("crm_teams")}${this.rows(rows, ["of_col_role", "of_col_sees"])}<p class="note">${ofEsc(this.t("of_teams_rule"))}</p>`;
  }

  // ---- LynkAcc -------------------------------------------------------------------------------------------------------------
  private accOverview(): string {
    const st = statements(CHART, trialBalance(CHART, ENTRIES));
    const row = (k: string, v: number, strong = false): string => `<tr${strong ? ' class="of-total"' : ""}><td>${ofEsc(this.t(k))}</td><td class="of-num">${ofEsc(this.c.money(v))}</td></tr>`;
    return `<h1>${ofEsc(this.title("acc_overview"))}</h1>${this.sample()}
      <h2>${ofEsc(this.t("of_profit_loss"))}</h2><table class="of-table"><tbody>${row("of_income", st.income)}${row("of_fig_cost_of_sales", st.cost_of_sales)}${row("of_gross", st.gross, true)}${row("of_fig_expenses", st.expenses)}${row("of_profit", st.profit, true)}</tbody></table>
      <h2>${ofEsc(this.t("of_balance_sheet"))}</h2><table class="of-table"><tbody>${row("of_assets", st.assets, true)}${row("of_liabilities", st.liabilities)}${row("of_equity_with_profit", st.equity_with_profit)}</tbody></table>
      <p class="note">${this.c.chip(st.balanced ? "confirmed" : "failed")} ${ofEsc(this.t(st.balanced ? "of_balanced" : "of_not_balanced"))}</p>`;
  }
  private accBills(): string {
    const chips = ["all", "to_approve", "to_pay"].map((id) => ({ id, label: this.t(`of_filter_${id}`), on: this.billFilter === id }));
    const shown = this.bills.filter((b) => this.billFilter === "all" || (this.billFilter === "to_approve" ? b.state === "awaiting_approval" : b.state === "approved"))
      .filter((b) => !this.query || this.name(b.supplier).toLowerCase().includes(this.query.toLowerCase()));
    const rows = shown.map((b) => {
      const own = !mayApprove(b.preparer, this.c.user);
      const next = b.state === "draft" ? "submit" : b.state === "awaiting_approval" ? "approve" : b.state === "approved" ? "pay_all" : "";
      const btn = next === "approve" && own ? `<span class="of-why">${ofEsc(this.t("of_not_own_bill"))}</span>`
        : next ? `<button class="${next === "approve" ? "primary" : "secondary"}" data-act="of:bill:${b.id}:${next}">${ofEsc(this.t(next === "submit" ? "of_send_for_approval" : `of_do_${next}`))}</button>` : "";
      return `<li><span>${ofEsc(this.name(b.supplier))}</span><span class="of-num">${ofEsc(this.c.money(b.total))}</span><span>${ofEsc(this.t(`of_state_${b.state}`))}</span><span>${ofEsc(this.t("of_due_on", { date: b.due }))}</span>${btn}</li>`;
    }).join("");
    return `<h1>${ofEsc(this.title("acc_bills"))}</h1>${this.sample()}${listToolbarHtml(this.t, { query: this.query, hint: this.t("of_hint_supplier"), chips, act: "of:billfilter", inputId: "ofSearch" })}
      ${rows ? `<ul class="rows">${rows}</ul>` : this.empty("of_no_bills", "of_show_all", "of:billfilter:all")}<p class="note">${ofEsc(this.t("of_paid_when_confirmed"))}</p>`;
  }
  private accBank(): string {
    const m = bankMatch(OF_B, this.bank, this.book);
    const pairs = m.matched.map(([lineId]) => {
      const line = this.bank.find((x) => x.id === lineId)!, done = this.matched.includes(lineId);
      return `<li><span>${ofEsc(this.c.money(line.amount))}${line.ref ? ` · ${ofEsc(line.ref)}` : ""}</span><span class="of-tag">${ofEsc(this.t("of_suggestion"))}</span>${done ? this.c.chip("confirmed") : `<button class="primary" data-act="of:match:${lineId}">${ofEsc(this.t("of_confirm_match"))}</button>`}</li>`;
    }).join("");
    const left = m.unmatched.map((id: string) => { const line = this.bank.find((x) => x.id === id)!; return `<li><span>${ofEsc(this.c.money(line.amount))}</span><span>${ofEsc(this.t("of_no_match"))}</span></li>`; }).join("");
    return `<h1>${ofEsc(this.title("acc_bank"))}</h1>${this.sample()}<p class="note">${ofEsc(this.t("of_bank_from_file"))}</p>
      <h2>${ofEsc(this.t("of_matches"))}</h2>${pairs ? `<ul class="rows">${pairs}</ul>` : this.empty("of_nothing_to_match", "of_import_statement", "of:noop")}
      <h2>${ofEsc(this.t("of_unmatched"))}</h2>${left ? `<ul class="rows">${left}</ul>` : `<p class="note">${ofEsc(this.t("of_all_matched"))}</p>`}`;
  }
  private accClose(): string {
    const missing = closeMissing(OF_B, this.closed), lock = twoPerson(OF_B, "lock_date", this.c.user, null);
    return `<h1>${ofEsc(this.title("acc_close"))}</h1>${this.sample()}<ul class="rows">${OF_B.closing.checklist.map((k) => { const done = this.closed.includes(k);
        return `<li><span>${ofEsc(this.t(`of_close_${k}`))}</span><button class="switch${done ? " on" : ""}" role="switch" aria-checked="${done}" data-act="of:close:${k}">${ofEsc(this.t(done ? "of_done" : "of_to_do"))}</button></li>`; }).join("")}</ul>
      <p class="${missing.length ? "warn" : "note"}">${ofEsc(missing.length ? this.t("of_still_missing", { n: missing.length }) : this.t("of_ready_to_close"))}</p>
      <label class="of-field" for="ofLock"><span>${ofEsc(this.t("of_lock_date"))}</span><input id="ofLock" type="date" data-in="of:lock" value="${ofEsc(this.lockDate)}" placeholder="${ofEsc(this.t("of_hint_date"))}"></label>
      <p class="note">${ofEsc(this.t("of_lock_rule"))}</p>${this.lockAsked ? `<p class="note">${this.c.chip("sent")} ${ofEsc(this.t("of_second_person_asked"))}</p>` : ""}
      ${saveBarHtml({ label: this.t(lock.needed ? "of_ask_second_person" : "of_lock"), act: "of:lock", disabled: !this.lockDate || missing.length > 0 })}`;
  }

  // ---- LynkInv -------------------------------------------------------------------------------------------------------------
  private owed(v: Inv): number { return v.total - v.paid - (v.credited ?? 0); }
  private open(): { id: string; outstanding: number; due: string }[] { return this.invoices.filter((v) => this.owed(v) > 0).map((v) => ({ id: v.id, outstanding: this.owed(v), due: v.due })); }
  private invOverview(): string {
    const a = ageing(OF_I, this.open(), this.c.today);
    const owed = this.open().reduce((s, v) => s + v.outstanding, 0);
    return `<h1>${ofEsc(this.title("inv_overview"))}</h1>${this.sample()}<div class="cards"><div class="card"><span>${ofEsc(this.t("of_owed_to_you"))}</span><strong>${ofEsc(this.c.money(owed))}</strong></div>
      <div class="card"><span>${ofEsc(this.t("of_fig_invoices_open"))}</span><strong>${this.open().length}</strong></div></div>
      <h2>${ofEsc(this.t("of_ageing"))}</h2><table class="of-table"><tbody>${OF_I.ageing.buckets.map((b) => `<tr><td>${ofEsc(this.t(`of_age_${b.id}`))}</td><td class="of-num">${ofEsc(this.c.money(a.totals[b.id] ?? 0))}</td></tr>`).join("")}</tbody></table>
      <button class="primary" data-act="of:go:inv_new">${ofEsc(this.t("of_page_inv_new"))}</button>`;
  }
  private invList(): string {
    const chips = ["all", "unpaid", "overdue", "paid"].map((id) => ({ id, label: this.t(id === "paid" || id === "overdue" ? `of_state_${id}` : `of_filter_${id}`), on: this.invFilter === id }));
    const shown = this.invoices.filter((v) => this.invFilter === "all" || (this.invFilter === "paid" ? v.state === "paid" : this.invFilter === "overdue" ? v.state === "overdue" : this.owed(v) > 0))
      .filter((v) => !this.query || `${v.number} ${this.custName(v.customer)}`.toLowerCase().includes(this.query.toLowerCase()));
    const rows = shown.map((v) => `<li><button class="link" data-act="of:inv:${v.id}">${ofEsc(this.t("of_invoice_no", { n: v.number }))}</button><span>${ofEsc(this.custName(v.customer))}</span><span class="of-num">${ofEsc(this.c.money(v.total))}</span><span>${ofEsc(this.t(`of_state_${v.state}`))}</span></li>`).join("");
    return `<h1>${ofEsc(this.title("inv_list"))}</h1>${this.sample()}${listToolbarHtml(this.t, { query: this.query, hint: this.t("of_hint_invoice"), chips, act: "of:invfilter", inputId: "ofSearch" })}
      ${rows ? `<ul class="rows">${rows}</ul>` : this.empty("of_no_invoices", "of_page_inv_new", "of:go:inv_new")}${this.issuedNote ? `<p class="note" role="status">${ofEsc(this.issuedNote)}</p>` : ""}`;
  }
  private custName(id: string): string { return this.t(`of_sample_customer_${id.slice(1)}`); }
  private invoiceRecord(): string {
    const v = this.invoices.find((x) => x.id === this.record); if (!v) return "";
    const head = recordHeaderHtml(this.c.nav, this.t, { title: this.t("of_invoice_no", { n: v.number }), state: `<span class="of-tag">${ofEsc(this.t(`of_state_${v.state}`))}</span>`,
      main: this.owed(v) > 0 && !this.crediting ? { label: this.t("of_credit_note"), act: "of:creditnote" } : undefined, current: this.tab, act: "of:tab" });
    let body = "";
    if (this.tab === "details") body = `<table class="of-table"><tbody>${v.lines.map((l) => `<tr><td>${ofEsc(this.t(l.name))}</td><td class="of-num">${ofEsc(this.t("of_qty", { n: l.qty / 1000 }))}</td><td class="of-num">${ofEsc(this.c.money(l.unit))}</td></tr>`).join("")}
      <tr class="of-total"><td>${ofEsc(this.t("of_total"))}</td><td></td><td class="of-num">${ofEsc(this.c.money(v.total))}</td></tr><tr><td>${ofEsc(this.t("of_state_paid"))}</td><td></td><td class="of-num">${ofEsc(this.c.money(v.paid))}</td></tr>${v.credited ? `<tr><td>${ofEsc(this.t("of_state_credited"))}</td><td></td><td class="of-num">${ofEsc(this.c.money(v.credited))}</td></tr>` : ""}<tr class="of-total"><td>${ofEsc(this.t("of_still_owed"))}</td><td></td><td class="of-num">${ofEsc(this.c.money(this.owed(v)))}</td></tr></tbody></table>
      <p class="note">${ofEsc(this.t("of_never_changes"))}</p>${this.crediting ? this.creditForm(v) : ""}${this.creditNote ? `<p class="note" role="status">${ofEsc(this.creditNote)}</p>` : ""}`;
    else if (this.tab === "activity") body = `<ul class="rows"><li><span>${ofEsc(this.t("of_act_issued", { date: v.issued }))}</span></li>${v.paid ? `<li><span>${ofEsc(this.t("of_act_paid", { amount: this.c.money(v.paid) }))}</span>${this.c.chip("confirmed")}</li>` : ""}</ul>`;
    else if (this.tab === "files") body = this.empty("of_no_files", "of_back_to_list", "of:back");
    else body = `<ul class="rows"><li><span>${ofEsc(this.custName(v.customer))}</span><button class="link" data-act="of:back">${ofEsc(this.t("of_back_to_list"))}</button></li></ul>`;
    return `${head}${body}`;
  }
  private creditForm(v: Inv): string {
    const amount = Math.round(Number(this.credit.amount || "0") * 100), too = amount > this.owed(v);
    return `<div class="of-form"><h2>${ofEsc(this.t("of_credit_note"))}</h2>
      <label class="of-field" for="ofCreditAmt"><span>${ofEsc(this.t("of_credit_amount"))}</span><input id="ofCreditAmt" data-in="of:credit:amount" inputmode="decimal" autocomplete="off" value="${ofEsc(this.credit.amount)}" placeholder="${ofEsc(this.t("of_hint_price"))}"></label>
      <label class="of-field" for="ofCreditWhy"><span>${ofEsc(this.t("of_credit_reason"))}</span><input id="ofCreditWhy" data-in="of:credit:reason" autocomplete="off" value="${ofEsc(this.credit.reason)}" placeholder="${ofEsc(this.t("of_hint_reason"))}"></label>
      ${too ? `<p class="warn" role="alert">${ofEsc(this.t("of_credit_too_much"))}</p>` : ""}
      ${saveBarHtml({ label: this.t("of_issue_credit_note"), act: "of:docredit", disabled: amount <= 0 || too || !this.credit.reason.trim(), secondary: { label: this.t("of_cancel"), act: "of:creditcancel" } })}</div>`;
  }
  private invNew(): string {
    const qty = Math.round(Number(this.draft.qty || "0") * 1000), unit = Math.round(Number(this.draft.price || "0") * 100);
    const lines = qty > 0 && unit > 0 ? [{ qty, unit_minor: unit }] : [];
    const tot = lines.length ? totals(lines, this.c.taxBp() ? [{ kind: "sales", rate_bp: this.c.taxBp() }] : []) : null;
    const waits = tot ? needsApproval(OF_I, tot.total, 500000, this.c.user, []) : false;
    const field = (id: string, label: string, hint: string, value: string, mode: string): string =>
      `<label class="of-field" for="${id}"><span>${ofEsc(this.t(label))}</span><input id="${id}" data-in="of:draft:${id}" inputmode="${mode}" autocomplete="off" value="${ofEsc(value)}" placeholder="${ofEsc(this.t(hint))}"></label>`;
    return `<h1>${ofEsc(this.title("inv_new"))}</h1>${this.sample()}
      <label class="of-field" for="ofCustomer"><span>${ofEsc(this.t("of_customer"))}</span><select id="ofCustomer" data-in="of:draft:customer">${["c1", "c2", "c3"].map((c) => `<option value="${c}"${c === this.draft.customer ? " selected" : ""}>${ofEsc(this.custName(c))}</option>`).join("")}</select></label>
      ${field("ofItem", "of_item", "of_hint_item", this.draft.name, "text")}${field("ofQty", "of_quantity", "of_hint_qty", this.draft.qty, "decimal")}${field("ofPrice", "of_price", "of_hint_price", this.draft.price, "decimal")}
      ${tot ? `<table class="of-table"><tbody><tr><td>${ofEsc(this.t("of_net"))}</td><td class="of-num">${ofEsc(this.c.money(tot.net))}</td></tr><tr><td>${ofEsc(this.t("of_tax"))}</td><td class="of-num">${ofEsc(this.c.money(tot.total - tot.net))}</td></tr><tr class="of-total"><td>${ofEsc(this.t("of_total"))}</td><td class="of-num">${ofEsc(this.c.money(tot.total))}</td></tr></tbody></table>` : `<p class="note">${ofEsc(this.t("of_add_a_line"))}</p>`}
      ${waits ? `<p class="warn">${ofEsc(this.t("of_waits_for_approval"))}</p>` : ""}<p class="note">${ofEsc(this.t("of_pay_link_note"))}</p>
      ${saveBarHtml({ label: this.t(waits ? "of_send_for_approval" : "of_issue"), act: "of:issue", disabled: !tot || !this.draft.name.trim(), secondary: { label: this.t("of_cancel"), act: "of:go:inv_list" } })}`;
  }

  // ---- LynkCRM -------------------------------------------------------------------------------------------------------------
  private crmList(): string {
    const chips = ["all", "owes", "may_message"].map((id) => ({ id, label: this.t(`of_filter_${id}`), on: this.crmFilter === id }));
    const owes = (p: Person): number => this.invoices.filter((v) => this.people.indexOf(p) >= 0 && `c${this.people.indexOf(p) + 1}` === v.customer).reduce((s, v) => s + this.owed(v), 0);
    const shown = this.people.filter((p) => !(this.merged && this.merged.gone === p.id)).filter((p) => this.crmFilter === "all" || (this.crmFilter === "owes" ? owes(p) > 0 : p.consent))
      .filter((p) => !this.query || this.t(p.name).toLowerCase().includes(this.query.toLowerCase()));
    const rows = shown.map((p) => `<li><button class="link" data-act="of:person:${p.id}">${ofEsc(this.t(p.name))}</button><span>${ofEsc(p.tags.map((x) => this.t(x)).join(", "))}</span><span class="of-num">${owes(p) ? ofEsc(this.t("of_owes", { amount: this.c.money(owes(p)) })) : ""}</span></li>`).join("");
    return `<h1>${ofEsc(this.title("crm_list"))}</h1>${this.sample()}${listToolbarHtml(this.t, { query: this.query, hint: this.t("of_hint_customer"), chips, act: "of:crmfilter", inputId: "ofSearch" })}
      ${rows ? `<ul class="rows">${rows}</ul>` : this.empty("of_no_customers", "of_show_all", "of:crmfilter:all")}<p class="note">${ofEsc(this.t("of_contacts_private"))}</p>`;
  }
  private personRecord(): string {
    const p = this.people.find((x) => x.id === this.record); if (!p) return "";
    const head = recordHeaderHtml(this.c.nav, this.t, { title: this.t(p.name), current: this.tab, act: "of:tab" });
    const fields = [{ id: "email" }, { id: "phone", hidden_from: ["sales"] }, { id: "team" }];
    const shown = visibleFields(fields, this.c.role);
    let body = "";
    if (this.tab === "details") body = `<table class="of-table"><tbody>${shown.map((f) => `<tr><td>${ofEsc(this.t(`of_field_${f}`))}</td><td>${ofEsc(f === "team" ? this.t(`of_team_${p.team}`) : (f === "email" ? p.email : p.phone) ?? "—")}</td></tr>`).join("")}
      <tr><td>${ofEsc(this.t("of_messages"))}</td><td>${ofEsc(this.t(p.consent ? "of_agreed" : "of_not_agreed"))}</td></tr></tbody></table>`;
    else if (this.tab === "activity") body = `<ul class="rows"><li><span>${ofEsc(this.t("of_act_created", { date: p.created }))}</span></li></ul>`;
    else if (this.tab === "files") body = this.empty("of_no_files", "of_back_to_list", "of:back");
    else body = `<ul class="rows">${this.deals.filter((d) => d.customer === p.id).map((d) => `<li><span>${ofEsc(this.t(`of_stage_${d.stage}`))}</span><span class="of-num">${ofEsc(this.c.money(d.amount))}</span></li>`).join("") || `<li><span>${ofEsc(this.t("of_no_deals"))}</span></li>`}</ul>`;
    return `${head}${body}`;
  }
  private crmDuplicates(): string {
    const recs = this.people.filter((p) => !(this.merged && this.merged.gone === p.id)).map((p) => ({ id: p.id, email: p.email, phone: p.phone, name: this.t(p.name), created: p.created }));
    const groups = duplicates(recs);
    const rows = groups.map((g) => { const keep = merge(recs.filter((r) => g.includes(r.id))).id;
      return `<li><span>${g.map((id) => ofEsc(id)).join(" · ")}</span><span>${ofEsc(this.t("of_keeps_oldest", { id: keep }))}</span><button class="primary" data-act="of:merge:${g.join("+")}">${ofEsc(this.t("of_merge"))}</button></li>`; }).join("");
    return `<h1>${ofEsc(this.title("crm_duplicates"))}</h1>${this.sample()}${rows ? `<ul class="rows">${rows}</ul>` : `<p class="note">${ofEsc(this.t("of_no_duplicates"))}</p>`}
      ${this.merged ? `<p class="note" role="status">${ofEsc(this.t("of_merged", { id: this.merged.kept }))} <button class="link" data-act="of:unmerge">${ofEsc(this.t("of_undo"))}</button></p>` : ""}`;
  }
  private crmPipeline(): string {
    const f = forecast(OF_C, this.deals);
    const stages = (CRM as unknown as { pipelines: { stages: string[] } }).pipelines.stages;
    const cols = stages.map((st) => `<section class="of-col"><h2>${ofEsc(this.t(`of_stage_${st}`))}</h2>${this.deals.filter((d) => d.stage === st).map((d) => {
      const nexts = stages.filter((to) => to !== "lost" && stageMove(OF_C, d.stage, to));
      return `<div class="card"><span>${ofEsc(this.t(this.people.find((p) => p.id === d.customer)?.name ?? ""))}</span><strong>${ofEsc(this.c.money(d.amount))}</strong>${nexts.map((to) => `<button class="secondary" data-act="of:deal:${d.id}:${to}">${ofEsc(this.t("of_move_to", { stage: this.t(`of_stage_${to}`) }))}</button>`).join("")}</div>`; }).join("")}</section>`).join("");
    return `<h1>${ofEsc(this.title("crm_pipeline"))}</h1>${this.sample()}<p class="note">${ofEsc(this.t("of_forecast", { amount: this.c.money(f.total) }))} · ${ofEsc(this.t("of_estimate"))}</p><div class="of-board">${cols}</div>`;
  }

  // ---- LynkStat ------------------------------------------------------------------------------------------------------------
  private figures(): Record<string, number> {
    const st = statements(CHART, trialBalance(CHART, ENTRIES));
    return { sales: st.income, cost_of_sales: st.cost_of_sales, expenses: st.expenses, refunds: 0, orders: this.invoices.length, customers: this.people.length,
      invoices_paid: this.invoices.filter((v) => v.state === "paid").length, invoices_open: this.open().length };
  }
  private statOverview(): string {
    const f = this.figures(), fr = freshness(STATS, 600, 603, "live", ["till_1", "till_2", "web"], ["till_1", "web"]);
    const g = goal(f.sales!, 1000000, 6667);
    return `<h1>${ofEsc(this.title("stat_overview"))}</h1>${this.sample()}<div class="cards">${["sales", "cost_of_sales", "expenses", "invoices_open"].map((k) => `<div class="card"><span>${ofEsc(this.t(`of_fig_${k}`))}</span><strong>${ofEsc(k === "invoices_open" ? String(f[k]) : this.c.money(f[k]!))}</strong></div>`).join("")}</div>
      <p class="note">${ofEsc(this.t("of_updated_minutes", { n: fr.age_minutes }))}${fr.missing.length ? ` · ${ofEsc(this.t("of_missing_sources", { n: fr.missing.length }))}` : ""}</p>
      <h2>${ofEsc(this.t("of_goal_sales"))}</h2><div class="of-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.min(100, Math.floor((g.progress_bp ?? 0) / 100))}"><i style="inline-size:${Math.min(100, Math.floor((g.progress_bp ?? 0) / 100))}%"></i></div>
      <p class="note">${ofEsc(this.t("of_goal_progress", { n: Math.floor((g.progress_bp ?? 0) / 100) }))} · ${ofEsc(this.t(g.on_track ? "of_on_track" : "of_behind"))}</p>${this.c.ad?.() ?? ""}`;
  }
  private statMeasures(): string {
    let out = "";
    try { const v = evaluate(STATS, this.measure, this.figures()); out = v === null ? this.t("of_measure_nothing") : this.t("of_measure_value", { n: v }); }
    catch { out = this.t("of_measure_invalid"); }
    return `<h1>${ofEsc(this.title("stat_measures"))}</h1>${this.sample()}<label class="of-field" for="ofMeasure"><span>${ofEsc(this.t("of_formula"))}</span><input id="ofMeasure" data-in="of:measure" autocomplete="off" spellcheck="false" value="${ofEsc(this.measure)}" placeholder="${ofEsc(`${STATS.measures.figures[0]} - ${STATS.measures.figures[1]}`)}"></label>
      <p class="note">${ofEsc(this.t("of_formula_rule"))}</p><p role="status"><strong>${ofEsc(out)}</strong></p>
      <h2>${ofEsc(this.t("of_figures_you_can_use"))}</h2><div class="pk-chips" role="group" aria-label="${ofEsc(this.t("of_figures_you_can_use"))}">${STATS.measures.figures.map((x) => `<button class="pk-chip" data-act="of:addfig:${ofEsc(x)}">${ofEsc(this.t(`of_fig_${x}`))}</button>`).join("")}</div>`;
  }
  private statWhatIf(): string {
    const bp = (s: string): number => Math.round(Number(s || "0") * 100);
    const base = { units: 1000, price_minor: 2500, unit_cost_minor: 1400, staff_minor: 300000 };
    const r = whatIf(STATS, base, { price_bp: bp(this.whatif.price), cost_bp: bp(this.whatif.cost), staff_hours_bp: bp(this.whatif.staff) });
    const field = (k: "price" | "cost" | "staff"): string => `<label class="of-field" for="ofWi_${k}"><span>${ofEsc(this.t(`of_change_${k}`))}</span><input id="ofWi_${k}" data-in="of:whatif:${k}" inputmode="decimal" autocomplete="off" value="${ofEsc(this.whatif[k])}" placeholder="${ofEsc(this.t("of_hint_percent"))}"></label>`;
    return `<h1>${ofEsc(this.title("stat_whatif"))}</h1>${this.sample()}${field("price")}${field("cost")}${field("staff")}
      <p class="of-estimate">${ofEsc(this.t("of_estimate"))}</p><table class="of-table"><tbody><tr><td>${ofEsc(this.t("of_units"))}</td><td class="of-num">${r.units}</td></tr><tr><td>${ofEsc(this.t("of_fig_sales"))}</td><td class="of-num">${ofEsc(this.c.money(r.revenue))}</td></tr><tr class="of-total"><td>${ofEsc(this.t("of_profit"))}</td><td class="of-num">${ofEsc(this.c.money(r.profit))}</td></tr></tbody></table>
      <p class="note">${ofEsc(this.t("of_whatif_rule"))}</p>`;
  }
  private statCohorts(): string {
    const buys = [["a", "2026-06"], ["a", "2026-07"], ["b", "2026-06"], ["b", "2026-09"], ["c", "2026-07"], ["c", "2026-08"], ["d", "2026-07"], ["e", "2026-08"], ["e", "2026-09"]].map(([customer, month]) => ({ customer: customer!, month: month! }));
    const rows = cohorts(STATS, buys);
    const width = Math.max(0, ...rows.map((r) => r.back.length));
    return `<h1>${ofEsc(this.title("stat_cohorts"))}</h1>${this.sample()}<p class="note">${ofEsc(this.t("of_cohorts_rule"))}</p>
      <table class="of-table"><thead><tr><th>${ofEsc(this.t("of_first_month"))}</th><th class="of-num">${ofEsc(this.t("of_page_crm_list"))}</th>${Array.from({ length: width }, (_, i) => `<th class="of-num">${ofEsc(this.t("of_month_n", { n: i + 1 }))}</th>`).join("")}</tr></thead>
      <tbody>${rows.map((r) => `<tr><td>${ofEsc(r.month)}</td><td class="of-num">${r.size}</td>${Array.from({ length: width }, (_, i) => `<td class="of-num">${i < r.back.length ? r.back[i] : ""}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  }
  private statPublic(): string {
    const rows = publicTable(STATS, [{ group: "of_region_north", n: 42, value: 1250 }, { group: "of_region_south", n: 3, value: 90 }, { group: "of_region_east", n: 17, value: 610 }]);
    return `<h1>${ofEsc(this.title("stat_public"))}</h1>${this.sample()}<p class="note">${ofEsc(this.t("of_public_rule", { n: STATS.public.min_group }))}</p>
      <table class="of-table"><thead><tr><th>${ofEsc(this.t("of_group"))}</th><th class="of-num">${ofEsc(this.t("of_people"))}</th><th class="of-num">${ofEsc(this.t("of_total"))}</th></tr></thead><tbody>${rows.map((r) => `<tr><td>${ofEsc(this.t(r.group))}</td><td class="of-num">${r.n === null ? ofEsc(this.t("of_hidden")) : r.n}</td><td class="of-num">${r.value === null ? ofEsc(this.t("of_hidden")) : r.value}</td></tr>`).join("")}</tbody></table>`;
  }

  // ---- acting ----------------------------------------------------------------------------------------------------------------
  /** Handles "of:..." acts; returns false for anything else so the host can act on it. */
  act(a: string): boolean {
    if (!a.startsWith("of:")) return false;
    const [, k = "", v = "", w = ""] = a.split(":");
    if (k === "claim") { const c = this.claims.find((x) => x.id === v); if (c && c.state === "submitted" && mayApprove(c.by, this.c.user)) c.state = "approved"; }
    else if (k === "billfilter") this.billFilter = v;
    else if (k === "invfilter") this.invFilter = v;
    else if (k === "crmfilter") this.crmFilter = v;
    else if (k === "bill") { const b = this.bills.find((x) => x.id === v); if (b) { if (w === "approve" && !mayApprove(b.preparer, this.c.user)) return true; const to = billMove(OF_B, b.state, w); if (to) b.state = to === "paid" ? "approved" : to; if (to === "paid") this.issuedNote = this.t("of_paid_when_confirmed"); } }
    else if (k === "match") { if (!this.matched.includes(v)) this.matched.push(v); }
    else if (k === "close") this.closed = this.closed.includes(v) ? this.closed.filter((x) => x !== v) : [...this.closed, v];
    else if (k === "lock") this.lockAsked = true;
    else if (k === "inv") { this.record = v; this.tab = "details"; this.crediting = false; this.creditNote = ""; }
    else if (k === "person") { this.record = v; this.tab = "details"; }
    else if (k === "tab") this.tab = v === "more" ? "details" : v;
    else if (k === "back") this.record = "";
    else if (k === "creditnote") { this.tab = "details"; this.crediting = true; this.creditNote = ""; }
    else if (k === "creditcancel") { this.crediting = false; this.credit = { amount: "", reason: "" }; }
    else if (k === "docredit") {
      const v = this.invoices.find((x) => x.id === this.record), amount = Math.round(Number(this.credit.amount || "0") * 100);
      if (v && amount > 0 && amount <= this.owed(v) && this.credit.reason.trim()) {        // never more than is still owed, always with a reason
        v.credited = (v.credited ?? 0) + amount; if (this.owed(v) === 0) v.state = v.paid ? "paid" : "credited";
        this.creditNote = this.t("of_credited_note", { amount: this.c.money(amount) }); this.crediting = false; this.credit = { amount: "", reason: "" };
      }
    }
    else if (k === "issue") { this.issuedNote = this.t("of_issued_note"); this.draft = { customer: "c1", name: "", qty: "", price: "" }; this.record = ""; }
    else if (k === "merge") { const ids = v.split("+"), recs = this.people.filter((p) => ids.includes(p.id)).map((p) => ({ id: p.id, created: p.created })); const keep = merge(recs).id; this.merged = { kept: keep, gone: ids.find((x) => x !== keep)! }; }
    else if (k === "unmerge") this.merged = null;
    else if (k === "addfig" && (STATS.measures.figures as readonly string[]).includes(v)) this.measure = `${this.measure.trimEnd()} ${v}`.trim();   // a figure's code goes into the formula
    else if (k === "deal") { const d = this.deals.find((x) => x.id === v); if (d && stageMove(OF_C, d.stage, w)) d.stage = w; }
    return true;
  }
  /** Typing in an office field; returns true when it was one. */
  input(key: string, value: string): boolean {
    if (!key.startsWith("of:")) return false;
    const [, k = "", f = ""] = key.split(":");
    if (k === "entity") { this.entityKind = value; return true; }
    if (k === "lock") this.lockDate = value;
    else if (k === "measure") this.measure = value;
    else if (k === "whatif") (this.whatif as Record<string, string>)[f] = value;
    else if (k === "credit") (this.credit as Record<string, string>)[f] = value;
    else if (k === "draft") { const map: Record<string, keyof OfficeView["draft"]> = { ofItem: "name", ofQty: "qty", ofPrice: "price", customer: "customer" }; const m = map[f]; if (m) this.draft[m] = value; }
    return true;
  }
  search(q: string): void { this.query = q; }
  reset(): void { this.record = ""; this.tab = "details"; this.query = ""; }
}
