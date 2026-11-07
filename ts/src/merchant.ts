/** LynkOmni merchant app rules (blueprint sections 2 and 5): who sees what on the role-aware home, stock levels and alerts,
 *  the day's summary, the insight of the day and the mode manager. No browser or Node APIs, so the same file runs in the phone
 *  emulator, the real app and the tests. Money is integer minor units; quantities are integer thousandths (1000 = one piece). */
import { lineTotal } from "./pos.js";
import type { SalePayload, PaymentPayload, UserState } from "./pos.js";

/** Roles of the contract ($defs.role). The owner always sees profit; the others only when the owner allows it. */
export const ROLES = ["owner", "manager", "cashier"] as const;
export type Role = (typeof ROLES)[number];
export interface Permissions { staffSeeProfit: boolean }
export const canSeeProfit = (role: Role, p: Permissions): boolean => role === "owner" || p.staffSeeProfit;
/** Settings that change what others may do (permissions, removing staff) stay with the owner. */
export const canChangeSettings = (role: Role): boolean => role === "owner";

/** Blocks of the home screen, in order, for each role (section 5). */
export type HomeBlock = "sales" | "profit" | "new_sale" | "alerts" | "chats" | "insight" | "stock_check" | "pending";
export function homeBlocks(role: Role, p: Permissions): HomeBlock[] {
  const money: HomeBlock[] = canSeeProfit(role, p) ? ["sales", "profit"] : role === "cashier" ? [] : ["sales"];
  return role === "owner" ? [...money, "new_sale", "alerts", "chats", "insight", "pending"]
    : [...money, "new_sale", "stock_check", "alerts", "chats", "pending"];
}

export interface StockItem { productId: string; cost: number; reorderAtMilli: number }
export type Levels = Record<string, number>;

/** Stock after a sale. A sale is NEVER blocked: stock may go below zero and is flagged for the owner instead. */
export function afterSale(levels: Levels, sale: SalePayload): Levels {
  const out = { ...levels };
  for (const l of sale.lines) out[l.product_id] = (out[l.product_id] ?? 0) - l.quantity_milli;
  return out;
}
export function adjust(levels: Levels, productId: string, deltaMilli: number): Levels {
  if (!Number.isSafeInteger(deltaMilli) || deltaMilli === 0) throw new Error("invalid_quantity");
  return { ...levels, [productId]: (levels[productId] ?? 0) + deltaMilli };
}
/** A count replaces the level; the difference is what the device believed, kept for the owner. */
export function counted(levels: Levels, productId: string, countedMilli: number): { levels: Levels; differenceMilli: number } {
  if (!Number.isSafeInteger(countedMilli) || countedMilli < 0) throw new Error("invalid_quantity");
  return { levels: { ...levels, [productId]: countedMilli }, differenceMilli: countedMilli - (levels[productId] ?? 0) };
}

export type StockState = "ok" | "low" | "negative";
export const stockState = (levelMilli: number, reorderAtMilli: number): StockState => (levelMilli < 0 ? "negative" : levelMilli <= reorderAtMilli ? "low" : "ok");
/** Products that need the owner: below zero first (a conflict to look at), then low stock. */
export function stockAlerts(items: readonly StockItem[], levels: Levels): { negative: string[]; low: string[] } {
  const negative: string[] = [], low: string[] = [];
  for (const i of items) {
    const s = stockState(levels[i.productId] ?? 0, i.reorderAtMilli);
    if (s === "negative") negative.push(i.productId); else if (s === "low") low.push(i.productId);
  }
  return { negative, low };
}

/** Cost of a line, rounded half up to a whole minor unit like line totals. */
export const lineCost = (qtyMilli: number, unitCost: number): number => lineTotal(qtyMilli, unitCost, 0);

export interface DaySale { sale: SalePayload; payments: PaymentPayload[]; voided: boolean }
export interface DaySummary {
  count: number; total: number; profit: number;
  cash: number;        // cash in the drawer from today's sales
  confirmed: number;   // non-cash money a provider has confirmed
  waiting: number;     // non-cash money not yet confirmed: never counted as received
  failed: number;
}
/** The daily closing summary. Voided sales do not count. Non-cash money counts as received only when the provider confirmed it. */
export function daySummary(sales: readonly DaySale[], costs: Readonly<Record<string, number>>): DaySummary {
  const s: DaySummary = { count: 0, total: 0, profit: 0, cash: 0, confirmed: 0, waiting: 0, failed: 0 };
  for (const d of sales) {
    if (d.voided) continue;
    s.count += 1; s.total += d.sale.total;
    s.profit += d.sale.lines.reduce((a, l) => a + l.line_total - lineCost(l.quantity_milli, costs[l.product_id] ?? 0), 0);
    const last = d.payments[d.payments.length - 1];
    if (!last) continue;
    if (last.status === "cash_received") s.cash += last.amount;
    else if (last.status === "confirmed") s.confirmed += last.amount;
    else if (last.status === "failed") s.failed += last.amount;
    else s.waiting += last.amount;
  }
  return s;
}

/** One insight for the day (section 5): the best seller by quantity, or nothing before the first sale. */
export function insight(sales: readonly DaySale[]): { productId: string; name: string; qtyMilli: number } | null {
  const q = new Map<string, { name: string; qtyMilli: number }>();
  for (const d of sales) if (!d.voided) for (const l of d.sale.lines) {
    const h = q.get(l.product_id) ?? { name: l.product_name, qtyMilli: 0 };
    h.qtyMilli += l.quantity_milli; q.set(l.product_id, h);
  }
  let best: { productId: string; name: string; qtyMilli: number } | null = null;
  for (const [productId, v] of q) if (!best || v.qtyMilli > best.qtyMilli) best = { productId, ...v };
  return best;
}

/** Mode manager (section 2): the phone switches by itself. A weak link counts as offline with opportunistic syncing, and the
 *  merchant can force offline to save data. Selling works the same in both modes. */
export type Link = "good" | "weak" | "none";
export type Mode = "online" | "offline";
export const mode = (link: Link, forcedOffline: boolean): Mode => (link === "good" && !forcedOffline ? "online" : "offline");
/** Weak links still try to send now and then; a forced offline never sends. */
export const maySync = (link: Link, forcedOffline: boolean): boolean => !forcedOffline && link !== "none";

/** The sync chip: how many items wait, and the least advanced state among them (five-state vocabulary only). */
export function pending(states: readonly UserState[]): { count: number; state: UserState } {
  const waiting = states.filter((s) => s === "queued" || s === "sent");
  return { count: waiting.length, state: waiting.includes("queued") ? "queued" : waiting.length ? "sent" : "accepted" };
}
