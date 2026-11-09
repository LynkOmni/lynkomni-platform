/** LynkOmni Business app on a phone or a tablet (blueprint 41 E, with 5, 7, 42 C, 42 I and 44 L row 3). Draws an original LynkOmni
 *  phone (or tablet) and runs the Business app inside it exactly as 41 E lays it out: getting in (sign in, choose the business,
 *  register this device, the language and region card, the setup checklist, the first sale), the top bar (emblem, screen title,
 *  connection chip, notifications, account), tabs by business type (a side rail on a tablet), Sell with every payment method and
 *  receipt, today's sales, shifts, practice mode, Stock, Chats and every Business section and setting. Every screen is listed in
 *  catalog/business-app.v1.json with its address; tests/test_business_app.py checks the emulator shows each one. Rules come from
 *  ts/src/pos.ts, merchant.ts, business.ts and agent.ts; payments and the cloud are sandboxes (test money only).
 *  Draft until a designer reviews it. Built into one offline HTML file by web/build.mjs; colours only from the design tokens. */
import { Cart, PosError, change, formatMoney, paymentPayload, paymentState, qtyText, quickCash, salePayload } from "../../../ts/src/pos.js";
import type { PaymentMethod, PaymentPayload, PaymentStatus, Product, SalePayload, UserState } from "../../../ts/src/pos.js";
import { adjust, afterSale, canChangeSettings, canSeeProfit, counted, daySummary, homeBlocks, insight, maySync, mode, pending, stockAlerts, stockState } from "../../../ts/src/merchant.js";
import type { DaySale, Levels, Link, Role, StockItem } from "../../../ts/src/merchant.js";
import { CHAT_FILTERS, COUNT_KINDS, FIRST_PRODUCT_WAYS, HUB, PAY_WAYS, REMOVE_REASONS, RETURN_REASONS, SETTINGS, SETUP_CHECKLIST, STOCK_FILTERS, TABS, THREAD_ACTIONS, VOID_REASONS,
  creditNeedsCustomer, moveStock, nextChecklistStep, parseVoice, payWay, receiptOptions, returnLine, secondCurrency, splitCheck, stockFilter, webRule } from "../../../ts/src/business.js";
import type { BusinessType, ChecklistStep, PosEntitlement, Entity, Workspaces } from "../../../ts/src/business.js";
import { workspaceTabs, workspaceWord } from "../../../ts/src/business.js";
import { Tracking } from "../../../ts/src/tracking.js";
import type { View as TrackView } from "../../../ts/src/tracking.js";
import { REGISTER } from "../../../ts/src/tracking.generated.js";
import { trackerHtml, trackerLine } from "../../../ts/src/trackview.js";
import { AGENT_SERVICES, COLLECTION_KINDS, FINANCE_PRODUCTS, combinedLimits, commission, floatForecastDays, limitCheck, lowFloat, mayHandOverCash } from "../../../ts/src/agent.js";
import type { AgentState, Limits } from "../../../ts/src/agent.js";
import { TEST_LANGS, esc, newId, pick, pseudo, publicId, randomBytes } from "../../../ts/src/emulator.js";
import { brandMark } from "../../../ts/src/brand.js";
import { shortFooterHtml } from "../../../ts/src/footer.js";
import { check } from "../../../ts/src/usernames.js";
import { kitchenOutput, mayOpenTable, restaurantLimits } from "../../../ts/src/restaurant.js";
import type { BrandPlaces } from "../../../ts/src/brand.js";
import { DeviceShell, screenArticles } from "../../../ts/src/deviceshell.js";
import type { Entry } from "../../../ts/src/shell.js";

interface BuildData {
  icons: Record<string, string>;
  brand: { body: string; receipt: string; places: BrandPlaces };
  pictures: { offLight: string; offDark: string; offAlt: string };
  agentPicture: { light: string; dark: string };
  states: Record<string, { label: string; meaning: string }>;
  /** Every country pack, the neutral sample pack first (Step 0): the chooser never opens on a real country. */
  packs: Record<string, CountryPack>;
  packOrder: string[];
  i18n: Record<string, { native: string; dir: "ltr" | "rtl"; texts: Record<string, string> }>;
  entitlements: Record<string, PosEntitlement>;
  fx: Record<string, number>;
  screens: { id: string; path: string; items: string[] }[];
  /** LynkPOS standard monthly prices in USD by tier, from services/billing.py FAMILIES (locked prices, version 3). */
  plans: number[];
  automations: { id: string; level: string }[];
  /** who the app is for (catalog/workspaces.v1.json): a person, a company or an organisation */
  workspaces: Workspaces;
}
interface CountryPack {
  code: string; name: string; currency: string; tz: string; locale: string; sample: boolean;
  ready: Record<string, { ok: boolean; message: string }>;
  services: { service: string; name: string; icon: string; state: "available" | "coming_soon" }[];
}
declare const DATA: BuildData;
/** The country the emulator shows. Read from the country pack and the provider ledger; nothing about a country lives in this code. */
const pack = (): CountryPack => DATA.packs[S.country] ?? DATA.packs[DATA.packOrder[0] ?? ""] as CountryPack;

type Tab = "home" | "sell" | "stock" | "chats" | "business" | "services" | "float" | "invoices" | "customers" | "tables" | "kitchen" | "books";
/** One name per screen of the register (catalog/business-app.v1.json), plus the in-between steps of a flow. */
type View = "main" | "basket" | "pay" | "cash" | "momo" | "split" | "credit" | "waiting" | "done" | "receipt" | "off" | "sales" | "sale" | "shift" | "practice"
  | "item" | "add" | "received" | "count" | "remove" | "move" | "suppliers" | "reorder" | "marketplace" | "labels" | "import" | "thread" | "svc" | "deliveries" | "delivery"
  | "notifications" | "account" | "hub" | "setting" | "cashcheck";
/** Agent point mode (blueprint 42 C and 42 I): the sample partners are sandbox partners; the float sits in the agent's own
 *  account at each partner and is only read from it. The device asks; the partner alone confirms. */
interface Partner { id: string; name: string; float: number; limits: Limits; bps: number }
interface AgentReq { id: string; partner: string; service: string; number: string; amount: number; fee: number; commission: number; state: AgentState; ref: string; reason: string; at: number; outlet: string; receipt: string }
interface Table { id: string; label: string; open: boolean; lines: { order: string; no: number; product: string; ready: boolean; at: number }[] }
interface Invoice { id: string; number: string; customer: string; amount: number; state: UserState }
const PARTNERS: Partner[] = [{ id: newId(), name: "partner_a", float: 400_000, limits: { per_transaction: 200_000, per_day: 2_000_000 }, bps: 100 }, { id: newId(), name: "partner_b", float: 30_000, limits: { per_transaction: 100_000, per_day: 1_000_000 }, bps: 120 }];
const AGENT_ALL = [...AGENT_SERVICES, ...COLLECTION_KINDS, ...FINANCE_PRODUCTS] as const;
interface Ev { n: number; type: string; origin: "device" | "server"; payload: unknown; sync: UserState; at: number }
interface Sale extends DaySale { at: number; tendered?: number; customer?: string; note?: string; returned: number }
interface Msg { out: boolean; text: string; at: number; state: UserState; card?: { kind: string; label: string }; lang?: string }
interface Thread { id: string; name: string; msgs: Msg[]; unread: number; order: boolean; assigned: string; lang: string; support?: boolean }
interface Item extends Product, StockItem { unit: string; variants: string[]; branch: string; supplier: string }
interface Customer { id: string; name: string; owes: number }
/** A delivery booked from a sale: the shop's own rider or a partner; its steps come from the tracking engine. */
interface Delivery { id: string; pid: string; order: string; receipt: string; own: boolean; timer: number }
interface Staff { id: string; name: string; role: Role; pin: boolean }
interface Notice { id: string; key: string; vars: Record<string, string | number>; at: number; read: boolean }

/** Screen words: English in strings.en.json, every other language from the packs in i18n/<lang>.json (translated by Claude and
 *  checked by tools/translation/claude_packs.py), all embedded by web/build.mjs so every language works offline. */
const PACKS = DATA.i18n;
const EN: Record<string, string> = PACKS.en?.texts ?? {};

const P = (milli: number): number => milli * 1000;
const CATALOG: Item[] = ([
  ["Rice 1 kg", 1500, 1150, "food", 10, "6001234500017", "kg", "main", "s1"], ["Sugar 1 kg", 1400, 1100, "food", 8, "6001234500024", "kg", "main", "s1"], ["Beans 1 kg", 1200, 900, "food", 10, "6001234500031", "kg", "main", "s1"],
  ["Cooking oil 1 L", 3200, 2600, "food", 5, "6001234500048", "l", "main", "s2"], ["Bread", 1000, 700, "food", 6, "6001234500055", "pc", "main", "s2"], ["Eggs, tray of 30", 4500, 3800, "food", 3, "6001234500062", "pc", "north", "s2"],
  ["Milk 500 ml", 600, 420, "drinks", 10, "6001234500079", "pc", "main", "s2"], ["Water 1.5 L", 700, 450, "drinks", 12, "6001234500086", "pc", "main", "s1"], ["Soda 300 ml", 500, 330, "drinks", 12, "6001234500093", "pc", "north", "s1"],
  ["Tea leaves 100 g", 900, 600, "drinks", 5, "6001234500109", "pc", "main", "s1"], ["Soap bar", 500, 320, "home", 6, "6001234500116", "pc", "main", "s2"], ["Matches, pack", 300, 180, "home", 10, "6001234500123", "pc", "north", "s2"],
] as const).map(([name, price, cost, category, reorder, barcode, unit, branch, supplier]) => { const id = newId(); return { id, productId: id, name, price, cost, category, reorderAtMilli: P(reorder), barcode, unit, variants: [], branch, supplier }; });
const START: Levels = Object.fromEntries(CATALOG.map((p, i) => [p.id, P([24, 6, 30, 2, 12, 1, 20, 36, 40, 15, 18, 50][i] ?? 0)]));
const COSTS = Object.fromEntries(CATALOG.map((p) => [p.id, p.cost]));
const NOTES = [500, 1000, 2000, 5000, 10000];
const BUSINESSES = ["Sample shop", "Sample shop, north branch"];
const BRANCHES = ["main", "north"];
const SUPPLIERS = [{ id: "s1", name: "Sample mill" }, { id: "s2", name: "Sample drinks company" }];
const DEVICE = "MP";
const CODE = "123456";
const ago = (min: number): number => Date.now() - min * 60_000;
const CUSTOMERS: Customer[] = [{ id: newId(), name: "Aline", owes: 0 }, { id: newId(), name: "Eric", owes: 4500 }, { id: newId(), name: "Grace", owes: 0 }];
const THREADS: Thread[] = [
  { id: publicId("CNV"), name: "LynkOmni Support", unread: 0, order: false, assigned: "", lang: "en", support: true, msgs: [{ out: false, text: "support_welcome", at: ago(600), state: "accepted" }] },
  { id: publicId("CNV"), name: "Aline", unread: 1, order: false, assigned: "", lang: "fr", msgs: [{ out: false, text: "Do you have cooking oil today?", at: ago(12), state: "accepted", lang: "fr", card: { kind: "product", label: "Cooking oil 1 L" } }] },
  { id: publicId("CNV"), name: "Eric", unread: 1, order: true, assigned: "", lang: "en", msgs: [{ out: false, text: "Can you keep 2 trays of eggs for me until 5 pm?", at: ago(40), state: "accepted", card: { kind: "order", label: "ORD" } }] },
  { id: publicId("CNV"), name: "Grace", unread: 0, order: false, assigned: "me", lang: "en", msgs: [{ out: false, text: "Thank you for the delivery!", at: ago(180), state: "accepted" }, { out: true, text: "You are welcome. See you soon.", at: ago(175), state: "sent" }] },
];
const SAVED_REPLIES = ["reply_open", "reply_kept", "reply_thanks"];
const TIERS = ["free", "plus", "pro", "max"] as const;

const S = {
  screen: "phone" as "phone" | "code" | "enrol" | "choose" | "locale" | "setup" | "app", tab: "home" as Tab, view: "main" as View, sheet: false,
  size: "phone" as "phone" | "tablet" | "web", tier: "free" as (typeof TIERS)[number],
  btype: "shop" as BusinessType, business: 0, setupDone: new Set<string>(), setupSkipped: new Set<string>(), shopName: "", firstWay: "",
  svc: "bills" as string, partner: PARTNERS[0]?.id ?? "", number: "", amount: "", reqs: [] as AgentReq[], req: "", cashIn: 150_000, usedToday: 0, outlet: "all", outletList: ["Main outlet", "Market outlet"], cashChecks: new Set<string>(),
  lang: "en", theme: "light" as "light" | "dark", link: "good" as Link, forced: false, realUser: false, country: "", outcome: "confirm" as "confirm" | "fail" | "silent",
  role: "owner" as Role, perms: { staffSeeProfit: false }, phone: "", code: "", input: "", note: "", flash: "", category: "all", search: "",
  cart: new Cart(), current: null as Sale | null, sales: [] as Sale[], events: [] as Ev[], levels: { ...START } as Levels, flagged: new Set<string>(),
  branchLevels: {} as Record<string, Record<string, number>>,
  discount: 0, saleNote: "", customer: "", parts: [] as { way: string; amount: number }[], receiptWay: "",
  selected: "", reason: "", returnQty: 1, restock: true,
  shift: null as null | { id: string; float: number; openedAt: number }, countKind: "day_end" as (typeof COUNT_KINDS)[number], practice: false, practiceFloat: 50_000,
  stockFilter: "all" as (typeof STOCK_FILTERS)[number], branch: "all", moveTo: "north", addWay: "scan", countMode: "full" as "full" | "partial",
  threads: THREADS, thread: "", draft: "", chatFilter: "all" as (typeof CHAT_FILTERS)[number], showOriginal: false,
  product: "", qty: 1, notified: new Set<string>(), receiptNo: 0, lastSync: 0, ticks: 0, enrolled: false,
  hub: "", setting: "", notices: [] as Notice[], staff: [{ id: newId(), name: "Owner", role: "owner", pin: true }, { id: newId(), name: "Aline", role: "cashier", pin: true }] as Staff[],
  orders: [] as { id: string; supplier: string; lines: number; state: "draft" | "sent" }[], shared: new Set<string>(), passport: false, englishOnce: false,
  invoices: [] as Invoice[], tables: [] as Table[], devices: [] as { id: string; name: string; revoked: boolean }[], runs: [] as { auto: string; at: number }[], autoOff: new Set<string>(),
  toggles: new Set<string>(["n_sales", "n_stock", "n_chats", "pin_lock", "idle_lock", "receipt_qr", "ads_never_protected"]), username: "", userDraft: "", takenNames: new Set<string>(["sampleshop"]),
  ask: "", answer: "", clockedIn: false, clockId: "", staffPhone: "", supplier: "s1", lynkTail: "7715",
  entity: "company" as Entity, kind: "business", deliveries: [] as Delivery[], delivery: "",
};
/** Every tracked thing on this phone (deliveries, kitchen orders, payments, agent requests) follows the shared engine (ts/src/tracking.ts). */
const TRK = new Tracking(REGISTER);

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
const ent = (): PosEntitlement => DATA.entitlements[S.tier] ?? {};
/** A payment way works when it needs no partner, or its partner is signed for the chosen country (the provider ledger, via the pack). */
const wayOk = (id: string): boolean => { const w = payWay(id); if (!w || !w.provider) return true; if (!S.realUser) return true; return pack().ready[w.provider]?.ok ?? pack().ready[w.method]?.ok ?? false; };
const item = (id: string): Item | undefined => CATALOG.find((p) => p.id === id);
const level = (id: string): number => S.levels[id] ?? 0;
const unread = (): number => S.threads.reduce((a, th) => a + th.unread, 0);
const unreadNotices = (): number => S.notices.filter((n) => !n.read).length;
const shop = (): string => S.shopName || BUSINESSES[S.business] || "";
const toast = (msg: string): void => { S.flash = msg; draw(); window.setTimeout(() => { S.flash = ""; draw(); }, 1600); };
const notice = (key: string, vars: Record<string, string | number> = {}): void => { S.notices.unshift({ id: newId(), key, vars, at: Date.now(), read: false }); };
/** Every automation run is shown in history with "Why did this happen?" (45 D); ids come from catalog/automations.v1.json. */
const run = (auto: string): void => { if (!S.autoOff.has(auto)) S.runs.unshift({ auto, at: Date.now() }); };
const key = (id: string): string => id.replace(/-/g, "_");
/** A language's name in the reader's language, from the browser (no name table in the file). */
const langName = (code: string): string => { try { return new Intl.DisplayNames([isTest() ? "en" : S.lang], { type: "language" }).of(code) ?? code; } catch { return code; } };
const cust = (id = S.customer): Customer | undefined => CUSTOMERS.find((c) => c.id === id);
const total = (): number => Math.max(0, S.cart.total() - S.discount);
/** The address of the screen shown (41 B deep links), from the register. */
function address(): string {
  const id = screenId(), p = DATA.screens.find((s) => s.id === id)?.path ?? "/";
  if (p.startsWith("account.")) return p;
  const dl = S.deliveries.find((x) => x.id === S.delivery) ?? S.deliveries[0];
  return `app.lynkomni.com${p.replace("{product_id}", S.product || "new").replace("{LOCNV}", S.thread || "").replace("{LODLV}", dl?.pid ?? "")}`;
}

// ---- event log and the simulated cloud --------------------------------------------------------------------------
/** Practice mode (7): a clearly marked training copy; nothing it does is real and nothing is sent. */
function emit(type: string, payload: unknown, origin: "device" | "server" = "device"): Ev {
  const e: Ev = { n: S.events.length + 1, type, origin, payload, sync: origin === "server" ? "accepted" : "queued", at: Date.now() };
  if (S.practice) return e;
  S.events.unshift(e); TRK.apply({ type, payload: payload as Record<string, unknown>, at: e.at / 1000 }, "me"); drawLog(); return e;
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
      notice("n_below_zero", { product: item(l.product_id)?.name ?? "" }); run("negative-stock-flag");
    }
  }
}
const asking = new Set<string>();
/** The sandbox provider answers after a short wait: confirmed, failed, or (with "stays silent") never, so the payment stays sent. */
function askProvider(s: Sale, p: PaymentPayload): void {
  if (S.outcome === "silent") return;
  asking.add(p.payment_id);
  window.setTimeout(() => {
    asking.delete(p.payment_id);
    if (!online()) return;
    const to: PaymentStatus = S.outcome === "confirm" ? "confirmed" : "failed";
    emit("PaymentStatusChanged", { payment_id: p.payment_id, from_status: p.status, to_status: to, source: "provider_callback", provider_reference: `SBX-${p.payment_id.slice(-8).toUpperCase()}` }, "server");
    p.status = to;
    if (S.current === s && S.view === "waiting" && s.payments.every((x) => x.status !== "pending_confirmation")) S.view = s.payments.some((x) => x.status === "failed") ? "waiting" : "receipt";
    notice(to === "confirmed" ? "n_payment_confirmed" : "n_payment_failed", { amount: money(p.amount) });
    draw();
  }, reduced() ? 300 : 2600);
}

// ---- selling ------------------------------------------------------------------------------------------------------
function recordSale(): Sale {
  if (S.current) return S.current;
  S.receiptNo += 1;
  const sale = salePayload(S.cart, newId(), `${DEVICE}-${S.receiptNo}`, pack().currency);
  if (S.discount > 0) { sale.discount_total += S.discount; sale.total = Math.max(0, sale.total - S.discount); }   // a basket discount, as the contract's discount_total
  emit("SaleRecorded", sale);
  emit("ReceiptIssued", { receipt_id: newId(), sale_id: sale.sale_id, receipt_number_local: sale.receipt_number_local, copy_number: 1, validity: "provisional" });
  if (!S.practice) S.levels = afterSale(S.levels, sale);   // never blocked: stock may go below zero and is flagged instead
  const s: Sale = { sale, payments: [], voided: false, at: Date.now(), customer: S.customer || undefined, note: S.saleNote || undefined, returned: 0 };
  if (!S.practice) S.sales.unshift(s);
  S.current = s;
  return s;
}
/** Record one payment (or one part of a split). Cash and credit settle on the device; every other way waits for its provider. */
function payPart(wayId: string, amount: number, tendered?: number): PaymentPayload | null {
  const w = payWay(wayId); if (!w) return null;
  const s = recordSale();
  const p = paymentPayload(newId(), s.sale.sale_id, w.method as PaymentMethod, amount);
  s.payments.push(p); emit("PaymentRecorded", { ...p, currency: pack().currency });
  if (wayId === "credit") {
    const c = cust(); if (c) { c.owes += amount; emit("CustomerCreditRecorded", { credit_id: newId(), customer_id: c.id, sale_id: s.sale.sale_id, amount, currency: pack().currency }); }
  }
  if (wayId === "cash") s.tendered = tendered;
  return p;
}
function finishPay(): void {
  const s = S.current; if (!s) return;
  S.view = s.payments.some((p) => p.status === "pending_confirmation") ? "waiting" : "receipt";
  draw();
}
function newSale(): void { S.cart.clear(); S.current = null; S.input = ""; S.note = ""; S.discount = 0; S.saleNote = ""; S.customer = ""; S.parts = []; S.receiptWay = ""; S.tab = "sell"; S.view = "main"; draw(); }
const lastPayment = (): PaymentPayload | undefined => S.current?.payments[S.current.payments.length - 1];
function voidSale(reason: string): void {
  const s = S.sales.find((x) => x.sale.sale_id === S.selected); if (!s || s.voided) return;
  emit("SaleVoided", { sale_id: s.sale.sale_id, reason_code: pick(VOID_REASONS as readonly string[], reason, "other") });
  s.voided = true; toast(t("voided"));
}
function returnSale(reason: string): void {
  const s = S.sales.find((x) => x.sale.sale_id === S.selected); const l = s?.sale.lines[0]; if (!s || !l) return;
  const r = returnLine(l.quantity_milli, l.unit_price, P(S.returnQty));
  if (!r.quantity_milli) return;
  emit("ReturnRecorded", { return_id: newId(), sale_id: s.sale.sale_id, lines: [{ line_no: l.line_no, product_id: l.product_id, quantity_milli: r.quantity_milli, restock: S.restock, refund_amount: r.refund_amount }],
    refund_total: r.refund_amount, reason_code: pick(RETURN_REASONS as readonly string[], reason, "other"), currency: pack().currency });
  if (S.restock) S.levels = { ...S.levels, [l.product_id]: level(l.product_id) + r.quantity_milli };
  s.returned += r.refund_amount; toast(t("refund_recorded", { amount: money(r.refund_amount) }));
}

// ---- shifts and cash counts (42 I): differences are flagged for the owner, never blocking --------------------------------
const expectedCash = (): number => (S.shift?.float ?? 0) + daySummary(S.sales.filter((s) => s.at >= (S.shift?.openedAt ?? 0)), COSTS).cash;
function openShift(): void {
  const float = Number(S.input || "0");
  S.shift = { id: newId(), float, openedAt: Date.now() };
  emit("ShiftOpened", { shift_id: S.shift.id, float_amount: float, currency: pack().currency });
  S.input = ""; toast(t("shift_opened"));
}
function countCash(close: boolean): void {
  if (!S.shift) return;
  const got = Number(S.input || "0"), exp = expectedCash(), countId = newId();
  emit("CashCounted", { count_id: countId, shift_id: S.shift.id, kind: close ? "day_end" : S.countKind, counted_cash: got, expected_cash: exp, currency: pack().currency });
  if (got !== exp) { emit("CashDifferenceFlagged", { count_id: countId, difference: got - exp, currency: pack().currency }, "server"); notice("n_cash_difference", { amount: money(got - exp) }); run("cash-difference-flag"); }
  if (close) { emit("ShiftClosed", { shift_id: S.shift.id, counted_cash: got, expected_cash: exp, currency: pack().currency }); S.shift = null; }
  S.input = ""; toast(t(got === exp ? "no_difference" : "difference_flagged"));
}

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
  } else if (kind === "move") {
    S.branchLevels = moveStock({ [p.branch]: { [p.id]: level(p.id) }, [S.moveTo]: S.branchLevels[S.moveTo] ?? {} }, p.id, p.branch, S.moveTo, q);
    emit("StockAdjusted", { adjustment_id: newId(), product_id: p.id, delta_milli: -q, reason_code: "other", note: `move ${p.branch} > ${S.moveTo}` });
    emit("StockAdjusted", { adjustment_id: newId(), product_id: p.id, delta_milli: q, reason_code: "other", note: `move ${p.branch} > ${S.moveTo}` });
  } else {
    emit("StockAdjusted", { adjustment_id: newId(), product_id: p.id, delta_milli: -q, reason_code: pick(REMOVE_REASONS as readonly string[], kind, "other") });
    S.levels = adjust(S.levels, p.id, -q);
  }
  toast(t("saved"));
}
function addProduct(way: string): void {
  const id = newId(), name = t(`sample_new_${way}`);
  CATALOG.push({ id, productId: id, name, price: 800, cost: 500, category: "home", reorderAtMilli: P(3), barcode: way === "scan" ? "6001234500130" : undefined, unit: "pc", variants: [], branch: "main", supplier: "s1" });
  S.levels = { ...S.levels, [id]: 0 };
  emit("ProductCreated", { product_id: id, name, unit: "pc", price: 800, track_stock: true, currency: pack().currency, ...(way === "scan" ? { barcode: "6001234500130" } : {}) });
  S.product = id; S.view = "item"; toast(t("saved"));
}
function draftOrder(): void {
  const low = stockAlerts(CATALOG, S.levels); const ids = [...low.negative, ...low.low];
  const bySupplier = new Map<string, number>();
  for (const id of ids) { const s = item(id)?.supplier ?? "s1"; bySupplier.set(s, (bySupplier.get(s) ?? 0) + 1); }
  for (const [supplier, lines] of bySupplier) S.orders.unshift({ id: newId(), supplier, lines, state: "draft" });
  emit("AutomationDrafted", { run_id: newId() }, "server"); run("low-stock-reorder");   // the low-stock-reorder automation's draft (catalog/automations.v1.json)
  toast(t("drafted"));
}

// ---- chats (customer-business and support only; messages are a server-side module, not device events) ------------------------
function sendMsg(card?: { kind: string; label: string }): void {
  const th = S.threads.find((x) => x.id === S.thread); const text = card ? "" : S.draft.trim();
  if (!th || (!text && !card)) return;
  th.msgs.push({ out: true, text, at: Date.now(), state: maySync(S.link, S.forced) && S.link === "good" ? "sent" : "queued", card });
  S.draft = ""; draw();
}

// ---- shell parts (41 B) inside the Business app (41 E) ------------------------------------------------------------------
/** 41 E fixes the top bar at five parts (emblem, title, chip, notifications, account), so the 41 B parts sit around them
 *  (decided 9 November 2026): help (?) beside the screen title, "Find or do anything" as a search field on Home and the Business
 *  hub, the account menu and sync sheet stay the app's own (account screen, chip sheet) and the language card stays in getting in. */
const DSH = new DeviceShell({
  t, icon: (id) => icon(id), clock,
  screen: () => ({ id: screenId(), title: document.querySelector("#app .top h1")?.textContent?.trim() || t("tab_home"), path: address() }),
  articles: (id) => screenArticles(t, id, document.querySelector("#app .top h1")?.textContent?.trim() || t("tab_home")),
  entries: (): Entry[] => [
    { id: "new_sale", kind: "action", title: t("new_sale"), act: "newsale" },
    ...(TABS[S.btype] as readonly Tab[]).map((k): Entry => ({ id: `tab-${k}`, kind: "action", title: t(`tab_${k}`), act: `tab:${k}` })),
    ...HUB.map((h): Entry => ({ id: `hub-${h.id}`, kind: h.id === "reports" ? "report" : "setting", title: t("it_" + h.id), act: `hub:${h.id}` })),
    ...CATALOG.map((p): Entry => ({ id: p.id, kind: "product", title: t(p.name), subtitle: money(p.price), act: `product:${p.id}` })),
    ...CUSTOMERS.map((c): Entry => ({ id: c.id, kind: "customer", title: c.name, subtitle: c.owes ? money(c.owes) : "", act: "hub:customers" })),
    ...S.sales.slice(0, 5).map((x): Entry => ({ id: x.sale.sale_id, kind: "order", title: x.sale.receipt_number_local, subtitle: money(x.sale.total), act: `sale:${x.sale.sale_id}` })),
  ],
  sync: () => ({ link: S.link === "none" ? "offline" : S.link, pending: pending(S.events.map((e) => e.sync)).count, lastSync: S.lastSync || null, dataSaver: S.toggles.has("data_saver"), forcedOffline: S.forced }),
  account: () => null,
  locale: () => ({ language: PACKS[S.lang]?.native ?? S.lang, region: pack().sample ? t("sample_country") : pack().name, currency: pack().currency, english: S.lang === "en" }),
  run: (a) => { if (a === "pictures") { if (DSH.pictures) S.toggles.add("low_literacy"); else S.toggles.delete("low_literacy"); return; } S.screen = "app"; act(a); }, redraw: () => draw(),
}, { firstRun: false });

// ---- chrome ---------------------------------------------------------------------------------------------------------
/** The top bar (41 E): emblem, screen title, connection chip, notifications, account. A back arrow takes the emblem's place
 *  inside a flow. */
function topBar(title: string, back?: string): string {
  const p = pending(S.events.map((e) => e.sync)), off = !online(), n = unreadNotices();
  const initials = (S.staff.find((x) => x.role === S.role)?.name ?? "O").slice(0, 1);
  return `<div class="top">${back ? `<button class="iconbtn back" data-act="${back}" aria-label="${esc(t("back"))}">${icon("ui-arrow-left")}</button>` : `${brandMark(DATA.brand.places, "app-top-bar", S.theme === "dark", "logo")}`}
    <h1>${esc(title)}</h1>${DSH.helpButton()}<button class="netchip${off ? " off" : ""}" data-act="sheet" aria-label="${esc(t(off ? "offline" : "online"))}. ${esc(t("sync"))}${p.count ? ` · ${p.count}` : ""}">${icon(off ? "ui-offline" : "ui-sync")}${p.count ? `<span class="count">${p.count}</span>` : ""}</button>
    <button class="iconbtn bell" data-act="view:notifications" aria-label="${esc(t("notifications"))}${n ? ` (${n})` : ""}">${icon("ui-bell")}${n ? `<span class="dot">${n}</span>` : ""}</button>
    <button class="iconbtn avatarbtn" data-act="view:account" aria-label="${esc(t("account"))}"><span class="initials" aria-hidden="true">${esc(initials)}</span></button></div>`;
}
const TAB_ICON: Record<string, string> = { home: "ui-home", sell: "ui-cart", stock: "product-stock", chats: "product-chat", business: "product-dash", services: "ui-grid", float: "ui-float",
  invoices: "ui-receipt", customers: "ui-user", tables: "ui-grid", kitchen: "ui-receipt", books: "ui-doc" };
/** The tabs of this workspace: the business type's tabs, or an office workspace's (a person's or an organisation's, no till). */
const tabs = (): readonly Tab[] => workspaceTabs(DATA.workspaces, S.entity, S.btype) as readonly Tab[];
/** A word as this workspace says it (catalog/workspaces.v1.json): customers are contacts for a person, members for an organisation. */
const ww = (k: string): string => t(workspaceWord(DATA.workspaces, S.entity, k));
const office = (): boolean => S.entity !== "company" && S.btype === "no_till";
/** Tabs follow the business type (5, 42 H): bottom tabs on a phone, the same tabs in a side rail on a tablet (41 E). */
function tabBar(): string {
  return `<nav class="${S.size === "tablet" ? "rail" : "tabbar"}" aria-label="LynkOmni">${tabs().map((k) => `<button data-act="tab:${k}" ${S.tab === k ? 'aria-current="page"' : ""}>${icon(TAB_ICON[k] ?? "ui-grid")}<span>${esc(ww(`tab_${k}`))}</span>${k === "chats" && unread() ? `<span class="dot">${unread()}</span>` : ""}</button>`).join("")}</nav>`;
}
const summary = () => daySummary(S.sales, COSTS);
const flash = (): string => (S.flash ? `<div class="toast" role="status">${icon("ui-check")}<span>${esc(S.flash)}</span></div>` : "");
const row = (label: string, value: string, act = ""): string => act
  ? `<li><button class="rowbtn" data-act="${act}"><span class="main"><span class="nm">${esc(label)}</span>${value ? `<span class="sub">${esc(value)}</span>` : ""}</span>${icon("ui-chevron-right", "ic fwd")}</button></li>`
  : `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(label)}</span>${value ? `<span class="sub">${esc(value)}</span>` : ""}</span></div></li>`;
const practiceBanner = (): string => (S.practice ? `<p class="practice" role="status">${icon("ui-warning")}<span>${esc(t("practice_banner"))}</span></p>` : "");

// ---- tracking (owner, 9 November 2026): everything on its way, from the shared engine and drawn the same everywhere ----------
const trackLook = { t, esc, icon: (id: string) => icon(id), time: (iso: string) => clock(Date.parse(iso)), chip: (st: TrackView["state"]) => chip(st) };
const trackTitle = (v: TrackView): string => {
  const d = S.deliveries.find((x) => x.id === v.record);
  return d ? `${t("trk_k_delivery")} · ${t("receipt")} ${d.receipt}` : t(v.label);
};
function onTheWayCard(): string {
  const act = TRK.active("me").filter((v) => v.kind === "delivery" || v.kind === "order");
  return `<div class="card" data-item="on_the_way"><h2>${icon("ui-cart")}<span>${esc(t("trk_on_the_way"))}</span></h2>${act.length
    ? `<ul class="list">${act.slice(0, 3).map((v) => trackerLine(v, trackLook, trackTitle(v), v.kind === "delivery" ? `delivery:${v.record}` : "view:deliveries")).join("")}</ul><button class="ghost inline" data-act="view:deliveries">${esc(t("deliveries"))}</button>`
    : `<p>${esc(t("trk_none"))}</p>`}</div>`;
}
function deliveriesScreen(): string {
  const all = TRK.active("me"), done = S.deliveries.map((d) => TRK.view("delivery", d.id, "merchant")).filter((v): v is TrackView => !!v && v.ended);
  return `${topBar(t("deliveries"), "tab:home")}<div class="body"><ul class="list card" data-item="trackers">${[...all, ...done].map((v) => trackerLine(v, trackLook, trackTitle(v), v.kind === "delivery" ? `delivery:${v.record}` : "view:deliveries")).join("") || `<li><p class="info">${esc(t("trk_none"))}</p></li>`}</ul>${flash()}</div>`;
}
function deliveryScreen(): string {
  const d = S.deliveries.find((x) => x.id === S.delivery) ?? S.deliveries[0];
  const v = d ? TRK.view("delivery", d.id, "merchant") : null;
  if (!d || !v) return deliveriesScreen();
  return `${topBar(t("trk_k_delivery"), "view:deliveries")}<div class="body">${trackerHtml(v, trackLook, trackTitle(v))}
    <div class="card" data-item="track_link"><h2>${esc(t("trk_link"))}</h2><p class="mono">shop.lynkomni.com/track/${esc(d.pid)}</p><button class="ghost inline" data-act="copylink">${icon("ui-copy")}<span>${esc(t("trk_copy"))}</span></button></div>
    <p class="sub" data-item="tracking_privacy">${esc(t("trk_privacy"))}</p><p class="sub">${esc(t(d.own ? "own_rider" : "partner"))}</p>${flash()}</div>`;
}
/** Book a delivery for the sale just made: the shop's own rider when the plan has one, else the sandbox partner. The partner (or the
 *  rider's phone) reports each step; here a timer plays that part, and progress is a share of the trip, never a position. */
function bookDelivery(): void {
  const c = S.current; if (!c || S.deliveries.some((d) => d.order === c.sale.sale_id)) return;
  const own = (ent().own_riders ?? 0) !== 0, id = newId();
  const d: Delivery = { id, pid: publicId("DLV"), order: c.sale.sale_id, receipt: c.sale.receipt_number_local, own, timer: 0 };
  S.deliveries.unshift(d); S.delivery = id;
  emit("DeliveryRequested", { delivery_id: id, order_id: c.sale.sale_id, own_rider: own, price: own ? 0 : 1500, currency: pack().currency });
  const eta = new Date(Date.now() + 30 * 60_000).toISOString().slice(0, 19) + "Z";
  const steps: [number, () => void][] = [
    [700, () => { emit("DeliveryAccepted", { delivery_id: id, partner_reference: own ? "own-rider" : "SBXD-SAMPLE", eta }, "server"); }],
    [2200, () => { emit("DeliveryPickedUp", { delivery_id: id }, own ? "device" : "server"); TRK.setProgress("delivery", id, 0.1); }],
    [3600, () => { TRK.setProgress("delivery", id, 0.45); }], [5000, () => { TRK.setProgress("delivery", id, 0.8); }],
    [6400, () => { emit("DeliveryDelivered", { delivery_id: id, proof: "code" }, own ? "device" : "server"); toast(t("delivered")); }]];
  let i = 0;
  const next = (): void => { const st = steps[i]; if (!st) return; d.timer = window.setTimeout(() => { if (online()) { st[1](); i += 1; } next(); draw(); }, reduced() ? 150 : st[0] - (steps[i - 1]?.[0] ?? 0)); };
  next(); S.tab = "home"; S.view = "delivery"; draw();
}

function home(): string {
  if (office()) return officeHome();
  const blocks = homeBlocks(S.role, S.perms), sm = summary(), out: string[] = [`<p class="greet">${esc(t("hello", { shop: shop() }))}</p>`, DSH.searchField()];
  const kpis = blocks.filter((b) => b === "sales" || b === "profit").map((b) => `<div class="card kpi" data-item="${b === "sales" ? "today_sales" : "today_profit"}"><span>${esc(t(b === "sales" ? "today_sales" : "today_profit"))}</span><strong>${esc(money(b === "sales" ? sm.total : sm.profit))}</strong>${b === "sales" ? `<small>${esc(t("sales_count", { n: sm.count }))}</small>` : ""}</div>`);
  if (kpis.length) out.push(kpis.length === 2 ? `<div class="duo">${kpis.join("")}</div>` : kpis.join(""));
  for (const b of blocks) {
    if (b === "new_sale") out.push(`<button class="big" data-act="newsale" data-item="new_sale">${icon("ui-plus")}<span>${esc(t("new_sale"))}</span></button>`);
    if (b === "stock_check") out.push(`<button class="ghost" data-act="tab:stock">${esc(t("stock_check"))}</button>`);
    if (b === "alerts") {
      const a = stockAlerts(CATALOG, S.levels);
      const rows = [...a.negative.map((id) => [id, "neg", "below_zero"]), ...a.low.map((id) => [id, "low", "low_stock"])].slice(0, 4)
        .map(([id, c, k]) => `<button class="alert ${c}" data-act="product:${id}">${icon("ui-warning")}<span><b>${esc(item(id ?? "")?.name ?? "")}</b>${esc(t(k ?? ""))}</span>${icon("ui-chevron-right", "ic fwd")}</button>`);
      out.push(`<div class="card" data-item="stock_alerts"><h2>${esc(t("attention"))}</h2>${rows.join("") || `<p>${esc(t("stock_fine"))}</p>`}</div>`);
    }
    if (b === "chats") out.push(`<button class="card rowbtn" data-act="tab:chats" data-item="chats">${icon("product-chat")}<span class="main"><span class="nm">${esc(t("tab_chats"))}</span><span class="sub">${esc(unread() ? t("unread", { n: unread() }) : t("no_unread"))}</span></span>${icon("ui-chevron-right", "ic fwd")}</button>`);
    if (b === "insight") { const best = insight(S.sales); out.push(`<div class="card" data-item="insight"><h2>${icon("product-grow")}<span>${esc(t("insight"))}</span></h2><p>${esc(best ? t("best_seller", { product: best.name, qty: qtyText(best.qtyMilli) }) : t("no_insight"))}</p></div>`); }
    if (b === "pending") { out.push(onTheWayCard()); const p = pending(S.events.map((e) => e.sync)); out.push(`<button class="card rowbtn" data-act="sheet" data-item="pending_sync">${chip(p.state)}<span class="main"><span class="sub">${esc(p.count ? t("waiting_send", { n: p.count }) : t("all_sent"))}</span></span>${icon("ui-chevron-right", "ic fwd")}</button>`); }
  }
  return `${topBar(t("tab_home"))}<div class="body">${practiceBanner()}${out.join("")}</div>`;
}

/** Home of an office workspace (a person or an organisation without a till): money in and out this month, invoices waiting, things on their way. */
function officeHome(): string {
  const paid = S.invoices.filter((v) => v.state === "confirmed").reduce((a, v) => a + v.amount, 0), waiting = S.invoices.filter((v) => v.state !== "confirmed").length;
  return `${topBar(t("tab_home"))}<div class="body">${practiceBanner()}<p class="greet">${esc(t("hello", { shop: shop() }))}</p>${DSH.searchField()}
    <div class="duo"><div class="card kpi" data-item="today_sales"><span>${esc(t("money_in"))}</span><strong>${esc(money(paid))}</strong></div><div class="card kpi" data-item="today_profit"><span>${esc(t("money_out"))}</span><strong>${esc(money(0))}</strong></div></div>
    <button class="big" data-act="newinvoice" data-item="new_sale">${icon("ui-plus")}<span>${esc(t("new_invoice"))}</span></button>
    <button class="card rowbtn" data-act="tab:invoices" data-item="stock_alerts">${icon("ui-receipt")}<span class="main"><span class="nm">${esc(t("tab_invoices"))}</span><span class="sub">${esc(waiting ? t("waiting_send", { n: waiting }) : t("no_invoices"))}</span></span>${icon("ui-chevron-right", "ic fwd")}</button>
    <button class="card rowbtn" data-act="tab:books" data-item="insight">${icon("ui-doc")}<span class="main"><span class="nm">${esc(t("tab_books"))}</span><span class="sub">${esc(t("office_note"))}</span></span>${icon("ui-chevron-right", "ic fwd")}</button>
    <button class="card rowbtn" data-act="tab:customers" data-item="chats">${icon("ui-user")}<span class="main"><span class="nm">${esc(ww("tab_customers"))}</span><span class="sub">${esc(t("people_n", { n: CUSTOMERS.length }))}</span></span>${icon("ui-chevron-right", "ic fwd")}</button>
    ${onTheWayCard()}<button class="card rowbtn" data-act="sheet" data-item="pending_sync">${chip(pending(S.events.map((e) => e.sync)).state)}<span class="main"><span class="sub">${esc(pending(S.events.map((e) => e.sync)).count ? t("waiting_send", { n: pending(S.events.map((e) => e.sync)).count }) : t("all_sent"))}</span></span>${icon("ui-chevron-right", "ic fwd")}</button></div>`;
}
/** Books of an office workspace: the categories this entity uses, each posting to one account of the global chart, and an organisation's funds. */
function booksTab(): string {
  const e = DATA.workspaces.entities[S.entity], cats = e?.categories, funds = e?.funds ?? [];
  const list = (side: "income" | "expense"): string => `<ul class="list card">${(cats?.[side] ?? []).map((c) => row(t("cat_" + c.id), "")).join("")}</ul>`;
  return `${topBar(t("tab_books"))}<div class="body"><div class="card" data-item="profit_loss"><h2>${esc(t("it_profit_loss"))}</h2><div class="kv"><span>${esc(t("money_in"))}</span><strong>${esc(money(0))}</strong></div><div class="kv"><span>${esc(t("money_out"))}</span><strong>${esc(money(0))}</strong></div></div>
    <h2 class="sect" data-item="expenses">${esc(t("categories_income"))}</h2>${list("income")}<h2 class="sect" data-item="cash_book">${esc(t("categories_expense"))}</h2>${list("expense")}
    ${funds.length ? `<h2 class="sect">${esc(t("funds"))}</h2><ul class="list card">${funds.map((f) => row(t("fund_" + f), "")).join("")}</ul>` : ""}
    <p class="sub" data-item="owed_to_me">${esc(t("office_note"))}</p><p class="sub" data-item="audit_export">${esc(t("full_pages_web", { path: "/accounting" }))}</p><span data-item="accountant_access" hidden></span>${flash()}</div>`;
}

function sell(): string {
  const c = S.current, tot = total();
  const due = (n: number): string => {
    const two = secondCurrency(n, pack().currency, pack().currency === "USD" ? "EUR" : "USD", (m, a, b) => Math.round(m * ((DATA.fx[b] ?? 1) / (DATA.fx[a] ?? 1))));
    return `<div class="due"><span>${esc(t("total"))}</span><strong>${esc(money(n))}</strong></div>${two ? `<p class="sub second" data-item="second_currency">${esc(t("second_currency", { amount: formatMoney(two.amount, two.currency, locale()), currency: pack().currency }))}</p>` : ""}`;
  };
  switch (S.view) {
    case "basket": {
      const c2 = cust();
      return `${topBar(t("basket"), "view:main")}<div class="body">${practiceBanner()}<ul class="list">${S.cart.lines().map((l) => `<li><div class="rowbtn"><span class="main"><span class="nm">${esc(l.product.name)}</span><span class="sub">${esc(money(l.product.price))}</span></span>
        <span class="stepper" data-item="quantity"><button class="iconbtn" data-act="dec:${l.product.id}" aria-label="-1 ${esc(l.product.name)}">${icon(l.qtyMilli > 1000 ? "ui-minus" : "ui-trash")}</button><output>${qtyText(l.qtyMilli)}</output><button class="iconbtn" data-act="inc:${l.product.id}" aria-label="+1 ${esc(l.product.name)}">${icon("ui-plus")}</button></span></div></li>`).join("") || `<li><p class="info">${esc(t("empty_basket"))}</p></li>`}</ul>
        <label class="field" data-item="discount"><span>${esc(t("discount"))}</span><input id="discIn" inputmode="numeric" autocomplete="off" value="${S.discount ? esc(String(S.discount)) : ""}" data-in="discount"></label>
        <label class="field" data-item="note"><span>${esc(t("sale_note"))}</span><input id="noteIn" autocomplete="off" value="${esc(S.saleNote)}" data-in="salenote"></label>
        <label class="field" data-item="attach_customer"><span>${esc(t("attach_customer"))}</span><select data-in="customer"><option value="">${esc(t("no_customer"))}</option>${CUSTOMERS.map((x) => `<option value="${x.id}" ${x.id === S.customer ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select></label>
        ${c2 ? `<p class="sub">${esc(t("customer_attached", { name: c2.name }))}</p>` : ""}</div>
        <div class="foot"><div class="sum"><span>${esc(t("items", { n: S.cart.count() }))}</span><strong>${esc(money(tot))}</strong></div><button class="primary" data-act="view:pay" ${S.cart.count() ? "" : "disabled"}>${esc(t("charge"))}</button></div>`;
    }
    case "pay":
      return `${topBar(t("charge"), "view:basket")}<div class="body">${due(tot)}<p class="info">${esc(t("how_pay"))}</p>
        ${PAY_WAYS.map((w) => { const ok = wayOk(w.id), off = w.online && !online(); return `<button class="method${ok ? "" : " off"}" data-act="way:${w.id}" data-item="${w.id}">${icon(w.id === "cash" ? "ui-receipt" : w.id === "credit" ? "ui-user" : w.id === "qr" || w.id === "pay_link" ? "ui-qr" : w.id === "bank_transfer" ? "ui-pay-bank" : w.id === "mobile_money" ? "ui-pay-mobile-money" : "ui-pay-card")}<span>${esc(t("way_" + w.id))}</span>${!ok ? `<em>${esc(t("coming_soon"))}</em>` : off ? `<em>${esc(t("st_queued"))}</em>` : w.online ? `<em>${esc(t("sandbox"))}</em>` : ""}${icon("ui-chevron-right", "ic fwd")}</button>`; }).join("")}
        <button class="method" data-act="view:split" data-item="split">${icon("ui-grid")}<span>${esc(t("way_split"))}</span>${icon("ui-chevron-right", "ic fwd")}</button>
        <p class="info" data-item="proof_warning">${icon("ui-warning")}<span>${esc(t("proof_warning"))}</span></p></div>`;
    case "cash": {
      const given = Number(S.input || "0"), enough = given >= tot;
      return `${topBar(t("way_cash"), "view:pay")}<div class="body">${due(tot)}
        <label class="field"><span>${esc(t("cash_given"))}</span><input id="cashIn" inputmode="numeric" autocomplete="off" value="${esc(S.input)}" data-in="cash"></label>
        <div class="quick">${quickCash(tot, NOTES).map((v) => `<button data-act="cash:${v}">${esc(money(v))}</button>`).join("")}</div>
        <div class="change ${enough ? "ok" : ""}"><span>${esc(t("change"))}</span><strong>${enough ? esc(money(change(tot, given))) : "–"}</strong></div></div>
        <div class="foot"><button class="primary" data-act="paycash" ${enough ? "" : "disabled"}>${esc(t("complete"))}</button></div>`;
    }
    case "momo": {
      const w = payWay(S.receiptWay || "mobile_money");
      const needsNumber = w?.id === "mobile_money";
      return `${topBar(t("way_" + (w?.id ?? "mobile_money")), "view:pay")}<div class="body">${due(tot)}
        ${needsNumber ? `<label class="field"><span>${esc(t("customer_phone"))}</span><input id="momoIn" inputmode="tel" autocomplete="off" value="${esc(S.input)}" data-in="momo"></label>` : ""}
        ${w?.id === "qr" ? `<div class="qrbox" role="img" aria-label="${esc(t("pay_qr_shown"))}">${icon("ui-qr", "bigqr")}<p>${esc(t("pay_qr_shown"))}</p></div>` : ""}
        ${w?.id === "pay_link" ? `<p class="info">${icon("ui-info")}<span>${esc(t("pay_link_sent"))}</span></p>` : ""}
        ${w?.id === "tap_to_pay" || w?.id === "card" ? `<div class="tapbox">${icon("ui-pay-card", "bigqr")}<p>${esc(t(w.id === "tap_to_pay" ? "tap_phone" : "tap_terminal"))}</p></div>` : ""}
        <p class="info sbx">${icon("ui-info")}<span>${esc(t("sandbox"))}: ${esc(t("test_money"))}</span></p></div>
        <div class="foot"><button class="primary" data-act="payonline" ${!needsNumber || S.input.replace(/\D/g, "").length >= 9 ? "" : "disabled"}>${esc(t("send_to_partner"))}</button></div>`;
    }
    case "credit": {
      const c2 = cust(), need = creditNeedsCustomer("credit", S.customer || null);
      return `${topBar(t("way_credit"), "view:pay")}<div class="body">${due(tot)}
        <label class="field"><span>${esc(t("attach_customer"))}</span><select data-in="customer"><option value="">${esc(t("no_customer"))}</option>${CUSTOMERS.map((x) => `<option value="${x.id}" ${x.id === S.customer ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select></label>
        ${need ? `<p class="alert low" role="alert">${icon("ui-warning")}<span>${esc(t("credit_needs_customer"))}</span></p>` : `<p class="sub">${esc(t("credit_book_line", { name: c2?.name ?? "", amount: money((c2?.owes ?? 0) + tot) }))}</p>`}</div>
        <div class="foot"><button class="primary" data-act="paycredit" ${need ? "disabled" : ""}>${esc(t("complete"))}</button></div>`;
    }
    case "split": {
      const parts = S.parts, left = tot - parts.reduce((a, p) => a + p.amount, 0), chk = splitCheck(tot, parts.map((p) => p.amount));
      return `${topBar(t("way_split"), "view:pay")}<div class="body">${due(tot)}<ul class="list card">${parts.map((p, i) => row(`${t("way_" + p.way)} · ${money(p.amount)}`, "", `unsplit:${i}`)).join("") || `<li><p class="info">${esc(t("split_hint"))}</p></li>`}</ul>
        <p class="sub">${esc(t("split_left", { amount: money(Math.max(0, left)) }))}</p>
        <label class="field"><span>${esc(t("amount"))}</span><input id="splitIn" inputmode="numeric" autocomplete="off" value="${esc(S.input)}" data-in="split"></label>
        <div class="quick">${["cash", "mobile_money", "credit"].map((w) => `<button data-act="splitadd:${w}" ${Number(S.input || "0") > 0 && Number(S.input) <= left && wayOk(w) ? "" : "disabled"}>${esc(t("way_" + w))}</button>`).join("")}</div></div>
        <div class="foot"><button class="primary" data-act="paysplit" ${chk === "ok" && !(parts.some((p) => p.way === "credit") && !S.customer) ? "" : "disabled"}>${esc(t("complete"))}</button></div>`;
    }
    case "waiting": {
      const p = lastPayment(); if (!p || !c) return "";
      const st = paymentState(p.status, online()), failed = st === "failed";
      return `${topBar(t("way_" + (S.receiptWay || "mobile_money")), failed ? "view:pay" : undefined)}<div class="center">${due(c.sale.total)}${failed ? "" : `<div class="spinner" aria-hidden="true"></div>`}${st !== "cash" && st !== "credit" ? chip(st) : ""}
        <p>${esc(failed ? t("failed_note") : st === "queued" ? t("queued_note") : t("wait_momo"))}</p><p class="sub">${esc(t("proof_warning"))}</p></div>
        ${st === "queued" || st === "sent" ? `<div class="foot"><button class="primary" data-act="newsale">${esc(t("new_sale"))}</button></div>` : ""}
        ${failed ? `<div class="foot two"><button class="ghost" data-act="view:pay">${esc(t("other_method"))}</button><button class="primary" data-act="retry">${esc(t("try_again"))}</button></div>` : ""}`;
    }
    case "done": case "receipt": {
      if (!c) return "";
      const opts = receiptOptions(ent());
      return `${topBar(t("receipt"))}<div class="body"><div class="center">${icon("ui-check", "bigcheck")}<h1>${esc(t("done"))}</h1><p class="amount">${esc(money(c.sale.total))}</p>
        ${c.tendered !== undefined ? `<p>${esc(t("change"))}: <strong>${esc(money(change(c.sale.total, c.tendered)))}</strong></p>` : ""}</div>
        <div class="receipt"><span class="nm">${esc(t("receipt"))} ${esc(c.sale.receipt_number_local)}</span>${c.payments.map((p) => `<span>${esc(t("method_" + p.method))} · ${esc(money(p.amount))} ${p.status === "pending_confirmation" ? chip("sent") : p.status === "confirmed" ? chip("confirmed") : p.status === "failed" ? chip("failed") : ""}</span>`).join("")}
          <span>${esc(t("provisional"))}</span><span data-item="not_tax_receipt">${esc(t("not_tax"))}</span><span class="verify" data-item="verify_qr">${icon("ui-qr")}<span>${esc(t("verify_receipt"))}</span></span></div>
        <h2 class="sect">${esc(t("send_receipt"))}</h2><div class="quick">${["print", "qr", "chat_link", "sms_link"].map((o) => `<button data-act="receipt:${o}" data-item="${o}" ${opts.includes(o) ? "" : "disabled"}>${esc(t("rc_" + o))}</button>`).join("")}</div>
        ${opts.includes("chat_link") ? "" : `<p class="sub">${esc(t("message_receipts_plan"))}</p>`}
        <button class="ghost inline" data-act="deliver" ${S.deliveries.some((d) => d.order === c.sale.sale_id) ? "disabled" : ""}>${icon("ui-cart")}<span>${esc(t("deliver_order"))}</span></button>${flash()}</div>
        <div class="foot"><button class="primary" data-act="newsale">${esc(t("new_sale"))}</button></div>`;
    }
    case "off":
      return `${topBar(t("charge"), "view:pay")}<div class="center"><span class="pic" role="img" aria-label="${esc(DATA.pictures.offAlt)}">${S.theme === "dark" ? DATA.pictures.offDark : DATA.pictures.offLight}</span>
        <p class="nm">${esc(t("coming_soon"))}</p>${notifyBtn("payments")}</div><div class="foot"><button class="primary" data-act="view:pay">${esc(t("other_method"))}</button></div>`;
    case "sales": return salesToday();
    case "sale": return saleDetail();
    case "shift": return shiftScreen();
    case "practice": return practiceScreen();
    default: {
      const cats = ["all", "food", "drinks", "home"];
      const q = S.search.trim().toLowerCase();
      const items = CATALOG.filter((p) => (S.category === "all" || p.category === S.category) && (!q || p.name.toLowerCase().includes(q) || (p.barcode ?? "").includes(q)));
      return `${topBar(t("tab_sell"))}${practiceBanner()}<div class="selltools"><label class="search" data-item="search"><span class="sr">${esc(t("search"))}</span><input id="searchIn" data-in="search" placeholder="${esc(t("search"))}" value="${esc(S.search)}" autocomplete="off"></label>
        <button class="iconbtn" data-act="scan" data-item="scan" aria-label="${esc(t("scan"))}">${icon("ui-qr")}</button><button class="iconbtn" data-act="voice" data-item="voice" aria-label="${esc(t("sell_by_voice"))}">${icon("ui-mic")}</button></div>
        <div class="cats" data-item="categories">${cats.map((k) => `<button data-act="cat:${k}" aria-pressed="${S.category === k}">${esc(t(k === "home" ? "household" : k))}</button>`).join("")}</div>
        <div class="body"><div class="grid">${items.map((p) => { const ql = S.cart.lines().find((l) => l.product.id === p.id); return `<button class="tile" data-act="add:${p.id}"><span class="nm">${esc(p.name)}</span><span class="pr">${esc(money(p.price))}</span>${ql ? `<span class="qty">${qtyText(ql.qtyMilli)}</span>` : ""}</button>`; }).join("") || `<p class="info">${esc(t("no_results"))}</p>`}</div>
        <div class="quick sellmore"><button data-act="view:sales">${esc(t("sales_today"))}</button><button data-act="view:shift">${esc(t("shift"))}</button><button data-act="tab:services">${esc(t("services_for_customers"))}</button><button data-act="view:practice">${esc(t("practice_mode"))}</button></div>${flash()}</div>
        <div class="foot"><div class="sum"><span>${esc(t("items", { n: S.cart.count() }))}</span><strong>${esc(money(tot))}</strong></div><button class="primary" data-act="view:basket" data-item="basket" ${S.cart.count() ? "" : "disabled"}>${esc(t("basket"))}</button></div>`;
    }
  }
}
function notifyBtn(service: string): string {
  return S.notified.has(service) ? `<p class="info">${icon("ui-bell")}<span>${esc(t("notify_done"))}</span></p>` : `<button class="linkbtn" data-act="notify:${service}">${esc(t("notify_me"))}</button>`;
}

// ---- inside Sell: today's sales, shifts, practice mode (41 E) -----------------------------------------------------------
function salesToday(): string {
  return `${topBar(t("sales_today"), "view:main")}<div class="body"><ul class="list card">${S.sales.map((s) => { const p = s.payments[s.payments.length - 1]; const ps = p ? paymentState(p.status, online()) : null;
    return `<li><button class="rowbtn" data-act="sale:${s.sale.sale_id}"><span class="main"><span class="nm">${esc(s.sale.receipt_number_local)} · ${esc(clock(s.at))}${s.voided ? ` · ${esc(t("voided"))}` : ""}</span><span class="sub">${esc(money(s.sale.total))}${s.returned ? ` · ${esc(t("refunded", { amount: money(s.returned) }))}` : ""}</span></span>${ps && ps !== "cash" && ps !== "credit" ? chip(ps) : ""}${icon("ui-chevron-right", "ic fwd")}</button></li>`; }).join("") || `<li><p class="info">${esc(t("no_sales_yet"))}</p></li>`}</ul></div>`;
}
function saleDetail(): string {
  const s = S.sales.find((x) => x.sale.sale_id === S.selected);
  if (!s) return salesToday();
  return `${topBar(s.sale.receipt_number_local, "view:sales")}<div class="body"><div class="card">${s.sale.lines.map((l) => `<div class="kv"><span>${esc(l.product_name)} × ${qtyText(l.quantity_milli)}</span><strong>${esc(money(l.line_total))}</strong></div>`).join("")}
    <div class="kv"><span>${esc(t("total"))}</span><strong>${esc(money(s.sale.total))}</strong></div></div>
    <button class="ghost inline" data-act="reprint" data-item="reprint">${esc(t("reprint"))}</button>
    ${s.voided ? `<p class="info">${esc(t("voided"))}</p>` : `<div class="card" data-item="void_reason"><h2>${esc(t("void_sale"))}</h2><div class="reasons">${VOID_REASONS.map((r) => `<button data-act="void:${r}">${esc(t("vr_" + r))}</button>`).join("")}</div></div>
    <div class="card" data-item="return_refund"><h2>${esc(t("return_refund"))}</h2><div class="stepper"><button class="iconbtn" data-act="rqty:-1" aria-label="-1">${icon("ui-minus")}</button><output>${S.returnQty}</output><button class="iconbtn" data-act="rqty:1" aria-label="+1">${icon("ui-plus")}</button></div>
      <label class="switch"><span>${esc(t("restock"))}</span><input type="checkbox" data-in="restock" ${S.restock ? "checked" : ""}></label>
      <div class="reasons">${RETURN_REASONS.map((r) => `<button data-act="return:${r}">${esc(t("rr_" + r))}</button>`).join("")}</div></div>`}${flash()}</div>`;
}
function shiftScreen(): string {
  const sh = S.shift;
  if (!sh) return `${topBar(t("shift"), "view:main")}<div class="body"><div class="card" data-item="open_float"><h2>${esc(t("open_shift"))}</h2>
    <label class="field"><span>${esc(t("opening_float"))}</span><input id="floatIn" inputmode="numeric" autocomplete="off" value="${esc(S.input)}" data-in="cashnum"></label>
    <button class="primary inline" data-act="openshift">${esc(t("open_shift"))}</button></div>${flash()}</div>`;
  return `${topBar(t("shift"), "view:main")}<div class="body"><div class="card" data-item="open_float"><div class="kv"><span>${esc(t("opening_float"))}</span><strong>${esc(money(sh.float))}</strong></div><div class="kv"><span>${esc(t("expected_in_drawer"))}</span><strong>${esc(money(expectedCash()))}</strong></div></div>
    <div class="card" data-item="cash_count"><h2>${esc(t("count_cash"))}</h2><label class="field"><span>${esc(t("counted"))}</span><input id="countIn" inputmode="numeric" autocomplete="off" value="${esc(S.input)}" data-in="cashnum"></label>
      <div class="reasons">${COUNT_KINDS.filter((k) => k !== "day_end").map((k) => `<button data-act="countkind:${k}" data-item="${k}" aria-pressed="${S.countKind === k}">${esc(t("ck_" + k))}</button>`).join("")}</div>
      <div class="foot two inline"><button class="ghost" data-act="countcash">${esc(t("count_cash"))}</button><button class="primary" data-act="closeshift" data-item="close_discrepancy">${esc(t("close_shift"))}</button></div>
      <p class="sub">${esc(t("difference_never_blocks"))}</p></div>${flash()}</div>`;
}
function practiceScreen(): string {
  return `${topBar(t("practice_mode"), "view:main")}<div class="body"><p class="info" data-item="marked_copy">${icon("ui-info")}<span>${esc(t("practice_mode_help"))}</span></p>
    <label class="switch"><span>${esc(t("practice_mode"))}</span><input type="checkbox" data-in="practice" ${S.practice ? "checked" : ""}></label>
    ${S.practice ? `<div class="card" data-item="practice_float"><div class="kv"><span>${esc(t("practice_float"))}</span><strong>${esc(money(S.practiceFloat))}</strong></div><p class="sub">${esc(t("practice_float_help"))}</p></div>` : ""}</div>`;
}

// ---- Stock (41 E) ------------------------------------------------------------------------------------------------------
function stock(): string {
  const p = item(S.product);
  const qtyPick = `<div class="card" data-item="quantity"><span class="sub">${esc(t("quantity"))}</span><div class="stepper"><button class="iconbtn" data-act="qty:-1" aria-label="-1">${icon("ui-minus")}</button><output>${S.qty}</output><button class="iconbtn" data-act="qty:1" aria-label="+1">${icon("ui-plus")}</button></div></div>`;
  const prodPick = `<label class="field"><span>${esc(t("product"))}</span><select data-in="product">${CATALOG.map((x) => `<option value="${x.id}" ${x.id === S.product ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select></label>`;
  switch (S.view) {
    case "item": {
      if (!p) return "";
      const lv = level(p.id), st = stockState(lv, p.reorderAtMilli), hist = S.events.filter((e) => JSON.stringify(e.payload).includes(p.id)).slice(0, 5);
      return `${topBar(p.name, "view:main")}<div class="body"><div class="card"><div class="duo"><div class="kpi"><span>${esc(t("in_stock"))}</span><strong>${qtyText(lv)}</strong></div><div class="kpi"><span>${esc(t("reorder_at"))}</span><strong>${qtyText(p.reorderAtMilli)}</strong></div></div>
        ${st === "negative" ? `<p class="info">${icon("ui-warning")}<span>${esc(t("never_blocked"))}</span></p>` : ""}</div>
        <ul class="list card">${lineItem("price", t("price"), money(p.price))}${lineItem("cost", t("cost"), money(p.cost))}${lineItem("barcode", t("barcode"), p.barcode ?? "–")}${lineItem("variants", t("variants"), p.variants.length ? p.variants.join(", ") : t("no_variants"))}${lineItem("units", t("unit"), t("unit_" + p.unit))}
          ${lineItem("photos", t("photos"), t("add_photo"))}</ul><ul class="list card" data-item="stock_per_branch">${BRANCHES.map((b) => row(t("stock_at_branch", { branch: t("branch_" + b) }), qtyText(b === p.branch ? lv : S.branchLevels[b]?.[p.id] ?? 0))).join("")}</ul>
        <div class="card" data-item="history"><h2>${esc(t("history"))}</h2>${hist.map((e) => `<div class="kv"><span>${esc(e.type)}</span>${chip(e.sync)}</div>`).join("") || `<p class="sub">${esc(t("no_history"))}</p>`}</div>
        <div class="quick"><button data-act="view:received">${esc(t("received"))}</button><button data-act="view:count">${esc(t("count_set"))}</button><button data-act="view:remove">${esc(t("remove"))}</button><button data-act="view:move">${esc(t("move_branch"))}</button></div>${flash()}</div>`;
    }
    case "add":
      return `${topBar(t("add_product"), "view:main")}<div class="body"><p class="info">${esc(t("add_product_ways"))}</p>${FIRST_PRODUCT_WAYS.map((w) => `<button class="method" data-act="addway:${w}" data-item="${w}">${icon(w === "scan" ? "ui-qr" : w === "voice" ? "ui-mic" : w === "import" ? "ui-doc" : w === "photo" ? "ui-edit" : "ui-grid")}<span>${esc(t("way_add_" + w))}</span>${icon("ui-chevron-right", "ic fwd")}</button>`).join("")}${flash()}</div>`;
    case "received":
      return `${topBar(t("received"), "view:main")}<div class="body">${prodPick}<label class="field" data-item="supplier"><span>${esc(t("supplier"))}</span><select data-in="supplier">${SUPPLIERS.map((x) => `<option value="${x.id}" ${x.id === S.supplier ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select></label>${qtyPick}
        <button class="primary inline" data-act="stock:received">${esc(t("save"))}</button>${flash()}</div>`;
    case "count":
      return `${topBar(t("count_set"), "view:main")}<div class="body"><div class="reasons">${(["full", "partial"] as const).map((m) => `<button data-act="countmode:${m}" data-item="${m}" aria-pressed="${S.countMode === m}">${esc(t("count_" + m))}</button>`).join("")}</div>
        <p class="sub">${esc(t(S.countMode === "full" ? "count_full_help" : "count_partial_help"))}</p>${prodPick}${qtyPick}<button class="primary inline" data-act="stock:count">${esc(t("save"))}</button>${flash()}</div>`;
    case "remove":
      return `${topBar(t("remove"), "view:main")}<div class="body">${prodPick}${qtyPick}<div class="card"><h2>${esc(t("reason"))}</h2><div class="reasons">${REMOVE_REASONS.map((r) => `<button data-act="stock:${r}" data-item="${REMOVE_ITEM[r] ?? r}">${esc(t("r_" + r))}</button>`).join("")}</div></div>${flash()}</div>`;
    case "move":
      return `${topBar(t("move_branch"), "view:main")}<div class="body">${prodPick}${lineItem("from_branch", t("branch"), t("branch_" + (p?.branch ?? "main")))}<label class="field" data-item="to_branch"><span>${esc(t("to_branch"))}</span><select data-in="moveto">${BRANCHES.map((b) => `<option value="${b}" ${b === S.moveTo ? "selected" : ""}>${esc(t("branch_" + b))}</option>`).join("")}</select></label>${qtyPick}
        <p class="sub">${esc(t("move_help"))}</p><button class="primary inline" data-act="stock:move">${esc(t("save"))}</button>${flash()}</div>`;
    case "suppliers":
      return `${topBar(t("suppliers"), "view:main")}<div class="body"><ul class="list card" data-item="supplier_list">${SUPPLIERS.map((s) => row(s.name, t("products_n", { n: CATALOG.filter((x) => x.supplier === s.id).length }))).join("")}</ul></div>`;
    case "reorder":
      return `${topBar(t("reorder"), "view:main")}<div class="body"><button class="primary inline" data-act="draftorder" data-item="drafts">${esc(t("draft_reorder"))}</button>
        <ul class="list card" data-item="purchase_orders">${S.orders.map((o) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(SUPPLIERS.find((x) => x.id === o.supplier)?.name ?? "")}</span><span class="sub">${esc(t("lines_n", { n: o.lines }))} · ${esc(t(o.state === "draft" ? "draft" : "purchase_order_sent"))}</span></span>${o.state === "draft" ? `<button class="ghost small" data-act="sendorder:${o.id}">${esc(t("confirm_send"))}</button>` : ""}</div></li>`).join("") || `<li><p class="info">${esc(t("no_drafts"))}</p></li>`}</ul>${flash()}</div>`;
    case "marketplace":
      return `${topBar(t("marketplace"), "view:main")}<div class="body"><ul class="list card" data-item="supplier_marketplace">${SUPPLIERS.map((s) => row(s.name, t("marketplace_line"))).join("")}</ul>
        <div class="card" data-item="buy_together"><h2>${esc(t("buy_together"))}</h2><p class="sub">${esc(t("buy_together_help"))}</p></div></div>`;
    case "labels":
      return `${topBar(t("labels"), "view:main")}<div class="body">${prodPick}<div class="label" data-item="labels">${esc(p?.name ?? "")}<strong>${esc(money(p?.price ?? 0))}</strong><span class="bars" aria-hidden="true" data-item="barcodes">${"|".repeat(28)}</span><span>${esc(p?.barcode ?? "")}</span></div>
        <button class="primary inline" data-act="printlabel">${esc(t("print_label"))}</button>${flash()}</div>`;
    case "import":
      return `${topBar(t("import_export"), "view:main")}<div class="body"><button class="method" data-act="importfile" data-item="import">${icon("ui-doc")}<span>${esc(t("import_products"))}</span>${icon("ui-chevron-right", "ic fwd")}</button>
        <button class="method" data-act="exportfile" data-item="export">${icon("ui-doc")}<span>${esc(t("export_products"))}</span>${icon("ui-chevron-right", "ic fwd")}</button><p class="sub">${esc(t("your_data_yours"))}</p>${flash()}</div>`;
  }
  const rank = { negative: 0, low: 1, ok: 2 } as const;
  const shown = stockFilter(CATALOG, S.levels, { state: S.stockFilter, category: S.category, branch: S.branch });
  const rows = [...shown].sort((a, b) => rank[stockState(level(a.id), a.reorderAtMilli)] - rank[stockState(level(b.id), b.reorderAtMilli)]).map((x) => {
    const st = stockState(level(x.id), x.reorderAtMilli);
    return `<li><button class="rowbtn" data-act="product:${x.id}">${icon("product-stock", "prod")}<span class="main"><span class="nm">${esc(x.name)}</span><span class="sub">${esc(t("in_stock"))}: ${qtyText(level(x.id))} · ${esc(t("branch_" + x.branch))}</span></span>
      ${st === "ok" ? "" : `<span class="pill ${st === "negative" ? "neg" : "low"}">${esc(t(st === "negative" ? "below_zero" : "low_stock"))}</span>`}</button></li>`;
  });
  return `${topBar(t("tab_stock"))}<div class="cats">${STOCK_FILTERS.map((f) => `<button data-act="sfilter:${f}" data-item="filter_${f}" aria-pressed="${S.stockFilter === f}">${esc(t("sf_" + f))}</button>`).join("")}</div>
    <div class="filters"><label class="field" data-item="filter_category"><span>${esc(t("category"))}</span><select data-in="category">${["all", "food", "drinks", "home"].map((k) => `<option value="${k}" ${S.category === k ? "selected" : ""}>${esc(t(k === "home" ? "household" : k))}</option>`).join("")}</select></label>
      <label class="field" data-item="filter_branch"><span>${esc(t("branch"))}</span><select data-in="branch">${["all", ...BRANCHES].map((b) => `<option value="${b}" ${S.branch === b ? "selected" : ""}>${esc(t(b === "all" ? "all" : "branch_" + b))}</option>`).join("")}</select></label></div>
    <div class="body"><ul class="list card">${rows.join("") || `<li><p class="info">${esc(t("no_results"))}</p></li>`}</ul>
    <div class="quick"><button data-act="view:add">${esc(t("add_product"))}</button><button data-act="view:received">${esc(t("received"))}</button><button data-act="view:count">${esc(t("count_set"))}</button><button data-act="view:remove">${esc(t("remove"))}</button>
      <button data-act="view:move">${esc(t("move_branch"))}</button><button data-act="view:suppliers">${esc(t("suppliers"))}</button><button data-act="view:reorder">${esc(t("reorder"))}</button><button data-act="view:marketplace">${esc(t("marketplace"))}</button>
      <button data-act="view:labels">${esc(t("labels"))}</button><button data-act="view:import">${esc(t("import_export"))}</button></div></div>`;
}

// ---- Chats (41 E, 44 E): customer-business and support only; LynkOmni Support pinned at the top ---------------------------
function chats(): string {
  const th = S.threads.find((x) => x.id === S.thread);
  if (S.view === "thread" && th) {
    const translated = th.lang !== "en" && !isTest() && th.lang !== S.lang;
    const actions = THREAD_ACTIONS.map((k) => `<button data-act="tact:${k}" data-item="${k}">${esc(t("ta_" + k))}</button>`).join("");
    const card = (c: { kind: string; label: string }): string => `<span class="mcard" data-item="attached_card">${icon(c.kind === "order" ? "ui-cart" : c.kind === "pay_link" ? "ui-qr" : c.kind === "receipt" ? "ui-receipt" : c.kind === "quote" ? "ui-doc" : "product-stock")}<span>${esc(t("card_" + c.kind))}${c.label ? ` · ${esc(c.label)}` : ""}</span></span>`;
    return `${topBar(th.name, "view:main")}<div class="thread">${th.support ? `<p class="info">${icon("ui-info")}<span>${esc(t("support_pinned"))}</span></p>` : ""}
      ${th.assigned ? `<p class="sub">${esc(t("assigned_to", { name: th.assigned === "me" ? t("me") : th.assigned }))}</p>` : ""}
      ${th.msgs.map((m) => `<div class="msg ${m.out ? "out" : "in"}">${m.card ? card(m.card) : ""}${m.text ? `<span>${esc(m.text === "support_welcome" ? t("support_welcome") : m.text)}</span>` : ""}
        ${!m.out && m.lang && m.lang !== "en" && translated ? `<button class="linkbtn small" data-act="original" data-item="translated_note">${esc(t(S.showOriginal ? "show_translation" : "translated_from", { lang: langName(m.lang) }))}</button>` : ""}
        <span class="meta">${esc(clock(m.at))}${m.out ? chip(m.state === "queued" ? "queued" : "sent") : ""}</span></div>`).join("")}</div>
      <div class="tactions" role="group" aria-label="${esc(t("chat_actions"))}">${actions}</div>
      ${S.setting === "replies" ? `<div class="quick">${SAVED_REPLIES.map((r) => `<button data-act="reply:${r}">${esc(t(r))}</button>`).join("")}</div>` : ""}
      <div class="compose"><input id="msgIn" data-in="msg" aria-label="${esc(t("write_message"))}" placeholder="${esc(t("write_message"))}" value="${esc(S.draft)}" autocomplete="off"><button class="iconbtn fwd" data-act="send" aria-label="${esc(t("send"))}">${icon("ui-chevron-right")}</button></div>`;
  }
  const shown = S.threads.filter((x) => x.support || S.chatFilter === "all" || (S.chatFilter === "unread" && x.unread > 0) || (S.chatFilter === "assigned" && x.assigned === "me") || (S.chatFilter === "orders" && x.order));
  return `${topBar(t("tab_chats"))}<div class="cats">${CHAT_FILTERS.map((f) => `<button data-act="cfilter:${f}" data-item="filter_${f}" aria-pressed="${S.chatFilter === f}">${esc(t("cf_" + f))}</button>`).join("")}</div>
    <div class="body"><p class="info">${icon("ui-info")}<span>${esc(t("business_chat"))}</span></p><ul class="list card">${shown.map((x) => { const last = x.msgs[x.msgs.length - 1];
    const lastText = last?.text === "support_welcome" ? t("support_welcome") : last?.card && !last.text ? t("card_" + last.card.kind) : last?.text ?? "";
    return `<li${x.support ? ' data-item="support_pinned"' : ""}><button class="rowbtn" data-act="thread:${x.id}"><span class="avatar" aria-hidden="true">${x.support ? icon("product-chat") : esc(x.name.slice(0, 1))}</span><span class="main"><span class="nm">${esc(x.name)}${x.support ? ` · ${esc(t("pinned"))}` : ""}</span><span class="sub">${esc(lastText)}</span></span>${x.unread ? `<span class="pill ok">${x.unread}</span>` : `<span class="sub">${esc(last ? clock(last.at) : "")}</span>`}</button></li>`; }).join("")}</ul></div>`;
}
function threadAct(k: string): void {
  const th = S.threads.find((x) => x.id === S.thread); if (!th) return;
  if (k === "saved_replies") { S.setting = S.setting === "replies" ? "" : "replies"; draw(); return; }
  if (k === "assign_staff") { th.assigned = th.assigned ? "" : (S.staff[1]?.name ?? "me"); toast(t(th.assigned ? "assigned_to" : "unassigned", { name: th.assigned })); return; }
  const kind = k === "send_product" ? "product" : k === "send_quote" ? "quote" : k === "send_pay_link" ? "pay_link" : k === "send_receipt" ? "receipt" : k === "photo" ? "photo" : "voice_note";
  const label = kind === "product" ? CATALOG[0]?.name ?? "" : kind === "quote" ? publicId("QUO") : kind === "pay_link" ? money(CATALOG[3]?.price ?? 0) : kind === "receipt" ? S.sales[0]?.sale.receipt_number_local ?? "" : "";
  sendMsg({ kind, label });
}

// ---- the Business hub (41 E): every section, in the blueprint's order, then the services waiting for a partner ---------------
/** Regulated parts open only when their licensed partner is signed for the country; until then "Coming to your country soon."
 *  with Notify me (global availability rule). The service each regulated item waits for: */
const REGULATED: Record<string, string> = { recovery: "recovery", evidence_packs: "payments", payout_splits: "payments", cards: "vcard", spend: "vcard", approvals: "vcard",
  issuer_display: "vcard", financing: "financing", protection: "insurance", brand_offers: "ads", received: "payments", payouts: "payments", fees: "payments" };
const serviceOn = (svc: string): boolean => {
  if (!S.realUser) return true;   // the sample country runs every partner as a sandbox
  const s = pack().services.find((x) => x.service === svc);
  return s ? s.state === "available" : false;
};
const lineItem = (id: string, label: string, value: string, act = ""): string => {
  const svc = REGULATED[id];
  if (svc && !serviceOn(svc)) return `<li data-item="${id}"><div class="rowbtn static"><span class="main"><span class="nm">${esc(label)}</span><span class="sub">${esc(t("coming_soon"))}</span></span>${notifyBtn(svc)}</div></li>`;
  return row(label, value, act).replace("<li>", `<li data-item="${id}">`);
};
function hubValue(item: string): string {
  const sm = summary(), a = stockAlerts(CATALOG, S.levels), owed = CUSTOMERS.reduce((x, c) => x + c.owes, 0);
  const com = S.reqs.filter((r) => r.state === "confirmed").reduce((x, r) => x + r.commission, 0);
  switch (item) {
    case "sales": return t("sales_count", { n: sm.count }) + " · " + money(sm.total);
    case "profit": return canSeeProfit(S.role, S.perms) ? money(sm.profit) : t("owner_only");
    case "payments": case "received": return money(sm.confirmed);
    case "cash_expected": return money(expectedCash());
    case "confirmed": return money(sm.confirmed);
    case "waiting": return money(sm.waiting);
    case "failed": return money(sm.failed);
    case "running_low": return t("products_n", { n: a.low.length + a.negative.length });
    case "unusual": return t("unusual_n", { n: S.notices.filter((n) => n.key === "n_cash_difference" || n.key === "n_below_zero").length });
    case "products": return t("products_n", { n: CATALOG.length });
    case "staff": return t("people_n", { n: S.staff.length });
    case "branches": return t("branches_n", { n: BRANCHES.length });
    case "period": return t("today");
    case "refunds": return money(S.sales.reduce((x, s) => x + s.returned, 0));
    case "who_owes_me": case "owed_to_me": return money(owed);
    case "directory": return t("people_n", { n: CUSTOMERS.length });
    case "commissions": return money(com);
    case "float": return money(PARTNERS.reduce((x, p) => x + p.float, 0));
    case "limits": { const l = combinedLimits(partner().limits); return t("limit_line", { per: money(l.per_transaction), day: money(l.per_day) }); }
    case "outlets": return ent().outlets === 0 || ent().outlets === undefined ? t("outlets_plan") : t("outlets_n", { n: S.outletList.length });
    case "seats": return t("people_n", { n: S.staff.length });
    case "devices": return t("devices_n", { n: S.devices.length });
    case "next_bill": return money(0);
    case "username": return S.username ? `@${S.username}` : t("not_set");
    case "link": case "shop_page": return S.username ? `shop.lynkomni.com/${S.username}` : t("not_set");
    case "online_orders": return t("orders_n", { n: S.threads.filter((x) => x.order).length });
    case "history": return t("runs_n", { n: S.runs.length });
    case "lessons": return t("lessons_n", { n: ACADEMY.length });
    default: return "";
  }
}
const REMOVE_ITEM: Record<string, string> = { damage: "damaged", loss: "lost", expiry: "expired" };
const ACADEMY = ["lesson_first_sale", "lesson_stock", "lesson_cash", "lesson_credit", "lesson_proof"];
const HUB_ICON: Record<string, string> = { reports: "product-dash", daily_close: "ui-receipt", money: "product-mpay", invoicing: "ui-doc", customers: "ui-user", loyalty: "product-rewards", books: "product-ledger",
  growth: "product-grow", assistant: "ui-info", cards: "product-vcard", online_shop: "product-checkout", agent_earnings: "ui-commission", team: "ui-user", branches_devices: "ui-grid",
  plans_billing: "ui-receipt", settings: "ui-settings", academy: "ui-info", automations: "ui-sync" };
function business(): string {
  if (S.view === "hub" && S.hub) return hubSection(S.hub);
  if (S.view === "setting" && S.setting) return settingScreen(S.setting);
  const waiting = pack().services.filter((s) => s.state !== "available");
  return `${topBar(t("tab_business"))}<div class="body">${webNote()}${DSH.searchField()}<ul class="list card">${HUB.map((h) => `<li data-item="${h.id}"><button class="rowbtn" data-act="hub:${h.id}">${icon(HUB_ICON[h.id] ?? "ui-grid", "prod")}<span class="main"><span class="nm">${esc(t("it_" + h.id))}</span>${hubValue(h.id === "daily_close" ? "sales" : h.id === "agent_earnings" ? "commissions" : "") ? `<span class="sub">${esc(hubValue(h.id === "daily_close" ? "sales" : "commissions"))}</span>` : ""}</span>${icon("ui-chevron-right", "ic fwd")}</button></li>`).join("")}</ul>
    <div class="card" data-item="waiting_services"><h2>${esc(t("it_waiting_services"))}</h2><ul class="list">${(waiting.length ? waiting : pack().services).map((s) => `<li class="svc">${icon(s.icon, "prod")}<span class="main"><span class="nm">${esc(s.name)}</span>
      <span class="sub">${esc(t(s.state === "available" ? "available" : "coming_soon"))}</span></span>${s.state === "available" ? `<span class="pill ok">${icon("ui-check")}</span>` : notifyBtn(s.service)}</li>`).join("")}</ul></div>${flash()}</div>`;
}
/** 44 C: a computer that is not a registered device sees the Business app as a web view, "View only on this computer". */
const webNote = (): string => (S.size === "web" ? `<p class="info" data-item="web_view">${icon("ui-info")}<span>${esc(t("view_only_computer"))}</span></p>` : "");
function hubSection(id: string): string {
  const reg = DATA.screens.find((s) => s.id === id); if (!reg) return "";
  const back = "view:main";
  const rows = (items: readonly string[], act: (i: string) => string = () => ""): string => `<ul class="list card">${items.map((i) => lineItem(i, t("it_" + i), hubValue(i), act(i))).join("")}</ul>`;
  let extra = "";
  switch (id) {
    case "daily_close": extra = `<p class="sub">${esc(t("daily_close_help"))}</p><button class="primary inline" data-act="closeday">${esc(t("close_day"))}</button>`; break;
    case "reports": case "invoicing": case "customers": case "books": extra = `<p class="sub">${esc(t("full_pages_web", { path: reg.path }))}</p>`; break;
    case "assistant": extra = `<label class="field"><span>${esc(t("it_ask"))}</span><input id="askIn" data-in="ask" value="${esc(S.ask)}" autocomplete="off"></label><button class="ghost inline" data-act="ask">${esc(t("send"))}</button>
      ${S.answer ? `<div class="card"><p class="sub">${esc(t("assist_label"))}</p><p>${esc(S.answer)}</p></div>` : ""}<p class="sub">${esc(t("assist_never"))}</p>`; break;
    case "cards": extra = `<p class="sub">${esc(t("cards_issuer"))}</p>`; break;
    case "online_shop": extra = `<label class="field"><span>${esc(t("it_username"))}</span><input id="userIn" data-in="username" value="${esc(S.userDraft)}" autocomplete="off" autocapitalize="none" spellcheck="false"></label>
      <p class="sub" role="status">${esc(usernameNote())}</p><button class="primary inline" data-act="takeusername" ${check(S.userDraft).ok ? "" : "disabled"}>${esc(t("save"))}</button>
      ${S.username ? `<div class="qrbox" data-item="qr" role="img" aria-label="${esc(t("shop_qr"))}">${icon("ui-qr", "bigqr")}<p>${esc(t("shop_qr"))}</p></div>` : ""}`; break;
    case "agent_earnings": extra = `<p class="sub">${esc(t("commission_partner_pays"))}</p>${(ent().outlets ?? 0) !== 0 ? `<ul class="list card">${S.outletList.map((o) => row(o, t("outlet_line"), `outlet:${o}`)).join("")}</ul>` : ""}`; break;
    case "team": extra = `<label class="switch"><span>${esc(t("staff_profit"))}</span><input type="checkbox" data-in="perm" ${S.perms.staffSeeProfit ? "checked" : ""} ${canChangeSettings(S.role) ? "" : "disabled"}></label>
      ${canChangeSettings(S.role) ? "" : `<p>${esc(t("owner_only"))}</p>`}<ul class="list card">${S.staff.map((x) => row(x.name, t("role_" + x.role))).join("")}</ul>
      <button class="ghost inline" data-act="invite">${esc(t("invite_staff"))}</button><button class="ghost inline" data-act="clock">${esc(t(S.clockedIn ? "clock_out" : "clock_in"))}</button>`; break;
    case "branches_devices": extra = `<ul class="list card">${S.devices.map((d) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(d.name)}</span><span class="sub">${esc(t(d.revoked ? "revoked" : "active"))}</span></span>${d.revoked ? "" : `<button class="ghost small" data-act="revoke:${d.id}">${esc(t("it_revoke"))}</button>`}</div></li>`).join("")}</ul><p class="sub">${esc(t("wipe_help"))}</p>`; break;
    case "plans_billing": extra = `<ul class="list card">${TIERS.map((k, i) => `<li><button class="rowbtn" data-act="tier:${k}" aria-pressed="${S.tier === k}"><span class="main"><span class="nm">LynkPOS ${esc(t("tier_" + k))}</span><span class="sub">${esc(t("per_month", { amount: formatMoney((DATA.plans[i] ?? 0) * 100, "USD", locale()) }))}</span></span>${S.tier === k ? icon("ui-check") : ""}</button></li>`).join("")}</ul><p class="sub">${esc(t("prices_usd_note"))}</p>`; break;
    case "automations": extra = `<ul class="list card">${DATA.automations.map((a) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(t("auto_" + key(a.id)))}</span><span class="sub">${esc(t("level_" + a.level))}</span></span><label class="switch mini"><span class="sr">${esc(t("it_off_switch"))}</span><input type="checkbox" data-in="auto:${a.id}" ${S.autoOff.has(a.id) ? "" : "checked"}></label></div></li>`).join("")}</ul>
      ${S.runs.slice(0, 3).map((r) => `<div class="card"><p class="nm">${esc(t("auto_" + key(r.auto)))} · ${esc(clock(r.at))}</p><p class="sub">${esc(t("why_" + key(r.auto)))}</p></div>`).join("")}`; break;
    case "academy": extra = `<ul class="list card">${ACADEMY.map((l) => row(t(l), t("minutes_n", { n: 2 }))).join("")}</ul>`; break;
    case "growth": extra = `<label class="switch"><span>${esc(t("passport_share"))}</span><input type="checkbox" data-in="passport" ${S.passport ? "checked" : ""}></label><p class="sub">${esc(t("passport_help"))}</p>`; break;
  }
  const act = (i: string): string => id === "settings" ? `setting:${i}` : i === "statement_match" ? "matchstatement" : i === "wipe" ? "" : "";
  return `${topBar(t("it_" + id), back)}<div class="body">${webNote()}${rows(reg.items, act)}${extra}${flash()}</div>`;
}
function usernameNote(): string {
  if (!S.userDraft) return t("username_rules");
  const c = check(S.userDraft);
  return c.ok ? (S.takenNames.has(c.username) ? t("username_taken") : t("username_free", { name: `@${c.username}` })) : t("username_bad_" + c.reason);
}

// ---- Settings (41 E, 44 L): owner changes; on a computer that is not registered a change needs a fresh check (44 C) ------------
const SETTING_ITEMS: Record<string, string[]> = {
  business_profile: ["shop_name", "business_type", "address", "logo"], receipts: ["receipt_footer", "receipt_qr", "receipt_language"], taxes: ["tax_rate", "prices_include_tax", "tax_pending"],
  payment_methods: PAY_WAYS.map((w) => "way_" + w.id), printers_scanners: ["printer", "scanner", "drawer"], language_region: ["language", "region", "currency"],
  notifications: ["n_sales", "n_stock", "n_chats", "quiet_hours"], data_saver: ["lite_mode", "images_wifi"], modes: ["low_literacy", "practice_mode", "sunlight"],
  ad_categories: ["ads_contextual", "ads_never_protected"], lock: ["pin_lock", "idle_lock"], data_privacy: ["export_data", "delete_business"],
  connected_apps: ["no_apps"], data_sharing: ["share_supplier", "share_health", "share_passport"],
};
function settingScreen(id: string): string {
  const owner = canChangeSettings(S.role), fresh = S.size === "web" && webRule("settings_change", false) === "step_up";
  const items = SETTING_ITEMS[id] ?? [];
  const sw = (k: string): string => `<li data-item="${k}"><label class="switch"><span>${esc(t(k.startsWith("way_") ? k : "st_" + k))}</span><input type="checkbox" data-in="set:${k}" ${S.toggles.has(k) ? "checked" : ""} ${owner ? "" : "disabled"}></label></li>`;
  const body = id === "language_region"
    ? `<ul class="list card">${row(t("st_language"), PACKS[S.lang]?.native ?? S.lang)}${row(t("st_region"), pack().sample ? t("sample_country") : pack().name)}${row(t("st_currency"), pack().currency)}</ul><button class="ghost inline" data-act="localecard">${esc(t("change"))}</button>`
    : id === "connected_apps" ? `<p class="info">${esc(t("st_no_apps"))}</p>`
    : id === "taxes" ? `<ul class="list card">${row(t("st_tax_rate"), t("from_country_pack"))}${sw("prices_include_tax")}</ul><p class="sub">${esc(t("not_tax"))}</p>`
    : id === "business_profile" ? `<ul class="list card">${row(t("st_shop_name"), shop())}${row(t("st_business_type"), t("type_" + S.btype))}${row(t("st_address"), t("not_set"))}${row(t("st_logo"), t("logo_rule"))}</ul>`
    : id === "data_privacy" ? `<ul class="list card">${row(t("st_export_data"), "", "exportfile")}${row(t("st_delete_business"), t("owner_only"))}</ul>`
    : `<ul class="list card">${items.map(sw).join("")}</ul>`;
  return `${topBar(t("it_" + id), "hub:settings")}<div class="body" data-setting="${id}">${fresh ? `<p class="info">${icon("ui-info")}<span>${esc(t("fresh_check"))}</span></p>` : ""}${owner ? "" : `<p class="info">${esc(t("owner_only"))}</p>`}${body}${flash()}</div>`;
}

// ---- notifications and the account menu (41 B) ---------------------------------------------------------------------------
function notifications(): string {
  return `${topBar(t("notifications"), "view:main")}<div class="body"><ul class="list card" data-item="list">${S.notices.map((n) => `<li><div class="rowbtn static${n.read ? "" : " unread"}"><span class="main"><span class="nm">${esc(t(n.key, n.vars))}</span><span class="sub">${esc(clock(n.at))}</span></span></div></li>`).join("") || `<li><p class="info">${esc(t("no_notifications"))}</p></li>`}</ul></div>`;
}
function account(): string {
  const it = (k: string, value: string, act = ""): string => row(t("am_" + k), value, act).replace("<li>", `<li data-item="${k}">`);
  return `${topBar(t("account"), "view:main")}<div class="body"><ul class="list card">${it("name_lynkid", "LOID-····-····-" + S.lynkTail, "copyid")}${it("switch_business", shop(), "view:choose")}${it("switch_role", t("role_" + S.role), "switchrole")}
    ${it("language_region", `${PACKS[S.lang]?.native ?? S.lang} · ${pack().currency}`, "localecard")}${it("theme", t("theme_" + S.theme), "theme")}${it("security_center", "account.lynkomni.com/security")}${it("help", "", "help")}${it("sign_out", "", "signout")}</ul>${flash()}</div>`;
}

// ---- agent point mode (42 C, 42 I): online only; the partner alone confirms; the cash is the agent's own --------------------
const partner = (id = S.partner): Partner => PARTNERS.find((p) => p.id === id) ?? (PARTNERS[0] as Partner);
const usual = (p: Partner): number => Math.max(...S.reqs.filter((r) => r.partner === p.id && r.state === "confirmed").map(() => 120_000), 120_000);
const feeFor = (amount: number): number => Math.max(100, Math.floor(amount / 100));
/** What the agent types is in whole units of the money (500, not 50000 cents); the event carries integer minor units. */
const toMinor = (typed: string): number => { const d = new Intl.NumberFormat("en", { style: "currency", currency: pack().currency }).resolvedOptions().maximumFractionDigits ?? 2; return Number(typed || 0) * 10 ** d; };
const outletsAllowed = (): boolean => (ent().outlets ?? 0) !== 0;
function agentHome(): string {
  const mine = S.reqs.filter((r) => S.outlet === "all" || r.outlet === S.outlet), today = mine.filter((r) => r.state === "confirmed");
  const com = today.reduce((a, r) => a + r.commission, 0);
  const floats = PARTNERS.map((p) => `<div class="kv"><span>${esc(t("float_at", { partner: t(p.name) }))}</span><strong>${esc(money(p.float))}</strong></div>${lowFloat(p.float, usual(p)) ? `<p class="alert low">${icon("ui-warning")}<span>${esc(t("low_float"))}</span></p>` : ""}`).join("");
  const outletPick = outletsAllowed() ? `<label class="field" data-item="outlets"><span>${esc(t("outlet"))}</span><select data-in="outlet"><option value="all" ${S.outlet === "all" ? "selected" : ""}>${esc(t("all_outlets"))}</option>${S.outletList.map((o) => `<option value="${esc(o)}" ${o === S.outlet ? "selected" : ""}>${esc(o)}</option>`).join("")}</select></label>`
    : `<p class="sub" data-item="outlets">${esc(t("outlets_plan"))}</p>`;
  const pic = S.toggles.has("lite_mode") ? "" : `<figure class="agentpic" role="img" aria-label="${esc(t("agent_point_picture"))}">${S.theme === "dark" ? DATA.agentPicture.dark : DATA.agentPicture.light}</figure>`;   // decorative pictures hide in lite mode
  return `${topBar(t("agent_point"))}<div class="body">${pic}${outletPick}<div class="card"><h2>${esc(t("float"))}</h2>${floats}<p class="sub">${esc(t("float_read_live"))}</p></div>
    <div class="duo"><div class="card kpi"><span>${esc(t("cash_in_drawer"))}</span><strong>${esc(money(S.cashIn))}</strong></div><div class="card kpi"><span>${esc(t("commission"))}</span><strong>${esc(money(com))}</strong><small>${esc(t("today_services", { n: today.length, amount: money(com) }))}</small></div></div>
    ${S.cashChecks.has("day_start") ? "" : `<button class="alert low" data-act="view:cashcheck">${icon("ui-warning")}<span>${esc(t("day_start_check"))}</span>${icon("ui-chevron-right", "ic fwd")}</button>`}
    <button class="big" data-act="tab:services">${icon("ui-grid")}<span>${esc(t("services"))}</span></button>
    <div class="quick"><button data-act="view:cashcheck">${esc(t("cash_check"))}</button><button data-act="hub:agent_earnings">${esc(t("it_agent_earnings"))}</button><button data-act="hub:daily_close">${esc(t("it_daily_close"))}</button></div>
    <div class="card"><h2>${esc(t("commissions"))}</h2>${mine.slice(0, 4).map((r) => `<div class="kv"><span>${esc(t(`svc_${r.service}`))} · ${esc(money(r.amount))}</span>${chip(r.state)}</div>`).join("") || `<p>${esc(t("no_sales_yet"))}</p>`}</div>
    <label class="switch" data-item="health_consent"><span>${esc(t("health_consent"))}</span><input type="checkbox" data-in="health" ${S.shared.has("health") ? "checked" : ""}></label><p class="sub">${esc(t("health_consent_help"))}</p></div>`;
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
      <p>${esc(t(r.state === "sent" ? "request_sent" : done ? "request_confirmed" : "request_failed"))}</p>${r.reason ? `<p class="sub">${esc(r.reason)}</p>` : ""}
      ${done ? `<div class="kv"><span>${esc(t("commission"))}</span><strong>${esc(money(r.commission))}</strong></div>` : ""}</div>
      ${done || r.state === "sent" ? `<div class="receipt" data-item="one_receipt"><span class="nm">${esc(t("receipt"))} ${esc(r.receipt)}</span><span>${esc(t("partner_ref"))}: ${esc(r.ref || t("st_sent"))}</span><span>${chip(r.state)}</span><span class="verify">${icon("ui-qr")}<span>${esc(t("verify_receipt"))}</span></span></div>` : ""}
      ${cashOut ? `<button class="primary inline" data-act="handcash" ${mayHandOverCash(r.state) ? "" : "disabled"}>${esc(t("hand_over_cash"))}</button><p class="note">${esc(t("never_before_confirmed"))}</p>` : ""}
      ${r.state === "sent" && S.outcome === "silent" ? `<p class="info">${icon("ui-info")}<span>${esc(t("partner_silent"))}</span></p>` : ""}
      ${done || r.state === "failed" ? `<button class="ghost inline" data-act="tab:services">${esc(t("close"))}</button>` : ""}</div>`;
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
      ${days !== null ? `<p class="sub">${esc(t("float_forecast", { days: days.toFixed(1) }))}</p>` : ""}<p class="sub">${esc(t("topup_partner"))}</p></div>`; }).join("")}
    <div class="card"><div class="kv"><span>${esc(t("cash_in_drawer"))}</span><strong>${esc(money(S.cashIn))}</strong></div><button class="ghost" data-act="view:cashcheck">${esc(t("cash_check"))}</button></div><p class="info">${icon("ui-info")}<span>${esc(t("float_read_live"))}</span></p></div>`;
}
/** Cash checks at day start, day end and shift handover (42 I): a difference is flagged for the owner, never blocking. */
function cashCheck(): string {
  return `${topBar(t("cash_check"), "view:main")}<div class="body"><div class="reasons">${COUNT_KINDS.filter((k) => k !== "spot").map((k) => `<button data-act="checkkind:${k}" aria-pressed="${S.countKind === k}" data-item="${k}">${esc(t("ck_" + k))}${S.cashChecks.has(k) ? " ✓" : ""}</button>`).join("")}</div>
    <div class="kv"><span>${esc(t("expected_in_drawer"))}</span><strong>${esc(money(S.cashIn))}</strong></div>
    <label class="field"><span>${esc(t("counted"))}</span><input id="checkIn" inputmode="numeric" autocomplete="off" value="${esc(S.input)}" data-in="cashnum"></label>
    <button class="primary inline" data-act="agentcount" ${S.input ? "" : "disabled"}>${esc(t("save"))}</button><p class="sub">${esc(t("difference_never_blocks"))}</p>${flash()}</div>`;
}
function agentCount(): void {
  const got = toMinor(S.input), countId = newId();
  emit("CashCounted", { count_id: countId, shift_id: S.shift?.id ?? newId(), kind: S.countKind, counted_cash: got, expected_cash: S.cashIn, currency: pack().currency });
  if (got !== S.cashIn) { emit("CashDifferenceFlagged", { count_id: countId, difference: got - S.cashIn, currency: pack().currency }, "server"); notice("n_cash_difference", { amount: money(got - S.cashIn) }); }
  S.cashChecks.add(S.countKind); S.input = ""; toast(t(got === S.cashIn ? "no_difference" : "difference_flagged"));
}
function agentSend(): void {
  if (!online() || webRule("agent_service", true) !== "ok") return;
  const p = partner(), isFinance = (FINANCE_PRODUCTS as readonly string[]).includes(S.svc), amount = isFinance ? 0 : toMinor(S.amount);
  const r: AgentReq = { id: newId(), partner: p.id, service: S.svc, number: S.number, amount, fee: feeFor(amount), commission: 0, state: "sent", ref: "", reason: "", at: Date.now(), outlet: S.outlet === "all" ? (S.outletList[0] ?? "") : S.outlet, receipt: publicId("RCP") };
  S.reqs.unshift(r); S.req = r.id;
  if (isFinance) emit("PartnerReferralRecorded", { referral_id: r.id, partner_id: p.id, product: S.svc, fee: 0, currency: pack().currency }, "server");
  else emit("AgentRequestCreated", { request_id: r.id, partner_id: p.id, service: (AGENT_SERVICES as readonly string[]).includes(S.svc) ? S.svc : S.svc === "voucher" || S.svc === "pickup" ? "bills" : S.svc, amount, fee: r.fee, currency: pack().currency, customer_reference: "ref-" + S.number.slice(-4) });
  draw();
  if (S.outcome === "silent" && !isFinance) return;   // the practice partner can stay silent: the request stays sent, no cash changes hands
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
    notice("n_agent_confirmed", { amount: money(amount) });
    draw();
  }, reduced() ? 300 : 2200);
}

// ---- a business without a till (41 E: Home, Invoices, Customers, Chats, Business) -----------------------------------------
/** Invoicing is LynkInv (services/invoicing.py, a cloud service): issued invoices never change (a credit note instead), every
 *  invoice is paid through a LynkCheckout pay link, and an electronic payment counts only when the provider confirms it. */
function invoices(): string {
  return `${topBar(t("tab_invoices"))}<div class="body"><button class="big" data-act="newinvoice">${icon("ui-plus")}<span>${esc(t("new_invoice"))}</span></button>
    <ul class="list card">${S.invoices.map((v) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(v.number)} · ${esc(v.customer)}</span><span class="sub">${esc(v.id)} · ${esc(money(v.amount))}</span></span>${chip(v.state)}</div></li>`).join("") || `<li><p class="info">${esc(t("no_invoices"))}</p></li>`}</ul>
    <p class="sub">${esc(t("invoice_rules"))}</p><p class="sub">${esc(t("full_pages_web", { path: "/invoicing" }))}</p>${flash()}</div>`;
}
function customersTab(): string {
  return `${topBar(ww("tab_customers"))}<div class="body"><ul class="list card">${CUSTOMERS.map((c) => `<li><div class="rowbtn static"><span class="avatar" aria-hidden="true">${esc(c.name.slice(0, 1))}</span><span class="main"><span class="nm">${esc(c.name)}</span><span class="sub">${esc(c.owes ? t("owes", { name: c.name, amount: money(c.owes) }) : t("owes_nothing"))}</span></span>
    ${c.owes ? `<button class="ghost small" data-act="paidcredit:${c.id}">${esc(t("record_paid"))}</button>` : ""}</div></li>`).join("")}</ul>
    <p class="sub">${esc(t("credit_reminders"))}</p><p class="sub">${esc(t("full_pages_web", { path: "/crm" }))}</p>${flash()}</div>`;
}

// ---- restaurant (41 E, 44 I N1: Home, Tables, Kitchen, Chats, Business) -------------------------------------------------
function tablesTab(): string {
  const lim = restaurantLimits(ent()), open = S.tables.filter((x) => x.open).length;
  return `${topBar(t("tab_tables"))}<div class="body"><button class="big" data-act="opentable" ${mayOpenTable(lim, open) ? "" : "disabled"}>${icon("ui-plus")}<span>${esc(t("open_table"))}</span></button>
    <div class="grid">${S.tables.map((x) => `<button class="tile${x.open ? " on" : ""}" data-act="tablesend:${x.id}" ${x.open ? "" : "disabled"}><span class="nm">${esc(t("table", { label: x.label }))}</span><span class="pr">${esc(t(x.open ? "open" : "closed"))}</span>${x.lines.filter((l) => !l.ready).length ? `<span class="qty">${x.lines.filter((l) => !l.ready).length}</span>` : ""}</button>`).join("") || `<p class="info">${esc(t("no_tables"))}</p>`}</div>
    <p class="sub">${esc(lim.tables === null ? "" : `${open}/${lim.tables} · `)}${esc(t(kitchenOutput(lim) === "screen" ? "kitchen_screen" : "printed_tickets"))}</p>
    ${S.tables.filter((x) => x.open && x.lines.length && x.lines.every((l) => l.ready)).map((x) => `<button class="ghost inline" data-act="closetable:${x.id}">${esc(t("close_table"))} · ${esc(t("table", { label: x.label }))}</button>`).join("")}${flash()}</div>`;
}
function kitchenTab(): string {
  const q = S.tables.flatMap((x) => x.lines.filter((l) => !l.ready).map((l) => ({ x, l })));
  return `${topBar(t("tab_kitchen"))}<div class="body"><ul class="list card">${q.map(({ x, l }) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(t("table", { label: x.label }))} · ${esc(item(l.product)?.name ?? "")}</span><span class="sub">${esc(clock(l.at))}</span></span><button class="ghost small" data-act="ready:${x.id}:${l.no}">${esc(t("ready"))}</button></div></li>`).join("") || `<li><p class="info">${esc(t("all_ready"))}</p></li>`}</ul></div>`;
}

// ---- getting in (41 E): sign in, choose the business, register this device, the language and region card, setup, first sale --
function signin(): string {
  const mark = brandMark(DATA.brand.places, "auth-onboarding", S.theme === "dark", "mark");   // sign-in and onboarding: the full logo (30)
  if (S.screen === "phone") {
    return `<div class="signin" data-gi="sign_in">${mark}<h1>${esc(t("welcome"))}</h1><p>${esc(t("works_anywhere"))}</p>
      <label class="field"><span>${esc(t("your_phone"))}</span><input id="phoneIn" inputmode="tel" autocomplete="off" value="${esc(S.phone)}" data-in="phone"></label>
      <p class="note" role="alert">${esc(S.note)}</p><div class="grow"></div><button class="primary" data-act="sendcode" ${S.phone.replace(/\D/g, "").length >= 9 ? "" : "disabled"}>${esc(t("send_code"))}</button></div>`;
  }
  if (S.screen === "code") {
    return `<div class="signin" data-gi="sign_in">${mark}<h1>${esc(t("verify"))}</h1><p>${esc(t("enter_code", { phone: S.phone }))}</p>
      <label class="field"><span>${esc(t("verify"))}</span><input id="codeIn" inputmode="numeric" autocomplete="one-time-code" value="${esc(S.code)}" data-in="code"></label>
      <p class="note" role="alert">${esc(S.note)}</p><p class="info sbx">${icon("ui-info")}<span>${esc(t("sandbox"))}: ${esc(t("code_hint"))}</span></p><div class="grow"></div>
      <button class="primary" data-act="verify" ${S.code.length === 6 ? "" : "disabled"}>${esc(t("verify"))}</button></div>`;
  }
  if (S.screen === "choose") {
    return `<div class="signin" data-gi="choose_business">${mark}<h1>${esc(t("choose_business"))}</h1><ul class="list card">${BUSINESSES.map((b, i) => `<li><button class="rowbtn" data-act="business:${i}"><span class="main"><span class="nm">${esc(b)}</span><span class="sub">${esc(t("role_owner"))}</span></span>${icon("ui-chevron-right", "ic fwd")}</button></li>`).join("")}
      <li><button class="rowbtn" data-act="business:new"><span class="main"><span class="nm">${esc(t("create_business"))}</span></span>${icon("ui-plus", "ic fwd")}</button></li></ul></div>`;
  }
  if (S.screen === "locale") {
    const native = PACKS[S.lang]?.native ?? S.lang;
    return `<div class="signin" data-gi="locale_card">${mark}<h1>${esc(t("locale_title"))}</h1><div class="card"><div class="kv"><span>${esc(t("st_language"))}</span><strong>${esc(native)}</strong></div>
      <div class="kv"><span>${esc(t("st_region"))}</span><strong>${esc(pack().sample ? t("sample_country") : pack().name)}</strong></div><div class="kv"><span>${esc(t("st_currency"))}</span><strong>${esc(pack().currency)}</strong></div></div>
      <div class="grow"></div><button class="primary" data-act="localeok">${esc(t("looks_right"))}</button>${S.lang === "en" ? "" : `<button class="ghost" data-act="english" lang="en" dir="ltr">English</button>`}<button class="linkbtn" data-act="localechange">${esc(t("change_setting"))}</button></div>`;
  }
  if (S.screen === "setup") return setup();
  return `<div class="signin" data-gi="register_device">${mark}${S.enrolled ? `<h1>${esc(t("welcome"))}</h1><p>${esc(t("registered"))}</p><div class="grow"></div><button class="primary" data-act="start">${esc(t("start"))}</button>`
    : `<h1>${esc(t("registering"))}</h1><div class="center"><div class="spinner" aria-hidden="true"></div></div>`}</div>`;
}
/** The setup checklist (41 E): under two minutes, every step skippable, then the first sale. */
function setup(): string {
  const next = nextChecklistStep(S.setupDone, S.setupSkipped);
  const step = (k: ChecklistStep): string => `<li data-item="${k}"><div class="rowbtn static"><span class="main"><span class="nm">${esc(t("cl_" + k))}</span><span class="sub">${esc(S.setupDone.has(k) ? t("done") : S.setupSkipped.has(k) ? t("skipped") : "")}</span></span>${S.setupDone.has(k) ? icon("ui-check") : ""}</div></li>`;
  let body = "";
  switch (next) {
    case "who_for": {
      const kinds = DATA.workspaces.entities[S.entity]?.kinds ?? [];
      body = `<div class="reasons who">${(["person", "company", "organisation"] as Entity[]).map((e) => `<button data-act="entity:${e}" aria-pressed="${S.entity === e}"><strong>${esc(t("entity_" + e))}</strong><span>${esc(t("entity_" + e + "_help"))}</span></button>`).join("")}</div>
        ${kinds.length > 1 ? `<div class="reasons">${kinds.map((k) => `<button data-act="kind:${k}" aria-pressed="${S.kind === k}">${esc(t("kind_" + k))}</button>`).join("")}</div>` : ""}<p class="sub">${esc(t("office_note"))}</p>`; break;
    }
    case "business_name_type": body = `<label class="field"><span>${esc(t("st_shop_name"))}</span><input id="shopIn" data-in="shopname" value="${esc(S.shopName)}" autocomplete="off"></label>
      <div class="reasons">${(["shop", "no_till", "agent_point", "restaurant"] as BusinessType[]).map((b) => `<button data-act="btype:${b}" aria-pressed="${S.btype === b}">${esc(t("type_" + b))}</button>`).join("")}</div>`; break;
    case "currency": body = `<p class="kv"><span>${esc(t("st_currency"))}</span><strong>${esc(pack().currency)}</strong></p><p class="sub">${esc(t("currency_from_region"))}</p>`; break;
    case "first_products": body = `<div class="quick">${FIRST_PRODUCT_WAYS.map((w) => `<button data-act="firstway:${w}" aria-pressed="${S.firstWay === w}">${esc(t("way_add_" + w))}</button>`).join("")}</div>`; break;
    case "invite_staff": body = `<label class="field"><span>${esc(t("staff_phone"))}</span><input id="staffIn" inputmode="tel" data-in="staffphone" value="${esc(S.staffPhone)}" autocomplete="off"></label>`; break;
    case "print_shop_qr": body = `<div class="qrbox" role="img" aria-label="${esc(t("shop_qr"))}">${icon("ui-qr", "bigqr")}<p>${esc(t("shop_qr"))}</p></div>`; break;
    default: body = `<p>${esc(t("setup_ready"))}</p>`;
  }
  return `<div class="signin setup" data-gi="setup"><h1>${esc(t("setup_title"))}</h1><p class="sub">${esc(t("setup_help"))}</p><ul class="list card">${SETUP_CHECKLIST.map(step).join("")}</ul>
    ${next ? `<div class="card"><h2>${esc(t("cl_" + next))}</h2>${body}</div><div class="foot two inline"><button class="ghost" data-act="skipstep:${next}">${esc(t("skip"))}</button><button class="primary" data-act="donestep:${next}">${esc(t("next"))}</button></div>`
      : `<button class="primary" data-act="firstsale" data-gi="first_sale">${esc(t("first_sale"))}</button>`}</div>`;
}

// ---- the router: which register screen is shown, and its address (41 B deep links) --------------------------------------
const TAB_PATHS: Record<string, string> = { services: "/services", float: "/float", tables: "/sell/tables", kitchen: "/sell/kitchen" };
const VIEW_SCREEN: Record<string, string> = { basket: "basket", pay: "pay", cash: "pay", momo: "pay", split: "pay", credit: "pay", waiting: "pay", off: "pay", receipt: "receipt", done: "receipt",
  sales: "sales_today", sale: "sales_today", shift: "shift", practice: "practice", item: "product", add: "add_product", received: "stock_received", count: "stock_count", remove: "stock_remove",
  move: "stock_move", suppliers: "suppliers", reorder: "reorder", marketplace: "marketplace", labels: "labels", import: "import_export", thread: "thread", notifications: "notifications",
  account: "account", setting: "settings", cashcheck: "shift", deliveries: "deliveries", delivery: "delivery" };
function screenId(): string {
  if (S.view === "hub") return S.hub || "business";
  if (S.view === "svc") return "services";
  if (S.view !== "main") return VIEW_SCREEN[S.view] ?? S.tab;
  return S.tab === "invoices" ? "invoicing" : S.tab;
}
const screenPath = (id: string): string => DATA.screens.find((s) => s.id === id)?.path ?? TAB_PATHS[id] ?? "/";

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

function view(): string {
  if (S.screen !== "app") return signin();
  const agent = S.btype === "agent_point";
  let body: string;
  if (S.view === "notifications") body = notifications();
  else if (S.view === "deliveries") body = deliveriesScreen();
  else if (S.view === "delivery") body = deliveryScreen();
  else if (S.view === "account") body = account();
  else if (S.view === "svc") body = agentFlow();
  else if (S.view === "cashcheck") body = cashCheck();
  else if (S.view === "hub" || S.view === "setting") body = business();
  else switch (S.tab) {
    case "services": body = agentServices(); break;
    case "float": body = agentFloat(); break;
    case "sell": body = sell(); break;
    case "stock": body = stock(); break;
    case "chats": body = chats(); break;
    case "invoices": body = invoices(); break;
    case "customers": body = customersTab(); break;
    case "books": body = booksTab(); break;
    case "tables": body = tablesTab(); break;
    case "kitchen": body = kitchenTab(); break;
    case "business": body = business() + shortFooterHtml(new Date(), pack().tz); break;   // the one-line short footer inside apps (26 C)
    default: body = agent ? agentHome() : home();
  }
  const noTabs = S.tab === "sell" && !["main", "done", "receipt", "sales", "shift", "practice"].includes(S.view) || S.view === "thread" || S.view === "svc";
  return `<div class="screen" data-screen="${esc(screenId())}">${body}</div>${noTabs ? "" : tabBar()}${S.sheet ? syncSheet() : ""}${DSH.overlay()}`;
}

function draw(): void {
  const d = $("#display");
  const focus = document.activeElement instanceof HTMLInputElement && d.contains(document.activeElement) ? { id: document.activeElement.id, at: document.activeElement.selectionStart } : null;
  DSH.pictures = S.toggles.has("low_literacy");
  d.className = `display ${S.theme} ${S.size}${S.toggles.has("low_literacy") ? " lowlit" : ""}`;   // picture mode (S4, 43 G): bigger pictures, the word always beside them
  d.lang = S.lang === "xx-rtl" ? "ar" : S.lang === "xx" ? "en" : S.lang;
  d.dir = S.lang === "xx-rtl" ? "rtl" : S.lang === "xx" ? "ltr" : PACKS[S.lang]?.dir ?? "ltr";
  $("#app").innerHTML = view();
  if (focus?.id) { const el = document.getElementById(focus.id) as HTMLInputElement | null; if (el) { el.focus(); if (focus.at !== null) el.setSelectionRange(focus.at, focus.at); } }
  drawStatus();
  const a = document.getElementById("address"); if (a) a.textContent = S.screen === "app" ? address() : "account.lynkomni.com/sign-in";
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

async function enrol(): Promise<void> {
  S.screen = "enrol"; draw();
  let raw: Uint8Array;
  try {   // a real P-256 key pair; the private key never leaves the phone (hardware-backed keys come with the native apps)
    const k = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, false, ["sign", "verify"]);
    raw = new Uint8Array(await crypto.subtle.exportKey("raw", k.publicKey));
  } catch { raw = new Uint8Array([4, ...randomBytes(64)]); }
  const b64 = btoa(String.fromCharCode(...raw)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  window.setTimeout(() => {
    const id = newId();
    emit("DeviceEnrolled", { device_id: id, device_name: "Sample phone", platform: "android", public_key: b64, enrolled_by_user_id: newId() }, "server");
    S.devices.unshift({ id, name: "Sample phone", revoked: false });
    S.enrolled = true; draw();
  }, reduced() ? 0 : 700);
}

// ---- what each tap does -----------------------------------------------------------------------------------------------
function payWith(wayId: string): void {
  const w = payWay(wayId); if (!w) return;
  S.receiptWay = wayId; S.input = "";
  S.view = !wayOk(wayId) ? "off" : wayId === "cash" ? "cash" : wayId === "credit" ? "credit" : "momo";
  draw();
}
function closeDay(): void {
  const sm = summary();
  // the daily closing summary is a LynkStat projection of the day's events (no event of its own); the automation only informs
  run("day-close-prepare"); notice("n_day_closed", { amount: money(sm.total) }); toast(t("saved"));
}
function act(a: string): void {
  const [k, v = ""] = a.split(/:(.*)/s);
  try {
    switch (k) {
      // getting in
      case "sendcode": if (!maySync(S.link, S.forced)) { S.note = t("code_needs_net"); draw(); return; } S.note = ""; S.screen = "code"; draw(); return;
      case "verify": if (S.code === CODE) { S.note = ""; S.screen = "choose"; draw(); } else { S.note = t("wrong_code"); S.code = ""; draw(); } return;
      case "business": if (v === "new") { S.business = 0; S.shopName = ""; S.setupDone.clear(); } else S.business = Number(v) || 0; if (S.enrolled) { S.screen = "locale"; draw(); } else void enrol(); return;
      case "start": S.screen = S.englishOnce || S.setupDone.size ? "app" : "locale"; S.tab = "home"; S.view = "main"; draw(); return;
      case "localeok": S.englishOnce = true; S.screen = S.setupDone.size || S.setupSkipped.size ? "app" : "setup"; draw(); return;
      case "english": S.lang = "en"; ($("#cLang") as HTMLSelectElement).value = "en"; act("localeok"); return;
      case "localechange": case "localecard": $("#cLang").focus(); S.screen = S.screen === "app" ? "app" : "locale"; toast(t("change_with_globe")); return;
      case "btype": S.btype = pick(["shop", "no_till", "agent_point", "restaurant"] as BusinessType[], v, "shop"); ($("#cType") as HTMLSelectElement).value = S.btype; draw(); return;
      case "firstway": S.firstWay = v; draw(); return;
      case "donestep":
        if (v === "first_products" && S.firstWay) addProduct(S.firstWay);
        if (v === "invite_staff" && S.staffPhone) { S.staff.push({ id: newId(), name: S.staffPhone, role: "cashier", pin: false }); S.staffPhone = ""; }
        S.setupDone.add(v); S.screen = "setup"; S.tab = "home"; S.view = "main"; draw(); return;
      case "skipstep": S.setupSkipped.add(v); draw(); return;
      case "firstsale": S.screen = "app"; S.tab = S.btype === "shop" ? "sell" : tabs()[1] as Tab; S.view = "main"; draw(); return;
      case "entity": { const e = pick(["person", "company", "organisation"] as Entity[], v, "company"); S.entity = e; S.kind = DATA.workspaces.entities[e]?.kinds[0] ?? "business";
        S.btype = DATA.workspaces.entities[e]?.default_type ?? "shop"; ($("#cEntity") as HTMLSelectElement).value = e; ($("#cType") as HTMLSelectElement).value = S.btype; draw(); return; }
      case "kind": S.kind = pick([...(DATA.workspaces.entities[S.entity]?.kinds ?? ["business"])], v, S.kind); draw(); return;
      case "deliver": bookDelivery(); return;
      case "delivery": S.delivery = S.deliveries.some((x) => x.id === v) ? v : ""; S.view = "delivery"; draw(); return;
      case "copylink": toast(t("copied")); return;
      // navigation
      case "tab": S.tab = pick(tabs(), v, "home"); S.view = "main"; S.note = ""; S.req = ""; S.hub = ""; S.setting = "";
        if (S.tab === "float") for (const p of PARTNERS) emit("FloatBalanceRead", { partner_id: p.id, balance: p.float, currency: pack().currency, read_at: new Date().toISOString().slice(0, 19) + "Z" }, "server");
        draw(); return;
      case "view": if (v === "choose") { S.screen = "choose"; draw(); return; } S.view = v as View; S.input = ""; S.note = ""; if (v === "notifications") window.setTimeout(() => S.notices.forEach((n) => { n.read = true; }), 0); draw(); return;
      case "hub": S.tab = "business"; S.hub = v; S.setting = ""; S.view = "hub"; draw(); return;
      case "setting": S.setting = v; S.view = "setting"; draw(); return;
      case "sheet": S.sheet = true; draw(); return;
      case "closesheet": S.sheet = false; draw(); return;
      // selling
      case "newsale": newSale(); return;
      case "cat": S.category = v; draw(); return;
      case "add": { const p = item(v); if (p) S.cart.add(p); draw(); return; }
      case "inc": { const l = S.cart.lines().find((x) => x.product.id === v); if (l) S.cart.setQty(v, l.qtyMilli + 1000); draw(); return; }
      case "dec": { const l = S.cart.lines().find((x) => x.product.id === v); if (l) S.cart.setQty(v, l.qtyMilli - 1000); if (!S.cart.lines().length) S.view = "main"; draw(); return; }
      case "scan": { const p = CATALOG.find((x) => x.barcode); if (p) { S.cart.add(p); toast(t("scanned", { product: p.name })); } return; }
      case "voice": { for (const [id, q] of parseVoice(t("voice_sample"), CATALOG)) { const p = item(id); if (p) S.cart.add(p, P(q)); } toast(t("heard", { text: t("voice_sample") })); return; }
      case "way": payWith(v); return;
      case "cash": S.input = v; draw(); return;
      case "paycash": { const g = Number(S.input || "0"); if (g >= total()) { payPart("cash", total(), g); finishPay(); } return; }
      case "payonline": { const p = payPart(S.receiptWay || "mobile_money", total()); if (p && online()) askProvider(S.current as Sale, p); finishPay(); return; }
      case "paycredit": if (!creditNeedsCustomer("credit", S.customer || null)) { payPart("credit", total()); finishPay(); } return;
      case "splitadd": { const n = Number(S.input || "0"); if (n > 0) S.parts.push({ way: v, amount: n }); S.input = ""; draw(); return; }
      case "unsplit": S.parts.splice(Number(v), 1); draw(); return;
      case "paysplit": if (splitCheck(total(), S.parts.map((p) => p.amount)) === "ok") { const tot = total(); for (const p of S.parts) { const q = payPart(p.way, p.amount, p.way === "cash" ? p.amount : undefined); if (q && payWay(p.way)?.online && online()) askProvider(S.current as Sale, q); } void tot; finishPay(); } return;
      case "retry": { const s = S.current, p = lastPayment(); if (s && p) { const q = paymentPayload(newId(), s.sale.sale_id, p.method, p.amount); s.payments.push(q); emit("PaymentRecorded", { ...q, currency: pack().currency }); if (online()) askProvider(s, q); S.view = "waiting"; draw(); } return; }
      case "receipt": S.receiptWay = v; if (v !== "print" && v !== "qr" && !online()) { toast(t("st_queued")); return; } toast(t("rc_done_" + v)); return;
      case "sale": S.selected = v; S.returnQty = 1; S.view = "sale"; draw(); return;
      case "reprint": { const s = S.sales.find((x) => x.sale.sale_id === S.selected); if (s) emit("ReceiptIssued", { receipt_id: newId(), sale_id: s.sale.sale_id, receipt_number_local: s.sale.receipt_number_local, copy_number: 2, validity: "provisional" }); toast(t("reprinted")); return; }
      case "void": voidSale(v); return;
      case "return": returnSale(v); return;
      case "rqty": S.returnQty = Math.max(1, S.returnQty + Number(v)); draw(); return;
      case "openshift": openShift(); return;
      case "countkind": S.countKind = pick(COUNT_KINDS as readonly string[], v, "spot") as (typeof COUNT_KINDS)[number]; draw(); return;
      case "countcash": countCash(false); return;
      case "closeshift": countCash(true); return;
      case "notify": S.notified.add(v); toast(t("notify_done")); return;
      // stock
      case "product": S.product = v; S.qty = 1; S.tab = "stock"; S.view = "item"; draw(); return;
      case "qty": S.qty = Math.max(1, S.qty + Number(v)); draw(); return;
      case "stock": stockAct(v); return;
      case "sfilter": S.stockFilter = pick(STOCK_FILTERS as readonly string[], v, "all") as (typeof STOCK_FILTERS)[number]; draw(); return;
      case "addway": addProduct(v); return;
      case "countmode": S.countMode = v === "partial" ? "partial" : "full"; draw(); return;
      case "draftorder": draftOrder(); return;
      case "sendorder": { const o = S.orders.find((x) => x.id === v); if (o) { o.state = "sent"; toast(t("purchase_order_sent")); } return; }
      case "printlabel": toast(t("label_printed")); return;
      case "importfile": toast(t("import_done")); return;
      case "exportfile": toast(t("export_done")); return;
      // chats
      case "cfilter": S.chatFilter = pick(CHAT_FILTERS as readonly string[], v, "all") as (typeof CHAT_FILTERS)[number]; draw(); return;
      case "thread": { S.thread = v; S.view = "thread"; S.setting = ""; const th = S.threads.find((x) => x.id === v); if (th) th.unread = 0; draw(); return; }
      case "send": sendMsg(); return;
      case "tact": threadAct(v); return;
      case "reply": S.draft = t(v); S.setting = ""; draw(); return;
      case "original": S.showOriginal = !S.showOriginal; draw(); return;
      // the Business hub
      case "closeday": closeDay(); return;
      case "ask": S.answer = S.ask.trim() ? t("assist_answer", { sales: money(summary().total), n: summary().count }) : ""; draw(); return;
      case "takeusername": { const c = check(S.userDraft); if (c.ok && !S.takenNames.has(c.username)) { S.username = c.username; S.takenNames.add(c.username); toast(t("saved")); } else draw(); return; }
      case "outlet": S.outlet = v; S.tab = "home"; S.view = "main"; draw(); return;
      case "invite": toast(t("invite_sent")); return;
      case "clock": S.clockedIn = !S.clockedIn; if (S.clockedIn) S.clockId = newId(); emit(S.clockedIn ? "ClockedIn" : "ClockedOut", { clock_id: S.clockId, employee_id: S.staff[0]?.id ?? newId() }); draw(); return;
      case "revoke": { const d = S.devices.find((x) => x.id === v); if (d) { d.revoked = true; emit("DeviceRevoked", { device_id: d.id, revoked_by_user_id: S.staff[0]?.id ?? newId(), reason: "other" }, "server"); toast(t("revoked")); } return; }
      case "tier": S.tier = pick(TIERS as readonly string[], v, "free") as (typeof TIERS)[number]; ($("#cTier") as HTMLSelectElement).value = S.tier; draw(); return;
      case "matchstatement": toast(t("statement_matched", { n: S.reqs.filter((r) => r.state === "confirmed").length })); return;
      // account menu
      case "copyid": toast(t("copied")); return;
      case "switchrole": S.role = S.role === "owner" ? "manager" : S.role === "manager" ? "cashier" : "owner"; ($("#cRole") as HTMLSelectElement).value = S.role; draw(); return;
      case "theme": S.theme = S.theme === "dark" ? "light" : "dark"; ($("#cDark") as HTMLInputElement).checked = S.theme === "dark"; draw(); return;
      case "help": DSH.act("dsh:help"); return;
      case "signout": S.screen = "phone"; S.code = ""; S.view = "main"; S.tab = "home"; draw(); return;
      // agent point
      case "svc": S.svc = pick(AGENT_ALL as readonly string[], v, "bills"); S.view = "svc"; S.req = ""; S.amount = ""; S.number = ""; draw(); return;
      case "agentsend": agentSend(); return;
      case "handcash": { const r = S.reqs.find((x) => x.id === S.req); if (r && mayHandOverCash(r.state)) { S.cashIn -= r.amount; toast(t("done")); } return; }
      case "checkkind": S.countKind = pick(COUNT_KINDS as readonly string[], v, "day_start") as (typeof COUNT_KINDS)[number]; draw(); return;
      case "agentcount": agentCount(); return;
      // without a till
      case "newinvoice": { const c = CUSTOMERS[S.invoices.length % CUSTOMERS.length] as Customer; S.invoices.unshift({ id: publicId("INV"), number: `A-${String(S.invoices.length + 1).padStart(4, "0")}`, customer: c.name, amount: 25_000, state: online() ? "sent" : "queued" }); toast(t("invoice_created")); return; }
      case "paidcredit": { const c = cust(v); if (c && c.owes) { emit("CustomerCreditPaid", { payment_id: newId(), credit_id: newId(), amount: c.owes, currency: pack().currency, method: "cash" }); c.owes = 0; toast(t("saved")); } return; }
      // restaurant
      case "opentable": { const id = newId(), label = String(S.tables.length + 1); S.tables.push({ id, label, open: true, lines: [] }); emit("TableOpened", { table_id: id, table_label: label, covers: 2 }); draw(); return; }
      case "tablesend": { const x = S.tables.find((y) => y.id === v); const p = CATALOG[S.tables.length % CATALOG.length]; if (x && p) { const oid = newId(), no = x.lines.length + 1; x.lines.push({ order: oid, no, product: p.id, ready: false, at: Date.now() }); emit("OrderSentToKitchen", { order_id: oid, table_id: x.id, lines: [{ line_no: no, product_id: p.id, quantity_milli: 1000 }] }); toast(t("sent_to_kitchen")); } return; }
      case "ready": { const [tid, no] = v.split(":"); const x = S.tables.find((y) => y.id === tid); const l = x?.lines.find((y) => y.no === Number(no)); if (l) { l.ready = true; emit("KitchenItemReady", { order_id: l.order, line_no: l.no }); } draw(); return; }
      case "closetable": { const x = S.tables.find((y) => y.id === v); if (x) { x.open = false; emit("TableClosed", { table_id: x.id }); } draw(); return; }
    }
  } catch (e) { S.note = e instanceof PosError ? e.reason : String(e); draw(); }
}

// ---- controls beside the phone ---------------------------------------------------------------------------------------
function onInput(el: HTMLInputElement): void {
  const k = el.dataset["in"] ?? "", digits = (n: number): string => el.value.replace(/\D/g, "").slice(0, n);
  switch (k) {
    case "cash": case "split": case "cashnum": S.input = digits(9); draw(); return;
    case "momo": S.input = el.value.replace(/[^\d ]/g, "").slice(0, 15); draw(); return;
    case "phone": S.phone = el.value.replace(/[^\d +]/g, "").slice(0, 16); draw(); return;
    case "code": S.code = digits(6); draw(); return;
    case "msg": S.draft = el.value.slice(0, 500); return;
    case "anum": S.number = el.value.replace(/[^\d ]/g, "").slice(0, 16); draw(); return;
    case "aamt": S.amount = digits(9); draw(); return;
    case "discount": S.discount = Math.min(S.cart.total(), Number(digits(9) || "0")); draw(); return;
    case "salenote": S.saleNote = el.value.slice(0, 140); return;
    case "search": S.search = el.value.slice(0, 60); draw(); return;
    case "ask": S.ask = el.value.slice(0, 200); return;
    case "username": S.userDraft = el.value.slice(0, 40); draw(); return;
    case "shopname": S.shopName = el.value.slice(0, 60); return;
    case "staffphone": S.staffPhone = el.value.replace(/[^\d +]/g, "").slice(0, 16); return;
  }
}
function onChange(el: HTMLInputElement & HTMLSelectElement): void {
  const k = el.dataset["in"] ?? "";
  if (k.startsWith("set:")) { if (canChangeSettings(S.role)) { const x = k.slice(4); if (el.checked) S.toggles.add(x); else S.toggles.delete(x); if (x === "practice_mode") S.practice = el.checked; } draw(); return; }
  if (k.startsWith("auto:")) { const x = k.slice(5); if (el.checked) S.autoOff.delete(x); else S.autoOff.add(x); draw(); return; }
  switch (k) {
    case "perm": if (canChangeSettings(S.role)) S.perms = { staffSeeProfit: el.checked }; break;
    case "forced": S.forced = el.checked; break;
    case "restock": S.restock = el.checked; break;
    case "practice": S.practice = el.checked; if (el.checked) S.toggles.add("practice_mode"); else S.toggles.delete("practice_mode"); break;
    case "passport": S.passport = el.checked; break;
    case "health": if (el.checked) S.shared.add("health"); else S.shared.delete("health"); break;
    case "partner": S.partner = pick(PARTNERS.map((p) => p.id), el.value, PARTNERS[0]?.id ?? ""); break;
    case "customer": S.customer = CUSTOMERS.some((c) => c.id === el.value) ? el.value : ""; break;
    case "product": S.product = item(el.value) ? el.value : S.product; break;
    case "supplier": S.supplier = el.value; break;
    case "moveto": S.moveTo = pick(BRANCHES, el.value, "north"); break;
    case "category": S.category = el.value; break;
    case "branch": S.branch = el.value === "all" ? "all" : pick(BRANCHES, el.value, "main"); break;
    case "outlet": S.outlet = el.value; break;
    default: return;
  }
  draw();
}
/** Test and demo hook: open any register screen directly (its deep link), as tests/test_business_app.py does. */
function go(id: string): void {
  S.screen = "app"; S.sheet = false; S.hub = ""; S.setting = ""; S.practice = id === "practice";
  const sell: Record<string, View> = { sell: "main", basket: "basket", pay: "pay", receipt: "receipt", sales_today: "sales", shift: "shift", practice: "practice" };
  const stockV: Record<string, View> = { stock: "main", product: "item", add_product: "add", stock_received: "received", stock_count: "count", stock_remove: "remove", stock_move: "move", suppliers: "suppliers", reorder: "reorder", marketplace: "marketplace", labels: "labels", import_export: "import" };
  if (id in sell) {
    if (S.btype !== "shop") S.btype = "shop";
    S.tab = "sell"; S.view = sell[id] as View;
    if ((id === "basket" || id === "pay" || id === "receipt") && !S.cart.count()) S.cart.add(CATALOG[0] as Item);
    if (id === "receipt" && !S.current) { payPart("cash", total(), total()); }
    if (id === "sales_today") { if (!S.sales.length) { S.cart.add(CATALOG[0] as Item); payPart("cash", total(), total()); S.current = null; S.cart.clear(); } S.selected = S.sales[0]?.sale.sale_id ?? ""; S.view = "sale"; }
    if (id === "shift" && !S.shift) { S.input = "0"; openShift(); S.flash = ""; }
    if (id === "practice") S.practice = true;
  } else if (id in stockV) { S.btype = "shop"; S.tab = "stock"; S.view = stockV[id] as View; if (id === "product") S.product = CATALOG[0]?.id ?? ""; }
  else if (id === "home") { S.tab = "home"; S.view = "main"; }
  else if (id === "chats") { S.tab = "chats"; S.view = "main"; }
  else if (id === "thread") { S.tab = "chats"; S.thread = S.threads[1]?.id ?? ""; S.view = "thread"; }
  else if (id === "business") { S.tab = "business"; S.view = "main"; }
  else if (id === "settings") { S.tab = "business"; S.hub = "settings"; S.view = "hub"; }
  else if (id === "notifications" || id === "account") { S.view = id; }
  else if (id === "deliveries" || id === "delivery") { S.tab = "home"; S.view = id;
    if (!S.deliveries.length) { S.btype = "shop"; S.cart.add(CATALOG[0] as Item); payPart("cash", total(), total()); bookDelivery(); } S.view = id; }
  else { S.tab = "business"; S.hub = id; S.view = "hub"; }
  draw();
}
function wire(): void {
  document.addEventListener("click", (ev) => {
    const target = ev.target as HTMLElement;
    const el = target.closest<HTMLElement>("[data-act]");
    if (!el || (el as HTMLButtonElement).disabled) return;
    if (el.dataset["act"] === "closesheet" && el.classList.contains("scrim") && target.closest("[data-stop]")) return;   // taps inside the sheet
    const a = el.dataset["act"] ?? "";
    if (el.classList.contains("dsh-scrim") && target.closest("[data-stop]")) return;
    if ((a.startsWith("dsh:") || DSH.panel) && DSH.act(a)) return;   // the shell panels (search, help) handle their own taps
    act(a);
  });
  const display = $("#display");
  display.addEventListener("input", (ev) => { if (!DSH.input(ev.target as HTMLInputElement)) onInput(ev.target as HTMLInputElement); });
  display.addEventListener("change", (ev) => onChange(ev.target as HTMLInputElement & HTMLSelectElement));
  display.addEventListener("keydown", (ev) => {
    const el = ev.target as HTMLElement;
    if (ev.key === "Enter" && el.dataset["in"] === "msg") { S.draft = (el as HTMLInputElement).value; sendMsg(); ev.preventDefault(); }
    if (ev.key === "Escape" && S.sheet) { S.sheet = false; draw(); }
  });
  document.addEventListener("keydown", (ev) => { if (S.screen === "app" && !S.sheet) DSH.key(ev); });
  const bind = (id: string, f: (el: HTMLInputElement & HTMLSelectElement) => void): void => { const el = $<HTMLInputElement & HTMLSelectElement>(id); el.addEventListener("change", () => f(el)); };
  bind("#cLink", (el) => { S.link = el.value as Link; draw(); });
  bind("#cRole", (el) => { S.role = pick(["owner", "manager", "cashier"] as Role[], el.value, "owner"); draw(); });
  bind("#cType", (el) => { S.btype = pick(["shop", "no_till", "agent_point", "restaurant"] as BusinessType[], el.value, "shop"); S.tab = "home"; S.view = "main"; S.hub = ""; draw(); });
  bind("#cEntity", (el) => { act(`entity:${el.value}`); S.tab = "home"; S.view = "main"; S.hub = ""; draw(); });
  bind("#cSize", (el) => { S.size = el.value === "tablet" ? "tablet" : el.value === "web" ? "web" : "phone"; $("#device").className = `device ${S.size}`; fit(); draw(); });
  bind("#cTier", (el) => { S.tier = pick(TIERS as readonly string[], el.value, "free") as (typeof TIERS)[number]; draw(); });
  bind("#cOutcome", (el) => { S.outcome = el.value === "fail" ? "fail" : el.value === "silent" ? "silent" : "confirm"; });
  bind("#cDark", (el) => { S.theme = el.checked ? "dark" : "light"; draw(); });
  bind("#cReal", (el) => { S.realUser = el.checked; draw(); });
  const country = $<HTMLSelectElement>("#cCountry");
  country.innerHTML = DATA.packOrder.map((c) => { const p = DATA.packs[c] as CountryPack; return `<option value="${esc(c)}">${esc(p.sample ? t("sample_country") : p.name)}</option>`; }).join("");
  country.addEventListener("change", (e) => { S.country = (e.target as HTMLSelectElement).value; draw(); });
  const sel = $<HTMLSelectElement>("#cLang");
  sel.insertAdjacentHTML("afterbegin", Object.entries(PACKS).map(([code, p]) => `<option value="${esc(code)}" lang="${esc(code)}" dir="${p.dir}">${esc(p.native)}</option>`).join(""));
  sel.value = "en";
  sel.addEventListener("change", () => { S.lang = sel.value; draw(); });
  const screens = $<HTMLSelectElement>("#cScreen");
  screens.innerHTML = DATA.screens.map((s) => `<option value="${esc(s.id)}">${esc(s.path)}</option>`).join("");
  screens.addEventListener("change", () => go(screens.value));
  addEventListener("resize", fit); fit();
  window.setInterval(tick, 350);
  window.setInterval(drawStatus, 30000);
}
function fit(): void {   // scale the whole device down on small screens, never up
  const s = Math.min(1, ($("#rig").clientWidth - 8) / $("#device").offsetWidth);
  document.documentElement.style.setProperty("--fit", String(s));
}

(window as unknown as { __go: (id: string) => void }).__go = go;
wire(); draw(); drawLog();
