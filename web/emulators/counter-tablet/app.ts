/** LynkPOS counter tablet (the agreed counter till, blueprint 42 I and 44 I N1): a tablet on a stand with a customer-facing
 *  display, receipt printer, scanner, cash drawer and card tap area. Runs the real rules from ts/src (sale, payments, stock,
 *  tabs by business type, tier limits, restaurant mode, shifts and cash counts, the web rule) on sandbox partners. Nothing
 *  about a country or a maker lives here: the country comes from its pack, the hardware is an original LynkOmni design. */
import { Cart, PosError, change, paymentPayload, paymentState, qtyText, quickCash, receiptLines, salePayload } from "../../../ts/src/pos.js";
import type { PaymentMethod, PaymentPayload, PaymentStatus, Product, SalePayload, UserState } from "../../../ts/src/pos.js";
import { afterSale, daySummary, insight } from "../../../ts/src/merchant.js";
import type { DaySale, Levels } from "../../../ts/src/merchant.js";
import { BUSINESS_TYPES, HANDHELD_TILES, IDLE_LOCK_S, TABS, mayShowConfirmed, practiceLabel, receiptChannels, secondCurrency, webRule } from "../../../ts/src/business.js";
import type { BusinessType, PosEntitlement } from "../../../ts/src/business.js";
import { chargedWhen, deliveryEntitlement, groupOutcome, kitchenOutput, mayAddRider, mayOpenGroup, mayOpenTable, mayRequestPartnerDelivery, pickQuotes, restaurantLimits, splitNeedsAtLeast } from "../../../ts/src/restaurant.js";
import { SETUP_STEPS, nextSetupStep, parseVoice } from "../../../ts/src/business.js";
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, newId, pick, plain, reducedMotion, appShortFooter } from "../../../ts/src/emulator.js";
import type { Build } from "../../../ts/src/emulator.js";
import { brandMark } from "../../../ts/src/brand.js";
import { designedState, panelShell, sampleAccount } from "../../../ts/src/deviceshell.js";
import type { Entry } from "../../../ts/src/shell.js";
import { DeviceMode } from "../../../ts/src/devicemode.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";

declare const DATA: Build & { entitlements: Record<string, PosEntitlement>; fx: Record<string, number> };
type Tab = "home" | "sell" | "stock" | "chats" | "business" | "tables" | "kitchen" | "invoices" | "customers" | "services" | "float";
type View = "main" | "pay" | "cash" | "waiting" | "done" | "shift" | "table" | "dayclose" | "locked" | "staff" | "deliver" | "group" | "setup" | "credit" | "voice";
const SUBVIEWS: View[] = ["shift", "dayclose", "pay", "main", "staff", "deliver", "group", "setup", "credit", "voice"];
const TIERS = ["free", "plus", "pro", "max"] as const;
interface Sale extends DaySale { at: number; tendered?: number; tableId?: string; tip?: number }
interface Table { id: string; label: string; covers: number; open: boolean; orders: { id: string; lines: { lineNo: number; name: string; qty: number; ready: boolean }[] }[]; sales: string[] }
interface Item extends Product { cost: number; barcode: string; level: number }

const S = {
  lang: "en", country: "", dark: false, online: true, fail: false, realUser: false, practice: false, tier: "plus" as (typeof TIERS)[number], type: "shop" as BusinessType,
  tab: "sell" as Tab, view: "locked" as View, pin: "", unlocked: false, idleTicks: 0, cat: "all", cart: new Cart(), current: null as Sale | null, sales: [] as Sale[], levels: {} as Levels,
  method: "cash" as PaymentMethod, tendered: 0, flash: "", shift: null as { id: string; float: number; cash: number } | null, counted: "", tables: [] as Table[], table: "", receiptNo: 0, ticks: 0,
  cdisplay: "welcome" as "welcome" | "basket" | "pay" | "thanks", registered: true, lastInput: Date.now(), tipPct: 0,
  clocked: {} as Record<string, number>, deliveries: [] as { id: string; partner: string; price: number; state: UserState }[], prefer: "cheapest" as "cheapest" | "fastest", riders: 0,
  group: { total: 6_000_000, target: 10_000_000, joined: false, outcome: "" as "" | "reached" | "failed" }, setup: new Set<string>(), credit: [{ name: "Aline", owes: 4500, due: 3 }, { name: "Eric", owes: 12000, due: -2 }] as { name: string; owes: number; due: number }[], heard: "",
};
const DPARTNERS = [{ partnerId: "da", price: 1500, etaS: 2700 }, { partnerId: "db", price: 2200, etaS: 1500 }];
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const icon = (id: string, cls = "ic"): string => `<span class="${cls}" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); });
const ent = (): PosEntitlement => DATA.entitlements[S.tier] ?? {};
const P = (n: number): number => n * 1000;

const CATALOG: Item[] = ([["p_rice", 1500, 1150, "food", 24, "6001"], ["p_sugar", 1400, 1100, "food", 6, "6002"], ["p_beans", 1200, 900, "food", 30, "6003"], ["p_oil", 3200, 2600, "food", 2, "6004"],
  ["p_bread", 1000, 700, "food", 12, "6005"], ["p_eggs", 4500, 3800, "food", 1, "6006"], ["p_milk", 600, 420, "drinks", 20, "6007"], ["p_water", 700, 450, "drinks", 36, "6008"],
  ["p_soda", 500, 330, "drinks", 40, "6009"], ["p_soup", 2500, 1200, "food", 50, "6010"], ["p_chicken", 6000, 3500, "food", 50, "6011"], ["p_juice", 1500, 600, "drinks", 50, "6012"]] as const)
  .map(([key, price, cost, category, level, barcode]) => ({ id: newId(), name: key, price, cost, category, barcode, level: P(level) }));
S.levels = Object.fromEntries(CATALOG.map((p) => [p.id, p.level]));
const COSTS = Object.fromEntries(CATALOG.map((p) => [p.id, p.cost]));
/** The app address of each place (catalog/addresses.v1.json app_paths), shown in the address line and used by search and help. */
const TAB_PATH: Record<Tab, string> = { home: "/", sell: "/sell", stock: "/stock", chats: "/chats", business: "/business", tables: "/sell/tables", kitchen: "/sell/kitchen", invoices: "/invoicing", customers: "/crm", services: "/services", float: "/float" };
const VIEW_PATH: Partial<Record<View, string>> = { pay: "/sell/payment", cash: "/sell/payment", waiting: "/sell/payment", done: "/sell/receipt", shift: "/sell/shifts", table: "/sell/tables", dayclose: "/business/daily-close", staff: "/business/team", deliver: "/deliveries", group: "/stock/marketplace/buy-together", setup: "/business/settings", credit: "/crm", voice: "/sell" };
const named = (p: Product): Product => ({ ...p, name: t(p.name) });
const money = (n: number): string => C.money(n);
const toast = (m: string): void => { S.flash = m; draw(); window.setTimeout(() => { S.flash = ""; draw(); }, 1500); };

// ---- the sandbox cloud: stock flags and provider answers
function onAccepted(e: { type: string; payload: unknown; n: number }): void {
  if (e.type === "SaleRecorded") for (const l of (e.payload as SalePayload).lines) if ((S.levels[l.product_id] ?? 0) < 0) LOG.emit("NegativeStockFlagged", { product_id: l.product_id, projected_milli: S.levels[l.product_id], as_of_cursor: e.n }, "server");
}
const asking = new Set<string>();
function askProvider(s: Sale, p: PaymentPayload): void {
  asking.add(p.payment_id);
  window.setTimeout(() => {
    asking.delete(p.payment_id); if (!S.online) return;
    const to: PaymentStatus = S.fail ? "failed" : "confirmed";
    LOG.emit("PaymentStatusChanged", { payment_id: p.payment_id, from_status: p.status, to_status: to, source: "provider_callback", provider_reference: `SBX-${p.payment_id.slice(-8).toUpperCase()}` }, "server");
    p.status = to; if (S.current === s && S.view === "waiting") { S.view = to === "confirmed" ? "done" : "pay"; if (to === "confirmed") S.cdisplay = "thanks"; }
    draw();
  }, reducedMotion() ? 300 : 2200);
}
function tick(): void {
  S.ticks += 1;
  if (S.unlocked && Date.now() - S.lastInput > IDLE_LOCK_S * 1000 && !W.isTest()) { S.unlocked = false; S.view = "locked"; S.pin = ""; LOG.emit("DeviceLocked", { device_id: "tablet", after_s: IDLE_LOCK_S }, "device", "accepted"); draw(); }
  if (S.practice) return;                                   // a practice device never syncs
  const changed = LOG.tick(S.online, false, S.ticks, onAccepted);
  if (S.online) for (const s of S.sales) for (const p of s.payments) if (p.status === "pending_confirmation" && !asking.has(p.payment_id)) askProvider(s, p);
  if (changed) draw();
}

// ---- selling
function recordSale(): Sale {
  if (S.current) return S.current;
  S.receiptNo += 1;
  const cart = new Cart(); for (const l of S.cart.lines()) cart.add(named(l.product), l.qtyMilli);
  const sale = salePayload(cart, newId(), `CT-${S.receiptNo}`, C.pack().currency);
  LOG.emit("SaleRecorded", sale); LOG.emit("ReceiptIssued", { receipt_id: newId(), sale_id: sale.sale_id, receipt_number_local: sale.receipt_number_local, copy_number: 1, validity: "provisional" });
  S.levels = afterSale(S.levels, sale);
  const s: Sale = { sale, payments: [], voided: false, at: Date.now(), tableId: S.table || undefined };
  S.sales.unshift(s); S.current = s; return s;
}
function pay(method: PaymentMethod, tendered?: number): void {
  const s = recordSale(); const p = paymentPayload(newId(), s.sale.sale_id, method, s.sale.total);
  s.payments.push(p); LOG.emit("PaymentRecorded", p);
  if (method === "cash") { s.tendered = tendered; if (S.shift) S.shift.cash += s.sale.total; S.view = "done"; S.cdisplay = "thanks"; openDrawer(); } else { S.view = "waiting"; S.cdisplay = "pay"; }
  if (S.tipPct && restaurantLimits(ent()).tips) { const tip = Math.round(s.sale.total * S.tipPct / 100); s.tip = tip; LOG.emit("TipRecorded", { tip_id: newId(), sale_id: s.sale.sale_id, amount: tip, currency: C.pack().currency }); }
  draw();
}
function newSale(): void { S.cart.clear(); S.current = null; S.tendered = 0; S.view = "main"; S.tab = S.type === "restaurant" ? "tables" : "sell"; S.cdisplay = "welcome"; S.tipPct = 0; draw(); }
const last = (): PaymentPayload | undefined => S.current?.payments[S.current.payments.length - 1];
function openDrawer(): void { const d = $("#drawer"); d.classList.add("open"); $("#drawerStatus").textContent = t("cash_in_drawer"); window.setTimeout(() => { d.classList.remove("open"); $("#drawerStatus").textContent = ""; }, reducedMotion() ? 200 : 1800); }
function printReceipt(): void {
  const s = S.current; if (!s) return;
  const words = Object.fromEntries(["provisional", "receipt", "total", "tendered", "change", "thanks", "not_tax", "method_cash", "method_card", "method_mobile_money", "method_bank_transfer", "method_credit", "method_other", "state_pending_confirmation", "state_confirmed", "state_failed", "state_credit_open"].map((k) => [k, k.startsWith("state_") ? t(`st_${k.slice(6) === "pending_confirmation" ? "sent" : k.slice(6) === "credit_open" ? "queued" : k.slice(6)}`) : t(k)]));
  const lines = receiptLines({ shop: t("sample_shop") + (S.practice ? ` (${t("practice")})` : ""), sale: s.sale, payments: s.payments, tendered: s.tendered, when: `${C.date(s.at)} ${C.clock(s.at)}`, money, words, width: 32 });
  $("#paper").innerHTML = `<div class="rhead">${DATA.brand.receipt}</div><pre class="rtext">${esc(lines.join("\n"))}</pre>`;
  $("#paperWrap").hidden = false; $("#paperWrap").classList.remove("torn"); $("#printerStatus").textContent = t("print");
  window.setTimeout(() => { $("#printerStatus").textContent = ""; }, 1500);
}
function scan(): void {
  const p = CATALOG[Math.floor(Math.random() * CATALOG.length)]; if (!p) return;
  if (S.view !== "main" || S.tab !== "sell") { S.tab = "sell"; S.view = "main"; }
  S.cart.add(p); S.cdisplay = "basket"; toast(t("scanned", { name: t(p.name) }));
}

// ---- screens
const total = (): number => S.cart.total();
const where = (): { id: string; path: string } => !S.unlocked ? { id: "locked", path: "/" } : S.view !== "main" ? { id: S.view, path: VIEW_PATH[S.view] ?? "/" } : { id: S.tab, path: TAB_PATH[S.tab] };
const DSH = panelShell({
  st: S, t, icon: (id) => icon(id), clock: (ms) => C.clock(ms),
  native: () => (DATA.i18n[S.lang]?.native ?? S.lang), region: () => (C.pack().sample ? t("sample_country") : C.pack().name), currency: () => C.pack().currency,
  pending: () => LOG.pending().count, lastSync: () => LOG.events.find((e) => e.sync === "accepted")?.at ?? null,
  screen: () => ({ ...where(), title: document.querySelector("#screen .body h2")?.textContent?.trim() || t(S.unlocked ? (S.view === "main" ? S.tab : "sample_shop") : "enter_pin") }),
  entries: (): Entry[] => !S.unlocked ? [] : [
    { id: "new", kind: "action", title: t("new_sale"), act: "new" }, { id: "count", kind: "action", title: t("count_cash"), act: "go:shift" }, { id: "close", kind: "action", title: t("day_close"), act: "go:dayclose" },
    ...TABS[S.type].map((k): Entry => ({ id: `tab-${k}`, kind: "action", title: t(k), act: `tab:${k}` })),
    ...CATALOG.map((p): Entry => ({ id: p.id, kind: "product", title: t(p.name), subtitle: money(p.price), act: `add:${p.id}` })),
    ...S.credit.map((c, i): Entry => ({ id: `c${i}`, kind: "customer", title: c.name, subtitle: money(c.owes), act: "go:credit" })),
    ...S.sales.slice(0, 5).map((x): Entry => ({ id: x.sale.sale_id, kind: "order", title: x.sale.receipt_number_local, subtitle: money(x.sale.total), act: "tab:home" })),
  ],
  account: () => sampleAccount(t, "cashier", ["cashier", "manager", "owner"], t("sample_shop"), S.dark ? "dark" : "light", DATA.i18n[S.lang]?.native ?? S.lang, C.pack().sample ? t("sample_country") : C.pack().name),
  run: (a) => { if (a === "role:cashier" || a.startsWith("role:") || a.startsWith("business:")) return; act(a); }, redraw: () => { syncPanel(); draw(); }, firstRun: true,
});
function syncPanel(): void { ($("#cLang") as HTMLSelectElement).value = S.lang; ($("#cDark") as HTMLInputElement).checked = S.dark; ($("#cOnline") as HTMLInputElement).checked = S.online; }
function tabBar(): string {
  const tabs = TABS[S.type];
  const ic: Record<string, string> = { home: "ui-home", sell: "ui-cart", stock: "product-stock", chats: "product-chat", business: "ui-grid", tables: "ui-grid", kitchen: "ui-bolt", invoices: "ui-doc", customers: "ui-user", services: "ui-grid", float: "ui-float" };
  return `<nav class="tabbar" aria-label="LynkOmni">${tabs.map((k) => `<button data-act="tab:${k}" ${S.tab === k ? 'aria-current="page"' : ""}>${icon(ic[k] ?? "ui-grid")}<span>${esc(t(k))}</span></button>`).join("")}</nav>`;
}
function top(title: string): string {
  return `<header class="top">${brandMark(DATA.brand.places, "app-top-bar", S.dark, "brandmark")}<h1>${esc(title)}</h1>${S.practice ? `<span class="practice">${esc(t("practice"))}</span>` : ""}
    ${S.unlocked ? DSH.bar() : DSH.bar({ search: false, account: false })}</header>`;
}
function sellScreen(): string {
  const cats = ["all", "food", "drinks", "home"];
  const items = CATALOG.filter((p) => S.cat === "all" || p.category === S.cat);
  const cur = C.pack().currency, second = total() === 0 ? null : secondCurrency(total(), cur, cur === "USD" ? "EUR" : "USD", (m, a, b) => Math.round(m * ((DATA.fx[b] ?? 1) / (DATA.fx[a] ?? 1))));
  return `<div class="sell"><div class="grid-side"><div class="cats">${cats.map((c) => `<button class="pill${S.cat === c ? " on" : ""}" data-act="cat:${c}">${esc(t(`cat_${c}`))}</button>`).join("")}</div>
    <div class="pgrid">${items.map((p) => `<button class="prod${(S.levels[p.id] ?? 0) <= 0 ? " out" : ""}" data-act="add:${p.id}"><span class="nm">${esc(t(p.name))}</span><span class="pr">${esc(money(p.price))}</span><span class="lv">${esc(t("in_stock", { n: qtyText(S.levels[p.id] ?? 0) }))}</span></button>`).join("")}</div></div>
    <div class="basket"><h2>${esc(t("basket"))}</h2><ul>${S.cart.lines().map((l) => `<li><span class="nm">${esc(t(l.product.name))}</span><span class="q"><button data-act="minus:${l.product.id}" aria-label="${esc(t("cancel"))}">${icon("ui-minus")}</button>${qtyText(l.qtyMilli)}<button data-act="add:${l.product.id}" aria-label="${esc(t("next"))}">${icon("ui-plus")}</button></span><span class="pr">${esc(money(l.product.price * l.qtyMilli / 1000))}</span></li>`).join("") || `<li class="empty">${esc(t("new_sale"))}</li>`}</ul>
    <div class="tot"><span>${esc(t("total"))}</span><strong>${esc(money(total()))}</strong></div>${second ? `<p class="second">${esc(t("second_currency", { amount: C.money(second.amount, second.currency), currency: cur }))}</p>` : ""}
    <button class="link" data-act="voice">${icon("ui-mic")} ${esc(t("voice"))}</button><button class="primary" data-act="charge" ${S.cart.lines().length ? "" : "disabled"}>${esc(t("charge"))}</button></div></div>`;
}
function payScreen(): string {
  const methods: PaymentMethod[] = ["cash", "card", "mobile_money", "bank_transfer"];
  const l = last(); const failed = l && l.status === "failed";
  return `<div class="paybox"><h2>${esc(money(total()))}</h2>${failed ? `<p class="warn">${esc(t("failed_try_again"))}</p>` : ""}<p class="note">${esc(t("not_proof"))}</p>
    <div class="methods">${methods.map((m) => { const ok = C.methodOk(m, S.realUser); return `<button class="method" data-act="method:${m}" ${ok ? "" : 'aria-disabled="true"'}>${icon(m === "cash" ? "ui-pay-wallet" : m === "card" ? "ui-pay-card" : m === "mobile_money" ? "ui-pay-mobile-money" : "ui-pay-bank")}<span>${esc(t(m))}</span>${ok ? "" : `<small>${esc(t("coming_soon"))}</small>`}</button>`; }).join("")}</div>
    ${restaurantLimits(ent()).tips ? `<div class="tips"><span>${esc(t("tip"))}</span>${[0, 5, 10, 15].map((p) => `<button class="pill${S.tipPct === p ? " on" : ""}" data-act="tip:${p}">${p}%</button>`).join("")}<small>${esc(t("tips_belong"))}</small></div>` : ""}
    <button class="link" data-act="back">${esc(t("back"))}</button></div>`;
}
function cashScreen(): string {
  const tot = total();
  return `<div class="paybox"><h2>${esc(t("tendered"))}</h2><div class="quick">${quickCash(tot, [500, 1000, 2000, 5000, 10000]).map((n) => `<button class="pill${S.tendered === n ? " on" : ""}" data-act="tender:${n}">${esc(money(n))}</button>`).join("")}</div>
    <p class="big">${esc(t("change"))}: <strong>${esc(S.tendered >= tot ? money(change(tot, S.tendered)) : "—")}</strong></p><button class="primary" data-act="paycash" ${S.tendered >= tot ? "" : "disabled"}>${esc(t("confirm"))}</button><button class="link" data-act="go:pay">${esc(t("back"))}</button></div>`;
}
function waitingScreen(): string {
  const l = last(); const st = l ? paymentState(l.status, S.online) : "sent";
  return `<div class="paybox center"><p class="big">${esc(money(total()))}</p><p>${esc(t("waiting_partner"))}</p>${chip(st === "cash" || st === "credit" ? "sent" : st)}<p class="note">${esc(t("not_proof"))}</p>${S.method === "card" ? `<p class="note">${esc(t("card"))}: ${esc(t("scan"))}</p>` : ""}<button class="link" data-act="back">${esc(t("cancel"))}</button></div>`;
}
function doneScreen(): string {
  const s = S.current; const l = last(); const confirmed = l ? mayShowConfirmed(l.status) || l.status === "cash_received" : false;
  const channels = receiptChannels(ent());
  return `<div class="paybox center"><span class="bigcheck">${icon("ui-check")}</span><h2>${esc(confirmed ? t("done") : t("st_sent"))}</h2><p class="big">${esc(money(s?.sale.total ?? 0))}</p>${s?.tendered !== undefined ? `<p>${esc(t("change"))}: ${esc(money(change(s.sale.total, s.tendered)))}</p>` : ""}
    <div class="row">${channels.includes("print") ? `<button data-act="print">${icon("ui-receipt")}${esc(t("print"))}</button>` : ""}${channels.includes("qr") ? `<button data-act="qr">${icon("ui-qr")}${esc(t("show_qr"))}</button>` : ""}${channels.includes("message") ? `<button data-act="msg">${icon("ui-bell")}${esc(t("send_receipt"))}</button>` : ""}</div>
    <div class="row"><button class="primary" data-act="new">${esc(t("new_sale"))}</button><button data-act="go:deliver">${icon("ui-chevron-right")}${esc(t("deliver"))}</button></div></div>`;
}
function tablesScreen(): string {
  const lim = restaurantLimits(ent()); const open = S.tables.filter((x) => x.open).length;
  return `<div class="tables"><div class="thead"><h2>${esc(t("tables"))}</h2><button class="primary small" data-act="opentable" ${mayOpenTable(lim, open) ? "" : "disabled"}>${esc(t("open_table"))}</button></div>
    <div class="tgrid">${S.tables.map((x) => `<button class="tbl${x.open ? " open" : ""}" data-act="table:${x.id}"><strong>${esc(t("table", { label: x.label }))}</strong><span>${esc(t("covers"))}: ${x.covers}</span><span>${x.orders.flatMap((o) => o.lines).filter((l) => !l.ready).length} ${esc(t("kitchen"))}</span></button>`).join("") || `<p class="empty">${esc(t("open_table"))}</p>`}</div>
    <p class="note">${esc(lim.tables === null ? "" : `${open}/${lim.tables}`)} ${esc(kitchenOutput(lim) === "screen" ? t("kitchen") : t("printed_tickets"))}${lim.tableQrOrdering ? ` · ${esc(t("order_qr"))}` : ""}</p></div>`;
}
function tableScreen(): string {
  const x = S.tables.find((v) => v.id === S.table); if (!x) return tablesScreen();
  const allReady = x.orders.every((o) => o.lines.every((l) => l.ready));
  return `<div class="tables"><div class="thead"><button class="link" data-act="tab:tables">${esc(t("back"))}</button><h2>${esc(t("table", { label: x.label }))}</h2></div>
    <div class="pgrid small">${CATALOG.filter((p) => p.category !== "home").map((p) => `<button class="prod" data-act="add:${p.id}"><span class="nm">${esc(t(p.name))}</span><span class="pr">${esc(money(p.price))}</span></button>`).join("")}</div>
    <div class="row"><button data-act="kitchen" ${S.cart.lines().length ? "" : "disabled"}>${esc(t("send_to_kitchen"))}</button><button data-act="charge" ${S.cart.lines().length ? "" : "disabled"}>${esc(t("charge"))}</button>${restaurantLimits(ent()).splitBills ? `<button data-act="split" ${S.cart.lines().length >= splitNeedsAtLeast ? "" : "disabled"}>${esc(t("split_bill"))}</button>` : ""}<button data-act="closetable" ${allReady && !S.cart.lines().length ? "" : "disabled"} title="${esc(allReady ? "" : t("kitchen_items_open"))}">${esc(t("close_table"))}</button></div>
    <ul class="orders">${x.orders.map((o) => o.lines.map((l) => `<li>${esc(l.name)} × ${l.qty} ${l.ready ? chip("confirmed") : `<button class="pill" data-act="ready:${o.id}:${l.lineNo}">${esc(t("ready"))}</button>`}</li>`).join("")).join("")}</ul>
    <p class="note">${esc(t("basket"))}: ${S.cart.lines().map((l) => `${t(l.product.name)} × ${qtyText(l.qtyMilli)}`).join(", ") || "—"}</p></div>`;
}
function kitchenScreen(): string {
  const q = S.tables.flatMap((x) => x.orders.flatMap((o) => o.lines.filter((l) => !l.ready).map((l) => ({ table: x.label, o: o.id, l }))));
  return `<div class="kitchen"><h2>${esc(t("kitchen_queue"))}</h2>${kitchenOutput(restaurantLimits(ent())) === "screen" ? "" : `<p class="note">${esc(t("printed_tickets"))}</p>`}<ul>${q.map((e) => `<li><strong>${esc(t("table", { label: e.table }))}</strong> ${esc(e.l.name)} × ${e.l.qty} <button class="pill" data-act="ready:${e.o}:${e.l.lineNo}">${esc(t("ready"))}</button></li>`).join("") || `<li class="empty">${esc(t("all_ready"))}</li>`}</ul></div>`;
}
function shiftScreen(): string {
  const sh = S.shift; const counted = Number(S.counted || 0);
  return `<div class="paybox"><h2>${esc(t("shift"))}</h2>${sh ? `<p>${esc(t("expected_cash"))}: <strong>${esc(money(sh.cash))}</strong></p><label>${esc(t("counted_cash"))} <input inputmode="numeric" id="counted" value="${esc(S.counted)}" data-filter="counted"></label>
    <p>${esc(t("difference"))}: ${esc(money(counted - sh.cash))}</p><div class="row"><button data-act="countcash">${esc(t("count_cash"))}</button><button class="primary" data-act="closeshift">${esc(t("close_shift"))}</button></div><p class="note">${esc(t("difference_flagged"))}</p>`
    : `<p>${esc(t("float_amount"))}</p><div class="quick">${[0, 2000, 5000, 10000].map((n) => `<button class="pill" data-act="openshift:${n}">${esc(money(n))}</button>`).join("")}</div>`}<button class="link" data-act="tab:business">${esc(t("back"))}</button></div>`;
}
function homeScreen(): string {
  const sm = daySummary(S.sales, COSTS); const best = insight(S.sales);
  return `<div class="home"><div class="cards"><div class="card"><span>${esc(t("today_sales"))}</span><strong>${esc(money(sm.total))}</strong><small>${sm.count}</small></div><div class="card"><span>${esc(t("today_profit"))}</span><strong>${esc(money(sm.profit))}</strong></div>
    <div class="card"><span>${esc(t("cash_in_drawer"))}</span><strong>${esc(money(S.shift ? S.shift.cash : sm.cash))}</strong></div><div class="card"><span>${esc(t("insight"))}</span><strong>${esc(best ? t("best_seller", { name: best.name }) : t("no_sales_yet"))}</strong></div></div>
    <div class="row"><button class="primary" data-act="new">${esc(t("new_sale"))}</button><button data-act="go:shift">${esc(t(S.shift ? "count_cash" : "open_shift"))}</button><button data-act="go:dayclose">${esc(t("day_close"))}</button></div><p class="note">${esc(t("setup_done_in"))}</p>${S.sales.length ? "" : designedState("empty", t, DATA.statePictures, S.dark, { label: t("new_sale"), act: "new" })}</div>`;
}
function dayCloseScreen(): string {
  const sm = daySummary(S.sales, COSTS); const low = CATALOG.filter((p) => (S.levels[p.id] ?? 0) <= P(5)).map((p) => t(p.name));
  return `<div class="paybox"><h2>${esc(t("day_close"))}</h2><p>${esc(t("day_close_body", { sales: sm.count, total: money(sm.total), cash: money(sm.cash), confirmed: money(sm.confirmed), waiting: money(sm.waiting) }))}</p>
    <p>${esc(t("low_stock"))}: ${esc(low.join(", ") || "—")}</p><p class="note">${esc(sm.failed ? t("st_failed") + ": " + money(sm.failed) : t("nothing_unusual"))}</p><button class="link" data-act="tab:home">${esc(t("back"))}</button></div>`;
}
function stockScreen(): string {
  return `<div class="stocklist"><h2>${esc(t("stock"))}</h2><ul>${CATALOG.map((p) => { const lv = S.levels[p.id] ?? 0; return `<li><span class="nm">${esc(t(p.name))}</span><span>${qtyText(lv)}</span>${lv < 0 ? `<span class="warn">${esc(t("negative_stock"))}</span>` : lv <= P(5) ? `<span class="low">${esc(t("low_stock"))}</span>` : ""}<button class="pill" data-act="count:${p.id}">${esc(t("count"))}</button></li>`; }).join("")}</ul></div>`;
}
function businessScreen(): string {
  const items: [string, string][] = [["shift", "shift"], ["dayclose", "day_close"], ["staff", "staff"], ["credit", "credit_book"], ["deliver", "deliveries"], ["group", "buy_together"], ["setup", "settings"], ["devices", "devices"], ["reports", "reports"], ["automations", "automations"], ["academy", "academy"]];
  return `<div class="biz"><h2>${esc(t("business"))}</h2><ul class="menu">${items.map(([k, w]) => `<li><button data-act="go:${k}">${esc(t(w))}${icon("ui-chevron-right")}</button></li>`).join("")}</ul>
    <p class="note">${esc(t("needs_registered_device"))} ${esc(webRule("sell", S.registered) === "ok" ? t("device_registered") : t("register_device"))}</p><p class="note">${esc(t("academy_hint"))}</p></div>`;
}
function staffScreen(): string {
  const people = ["sample_staff_1", "sample_staff_2"];
  return `<div class="paybox"><h2>${esc(t("staff"))}</h2><ul class="orders">${people.map((p) => { const at = S.clocked[p]; return `<li><span>${esc(t(p))}</span>${at ? `<span class="note">${esc(t("clocked_in", { name: t(p), when: C.clock(at) }))}</span><button class="pill" data-act="clockout:${p}">${esc(t("clock_out"))}</button>` : `<button class="pill" data-act="clockin:${p}">${esc(t("clock_in"))}</button>`}</li>`; }).join("")}</ul><button class="link" data-act="tab:business">${esc(t("back"))}</button></div>`;
}
function deliverScreen(): string {
  const e = deliveryEntitlement(ent(), ent()), quotes = pickQuotes(DPARTNERS, e.routing, S.prefer), used = S.deliveries.length;
  return `<div class="paybox"><h2>${esc(t("deliver"))}</h2>${S.online ? "" : `<p class="warn">${esc(t("online_only"))}</p>`}
    ${e.routing ? `<div class="row"><button class="pill${S.prefer === "cheapest" ? " on" : ""}" data-act="prefer:cheapest">${esc(t("cheapest"))}</button><button class="pill${S.prefer === "fastest" ? " on" : ""}" data-act="prefer:fastest">${esc(t("fastest"))}</button></div>` : ""}
    <ul class="orders">${quotes.map((q) => `<li><span>${esc(t("partner_price", { partner: t(q.partnerId === "da" ? "partner_a" : "partner_b"), price: money(q.price), min: Math.round(q.etaS / 60) }))}</span><button class="pill" data-act="book:${q.partnerId}" ${S.online && mayRequestPartnerDelivery(used, e) ? "" : "disabled"}>${esc(t("book_delivery"))}</button></li>`).join("")}
      <li><span>${esc(t("own_rider"))} (${S.riders})</span><button class="pill" data-act="book:own" ${S.online && S.riders > 0 ? "" : "disabled"}>${esc(t("book_delivery"))}</button><button class="pill" data-act="addrider" ${mayAddRider(S.riders, e) ? "" : "disabled"}>+</button></li></ul>
    <ul class="orders">${S.deliveries.map((d) => `<li><span>${esc(d.partner)}</span><span>${esc(money(d.price))}</span>${chip(d.state)}</li>`).join("")}</ul><p class="note">${esc(t("proof_photo"))}</p><button class="link" data-act="tab:business">${esc(t("back"))}</button></div>`;
}
function groupScreen(): string {
  const g = S.group;
  return `<div class="paybox"><h2>${esc(t("buy_together"))}</h2><p>${esc(t("group_order", { total: money(g.total), target: money(g.target), when: C.date(Date.now() + 2 * 86400000) }))}</p>
    ${g.outcome ? `<p class="${g.outcome === "reached" ? "note" : "warn"}">${esc(t(g.outcome === "reached" ? "group_reached" : "group_failed"))}</p>` : g.joined ? `<p class="note">${esc(t("joined"))}</p>` : `<button class="primary" data-act="joingroup">${esc(t("join_group"))}</button>`}
    <div class="row"><button class="pill" data-act="closegroup:short">${esc(t("group_failed"))}</button><button class="pill" data-act="closegroup:reach">${esc(t("group_reached"))}</button></div>
    ${mayOpenGroup(S.tier) ? "" : `<p class="note">${esc(t("start_group_pro"))}</p>`}<button class="link" data-act="tab:business">${esc(t("back"))}</button></div>`;
}
function setupScreen(): string {
  const next = nextSetupStep(S.setup);
  return `<div class="paybox"><h2>${esc(t("settings"))}</h2><p class="note">${esc(t("setup_done_in"))}</p><ol class="orders">${SETUP_STEPS.map((st) => `<li><span>${esc(t(st === "locale_card" ? "locale_card" : st === "business_name" ? "name_business" : st === "business_type" ? "pick_type" : "first_product"))}</span>${S.setup.has(st) ? chip("confirmed") : st === next ? `<button class="pill" data-act="setup:${st}">${esc(t("next"))}</button>` : ""}</li>`).join("")}</ol>
    <button class="link" data-act="tab:business">${esc(t("back"))}</button></div>`;
}
function creditScreen(): string {
  return `<div class="paybox"><h2>${esc(t("credit_book"))}</h2><ul class="orders">${S.credit.map((c, i) => `<li><span>${esc(t("owes", { name: c.name, amount: money(c.owes) }))}</span><span class="note">${esc(t("due_on", { when: C.date(Date.now() + c.due * 86400000) }))}</span>
    <button class="pill" data-act="creditpay:${i}" ${c.owes ? "" : "disabled"}>${esc(t("record_payment"))}</button><button class="pill" data-act="remind:${i}" ${c.owes ? "" : "disabled"}>${esc(t("remind"))}</button></li>`).join("")}</ul>
    <button class="primary" data-act="sellcredit" ${S.cart.lines().length ? "" : "disabled"}>${esc(t("sell_on_credit"))}</button><button class="link" data-act="tab:business">${esc(t("back"))}</button></div>`;
}
function voiceScreen(): string {
  return `<div class="paybox center"><span class="bigcheck">${icon("ui-mic")}</span><h2>${esc(t("voice"))}</h2><p class="note">${esc(t("voice_hint"))}</p>${S.heard ? `<p>${esc(t("voice_heard", { text: S.heard }))}</p>` : ""}
    <div class="row"><button class="primary" data-act="listen">${icon("ui-mic")}${esc(t("voice"))}</button><button class="link" data-act="back">${esc(t("basket"))}</button></div></div>`;
}
function lockScreen(): string {
  return `<div class="lock">${brandMark(DATA.brand.places, "auth-onboarding", S.dark, "locklogo")}<h1>${esc(t("enter_pin"))}</h1><p class="note">${esc(S.idleTicks ? t("locked_idle") : "")}</p><div class="dots">${[0, 1, 2, 3].map((i) => `<i class="${S.pin.length > i ? "on" : ""}"></i>`).join("")}</div>
    <div class="soft">${[1, 2, 3, 4, 5, 6, 7, 8, 9].map((d) => `<button data-act="d${d}">${d}</button>`).join("")}<button data-act="clear" aria-label="${esc(t("cancel"))}">${icon("ui-arrow-left")}</button><button data-act="d0">0</button><button data-act="enter" aria-label="${esc(t("unlock"))}">${icon("ui-check")}</button></div><p class="hint">PIN 1234</p></div>`;
}
function page(): string {
  if (!S.unlocked) return lockScreen();
  switch (S.view) {
    case "pay": return payScreen(); case "cash": return cashScreen(); case "waiting": return waitingScreen(); case "done": return doneScreen();
    case "shift": return shiftScreen(); case "table": return tableScreen(); case "dayclose": return dayCloseScreen();
    case "staff": return staffScreen(); case "deliver": return deliverScreen(); case "group": return groupScreen(); case "setup": return setupScreen(); case "credit": return creditScreen(); case "voice": return voiceScreen();
    default: break;
  }
  switch (S.tab) {
    case "home": return homeScreen(); case "sell": return sellScreen(); case "stock": return stockScreen(); case "tables": return tablesScreen(); case "kitchen": return kitchenScreen();
    case "business": return businessScreen() + appShortFooter(C);   // the one-line short footer inside apps (26 C)
    default: return `<div class="paybox"><h2>${esc(t(S.tab))}</h2><p class="note">${esc(t("sandbox_note"))}</p></div>`;
  }
}
function customerDisplay(): string {
  const cur = C.pack().currency;
  if (S.cdisplay === "welcome" || !S.unlocked || (S.cdisplay === "basket" && !S.cart.lines().length)) return `<div class="cwelcome">${brandMark(DATA.brand.places, "customer-welcome", S.dark, "cmark", 118)}<h2>${esc(t("welcome"))}</h2><p>${esc(t("sample_shop"))}</p></div>`;
  if (S.cdisplay === "thanks") return `<div class="cwelcome"><h2>${esc(t("thank_you_visit"))}</h2><p>${esc(money(S.current?.sale.total ?? 0))}</p></div>`;
  const second = secondCurrency(total(), cur, cur === "USD" ? "EUR" : "USD", (m, a, b) => Math.round(m * ((DATA.fx[b] ?? 1) / (DATA.fx[a] ?? 1))));
  return `<div class="cbasket"><ul>${S.cart.lines().map((l) => `<li><span>${esc(t(l.product.name))} × ${qtyText(l.qtyMilli)}</span><span>${esc(money(l.product.price * l.qtyMilli / 1000))}</span></li>`).join("")}</ul><div class="ctot"><span>${esc(t("your_total"))}</span><strong>${esc(money(total()))}</strong></div>${second ? `<small>${esc(t("second_currency", { amount: C.money(second.amount, second.currency), currency: cur }))}</small>` : ""}${S.cdisplay === "pay" && S.method !== "cash" ? `<p class="cpay">${icon("ui-qr")} ${esc(t("pay_by_qr"))}</p>` : ""}${S.tier === "free" && S.cdisplay !== "pay" ? `<small class="pb">${esc(t("powered_by"))} LynkOmni</small>` : ""}</div>`;   // never on the payment step (powered_by rule)
}

/** A counter tablet is made with a touch screen only (catalog/devices.v1.json wall-tablet, dual-screen-pos): its screen carries that interface. */
const DM = new DeviceMode(DEVICES, "wall-tablet");
function draw(): void {
  const screen = $("#screen"), app = screen.querySelector(".app") as HTMLElement; DM.apply(screen);
  screen.classList.toggle("light", !S.dark); screen.classList.toggle("dark", S.dark); screen.classList.toggle("lowlit", DSH.pictures); applyRoot(screen, W);
  const cs = $("#cscreen"); cs.classList.toggle("light", !S.dark); cs.classList.toggle("dark", S.dark); applyRoot(cs, W);
  app.innerHTML = `${top(t("sample_shop"))}<div class="body">${page()}</div>${S.unlocked && ["main", "shift", "dayclose"].includes(S.view) ? tabBar() : ""}${S.flash ? `<div class="toast" role="status">${esc(S.flash)}</div>` : ""}${DSH.overlay()}`;
  const ad = document.getElementById("address"); if (ad) ad.textContent = DSH.address();
  cs.innerHTML = customerDisplay();
}
function act(a: string): void {
  S.lastInput = Date.now();
  const [k = "", v = "", v2 = ""] = a.split(":");
  if (!S.unlocked) {
    if (k.startsWith("d") && k.length === 2) S.pin = (S.pin + k[1]).slice(0, 4);
    else if (k === "clear") S.pin = S.pin.slice(0, -1);
    else if (k === "enter" || S.pin.length === 4) { if (S.pin === "1234") { S.unlocked = true; S.view = "main"; S.tab = S.type === "restaurant" ? "tables" : "sell"; } else { S.pin = ""; toast(t("wrong_pin")); return; } }
    if (S.pin.length === 4 && !S.unlocked) { if (S.pin === "1234") { S.unlocked = true; S.view = "main"; } else { S.pin = ""; toast(t("wrong_pin")); return; } }
    draw(); return;
  }
  const prod = CATALOG.find((p) => p.id === v);
  switch (k) {
    case "tab": S.tab = pick([...TABS[S.type]] as Tab[], v, "home"); S.view = "main"; if (S.tab === "sell") S.cdisplay = S.cart.lines().length ? "basket" : "welcome"; break;
    case "cat": S.cat = pick(["all", "food", "drinks", "home"], v, "all"); break;
    case "add": if (prod) { S.cart.add(prod); S.cdisplay = "basket"; } break;
    case "minus": if (prod) { const l = S.cart.lines().find((x) => x.product.id === prod.id); if (l) S.cart.setQty(prod.id, l.qtyMilli - 1000); } break;
    case "charge": if (webRule("sell", S.registered) !== "ok") { toast(t("needs_registered_device")); return; } S.view = "pay"; S.cdisplay = "basket"; break;
    case "method": { const m = pick(["cash", "card", "mobile_money", "bank_transfer"] as PaymentMethod[], v, "cash"); if (!C.methodOk(m, S.realUser)) { toast(t("coming_soon")); return; } S.method = m; if (m === "cash") { S.view = "cash"; S.tendered = total(); } else { S.cdisplay = "pay"; pay(m); return; } break; }
    case "tip": S.tipPct = pick(["0", "5", "10", "15"], v, "0") === v ? Number(v) : 0; break;
    case "tender": S.tendered = Math.max(0, Number(v) || 0); break;
    case "paycash": try { pay("cash", S.tendered); return; } catch (e) { toast((e as PosError).reason ?? "error"); return; }
    case "go": S.view = pick(SUBVIEWS, v, "main"); if (!(SUBVIEWS as string[]).includes(v)) { toast(t(pick(["devices", "reports", "automations", "academy"], v, "devices"))); } break;
    case "clockin": S.clocked[v] = Date.now(); LOG.emit("ClockedIn", { clock_id: newId(), employee_id: newId() }); break;
    case "clockout": delete S.clocked[v]; LOG.emit("ClockedOut", { clock_id: newId(), employee_id: newId() }); break;
    case "prefer": S.prefer = v === "fastest" ? "fastest" : "cheapest"; break;
    case "addrider": if (mayAddRider(S.riders, deliveryEntitlement(ent(), ent()))) S.riders += 1; break;
    case "book": { if (!S.online) break; const own = v === "own", q = DPARTNERS.find((x) => x.partnerId === v); const d = { id: newId(), partner: own ? t("own_rider") : t(v === "da" ? "partner_a" : "partner_b"), price: own ? 0 : q?.price ?? 0, state: "sent" as UserState };
      S.deliveries.unshift(d); LOG.emit("DeliveryRequested", { delivery_id: d.id, order_id: newId(), own_rider: own, price: d.price, currency: C.pack().currency, ...(own ? {} : { partner_id: v }) });
      window.setTimeout(() => { d.state = S.fail ? "failed" : "accepted"; LOG.emit(S.fail ? "DeliveryFailed" : "DeliveryAccepted", S.fail ? { delivery_id: d.id, reason_code: "partner_declined" } : { delivery_id: d.id, partner_reference: own ? "own-rider" : `SBXD-${d.id.slice(-6)}` }, "server"); draw(); }, reducedMotion() ? 300 : 1500); break; }
    case "joingroup": S.group.joined = true; S.group.total += 2_000_000; LOG.emit("GroupOrderJoined", { group_id: newId(), order_id: newId(), amount: 2_000_000, currency: C.pack().currency }); break;
    case "closegroup": { const out = v === "reach" ? "reached" : groupOutcome(S.group.total, S.group.target + 10_000_000); S.group.outcome = out; LOG.emit(out === "reached" ? "GroupOrderReached" : "GroupOrderFailed", { group_id: newId() }, "server"); if (!chargedWhen(out)) S.group.joined = false; break; }
    case "setup": if ((SETUP_STEPS as readonly string[]).includes(v)) S.setup.add(v); break;
    case "creditpay": { const c = S.credit[Number(v)]; if (c && c.owes) { LOG.emit("CustomerCreditPaid", { payment_id: newId(), credit_id: newId(), amount: c.owes, currency: C.pack().currency, method: "cash" }); if (S.shift) S.shift.cash += c.owes; c.owes = 0; } break; }
    case "remind": toast(t("reminder_sent")); return;     // sent by chat or SMS only to a customer who agreed to reminders
    case "sellcredit": { const s = recordSale(); const name = "Aline"; LOG.emit("CustomerCreditRecorded", { credit_id: newId(), customer_id: newId(), sale_id: s.sale.sale_id, amount: s.sale.total, currency: C.pack().currency }); const c = S.credit.find((x) => x.name === name); if (c) c.owes += s.sale.total; S.cart.clear(); S.current = null; break; }
    case "voice": S.view = "voice"; S.heard = ""; break;
    case "listen": { const phrase = "two bags of rice, one soap"; S.heard = phrase; const lines = parseVoice(phrase, CATALOG.map((p) => ({ id: p.id, name: t(p.name).replace(/ \d.*$/, "") }))); for (const [id, q] of lines) { const p = CATALOG.find((x) => x.id === id); if (p) S.cart.add(p, q); } if (!lines.length) toast(t("nothing_understood")); break; }
    case "back": S.view = "main"; S.cdisplay = S.cart.lines().length ? "basket" : "welcome"; break;
    case "new": newSale(); return;
    case "print": printReceipt(); break;
    case "qr": toast(t("show_qr")); break;
    case "msg": LOG.emit("ReceiptDelivered", { sale_id: S.current?.sale.sale_id, channel: "message", by_automation: "receipt-delivery" }, "server"); toast(t("receipt_sent")); return;
    case "openshift": { const f = Math.max(0, Number(v) || 0); S.shift = { id: newId(), float: f, cash: f }; LOG.emit("ShiftOpened", { shift_id: S.shift.id, float_amount: f, currency: C.pack().currency }); break; }
    case "countcash": if (S.shift) { const c = Math.max(0, Number(S.counted) || 0); const id = newId(); LOG.emit("CashCounted", { count_id: id, shift_id: S.shift.id, kind: "spot", counted_cash: c, expected_cash: S.shift.cash, currency: C.pack().currency }); if (c !== S.shift.cash) LOG.emit("CashDifferenceFlagged", { count_id: id, difference: c - S.shift.cash, currency: C.pack().currency }, "server"); toast(t(c === S.shift.cash ? "no_difference" : "difference_flagged")); return; } break;
    case "closeshift": if (S.shift) { const c = Math.max(0, Number(S.counted) || 0); LOG.emit("ShiftClosed", { shift_id: S.shift.id, counted_cash: c, expected_cash: S.shift.cash, currency: C.pack().currency }); S.shift = null; S.counted = ""; S.view = "main"; S.tab = "home"; } break;
    case "count": if (prod) { LOG.emit("StockCounted", { count_id: newId(), product_id: prod.id, counted_milli: Math.max(S.levels[prod.id] ?? 0, 0), device_view_milli: S.levels[prod.id] ?? 0 }); S.levels = { ...S.levels, [prod.id]: Math.max(S.levels[prod.id] ?? 0, 0) }; toast(t("saved")); return; } break;
    case "opentable": { const id = newId(); const label = String(S.tables.length + 1); S.tables.push({ id, label, covers: 2, open: true, orders: [], sales: [] }); LOG.emit("TableOpened", { table_id: id, table_label: label, covers: 2 }); S.table = id; S.view = "table"; S.cart.clear(); break; }
    case "table": S.table = S.tables.some((x) => x.id === v) ? v : ""; S.view = S.table ? "table" : "main"; S.cart.clear(); break;
    case "kitchen": { const x = S.tables.find((y) => y.id === S.table); if (!x) break; const oid = newId(); const lines = S.cart.lines().map((l, i) => ({ lineNo: i + 1, name: t(l.product.name), qty: Math.ceil(l.qtyMilli / 1000), ready: false }));
      LOG.emit("OrderSentToKitchen", { order_id: oid, table_id: x.id, lines: S.cart.lines().map((l, i) => ({ line_no: i + 1, product_id: l.product.id, quantity_milli: l.qtyMilli })) }); x.orders.push({ id: oid, lines }); S.cart.clear(); break; }
    case "ready": for (const x of S.tables) for (const o of x.orders) if (o.id === v) for (const l of o.lines) if (l.lineNo === Number(v2)) { l.ready = true; LOG.emit("KitchenItemReady", { order_id: o.id, line_no: l.lineNo }); } break;
    case "split": { const x = S.tables.find((y) => y.id === S.table); if (!x) break; const ids: string[] = []; for (const l of S.cart.lines()) { const c = new Cart(); c.add(named(l.product), l.qtyMilli); S.receiptNo += 1; const sale = salePayload(c, newId(), `CT-${S.receiptNo}`, C.pack().currency); LOG.emit("SaleRecorded", sale); ids.push(sale.sale_id); S.sales.unshift({ sale, payments: [paymentPayload(newId(), sale.sale_id, "cash", sale.total)], voided: false, at: Date.now() }); } LOG.emit("TableBillSplit", { table_id: x.id, sale_ids: ids }); x.sales.push(...ids); S.cart.clear(); toast(t("split_bill")); return; }
    case "closetable": { const x = S.tables.find((y) => y.id === S.table); if (x && x.orders.every((o) => o.lines.every((l) => l.ready))) { x.open = false; LOG.emit("TableClosed", { table_id: x.id }); S.view = "main"; S.tab = "tables"; } break; }
    default: break;
  }
  draw();
}

function bindPanel(): void {
  const set = (id: string, text: string): void => { const el = document.getElementById(id); if (el) el.textContent = text; };
  set("pTry", t("try_it")); set("pHelp", `${t("sandbox_note")} PIN 1234.`); set("pCond", t("conditions")); set("lOnline", t("internet")); set("lFail", t("provider_declines")); set("lType", t("business_type")); set("lPlan", t("plan"));
  set("lCountry", t("country")); set("lReal", t("real_user")); set("lPractice", t("practice_mode")); set("lDark", t("dark_screen")); set("lLang", t("language")); set("pLog", t("event_log"));
  $("#cType").innerHTML = BUSINESS_TYPES.map((x) => `<option value="${x}" ${x === S.type ? "selected" : ""}>${esc(t(`type_${x}`))}</option>`).join("");
  $("#cPlan").innerHTML = TIERS.map((x) => `<option value="${x}" ${x === S.tier ? "selected" : ""}>${esc(t(`card_${x}`))}</option>`).join("");
  $("#cCountry").innerHTML = C.options(t("sample_country"));
  ($("#cCountry") as HTMLSelectElement).value = S.country || DATA.packOrder[0] || "";
  $("#cLang").innerHTML = W.options(t("long_text_test"), t("rtl_test")); ($("#cLang") as HTMLSelectElement).value = S.lang;
}
function main(): void {
  S.country = DATA.packOrder[0] ?? "";
  bindPanel(); draw();
  document.addEventListener("click", (e) => { const tg = e.target as HTMLElement, b = tg.closest<HTMLElement>("[data-act]"); if (!b || b.hasAttribute("aria-disabled")) return;
    const a = b.dataset["act"] ?? ""; if (b.classList.contains("dsh-scrim") && tg.closest("[data-stop]")) return; if (DSH.act(a)) return; act(a); });
  document.addEventListener("keydown", (e) => { if (S.unlocked || DSH.panel || DSH.firstRun) DSH.key(e); });
  (window as unknown as { __settle: () => void }).__settle = () => { DSH.settle(); draw(); };
  document.addEventListener("input", (e) => { DSH.input(e.target as HTMLInputElement); const el = e.target as HTMLInputElement; if (el.dataset["filter"] === "counted") { S.counted = plain(el.value).replace(/\D/g, ""); } });
  $("#cOnline").addEventListener("change", (e) => { S.online = (e.target as HTMLInputElement).checked; draw(); });
  $("#cFail").addEventListener("change", (e) => { S.fail = (e.target as HTMLInputElement).checked; });
  $("#cReal").addEventListener("change", (e) => { S.realUser = (e.target as HTMLInputElement).checked; draw(); });
  $("#cPractice").addEventListener("change", (e) => { S.practice = (e.target as HTMLInputElement).checked; draw(); });
  $("#cDark").addEventListener("change", (e) => { S.dark = (e.target as HTMLInputElement).checked; draw(); });
  $("#cType").addEventListener("change", (e) => { S.type = pick(BUSINESS_TYPES, (e.target as HTMLSelectElement).value, "shop"); S.tab = S.type === "restaurant" ? "tables" : "home"; S.view = "main"; draw(); });
  $("#cPlan").addEventListener("change", (e) => { S.tier = pick(TIERS, (e.target as HTMLSelectElement).value, "plus"); draw(); });
  $("#cCountry").addEventListener("change", (e) => { S.country = pick(DATA.packOrder, (e.target as HTMLSelectElement).value, S.country); draw(); });
  $("#cLang").addEventListener("change", (e) => { const v = (e.target as HTMLSelectElement).value; S.lang = v in DATA.i18n || v === "xx" || v === "xx-rtl" ? v : "en"; bindPanel(); draw(); });
  $("#scanKey").addEventListener("click", () => { if (S.unlocked) scan(); });
  $("#tapzone").addEventListener("click", () => { if (S.unlocked && S.view === "pay") act("method:card"); });
  $("#tearBtn").addEventListener("click", () => { $("#paperWrap").classList.add("torn"); window.setTimeout(() => { $("#paperWrap").hidden = true; }, 500); });
  $("#stateButtons").innerHTML = ["locked", "sell", "pay", "cash", "done", "tables", "kitchen", "shift", "dayclose", "stock", "business", "staff", "deliver", "group", "setup", "credit", "voice"].map((k) => `<button type="button" data-state="${k}">${esc(k)}</button>`).join("");
  $("#stateButtons").addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-state]"); if (!b) return; const k = b.dataset["state"] ?? ""; S.lastInput = Date.now(); DSH.settle();
    if (k === "locked") { S.unlocked = false; S.pin = ""; } else { S.unlocked = true; if (["sell", "stock", "tables", "kitchen", "business"].includes(k)) { if (k === "tables" || k === "kitchen") S.type = "restaurant"; S.tab = k as Tab; S.view = "main"; } else { if (!S.cart.lines().length && CATALOG[0]) S.cart.add(CATALOG[0]); if (k === "done") { S.view = "cash"; S.tendered = total(); pay("cash", S.tendered); return; } S.view = pick(["pay", "cash", "shift", "dayclose", "staff", "deliver", "group", "setup", "credit", "voice"] as View[], k, "main"); if (k === "cash") S.tendered = total(); } } draw(); });
  window.setInterval(tick, 400);
  fitToWidth($("#rig"), 740);
}
main();
