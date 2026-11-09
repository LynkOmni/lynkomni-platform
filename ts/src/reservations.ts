/** Stock reserved at online checkout (port of core/reservations.py, same rules and tests): a Storefront checkout holds free stock
 *  for 15 minutes; the provider's confirmation commits it, a failure or the time releases it; an in-person sale is never blocked
 *  and a clash is flagged for the owner. Quantities are integer thousandths. */
export const HOLD_S = 15 * 60;
export interface Hold { product: string; qty_milli: number; order: string; expires_at: number; state: "held" | "committed" | "released" }
export type Emit = (type: string, payload: Record<string, unknown>) => void;
export class Reservations {
  holds = new Map<string, Hold>();
  constructor(private emit: Emit = () => undefined) {}
  held(product: string, now: number): number { let n = 0; for (const h of this.holds.values()) if (h.product === product && h.state === "held" && h.expires_at > now) n += h.qty_milli; return n; }
  free(product: string, onHand: number, now: number): number { return onHand - this.held(product, now); }
  reserve(id: string, product: string, qty: number, order: string, onHand: number, now: number): { ok: boolean; reason?: string; expires_at?: number; repeat?: boolean } {
    if (!Number.isInteger(qty) || qty <= 0) throw new Error("a quantity is a positive whole number of thousandths");
    if (this.holds.has(id)) return { ok: true, repeat: true };
    if (this.free(product, onHand, now) < qty) return { ok: false, reason: "not_enough_stock" };
    this.holds.set(id, { product, qty_milli: qty, order, expires_at: now + HOLD_S, state: "held" });
    this.emit("StockReserved", { reservation_id: id, product_id: product, quantity_milli: qty, order_ref: order, expires_at: now + HOLD_S });
    return { ok: true, expires_at: now + HOLD_S };
  }
  onPayment(id: string, status: "confirmed" | "failed", _now: number): Hold["state"] | null {
    const h = this.holds.get(id); if (!h || h.state !== "held") return null;
    if (status === "confirmed") { h.state = "committed"; this.emit("StockReservationCommitted", { reservation_id: id, product_id: h.product, quantity_milli: h.qty_milli }); }
    else { h.state = "released"; this.emit("StockReservationReleased", { reservation_id: id, product_id: h.product, reason: "payment_failed" }); }
    return h.state;
  }
  expire(now: number): string[] {
    const out: string[] = [];
    for (const [id, h] of this.holds) if (h.state === "held" && h.expires_at <= now) { h.state = "released"; out.push(id); this.emit("StockReservationReleased", { reservation_id: id, product_id: h.product, reason: "timed_out" }); }
    return out;
  }
  inPersonSale(product: string, qty: number, onHand: number, now: number): { ok: true; on_hand_milli: number; conflict: boolean } {
    const after = onHand - qty, freeAfter = after - this.held(product, now);
    if (freeAfter < 0) this.emit("StockConflictFlagged", { product_id: product, short_milli: -freeAfter, reason: "online_hold" });
    return { ok: true, on_hand_milli: after, conflict: freeAfter < 0 };
  }
}
