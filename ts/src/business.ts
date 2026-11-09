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

export const SETUP_STEPS = ["locale_card", "business_name", "business_type", "first_product"] as const;   // under two minutes
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
