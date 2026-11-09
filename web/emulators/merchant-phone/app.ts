/** LynkOmni merchant app on a phone (blueprint sections 2 and 5). Draws an original LynkOmni phone and runs the merchant app
 *  inside it: sign-in and device registration, the role-aware Home, Sell, Stock, Chats and Business tabs, the connection chip
 *  and sync sheet (mode manager). Selling, stock and the day's summary use the real rules in ts/src/pos.ts and
 *  ts/src/merchant.ts; payments and the cloud are sandboxes (test money only). Draft until a designer reviews it.
 *  Built into one offline HTML file by web/build.mjs. Colours come only from the design tokens (CSS variables). */
import { Cart, PosError, change, formatMoney, paymentPayload, paymentState, qtyText, quickCash, salePayload, uuid7 } from "../../../ts/src/pos.js";
import type { PaymentMethod, PaymentPayload, PaymentStatus, Product, SalePayload, UserState } from "../../../ts/src/pos.js";
import { adjust, afterSale, canChangeSettings, canSeeProfit, counted, daySummary, homeBlocks, insight, maySync, mode, pending, stockAlerts, stockState } from "../../../ts/src/merchant.js";
import type { DaySale, Levels, Link, Role, StockItem } from "../../../ts/src/merchant.js";
import { TABS, webRule } from "../../../ts/src/business.js";
import type { BusinessType } from "../../../ts/src/business.js";
import { AGENT_SERVICES, COLLECTION_KINDS, FINANCE_PRODUCTS, combinedLimits, commission, floatForecastDays, limitCheck, lowFloat, mayHandOverCash } from "../../../ts/src/agent.js";
import type { AgentState, Limits } from "../../../ts/src/agent.js";
import { TEST_LANGS, esc, newId, pick, pseudo, randomBytes } from "../../../ts/src/emulator.js";

interface BuildData {
  icons: Record<string, string>;
  brand: { body: string; topLight: string; topDark: string; receipt: string };
  pictures: { offLight: string; offDark: string; offAlt: string };
  states: Record<string, { label: string; meaning: string }>;
  /** Every country pack, the neutral sample pack first (Step 0): the chooser never opens on a real country. */
  packs: Record<string, CountryPack>;
  packOrder: string[];
  i18n: Record<string, { native: string; dir: "ltr" | "rtl"; texts: Record<string, string> }>;
}
interface CountryPack {
  code: string; name: string; currency: string; tz: string; locale: string; sample: boolean;
  ready: Record<string, { ok: boolean; message: string }>;
  services: { service: string; name: string; icon: string; state: "available" | "coming_soon" }[];
}
declare const DATA: BuildData;
/** The country the emulator shows. Read from the country pack and the provider ledger; nothing about a country lives in this code. */
const pack = (): CountryPack => DATA.packs[S.country] ?? DATA.packs[DATA.packOrder[0] ?? ""] as CountryPack;

type Tab = "home" | "sell" | "stock" | "chats" | "business" | "services" | "float";
type View = "main" | "basket" | "pay" | "cash" | "momo" | "waiting" | "done" | "off" | "item" | "thread" | "svc";
/** Agent point mode (blueprint 42 C and 42 I): the sample partners are sandbox partners; the float sits in the agent's own
 *  account at each partner and is only read from it. The device asks; the partner alone confirms. */
interface Partner { id: string; name: string; float: number; limits: Limits; bps: number }
interface AgentReq { id: string; partner: string; service: string; number: string; amount: number; fee: number; commission: number; state: AgentState; ref: string; reason: string; at: number }
const PARTNERS: Partner[] = [{ id: "pa", name: "partner_a", float: 400_000, limits: { per_transaction: 200_000, per_day: 2_000_000 }, bps: 100 }, { id: "pb", name: "partner_b", float: 30_000, limits: { per_transaction: 100_000, per_day: 1_000_000 }, bps: 120 }];
const AGENT_ALL = [...AGENT_SERVICES, ...COLLECTION_KINDS, ...FINANCE_PRODUCTS] as const;
interface Ev { n: number; type: string; origin: "device" | "server"; payload: unknown; sync: UserState; at: number }
interface Sale extends DaySale { at: number; tendered?: number }
interface Msg { out: boolean; text: string; at: number; state: UserState }
interface Thread { id: string; name: string; msgs: Msg[]; unread: number }
interface Item extends Product, StockItem {}

/** Screen words: English in strings.en.json, every other language from the packs in i18n/<lang>.json (translated by Claude and
 *  checked by tools/translation/claude_packs.py), all embedded by web/build.mjs so every language works offline. */
const PACKS = DATA.i18n;
const EN: Record<string, string> = PACKS.en?.texts ?? {};

const P = (milli: number): number => milli * 1000;
const CATALOG: Item[] = ([
  ["Rice 1 kg", 1500, 1150, "food", 24, 10], ["Sugar 1 kg", 1400, 1100, "food", 6, 8], ["Beans 1 kg", 1200, 900, "food", 30, 10],
  ["Cooking oil 1 L", 3200, 2600, "food", 2, 5], ["Bread", 1000, 700, "food", 12, 6], ["Eggs, tray of 30", 4500, 3800, "food", 1, 3],
  ["Milk 500 ml", 600, 420, "drinks", 20, 10], ["Water 1.5 L", 700, 450, "drinks", 36, 12], ["Soda 300 ml", 500, 330, "drinks", 40, 12],
  ["Tea leaves 100 g", 900, 600, "drinks", 15, 5], ["Soap bar", 500, 320, "home", 18, 6], ["Matches, pack", 300, 180, "home", 50, 10],
] as const).map(([name, price, cost, category, , reorder]) => { const id = newId(); return { id, productId: id, name, price, cost, category, reorderAtMilli: P(reorder) }; });
const START: Levels = Object.fromEntries(CATALOG.map((p, i) => [p.id, P([24, 6, 30, 2, 12, 1, 20, 36, 40, 15, 18, 50][i] ?? 0)]));
const COSTS = Object.fromEntries(CATALOG.map((p) => [p.id, p.cost]));
const NOTES = [500, 1000, 2000, 5000, 10000];
const SHOP = "Sample shop";
const DEVICE = "MP";
const CODE = "123456";
const ago = (min: number): number => Date.now() - min * 60_000;
const THREADS: Thread[] = [
  { id: "t1", name: "Aline", unread: 1, msgs: [{ out: false, text: "Do you have cooking oil today?", at: ago(12), state: "accepted" }] },
  { id: "t2", name: "Eric", unread: 1, msgs: [{ out: false, text: "Can you keep 2 trays of eggs for me until 5 pm?", at: ago(40), state: "accepted" }] },
  { id: "t3", name: "Grace", unread: 0, msgs: [{ out: false, text: "Thank you for the delivery!", at: ago(180), state: "accepted" }, { out: true, text: "You are welcome. See you soon.", at: ago(175), state: "sent" }] },
];

const S = {
  screen: "phone" as "phone" | "code" | "enrol" | "app", tab: "home" as Tab, view: "main" as View, sheet: false,
  btype: "shop" as BusinessType, svc: "bills" as string, partner: "pa", number: "", amount: "", reqs: [] as AgentReq[], req: "", cashIn: 150_000, usedToday: 0,
  lang: "en", theme: "light" as "light" | "dark", link: "good" as Link, forced: false, realUser: false, country: "", outcome: "confirm" as "confirm" | "fail",
  role: "owner" as Role, perms: { staffSeeProfit: false }, phone: "", code: "", input: "", note: "", flash: "", category: "all",
  cart: new Cart(), current: null as Sale | null, sales: [] as Sale[], events: [] as Ev[], levels: { ...START }, flagged: new Set<string>(),
  threads: THREADS, thread: "", draft: "", product: "", qty: 1, notified: new Set<string>(), receiptNo: 0, lastSync: 0, ticks: 0, enrolled: false,
};

const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const isTest = (): boolean => (TEST_LANGS as readonly string[]).includes(S.lang);
const t = (k: string, vars: Record<string, string | number> = {}): string => {
  const en = EN[k] ?? k, raw = isTest() ? pseudo(en) : PACKS[S.lang]?.texts[k] ?? en;
  return raw.replace(/\{(\w+)\}/g, (m, v: string) => (v in vars ? String(vars[v]) : m));
};
const locale = (): string => `${isTest() ? "en" : S.lang}-${pack().code}`;
const money = (n: number): string => formatMoney(n, pack().currency, locale());
const icon = (id: string, cls = "ic"): string => `<span class="${cls}" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const clock = (ms: number): string => new Intl.DateTimeFormat(locale(), { timeZone: pack().tz, hour: "2-digit", minute: "2-digit" }).format(ms);
const reduced = (): boolean => matchMedia("(prefers-reduced-motion: reduce)").matches;
const online = (): boolean => mode(S.link, S.forced) === "online";
const methodOk = (m: PaymentMethod): boolean => m === "cash" || !S.realUser || (pack().ready[m]?.ok ?? false);
const item = (id: string): Item | undefined => CATALOG.find((p) => p.id === id);
const level = (id: string): number => S.levels[id] ?? 0;
const unread = (): number => S.threads.reduce((a, th) => a + th.unread, 0);
const toast = (msg: string): void => { S.flash = msg; draw(); window.setTimeout(() => { S.flash = ""; draw(); }, 1600); };

// ---- event log and the simulated cloud --------------------------------------------------------------------------
function emit(type: string, payload: unknown, origin: "device" | "server" = "device"): Ev {
  const e: Ev = { n: S.events.length + 1, type, origin, payload, sync: origin === "server" ? "accepted" : "queued", at: Date.now() };
  S.events.unshift(e); drawLog(); return e;
}
function tick(): void {
  S.ticks += 1;
  if (!maySync(S.link, S.forced) || (S.link === "weak" && S.ticks % 4)) return;   // a weak link sends now and then
  const now = Date.now();
  let changed = false;
  for (const e of [...S.events].reverse()) {
    if (e.sync === "queued") { e.sync = "sent"; e.at = now; changed = true; }
    else if (e.sync === "sent" && now - e.at > 700) { e.sync = "accepted"; changed = true; if (e.type === "SaleRecorded") cloudChecksStock(e); }
  }
  for (const th of S.threads) for (const m of th.msgs) if (m.out && m.state === "queued") { m.state = "sent"; changed = true; }
  if (online()) for (const s of S.sales) for (const p of s.payments) if (p.status === "pending_confirmation" && !asking.has(p.payment_id)) askProvider(s, p);
  if (changed || !pending(S.events.map((e) => e.sync)).count) S.lastSync = now;
  if (changed) { drawLog(); draw(); }
}
/** The cloud never blocks a sale; it flags stock that went below zero so the owner can count it (server-only event). */
function cloudChecksStock(e: Ev): void {
  for (const l of (e.payload as SalePayload).lines) {
    if (level(l.product_id) < 0 && !S.flagged.has(l.product_id)) {
      S.flagged.add(l.product_id);
      emit("NegativeStockFlagged", { product_id: l.product_id, projected_milli: level(l.product_id), as_of_cursor: e.n }, "server");
    }
  }
}
const asking = new Set<string>();
function askProvider(s: Sale, p: PaymentPayload): void {   // the sandbox provider answers after a short wait
  asking.add(p.payment_id);
  window.setTimeout(() => {
    asking.delete(p.payment_id);
    if (!online()) return;
    const to: PaymentStatus = S.outcome === "confirm" ? "confirmed" : "failed";
    emit("PaymentStatusChanged", { payment_id: p.payment_id, from_status: p.status, to_status: to, source: "provider_callback", provider_reference: `SBX-${p.payment_id.slice(-8).toUpperCase()}` }, "server");
    p.status = to;
    if (S.current === s && S.view === "waiting" && to === "confirmed") S.view = "done";
    draw();
  }, reduced() ? 300 : 2600);
}

// ---- selling ------------------------------------------------------------------------------------------------------
function recordSale(): Sale {
  if (S.current) return S.current;
  S.receiptNo += 1;
  const sale = salePayload(S.cart, newId(), `${DEVICE}-${S.receiptNo}`, pack().currency);
  emit("SaleRecorded", sale);
  emit("ReceiptIssued", { receipt_id: newId(), sale_id: sale.sale_id, receipt_number_local: sale.receipt_number_local, copy_number: 1, validity: "provisional" });
  S.levels = afterSale(S.levels, sale);   // never blocked: stock may go below zero and is flagged instead
  const s: Sale = { sale, payments: [], voided: false, at: Date.now() };
  S.sales.unshift(s); S.current = s;
  return s;
}
function pay(method: PaymentMethod, tendered?: number): void {
  const s = recordSale();
  const p = paymentPayload(newId(), s.sale.sale_id, method, s.sale.total);
  s.payments.push(p); emit("PaymentRecorded", p);
  if (method === "cash") { s.tendered = tendered; S.view = "done"; } else S.view = "waiting";
  draw();
}
function newSale(): void { S.cart.clear(); S.current = null; S.input = ""; S.note = ""; S.tab = "sell"; S.view = "main"; draw(); }
const lastPayment = (): PaymentPayload | undefined => S.current?.payments[S.current.payments.length - 1];

// ---- stock ----------------------------------------------------------------------------------------------------------
function stockAct(kind: string): void {
  const p = item(S.product); if (!p) return;
  const q = P(S.qty);
  if (kind === "received") {
    emit("StockReceived", { stock_receipt_id: newId(), lines: [{ product_id: p.id, quantity_milli: q, unit_cost: p.cost }] });
    S.levels = { ...S.levels, [p.id]: level(p.id) + q };
  } else if (kind === "count") {
    emit("StockCounted", { count_id: newId(), product_id: p.id, counted_milli: q, device_view_milli: level(p.id) });
    S.levels = counted(S.levels, p.id, q).levels; S.flagged.delete(p.id);
  } else {
    emit("StockAdjusted", { adjustment_id: newId(), product_id: p.id, delta_milli: -q, reason_code: kind });
    S.levels = adjust(S.levels, p.id, -q);
  }
  toast(t("saved"));
}

// ---- chats (a server-side module in contract v1, so messages are not device events) ---------------------------------
function sendMsg(): void {
  const th = S.threads.find((x) => x.id === S.thread); const text = S.draft.trim();
  if (!th || !text) return;
  th.msgs.push({ out: true, text, at: Date.now(), state: maySync(S.link, S.forced) && S.link === "good" ? "sent" : "queued" });
  S.draft = ""; draw();
}

// ---- screens --------------------------------------------------------------------------------------------------------
const logo = (): string => (S.theme === "dark" ? DATA.brand.topDark : DATA.brand.topLight);
function topBar(title: string, back?: string): string {
  const p = pending(S.events.map((e) => e.sync)), off = !online();
  return `<div class="top">${back ? `<button class="iconbtn back" data-act="${back}" aria-label="${esc(t("back"))}">${icon("ui-arrow-left")}</button>` : `<span class="logo" role="img" aria-label="LynkOmni">${logo()}</span>`}
    <h1>${esc(title)}</h1><button class="netchip${off ? " off" : ""}" data-act="sheet" aria-label="${esc(t("sync"))}">${icon(off ? "ui-offline" : "ui-sync")}<span>${esc(t(off ? "offline" : "online"))}</span>${p.count ? `<span class="count">${p.count}</span>` : ""}</button></div>`;
}
function tabBar(): string {
  const ic: Record<string, string> = { home: "ui-home", sell: "ui-cart", stock: "product-stock", chats: "product-chat", business: "product-dash", services: "ui-grid", float: "ui-chart" };
  const tabs: [Tab, string][] = TABS[S.btype === "agent_point" ? "agent_point" : "shop"].map((k) => [k as Tab, ic[k] ?? "ui-grid"]);
  return `<nav class="tabbar" aria-label="LynkOmni">${tabs.map(([k, ic]) => `<button data-act="tab:${k}" ${S.tab === k ? 'aria-current="page"' : ""}>${icon(ic)}<span>${esc(t(`tab_${k}`))}</span>${k === "chats" && unread() ? `<span class="dot">${unread()}</span>` : ""}</button>`).join("")}</nav>`;
}
const summary = () => daySummary(S.sales, COSTS);

function home(): string {
  const blocks = homeBlocks(S.role, S.perms), sm = summary(), out: string[] = [`<p class="greet">${esc(t("hello", { shop: SHOP }))}</p>`];
  const kpis = blocks.filter((b) => b === "sales" || b === "profit").map((b) => `<div class="card kpi"><span>${esc(t(b === "sales" ? "today_sales" : "today_profit"))}</span><strong>${esc(money(b === "sales" ? sm.total : sm.profit))}</strong>${b === "sales" ? `<small>${esc(t("sales_count", { n: sm.count }))}</small>` : ""}</div>`);
  if (kpis.length) out.push(kpis.length === 2 ? `<div class="duo">${kpis.join("")}</div>` : kpis.join(""));
  for (const b of blocks) {
    if (b === "new_sale") out.push(`<button class="big" data-act="newsale">${icon("ui-plus")}<span>${esc(t("new_sale"))}</span></button>`);
    if (b === "stock_check") out.push(`<button class="ghost" data-act="tab:stock">${esc(t("stock_check"))}</button>`);
    if (b === "alerts") {
      const a = stockAlerts(CATALOG, S.levels);
      const rows = [...a.negative.map((id) => [id, "neg", "below_zero"]), ...a.low.map((id) => [id, "low", "low_stock"])].slice(0, 4)
        .map(([id, c, k]) => `<button class="alert ${c}" data-act="product:${id}">${icon("ui-warning")}<span><b>${esc(item(id ?? "")?.name ?? "")}</b>${esc(t(k ?? ""))}</span>${icon("ui-chevron-right", "ic fwd")}</button>`);
      out.push(`<div class="card"><h2>${esc(t("attention"))}</h2>${rows.join("") || `<p>${esc(t("stock_fine"))}</p>`}</div>`);
    }
    if (b === "chats") out.push(`<button class="card rowbtn" data-act="tab:chats">${icon("product-chat")}<span class="main"><span class="nm">${esc(t("tab_chats"))}</span><span class="sub">${esc(unread() ? t("unread", { n: unread() }) : t("no_unread"))}</span></span>${icon("ui-chevron-right", "ic fwd")}</button>`);
    if (b === "insight") { const best = insight(S.sales); out.push(`<div class="card"><h2>${icon("product-grow")}<span>${esc(t("insight"))}</span></h2><p>${esc(best ? t("best_seller", { product: best.name, qty: qtyText(best.qtyMilli) }) : t("no_insight"))}</p></div>`); }
    if (b === "pending") { const p = pending(S.events.map((e) => e.sync)); out.push(`<button class="card rowbtn" data-act="sheet">${chip(p.state)}<span class="main"><span class="sub">${esc(p.count ? t("waiting_send", { n: p.count }) : t("all_sent"))}</span></span>${icon("ui-chevron-right", "ic fwd")}</button>`); }
  }
  return `${topBar(t("tab_home"))}<div class="body">${out.join("")}</div>`;
}

function sell(): string {
  const c = S.current, total = S.cart.total();
  const due = (n: number): string => `<div class="due"><span>${esc(t("total"))}</span><strong>${esc(money(n))}</strong></div>`;
  switch (S.view) {
    case "basket":
      return `${topBar(t("basket"), "view:main")}<div class="body"><ul class="list">${S.cart.lines().map((l) => `<li><div class="rowbtn"><span class="main"><span class="nm">${esc(l.product.name)}</span><span class="sub">${esc(money(l.product.price))}</span></span>
        <span class="stepper"><button class="iconbtn" data-act="dec:${l.product.id}" aria-label="-1 ${esc(l.product.name)}">${icon(l.qtyMilli > 1000 ? "ui-minus" : "ui-trash")}</button><output>${qtyText(l.qtyMilli)}</output><button class="iconbtn" data-act="inc:${l.product.id}" aria-label="+1 ${esc(l.product.name)}">${icon("ui-plus")}</button></span></div></li>`).join("") || `<li><p class="info">${esc(t("empty_basket"))}</p></li>`}</ul></div>
        <div class="foot"><div class="sum"><span>${esc(t("items", { n: S.cart.count() }))}</span><strong>${esc(money(total))}</strong></div><button class="primary" data-act="view:pay" ${S.cart.count() ? "" : "disabled"}>${esc(t("charge"))}</button></div>`;
    case "pay":
      return `${topBar(t("charge"), "view:basket")}<div class="body">${due(total)}<p class="info">${esc(t("how_pay"))}</p>
        ${(["cash", "mobile_money"] as PaymentMethod[]).map((m) => { const ok = methodOk(m); return `<button class="method${ok ? "" : " off"}" data-act="method:${m}">${icon(m === "cash" ? "ui-receipt" : "ui-pay-mobile-money")}<span>${esc(t("method_" + m))}</span>${ok ? (m !== "cash" ? `<em>${esc(t("sandbox"))}</em>` : "") : `<em>${esc(t("coming_soon"))}</em>`}${icon("ui-chevron-right", "ic fwd")}</button>`; }).join("")}</div>`;
    case "cash": {
      const given = Number(S.input || "0"), enough = given >= total;
      return `${topBar(t("method_cash"), "view:pay")}<div class="body">${due(total)}
        <label class="field"><span>${esc(t("cash_given"))}</span><input id="cashIn" inputmode="numeric" autocomplete="off" value="${esc(S.input)}" data-in="cash"></label>
        <div class="quick">${quickCash(total, NOTES).map((v) => `<button data-act="cash:${v}">${esc(money(v))}</button>`).join("")}</div>
        <div class="change ${enough ? "ok" : ""}"><span>${esc(t("change"))}</span><strong>${enough ? esc(money(change(total, given))) : "–"}</strong></div></div>
        <div class="foot"><button class="primary" data-act="paycash" ${enough ? "" : "disabled"}>${esc(t("complete"))}</button></div>`;
    }
    case "momo":
      return `${topBar(t("method_mobile_money"), "view:pay")}<div class="body">${due(total)}
        <label class="field"><span>${esc(t("customer_phone"))}</span><input id="momoIn" inputmode="tel" autocomplete="off" value="${esc(S.input)}" data-in="momo"></label>
        <p class="info sbx">${icon("ui-info")}<span>${esc(t("sandbox"))}: ${esc(t("test_money"))}</span></p></div>
        <div class="foot"><button class="primary" data-act="paymomo" ${S.input.replace(/\D/g, "").length >= 9 ? "" : "disabled"}>${esc(t("send_to_partner"))}</button></div>`;
    case "waiting": {
      const p = lastPayment(); if (!p || !c) return "";
      const st = paymentState(p.status, online()), failed = st === "failed";
      return `${topBar(t("method_mobile_money"), failed ? "view:pay" : undefined)}<div class="center">${due(c.sale.total)}${failed ? "" : `<div class="spinner" aria-hidden="true"></div>`}${st !== "cash" && st !== "credit" ? chip(st) : ""}
        <p>${esc(failed ? t("failed_note") : st === "queued" ? t("queued_note") : t("wait_momo"))}</p></div>
        ${st === "queued" ? `<div class="foot"><button class="primary" data-act="newsale">${esc(t("new_sale"))}</button></div>` : ""}
        ${failed ? `<div class="foot two"><button class="ghost" data-act="view:pay">${esc(t("other_method"))}</button><button class="primary" data-act="retry">${esc(t("try_again"))}</button></div>` : ""}`;
    }
    case "done":
      return `${topBar(t("done"))}<div class="center">${icon("ui-check", "bigcheck")}<h1>${esc(t("done"))}</h1>${c ? `<p class="amount">${esc(money(c.sale.total))}</p>
        ${c.tendered !== undefined ? `<p>${esc(t("change"))}: <strong>${esc(money(change(c.sale.total, c.tendered)))}</strong></p>` : ""}
        <div class="receipt"><span class="nm">${esc(t("receipt"))} ${esc(c.sale.receipt_number_local)}</span><span>${esc(t("provisional"))}</span><span>${esc(t("not_tax"))}</span></div>` : ""}</div>
        <div class="foot"><button class="primary" data-act="newsale">${esc(t("new_sale"))}</button></div>`;
    case "off":
      return `${topBar(t("method_mobile_money"), "view:pay")}<div class="center"><span class="pic" role="img" aria-label="${esc(DATA.pictures.offAlt)}">${S.theme === "dark" ? DATA.pictures.offDark : DATA.pictures.offLight}</span>
        <p class="nm">${esc(t("coming_soon"))}</p>${notifyBtn("payments")}</div><div class="foot"><button class="primary" data-act="view:pay">${esc(t("other_method"))}</button></div>`;
    default: {
      const cats = ["all", "food", "drinks", "home"];
      const items = CATALOG.filter((p) => S.category === "all" || p.category === S.category);
      return `${topBar(t("tab_sell"))}<div class="cats">${cats.map((k) => `<button data-act="cat:${k}" aria-pressed="${S.category === k}">${esc(t(k === "home" ? "household" : k))}</button>`).join("")}</div>
        <div class="body"><div class="grid">${items.map((p) => { const q = S.cart.lines().find((l) => l.product.id === p.id); return `<button class="tile" data-act="add:${p.id}"><span class="nm">${esc(p.name)}</span><span class="pr">${esc(money(p.price))}</span>${q ? `<span class="qty">${qtyText(q.qtyMilli)}</span>` : ""}</button>`; }).join("")}</div></div>
        <div class="foot"><div class="sum"><span>${esc(t("items", { n: S.cart.count() }))}</span><strong>${esc(money(total))}</strong></div><button class="primary" data-act="view:basket" ${S.cart.count() ? "" : "disabled"}>${esc(t("basket"))}</button></div>`;
    }
  }
}
function notifyBtn(service: string): string {
  return S.notified.has(service) ? `<p class="info">${icon("ui-bell")}<span>${esc(t("notify_done"))}</span></p>` : `<button class="linkbtn" data-act="notify:${service}">${esc(t("notify_me"))}</button>`;
}

function stock(): string {
  if (S.view === "item") {
    const p = item(S.product); if (!p) return "";
    const lv = level(p.id), st = stockState(lv, p.reorderAtMilli);
    return `${topBar(p.name, "view:main")}<div class="body"><div class="card"><div class="duo"><div class="kpi"><span>${esc(t("in_stock"))}</span><strong>${qtyText(lv)}</strong></div><div class="kpi"><span>${esc(t("reorder_at"))}</span><strong>${qtyText(p.reorderAtMilli)}</strong></div></div>
      ${st === "negative" ? `<p class="info">${icon("ui-warning")}<span>${esc(t("never_blocked"))}</span></p>` : ""}</div>
      <div class="card"><span class="sub">${esc(t("quantity"))}</span><div class="stepper"><button class="iconbtn" data-act="qty:-1" aria-label="-1">${icon("ui-minus")}</button><output>${S.qty}</output><button class="iconbtn" data-act="qty:1" aria-label="+1">${icon("ui-plus")}</button></div>
      <div class="actions"><button class="primary" data-act="stock:received">${esc(t("received"))}</button><button class="ghost" data-act="stock:count">${esc(t("count_set"))}</button></div></div>
      <div class="card"><h2>${esc(t("remove"))}</h2><div class="reasons">${["damage", "loss", "expiry", "correction"].map((r) => `<button data-act="stock:${r}">${esc(t("r_" + r))}</button>`).join("")}</div></div>
      ${S.flash ? `<div class="toast" role="status">${icon("ui-check")}<span>${esc(S.flash)}</span></div>` : ""}</div>`;
  }
  const rank = { negative: 0, low: 1, ok: 2 } as const;
  const rows = [...CATALOG].sort((a, b) => rank[stockState(level(a.id), a.reorderAtMilli)] - rank[stockState(level(b.id), b.reorderAtMilli)]).map((p) => {
    const st = stockState(level(p.id), p.reorderAtMilli);
    return `<li><button class="rowbtn" data-act="product:${p.id}">${icon("product-stock", "prod")}<span class="main"><span class="nm">${esc(p.name)}</span><span class="sub">${esc(t("in_stock"))}: ${qtyText(level(p.id))}</span></span>
      ${st === "ok" ? "" : `<span class="pill ${st === "negative" ? "neg" : "low"}">${esc(t(st === "negative" ? "below_zero" : "low_stock"))}</span>`}</button></li>`;
  });
  return `${topBar(t("tab_stock"))}<div class="body"><ul class="list card">${rows.join("")}</ul></div>`;
}

function chats(): string {
  const th = S.threads.find((x) => x.id === S.thread);
  if (S.view === "thread" && th) {
    return `${topBar(th.name, "view:main")}<div class="thread"><p class="info">${icon("ui-info")}<span>${esc(t("original_language"))}</span></p>
      ${th.msgs.map((m) => `<div class="msg ${m.out ? "out" : "in"}"><span>${esc(m.text)}</span><span class="meta">${esc(clock(m.at))}${m.out ? chip(m.state === "queued" ? "queued" : "sent") : ""}</span></div>`).join("")}</div>
      <div class="compose"><input id="msgIn" data-in="msg" aria-label="${esc(t("write_message"))}" placeholder="${esc(t("write_message"))}" value="${esc(S.draft)}" autocomplete="off"><button class="iconbtn fwd" data-act="send" aria-label="${esc(t("send"))}">${icon("ui-chevron-right")}</button></div>`;
  }
  return `${topBar(t("tab_chats"))}<div class="body"><p class="info">${icon("ui-info")}<span>${esc(t("business_chat"))}</span></p><ul class="list card">${S.threads.map((x) => { const last = x.msgs[x.msgs.length - 1];
    return `<li><button class="rowbtn" data-act="thread:${x.id}"><span class="avatar" aria-hidden="true">${esc(x.name.slice(0, 1))}</span><span class="main"><span class="nm">${esc(x.name)}</span><span class="sub">${esc(last?.text ?? "")}</span></span>${x.unread ? `<span class="pill ok">${x.unread}</span>` : `<span class="sub">${esc(last ? clock(last.at) : "")}</span>`}</button></li>`; }).join("")}</ul></div>`;
}

function business(): string {
  const sm = summary(), profit = canSeeProfit(S.role, S.perms), owner = canChangeSettings(S.role);
  const kv = (k: string, v: number): string => `<div class="kv"><span>${esc(t(k))}</span><strong>${esc(money(v))}</strong></div>`;
  return `${topBar(t("tab_business"))}<div class="body">
    <div class="card"><h2>${icon("product-dash")}<span>${esc(t("closing"))}</span></h2>
      <div class="duo"><div class="kpi"><span>${esc(t("today_sales"))}</span><strong>${esc(money(sm.total))}</strong><small>${esc(t("sales_count", { n: sm.count }))}</small></div>
      ${profit ? `<div class="kpi"><span>${esc(t("today_profit"))}</span><strong>${esc(money(sm.profit))}</strong></div>` : ""}</div>
      ${kv("cash_drawer", sm.cash)}${kv("confirmed_money", sm.confirmed)}${kv("waiting_money", sm.waiting)}${kv("failed_money", sm.failed)}</div>
    <div class="card"><h2>${esc(t("services"))}</h2><ul class="list">${pack().services.map((s) => `<li class="svc">${icon(s.icon, "prod")}<span class="main"><span class="nm">${esc(s.name)}</span>
      <span class="sub">${esc(t(s.state === "available" ? "available" : "coming_soon"))}</span></span>${s.state === "available" ? `<span class="pill ok">${icon("ui-check")}</span>` : notifyBtn(s.service)}</li>`).join("")}</ul></div>
    <div class="card"><h2>${esc(t("team"))}</h2><div class="kv"><span>${esc(t("signed_in"))}</span><strong>${esc(t(`role_${S.role}`))}</strong></div>
      <label class="switch"><span>${esc(t("staff_profit"))}</span><input type="checkbox" data-in="perm" ${S.perms.staffSeeProfit ? "checked" : ""} ${owner ? "" : "disabled"}></label>
      ${owner ? "" : `<p>${esc(t("owner_only"))}</p>`}</div>
    ${S.flash ? `<div class="toast" role="status">${icon("ui-bell")}<span>${esc(S.flash)}</span></div>` : ""}</div>`;
}


// ---- agent point mode ------------------------------------------------------------------------------------------------
const partner = (id = S.partner): Partner => PARTNERS.find((p) => p.id === id) ?? (PARTNERS[0] as Partner);
const usual = (p: Partner): number => Math.max(...S.reqs.filter((r) => r.partner === p.id && r.state === "confirmed").map(() => 120_000), 120_000);
const feeFor = (amount: number): number => Math.max(100, Math.floor(amount / 100));
/** What the agent types is in whole units of the money (500, not 50000 cents); the event carries integer minor units. */
const toMinor = (typed: string): number => { const d = new Intl.NumberFormat("en", { style: "currency", currency: pack().currency }).resolvedOptions().maximumFractionDigits ?? 2; return Number(typed || 0) * 10 ** d; };
function agentHome(): string {
  const today = S.reqs.filter((r) => r.state === "confirmed");
  const com = today.reduce((a, r) => a + r.commission, 0);
  const floats = PARTNERS.map((p) => `<div class="kv"><span>${esc(t("float_at", { partner: t(p.name) }))}</span><strong>${esc(money(p.float))}</strong></div>${lowFloat(p.float, usual(p)) ? `<p class="alert low">${icon("ui-warning")}<span>${esc(t("low_float"))}</span></p>` : ""}`).join("");
  return `${topBar(t("agent_point"))}<div class="body"><div class="card"><h2>${esc(t("float"))}</h2>${floats}<p class="sub">${esc(t("float_read_live"))}</p></div>
    <div class="duo"><div class="card kpi"><span>${esc(t("cash_in_drawer"))}</span><strong>${esc(money(S.cashIn))}</strong></div><div class="card kpi"><span>${esc(t("commission"))}</span><strong>${esc(money(com))}</strong><small>${esc(t("today_services", { n: today.length, amount: money(com) }))}</small></span></div></div>
    <button class="big" data-act="tab:services">${icon("ui-grid")}<span>${esc(t("services"))}</span></button>
    <div class="card"><h2>${esc(t("commissions"))}</h2>${S.reqs.slice(0, 4).map((r) => `<div class="kv"><span>${esc(t(`svc_${r.service}`))} · ${esc(money(r.amount))}</span>${chip(r.state)}</div>`).join("") || `<p>${esc(t("no_sales_yet"))}</p>`}</div></div>`;
}
function agentServices(): string {
  const tile = (k: string, group: string): string => `<button class="tile" data-act="svc:${k}">${icon(group === "agent" ? "ui-pay-mobile-money" : group === "collect" ? "ui-receipt" : "ui-pay-bank")}<span>${esc(t(`svc_${k}`))}</span></button>`;
  return `${topBar(t("services"))}<div class="body">${online() ? "" : `<p class="alert low">${icon("ui-offline")}<span>${esc(t("online_only"))}</span></p>`}
    <h2 class="sect">${esc(t("agent"))}</h2><div class="tiles">${AGENT_SERVICES.map((k) => tile(k, "agent")).join("")}</div>
    <h2 class="sect">${esc(t("collection_point"))}</h2><div class="tiles">${COLLECTION_KINDS.map((k) => tile(k, "collect")).join("")}</div>
    <h2 class="sect">${esc(t("partner_finance"))}</h2><div class="tiles">${FINANCE_PRODUCTS.map((k) => tile(k, "finance")).join("")}</div></div>`;
}
function agentFlow(): string {
  const p = partner(), amount = toMinor(S.amount), fee = feeFor(amount), lim = combinedLimits(p.limits), r = S.reqs.find((x) => x.id === S.req);
  const isFinance = (FINANCE_PRODUCTS as readonly string[]).includes(S.svc);
  if (r) {
    const done = r.state === "confirmed", cashOut = r.service === "cash_withdrawal";
    return `${topBar(t(`svc_${r.service}`), "tab:services")}<div class="body"><div class="card center"><p class="amt">${esc(money(r.amount))}</p>${chip(r.state)}
      <p>${esc(t(r.state === "sent" ? "request_sent" : done ? "request_confirmed" : "request_failed"))}</p>${r.ref ? `<p class="sub">${esc(t("partner_ref"))}: ${esc(r.ref)}</p>` : ""}${r.reason ? `<p class="sub">${esc(r.reason)}</p>` : ""}
      ${done ? `<div class="kv"><span>${esc(t("commission"))}</span><strong>${esc(money(r.commission))}</strong></div>` : ""}</div>
      ${cashOut ? `<button class="primary inline" data-act="handcash" ${mayHandOverCash(r.state) ? "" : "disabled"}>${esc(t("hand_over_cash"))}</button><p class="note">${esc(t("never_before_confirmed"))}</p>` : ""}
      ${done ? `<button class="ghost inline" data-act="tab:services">${esc(t("close"))}</button>` : ""}</div>`;
  }
  return `${topBar(t(`svc_${S.svc}`), "tab:services")}<div class="body">
    <label class="field"><span>${esc(t("partner"))}</span><select data-in="partner">${PARTNERS.map((x) => `<option value="${x.id}" ${x.id === p.id ? "selected" : ""}>${esc(t(x.name))}</option>`).join("")}</select></label>
    <label class="field"><span>${esc(t("customer_number"))}</span><input inputmode="tel" autocomplete="off" data-in="anum" id="anumIn" value="${esc(S.number)}"></label>
    ${isFinance ? "" : `<label class="field"><span>${esc(t("amount"))}</span><input inputmode="numeric" autocomplete="off" data-in="aamt" id="aamtIn" value="${esc(S.amount)}"></label>
    <div class="card"><div class="kv"><span>${esc(t("fee"))}</span><strong>${esc(money(fee))}</strong></div><div class="kv"><span>${esc(t("commission"))}</span><strong>${esc(money(commission(amount, p.bps)))}</strong></div>
      <p class="sub">${esc(t("limit_line", { per: money(lim.per_transaction), day: money(lim.per_day) }))}</p></div>
    ${amount && limitCheck(amount, S.usedToday, lim) !== "ok" ? `<p class="alert neg" role="alert">${icon("ui-warning")}<span>${esc(t("limit_exceeded"))}</span></p>` : ""}`}
    <p class="info">${icon("ui-info")}<span>${esc(t(isFinance ? "referred" : "identity_check"))}</span></p>
    ${online() ? "" : `<p class="alert low">${icon("ui-offline")}<span>${esc(t("online_only"))}</span></p>`}
    <button class="primary inline" data-act="agentsend" ${online() && S.number.length >= 4 && (isFinance || (amount > 0 && limitCheck(amount, S.usedToday, lim) === "ok")) ? "" : "disabled"}>${esc(t("send_to_partner"))}</button></div>`;
}
function agentFloat(): string {
  return `${topBar(t("float"))}<div class="body">${PARTNERS.map((p) => { const days = floatForecastDays(p.float, usual(p));
    return `<div class="card"><h2>${esc(t(p.name))}</h2><div class="kv"><span>${esc(t("float"))}</span><strong>${esc(money(p.float))}</strong></div>${lowFloat(p.float, usual(p)) ? `<p class="alert low">${icon("ui-warning")}<span>${esc(t("low_float"))}</span></p>` : ""}
      ${days !== null ? `<p class="sub">${esc(t("float_forecast", { days: days.toFixed(1) }))}</p>` : ""}</div>`; }).join("")}
    <div class="card"><div class="kv"><span>${esc(t("cash_in_drawer"))}</span><strong>${esc(money(S.cashIn))}</strong></div><button class="ghost" data-act="tab:business">${esc(t("count_cash"))}</button></div><p class="info">${icon("ui-info")}<span>${esc(t("float_read_live"))}</span></p></div>`;
}
function agentSend(): void {
  if (!online() || webRule("agent_service", true) !== "ok") return;
  const p = partner(), isFinance = (FINANCE_PRODUCTS as readonly string[]).includes(S.svc), amount = isFinance ? 0 : toMinor(S.amount);
  const r: AgentReq = { id: newId(), partner: p.id, service: S.svc, number: S.number, amount, fee: feeFor(amount), commission: 0, state: "sent", ref: "", reason: "", at: Date.now() };
  S.reqs.unshift(r); S.req = r.id;
  if (isFinance) emit("PartnerReferralRecorded", { referral_id: r.id, partner_id: p.id, product: S.svc, fee: 0, currency: pack().currency }, "server");
  else emit("AgentRequestCreated", { request_id: r.id, partner_id: p.id, service: (AGENT_SERVICES as readonly string[]).includes(S.svc) ? S.svc : S.svc === "voucher" || S.svc === "pickup" ? "bills" : S.svc, amount, fee: r.fee, currency: pack().currency, customer_reference: "ref-" + S.number.slice(-4) });
  draw();
  window.setTimeout(() => {
    if (isFinance) { r.state = "confirmed"; draw(); return; }
    if (!online()) { r.state = "failed"; r.reason = t("request_failed"); emit("AgentRequestFailed", { request_id: r.id, reason_code: "timeout" }, "server"); draw(); return; }
    const out = S.svc === "cash_deposit" ? 0 : amount;
    if (S.outcome === "fail" || out > p.float) { r.state = "failed"; r.reason = t(out > p.float ? "low_float" : "request_failed"); emit("AgentRequestFailed", { request_id: r.id, reason_code: out > p.float ? "insufficient_float" : "partner_declined" }, "server"); draw(); return; }
    r.state = "confirmed"; r.ref = `SBX-${r.id.slice(-8).toUpperCase()}`; r.commission = commission(amount, p.bps); S.usedToday += amount;
    p.float += S.svc === "cash_deposit" ? amount : -amount;
    if (S.svc === "cash_deposit") S.cashIn += amount + r.fee; else S.cashIn += r.fee;
    emit("AgentRequestConfirmed", { request_id: r.id, partner_reference: r.ref, amount, fee: r.fee, commission: r.commission, currency: pack().currency }, "server");
    emit("CommissionRecorded", { commission_id: newId(), request_id: r.id, partner_id: p.id, amount: r.commission, currency: pack().currency, period: new Date().toISOString().slice(0, 10) }, "server");
    draw();
  }, reduced() ? 300 : 2200);
}

function syncSheet(): string {
  const p = pending(S.events.map((e) => e.sync)), off = !online();
  return `<div class="scrim" data-act="closesheet"><div class="sheet" role="dialog" aria-modal="true" aria-label="${esc(t("sync"))}" data-stop="1"><h2>${esc(t("sync"))}</h2>
    <p class="info">${icon(off ? "ui-offline" : "ui-sync")}<span>${esc(t(off ? "offline" : "online"))}</span></p>
    <div class="kv"><span>${esc(p.count ? t("waiting_send", { n: p.count }) : t("all_sent"))}</span>${chip(p.state)}</div>
    <div class="kv"><span>${esc(t("last_sync"))}</span><strong>${esc(S.lastSync ? clock(S.lastSync) : t("not_yet"))}</strong></div>
    ${S.link === "weak" && !S.forced ? `<p class="info">${icon("ui-info")}<span>${esc(t("weak_note"))}</span></p>` : ""}
    <label class="switch"><span>${esc(t("stay_offline"))}</span><input type="checkbox" data-in="forced" ${S.forced ? "checked" : ""}></label>
    <p class="info">${icon("ui-info")}<span>${esc(t("needs_net"))}</span></p>
    <button class="primary" data-act="closesheet">${esc(t("close"))}</button></div></div>`;
}

function signin(): string {
  const mark = `<span class="mark" role="img" aria-label="LynkOmni">${logo()}</span>`;
  if (S.screen === "phone") {
    return `<div class="signin">${mark}<h1>${esc(t("welcome"))}</h1><p>${esc(t("works_anywhere"))}</p>
      <label class="field"><span>${esc(t("your_phone"))}</span><input id="phoneIn" inputmode="tel" autocomplete="off" value="${esc(S.phone)}" data-in="phone"></label>
      <p class="note" role="alert">${esc(S.note)}</p><div class="grow"></div><button class="primary" data-act="sendcode" ${S.phone.replace(/\D/g, "").length >= 9 ? "" : "disabled"}>${esc(t("send_code"))}</button></div>`;
  }
  if (S.screen === "code") {
    return `<div class="signin">${mark}<h1>${esc(t("verify"))}</h1><p>${esc(t("enter_code", { phone: S.phone }))}</p>
      <label class="field"><span>${esc(t("verify"))}</span><input id="codeIn" inputmode="numeric" autocomplete="one-time-code" value="${esc(S.code)}" data-in="code"></label>
      <p class="note" role="alert">${esc(S.note)}</p><p class="info sbx">${icon("ui-info")}<span>${esc(t("sandbox"))}: ${esc(t("code_hint"))}</span></p><div class="grow"></div>
      <button class="primary" data-act="verify" ${S.code.length === 6 ? "" : "disabled"}>${esc(t("verify"))}</button></div>`;
  }
  return `<div class="signin">${mark}${S.enrolled ? `<h1>${esc(t("welcome"))}</h1><p>${esc(t("registered"))}</p><div class="grow"></div><button class="primary" data-act="start">${esc(t("start"))}</button>`
    : `<h1>${esc(t("registering"))}</h1><div class="center"><div class="spinner" aria-hidden="true"></div></div>`}</div>`;
}

function view(): string {
  if (S.screen !== "app") return signin();
  const agent = S.btype === "agent_point";
  const body = S.view === "svc" ? agentFlow() : S.tab === "services" ? agentServices() : S.tab === "float" ? agentFloat() : agent && S.tab === "home" ? agentHome()
    : S.tab === "sell" ? sell() : S.tab === "stock" ? stock() : S.tab === "chats" ? chats() : S.tab === "business" ? business() : home();
  const noTabs = S.tab === "sell" && S.view !== "main" && S.view !== "done" || S.tab === "chats" && S.view === "thread" || S.view === "svc";
  return `${body}${noTabs ? "" : tabBar()}${S.sheet ? syncSheet() : ""}`;
}

function draw(): void {
  const d = $("#display");
  const focus = document.activeElement instanceof HTMLInputElement && d.contains(document.activeElement) ? { id: document.activeElement.id, at: document.activeElement.selectionStart } : null;
  d.className = `display ${S.theme}`;
  d.lang = S.lang === "xx-rtl" ? "ar" : S.lang === "xx" ? "en" : S.lang;
  d.dir = S.lang === "xx-rtl" ? "rtl" : S.lang === "xx" ? "ltr" : PACKS[S.lang]?.dir ?? "ltr";
  $("#app").innerHTML = view();
  if (focus?.id) { const el = document.getElementById(focus.id) as HTMLInputElement | null; if (el) { el.focus(); if (focus.at !== null) el.setSelectionRange(focus.at, focus.at); } }
  drawStatus();
}
function drawStatus(): void {
  const bars = S.link === "good" ? 4 : S.link === "weak" ? 1 : 0;
  $("#statusbar").innerHTML = `<span class="time">${esc(clock(Date.now()))}</span><span class="cam" aria-hidden="true"></span>${S.realUser ? "" : `<span class="chip st-queued">${esc(t("sandbox"))}</span>`}
    <span class="bars" aria-hidden="true">${[0, 1, 2, 3].map((i) => `<i class="${i < bars ? "" : "off"}"></i>`).join("")}</span><span class="batt" aria-hidden="true"><i></i></span>`;
}
function drawLog(): void {
  $("#log").innerHTML = S.events.slice(0, 40).map((e) => `<li><span class="n">#${e.n}</span><code>${esc(e.type)}</code><span class="org">${e.origin}</span>${chip(e.sync)}
    <details><summary>payload</summary><pre>${esc(JSON.stringify(e.payload, null, 1))}</pre></details></li>`).join("") || `<li class="empty">No events yet. Sign in and make a sale.</li>`;
}

// ---- sign-in and device registration ----------------------------------------------------------------------------------
async function enrol(): Promise<void> {
  S.screen = "enrol"; draw();
  let raw: Uint8Array;
  try {   // a real P-256 key pair; the private key never leaves the phone (hardware-backed keys come with the native apps)
    const k = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, false, ["sign", "verify"]);
    raw = new Uint8Array(await crypto.subtle.exportKey("raw", k.publicKey));
  } catch { raw = new Uint8Array([4, ...randomBytes(64)]); }
  const b64 = btoa(String.fromCharCode(...raw)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  window.setTimeout(() => {
    emit("DeviceEnrolled", { device_id: newId(), device_name: "Sample phone", platform: "android", public_key: b64, enrolled_by_user_id: newId() }, "server");
    S.enrolled = true; draw();
  }, reduced() ? 0 : 700);
}

function act(a: string): void {
  const [k, v = ""] = a.split(/:(.*)/s);
  try {
    switch (k) {
      case "sendcode": if (!maySync(S.link, S.forced)) { S.note = t("code_needs_net"); draw(); return; } S.note = ""; S.screen = "code"; draw(); return;
      case "verify": if (S.code === CODE) { S.note = ""; void enrol(); } else { S.note = t("wrong_code"); S.code = ""; draw(); } return;
      case "start": S.screen = "app"; S.tab = "home"; S.view = "main"; draw(); return;
      case "tab": S.tab = pick(["home", "sell", "stock", "chats", "business", "services", "float"] as Tab[], v, "home"); S.view = "main"; S.note = ""; S.req = "";
        if (S.tab === "float") for (const p of PARTNERS) emit("FloatBalanceRead", { partner_id: p.id, balance: p.float, currency: pack().currency, read_at: new Date().toISOString().slice(0, 19) + "Z" }, "server");
        draw(); return;
      case "svc": S.svc = pick(AGENT_ALL as readonly string[], v, "bills"); S.view = "svc"; S.req = ""; S.amount = ""; S.number = ""; draw(); return;
      case "agentsend": agentSend(); return;
      case "handcash": { const r = S.reqs.find((x) => x.id === S.req); if (r && mayHandOverCash(r.state)) { S.cashIn -= r.amount; toast(t("done")); } return; }
      case "view": S.view = v as View; S.input = ""; S.note = ""; draw(); return;
      case "sheet": S.sheet = true; draw(); return;
      case "closesheet": S.sheet = false; draw(); return;
      case "newsale": newSale(); return;
      case "cat": S.category = v; draw(); return;
      case "add": { const p = item(v); if (p) S.cart.add(p); draw(); return; }
      case "inc": { const l = S.cart.lines().find((x) => x.product.id === v); if (l) S.cart.setQty(v, l.qtyMilli + 1000); draw(); return; }
      case "dec": { const l = S.cart.lines().find((x) => x.product.id === v); if (l) S.cart.setQty(v, l.qtyMilli - 1000); if (!S.cart.lines().length) S.view = "main"; draw(); return; }
      case "method": { const m = v as PaymentMethod; S.input = ""; S.view = !methodOk(m) ? "off" : m === "cash" ? "cash" : "momo"; draw(); return; }
      case "cash": S.input = v; draw(); return;
      case "paycash": { const g = Number(S.input || "0"); if (g >= S.cart.total()) pay("cash", g); return; }
      case "paymomo": pay("mobile_money"); return;
      case "retry": { const s = S.current, p = lastPayment(); if (s && p) { const q = paymentPayload(newId(), s.sale.sale_id, p.method, s.sale.total); s.payments.push(q); emit("PaymentRecorded", q); S.view = "waiting"; draw(); } return; }
      case "notify": S.notified.add(v); toast(t("notify_done")); return;
      case "product": S.product = v; S.qty = 1; S.tab = "stock"; S.view = "item"; draw(); return;
      case "qty": S.qty = Math.max(1, S.qty + Number(v)); draw(); return;
      case "stock": stockAct(v); return;
      case "thread": { S.thread = v; S.view = "thread"; const th = S.threads.find((x) => x.id === v); if (th) th.unread = 0; draw(); return; }
      case "send": sendMsg(); return;
    }
  } catch (e) { S.note = e instanceof PosError ? e.reason : String(e); draw(); }
}

// ---- controls beside the phone ---------------------------------------------------------------------------------------
function wire(): void {
  document.addEventListener("click", (ev) => {
    const target = ev.target as HTMLElement;
    const el = target.closest<HTMLElement>("[data-act]");
    if (!el || (el as HTMLButtonElement).disabled) return;
    if (el.dataset["act"] === "closesheet" && el.classList.contains("scrim") && target.closest("[data-stop]")) return;   // taps inside the sheet
    act(el.dataset["act"] ?? "");
  });
  const display = $("#display");
  display.addEventListener("input", (ev) => {
    const el = ev.target as HTMLInputElement, k = el.dataset["in"];
    if (k === "cash") { S.input = el.value.replace(/\D/g, "").slice(0, 9); draw(); }
    else if (k === "momo") { S.input = el.value.replace(/[^\d ]/g, "").slice(0, 15); draw(); }
    else if (k === "phone") { S.phone = el.value.replace(/[^\d +]/g, "").slice(0, 16); draw(); }
    else if (k === "code") { S.code = el.value.replace(/\D/g, "").slice(0, 6); draw(); }
    else if (k === "msg") S.draft = el.value.slice(0, 500);
    else if (k === "anum") { S.number = el.value.replace(/[^\d ]/g, "").slice(0, 16); draw(); }
    else if (k === "aamt") { S.amount = el.value.replace(/\D/g, "").slice(0, 9); draw(); }
  });
  display.addEventListener("change", (ev) => {
    const el = ev.target as HTMLInputElement, k = el.dataset["in"];
    if (k === "perm" && canChangeSettings(S.role)) { S.perms = { staffSeeProfit: el.checked }; draw(); }
    if (k === "forced") { S.forced = el.checked; draw(); }
    if (k === "partner") { S.partner = pick(PARTNERS.map((p) => p.id), el.value, "pa"); draw(); }
  });
  display.addEventListener("keydown", (ev) => {
    const el = ev.target as HTMLElement;
    if (ev.key === "Enter" && el.dataset["in"] === "msg") { S.draft = (el as HTMLInputElement).value; sendMsg(); ev.preventDefault(); }
    if (ev.key === "Escape" && S.sheet) { S.sheet = false; draw(); }
  });
  const bind = (id: string, f: (el: HTMLInputElement & HTMLSelectElement) => void): void => { const el = $<HTMLInputElement & HTMLSelectElement>(id); el.addEventListener("change", () => f(el)); };
  bind("#cLink", (el) => { S.link = el.value as Link; draw(); });
  bind("#cRole", (el) => { S.role = el.value as Role; draw(); });
  bind("#cType", (el) => { S.btype = el.value === "agent_point" ? "agent_point" : "shop"; S.tab = "home"; S.view = "main"; draw(); });
  bind("#cDark", (el) => { S.theme = el.checked ? "dark" : "light"; draw(); });
  bind("#cReal", (el) => { S.realUser = el.checked; draw(); });
  const country = $<HTMLSelectElement>("#cCountry");
  country.innerHTML = DATA.packOrder.map((c) => { const p = DATA.packs[c] as CountryPack; return `<option value="${esc(c)}">${esc(p.sample ? t("sample_country") : p.name)}</option>`; }).join("");
  country.addEventListener("change", (e) => { S.country = (e.target as HTMLSelectElement).value; draw(); });
  bind("#cFail", (el) => { S.outcome = el.checked ? "fail" : "confirm"; });
  const sel = $<HTMLSelectElement>("#cLang");
  sel.insertAdjacentHTML("afterbegin", Object.entries(PACKS).map(([code, p]) => `<option value="${esc(code)}" lang="${esc(code)}" dir="${p.dir}">${esc(p.native)}</option>`).join(""));
  sel.value = "en";
  sel.addEventListener("change", () => { S.lang = sel.value; draw(); });
  const fit = (): void => {   // scale the whole phone down on small screens, never up
    const s = Math.min(1, ($("#rig").clientWidth - 8) / $("#device").offsetWidth);
    document.documentElement.style.setProperty("--fit", String(s));
  };
  addEventListener("resize", fit); fit();
  window.setInterval(tick, 350);
  window.setInterval(drawStatus, 30000);
}

wire(); draw(); drawLog();
