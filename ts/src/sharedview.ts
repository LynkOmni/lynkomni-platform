/** The pages of the parts every service shares (CONNECT UPDATE 71.3; section 4 row 71.9 step 2b): calendar, contacts, recycle bin,
 *  audit viewer, consents, test copy and plans and limits. One shared part draws them on every screen that shows them (the Business
 *  app on a phone and the owner's computer view), on the rules of ts/src/shared.ts; words in web/shared (prefix sv_).
 *  The data on these pages is sample data, labelled Sample; the cloud side is services/shared.py. */
import { SHARED } from "./shared.generated.js";
import { binnable, calendarSources, mayAudit, purgeDue, sharedMay } from "./shared.js";

export const SHARED_PAGES = ["calendar", "contacts", "recycle_bin", "audit", "consents", "test_copy"] as const;
export type SharedPage = (typeof SHARED_PAGES)[number];

export interface SharedLook {
  t: (key: string, vars?: Record<string, string | number>) => string;
  esc: (s: string) => string;
  icon: (id: string) => string;
  /** a date in the viewer's own calendar and digits, from seconds since 1970 */
  date: (secs: number) => string;
  /** a product's name with its plain word (namePair main) */
  name: (family: string) => string;
  /** the screen's own button classes and switch, so the part looks native on each device */
  btn: { primary: string; secondary: string };
  toggle: (on: boolean, act: string, label: string, why: string | null) => string;
}

interface Contact { id: string; kind: string; name: string; usedBy: string[]; binned: number | null }
interface Event { at: number; word: string }
export interface SharedState {
  now: number;
  role: string;
  contacts: Contact[];
  files: { id: string; binned: number }[];
  links: Record<string, boolean>;
  shared: { id: string; word: string; until: number; withdrawn: boolean }[];
  channels: Record<string, number>;
  testCopy: boolean;
  events: Event[];
  looks: number;
}

const SV_DAY = 86400;
const SRC_WORD: Record<string, string> = { invoice_due: "sv_src_invoice_due", promise_to_pay: "sv_src_promise_to_pay", bill_due: "sv_src_bill_due", lock_date: "sv_src_lock_date" };
const KIND_WORD: Record<string, string> = { customer: "sv_kind_customer", supplier: "sv_kind_supplier", organisation: "sv_kind_organisation", contact: "sv_kind_contact", file: "sv_kind_file" };
const CH_WORD: Record<string, string> = { email: "sv_ch_email", sms: "sv_ch_sms", chat: "sv_ch_chat", push: "sv_ch_push", calls: "sv_ch_calls", post: "sv_ch_post" };
const LIM_WORD: Record<string, string> = { invoices_per_month: "sv_lim_invoices_per_month", customers: "sv_lim_customers" };
const TITLE_WORD: Record<SharedPage, string> = { calendar: "sv_calendar", contacts: "sv_contacts", recycle_bin: "sv_recycle_bin", audit: "sv_audit", consents: "sv_consents", test_copy: "sv_test_copy" };
const word = (map: Record<string, string>, k: string): string => map[k] ?? "sv_sample";
/** The links between services that need the business's consent (catalog/connections.v1.json), given by the build. */
export interface ConsentLink { id: string; from: string; to: string }

/** Sample data for the pages, relative to now; every page labels it Sample. */
export function sampleShared(now: number, role = "owner"): SharedState {
  return {
    now, role,
    contacts: [
      { id: "LOCST-1001", kind: "customer", name: "Amina Uwase", usedBy: ["lynkcrm", "lynkinv"], binned: null },
      { id: "LOCST-1002", kind: "supplier", name: "Green Farm", usedBy: ["lynkcrm", "lynkacc"], binned: null },
      { id: "LOCST-1003", kind: "organisation", name: "City Traders", usedBy: ["lynkcrm"], binned: null },
      { id: "LOCST-1004", kind: "customer", name: "Jean Mugabo", usedBy: ["lynkcrm"], binned: now - 26 * SV_DAY },
    ],
    files: [{ id: "LODOC-2001", binned: now - 3 * SV_DAY }],
    links: {},
    shared: [{ id: "LOCNS-3001", word: "sv_cs_accountant", until: now + 60 * SV_DAY, withdrawn: false }],
    channels: { email: 42, sms: 17, push: 9 },
    testCopy: false,
    events: [
      { at: now - 600, word: "sv_ev_invoice" }, { at: now - 3600, word: "sv_ev_payment" },
      { at: now - 7200, word: "sv_ev_bill" }, { at: now - 86400, word: "sv_ev_role" }, { at: now - 2 * SV_DAY, word: "sv_ev_bin" },
    ],
    looks: 0,
  };
}

const sample = (o: SharedLook): string => `<span class="sv-sample">${o.esc(o.t("sv_sample"))}</span>`;
const intro = (o: SharedLook, key: string, vars?: Record<string, string | number>): string => `<p class="sv-note">${o.esc(o.t(key, vars))} · ${sample(o)}</p>`;

/** Calendar: dates from each service's own records, only from the sources built so far (ts/src/shared.ts calendarSources). */
export function calendarHtml(st: SharedState, o: SharedLook, built: (section: string) => boolean): string {
  const on = calendarSources(built);
  const rows = [
    { src: "invoice_due", at: st.now + 3 * SV_DAY, ref: "LOINV-1002" }, { src: "promise_to_pay", at: st.now + 5 * SV_DAY, ref: "LOINV-1001" },
    { src: "bill_due", at: st.now + 9 * SV_DAY, ref: "Green Farm" }, { src: "lock_date", at: st.now - 20 * SV_DAY, ref: "" },
  ].filter((r) => on.includes(r.src)).sort((a, b) => a.at - b.at);
  const items = ["invoice_due", "promise_to_pay", "bill_due", "lock_date"];
  return `<section class="sv" data-item="calendar_list">${intro(o, "sv_cal_intro")}<ul class="rows sv-rows">${rows.map((r) => `<li data-item="${o.esc(r.src)}"><span class="sv-main"><span class="sv-nm">${o.esc(o.date(r.at))}</span><span class="sv-sub">${o.esc(o.t(word(SRC_WORD, r.src)))}${r.ref ? ` · ${o.esc(r.ref)}` : ""}</span></span></li>`).join("")}</ul>
    ${items.filter((i) => !rows.some((r) => r.src === i)).map((i) => `<span hidden data-item="${i}"></span>`).join("")}</section>`;
}

/** Contacts: the one address book; names come from the vault (sample names here), never typed twice. */
export function contactsHtml(st: SharedState, o: SharedLook): string {
  const live = st.contacts.filter((c) => c.binned === null);
  const kinds = SHARED.address_kinds as readonly string[];
  return `<section class="sv">${intro(o, "sv_ct_intro")}<ul class="rows sv-rows">${live.map((c) => `<li data-item="${o.esc(c.kind)}"><span class="sv-main"><span class="sv-nm">${o.esc(c.name)}</span><span class="sv-sub">${o.esc(o.t(word(KIND_WORD, c.kind)))} · ${o.esc(o.t("sv_used_by", { services: c.usedBy.map((f) => o.name(f)).join(", ") }))}</span></span><button class="${o.btn.secondary}" data-act="shv:delete:${o.esc(c.id)}">${o.esc(o.t("sv_delete"))}</button></li>`).join("")}</ul>
    ${kinds.filter((k) => !live.some((c) => c.kind === k)).map((k) => `<span hidden data-item="${k}"></span>`).join("")}</section>`;
}

/** Recycle bin: what the rules allow to be undone, kept for the bin's days, then removed for good. */
export function binHtml(st: SharedState, o: SharedLook): string {
  const days = SHARED.bin.keep_days;
  const left = (at: number): number => Math.max(0, days - Math.floor((st.now - at) / SV_DAY));
  const rows = [
    ...st.contacts.filter((c) => c.binned !== null && binnable("crm_record") && !purgeDue(c.binned, st.now)).map((c) => ({ id: c.id, label: c.name, kind: word(KIND_WORD, c.kind), at: c.binned as number })),
    ...st.files.filter((f) => binnable("file") && !purgeDue(f.binned, st.now)).map((f) => ({ id: f.id, label: f.id, kind: KIND_WORD["file"] ?? "sv_kind_file", at: f.binned })),
  ];
  const list = rows.length ? `<ul class="rows sv-rows">${rows.map((r) => `<li><span class="sv-main"><span class="sv-nm">${o.esc(r.label)}</span><span class="sv-sub">${o.esc(o.t(r.kind))} · ${o.esc(o.t("sv_bin_left", { days: left(r.at) }))}</span></span><button class="${o.btn.secondary}" data-act="shv:restore:${o.esc(r.id)}">${o.esc(o.t("sv_restore"))}</button></li>`).join("")}</ul>`
    : `<p class="sv-note">${o.icon("ui-info")}<span>${o.esc(o.t("sv_bin_empty"))}</span></p>`;
  return `<section class="sv">${intro(o, "sv_bin_intro", { days })}<p class="sv-note" data-item="keep_days">${o.esc(o.t("sv_bin_never"))}</p><div data-item="restore">${list}</div></section>`;
}

/** Audit viewer: the owner, an auditor or the accountant only; every look is recorded. */
export function auditHtml(st: SharedState, o: SharedLook): string {
  if (!mayAudit(st.role)) return `<section class="sv"><p class="sv-warn" role="status" data-item="events">${o.icon("ui-lock")}<span>${o.esc(o.t("sv_au_denied"))}</span></p><span hidden data-item="looks_recorded"></span></section>`;
  const rows = [{ at: st.now, word: "sv_ev_viewed" }, ...st.events];
  return `<section class="sv">${intro(o, "sv_au_intro")}<ul class="rows sv-rows" data-item="events">${rows.map((e) => `<li><span class="sv-main"><span class="sv-nm">${o.esc(o.t(e.word))}</span><span class="sv-sub">${o.esc(o.date(e.at))}</span></span></li>`).join("")}</ul>
    <p class="sv-note" data-item="looks_recorded">${o.icon("ui-info")}<span>${o.esc(o.t("sv_au_looks", { n: st.looks }))}</span></p></section>`;
}

/** Consents: what is shared with others, the links that need the business's consent and how many contacts agreed per channel. */
export function consentsHtml(st: SharedState, o: SharedLook, links: readonly ConsentLink[]): string {
  const canSwitch = sharedMay("base", st.role, "crm", "admin");
  const shared = st.shared.filter((x) => !x.withdrawn);
  return `<section class="sv" data-item="shared_with_others"><h2>${o.esc(o.t("sv_cs_shared"))}</h2>${intro(o, "sv_cs_shared_help")}
    ${shared.length ? `<ul class="rows sv-rows">${shared.map((x) => `<li><span class="sv-main"><span class="sv-nm">${o.esc(o.t(x.word))}</span><span class="sv-sub">${o.esc(o.t("sv_until", { date: o.date(x.until) }))}</span></span><button class="${o.btn.secondary}" data-act="shv:withdraw:${o.esc(x.id)}">${o.esc(o.t("sv_withdraw"))}</button></li>`).join("")}</ul>` : `<p class="sv-note">${o.esc(o.t("sv_cs_none"))}</p>`}</section>
    <section class="sv" data-item="links"><h2>${o.esc(o.t("sv_cs_links"))}</h2><p class="sv-note">${o.esc(o.t("sv_cs_links_help"))}</p><ul class="rows sv-rows">${links.map((l) => { const on = !!st.links[l.id];
      return `<li><span class="sv-main"><span class="sv-nm">${o.esc(o.t("sv_link_pair", { from: o.name(l.from), to: o.name(l.to) }))}</span></span>${o.toggle(on, `shv:link:${l.id}`, o.t("sv_link_pair", { from: o.name(l.from), to: o.name(l.to) }), canSwitch ? null : o.t("sv_owner_only"))}</li>`; }).join("")}</ul></section>
    <section class="sv" data-item="contact_channels"><h2>${o.esc(o.t("sv_cs_channels"))}</h2><ul class="rows sv-rows">${Object.entries(st.channels).map(([ch, n]) => `<li><span class="sv-main"><span class="sv-nm">${o.esc(o.t(word(CH_WORD, ch)))}</span><span class="sv-sub">${o.esc(o.t("sv_cs_count", { n }))}</span></span></li>`).join("")}</ul></section>`;
}

/** Test copy: try connections and automations with sample data; no message is sent and no money moves. */
export function testCopyHtml(st: SharedState, o: SharedLook): string {
  return `<section class="sv">${intro(o, "sv_tc_intro")}${st.testCopy ? `<p class="sv-notice" role="status">${o.icon("ui-info")}<span>${o.esc(o.t("sv_tc_on"))}</span></p>` : ""}
    <p>${st.testCopy ? `<button class="${o.btn.secondary}" data-item="close" data-act="shv:copy:close">${o.esc(o.t("sv_tc_close"))}</button><span hidden data-item="open"></span>` : `<button class="${o.btn.primary}" data-item="open" data-act="shv:copy:open">${o.esc(o.t("sv_tc_open"))}</button><span hidden data-item="close"></span>`}</p></section>`;
}

/** Plans and limits: each plan from billing, with the numbered limits a service counts. */
export function plansLimitsHtml(rows: readonly { family: string; tier: string; limits: readonly { key: string; limit: number | null; used: number | null }[] }[], o: SharedLook): string {
  return `<section class="sv" data-item="plans_limits"><h2>${o.esc(o.t("sv_plans_limits"))}</h2>${intro(o, "sv_pl_intro")}<ul class="rows sv-rows">${rows.map((r) => `<li><span class="sv-main"><span class="sv-nm">${o.esc(o.name(r.family))} · ${o.esc(o.t(`card_${r.tier}`))}</span>${r.limits.map((l) => `<span class="sv-sub">${o.esc(o.t(word(LIM_WORD, l.key)))}: ${o.esc(l.limit === null ? o.t("sv_no_limit") : l.used === null ? String(l.limit) : o.t("sv_used", { used: l.used, limit: l.limit }))}</span>`).join("")}</span></li>`).join("")}</ul></section>`;
}

/** The page for an id, with its title word. */
export function sharedPage(id: SharedPage, st: SharedState, o: SharedLook, ctx: { links: readonly ConsentLink[]; built: (section: string) => boolean }): string {
  switch (id) {
    case "calendar": return calendarHtml(st, o, ctx.built);
    case "contacts": return contactsHtml(st, o);
    case "recycle_bin": return binHtml(st, o);
    case "audit": st.looks += 1; return auditHtml(st, o);
    case "consents": return consentsHtml(st, o, ctx.links);
    case "test_copy": return testCopyHtml(st, o);
  }
}
export const sharedTitle = (id: SharedPage): string => TITLE_WORD[id];

/** The page's actions (prefix shv:): delete to the bin, restore, switch a link, withdraw, open or close the test copy. */
export function sharedAct(st: SharedState, a: string): boolean {
  if (!a.startsWith("shv:")) return false;
  const [, k = "", v = ""] = a.split(":");
  const c = st.contacts.find((x) => x.id === v);
  if (k === "delete" && c && binnable("crm_record")) c.binned = st.now;
  if (k === "restore") { if (c) c.binned = null; st.files = st.files.filter((f) => f.id !== v); }
  if (k === "link") st.links[v] = !st.links[v];
  if (k === "withdraw") st.shared.forEach((x) => { if (x.id === v) x.withdrawn = true; });
  if (k === "copy") st.testCopy = v === "open";
  return true;
}
