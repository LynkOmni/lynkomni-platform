import os, unittest
from core.money import FX, fmt, to_minor
from core.providers import Simulator
from core.regions import resolve_country
from services.platform import Platform, ServiceOff

def item(sku, qty, price): return {"sku": sku, "qty": qty, "price_minor": price}

class T(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None)
        self.p = Platform()
        self.p.register("m1", "RW")
    def sandbox(self): os.environ["LYNK_MODE"] = "sandbox"
    def tearDown(self): os.environ.pop("LYNK_MODE", None)

    def test_money(self):
        self.assertEqual(to_minor("1500", "RWF"), 1500); self.assertEqual(to_minor("12.345", "USD"), 1234)
        self.assertEqual(fmt(1500000, "RWF"), "RWF 1,500,000")
        fx = FX(); self.assertEqual(fx.convert(1450, "RWF", "USD"), 100)

    def test_geo(self):
        self.assertEqual(resolve_country(-1.95, 30.06), "RW"); self.assertEqual(resolve_country(-1.29, 36.82), "KE")
        self.assertEqual(resolve_country(0.35, 32.58), "UG"); self.assertEqual(resolve_country(0, 0, "ae"), "AE")
        self.assertIsNone(resolve_country(0, -30))

    def test_sync_idempotent_and_blocks_server_events(self):
        ev = [{"id": "a", "type": "stock.received", "payload": {"sku": "x", "qty": 5, "cost_minor": 100}},
              {"id": "b", "type": "payment.settled", "payload": {"fee_minor": 9999}}]
        r1 = self.p.sync("m1", "d1", ev); r2 = self.p.sync("m1", "d1", ev)
        self.assertEqual((r1["accepted"], r1["rejected"], r2["duplicates"]), (1, 1, 1))
        self.assertEqual(self.p.inventory.levels("m1"), {"x": 5})

    def test_two_devices_sell_last_unit(self):
        self.p.sync("m1", "d1", [{"id": "r", "type": "stock.received", "payload": {"sku": "x", "qty": 1, "cost_minor": 100}}])
        for d in ("d1", "d2"):
            r = self.p.sync("m1", d, [{"id": "s" + d, "type": "sale.recorded", "payload": {"items": [item("x", 1, 150)], "total_minor": 150, "currency": "RWF"}}])
        self.assertEqual(r["negative_stock"], {"x": -1})  # both sales kept, owner alerted

    def test_accountant_and_dashboard(self):
        self.p.inventory.receive("m1", "d", "x", 10, 100)
        self.p.pos.record_sale("m1", "d", [item("x", 4, 150)]); self.p.pos.expense("m1", "d", 50, "rent")
        a = self.p.accountant.summary("m1")
        self.assertEqual((a["revenue_minor"], a["cogs_minor"], a["profit_minor"]), (600, 400, 150))
        v = self.p.dashboard.view("m1", "USD"); self.assertEqual(v["currency"], "USD")

    def test_receipt_is_pending_fiscal_until_the_authority_confirms(self):
        r = self.p.pos.record_sale("m1", "d", [item("x", 1, 100)])["receipt"]
        self.assertEqual((r["status"], r["fiscal"]), ("pending_fiscal", False))

    def test_flags_gate_unintegrated_services(self):
        with self.assertRaises(ServiceOff): self.p.payments.charge("m1", 1000, "mobile_money", "k1")

    def test_failure_recovery_reroutes(self):
        self.sandbox()
        prov = {"RW": [Simulator("momo_mtn", ("mobile_money",), fail_first=5), Simulator("airtel_money", ("mobile_money",))]}
        p = Platform(providers=prov); p.register("m2", "RW")
        r = p.payments.charge("m2", 10000, "mobile_money", "k1")
        self.assertEqual((r["ok"], r["provider"]), (True, "airtel_money"))
        self.assertEqual(p.payments.charge("m2", 10000, "mobile_money", "k1")["ref"], r["ref"])  # idempotent
        self.assertFalse(p.payments.charge("m2", 10000, "upi", "k2")["ok"])

    def test_paylink_tamper(self):
        self.sandbox(); link = self.p.paylinks.create("m1", 5000, "inv1")
        tok = link["qr_payload"].split("t=")[1]
        self.assertEqual(self.p.paylinks.verify(tok)["amount_minor"], 5000)
        self.assertIsNone(self.p.paylinks.verify(tok[:-2] + "zz"))

    def test_financing_needs_consent_and_loyalty(self):
        self.sandbox(); self.p.pos.record_sale("m1", "d", [item("x", 1, 100)])
        with self.assertRaises(PermissionError): self.p.growth.share_with_lender("m1", "bankA")
        self.p.growth.grant_consent("m1", "bankA")
        self.assertIn("revenue_minor", self.p.growth.share_with_lender("m1", "bankA"))
        self.p.loyalty.earn("m1", "c1", 5000); self.assertTrue(self.p.loyalty.redeem("m1", "c1", 4000))
        self.assertFalse(self.p.loyalty.redeem("m1", "c1", 4000))

    def test_marketplace_reorder(self):
        self.p.inventory.receive("m1", "d", "x", 2, 100); self.p.marketplace.register_supplier("A", {"x": 90}); self.p.marketplace.register_supplier("B", {"x": 80})
        self.assertEqual(self.p.marketplace.reorder("m1")[0]["best"], (80, "B"))

if __name__ == "__main__":
    unittest.main()
