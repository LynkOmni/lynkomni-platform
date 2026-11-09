"""Stock reserved at online checkout (BIZZ & DEVICE, section 3). A Storefront buyer's checkout holds the stock it needs for a short
time so two buyers cannot pay for the last item; the hold ends when the licensed provider confirms the payment (the stock is sold)
or when the payment fails or the time runs out (the stock is free again). Quantities are integer thousandths.

Rules:
- Only an online checkout reserves, and only from stock that is free (on hand minus what is already held); if there is not
  enough, the checkout says so before the buyer pays. That is the only place stock ever refuses anything.
- An in-person sale is never blocked, online or offline: if it takes stock that a checkout was holding, the hold stays, the free
  quantity goes below zero, and the owner sees a conflict flag to sort out (never a refusal at the till).
- A hold becomes a sale only on the provider's confirmation (PaymentStatusChanged confirmed), never on the buyer's word.
"""
HOLD_S = 15 * 60
STATES = ("held", "committed", "released")


class Reservations:
    def __init__(self, emit=None):
        self.holds = {}                    # reservation_id -> {product, qty_milli, order, expires_at, state}
        self.emit = emit or (lambda type_, payload: None)

    def held(self, product, now):
        return sum(h["qty_milli"] for h in self.holds.values() if h["product"] == product and h["state"] == "held" and h["expires_at"] > now)

    def free(self, product, on_hand_milli, now):
        """Stock a checkout may still hold: on hand minus live holds (can go below zero after an in-person sale; never blocks it)."""
        return on_hand_milli - self.held(product, now)

    def reserve(self, reservation_id, product, qty_milli, order, on_hand_milli, now):
        if isinstance(qty_milli, bool) or not isinstance(qty_milli, int) or qty_milli <= 0:
            raise ValueError("a quantity is a positive whole number of thousandths")
        if reservation_id in self.holds:
            return {"ok": True, "reservation_id": reservation_id, "repeat": True}
        if self.free(product, on_hand_milli, now) < qty_milli:
            return {"ok": False, "reason": "not_enough_stock"}
        self.holds[reservation_id] = {"product": product, "qty_milli": qty_milli, "order": order, "expires_at": now + HOLD_S, "state": "held"}
        self.emit("StockReserved", {"reservation_id": reservation_id, "product_id": product, "quantity_milli": qty_milli, "order_ref": order, "expires_at": now + HOLD_S})
        return {"ok": True, "reservation_id": reservation_id, "expires_at": now + HOLD_S}

    def on_payment(self, reservation_id, provider_status, now):
        """The provider's answer for the checkout: confirmed commits the hold (the stock is sold), failed releases it."""
        h = self.holds.get(reservation_id)
        if not h or h["state"] != "held":
            return None
        if provider_status == "confirmed":
            h["state"] = "committed"
            self.emit("StockReservationCommitted", {"reservation_id": reservation_id, "product_id": h["product"], "quantity_milli": h["qty_milli"]})
        elif provider_status == "failed":
            h["state"] = "released"
            self.emit("StockReservationReleased", {"reservation_id": reservation_id, "product_id": h["product"], "reason": "payment_failed"})
        return h["state"]

    def expire(self, now):
        """Releases holds whose time ran out without a provider answer; the checkout must start again."""
        out = []
        for rid, h in self.holds.items():
            if h["state"] == "held" and h["expires_at"] <= now:
                h["state"] = "released"; out.append(rid)
                self.emit("StockReservationReleased", {"reservation_id": rid, "product_id": h["product"], "reason": "timed_out"})
        return out

    def in_person_sale(self, product, qty_milli, on_hand_milli, now):
        """An in-person sale always goes through. If it eats into held stock, the owner gets a conflict flag (never a refusal)."""
        after = on_hand_milli - qty_milli
        free_after = after - self.held(product, now)
        if free_after < 0:
            self.emit("StockConflictFlagged", {"product_id": product, "short_milli": -free_after, "reason": "online_hold"})
        return {"ok": True, "on_hand_milli": after, "conflict": free_after < 0}
