/** The Business app rules shared by every merchant screen (TypeScript port of merchant/business.py and merchant/devices.py,
 *  build section 3). Tabs follow the business type; the web rule says what needs a registered device; a second currency is a
 *  labelled estimate; "Confirmed" shows only when the provider confirms; practice mode is always marked. No browser or Node APIs. */

export const BUSINESS_TYPES = ["shop", "no_till", "agent_point", "restaurant"] as const;
export type BusinessType = (typeof BUSINESS_TYPES)[number];
export const TABS: Record<BusinessType, readonly string[]> = {
  shop: ["home", "sell", "stock", "chats", "business"],
  no_till: ["home", "invoices", "customers", "chats", "business"],
  agent_point: ["home", "services", "float", "chats", "business"],
  restaurant: ["home", "tables", "kitchen", "chats", "business"],
};
export const tabsFor = (t: BusinessType): readonly string[] => TABS[t];

export const SETUP_STEPS = ["locale_card", "who_for", "business_name", "business_type", "first_product"] as const;   // under two minutes

/** Who LynkOmni is for (catalog/workspaces.v1.json; core/workspaces.py): a person, a company or an organisation. The entity changes
 *  words, tabs, categories and suggestions only; records, prices and rules are the same for everyone. */
export interface Workspaces {
  office_families: readonly string[];
  entities: Record<string, { kinds: readonly string[]; default_type: BusinessType; tabs: readonly string[] | null; words: Record<string, string>; suggested: readonly string[];
    categories: { income: readonly { id: string; account: string }[]; expense: readonly { id: string; account: string }[] }; funds?: readonly string[] }>;
}
export const ENTITIES = ["person", "company", "organisation"] as const;
export type Entity = (typeof ENTITIES)[number];
export function workspaceTabs(w: Workspaces, entity: Entity, type: BusinessType): readonly string[] {
  const t = w.entities[entity]?.tabs;
  return t && type === "no_till" ? t : TABS[type];
}
/** The word a screen shows for a key in this workspace (presentation only): customers are contacts for a person, members for an organisation. */
export const workspaceWord = (w: Workspaces, entity: Entity, key: string): string => w.entities[entity]?.words[key] ?? key;
export const categoryAccount = (w: Workspaces, entity: Entity, category: string): string | null =>
  [...(w.entities[entity]?.categories.income ?? []), ...(w.entities[entity]?.categories.expense ?? [])].find((c) => c.id === category)?.account ?? null;
export const isOfficeFamily = (w: Workspaces, family: string): boolean => w.office_families.includes(family);
export type SetupStep = (typeof SETUP_STEPS)[number];
export const nextSetupStep = (done: ReadonlySet<string>): SetupStep | null => SETUP_STEPS.find((s) => !done.has(s)) ?? null;

/** The handheld redesigned around 12 tiles (blueprint 42 I). */
export const HANDHELD_TILES = ["sell", "agent", "collect", "bills", "airtime_data", "tickets", "government", "remittances", "partner_finance", "customers_credit", "reports", "settings"] as const;
export const FAST_CHECKOUT = ["scan", "tap", "voice"] as const;
export const RECEIPT_CHANNELS = ["print", "qr", "message"] as const;
export const BUSINESS_SECTIONS = ["money", "reports", "staff", "devices", "loyalty", "marketplace", "growth", "automations", "settings", "academy"] as const;

/** The web rule (blueprint 44 C): the till needs a registered device; settings in a browser need a fresh check; the rest works anywhere. */
export const TILL_ACTIONS = ["sell", "cash_drawer", "shift", "cash_count", "agent_service", "collection", "partner_finance"] as const;
export const STEP_UP_IN_BROWSER = ["settings_change"] as const;
export type WebRule = "ok" | "registered_device" | "step_up";
export function webRule(action: string, deviceRegistered: boolean): WebRule {
  if ((TILL_ACTIONS as readonly string[]).includes(action)) return deviceRegistered ? "ok" : "registered_device";
  if ((STEP_UP_IN_BROWSER as readonly string[]).includes(action)) return deviceRegistered ? "ok" : "step_up";
  return "ok";
}

/** What the plan allows (billing FEATURES for lynkpos, merged up to the tier; null = unlimited). The emulator gets it from the build data. */
export interface PosEntitlement { devices?: number | null; receipts?: readonly string[]; custom_receipts?: boolean; agent_partners?: number | null; outlets?: number | null;
  tables?: number | null; kitchen_screens?: number | null; split_bills?: boolean; tips?: boolean; table_qr_ordering?: boolean; central_menu?: boolean;
  partner_deliveries_per_month?: number | null; own_riders?: number | null; delivery_routing?: boolean; time_clock?: boolean }
export const receiptChannels = (e: PosEntitlement): readonly string[] => e.receipts ?? ["print", "qr"];
/** Under a limit? null means unlimited. */
export const within = (limit: number | null | undefined, have: number): boolean => limit === null || limit === undefined || have < limit;

/** A second currency beside the sale currency (S7, visitor prices): an estimate at the day's rate; the sale stays in local money. */
export interface SecondCurrency { amount: number; currency: string; estimate: true; saleCurrency: string }
export function secondCurrency(amountMinor: number, saleCurrency: string, shown: string, convert: (minor: number, from: string, to: string) => number): SecondCurrency | null {
  if (shown === saleCurrency) return null;
  return { amount: convert(amountMinor, saleCurrency, shown), currency: shown, estimate: true, saleCurrency };
}

export const practiceLabel = (practice: boolean): string | null => (practice ? "PRACTICE" : null);
/** Fake payment protection: only the provider confirms; a text message or screenshot is not proof. */
export const mayShowConfirmed = (paymentStatus: string): boolean => paymentStatus === "confirmed";
export const PROOF_WARNING_KEY = "payment_proof_warning";

/** Sell by voice (English reference parser; the cashier confirms before the sale is saved). */
const NUMBER_WORDS: Record<string, number> = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, a: 1, an: 1 };
export function parseVoice(text: string, products: readonly { id: string; name: string }[]): [string, number][] {
  const out: [string, number][] = [];
  for (const raw of text.toLowerCase().split(/,| and /)) {
    const part = raw.trim();
    if (!part) continue;
    const m = /^(\d+|[a-z]+)\s+(.*)$/.exec(part);
    let qty: number | undefined = m ? (/^\d+$/.test(m[1] ?? "") ? Number(m[1]) : NUMBER_WORDS[m[1] ?? ""]) : undefined;
    let rest = m ? (m[2] ?? "") : part;
    if (qty === undefined) { qty = 1; rest = part; }
    const hit = products.find((p) => rest.includes(p.name.toLowerCase()) || rest.endsWith(p.name.toLowerCase().replace(/s$/, "")));
    if (hit) out.push([hit.id, qty * 1000]);
  }
  return out;
}

/** The merchant home cards (section 5), in order. */
export function homeCards(role: "owner" | "manager" | "cashier", staffSeeProfit: boolean, pendingSync: number, lowStock: number, negativeStock: number, unreadChats: number): string[] {
  const cards = ["today_sales", ...(role === "owner" || staffSeeProfit ? ["today_profit"] : []), "new_sale"];
  if (lowStock || negativeStock) cards.push("stock_alerts");
  if (unreadChats) cards.push("chats");
  cards.push("insight");
  if (pendingSync) cards.push("pending_sync");
  return cards;
}

export const IDLE_LOCK_S = 120;          // staff PIN lock after two idle minutes
export const SYNC_ORDER = ["sales", "payments", "stock", "chats", "media"] as const;   // priority sync: sales and payments first, media last
export const syncOrder = (pending: Readonly<Record<string, number>>): string[] => SYNC_ORDER.filter((k) => (pending[k] ?? 0) > 0);

// ---- the Business app as blueprint 41 E lays it out (catalog/business-app.v1.json is the register of its screens) --------------

/** Getting in (41 E): sign in, choose the business (if more than one), register this device, the language and region card, the
 *  setup checklist, then the first sale. */
export const GETTING_IN = ["sign_in", "choose_business", "register_device", "locale_card", "setup", "first_sale"] as const;
/** The setup checklist (41 E): every step skippable, under two minutes. First products come by scan, photo, voice, template or import. */
export const SETUP_CHECKLIST = ["who_for", "business_name_type", "currency", "first_products", "invite_staff", "print_shop_qr"] as const;
export const FIRST_PRODUCT_WAYS = ["scan", "photo", "voice", "template", "import"] as const;
export type ChecklistStep = (typeof SETUP_CHECKLIST)[number];
/** The next step to show: the first one neither done nor skipped; null when the checklist is finished (then the first sale). */
export const nextChecklistStep = (done: ReadonlySet<string>, skipped: ReadonlySet<string>): ChecklistStep | null =>
  SETUP_CHECKLIST.find((s) => !done.has(s) && !skipped.has(s)) ?? null;
/** The phone top bar (41 E): emblem, screen title, connection chip, notifications, account. */
export const TOP_BAR = ["emblem", "screen_title", "connection_chip", "notifications", "account"] as const;

/** Every way to take money at the till (41 E, 42 C), how it is recorded in the contract and what it needs. Cash and credit work
 *  offline; every other method is sent and shows confirmed only when the provider confirms (fake payment protection). */
export interface PayWay { id: string; method: "cash" | "mobile_money" | "bank_transfer" | "card" | "credit" | "other"; online: boolean; provider: string | null }
export const PAY_WAYS: readonly PayWay[] = [
  { id: "cash", method: "cash", online: false, provider: null },
  { id: "mobile_money", method: "mobile_money", online: true, provider: "mobile_money" },
  { id: "card", method: "card", online: true, provider: "card" },                  // on the LynkPOS handheld or a terminal
  { id: "tap_to_pay", method: "card", online: true, provider: "tap_to_pay" },       // the phone itself, through a certified acquirer (7)
  { id: "bank_transfer", method: "bank_transfer", online: true, provider: "bank_transfer" },
  { id: "qr", method: "other", online: true, provider: "qr" },                      // LynkCheckout: the customer pays on the pay page
  { id: "pay_link", method: "other", online: true, provider: "pay_link" },
  { id: "credit", method: "credit", online: false, provider: null },                // pay later on credit, with the customer attached
];
export const payWay = (id: string): PayWay | undefined => PAY_WAYS.find((w) => w.id === id);
/** A split payment: the parts must add up to the total exactly (integer minor units), each part above zero. */
export function splitCheck(total: number, parts: readonly number[]): "ok" | "short" | "over" | "empty_part" {
  if (parts.some((p) => !(p > 0))) return "empty_part";
  const sum = parts.reduce((a, b) => a + b, 0);
  return sum === total ? "ok" : sum < total ? "short" : "over";
}
/** A credit sale needs a customer attached (the credit book, S6). */
export const creditNeedsCustomer = (wayId: string, customerId: string | null): boolean => wayId === "credit" && !customerId;

/** Receipt channels by plan (42 C): print and QR on every plan; chat and SMS links from Plus (message receipts). Every receipt
 *  carries a QR the customer can verify (7, Verified receipts) and says it is not a tax receipt until the authority confirms. */
export function receiptOptions(e: PosEntitlement): string[] {
  const allowed = receiptChannels(e);
  return ["print", "qr", ...(allowed.includes("message") ? ["chat_link", "sms_link"] : [])];
}

/** Contract reason codes (contract/event-payloads.v2.json): the screens offer exactly these. */
export const VOID_REASONS = ["entered_in_error", "customer_cancelled", "price_error", "duplicate", "other"] as const;
export const RETURN_REASONS = ["defective", "wrong_item", "customer_changed_mind", "price_error", "other"] as const;
export const REMOVE_REASONS = ["damage", "loss", "theft", "expiry", "correction", "other"] as const;
export const COUNT_KINDS = ["day_start", "day_end", "handover", "spot"] as const;

/** A return: refund at most what was paid for the line; restocking is the cashier's choice per line. */
export function returnLine(soldQtyMilli: number, unitPrice: number, returnQtyMilli: number): { quantity_milli: number; refund_amount: number } {
  const q = Math.max(0, Math.min(soldQtyMilli, returnQtyMilli));
  return { quantity_milli: q, refund_amount: Math.round((q * unitPrice) / 1000) };
}

/** Stock list filters (41 E): low, below zero, category, branch. */
export const STOCK_FILTERS = ["all", "low", "below_zero"] as const;
export function stockFilter<T extends { category: string; branch?: string; reorderAtMilli: number; id: string }>(items: readonly T[], levels: Readonly<Record<string, number>>,
  f: { state: (typeof STOCK_FILTERS)[number]; category: string; branch: string }): T[] {
  return items.filter((p) => {
    const lv = levels[p.id] ?? 0;
    if (f.state === "low" && !(lv >= 0 && lv <= p.reorderAtMilli)) return false;
    if (f.state === "below_zero" && !(lv < 0)) return false;
    if (f.category !== "all" && p.category !== f.category) return false;
    if (f.branch !== "all" && (p.branch ?? "main") !== f.branch) return false;
    return true;
  });
}
/** A move between branches is two adjustments with the same reason, so stock is never created or lost on the way. */
export function moveStock(levels: Readonly<Record<string, Record<string, number>>>, productId: string, from: string, to: string, qtyMilli: number): Record<string, Record<string, number>> {
  if (from === to || qtyMilli <= 0) return { ...levels };
  const out: Record<string, Record<string, number>> = {};
  for (const [b, l] of Object.entries(levels)) out[b] = { ...l };
  out[from] = { ...(out[from] ?? {}), [productId]: (out[from]?.[productId] ?? 0) - qtyMilli };
  out[to] = { ...(out[to] ?? {}), [productId]: (out[to]?.[productId] ?? 0) + qtyMilli };
  return out;
}

/** Chat inbox filters (41 E) and the thread actions. */
export const CHAT_FILTERS = ["unread", "assigned", "orders", "all"] as const;
export const THREAD_ACTIONS = ["send_product", "send_quote", "send_pay_link", "send_receipt", "saved_replies", "photo", "voice_note", "assign_staff"] as const;

/** The Business hub (41 E), in the blueprint's order, with the build section where each service's own full pages are built
 *  (41 S). The hub entry itself is built here; "Coming to your country soon." comes from the country pack and the ledger. */
export const HUB: readonly { id: string; serviceSection: number }[] = [
  { id: "reports", serviceSection: 4 }, { id: "daily_close", serviceSection: 3 }, { id: "money", serviceSection: 3 }, { id: "invoicing", serviceSection: 4 },
  { id: "customers", serviceSection: 4 }, { id: "loyalty", serviceSection: 3 }, { id: "books", serviceSection: 4 }, { id: "growth", serviceSection: 3 },
  { id: "assistant", serviceSection: 3 }, { id: "cards", serviceSection: 3 }, { id: "online_shop", serviceSection: 3 }, { id: "agent_earnings", serviceSection: 3 },
  { id: "team", serviceSection: 3 }, { id: "branches_devices", serviceSection: 3 }, { id: "plans_billing", serviceSection: 3 }, { id: "settings", serviceSection: 3 },
  { id: "academy", serviceSection: 3 }, { id: "automations", serviceSection: 3 },
];
/** Settings (41 E, with 44 L: data sharing). Changing a setting on a computer that is not registered needs a fresh check (44 C). */
export const SETTINGS = ["business_profile", "receipts", "taxes", "payment_methods", "printers_scanners", "language_region", "notifications", "data_saver", "modes", "ad_categories", "lock", "data_privacy", "connected_apps", "data_sharing"] as const;
