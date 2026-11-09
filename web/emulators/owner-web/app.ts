/** The owner's Business app in a browser on a laptop (42 J build section 3; 44 C web rule; 45 D automation control panel).
 *  Today at a glance, sales, registered devices, staff and shifts with cash differences, agent commissions matched to partner
 *  statements, the automation control panel and history at app.lynkomni.com/business/automations ("Why did this happen?" and an
 *  off switch for each), and data sharing with suppliers (one consent each, withdrawable). Selling is not here: the till needs a
 *  registered device, so "New sale" explains that instead of opening a till in the browser. */
import type { UserState } from "../../../ts/src/pos.js";
import { homeCards, webRule } from "../../../ts/src/business.js";
import { matchStatement } from "../../../ts/src/agent.js";
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, newId, panelChange, panelHtml, stateButtons, appMainFooter } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";
import { brandMark } from "../../../ts/src/brand.js";
const SIDE_W = 200;   // px of room the 220 px sidebar gives its brand place (side-menu: logo from 140 px)

interface Auto { id: string; level: string; assist: string | null; trigger: string; min_tier: string | null; default: string }
declare const DATA: Build & { automations: Auto[] };
type Page = "today" | "sales" | "devices" | "staff" | "commissions" | "automations" | "sharing";
const PAGES: Page[] = ["today", "sales", "devices", "staff", "commissions", "automations", "sharing"];
const PATH: Record<Page, string> = { today: "/business", sales: "/sell/sales", devices: "/business/devices", staff: "/business/staff", commissions: "/business/money/commissions", automations: "/business/automations", sharing: "/business/settings/data-sharing" };
const TIERS = ["free", "plus", "pro", "max"] as const;
const S: PanelState & { page: Page; off: Set<string>; why: string; sharing: Set<string>; notice: string } =
  { online: true, fail: false, type: "shop", tier: "plus", country: "", realUser: false, practice: false, dark: false, lang: "en", page: "today", off: new Set(), why: "", sharing: new Set(), notice: "" };
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
function automations(): string {
  return `<h1>${esc(t("automations"))}</h1><p class="note">${esc(t("automations_intro"))}</p><ul class="autos">${DATA.automations.map((a) => { const on = !S.off.has(a.id) && a.default === "on";
    return `<li><div><strong>${esc(t(`auto_${key(a.id)}`))}</strong><span class="lvl">${esc(t(`level_${a.level}`))}${a.assist ? ` · ${esc(t("assist_suggestion"))}` : ""}</span></div><button class="switch${on ? " on" : ""}" role="switch" aria-checked="${on}" data-act="toggle:${a.id}">${esc(t(on ? "on" : "off"))}</button></li>`; }).join("")}</ul>
    <h2>${esc(t("automation_history"))}</h2><ul class="rows">${HISTORY.filter(([id]) => !S.off.has(id)).map(([id, min]) => `<li><span>${esc(t(`auto_${key(id)}`))}</span><span>${esc(t("ran_at", { when: C.clock(now - min * 60000) }))}</span><button class="link" data-act="why:${id}">${esc(t("why_happened"))}</button>${S.why === id ? `<p class="why">${esc(t(`why_${key(id)}`))}</p>` : ""}</li>`).join("")}</ul>`;
}
function sharing(): string {
  const sup = [["s1", "supplier_1"], ["s2", "supplier_2"]] as const;
  return `<h1>${esc(t("data_sharing"))}</h1><p class="note">${esc(t("data_sharing_body"))}</p><ul class="rows">${sup.map(([id, w]) => `<li><span>${esc(t(w))}</span>${S.sharing.has(id) ? `${chip("confirmed")}<button class="secondary" data-act="unshare:${id}">${esc(t("stop_sharing"))}</button>` : `<button class="primary" data-act="share:${id}">${esc(t("share"))}</button>`}</li>`).join("")}</ul><p>${esc(t("sharing_with", { n: S.sharing.size }))}</p>`;
}
function page(): string { return { today, sales, devices, staff, commissions, automations, sharing }[S.page](); }
function draw(): void {
  const el = $("#screen"); el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W);
  const label: Record<Page, string> = { today: "home", sales: "sales", devices: "devices", staff: "staff_shifts", commissions: "agent_commissions", automations: "automations", sharing: "data_sharing" };
  el.innerHTML = `<div class="bar"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span><span class="url">${icon("ui-lock")}app.lynkomni.com${esc(PATH[S.page])}</span></div>
    <div class="app"><nav class="side" aria-label="LynkOmni">${brandMark(DATA.brand.places, "side-menu", S.dark, "logo", SIDE_W)}${PAGES.map((p) => `<button data-act="go:${p}" ${S.page === p ? 'aria-current="page"' : ""}>${esc(t(label[p]))}</button>`).join("")}</nav><main class="main">${page()}${appMainFooter(W, C, DATA)}</main></div>`;
}
function act(a: string): void {
  const [k = "", v = ""] = a.split(":");
  if (k === "go") { S.page = PAGES.includes(v as Page) ? (v as Page) : "today"; S.why = ""; S.notice = ""; }
  if (k === "newsale") S.notice = t("needs_registered_device");
  if (k === "toggle") { const on = !S.off.has(v); if (on) S.off.add(v); else S.off.delete(v); }
  if (k === "why") S.why = S.why === v ? "" : v;
  if (k === "share") { S.sharing.add(v); LOG.emit("DataSharingConsentGiven", { supplier: v, consent: "LOCNS-…" }, "server"); }
  if (k === "unshare") { S.sharing.delete(v); LOG.emit("DataSharingConsentWithdrawn", { supplier: v }, "server"); }
  if (k === "revoke") LOG.emit("DeviceRevoked", { device_id: newId(), reason: "staff_left" }, "server");
  draw();
}
function panel(): void {
  $("#panel").innerHTML = panelHtml(["plan", "country", "dark", "lang"], S, W, C, { tiers: TIERS });
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), [...PAGES, "why", "new-sale"], (k) => { if (k === "why") { S.page = "automations"; S.why = "cash-difference-flag"; } else if (k === "new-sale") { S.page = "today"; S.notice = t("needs_registered_device"); } else { S.page = k as Page; S.why = ""; S.notice = ""; } draw(); });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? ""; panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (b) act(b.dataset["act"] ?? ""); });
  $("#panel").addEventListener("change", (e) => { if (panelChange(e.target as HTMLSelectElement, S, DATA, { tiers: TIERS })) panel(); draw(); });
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 1180);
}
main();
