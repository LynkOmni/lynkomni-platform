/** N1 Restaurant mode and N8 Delivery rules (TypeScript port of merchant/restaurant.py and merchant/delivery.py, build section 3).
 *  Tables and the kitchen work offline; tips belong to the business; a delivery's proof is a code or a parcel photo, never a person. */
import type { PosEntitlement } from "./business.js";

export const RESTAURANT_TABS = ["home", "tables", "kitchen", "chats", "business"] as const;
export const KITCHEN_WITHOUT_SCREEN = "printed_tickets";
export interface RestaurantLimits { tables: number | null; kitchenScreens: number | null; splitBills: boolean; tips: boolean; tableQrOrdering: boolean; centralMenu: boolean }
export function restaurantLimits(e: PosEntitlement): RestaurantLimits {
  return { tables: e.tables ?? null, kitchenScreens: e.kitchen_screens === undefined ? 0 : e.kitchen_screens, splitBills: !!e.split_bills, tips: !!e.tips, tableQrOrdering: !!e.table_qr_ordering, centralMenu: !!e.central_menu };
}
export const mayOpenTable = (l: RestaurantLimits, openNow: number): boolean => l.tables === null || openNow < l.tables;
export const kitchenOutput = (l: RestaurantLimits): "screen" | typeof KITCHEN_WITHOUT_SCREEN => (l.kitchenScreens === 0 ? KITCHEN_WITHOUT_SCREEN : "screen");
export const tipShareForLynkOmni = (_amount: number): number => 0;        // always zero
export const splitNeedsAtLeast = 2;                                        // one bill is an ordinary sale
export const tableQrPath = (username: string, table: string): string => `shop.lynkomni.com/${username}/tables/${table}`;

export interface KitchenLine { table: string; orderId: string; lineNo: number; ready: boolean }
/** Open kitchen lines in the order they were sent. */
export const kitchenQueue = (lines: readonly KitchenLine[]): KitchenLine[] => lines.filter((l) => !l.ready);
/** A table closes only when every kitchen line of its orders is ready. */
export const mayCloseTable = (lines: readonly KitchenLine[], orderIds: ReadonlySet<string>): boolean => lines.every((l) => !orderIds.has(l.orderId) || l.ready);

// ---- N8 delivery and pickup
export const DELIVERY_STATES = ["sent", "accepted", "picked_up", "delivered", "failed"] as const;
export type DeliveryState = (typeof DELIVERY_STATES)[number];
export const PROOFS = ["code", "photo"] as const;     // never a photo of a person
export interface DeliveryEntitlement { partnerDeliveriesPerMonth: number | null; ownRiders: number | null; routing: boolean }
/** The higher of LynkPOS or LynkCheckout decides (null = unlimited). */
export function deliveryEntitlement(pos: PosEntitlement, checkout: PosEntitlement): DeliveryEntitlement {
  const higher = (a: number | null | undefined, b: number | null | undefined): number | null => (a === null || a === undefined || b === null || b === undefined ? null : Math.max(a, b));
  return { partnerDeliveriesPerMonth: higher(pos.partner_deliveries_per_month, checkout.partner_deliveries_per_month), ownRiders: higher(pos.own_riders, checkout.own_riders), routing: !!(pos.delivery_routing || checkout.delivery_routing) };
}
export interface Quote { partnerId: string; price: number; etaS: number }
/** Several partners, cheapest or fastest, only where the plan routes; otherwise the first partner's quote. */
export function pickQuotes(quotes: readonly Quote[], routing: boolean, prefer: "cheapest" | "fastest" = "cheapest"): Quote[] {
  if (!routing) return quotes.slice(0, 1);
  return [...quotes].sort((a, b) => (prefer === "cheapest" ? a.price - b.price : a.etaS - b.etaS));
}
export const mayRequestPartnerDelivery = (usedThisMonth: number, e: DeliveryEntitlement): boolean => e.partnerDeliveriesPerMonth === null || usedThisMonth < e.partnerDeliveriesPerMonth;
export const mayAddRider = (haveRiders: number, e: DeliveryEntitlement): boolean => e.ownRiders === null || haveRiders < e.ownRiders;
/** What the device may do to a delivery: own riders record steps offline; a partner reports its own. */
export const nextDeliveryStep = (state: DeliveryState): DeliveryState | null => (state === "accepted" ? "picked_up" : state === "picked_up" ? "delivered" : null);
export const DELIVERY_SHARE_CENTS = 10;   // paid by the partner, an assumption until contracts (billing SERVICE_FEES delivery_share_cents)
export const lynkomniShareCents = (partnerDeliveries: number): number => partnerDeliveries * DELIVERY_SHARE_CENTS;

// ---- N11 buy together: no pooled money
export const mayOpenGroup = (tier: string): boolean => tier === "pro" || tier === "max";
export const groupOutcome = (total: number, target: number): "reached" | "failed" => (total >= target ? "reached" : "failed");
export const chargedWhen = (outcome: "reached" | "failed"): boolean => outcome === "reached";   // each shop pays the supplier for its own part; short means nobody pays
