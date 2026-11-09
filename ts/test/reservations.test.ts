import { test } from "node:test";
import assert from "node:assert/strict";
import { HOLD_S, Reservations } from "../src/reservations.js";

test("the last item cannot be paid for twice, and the same checkout never holds twice", () => {
  const r = new Reservations();
  assert.equal(r.reserve("r1", "p", 1000, "o1", 1000, 0).ok, true);
  assert.deepEqual(r.reserve("r2", "p", 1000, "o2", 1000, 0), { ok: false, reason: "not_enough_stock" });
  assert.equal(r.reserve("r1", "p", 1000, "o1", 1000, 1).repeat, true);
});
test("the provider commits or releases, time releases, and an in-person sale is never blocked (same as core/reservations.py)", () => {
  const ev: string[] = []; const r = new Reservations((t) => ev.push(t));
  r.reserve("r1", "p", 2000, "o1", 5000, 0); r.reserve("r2", "p", 1000, "o2", 5000, 0); r.reserve("r3", "p", 1000, "o3", 5000, 0);
  assert.equal(r.free("p", 5000, 1), 1000);
  assert.equal(r.onPayment("r1", "confirmed", 10), "committed"); assert.equal(r.onPayment("r2", "failed", 10), "released"); assert.equal(r.onPayment("r2", "confirmed", 11), null);
  assert.deepEqual(r.expire(HOLD_S), ["r3"]);
  assert.deepEqual(ev, ["StockReserved", "StockReserved", "StockReserved", "StockReservationCommitted", "StockReservationReleased", "StockReservationReleased"]);
  const q = new Reservations(); q.reserve("x", "p", 1000, "o", 1000, 0);
  assert.deepEqual(q.inPersonSale("p", 1000, 1000, 1), { ok: true, on_hand_milli: 0, conflict: true });
  for (const bad of [0, -1, 1.5]) assert.throws(() => q.reserve("y" + bad, "p", bad, "o", 9000, 0));
});
