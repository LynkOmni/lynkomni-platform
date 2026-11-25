/** The pages of the parts every service shares (CONNECT UPDATE 71.3; section 4 row 71.9 step 2b): calendar, contacts, recycle bin,
 *  audit viewer, consents, test copy and plans and limits. One shared part draws them on every screen that shows them (the Business
 *  app on a phone and the owner's computer view), on the rules of ts/src/shared.ts; words in web/shared (prefix sv_).
 *  The data on these pages is sample data, labelled Sample; the cloud side is services/shared.py. */
import { SHARED } from "./shared.generated.js";
import { binnable, calendarSources, mayAudit, purgeDue, sharedMay } from "./shared.js";
import { MESSAGE_SYSTEM } from "./parts.generated.js";
import { checkWording } from "./notify.js";

/** The shared pages, and the message system's pages (CONNECT UPDATE 71.7; section 4 row 71.9 step 4b): the role inbox, urgent
 *  broadcast, forward by email, message wording with test mode and message results. Their rules are services/messages.py and
 *  services/message_desk.py in the cloud and MESSAGE_SYSTEM and checkWording here. */
export const SHARED_PAGES = ["calendar", "contacts", "recycle_bin", "audit", "consents", "test_copy", "role_inbox", "broadcast", "email_in", "message_wording", "message_results"] as const;
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
  msg: MsgState;
}
interface InboxItem { id: string; word: string; at: number; takenBy: string | null; doneBy: string | null }
interface Broadcast { id: string; aud: string; at: number; seen: string[]; notSeen: string[] }
export interface MsgState {
  role: string;
  inbox: Record<string, InboxItem[]>;
  bc: { aud: string; text: string; confirm: number | null; why: string | null; sent: Broadcast[] };
  mw: { kind: string; text: string; state: "standard" | "testing" | "live"; why: string | null };
  held: { id: string; box: string }[];
  allowed: number;
  username: string;
  copied: string | null;
}

const SV_DAY = 86400;
const SRC_WORD: Record<string, string> = { invoice_due: "sv_src_invoice_due", promise_to_pay: "sv_src_promise_to_pay", bill_due: "sv_src_bill_due", lock_date: "sv_src_lock_date" };
const KIND_WORD: Record<string, string> = { customer: "sv_kind_customer", supplier: "sv_kind_supplier", organisation: "sv_kind_organisation", contact: "sv_kind_contact", file: "sv_kind_file" };
const CH_WORD: Record<string, string> = { email: "sv_ch_email", sms: "sv_ch_sms", chat: "sv_ch_chat", push: "sv_ch_push", calls: "sv_ch_calls", post: "sv_ch_post" };
const LIM_WORD: Record<string, string> = { invoices_per_month: "sv_lim_invoices_per_month", customers: "sv_lim_customers" };
const TITLE_WORD: Record<SharedPage, string> = { calendar: "sv_calendar", contacts: "sv_contacts", recycle_bin: "sv_recycle_bin", audit: "sv_audit", consents: "sv_consents", test_copy: "sv_test_copy",
  role_inbox: "sv_role_inbox", broadcast: "sv_broadcast", email_in: "sv_email_in", message_wording: "sv_message_wording", message_results: "sv_message_results" };
const ROLE_WORD: Record<string, string> = { owner: "sv_role_owner", manager: "sv_role_manager", front_desk: "sv_role_front_desk", cashier: "sv_role_cashier", stock_staff: "sv_role_stock_staff", kitchen_staff: "sv_role_kitchen_staff", rider: "sv_role_rider" };
const AUD_WORD: Record<string, string> = { staff: "sv_aud_staff", guardians: "sv_aud_guardians", tenants: "sv_aud_tenants", members: "sv_aud_members" };
const BOX_WORD: Record<string, string> = { bills: "sv_box_bills", files: "sv_box_files", cvs: "sv_box_cvs" };
const BOX_HELP: Record<string, string> = { bills: "sv_box_bills_help", files: "sv_box_files_help", cvs: "sv_box_cvs_help" };
/** Customer messages of the sections built so far; each later section adds its kinds' words when it is built. */
const MK_WORD: Record<string, string> = { receipt: "sv_mk_receipt", document: "sv_mk_document", queue_your_turn: "sv_mk_queue_your_turn", queue_next_section: "sv_mk_queue_next_section", queue_missed: "sv_mk_queue_missed", survey_invite: "sv_mk_survey_invite", survey_you_said: "sv_mk_survey_you_said" };
const MG_WHY_WORD: Record<string, string> = { empty: "sv_mw_why_empty", too_long: "sv_mw_why_too_long", unknown_placeholder: "sv_mw_why_unknown", missing_placeholder: "sv_mw_why_missing", not_allowed: "sv_mw_why_not_allowed", per_day: "sv_bc_why_per_day" };
const SAMPLE_PEOPLE = ["Ama", "Ben", "Chantal", "Didier", "Esther"];
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
    msg: {
      role: "front_desk",
      inbox: {
        front_desk: [{ id: "MI-1", word: "sv_mi_ev_booking", at: now - 300, takenBy: null, doneBy: null }, { id: "MI-2", word: "sv_mi_ev_queue", at: now - 1500, takenBy: "Ama", doneBy: null }, { id: "MI-3", word: "sv_mi_ev_visitor", at: now - 7200, takenBy: "Ben", doneBy: "Ben" }],
        manager: [{ id: "MI-4", word: "sv_mi_ev_cash", at: now - 900, takenBy: null, doneBy: null }],
        stock_staff: [{ id: "MI-5", word: "sv_mi_ev_stock", at: now - 2400, takenBy: null, doneBy: null }],
      },
      bc: { aud: "staff", text: "", confirm: null, why: null, sent: [{ id: "BC-1", aud: "staff", at: now - 5400, seen: ["Ama", "Ben", "Chantal"], notSeen: ["Didier", "Esther"] }] },
      mw: { kind: "receipt", text: "", state: "standard", why: null },
      held: [{ id: "HE-1", box: "bills" }],
      allowed: 2,
      username: "sample.shop",
      copied: null,
    },
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

// ---- the message system's pages (CONNECT UPDATE 71.7) ------------------------------------------------------------------------
const mayLead = (role: string): boolean => (MESSAGE_SYSTEM.broadcast.senders as readonly string[]).includes(role);
const mgAgo = (o: SharedLook, now: number, at: number): string => o.t("sv_mins_ago", { n: Math.max(1, Math.round((now - at) / 60)) });

/** Role inbox: a shared list for a role, so an alert is handled once; Take it shows the others who has it; Done clears it for all. */
export function roleInboxHtml(st: SharedState, o: SharedLook): string {
  const m = st.msg, items = (m.inbox[m.role] ?? []).filter((x) => !x.doneBy), done = (m.inbox[m.role] ?? []).filter((x) => x.doneBy);
  const roles = MESSAGE_SYSTEM.roles.map((r) => `<button class="${r === m.role ? o.btn.primary : o.btn.secondary}" data-act="shv:inbox:${o.esc(r)}" aria-pressed="${r === m.role}">${o.esc(o.t(word(ROLE_WORD, r)))}</button>`).join("");
  const row = (x: InboxItem): string => `<li><span class="sv-main"><span class="sv-nm">${o.esc(o.t(x.word))}</span><span class="sv-sub">${o.esc(mgAgo(o, st.now, x.at))}${x.takenBy ? ` · ${o.esc(o.t("sv_mi_taken_by", { name: x.takenBy === "you" ? o.t("sv_mi_you") : x.takenBy }))}` : ""}</span></span>${
    x.takenBy && x.takenBy !== "you" ? "" : x.takenBy === "you" ? `<button class="${o.btn.primary}" data-act="shv:done:${o.esc(x.id)}">${o.esc(o.t("sv_mi_done"))}</button>` : `<button class="${o.btn.secondary}" data-act="shv:take:${o.esc(x.id)}">${o.esc(o.t("sv_mi_take"))}</button>`}</li>`;
  return `<section class="sv">${intro(o, "sv_mi_intro")}<div class="sv-chips" role="group" aria-label="${o.esc(o.t("sv_mi_roles"))}" data-item="roles">${roles}</div>
    ${items.length ? `<ul class="rows sv-rows" data-item="take">${items.map(row).join("")}</ul>` : `<p class="sv-note" data-item="take">${o.icon("ui-info")}<span>${o.esc(o.t("sv_mi_empty"))}</span></p>`}
    ${done.length ? `<h2>${o.esc(o.t("sv_mi_done_list"))}</h2><ul class="rows sv-rows" data-item="done">${done.map((x) => `<li><span class="sv-main"><span class="sv-nm">${o.esc(o.t(x.word))}</span><span class="sv-sub">${o.esc(o.t("sv_mi_done_by", { name: x.doneBy === "you" ? o.t("sv_mi_you") : x.doneBy ?? "" }))}</span></span></li>`).join("")}</ul>` : `<span hidden data-item="done"></span>`}</section>`;
}

/** Urgent broadcast: the owner or a manager writes once to a group; texts are shown before they are spent; who has seen it comes
 *  only from the app's read state. */
export function broadcastHtml(st: SharedState, o: SharedLook): string {
  const b = st.msg.bc, lead = mayLead(st.role), left = MESSAGE_SYSTEM.broadcast.per_day - b.sent.filter((x) => st.now - x.at < 86400).length;
  const why = lead ? (left <= 0 ? o.t("sv_bc_why_per_day") : null) : o.t("sv_bc_owner_or_manager");
  const auds = MESSAGE_SYSTEM.broadcast.audiences.map((a) => `<label class="sv-pick"><input type="radio" name="bcAud" data-act="shv:aud:${o.esc(a)}" value="${o.esc(a)}"${a === b.aud ? " checked" : ""}${why ? ` disabled data-why="${o.esc(why)}"` : ""}><span>${o.esc(o.t(word(AUD_WORD, a)))}</span></label>`).join("");
  const form = `<fieldset class="sv-set" data-item="compose"><legend>${o.esc(o.t("sv_bc_to"))}</legend><div class="sv-picks">${auds}</div></fieldset>
    <label class="sv-field" for="svBcText"><span>${o.esc(o.t("sv_bc_text"))}</span><textarea id="svBcText" data-in="shv:bc_text" data-draft="shv:broadcast" rows="3" maxlength="${MESSAGE_SYSTEM.broadcast.max_chars}" placeholder="${o.esc(o.t("sv_hint_bc_text"))}"${why ? ` disabled data-why="${o.esc(why)}"` : ""}>${o.esc(b.text)}</textarea></label>
    <p class="sv-note">${o.esc(o.t("sv_bc_limits", { chars: MESSAGE_SYSTEM.broadcast.max_chars, left: Math.max(0, left), per_day: MESSAGE_SYSTEM.broadcast.per_day }))}</p>
    ${b.why ? `<p class="sv-warn" role="alert">${o.icon("ui-info")}<span>${o.esc(o.t(word(MG_WHY_WORD, b.why)))}</span></p>` : ""}
    ${b.confirm !== null ? `<div class="sv-notice" role="status" data-item="cost">${o.icon("ui-info")}<span>${o.esc(o.t("sv_bc_cost", { n: b.confirm }))} · ${sample(o)}</span></div><p class="sv-btns"><button class="${o.btn.primary}" data-wait data-act="shv:bc:confirm">${o.esc(o.t("sv_bc_send_anyway"))}</button><button class="${o.btn.secondary}" data-act="shv:bc:cancel">${o.esc(o.t("sv_cancel"))}</button></p>`
      : `<p class="sv-btns"><button class="${o.btn.primary}" data-wait data-act="shv:bc:send"${why ? ` disabled data-why="${o.esc(why)}"` : ""}>${o.esc(o.t("sv_bc_send"))}</button></p><span hidden data-item="cost"></span>`}`;
  const sent = b.sent.length ? `<h2>${o.esc(o.t("sv_bc_sent"))}</h2><ul class="rows sv-rows" data-item="seen">${b.sent.map((x) => { const n = x.seen.length + x.notSeen.length;
    return `<li><span class="sv-main"><span class="sv-nm">${o.esc(o.t(word(AUD_WORD, x.aud)))} · ${o.esc(mgAgo(o, st.now, x.at))}</span><span class="sv-sub">${o.esc(o.t("sv_bc_seen", { seen: x.seen.length, n }))}</span>${x.notSeen.length ? `<span class="sv-sub">${o.esc(o.t("sv_bc_not_seen", { names: x.notSeen.join(", ") }))}</span>` : ""}</span></li>`; }).join("")}</ul>
    <p class="sv-note">${o.esc(o.t("sv_bc_seen_how"))}</p>` : `<span hidden data-item="seen"></span>`;
  return `<section class="sv">${intro(o, "sv_bc_intro")}${form}${sent}</section>`;
}

/** Forward by email: each box's address; only allowed senders get through, the rest wait for the owner. */
export function emailInHtml(st: SharedState, o: SharedLook, built: (section: string) => boolean): string {
  const m = st.msg;
  const boxes = Object.entries(MESSAGE_SYSTEM.email_in).map(([box, v]) => { const on = built(v.section);
    return `<li data-item="${o.esc(box)}"><span class="sv-main"><span class="sv-nm">${o.esc(o.t(word(BOX_WORD, box)))}</span><span class="sv-sub">${o.esc(o.t(word(BOX_HELP, box)))}</span>${on ? `<span class="sv-sub sv-addr" data-names="off" translate="no">${o.esc(v.address.replace("{username}", m.username))}</span>` : `<span class="sv-sub">${o.esc(o.t("sv_box_later"))}</span>`}</span>${on ? `<button class="${o.btn.secondary}" data-act="shv:copy_addr:${o.esc(box)}">${o.esc(o.t(m.copied === box ? "sv_copied" : "sv_copy"))}</button>` : ""}</li>`; }).join("");
  const held = m.held.length ? `<h2>${o.esc(o.t("sv_ei_held"))}</h2><ul class="rows sv-rows" data-item="held">${m.held.map((h) => `<li><span class="sv-main"><span class="sv-nm">${o.esc(o.t(word(BOX_WORD, h.box)))}</span><span class="sv-sub">${o.esc(o.t("sv_ei_held_help"))}</span></span><button class="${o.btn.primary}" data-act="shv:release:${o.esc(h.id)}">${o.esc(o.t("sv_ei_let_in"))}</button><button class="${o.btn.secondary}" data-act="shv:drop:${o.esc(h.id)}">${o.esc(o.t("sv_delete"))}</button></li>`).join("")}</ul>` : `<span hidden data-item="held"></span>`;
  return `<section class="sv">${intro(o, "sv_ei_intro")}<ul class="rows sv-rows">${boxes}</ul><p class="sv-note" data-item="allowed">${o.icon("ui-lock")}<span>${o.esc(o.t("sv_ei_allowed", { n: m.allowed }))}</span></p>${held}</section>`;
}

/** Message wording: change a customer message's words within safe limits; a new wording goes only to the owner until approved. */
export function wordingHtml(st: SharedState, o: SharedLook, built: (section: string) => boolean, kindBuilt: (kind: string) => boolean): string {
  const w = st.msg.mw, lead = mayLead(st.role), isOwner = st.role === "owner";
  const kinds = MESSAGE_SYSTEM.wording_kinds.filter((k) => MK_WORD[k] && kindBuilt(k));
  void built;
  const opts = kinds.map((k) => `<option value="${o.esc(k)}"${k === w.kind ? " selected" : ""}>${o.esc(o.t(word(MK_WORD, k)))}</option>`).join("");
  const why = lead ? null : o.t("sv_mw_owner_or_manager");
  const state = w.state === "testing" ? `<div class="sv-notice" role="status" data-item="test_mode">${o.icon("ui-info")}<span>${o.esc(o.t("sv_mw_testing"))}</span></div>
      <p class="sv-btns"><button class="${o.btn.primary}" data-act="shv:mw:approve"${isOwner ? "" : ` disabled data-why="${o.esc(o.t("sv_mw_owner_approves"))}"`}>${o.esc(o.t("sv_mw_approve"))}</button><button class="${o.btn.secondary}" data-act="shv:mw:reset"${why ? ` disabled data-why="${o.esc(why)}"` : ""}>${o.esc(o.t("sv_mw_reset"))}</button></p>`
    : w.state === "live" ? `<p class="sv-note" role="status" data-item="test_mode">${o.icon("ui-info")}<span>${o.esc(o.t("sv_mw_live"))}</span></p><p class="sv-btns"><button class="${o.btn.secondary}" data-act="shv:mw:reset"${why ? ` disabled data-why="${o.esc(why)}"` : ""}>${o.esc(o.t("sv_mw_reset"))}</button></p>`
    : `<span hidden data-item="test_mode"></span>`;
  return `<section class="sv">${intro(o, "sv_mw_intro")}
    <label class="sv-field" for="svMwKind"><span>${o.esc(o.t("sv_mw_which"))}</span><select id="svMwKind" data-in="shv:mw_kind"${why ? ` disabled data-why="${o.esc(why)}"` : ""}>${opts}</select></label>
    <label class="sv-field" for="svMwText"><span>${o.esc(o.t("sv_mw_words"))}</span><textarea id="svMwText" data-in="shv:mw_text" data-draft="shv:wording" rows="3" maxlength="${MESSAGE_SYSTEM.wording.max_chars}" placeholder="${o.esc(o.t("sv_hint_mw_text"))}"${why ? ` disabled data-why="${o.esc(why)}"` : ""}>${o.esc(w.text)}</textarea></label>
    <p class="sv-note" data-item="limits">${o.esc(o.t("sv_mw_limits", { chars: MESSAGE_SYSTEM.wording.max_chars, fills: MESSAGE_SYSTEM.wording.placeholders.join(" "), must: MESSAGE_SYSTEM.wording.required.join(" ") }))}</p>
    ${w.why ? `<p class="sv-warn" role="alert">${o.icon("ui-info")}<span>${o.esc(o.t(word(MG_WHY_WORD, w.why)))}</span></p>` : ""}
    <p class="sv-btns"><button class="${o.btn.primary}" data-wait data-act="shv:mw:save"${why ? ` disabled data-why="${o.esc(why)}"` : ""}>${o.esc(o.t("sv_mw_save"))}</button></p>
    <p class="sv-note" data-item="preview">${o.esc(o.t("sv_mw_languages"))}</p>${state}</section>`;
}

/** Message results: totals by kind, from 5 up; nothing per person and no email or text opens. */
export function resultsHtml(st: SharedState, o: SharedLook, kindBuilt: (kind: string) => boolean): string {
  void st;
  const lo = MESSAGE_SYSTEM.min_shown;
  const rows: { kind: string; sent: number; delivered: number; failed: number; acted: number }[] = [
    { kind: "receipt", sent: 128, delivered: 121, failed: 3, acted: 0 }, { kind: "queue_your_turn", sent: 64, delivered: 62, failed: 2, acted: 51 },
    { kind: "survey_invite", sent: 40, delivered: 38, failed: 1, acted: 9 },
  ].filter((r) => MK_WORD[r.kind] && kindBuilt(r.kind));
  const num = (n: number): string => (n >= lo ? String(n) : o.t("sv_mr_few", { n: lo }));
  return `<section class="sv">${intro(o, "sv_mr_intro")}<ul class="rows sv-rows" data-item="totals">${rows.map((r) => `<li><span class="sv-main"><span class="sv-nm">${o.esc(o.t(word(MK_WORD, r.kind)))}</span><span class="sv-sub">${o.esc(o.t("sv_mr_line", { sent: num(r.sent), delivered: num(r.delivered), failed: num(r.failed), acted: num(r.acted) }))}</span></span></li>`).join("")}</ul>
    <p class="sv-note" data-item="privacy">${o.icon("ui-lock")}<span>${o.esc(o.t("sv_mr_privacy", { n: lo }))}</span></p></section>`;
}

/** The page for an id, with its title word. */
export function sharedPage(id: SharedPage, st: SharedState, o: SharedLook, ctx: { links: readonly ConsentLink[]; built: (section: string) => boolean; kindBuilt?: (kind: string) => boolean }): string {
  const kb = ctx.kindBuilt ?? (() => true);
  switch (id) {
    case "calendar": return calendarHtml(st, o, ctx.built);
    case "contacts": return contactsHtml(st, o);
    case "recycle_bin": return binHtml(st, o);
    case "audit": st.looks += 1; return auditHtml(st, o);
    case "consents": return consentsHtml(st, o, ctx.links);
    case "test_copy": return testCopyHtml(st, o);
    case "role_inbox": return roleInboxHtml(st, o);
    case "broadcast": return broadcastHtml(st, o);
    case "email_in": return emailInHtml(st, o, ctx.built);
    case "message_wording": return wordingHtml(st, o, ctx.built, kb);
    case "message_results": return resultsHtml(st, o, kb);
  }
}
export const sharedTitle = (id: SharedPage): string => TITLE_WORD[id];

/** Typing on the pages (data-in prefix shv:): kept in the state, no redraw, so the field keeps its focus. */
export function sharedInput(st: SharedState, key: string, value: string): boolean {
  if (key === "shv:bc_text") { st.msg.bc.text = value.slice(0, MESSAGE_SYSTEM.broadcast.max_chars); st.msg.bc.why = null; st.msg.bc.confirm = null; return false; }
  if (key === "shv:mw_text") { st.msg.mw.text = value.slice(0, MESSAGE_SYSTEM.wording.max_chars); st.msg.mw.why = null; return false; }
  if (key === "shv:mw_kind") { st.msg.mw.kind = value; st.msg.mw.text = ""; st.msg.mw.state = "standard"; st.msg.mw.why = null; return true; }
  return false;
}

/** The message pages' actions; sample people, labelled Sample. In the cloud these are services/message_desk.py and the Notifier. */
function msgAct(st: SharedState, k: string, v: string): void {
  const m = st.msg, me = "you";
  const item = Object.values(m.inbox).flat().find((x) => x.id === v);
  m.copied = k === "copy_addr" ? v : null;
  if (k === "inbox") m.role = v;
  if (k === "take" && item && !item.takenBy) item.takenBy = me;
  if (k === "done" && item && item.takenBy === me) item.doneBy = me;
  if (k === "aud") { m.bc.aud = v; m.bc.confirm = null; }
  if (k === "bc") {
    if (v === "cancel") { m.bc.confirm = null; return; }
    if (!mayLead(st.role)) return;
    const text = m.bc.text.trim();
    if (!text) { m.bc.why = "empty"; return; }
    if (checkWording("{business} " + text) === "not_allowed") { m.bc.why = "not_allowed"; return; }
    if (m.bc.sent.filter((x) => st.now - x.at < 86400).length >= MESSAGE_SYSTEM.broadcast.per_day) { m.bc.why = "per_day"; return; }
    if (v === "send") { m.bc.confirm = 2; return; }        // two of the sample people get a text: shown before it is spent
    m.bc.sent.unshift({ id: `BC-${m.bc.sent.length + 1}`, aud: m.bc.aud, at: st.now, seen: [], notSeen: [...SAMPLE_PEOPLE] });
    m.bc.text = ""; m.bc.confirm = null; m.bc.why = null;
  }
  if (k === "release" || k === "drop") m.held = m.held.filter((h) => h.id !== v);
  if (k === "release") m.allowed += 1;
  if (k === "mw") {
    if (!mayLead(st.role)) return;
    if (v === "save") { const why = checkWording(m.mw.text); m.mw.why = why; if (!why) m.mw.state = "testing"; }
    if (v === "approve" && st.role === "owner" && m.mw.state === "testing") m.mw.state = "live";
    if (v === "reset") { m.mw.state = "standard"; m.mw.text = ""; m.mw.why = null; }
  }
}

/** The page's actions (prefix shv:): delete to the bin, restore, switch a link, withdraw, open or close the test copy, and the
 *  message pages' actions. */
export function sharedAct(st: SharedState, a: string): boolean {
  if (!a.startsWith("shv:")) return false;
  const [, k = "", v = ""] = a.split(":");
  if (["inbox", "take", "done", "aud", "bc", "release", "drop", "mw", "copy_addr"].includes(k)) { msgAct(st, k, v); return true; }
  const c = st.contacts.find((x) => x.id === v);
  if (k === "delete" && c && binnable("crm_record")) c.binned = st.now;
  if (k === "restore") { if (c) c.binned = null; st.files = st.files.filter((f) => f.id !== v); }
  if (k === "link") st.links[v] = !st.links[v];
  if (k === "withdraw") st.shared.forEach((x) => { if (x.id === v) x.withdrawn = true; });
  if (k === "copy") st.testCopy = v === "open";
  return true;
}
