import os, unittest
from core.money import to_minor
from services.billing import FAMILIES, SUITE_MEMBERS
from services.devplatform import RateLimited
from services.platform import Platform

def usd_rwf(usd): return Platform().c.fx.convert(to_minor(usd, "USD"), "USD", "RWF")   # RW price index is applied by the caller

class T(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.b = self.p.billing
        for a in ("a", "b", "c", "dev1"): self.p.register(a, "RW")
    def tearDown(self): os.environ.pop("LYNK_MODE", None)
    def rwf(self, usd): return self.p.c.fx.convert(to_minor(usd * .35, "USD"), "USD", "RWF")   # Rwanda price index 0.35

    def test_families_names_and_tiers(self):
        self.assertEqual(len(FAMILIES), 16); self.assertEqual(len(SUITE_MEMBERS), 7)
        self.assertEqual(FAMILIES["lynkmpay"][:2], ("LynkOmni Merchant Payments", "LynkMPay"))
        self.assertEqual(FAMILIES["lynksuite"][2:4], (("free", "plus", "pro", "max"), (0, 17, 49, 125)))
        self.assertEqual(FAMILIES["lynkdev"][2], ("free", "starter", "business", "enterprise"))
        self.assertNotIn("lynkmpay", SUITE_MEMBERS); self.assertNotIn("lynkassist", SUITE_MEMBERS)     # add-on families are never inside LynkSuite
        with self.assertRaises(ValueError): self.b.set_plan("a", "lynkdev", "plus")                        # developers use their own plan names
        self.b.set_plan("a", "lynkbooking", "max"); self.assertEqual(self.b.entitlement("a", "lynkbooking")["dedicated_concierge"], True)      # consumer families have Max too
        self.assertEqual(self.b.bill("a")["total_minor"], self.rwf(19.99))

    def test_suite_stays_a_real_bundle_discount_and_tiers_never_get_cheaper(self):
        # LynkSuite must cost less than its seven products together (the point of a bundle) but not give them away.
        for i, tier in enumerate(("plus", "pro", "max"), start=1):
            parts = sum(FAMILIES[m][3][i] for m in SUITE_MEMBERS)
            suite = FAMILIES["lynksuite"][3][i]
            self.assertLess(suite, parts, tier); self.assertGreaterEqual(suite, parts * 0.65, tier)
        for k, v in FAMILIES.items():
            self.assertEqual(v[3][0], 0, k)                                           # Free is always free
            self.assertEqual(list(v[3]), sorted(v[3]), k)                             # a higher tier never costs less

    def test_regional_price_and_single_product(self):
        self.b.set_plan("a", "lynkpos", "pro")
        self.assertEqual(self.b.bill("a")["total_minor"], self.rwf(14))
        self.assertEqual(self.b.bill("b")["total_minor"], 0)                                                # Free costs nothing

    def test_suite_replaces_products_without_double_billing(self):
        self.b.set_plan("a", "lynksuite", "pro"); self.b.set_plan("a", "lynkpos", "pro"); self.b.set_plan("a", "lynkchat", "plus")
        bill = self.b.bill("a")
        self.assertEqual([l["family"] for l in bill["lines"]], ["lynksuite"]); self.assertEqual(bill["total_minor"], self.rwf(49))
        self.assertEqual(set(bill["credited"]), {"lynkpos", "lynkchat"})
        self.assertEqual(self.b.effective("a")["lynkchat"], {"tier": "pro", "source": "suite"})              # the higher tier wins, tiers never stack
        self.b.set_plan("a", "lynkpos", "max")                                                              # above the Suite tier: only the difference
        self.assertEqual(self.b.bill("a")["total_minor"], self.rwf(49) + self.rwf(35 - 14))

    def test_addons_are_separate_and_suite_free_costs_nothing(self):
        self.b.set_plan("a", "lynksuite", "plus"); self.b.set_plan("a", "lynkmpay", "plus"); self.b.set_plan("a", "lynkassist", "pro")
        self.assertEqual(self.b.bill("a")["total_minor"], self.rwf(17) + self.rwf(5) + self.rwf(15))
        self.b.set_plan("b", "lynksuite", "free"); self.b.set_plan("b", "lynkpos", "pro")
        self.assertEqual(self.b.bill("b")["total_minor"], self.rwf(14))                                     # Suite Free replaces nothing
        self.assertEqual(self.b.tier("b", "lynkchat"), "free")

    def test_one_invoice_per_period_and_counted_once(self):
        self.b.set_plan("a", "lynksuite", "pro"); self.b.set_plan("a", "lynkpos", "pro"); self.b.set_plan("b", "lynksuite", "free"); self.b.set_plan("c", "lynkpos", "plus")
        self.assertEqual(self.b.invoice("a", "2026-11")["status"], "invoiced"); self.assertEqual(self.b.invoice("a", "2026-11")["status"], "already_invoiced")
        self.b.invoice("c", "2026-11")
        streams = [e["payload"]["stream"] for e in self.p.c.store.of("_company", "revenue.earned")]
        self.assertEqual(sorted(streams), ["subscription:lynkpos", "subscription:lynksuite"])             # one revenue line per paid subscription
        self.assertEqual(self.b.counts(), {"lynksuite": {"pro": 1}, "lynkpos": {"plus": 1}})            # Suite Free and credited POS are not counted
        self.assertEqual(self.p.control.funnel("2026-11-30T00:00:00Z")["paid"], 2)

    def test_entitlements_accumulate(self):
        self.assertEqual((self.b.entitlement("a", "lynkpos")["devices"], self.b.entitlement("a", "lynkpos")["ads"]), (1, True))
        self.b.set_plan("a", "lynksuite", "pro"); e = self.b.entitlement("a", "lynkchat")
        self.assertEqual((e["seats"], e["customer_messaging"], e["shared_inbox"], e["team_inbox"]), (5, True, True, True))
        self.assertEqual(self.b.entitlement("a", "lynkpos")["ads"], False); self.assertEqual(self.b.entitlement("a", "lynkpos")["devices"], 5)

    def test_ads_depend_on_each_products_tier(self):
        os.environ["LYNK_MODE"] = "sandbox"; a = self.p.ads
        cid = a.create_campaign("TelcoX", "telecom", {"en": "Bonus"}, ["RW"], "cpm", 1000, 100000, "RWF"); a.review(cid)
        self.assertIsNotNone(a.select("a", "receipt_footer")); self.assertIsNotNone(a.select("a", "dashboard_card"))
        self.b.set_plan("a", "lynkpos", "plus")
        self.assertIsNone(a.select("a", "receipt_footer")); self.assertIsNotNone(a.select("a", "dashboard_card"))    # only POS surfaces lose ads
        self.b.set_plan("b", "lynksuite", "plus")
        self.assertIsNone(a.select("b", "pos_idle")); self.assertIsNone(a.select("b", "dashboard_card")); self.assertIsNone(a.select("b", "reorder_promoted"))
        self.b.set_plan("c", "lynksuite", "free"); self.assertIsNotNone(a.select("c", "pos_idle"))             # LynkSuite Free still shows ads

    def test_developer_platform_consent_scopes_quota_and_audit(self):
        d = self.p.dev; app = d.create_app("dev1", "Ledger sync", ["sales.read"])
        with self.assertRaises(ValueError): d.create_app("dev1", "Bad", ["admin.all"])
        with self.assertRaises(PermissionError): d.authorize(app["api_key"], "a", "sales.read")               # the merchant has not approved
        d.grant("a", app["app_id"], "sales.read"); self.assertTrue(d.authorize(app["api_key"], "a", "sales.read")["ok"])
        with self.assertRaises(PermissionError): d.authorize(app["api_key"], "a", "stock.read")               # scope not declared
        with self.assertRaises(PermissionError): d.authorize("lk_wrong", "a", "sales.read")
        self.assertEqual(d.usage(app["app_id"]), 1); self.assertTrue(self.p.c.store.of("a", "api.access"))      # metered, and visible to the merchant
        self.assertNotIn(app["api_key"], str(self.p.c.store.of("_company", "dev.app.created")))                # only the hash is stored
        d.revoke("a", app["app_id"], "sales.read")
        with self.assertRaises(PermissionError): d.authorize(app["api_key"], "a", "sales.read")
        d.grant("a", app["app_id"], "sales.read"); self.b.set_plan("dev1", "lynkdev", "free")
        from services import billing; old = billing.FEATURES["lynkdev"][0]["api_calls_per_day"]; billing.FEATURES["lynkdev"][0]["api_calls_per_day"] = 2
        try:
            d.authorize(app["api_key"], "a", "sales.read")
            with self.assertRaises(RateLimited): d.authorize(app["api_key"], "a", "sales.read")
        finally: billing.FEATURES["lynkdev"][0]["api_calls_per_day"] = old

    def test_exchange_needs_terms_and_step_up(self):
        os.environ["LYNK_MODE"] = "sandbox"; s = self.p.services; q = s.exchange_quote("a", "USD", 145000)
        with self.assertRaises(PermissionError): s.buy("a", "currency_exchange", q, "mobile_money", "x1", stepup=self.p.identity.issue("a", verified=True))   # no terms yet
        s.accept_terms("a", "currency_exchange")
        with self.assertRaises(PermissionError): s.buy("a", "currency_exchange", q, "mobile_money", "x1")                                                 # no step-up
        with self.assertRaises(PermissionError): self.p.identity.issue("a", verified=False)
        self.assertTrue(s.buy("a", "currency_exchange", q, "mobile_money", "x1", stepup=self.p.identity.issue("a", verified=True))["ok"])
        self.p.register("k", "KE"); s.accept_terms("k", "insurance_payments")
        self.assertEqual([e["payload"]["country"] for e in self.p.c.store.of("k", "terms.accepted")], ["KE"])                                          # terms are per country

if __name__ == "__main__":
    unittest.main()
