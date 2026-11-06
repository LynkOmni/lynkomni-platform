import os, unittest
os.environ["LYNK_MODE"] = "sandbox"
from services.platform import Platform
from services import billing as B

LINES = [{"qty_milli": 2000, "unit_minor": 1000}, {"qty_milli": 1500, "unit_minor": 333, "discount_minor": 0}]

class T(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"; self.p = Platform(); self.p.register("m1", "RW"); self.iv = self.p.invoicing

    def test_issue_numbers_total_and_label(self):
        r = self.iv.issue("m1", "cust1", LINES)
        self.assertTrue(r["id"].startswith("LOINV-")); self.assertEqual(r["number"], 1)
        self.assertEqual(r["net_minor"], 2000 + 500); self.assertEqual(r["tax_minor"], 450); self.assertEqual(r["total_minor"], r["net_minor"] + r["tax_minor"])   # 1.5 x 333 = 499.5 -> 500; 18% of 2500
        self.assertEqual(self.iv.issue("m1", "cust1", LINES)["number"], 2)
        self.assertEqual(r["label"], "Invoice (not a tax invoice)")              # never 'tax invoice' without written confirmation

    def test_plan_limits(self):
        self.assertEqual([self.iv.ent("m1")["invoices_per_month"]], [3])
        for _ in range(3): self.iv.issue("m1", "c", LINES, month="2026-11")
        with self.assertRaises(PermissionError): self.iv.issue("m1", "c", LINES, month="2026-11")
        self.iv.issue("m1", "c", LINES, month="2026-12")                          # new month starts fresh
        self.p.billing.set_plan("m1", "lynkcheckout", "plus"); self.iv.issue("m1", "c", LINES, month="2026-11")
        self.assertEqual([self._ent(t)["invoices_per_month"] for t in B.MT], [3, 20, 200, None])
        self.assertEqual([self._ent(t)["invoice_series"] for t in B.MT], [1, 1, 3, None])
        self.assertEqual(B.FAMILIES["lynkcheckout"][3], (0, 3, 7, 15))            # prices raised 2026-11-06 (placeholders)
    def _ent(self, tier):
        d = {}
        for x in B.FEATURES["lynkcheckout"][: B.MT.index(tier) + 1]: d.update(x)
        return d

    def test_paid_only_when_the_provider_confirms(self):
        r = self.iv.issue("m1", "c", LINES); iid = r["id"]
        with self.assertRaises(PermissionError): self.iv.record_payment("m1", iid, "mobile_money", r["total_minor"])
        self.assertEqual(self.iv.state(iid), "issued")
        self.assertEqual(self.iv.record_payment("m1", iid, "mobile_money", r["total_minor"], provider_confirmed=True, payment_ref="tx1")["state"], "paid")
        with self.assertRaises(ValueError): self.iv.record_payment("m1", iid, "cash", 1)

    def test_retry_never_counts_twice_and_partial_needs_a_plan(self):
        self.p.billing.set_plan("m1", "lynkcheckout", "pro"); r = self.iv.issue("m1", "c", LINES); iid = r["id"]
        a = self.iv.record_payment("m1", iid, "card", 1000, True, "tx9"); b = self.iv.record_payment("m1", iid, "card", 1000, True, "tx9")
        self.assertEqual(a["state"], "partially_paid"); self.assertTrue(b["duplicate"]); self.assertEqual(self.iv.outstanding(iid), r["total_minor"] - 1000)
        self.p2 = Platform(); self.p2.register("m2", "RW"); r2 = self.p2.invoicing.issue("m2", "c", LINES)
        with self.assertRaises(PermissionError): self.p2.invoicing.record_payment("m2", r2["id"], "cash", 100)    # Free: no partial payments

    def test_issued_invoices_never_change_credit_notes_do(self):
        r = self.iv.issue("m1", "c", LINES); iid = r["id"]
        with self.assertRaises(PermissionError): self.iv.edit(iid, total_minor=1)
        with self.assertRaises(PermissionError): self.iv.credit_note("m1", iid, 100, "error")                     # Free: no credit notes
        self.p.billing.set_plan("m1", "lynkcheckout", "plus")
        with self.assertRaises(ValueError): self.iv.credit_note("m1", iid, 100, "")
        with self.assertRaises(ValueError): self.iv.credit_note("m1", iid, r["total_minor"] + 1, "too much")
        self.iv.credit_note("m1", iid, r["total_minor"], "wrong price"); self.assertEqual(self.iv.state(iid), "credited"); self.assertEqual(self.iv.outstanding(iid), 0)
        v = self.iv.issue("m1", "c", LINES)["id"]; self.iv.void_unpaid("m1", v, "duplicate"); self.assertEqual(self.iv.state(v), "void")

    def test_overdue_and_viewed(self):
        t = [1000.0]; self.iv.now = lambda: t[0]; iid = self.iv.issue("m1", "c", LINES, due_days=1)["id"]
        self.iv.mark_viewed(iid); self.assertEqual(self.iv.state(iid), "viewed"); t[0] += 2 * 86400; self.assertEqual(self.iv.state(iid), "overdue")

    def test_offline_numbers_come_from_a_leased_block_and_gaps_are_voided_with_a_reason(self):
        self.p.billing.set_plan("m1", "lynkcheckout", "pro"); blk = self.iv.lease_block("m1", "devA", "A", size=5)
        self.assertEqual((blk["first"], blk["last"]), (1, 5))
        r = self.iv.accept_offline("m1", "devA", "c", LINES, "A", 2)
        self.assertEqual(r["number"], 2)
        with self.assertRaises(ValueError): self.iv.accept_offline("m1", "devA", "c", LINES, "A", 2)            # a number is used once
        with self.assertRaises(ValueError): self.iv.accept_offline("m1", "devB", "c", LINES, "A", 3)            # another device's block
        self.assertEqual(self.iv.lease_block("m1", "devB", "A", size=3)["first"], 6)                              # blocks never overlap
        void = self.iv.release_block("m1", "devA", "A", 1, reason="device returned unused"); self.assertEqual(sorted(void), ["1", "3", "4", "5"])
        self.assertEqual(self.iv.issue("m1", "c", LINES)["number"], 9)                                            # cloud continues after every leased number

    def test_pay_link_only_after_the_cloud_accepts(self):
        r = self.iv.issue("m1", "c", LINES, accepted=False); iid = r["id"]
        with self.assertRaises(PermissionError): self.iv.pay_link("m1", iid)
        self.iv.inv[iid]["sent_state"] = "accepted"; link = self.iv.pay_link("m1", iid)
        self.assertEqual(self.p.paylinks.verify(link["url"].rsplit("/", 1)[1])["amount_minor"], r["total_minor"])

    def test_series_limits_reminders_and_recurring(self):
        self.iv.lease_block("m1", "d", "A", 1)
        with self.assertRaises(PermissionError): self.iv.lease_block("m1", "d", "B", 1)                           # Free: one series
        iid = self.iv.issue("m1", "c", LINES)["id"]
        with self.assertRaises(PermissionError): self.iv.remind("m1", iid, "sms", [])                             # no consent
        self.assertTrue(self.iv.remind("m1", iid, "sms", ["sms"]))
        with self.assertRaises(PermissionError): self.iv.remind("m1", iid, "sms", ["sms"], automatic=True)         # Free: manual only
        with self.assertRaises(PermissionError): self.iv.schedule("m1", "c", LINES, 7, 100)
        self.p.billing.set_plan("m1", "lynkcheckout", "pro"); self.assertTrue(self.iv.remind("m1", iid, "sms", ["sms"], automatic=True))
        self.iv.lease_block("m1", "d", "B", 1)
        self.iv.schedule("m1", "c", LINES, 7, 100); self.assertEqual(len(self.iv.run_due(100)), 1); self.assertEqual(len(self.iv.run_due(100)), 0); self.assertEqual(len(self.iv.run_due(107)), 1)

    def test_no_extra_fee_is_charged_for_invoicing(self):
        before = len(self.p.c.store.all_of("revenue.earned")); self.iv.issue("m1", "c", LINES); self.assertEqual(len(self.p.c.store.all_of("revenue.earned")), before)

    def test_state_survives_a_restart(self):
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), "i.db"); a = Platform(path); a.register("m1", "RW"); iid = a.invoicing.issue("m1", "c", LINES)["id"]; a.c.store.db.commit()
        b = Platform(path); self.assertEqual(b.invoicing.inv[iid]["number"], 1); self.assertEqual(b.invoicing.issue("m1", "c", LINES)["number"], 2)

if __name__ == "__main__": unittest.main()
