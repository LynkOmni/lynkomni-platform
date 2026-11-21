"""The office side of gift cards, store credit, deposits, matching and payment costs (SERVICES UPDATE 67.2 and 67.8; section 4 step
F, row 67.17): the register, the rules agreeing in Python and TypeScript, and LynkAcc's books from the events of contract version 16."""
import os, subprocess, sys, unittest, uuid
from collections import defaultdict
from core import office_money as O

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Rules(unittest.TestCase):
    def test_vectors_and_the_typescript_numbers_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "office_money_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_accounts_are_real_and_every_outcome_posts(self):
        from core import accounts as AC
        R = O.MONEY
        used = [k["account"] for k in R["stored_value"]["kinds"].values()] + list(R["stored_value"]["issue_debit"].values()) + [
            R["stored_value"]["spend_credit"], R["deposits"]["account"], R["costs"]["account"], R["payouts"]["arrived_debit"], R["payouts"]["arrived_credit"]
        ] + [o["credit"] for o in R["deposits"]["outcomes"].values()]
        self.assertFalse([a for a in used if a not in AC.ACCOUNTS])

    def test_never_a_guess_between_two(self):
        t = [{"kind": "booking", "id": x, "amount": 4000, "currency": "RWF", "on": "2026-11-10"} for x in ("b1", "b2")]
        self.assertEqual(O.match([{"ref": "R", "amount": 4000, "currency": "RWF", "on": "2026-11-10"}], t)["unmatched"], ["R"])


class Books(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"
        from services.platform import Platform
        self.p = Platform(); self.p.register("m1", "RW"); self.o = self.p.office_money

    def dev(self, type_, payload):
        self.p.c.store.append("m1", "dev-1", type_, payload)

    def bal(self):
        tb = defaultdict(int)
        for e in self.p.c.store.of("m1", "journal.posted"):
            for a, d, c in e["payload"]["lines"]:
                tb[a] += d - c
        return tb

    def test_gift_cards_and_store_credit_are_a_debt_of_the_shop(self):
        card, credit = str(uuid.uuid4()), str(uuid.uuid4())
        self.dev("GiftCardSold", {"card_id": card, "amount": 10000, "currency": "RWF", "method": "cash", "top_up": False})
        self.dev("GiftCardSold", {"card_id": card, "amount": 2000, "currency": "RWF", "method": "mobile_money", "top_up": True})
        self.dev("StoreCreditIssued", {"credit_id": credit, "customer_id": str(uuid.uuid4()), "amount": 3000, "currency": "RWF", "reason": "return"})
        self.dev("VoucherRedeemed", {"redemption_id": str(uuid.uuid4()), "voucher_id": card, "amount": 7000, "currency": "RWF"})
        self.dev("VoucherRedeemed", {"redemption_id": str(uuid.uuid4()), "voucher_id": credit, "amount": 1000, "currency": "RWF"})
        tb = self.bal()
        self.assertEqual((tb["2200"], tb["2510"], tb["4000"], tb["6400"]), (-5000, -2000, -8000, 3000))
        self.assertEqual(self.o.stored_value("m1")["owed"], {"gift_card": 5000, "store_credit": 2000})

    def test_spending_below_nothing_is_flagged_once_never_blocked(self):
        card = str(uuid.uuid4())
        self.dev("GiftCardSold", {"card_id": card, "amount": 1000, "currency": "RWF", "method": "cash", "top_up": False})
        for _ in range(2):
            self.dev("VoucherRedeemed", {"redemption_id": str(uuid.uuid4()), "voucher_id": card, "amount": 800, "currency": "RWF"})
        flags = self.p.c.store.of("m1", "StoredValueConflictFlagged")
        self.assertEqual(len(flags), 1); self.assertEqual(flags[0]["payload"]["held"], -600)
        self.assertEqual(self.o.stored_value("m1")["conflicts"], [card])

    def test_a_deposit_is_held_until_used_kept_or_returned(self):
        d = str(uuid.uuid4())
        self.dev("DepositTaken", {"deposit_id": d, "for": "rental", "amount": 20000, "currency": "RWF", "method": "cash"})
        self.assertEqual(self.bal()["2500"], -20000)
        self.dev("DepositSettled", {"settlement_id": str(uuid.uuid4()), "deposit_id": d, "outcome": "kept", "amount": 5000, "currency": "RWF"})
        self.dev("DepositSettled", {"settlement_id": str(uuid.uuid4()), "deposit_id": d, "outcome": "returned_cash", "amount": 9000, "currency": "RWF"})
        self.assertTrue(self.o.deposit_refunded("m1", d, 8000, "PRV-9"))
        self.assertFalse(self.o.deposit_refunded("m1", d, 8000, "PRV-9"), "a repeated answer changes nothing")
        tb = self.bal()
        self.assertEqual((tb["2500"], tb["4200"], tb["1000"], tb["6400"], tb["1010"]), (0, -5000, 11000, 2000, -8000))
        self.assertEqual(self.o.deposits("m1")[0]["left"], 0)

    def test_costs_payouts_and_the_matching_centre(self):
        sale = str(uuid.uuid4())
        self.dev("PaymentRecorded", {"payment_id": str(uuid.uuid4()), "sale_id": sale, "method": "mobile_money", "amount": 1500, "status": "pending_confirmation",
                                     "currency": "RWF", "provider_reference": "R1"})
        today = self.o._today()
        lines = [{"provider_reference": "R1", "amount": 1500, "currency": "RWF", "provider_fee": 30, "lynkomni_part": 8, "settled_on": today},
                 {"provider_reference": "R2", "amount": 999, "currency": "RWF", "provider_fee": 20, "lynkomni_part": 5, "settled_on": today}]
        self.assertEqual(self.o.provider_report("m1", lines), 2)
        self.assertEqual(self.o.provider_report("m1", lines), 0, "each line once")
        with self.assertRaises(ValueError):
            self.o.provider_report("m1", [{**lines[0], "provider_reference": "R3", "provider_fee": 1.5}])
        self.assertEqual(self.o.costs("m1")["months"][0]["provider_fee"], 50)
        self.assertEqual(self.bal()["6100"], 63)
        c = self.o.matching_centre("m1")
        self.assertEqual(c["matched"], [["R1", "sale", sale, "reference"]]); self.assertEqual(c["unmatched"], ["R2"])
        with self.assertRaises(ValueError):
            self.o.undo("m1", "R1")
        pid = str(uuid.uuid4())
        self.assertTrue(self.o.payout_scheduled("m1", pid, "2026-11-01", 1400, "RWF"))
        self.assertEqual(self.o.payout_calendar("m1", "2026-11-21")[0]["state"], "late")
        self.assertTrue(self.o.payout_arrived("m1", pid, "PO-1")); self.assertFalse(self.o.payout_arrived("m1", pid, "PO-1"))
        self.assertEqual(self.o.payout_calendar("m1")[0]["state"], "arrived")
        self.assertEqual(self.bal()["1020"], 1400)

    def test_suggestions_wait_for_a_person_on_free_and_are_automatic_from_plus(self):
        today = self.o._today()
        sale = str(uuid.uuid4())
        self.dev("PaymentRecorded", {"payment_id": str(uuid.uuid4()), "sale_id": sale, "method": "card", "amount": 2500, "status": "pending_confirmation", "currency": "RWF"})
        self.o.provider_report("m1", [{"provider_reference": "S1", "amount": 2500, "currency": "RWF", "provider_fee": 50, "lynkomni_part": 0, "settled_on": today}])
        self.assertEqual(self.o.matching_centre("m1")["suggested"], [["S1", "sale", sale]])
        self.p.billing.set_plan("m1", "lynkacc", "plus")
        c = self.o.matching_centre("m1")
        self.assertEqual((c["suggested"], c["matched"][0][3]), ([], "automatic"))
        self.o.undo("m1", "S1")
        self.assertEqual(self.p.c.store.of("m1", "PaymentMatchUndone")[0]["payload"]["provider_reference"], "S1")
        self.assertEqual(self.o.matching_centre("m1")["suggested"], [["S1", "sale", sale]], "an undone match is never made again by itself")
        self.o.confirm("m1", "S1", "sale", sale)
        self.assertEqual(self.o.matching_centre("m1")["matched"][0][3], "confirmed")

    def test_an_invoice_match_is_confirmed_by_a_person_and_paid_on_the_invoice(self):
        self.p.billing.set_plan("m1", "lynkacc", "plus")
        inv = self.p.invoicing.issue("m1", "C1", [{"name": "Work", "qty_milli": 1000, "unit_minor": 5000}])
        due = self.p.invoicing.outstanding(inv["id"])
        self.o.provider_report("m1", [{"provider_reference": "I1", "amount": due, "currency": "RWF", "provider_fee": 0, "lynkomni_part": 0, "settled_on": self.o._today()}])
        self.assertEqual(self.o.matching_centre("m1")["suggested"], [["I1", "invoice", inv["id"]]], "never automatic for an invoice")
        self.o.confirm("m1", "I1", "invoice", inv["id"])
        self.assertEqual(self.p.invoicing.outstanding(inv["id"]), 0)
        with self.assertRaises(ValueError):
            self.o.undo("m1", "I1")

    def test_the_sandbox_provider_report_never_posts_a_fee_twice(self):
        from core.providers import Simulator
        sim = Simulator("card", ("card",), fee_bps=200)
        res = sim.charge(10000, "RWF", "card", "k1")
        self.p.c.store.append("m1", "server", "payment.settled", {"provider": "card", "amount_minor": 10000, "currency": "RWF", "fee_minor": res["fee_minor"], "ref": res["ref"]})
        before = self.bal()["6100"]
        self.assertEqual(self.o.provider_report("m1", sim.settlement_report(self.o._today())), 1)
        self.assertEqual(self.bal()["6100"], before, "the fee of a payment the cloud charged itself is posted once")
        self.assertEqual(self.o.costs("m1")["payments"][0]["cost"], 200)


if __name__ == "__main__":
    unittest.main()
