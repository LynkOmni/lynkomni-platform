"""The cross-service journeys of CONNECT UPDATE 71.2 run end to end on the real platform (section 4 row 71.9: journey tests).
Each journey in catalog/connections.v1.json names the test that proves it once its section is built; a journey of a later section
names its section only. Here: sale to books and quote to cash, the two finished in section 4."""
import json, os, unittest
os.environ["LYNK_MODE"] = "sandbox"
from core import accounts as AC, build_sections as B, connections as C
from services.platform import Platform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINES = [{"qty_milli": 2000, "unit_minor": 1000}]
def item(sku, qty, price): return {"sku": sku, "qty": qty, "price_minor": price}


class Journeys(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"
        self.p = Platform(); self.p.register("m1", "RW")
        for fam in ("lynkinv", "lynkcrm", "lynkacc", "lynkstat"):
            self.p.billing.set_plan("m1", fam, "pro")
        self.cust = self.p.crm.create("m1", "u1", "customer", name="Amina")

    def tb(self):
        e = self.p.accountant.journal("m1")
        self.assertTrue(AC.balanced(e), "the books balance at every step")
        return AC.trial_balance(e)

    def test_sale_to_books(self):
        """pos-stock, pos-crm, pos-acc, mpay-acc and acc-stat: one sale moves stock, lands on the customer, posts and is reported."""
        self.p.inventory.receive("m1", "d1", "rice", 10, 400)
        self.p.pos.record_sale("m1", "d1", [item("rice", 3, 1000)], method="cash", customer=self.cust)
        self.assertEqual(self.p.inventory.levels("m1")["rice"], 7, "pos-stock: the sale moved stock")
        self.assertEqual(self.p.crm.take_sales("m1"), 1)
        self.assertEqual(self.p.crm.take_sales("m1"), 0, "a sale lands on the customer once")
        self.assertEqual(len(self.p.crm.timeline("m1", self.cust, ["sales"])), 1, "pos-crm: the sale is on the customer's record")
        tb = self.tb()
        self.assertEqual((tb["4000"], tb["1000"], tb["5000"]), (3000, 3000, 1200), "pos-acc: sold, cash in, cost of what was sold")
        self.p.pos.record_sale("m1", "d1", [item("rice", 1, 1000)], method="mobile_money")
        self.assertEqual(self.tb()["1010"], 1000, "mpay-acc: an electronic payment waits in the payments clearing account")
        f = self.p.stats.figures("m1")
        self.assertEqual((f["sales"], f["cost_of_sales"]), (4000, 1600), "acc-stat: the reports read the books")

    def test_quote_to_cash(self):
        """crm-inv, inv-checkout, inv-acc and inv-chat: an accepted quote becomes one invoice, paid through a pay link, in the books and the chat."""
        q = self.p.invoicing.quote("m1", self.cust, LINES)
        self.assertTrue(q.startswith("LOQUO-"))
        self.assertNotIn("1100", self.tb(), "a quote never posts")
        inv = self.p.invoicing.accept_quote("m1", q)
        self.assertEqual(self.p.invoicing.accept_quote("m1", q), {"id": inv["id"], "again": True}, "accepted twice, still one invoice")
        self.assertEqual(self.tb()["1100"], inv["total_minor"], "inv-acc: the invoice is owed")
        link = self.p.invoicing.pay_link("m1", inv["id"])
        self.assertTrue(link, "inv-checkout: every invoice is paid through a pay link")
        with self.assertRaises(PermissionError):                                     # an electronic payment counts only when the provider confirms
            self.p.invoicing.record_payment("m1", inv["id"], "mobile_money", inv["total_minor"])
        self.p.invoicing.record_payment("m1", inv["id"], "mobile_money", inv["total_minor"], provider_confirmed=True, payment_ref="t1")
        self.assertEqual(self.p.invoicing.state(inv["id"]), "paid")
        tb = self.tb()
        self.assertEqual((tb.get("1100", 0), tb["1010"]), (0, inv["total_minor"]), "inv-acc: paid clears what was owed")
        conv = self.p.office_chat.open("m1", self.cust)
        card = self.p.office_chat.card("m1", conv, "invoice", inv["id"])
        self.assertNotIn("pay", card["actions"], "inv-chat: a paid invoice's card offers nothing to pay")
        types = [e["type"] for e in self.p.c.store.since("m1")]
        for t in ("document.issued", "quote.accepted", "invoice.issued", "invoice.from_quote"):
            self.assertIn(t, types)


class Register(unittest.TestCase):
    def test_every_built_journey_names_the_test_that_proves_it(self):
        src = open(__file__, encoding="utf-8").read()
        for j in C.JOURNEYS.values():
            if B.status(j["build_section"]) == "locked" or str(j["build_section"]) == "4":
                self.assertIn("proved_by", j, j["id"])
            if "proved_by" in j:
                f, name = j["proved_by"].split("::")
                self.assertIn(f"def {name.split('.')[-1]}(", open(os.path.join(ROOT, f), encoding="utf-8").read(), j["proved_by"])


if __name__ == "__main__":
    unittest.main()
