import os, unittest
from core.providers import Simulator
from services.catalog import CATEGORIES, SUBS, SandboxProvider
from services.platform import Platform, ServiceOff

class T(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.p.register("m1", "RW"); self.p.register("agent", "RW")
    def tearDown(self): os.environ.pop("LYNK_MODE", None)
    def tok(self): return self.p.identity.issue("m1", verified=True)

    def test_catalog_has_all_25_sub_services(self):
        by = {c: [k for k, v in SUBS.items() if v[0] == c] for c in CATEGORIES}
        self.assertEqual((len(by["booking"]), len(by["utility"])), (11, 14))

    def test_off_until_activated_then_buy_with_agent_commission(self):
        with self.assertRaises(ServiceOff): self.p.services.search("m1", "airtime")
        self.assertEqual(self.p.services.available("RW"), [])
        os.environ["LYNK_MODE"] = "sandbox"
        self.assertEqual(len(self.p.services.available("RW")), 25)
        q = self.p.services.search("m1", "airtime", phone="0788000000")[0]
        r = self.p.services.buy("m1", "airtime", q, "mobile_money", "ord1", agent="agent")
        self.assertTrue(r["ok"]); self.assertEqual(len(self.p.services.my_items("m1")), 1)           # cached for offline display
        agent_cut = self.p.c.store.of("agent", "commission.earned")[0]["payload"]["amount_minor"]
        self.assertEqual(agent_cut, r["commission_minor"] * 3000 // 10000)
        self.assertEqual(self.p.control.revenue("stream", "month")[0]["group"], "service_commission")

    def test_failures_and_refunds(self):
        os.environ["LYNK_MODE"] = "sandbox"
        q = self.p.services.search("m1", "esim")[0]
        self.p.services.provider = SandboxProvider(fail_fulfil=True)
        r = self.p.services.buy("m1", "esim", q, "mobile_money", "ord2")
        self.assertEqual((r["ok"], r["stage"], r["refund_due"]), (False, "fulfilment", True))
        self.assertTrue(self.p.c.store.of("m1", "service.refund_due"))
        bad = Platform(providers={"RW": [Simulator("momo_mtn", ("mobile_money",), fail_first=99)]}); bad.register("b", "RW")
        q = bad.services.search("b", "airtime")[0]
        self.assertEqual(bad.services.buy("b", "airtime", q, "mobile_money", "ord3")["stage"], "payment")

    def test_cancel_window_and_credit_is_referral_only(self):
        os.environ["LYNK_MODE"] = "sandbox"
        q = self.p.services.search("m1", "events")[0]; self.p.services.buy("m1", "events", q, "mobile_money", "ord4")
        self.p.services.cancel("m1", "ord4")
        with self.assertRaises(ValueError): self.p.services.cancel("m1", "ord4")
        q = self.p.services.search("m1", "bus")[0]; self.p.services.provider.cancel_hours = -1
        self.p.services.buy("m1", "bus", q, "mobile_money", "ord5")
        with self.assertRaises(PermissionError): self.p.services.cancel("m1", "ord5")
        with self.assertRaises(ValueError): self.p.services.buy("m1", "credit_services", q, "mobile_money", "ord6")
        with self.assertRaises(PermissionError): self.p.services.apply_credit("m1", "lenderA", 100000, stepup=self.tok())      # no consent yet
        self.p.services.accept_terms("m1", "credit_services"); self.p.rights.grant("m1", "lenderA")
        self.assertEqual(self.p.services.apply_credit("m1", "lenderA", 100000, stepup=self.tok())["decision"], "by the lender")

    def test_currency_and_crypto_exchange(self):
        os.environ["LYNK_MODE"] = "sandbox"; s = self.p.services
        q = s.exchange_quote("m1", "USD", 145000)                                   # 145,000 RWF is about 100 USD
        self.assertEqual((q["receive_minor"], q["spread_bps"]), (9900, 100))
        s.accept_terms("m1", "currency_exchange"); self.assertTrue(s.buy("m1", "currency_exchange", q, "mobile_money", "fx1", stepup=self.tok())["ok"])
        q2 = s.exchange_quote("m1", "USD", 145000); q2["expires"] = 0
        with self.assertRaises(PermissionError): s.buy("m1", "currency_exchange", q2, "mobile_money", "fx2", stepup=self.tok())     # expired quote
        s.accept_terms("m1", "crypto_exchange")
        with self.assertRaises(ValueError): s.buy("m1", "crypto_exchange", q, "mobile_money", "cx1", stepup=self.tok())      # referral only
        with self.assertRaises(ValueError): s.refer_crypto("m1", "exchangeA", stepup=self.tok())                            # no risk acknowledgement
        with self.assertRaises(PermissionError): s.refer_crypto("m1", "exchangeA", True, stepup=self.tok())                 # no consent
        with self.assertRaises(PermissionError): s.refer_crypto("m1", "exchangeA", True)                                    # no step-up token
        with self.assertRaises(PermissionError): s.refer_crypto("m1", "exchangeA", True, stepup=self.p.identity.issue("someone_else", verified=True))  # token for another account
        self.p.rights.grant("m1", "exchangeA")
        self.assertEqual(s.refer_crypto("m1", "exchangeA", True, stepup=self.tok())["custody"], "none")

    def test_country_can_block_a_service(self):
        from core.regions import COUNTRIES
        os.environ["LYNK_MODE"] = "sandbox"
        COUNTRIES["RW"]["blocked_services"] = ["crypto_exchange"]
        try:
            with self.assertRaises(ServiceOff): self.p.services.refer_crypto("m1", "exchangeA", True)
            self.assertNotIn("crypto_exchange", self.p.services.available("RW"))
        finally:
            del COUNTRIES["RW"]["blocked_services"]

if __name__ == "__main__":
    unittest.main()
