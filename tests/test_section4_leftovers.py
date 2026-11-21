"""Section 4 leftovers (fixed in the leftover step): the trackers planned for section 4 (bills to pay, expense claims, message
delivery) move only on their service's own state, reported in its events (catalog/tracking.v1.json from_service_events); the
invoice tracker now follows LynkInv; ad earnings are recorded once a month and posted to LynkAcc as other income."""
import unittest


class Trackers(unittest.TestCase):
    def setUp(self):
        from services.platform import Platform
        self.p = Platform(); self.p.register("m1", "US")

    def step(self, kind, record, audience="merchant"):
        return self.p.tracking.view(kind, record, audience)["step"]

    def test_a_bill_moves_from_received_to_paid(self):
        b = self.p.books
        bid = b.record_bill("m1", "clerk", 30000)["bill"]
        self.assertEqual(self.step("bill_to_pay", bid), "received")
        b.submit_bill("m1", bid)
        self.assertEqual(self.step("bill_to_pay", bid), "approved")
        b.pay_bill("m1", bid, 10000, provider_confirmed=True, ref="r1")
        self.assertEqual(self.step("bill_to_pay", bid), "partly_paid")
        b.pay_bill("m1", bid, 20000, provider_confirmed=True, ref="r2")
        v = self.p.tracking.view("bill_to_pay", bid, "merchant")
        self.assertEqual((v["step"], v["state"], v["ended"]), ("paid", "confirmed", True))

    def test_an_expense_claim_and_an_invoice_move_on_their_service_state(self):
        b = self.p.books
        cid = b.submit_claim("m1", "staff-1", "receipt", total_minor=4500)["claim"]
        self.assertEqual(self.step("expense_claim", cid), "submitted")
        b.approve_claim("m1", cid, "owner", "owner"); b.repay_claim("m1", cid, provider_confirmed=True)
        self.assertEqual(self.step("expense_claim", cid), "repaid")
        inv = self.p.invoicing.issue("m1", "c1", [{"name": "Work", "qty_milli": 1000, "unit_minor": 5000}], included=True)
        self.assertEqual(self.step("invoice", inv["id"]), "issued")

    def test_a_message_is_delivered_in_the_app_or_waits_and_never_carries_its_words(self):
        n = self.p.notifier
        r = n.notify("invoice_paid", "owner-1", "e1", 1_800_014_400, business="m1", role="owner")
        v = self.p.tracking.view("message_delivery", r["nid"], "merchant")
        self.assertEqual(v["step"], "delivered")
        q = n.notify("invoice_paid", "owner-2", "e2", 1_800_014_400, business="m1", role="owner", online=False)
        self.assertEqual(self.p.tracking.view("message_delivery", q["nid"], "merchant")["step"], "queued")
        for e in self.p.c.store.of("m1", "notification.state"):
            self.assertEqual(set(e["payload"]), {"nid", "kind", "state", "channel"})


class AdEarnings(unittest.TestCase):
    def test_ad_earnings_are_recorded_once_a_month_and_posted_as_income(self):
        from services.platform import Platform
        p = Platform(); p.register("m1", "US")
        for amount in (120, 80):
            p.c.store.append("m1", "server", "ad.share.earned", {"campaign_id": "c1", "amount_minor": amount, "currency": "USD"}, ts="2026-11-05T10:00:00Z")
        p.c.store.append("m1", "server", "ad.share.earned", {"campaign_id": "c1", "amount_minor": 999, "currency": "USD"}, ts="2026-10-30T10:00:00Z")
        self.assertEqual(p.ads.record_earnings("m1", "2026-11"), [{"currency": "USD", "amount": 200}])
        self.assertEqual(p.ads.record_earnings("m1", "2026-11"), [], "each month and currency once")
        ev = p.c.store.of("m1", "AdEarningsRecorded")
        self.assertEqual([(e["payload"]["period"], e["payload"]["amount"]) for e in ev], [("2026-11", 200)])
        lines = [l for e in p.c.store.of("m1", "journal.posted") for l in e["payload"]["lines"]]
        self.assertEqual(sorted(map(tuple, lines)), [("1010", 200, 0), ("4200", 0, 200)])


if __name__ == "__main__":
    unittest.main()
