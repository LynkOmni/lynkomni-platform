"""Stock reserved at online checkout (BIZZ & DEVICE, section 3): a checkout holds free stock for 15 minutes; the provider's
confirmation commits it, a failure or the time releases it; an in-person sale is never blocked and a clash is flagged."""
import unittest
from core.reservations import HOLD_S, Reservations


class Holds(unittest.TestCase):
    def setUp(self):
        self.ev = []; self.r = Reservations(lambda t, p: self.ev.append((t, p)))

    def test_last_item_cannot_be_paid_for_twice(self):
        self.assertTrue(self.r.reserve("r1", "p", 1000, "o1", 1000, 0)["ok"])
        self.assertEqual(self.r.reserve("r2", "p", 1000, "o2", 1000, 0), {"ok": False, "reason": "not_enough_stock"})
        self.assertTrue(self.r.reserve("r1", "p", 1000, "o1", 1000, 1)["repeat"])                  # the same checkout again: no second hold

    def test_provider_confirms_or_fails_and_time_runs_out(self):
        self.r.reserve("r1", "p", 2000, "o1", 5000, 0); self.r.reserve("r2", "p", 1000, "o2", 5000, 0); self.r.reserve("r3", "p", 1000, "o3", 5000, 0)
        self.assertEqual(self.r.free("p", 5000, 1), 1000)
        self.assertEqual(self.r.on_payment("r1", "confirmed", 10), "committed")
        self.assertEqual(self.r.on_payment("r2", "failed", 10), "released")
        self.assertIsNone(self.r.on_payment("r2", "confirmed", 11))                                # an answer after release changes nothing
        self.assertEqual(self.r.expire(HOLD_S), ["r3"])
        self.assertEqual([t for t, _ in self.ev], ["StockReserved"] * 3 + ["StockReservationCommitted", "StockReservationReleased", "StockReservationReleased"])

    def test_in_person_sale_is_never_blocked(self):
        self.r.reserve("r1", "p", 1000, "o1", 1000, 0)
        out = self.r.in_person_sale("p", 1000, 1000, 1)
        self.assertTrue(out["ok"]); self.assertTrue(out["conflict"]); self.assertEqual(self.ev[-1][0], "StockConflictFlagged")

    def test_quantities_are_whole_thousandths(self):
        for bad in (0, -1, 1.5, True):
            with self.assertRaises(ValueError): self.r.reserve("x", "p", bad, "o", 9000, 0)


if __name__ == "__main__":
    unittest.main()
