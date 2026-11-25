/** The owner's Business app in a browser on a laptop (42 J build section 3; 44 C web rule; 45 D automation control panel).
 *  Today at a glance, sales, registered devices, staff and shifts with cash differences, agent commissions matched to partner
 *  statements, the automation control panel and history at app.lynkomni.com/business/automations ("Why did this happen?" and an
 *  off switch for each), and data sharing with suppliers (one consent each, withdrawable). Selling is not here: the till needs a
 *  registered device, so "New sale" explains that instead of opening a till in the browser. */
import { PageWait } from "../../../ts/src/placeholder.js";
import type { UserState } from "../../../ts/src/pos.js";
import { homeCards, webRule } from "../../../ts/src/business.js";
import { matchStatement } from "../../../ts/src/agent.js";
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, newId, panelChange, panelHtml, stateButtons, appMainFooter, pageWaiting } from "../../../ts/src/emulator.js";
import { emailFieldHtml, wireEmails } from "../../../ts/src/emailfield.js";
import { FOOTER_EMAIL_ID } from "../../../ts/src/footer.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";
import { brandMark } from "../../../ts/src/brand.js";
import { panelShell, sampleAccount } from "../../../ts/src/deviceshell.js";
import type { Entry } from "../../../ts/src/shell.js";
import { DeviceMode } from "../../../ts/src/devicemode.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";
import { firstColumnHtml, launcherGroupsHtml, orderedMenuHtml } from "../../../ts/src/appshell.js";
import type { BarLook } from "../../../ts/src/appshell.js";
import { NAV } from "../../../ts/src/navigation.generated.js";
import { OFFICE_PATHS, OFFICE_SERVICES, OfficeView } from "../../../ts/src/officeview.js";
import type { OfficeService } from "../../../ts/src/officeview.js";
import { WORK_PATHS, WORK_SERVICES, WorkView } from "../../../ts/src/workview.js";
import type { WorkService } from "../../../ts/src/workview.js";
import { watchNames, namePair } from "../../../ts/src/names.js";
import { mayShow, slotHtml, whyHtml } from "../../../ts/src/ads.js";
import { NAME_INFO_KEYS } from "../../../ts/src/nameinfo.js";
import { Tracking } from "../../../ts/src/tracking.js";
import { REGISTER } from "../../../ts/src/tracking.generated.js";
import { towerHtml, exceptionsHtml, scanHtml, extraStepsHtml } from "../../../ts/src/trackview.js";
import type { TowerLook } from "../../../ts/src/trackview.js";
import { SHARED_PAGES, sampleShared, sharedPage, sharedAct, sharedInput, plansLimitsHtml } from "../../../ts/src/sharedview.js";
import type { SharedLook, SharedPage, ConsentLink } from "../../../ts/src/sharedview.js";
const SIDE_W = 200;   // px of room the 220 px sidebar gives its brand place (side-menu: logo from 140 px)

interface Auto { id: string; level: string; assist: string | null; trigger: string; min_tier: string | null; default: string }
declare const DATA: Build & { automations: Auto[]; autoSystem: { days: number; maxPerDay: number; afterHours: number }; planLimits: Record<string, Record<string, Record<string, number | null>>>; consentLinks: ConsentLink[]; launcher: { family: string; name: string; app: string }[]; taxBp: Record<string, number> };
type Page = "today" | "sales" | "devices" | "staff" | "commissions" | "automations" | "sharing" | "tracking" | SharedPage | "plans";
const PAGES: Page[] = ["today", "sales", "devices", "staff", "commissions", "automations", "sharing", "tracking", ...SHARED_PAGES, "plans"];
const PATH: Record<Page, string> = { today: "/business", sales: "/sell/sales", devices: "/business/devices", staff: "/business/team", commissions: "/business/agent-earnings", automations: "/business/automations", sharing: "/business/settings/data-sharing", tracking: "/tracking",
  calendar: "/business/calendar", contacts: "/business/contacts", recycle_bin: "/business/recycle-bin", audit: "/business/audit", consents: "/business/settings/consents", test_copy: "/business/settings/test-copy", plans: "/business/plans",
  role_inbox: "/business/team-inbox", broadcast: "/business/urgent-messages", message_results: "/business/message-results", email_in: "/business/settings/forward-by-email", message_wording: "/business/settings/message-wording" };
const TIERS = ["free", "plus", "pro", "max"] as const;
const S: PanelState & { page: Page; off: Set<string>; why: string; sharing: Set<string>; notice: string; launcher: boolean; place: string; office: string } =
  { online: true, fail: false, type: "shop", tier: "plus", country: "", realUser: false, practice: false, dark: false, lang: "en", page: "today", off: new Set(), why: "", sharing: new Set(), notice: "", launcher: false, place: "", office: "" };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const icon = (id: string): string => `<span class="ic" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); });
const key = (id: string): string => id.replace(/-/g, "_");
const H = 3_600_000, now = Date.now();
const SALES = [[8, 4500, "cash_received"], [7, 12000, "confirmed"], [5, 3200, "cash_received"], [3, 9800, "pending_confirmation"], [2, 1500, "failed"], [1, 6700, "confirmed"]] as const;
const HISTORY = [["day-close-prepare", 20], ["cash-difference-flag", 26], ["low-stock-reorder", 50], ["receipt-delivery", 70], ["staff-pin-lock", 95], ["sync-retry", 130]] as const;
const ours = { r1: 120, r2: 75, r3: 40 };
const reported = [{ request_id: "r1", commission: 120 }, { request_id: "r2", commission: 70 }];

function today(): string {
  const total = SALES.filter((s) => s[2] !== "failed").reduce((a, s) => a + s[1], 0);
  const cards = homeCards("owner", false, 2, 1, 1, 3);
  const val: Record<string, string> = { today_sales: C.money(total), today_profit: C.money(Math.round(total * 0.22)), new_sale: "", stock_alerts: `${t("low_stock")} · ${t("negative_stock")}`, chats: "3", insight: t("best_seller", { name: t("p_bread") }), pending_sync: t("pending_items", { n: 2 }) };
  return `<h1>${esc(t("home"))}</h1><div class="cards">${cards.map((c) => c === "new_sale" ? `<button class="card action" data-act="newsale">${icon("ui-cart")}<strong>${esc(t("new_sale"))}</strong></button>` : `<div class="card"><span>${esc(t(c))}</span><strong>${esc(val[c] ?? "")}</strong></div>`).join("")}</div>
    ${S.notice ? `<p class="notice" role="status">${icon("ui-info")}${esc(S.notice)}</p>` : ""}<p class="note">${esc(t("laptop_note"))}</p>`;
}
function sales(): string {
  const word = (st: string): UserState => (st === "confirmed" ? "confirmed" : st === "failed" ? "failed" : st === "cash_received" ? "accepted" : "sent");
  return `<h1>${esc(t("sales"))}</h1><table><thead><tr><th>${esc(t("receipt"))}</th><th>${esc(t("total"))}</th><th>${esc(t("pay"))}</th></tr></thead><tbody>${SALES.map((s, i) => `<tr><td>TB-${i + 101} · ${esc(C.clock(now - s[0] * H))}</td><td>${esc(C.money(s[1]))}</td><td>${s[2] === "cash_received" ? esc(t("cash")) : chip(word(s[2]))}</td></tr>`).join("")}</tbody></table><p class="note">${esc(t("not_proof"))}</p>`;
}
function devices(): string {
  const list = [["device_kind_handheld", true, 1], ["device_kind_tablet", true, 3], ["device_kind_phone", false, 50]] as const;
  return `<h1>${esc(t("devices"))}</h1><p class="note">${esc(t("needs_registered_device"))}</p><ul class="rows">${list.map(([k, active, h]) => `<li><span>${icon("ui-lock")}${esc(t(k))}</span><span>${esc(t("last_seen", { when: C.clock(now - h * H) }))}</span><span>${active ? chip("confirmed") : chip("failed")}</span>${active ? `<button class="secondary" data-act="revoke">${esc(t("revoke"))}</button>` : ""}</li>`).join("")}</ul>
    <p class="note">${esc(t("sell"))}: ${esc(webRule("sell", false) === "registered_device" ? t("needs_registered_device") : "")}</p>`;
}
function staff(): string {
  return `<h1>${esc(t("staff_shifts"))}</h1><ul class="rows"><li><span>${esc(t("sample_staff_1"))}</span><span>${esc(t("day_end"))}</span><span>${esc(t("difference"))}: ${esc(C.money(-500))}</span><em>${esc(t("difference_flagged"))}</em></li>
    <li><span>${esc(t("sample_staff_2"))}</span><span>${esc(t("handover"))}</span><span>${esc(t("no_difference"))}</span></li></ul>`;
}
function commissions(): string {
  const m = matchStatement(ours, reported);
  return `<h1>${esc(t("agent_commissions"))}</h1><p>${esc(t("statement_matched", { n: m.matched }))} · ${esc(C.money(m.total))}</p><p class="warn">${esc(t("statement_mismatch", { n: m.mismatches.length }))}</p>
    <ul class="rows">${Object.entries(ours).map(([id, c]) => { const r = reported.find((x) => x.request_id === id); return `<li><span>${esc(t("partner_a"))} · ${esc(id.toUpperCase())}</span><span>${esc(C.money(c))}</span><span>${r ? esc(C.money(r.commission)) : "—"}</span>${r && r.commission === c ? chip("confirmed") : chip("failed")}</li>`; }).join("")}</ul><p class="note">${esc(t("float_read_live"))}</p>`;
}
// ---- the automation system (CONNECT UPDATE 71.2, section 4 row 71.9; services/flow.py is the rule): sample state, labelled Sample ----
const SY = DATA.autoSystem;
const DRAFT_IDS = DATA.automations.filter((a) => a.level === "draft").slice(0, 2).map((a) => a.id);
const AU: { open: string; tried: Set<string>; digest: Set<string>; paused: string; drafts: { id: string; automation: string; step: number }[] } =
  { open: "", tried: new Set(), digest: new Set(), paused: DATA.automations.find((a) => a.level === "auto")?.id ?? "", drafts: DRAFT_IDS.map((a, i) => ({ id: `d${i + 1}`, automation: a, step: 0 })) };
const CHAIN = ["au_role_manager", "au_role_owner"];
/** A steady sample count for "would have started", so the screen never shows a made-up number twice differently. */
const wouldStart = (id: string): number => [...id].reduce((n, ch) => (n * 31 + ch.charCodeAt(0)) % 97, 7) + 3;
function autoSystemHtml(): string {
  const paused = AU.paused ? `<p class="notice au-paused" role="status">${icon("ui-warning")}<span>${esc(t("au_paused", { name: t(`auto_${key(AU.paused)}`) }))}</span><button class="secondary" data-act="au:resume">${esc(t("au_resume"))}</button></p>` : "";
  const waiting = AU.drafts.filter((d) => d.step < CHAIN.length);
  const drafts = waiting.length ? `<h2>${esc(t("au_waiting"))}</h2><p class="note">${esc(t("au_escalate", { hours: SY.afterHours }))}</p><ul class="rows">${waiting.map((d) => `<li><span>${esc(t(`auto_${key(d.automation)}`))} · ${esc(t("au_sample"))}</span><span>${esc(t("au_step", { n: d.step + 1, total: CHAIN.length, role: t(CHAIN[d.step]!) }))}</span><button class="primary" data-act="au:approve:${d.id}">${esc(t("au_approve"))}</button></li>`).join("")}</ul>${waiting.length > 1 ? `<p><button class="secondary" data-act="au:all">${esc(t("au_approve_all"))}</button></p>` : ""}` : "";
  return paused + drafts;
}
function autoDetail(a: Auto): string {
  if (AU.open !== a.id) return "";
  const tried = AU.tried.has(a.id) ? `<p class="note" role="status">${esc(t("au_would", { n: wouldStart(a.id) }))} · ${esc(t("au_sample"))}</p>` : "";
  const digest = a.level === "inform" ? `<label class="au-check"><input type="checkbox" data-act="au:digest:${a.id}"${AU.digest.has(a.id) ? " checked" : ""}> <span>${esc(t("au_digest"))}</span></label>` : "";
  return `<div class="au-more"><p>${esc(t("au_owner", { name: t("au_role_owner") }))} · ${esc(t("au_limit", { n: SY.maxPerDay }))}</p><p><button class="link" data-act="au:try:${a.id}">${esc(t("au_try", { days: SY.days }))}</button></p>${tried}${digest}</div>`;
}
function auAct(a: string): boolean {
  if (!a.startsWith("au:")) return false;
  const [, k = "", v = ""] = a.split(":");
  if (k === "resume") AU.paused = "";
  if (k === "approve") { const d = AU.drafts.find((x) => x.id === v); if (d) d.step += 1; }
  if (k === "all") AU.drafts.forEach((d) => { if (d.step < CHAIN.length) d.step += 1; });
  if (k === "open") AU.open = AU.open === v ? "" : v;
  if (k === "try") AU.tried.add(v);
  if (k === "digest") { if (AU.digest.has(v)) AU.digest.delete(v); else AU.digest.add(v); }
  return true;
}
function automations(): string {
  return `<h1>${esc(t("automations"))}</h1><p class="note">${esc(t("automations_intro"))}</p>${autoSystemHtml()}<ul class="autos">${DATA.automations.map((a) => { const on = !S.off.has(a.id) && a.default === "on" && AU.paused !== a.id;
    return `<li><div><strong>${esc(t(`auto_${key(a.id)}`))}</strong><span class="lvl">${esc(t(`level_${a.level}`))}${a.assist ? ` · ${esc(t("assist_suggestion"))}` : ""}</span>${autoDetail(a)}</div><button class="secondary au-set" aria-expanded="${AU.open === a.id}" data-act="au:open:${a.id}">${esc(t("au_settings"))}</button><button class="switch${on ? " on" : ""}" role="switch" aria-checked="${on}" data-act="toggle:${a.id}">${esc(t(on ? "on" : "off"))}</button></li>`; }).join("")}</ul>
    <h2>${esc(t("automation_history"))}</h2><ul class="rows">${HISTORY.filter(([id]) => !S.off.has(id)).map(([id, min]) => `<li><span>${esc(t(`auto_${key(id)}`))}</span><span>${esc(t("ran_at", { when: C.clock(now - min * 60000) }))}</span><button class="link" data-act="why:${id}">${esc(t("why_happened"))}</button>${S.why === id ? `<p class="why">${esc(t(`why_${key(id)}`))}</p>` : ""}</li>`).join("")}</ul>`;
}
function sharing(): string {
  const sup = [["s1", "supplier_1"], ["s2", "supplier_2"]] as const;
  return `<h1>${esc(t("data_sharing"))}</h1><p class="note">${esc(t("data_sharing_body"))}</p><ul class="rows">${sup.map(([id, w]) => `<li><span>${esc(t(w))}</span>${S.sharing.has(id) ? `${chip("confirmed")}<button class="secondary" data-act="unshare:${id}">${esc(t("stop_sharing"))}</button>` : `<button class="primary" data-act="share:${id}">${esc(t("share"))}</button>`}</li>`).join("")}</ul><p>${esc(t("sharing_with", { n: S.sharing.size }))}</p>`;
}
// ---- the control tower (TRACKING UPDATE 72.4, section 4 row 72.9): sample items run through the real engine (ts/src/tracking.ts) ----
const ME = "m-sample", MIN = 60, T_NOW = Math.floor(now / 1000);
const TRK = new Tracking(REGISTER);
const TRK_NAMES: Record<string, string> = {};
const TRK_PRACTICE = new Set<string>();
function trkSample(): void {
  const at = (minAgo: number): number => T_NOW - minAgo * MIN;
  const e = (type: string, minAgo: number, id: string, payload: Record<string, unknown>): void => { TRK.apply({ type, payload, at: at(minAgo), id: `${id}-${type}` }, ME); };
  // three deliveries: on time, late, and one where the rider marked delivered after the partner had reported a failure (two endings clash)
  e("DeliveryRequested", 6, "d1", { delivery_id: "d1", order_id: "o9", own_rider: true, price: 0, currency: "USD" });
  e("DeliveryRequested", 90, "d2", { delivery_id: "d2", order_id: "o8", own_rider: true, price: 0, currency: "USD" }); e("DeliveryPickedUp", 85, "d2", { delivery_id: "d2" });
  e("DeliveryRequested", 50, "d3", { delivery_id: "d3", order_id: "o7", own_rider: true, price: 0, currency: "USD" }); e("DeliveryFailed", 20, "d3", { delivery_id: "d3", reason_code: "timeout" }); e("DeliveryDelivered", 10, "d3", { delivery_id: "d3", proof: "code" });
  // kitchen orders: one about to miss its promise, one ready and waiting for the customer, one practice order that is never raised
  e("OrderSentToKitchen", 9, "o1", { order_id: "o1", table_id: "t1", lines: [{ line_no: 0 }] });
  e("OrderSentToKitchen", 20, "o2", { order_id: "o2", table_id: "t2", lines: [{ line_no: 0 }] }); e("KitchenItemReady", 15, "o2", { order_id: "o2", line_no: 0 }); e("KitchenItemReady", 12, "o2b", { order_id: "o2", line_no: 0 });
  e("OrderSentToKitchen", 2, "o3", { order_id: "o3", table_id: "t3", lines: [{ line_no: 0 }], practice: true });
  e("TicketIssued", 30, "k1", { ticket_id: "k1", section: "A" });
  Object.assign(TRK_NAMES, { d1: "DLV-1041", d2: "DLV-1038", d3: "DLV-1036", o1: "ORD-2207", o2: "ORD-2204", o3: "ORD-2209", k1: "A-7KQ2MD" });
  TRK_PRACTICE.add("o3");
}
trkSample();
const TS: { item: string; step: string; proof: string; result: { ok: boolean; event: string | null; why: string[] } | null; extra: { id: string; label: string }[]; draft: string } =
  { item: "delivery|d1", step: "on_the_way", proof: "", result: null, extra: [], draft: "" };
const towerLook = (): TowerLook => ({ t, esc, icon, chip, time: (x) => C.clock(Date.parse(x)), name: (_k, r) => TRK_NAMES[r] ?? r });
function tracking(): string {
  const o = towerLook(), active = TRK.active(ME, T_NOW);
  const items = active.map((v) => ({ kind: v.kind, record: v.record ?? "" })).filter((x) => x.record);
  const kind = TS.item.split("|")[0] ?? "delivery";
  const steps = Object.keys(REGISTER.kinds.find((k) => k.id === kind)?.scan ?? {});
  if (!steps.includes(TS.step)) TS.step = steps[0] ?? "";
  return `<h1>${esc(t("trk_tower"))}</h1>${exceptionsHtml(TRK.exceptions(ME, T_NOW), o)}${towerHtml(TRK.tower(ME, T_NOW), o, TRK_PRACTICE)}
    ${scanHtml(items, steps, o, TS)}${extraStepsHtml("order", TS.extra, REGISTER.engine?.extra_steps_max ?? 5, o, TS.draft)}`;
}
function trkAct(a: string): boolean {
  if (!a.startsWith("trk:")) return false;
  const [, k = "", v = ""] = a.split(":");
  if (k === "scan") { const [kind = "", rec = ""] = TS.item.split("|"); TS.result = TRK.scan(kind, rec, TS.step, TS.proof || null); if (TS.result.ok && TS.result.event) LOG.emit(TS.result.event, { [REGISTER.kinds.find((x) => x.id === kind)?.key ?? "id"]: rec, ...(TS.proof ? { proof: TS.proof } : {}) }, "device"); }
  if (k === "add" && TS.draft.trim()) { const id = `own_${TS.extra.length + 1}`; TS.extra = [...TS.extra, { id, label: TS.draft.trim() }]; TRK.setExtraSteps(ME, "order", TS.extra); TS.draft = ""; }
  if (k === "drop") { TS.extra = TS.extra.filter((x) => x.id !== v); TRK.setExtraSteps(ME, "order", TS.extra); }
  return true;
}
function trkInput(key: string, value: string): boolean {
  if (!key.startsWith("trk:")) return false;
  const k = key.slice(4);
  if (k === "item") { TS.item = value; TS.result = null; } else if (k === "step") { TS.step = value; TS.result = null; } else if (k === "proof") { TS.proof = value; TS.result = null; } else if (k === "extra") TS.draft = value;
  return true;
}
// ---- the parts every service shares (CONNECT UPDATE 71.3, section 4 row 71.9 step 2b): drawn by ts/src/sharedview.ts ----
const SHV = sampleShared(Math.floor(now / 1000));
const shvLook = (): SharedLook => ({ t, esc, icon, name: (f) => nameOf(f), date: (secs) => C.date(secs * 1000), btn: { primary: "primary", secondary: "secondary" },
  toggle: (on, act, label, why) => `<button class="switch${on ? " on" : ""}" role="switch" aria-checked="${on}" aria-label="${esc(label)}" data-act="${esc(act)}"${why ? ` disabled data-why="${esc(why)}"` : ""}>${esc(t(on ? "on" : "off"))}</button>` });
const shvBuilt = (section: string): boolean => section === "4" || ["1", "2", "3", "3A", "3B"].includes(section);
function sharedOwner(id: SharedPage): string {
  return `<h1>${esc(t(LABEL[id]))}</h1>${sharedPage(id, SHV, shvLook(), { links: DATA.consentLinks, built: shvBuilt })}`;
}
function plansOwner(): string {
  const rows = Object.entries(DATA.planLimits).map(([family, tiers]) => { const tier = family === "lynkinv" ? "plus" : "free";
    return { family, tier, limits: Object.entries(tiers[tier] ?? {}).map(([key, limit]) => ({ key, limit, used: key === "customers" ? 37 : 12 })) }; });
  return `<h1>${esc(t("sv_plans_limits"))}</h1>${plansLimitsHtml(rows, shvLook())}`;
}
const LABEL: Record<Page, string> = { today: "home", sales: "sales", devices: "devices", staff: "staff_shifts", commissions: "agent_commissions", automations: "automations", sharing: "data_sharing", tracking: "trk_tower",
  calendar: "sv_calendar", contacts: "sv_contacts", recycle_bin: "sv_recycle_bin", audit: "sv_audit", consents: "sv_consents", test_copy: "sv_test_copy", plans: "sv_plans_limits",
  role_inbox: "sv_role_inbox", broadcast: "sv_broadcast", message_results: "sv_message_results", email_in: "sv_email_in", message_wording: "sv_message_wording" };
const DSH = panelShell({
  st: S, t, icon, clock: (ms) => C.clock(ms),
  native: () => (DATA.i18n[S.lang]?.native ?? S.lang), region: () => (C.pack().sample ? t("sample_country") : C.pack().name), currency: () => C.pack().currency,
  pending: () => LOG.pending().count, lastSync: () => LOG.events.find((e) => e.sync === "accepted")?.at ?? null,
  screen: () => ({ id: S.page, title: t(LABEL[S.page]), path: PATH[S.page] }),
  entries: (): Entry[] => [{ id: "new", kind: "action", title: t("new_sale"), act: "newsale" }, ...PAGES.map((p): Entry => ({ id: p, kind: p === "sales" || p === "commissions" ? "report" : "setting", title: t(LABEL[p]), act: `go:${p}` })),
    ...DATA.automations.map((a): Entry => ({ id: a.id, kind: "setting", title: t(`auto_${key(a.id)}`), act: "go:automations" }))],
  account: () => sampleAccount(t, "owner", ["owner", "manager"], t("sample_shop"), S.dark ? "dark" : "light", DATA.i18n[S.lang]?.native ?? S.lang, C.pack().sample ? t("sample_country") : C.pack().name),
  run: (a) => act(a), redraw: () => draw(),
});
// ---- the office services in the browser (section 4 step D5): LynkAcc, LynkInv, LynkCRM and LynkStat from ts/src/officeview.ts ---
// ADS UPDATE 79 (section 4 row 79.10): one labelled card on LynkStat Free; off until the country's legal sign-off; a paid plan shows none
const AD = { on: false, why: false, reported: false };
const adSlot = (): string => !mayShow("dashboard_card", { screen: "dashboard", country_on: AD.on, ad_free: S.tier !== "free" }) ? ""
  : slotHtml("dashboard_card", { id: "sample-ad", text: t("ad_sample_text"), sample: true }, { t, esc, icon }) + (AD.why ? whyHtml({ t, esc, icon }) : "") + (AD.reported ? `<p class="ad-why" role="status">${esc(t("ad_reported"))}</p>` : "");
const OV = new OfficeView({ t, money: (n) => C.money(n), icon, chip, nav: NAV, role: "owner", user: "u-owner", today: "2026-11-20", taxBp: () => DATA.taxBp[S.country] ?? 0, ad: adSlot });
// ---- LynkHR, LynkProject and LynkFiles in the browser (build section 4B step 4): ts/src/workview.ts on the real rules of hr.ts, project.ts and files.ts
const WV = new WorkView({ t, money: (n) => C.money(n), icon, chip, nav: NAV, today: "2026-11-25" });
const work = (): WorkService | null => (WORK_SERVICES as readonly string[]).includes(S.place) ? (S.place as WorkService) : null;
const office = (): OfficeService | null => (OFFICE_SERVICES as readonly string[]).includes(S.place) ? (S.place as OfficeService) : null;
function page(): string { const o = office(); if (o) return OV.draw(o, S.office || OV.pages(o)[0]!.id); const w = work(); if (w) return WV.draw(w, S.office || WV.pages(w)[0]!.id); return S.place ? placePage() : (SHARED_PAGES as readonly string[]).includes(S.page) ? sharedOwner(S.page as SharedPage) : S.page === "plans" ? plansOwner() : ({ today, sales, devices, staff, commissions, automations, sharing, tracking } as Record<string, () => string>)[S.page]!(); }

// ---- the app shell on a computer: the two-level side bar (INTERFACE UPDATE 73.3, ts/src/appshell.ts) ---------------------------
const look: BarLook = { t, icon: (id) => icon(id) };
/** Where each first-column place goes in this view. Track joins in section 7 with the "Track" home; pins come with the person's own choices. */
const RAIL: Record<string, string> = { home: "go:today", inbox: "dsh:bell", track: "go:tracking", all_services: "launcher", emulators: "go:devices", automations: "go:automations", settings: "go:sharing", help: "dsh:help" };
const RAIL_CURRENT: Partial<Record<Page, string>> = { today: "home", tracking: "track", devices: "emulators", automations: "automations", sharing: "settings" };
/** This view's pages in the register's fixed order: Overview, the lists, Automations, Settings. */
const SLOT: Record<Page, string> = { today: "overview", sales: "list", devices: "list", staff: "list", commissions: "list", automations: "automations", sharing: "settings", tracking: "list",
  calendar: "list", contacts: "list", recycle_bin: "settings", audit: "reports", consents: "settings", test_copy: "settings", plans: "settings",
  role_inbox: "list", broadcast: "list", message_results: "reports", email_in: "settings", message_wording: "settings" };
const MINE = ["lynkpos", "lynkstock", "lynkchat", "lynkacc", "lynkinv", "lynkcrm", "lynkstat", "lynkhr", "lynkproject", "lynkfiles"];
const nameOf = (f: string): string => DATA.launcher.find((x) => x.family === f)?.name ?? f;
const appOf = (f: string): string => DATA.launcher.find((x) => x.family === f)?.app ?? "";
function sideBar(): string {
  const first = firstColumnHtml(NAV, look, { current: S.place ? "all_services" : RAIL_CURRENT[S.page] ?? "", hidden: [], act: "rail" });
  const logo = `<div class="menu-logo">${brandMark(DATA.brand.places, "side-menu", S.dark, "logo", SIDE_W)}</div>`;
  const o = office();
  const menu = o ? orderedMenuHtml(NAV, look, { items: OV.pages(o).map((p) => ({ id: p.id, slot: p.slot, label: OV.title(p.id) })), current: S.office || OV.pages(o)[0]!.id, act: "office", label: nameOf(o), top: logo })
    : work() ? orderedMenuHtml(NAV, look, { items: WV.pages(work()!).map((p) => ({ id: p.id, slot: p.slot, label: WV.title(p.id) })), current: S.office || WV.pages(work()!)[0]!.id, act: "office", label: nameOf(work()!), top: logo })
    : orderedMenuHtml(NAV, look, { items: PAGES.map((p) => ({ id: p, slot: SLOT[p], label: t(LABEL[p]) })), current: S.place ? "" : S.page, act: "go", label: "LynkOmni", top: logo });
  return first + menu;
}
/** A service opened from All services: its address and name; its screens on a computer come with its own build section. */
function placePage(): string {
  return `<h1>${esc(nameOf(S.place))}</h1><p class="note">${esc(appOf(S.place))}</p><p><button class="secondary" data-act="go:today">${esc(t("nv_home"))}</button></p>`;
}
function launcherOverlay(): string {
  if (!S.launcher) return "";
  return `<div class="dsh-scrim launch-scrim" data-act="launcher"><div class="launch" role="dialog" aria-modal="true" aria-label="${esc(t("nv_all_services"))}" data-stop="1"><h2>${esc(t("nv_all_services"))}</h2>
    ${launcherGroupsHtml(NAV, look, { mine: MINE, name: (f) => namePair(nameOf(f), t).main, plain: (f) => namePair(nameOf(f), t).sub, productIcon: () => "ui-grid", act: "place", families: DATA.launcher.map((x) => x.family) })}
    <button class="secondary" data-act="launcher">${esc(t("nv_back"))}</button></div></div>`;
}
/** The owner's computer view is the all-in-one without touch (catalog/devices.v1.json): mouse and keyboard. */
const DM = new DeviceMode(DEVICES, "all-in-one-pos", "non_touch");
const WAIT = new PageWait();
/** The footer's newsletter email (section 4C point 1): drawn by the shared email part, its text kept across redraws. */
const NEWS = { text: "" };
const newsBox = (label: string): string => emailFieldHtml({ t }, { id: FOOTER_EMAIL_ID, label, text: NEWS.text });
const newsWire = (root: ParentNode): void => wireEmails(root, { t, onEmail: (_id, v) => { NEWS.text = v.text; } });
function draw(): void {
  const el = $("#screen"); DM.apply(el); el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); el.classList.toggle("lowlit", DSH.pictures); applyRoot(el, W);
  el.innerHTML = `<div class="bar"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span><span class="url">${icon("ui-lock")}${esc(office() ? `app.lynkomni.com${OFFICE_PATHS[office()!]}` : work() ? `app.lynkomni.com${WORK_PATHS[work()!]}` : S.place ? appOf(S.place) : `app.lynkomni.com${PATH[S.page]}`)}</span></div>
    <div class="app">${sideBar()}<main class="main"><div class="mhead">${DSH.bar()}</div>${office() ? OV.browserNote() : work() ? WV.note() : `<p class="viewonly" role="note">${icon("ui-info")}${esc(t("view_only_computer"))}</p>`}<div data-wait-area data-wrap>${page()}</div>${appMainFooter(W, C, DATA, newsBox)}</main></div>${launcherOverlay()}${DSH.overlay()}`;
  const ad = document.getElementById("address"); if (ad) ad.textContent = DSH.address();
  newsWire(el);
  pageWaiting(WAIT, { online: true, firstOpen: S.firstOpen }, el, t, draw);   // PLACEHOLDER UPDATE 83: a browser page is online
}
/** Redraws while typing and puts the cursor back where it was, so a field never loses its place. */
function keepFocus(id: string): void { const el = document.getElementById(id) as HTMLInputElement | null; const pos = el?.selectionStart ?? null; draw(); const again = document.getElementById(id) as HTMLInputElement | null; if (again) { again.focus(); if (pos !== null && again.type !== "date") again.setSelectionRange(pos, pos); } }
function act(a: string): void {
  if (a.startsWith("ad:why:")) { AD.why = !AD.why; draw(); return; }
  if (a.startsWith("ad:report:")) { AD.reported = true; draw(); return; }
  const [k = "", v = ""] = a.split(":");
  if (trkAct(a) || auAct(a) || sharedAct(SHV, a)) { draw(); return; }
  if (k === "rail") { const to = RAIL[v]; if (to) { if (to.startsWith("dsh:")) { if (DSH.act(to)) return; } else act(to); } return; }
  if (a === "launcher") { S.launcher = !S.launcher; draw(); return; }
  if (k === "office") { S.office = v; OV.reset(); draw(); return; }
  if (WV.act(a)) { draw(); return; }
  if (OV.act(a)) { if (k === "of" && a.startsWith("of:go:")) { S.office = a.slice(6); OV.reset(); } draw(); return; }
  if (k === "place") { S.launcher = false; S.office = ""; OV.reset(); const page = (Object.keys(PATH) as Page[]).find((p) => appOf(v) === `app.lynkomni.com${PATH[p]}` || (v === "lynkpos" && p === "sales")); if (page) { S.place = ""; S.page = page; } else S.place = v; draw(); return; }
  if (k === "go") { S.place = ""; S.page = PAGES.includes(v as Page) ? (v as Page) : "today"; S.why = ""; S.notice = ""; }
  if (k === "newsale") S.notice = t("needs_registered_device");
  if (k === "toggle") { const on = !S.off.has(v); if (on) S.off.add(v); else S.off.delete(v); }
  if (k === "why") S.why = S.why === v ? "" : v;
  if (k === "share") { S.sharing.add(v); LOG.emit("DataSharingConsentGiven", { supplier: v, consent: "LOCNS-…" }, "server"); }
  if (k === "unshare") { S.sharing.delete(v); LOG.emit("DataSharingConsentWithdrawn", { supplier: v }, "server"); }
  if (k === "revoke") LOG.emit("DeviceRevoked", { device_id: newId(), reason: "staff_left" }, "server");
  draw();
}
function panel(): void {
  $("#panel").innerHTML = panelHtml(["plan", "firstopen", "country", "dark", "lang"], S, W, C, { tiers: TIERS }) + `<label><input type="checkbox" data-ctl="ads"${AD.on ? " checked" : ""}> <span>${esc(t("ad_sponsored"))} · ${esc(t("ad_sample"))}</span></label>`;
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  const OFFICE_STATES = OFFICE_SERVICES.flatMap((svc) => OV.pages(svc).map((p) => p.id));
  const WORK_STATES = WORK_SERVICES.flatMap((svc) => WV.pages(svc).map((p) => p.id));        // every LynkHR, LynkProject and LynkFiles page too        // every office page, so every check visits it
  stateButtons($("#stateButtons"), [...PAGES, "why", "new-sale", ...OFFICE_STATES, ...WORK_STATES, "inv_record", "crm_record"], (k) => {
    OV.reset();
    const svc = OFFICE_SERVICES.find((x) => OV.pages(x).some((p) => p.id === k));
    if (svc) { S.place = svc; S.office = k; draw(); return; }
    const wsv = WORK_SERVICES.find((x) => WV.pages(x).some((p) => p.id === k));
    if (wsv) { S.place = wsv; S.office = k; draw(); return; }
    if (k === "inv_record") { S.place = "lynkinv"; S.office = "inv_list"; OV.act("of:inv:LOINV-1002"); OV.act("of:creditnote"); draw(); return; }
    if (k === "crm_record") { S.place = "lynkcrm"; S.office = "crm_list"; OV.act("of:person:LOCST-1001"); draw(); return; }
    S.place = ""; S.office = "";
    if (k === "why") { S.page = "automations"; S.why = "cash-difference-flag"; } else if (k === "new-sale") { S.page = "today"; S.notice = t("needs_registered_device"); } else { S.page = k as Page; S.why = ""; S.notice = ""; } draw(); });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? ""; panel(); draw();
  document.addEventListener("click", (e) => { const tg = e.target as HTMLElement, b = tg.closest<HTMLElement>("[data-act]"); if (!b) return; const a = b.dataset["act"] ?? "";
    if (b.classList.contains("dsh-scrim") && tg.closest("[data-stop]")) return; if (!DSH.act(a)) act(a); });
  document.addEventListener("input", (e) => { const el = e.target as HTMLInputElement;
    if (el.id === "ofSearch") { OV.search(el.value); keepFocus(el.id); return; }
    const k = el.dataset["in"] ?? ""; if (k.startsWith("shv:")) { if (sharedInput(SHV, k, el.value)) draw(); return; } if (trkInput(k, el.value)) { keepFocus(el.id); return; } if (WV.input(k, el.value)) { keepFocus(el.id); return; } if (OV.input(k, el.value)) { keepFocus(el.id); return; } DSH.input(el); });
  document.addEventListener("change", (e) => { const el = e.target as HTMLSelectElement; if (el.tagName === "SELECT" && (el.dataset["in"] ?? "").startsWith("shv:")) { if (sharedInput(SHV, el.dataset["in"] ?? "", el.value)) draw(); return; } if (el.closest("#screen") && el.tagName === "SELECT" && (trkInput(el.dataset["in"] ?? "", el.value) || WV.input(el.dataset["in"] ?? "", el.value) || OV.input(el.dataset["in"] ?? "", el.value))) draw(); });
  document.addEventListener("keydown", (e) => { DSH.key(e); });
  (window as unknown as { __settle: () => void }).__settle = () => { DSH.settle(); draw(); };
  $("#panel").addEventListener("change", (e) => { const el = e.target as HTMLInputElement; if (el.dataset["ctl"] === "ads") { AD.on = el.checked; AD.why = false; AD.reported = false; draw(); return; } if (panelChange(e.target as HTMLSelectElement, S, DATA, { tiers: TIERS })) panel(); draw(); });
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 1180);
}
main();
/** Every Lynk name on this page carries its plain word (catalog/names.v1.json, ts/src/names.ts). */
watchNames(document.body, () => t);
void NAME_INFO_KEYS;   // this page carries the one-line descriptions, so search and the name notes say what each product does
