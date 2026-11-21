"""LynkExchange in the office services (EXCHANGE UPDATE, master blueprint 65.9; section 4 step E4b): core/exchange.py and
ts/src/exchange.ts with shared vectors, the practice partner and services/exchange_office.py on contract version 15.

One full price with LynkOmni's part at the lower of the plan and the level; "Coming to your country soon." where no partner is signed;
Practice mode everywhere, never moving money or touching the books; a second person approves large orders; foreign money held at
cost and a rate gain or loss booked only when it comes back; invoices paid from abroad and bills paid abroad recorded once on the
partner's confirmation; payees in LynkCRM with bank details only in the vault; the Exchange report; a proof anyone can check."""
import json, os, subprocess, sys, unittest
from unittest import mock

from core import exchange as X
from services import billing as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ON = {"state": "available", "message": None, "visual": None, "notify_me": False}


class SignedPartner:
    """Stands in for a signed licensed partner in these tests only: the practice prices, but not marked practice."""
    def __init__(self):
        from services.exchange_partners import SandboxExchangePartner
        self.s = SandboxExchangePartner()
    def quote(self, frm, to, amount):
        return {**self.s.quote(frm, to, amount), "practice": False}
    def place(self, *a):
        return {**self.s.place(*a), "practice": False}


class Rules(unittest.TestCase):
    def test_vectors_and_the_typescript_rule_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "exchange_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_the_lower_of_plan_and_level_and_one_full_price(self):
        self.assertEqual(X.part_bps(50, B.EXCHANGE_LEVELS, 0), 50)
        self.assertEqual(X.part_bps(50, B.EXCHANGE_LEVELS, 10_000_000), 20, "a big month's level beats the Free plan's part")
        self.assertEqual(X.part_bps(20, B.EXCHANGE_LEVELS, 0), 20, "the Max plan's part beats a small month")
        self.assertEqual(X.quote(100000, 92, 100, 50), {"part": 500, "to_amount": 91540})
        with self.assertRaises(ValueError):
            X.quote(100000, 0.92, 1, 50)                                                  # a rate is never a decimal


class Office(unittest.TestCase):
    def setUp(self):
        from services.platform import Platform
        self.p = Platform(); self.p.register("m1", "US"); self.x = self.p.exchange_office
        self.practice_partner, self.x.partner = self.x.partner, SignedPartner()

    def balances(self):
        tb = {}
        for e in self.p.c.store.of("m1", "journal.posted"):
            for acct, dr, cr in e["payload"]["lines"]:
                tb[acct] = tb.get(acct, 0) + dr - cr
        return {k: v for k, v in tb.items() if v}

    def order(self, frm, to, amount, kind="convert", **kw):
        with mock.patch("providers.availability", return_value=ON):
            q = self.x.quote("m1", frm, to, amount, kind=kind, **kw)
        return q, self.x.place("m1", q["quote_id"], "owner")

    def test_coming_soon_where_no_partner_and_practice_everywhere(self):
        off = {"state": "coming_soon", "message": "Coming to your country soon.", "visual": "state-coming-soon", "notify_me": True}
        with mock.patch("providers.availability", return_value=off):
            self.assertEqual(self.x.quote("m1", "USD", "EUR", 100000)["message"], "Coming to your country soon.")
        self.x.partner = self.practice_partner
        q = self.x.quote("m1", "USD", "EUR", 100000, practice=True)
        self.assertTrue(q["practice"]); self.assertEqual(q["above_mid_bps"], 100, "the practice partner's 0.5% and LynkOmni's 0.5% on Free")
        o = self.x.place("m1", q["quote_id"], "owner")
        self.x.partner_paid(o["order_id"], "p0"); self.x.partner_settled(o["order_id"], q["to_amount"], "p0")
        self.assertEqual(self.balances(), {}, "practice never touches the books")
        self.assertEqual([e["payload"]["practice"] for e in self.p.c.store.of("m1", "ExchangeOrderPlaced")], [True])
        self.assertEqual(self.p.c.store.of("m1", "ExchangeSettled"), [], "practice never writes a money fact")

    def test_foreign_money_is_held_at_cost_and_gains_are_booked_on_the_way_back(self):
        q1, o1 = self.order("USD", "EUR", 100000)
        self.x.partner_paid(o1["order_id"], "p1"); self.x.partner_settled(o1["order_id"], q1["to_amount"], "p1")
        self.assertEqual(self.balances(), {}, "bank to bank at cost: nothing earned or lost yet")
        q2, o2 = self.order("EUR", "USD", q1["to_amount"])
        self.x.partner_paid(o2["order_id"], "p2"); self.x.partner_settled(o2["order_id"], 99000, "p2")
        self.assertEqual(self.balances(), {"1020": -1000, "6700": 1000}, "the round trip's cost is a rate loss")
        rep = self.x.report("m1")
        self.assertEqual((rep["losses"], rep["pairs"]["USD-EUR"]["part"]), (1000, 500))

    def test_a_second_person_approves_large_orders(self):
        self.p.billing.set_plan("m1", "lynkexchange", "plus")
        self.x.set_approval("m1", 50000)
        with mock.patch("providers.availability", return_value=ON):
            q = self.x.quote("m1", "USD", "EUR", 100000)
        with self.assertRaises(PermissionError):
            self.x.place("m1", q["quote_id"], "owner", approver="owner")
        self.assertEqual(self.x.place("m1", q["quote_id"], "owner", approver="manager")["state"], "placed")

    def test_an_expired_price_is_never_used(self):
        with mock.patch("providers.availability", return_value=ON):
            q = self.x.quote("m1", "USD", "EUR", 100000)
        self.x.now = lambda: 10 ** 12
        with self.assertRaises(ValueError):
            self.x.place("m1", q["quote_id"], "owner")

    def test_an_invoice_paid_from_abroad_and_a_bill_paid_abroad(self):
        inv = self.p.invoicing.issue("m1", "cust-abroad", [{"name": "Design work", "qty_milli": 1000, "unit_minor": 50000}], included=True)
        with mock.patch("providers.availability", return_value=ON):
            q = self.x.invoice_from_abroad("m1", inv["id"], "EUR")
        o = self.x.place("m1", q["quote_id"], "owner")
        self.x.partner_paid(o["order_id"], "p3"); self.x.partner_settled(o["order_id"], 50000, "p3")
        self.assertEqual(self.p.invoicing.state(inv["id"]), "paid")
        self.x.partner_settled(o["order_id"], 50000, "p3")                              # a repeated answer never pays twice
        self.assertEqual(self.p.invoicing.inv[inv["id"]]["paid_minor"], 50000)
        bid = self.p.books.record_bill("m1", "clerk", 30000)["bill"]
        self.p.books.submit_bill("m1", bid)
        if self.p.books.bills[bid]["state"] == "awaiting_approval":
            self.p.books.approve_bill("m1", bid, "owner", "owner")
        with mock.patch("providers.availability", return_value=ON):
            q = self.x.bill_abroad("m1", bid, "EUR")
        o = self.x.place("m1", q["quote_id"], "owner")
        self.x.partner_paid(o["order_id"], "p4"); self.x.partner_settled(o["order_id"], q["to_amount"], "p4")
        self.assertEqual(self.p.books.bills[bid]["paid"], 30000)

    def test_payees_live_in_lynkcrm_with_bank_details_only_in_the_vault(self):
        rid = self.x.add_payee("m1", "owner", "Supplier GmbH", "DE89 3704 0044 0532 0130 00")
        self.assertEqual(self.p.crm.recs[rid]["kind"], "payee")
        stored = json.dumps([v for _, v in self.x.payees.items()]) + json.dumps(dict(self.p.crm.recs[rid]))
        self.assertNotIn("DE89", stored)
        events = json.dumps([e["payload"] for e in self.p.c.store.since("m1")])
        self.assertNotIn("DE89", events); self.assertNotIn("Supplier GmbH", events)

    def test_a_proof_of_exchange_anyone_can_check(self):
        q, o = self.order("USD", "EUR", 100000)
        with self.assertRaises(ValueError):
            self.x.proof("m1", o["order_id"])
        self.x.partner_paid(o["order_id"], "p5"); self.x.partner_settled(o["order_id"], q["to_amount"], "p5")
        pr = self.x.proof("m1", o["order_id"])
        v = self.p.files.verify(pr["code"])
        self.assertEqual((v["ok"], v["issuer"], v["signers"]), (True, "lynkexchange", 0))
        ev = self.p.c.store.of("m1", "ExchangeProofIssued")[0]["payload"]
        self.assertNotIn(pr["code"], json.dumps(ev))

    def test_a_refund_puts_the_cost_back(self):
        q, o = self.order("USD", "EUR", 100000)
        self.x.partner_paid(o["order_id"], "p6")
        self.assertEqual(self.balances(), {"1010": 100000, "1020": -100000})
        self.x.partner_refunded(o["order_id"], 100000, "p6")
        self.assertEqual(self.balances(), {})


if __name__ == "__main__":
    unittest.main()
