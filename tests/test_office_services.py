"""LynkAcc and LynkInv in the cloud (OFFICE UPDATE 66; section 4 step D2b): services/accounting.py and services/invoicing.py on the
rules of core/books.py and core/invoices.py, every fact an event and the journal the log's projection. The two journeys of 71.2
due in section 4, sale to books and quote to cash, run end to end and the books balance at every step."""
import os, unittest
os.environ["LYNK_MODE"] = "sandbox"
from core import accounts as AC
from services.platform import Platform

LINES = [{"qty_milli": 2000, "unit_minor": 1000}]


class Office(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"
        self.p = Platform(); self.p.register("m1", "RW")
        self.acc, self.iv = self.p.books, self.p.invoicing

    def tb(self):
        e = self.p.accountant.journal("m1")
        self.assertTrue(AC.balanced(e), "every entry balances")
        return AC.trial_balance(e)

    def test_quote_to_cash_posts_and_clears_the_receivable(self):
        q = self.iv.document("m1", "quote")
        r = self.iv.issue("m1", "c1", LINES)                                          # 2000 net + 18% = 2360
        tb = self.tb()
        self.assertEqual((tb["1100"], tb["4000"], tb["2100"]), (2360, 2000, 360), "an issued invoice is owed, earned and taxed")
        self.iv.record_payment("m1", r["id"], "mobile_money", 2360, provider_confirmed=True, payment_ref="t1")
        tb = self.tb()
        self.assertEqual((tb.get("1100", 0), tb["1010"]), (0, 2360), "the payment clears what the customer owed")
        self.assertTrue(q.startswith("LOQUO-"))

    def test_an_overpayment_is_a_credit_balance_never_income(self):
        self.p.billing.set_plan("m1", "lynkinv", "plus")
        a = self.iv.issue("m1", "c1", LINES)
        r = self.iv.pay_several("m1", "c1", 3000, "cash")
        self.assertEqual(r["credit_balance"], 640)
        self.assertEqual(self.iv.credit_balance("m1", "c1"), 640)
        tb = self.tb()
        self.assertEqual((tb["2510"], tb.get("1100", 0), tb["1000"]), (640, 0, 3000))
        b = self.iv.issue("m1", "c1", LINES)
        self.assertEqual(self.iv.apply_credit("m1", "c1", b["id"]), 640)
        self.assertEqual(self.tb().get("2510", 0), 0)
        self.assertEqual(self.iv.state(a["id"]), "paid")

    def test_write_offs_need_two_people_and_post_to_bad_debts(self):
        self.p.billing.set_plan("m1", "lynkinv", "pro")
        r = self.iv.issue("m1", "c1", LINES)
        with self.assertRaises(PermissionError):
            self.iv.write_off("m1", r["id"], "u1", "u1")
        self.assertEqual(self.iv.write_off("m1", r["id"], "u1", "u2"), 2360)
        tb = self.tb()
        self.assertEqual((tb.get("1100", 0), tb["6800"]), (0, 2360))

    def test_approval_before_sending_holds_an_invoice_until_someone_else_approves(self):
        self.p.billing.set_plan("m1", "lynkinv", "pro")
        self.iv.settings.put("m1|approval", {"over_minor": 1000})
        h = self.iv.issue("m1", "c1", LINES, preparer="u1")
        self.assertEqual(h["state"], "awaiting_approval")
        self.assertNotIn("1100", self.tb(), "nothing is owed until it is issued")
        with self.assertRaises(PermissionError):
            self.iv.approve("m1", h["held"], "u1")
        self.assertTrue(self.iv.approve("m1", h["held"], "u2")["id"].startswith("LOINV-"))

    def test_bills_are_approved_by_others_and_paid_only_when_confirmed(self):
        self.p.billing.set_plan("m1", "lynkacc", "plus")
        b = self.acc.record_bill("m1", "u1", 60000, account="6000")["bill"]
        self.assertEqual(self.acc.submit_bill("m1", b), "awaiting_approval")
        with self.assertRaises(PermissionError):
            self.acc.approve_bill("m1", b, "u1", "manager")
        self.acc.approve_bill("m1", b, "u2", "manager")
        with self.assertRaises(PermissionError):
            self.acc.approve_bill("m1", b, "u2", "owner")                             # each step a different person
        self.assertEqual(self.acc.approve_bill("m1", b, "u3", "owner"), "approved")
        with self.assertRaises(PermissionError):
            self.acc.pay_bill("m1", b, 60000, "bank")
        self.assertEqual(self.acc.pay_bill("m1", b, 60000, "bank", provider_confirmed=True)["state"], "paid")
        tb = self.tb()
        self.assertEqual((tb.get("2000", 0), tb["6000"], tb["1020"]), (0, 60000, -60000))

    def test_a_bill_with_an_order_is_matched_first(self):
        b = self.acc.record_bill("m1", "u1", 1000, order="po1")["bill"]
        self.acc.submit_bill("m1", b)                                                # Free: one person, no approval steps
        with self.assertRaises(PermissionError):
            self.acc.pay_bill("m1", b, 1000, "cash")
        self.acc.match_bill("m1", b, [{"sku": "A", "qty": 1000, "price_minor": 1000}], [{"sku": "A", "qty": 1000}], [{"sku": "A", "qty": 1000, "price_minor": 1000}])
        self.assertEqual(self.acc.pay_bill("m1", b, 1000, "cash")["state"], "paid")

    def test_expense_claims_assets_and_journals(self):
        self.p.billing.set_plan("m1", "lynkacc", "pro")
        c = self.acc.submit_claim("m1", "u1", "mileage", km_thousandths=12500, rate_minor=300)
        self.assertEqual(c["total"], 3750)
        with self.assertRaises(PermissionError):
            self.acc.approve_claim("m1", c["claim"], "u1", "manager")
        self.acc.approve_claim("m1", c["claim"], "u2", "manager")
        self.acc.repay_claim("m1", c["claim"], provider_confirmed=True)
        a = self.acc.add_asset("m1", 600000, 5)
        self.assertTrue(a["asset"].startswith("LOAST-"))
        self.assertEqual(self.acc.post_depreciation("m1", a["asset"], "2026")["amount"], 120000)
        self.assertTrue(self.acc.post_depreciation("m1", a["asset"], "2026").get("duplicate"))
        j = self.acc.prepare_journal("m1", "manual", [["6000", 500, 0], ["1000", 0, 500]], "u1")
        self.assertEqual(j["state"], "awaiting_approval")
        with self.assertRaises(PermissionError):
            self.acc.approve_journal("m1", j["pending"], "u1")
        self.acc.approve_journal("m1", j["pending"], "u2")
        with self.assertRaises(ValueError):
            self.acc.prepare_journal("m1", "manual", [["6000", 500, 0], ["1000", 0, 499]], "u1")
        tb = self.tb()
        self.assertEqual((tb["2800"], tb["1500"], tb["1510"], tb["6500"]), (0, 600000, 120000, 120000))
        self.assertTrue(self.acc.statements("m1")["statements"]["balanced"])

    def test_nothing_posts_on_a_locked_date(self):
        self.p.billing.set_plan("m1", "lynkacc", "pro")
        with self.assertRaises(PermissionError):
            self.acc.set_lock_date("m1", "2099-12-31", "u1", "u1")
        self.acc.set_lock_date("m1", "2099-12-31", "u1", "u2")
        with self.assertRaises(PermissionError):
            self.iv.issue("m1", "c1", LINES)

    def test_the_year_end_close_needs_its_checklist_and_two_people(self):
        self.p.billing.set_plan("m1", "lynkacc", "pro")
        self.iv.issue("m1", "c1", LINES)
        r = self.acc.close_year("m1", [], "u1", "u2", "2026-12-31")
        self.assertFalse(r["closed"]); self.assertIn("bank_matched", r["missing"])
        from core import books as B
        r = self.acc.close_year("m1", B.BOOKS["closing"]["checklist"], "u1", "u2", "2099-12-31")
        self.assertTrue(r["closed"])
        tb = self.tb()
        self.assertEqual((tb.get("4000", 0), tb["3100"]), (0, 2000), "the year's profit moves to profit kept")

    def test_subscriptions_and_instalments_add_up(self):
        self.p.billing.set_plan("m1", "lynkinv", "pro")
        sid = self.iv.subscribe("m1", "c1", 1900)
        self.assertTrue(sid.startswith("LOSUB-"))
        self.assertEqual(self.iv.change_subscription("m1", sid, "upgrade", 4900, 15)["amount"], 1500)
        self.assertEqual(self.iv.change_subscription("m1", sid, "pause")["state"], "paused")
        r = self.iv.issue("m1", "c1", LINES)
        parts = self.iv.instalment_plan("m1", r["id"], 3, "2026-01-31")
        self.assertEqual(sum(x["amount"] for x in parts), 2360)


if __name__ == "__main__":
    unittest.main()
