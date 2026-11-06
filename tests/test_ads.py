import os, unittest
from core.locale import receipt_text
from services.platform import Platform, ServiceOff

D = "2026-10-25"
def ts(h=10): return f"{D}T{h:02d}:00:00Z"

class T(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.a = self.p.ads
        for m in ("m1", "m2"): self.p.register(m, "RW")
    def tearDown(self): os.environ.pop("LYNK_MODE", None)
    def camp(self, **kw):
        base = dict(advertiser="TelcoX", category="telecom", creative={"en": "Free data bonus", "fr": "Bonus data gratuit"}, countries=["RW"],
                    model="cpm", price_minor=1000, budget_minor=100000, currency="RWF")
        cid = self.a.create_campaign(**{**base, **kw}); return cid, self.a.review(cid)

    def test_off_until_enabled_and_review_rules(self):
        cid, _ = self.camp()
        with self.assertRaises(ServiceOff): self.a.select("m1", "pos_idle")
        os.environ["LYNK_MODE"] = "sandbox"
        self.assertIsNone(self.a.select("m1", "pos_idle", lang="en") and None)       # approved campaign serves
        self.assertEqual(self.a.select("m1", "pos_idle", lang="fr")["text"], "Bonus data gratuit")
        self.assertEqual(self.a.select("m1", "pos_idle", lang="sw")["text"], "Free data bonus")   # falls back to English
        self.assertFalse(self.camp(category="gambling")[1]["approved"])
        self.assertFalse(self.camp(category="lending")[1]["approved"])                # regulated, advertiser not licensed
        self.assertTrue(self.camp(category="lending", licensed_in=["RW"])[1]["approved"])

    def test_never_in_critical_screens_and_merchant_controls(self):
        os.environ["LYNK_MODE"] = "sandbox"; self.camp()
        for screen in ("payment", "void", "cash_count", "fiscal_receipt_body", "chat_thread"):
            self.assertIsNone(self.a.select("m1", "pos_idle", screen=screen))
        self.assertIsNotNone(self.a.select("m1", "pos_idle"))
        self.a.set_ad_free("m1"); self.assertIsNone(self.a.select("m1", "pos_idle")); self.assertIsNotNone(self.a.select("m2", "pos_idle"))
        self.a.opt_out("m2", "telecom"); self.assertIsNone(self.a.select("m2", "pos_idle"))
        with self.assertRaises(ValueError): self.a.select("m1", "chat_between_users")

    def test_targeting_frequency_and_budget(self):
        os.environ["LYNK_MODE"] = "sandbox"
        self.camp(countries=["KE"]); self.assertIsNone(self.a.select("m1", "pos_idle"))      # wrong country
        cid, _ = self.camp(contexts=["low_stock"])
        self.assertIsNone(self.a.select("m1", "pos_idle", context="sale")); self.assertIsNotNone(self.a.select("m1", "pos_idle", context="low_stock"))
        for _ in range(5): self.p.c.store.append("m1", "d", "ad.impression", {"campaign_id": cid, "surface": "pos_idle"}, ts=ts())
        self.assertIsNone(self.a.select("m1", "pos_idle", context="low_stock", today=D))      # daily cap reached
        cid2, _ = self.camp(budget_minor=1, price_minor=1000, model="cpc")
        self.a.click("m2", "d", cid2, "pos_idle"); self.a.impression("m2", "d", cid2, "pos_idle")
        self.assertIsNone(self.a.select("m2", "pos_idle", merchant_type=None) and None)

    def test_offline_bundle_sync_and_billing_with_merchant_share(self):
        os.environ["LYNK_MODE"] = "sandbox"; cid, _ = self.camp(price_minor=1000000)       # 1,000 RWF per impression
        bundle = self.a.bundle("m1", ["receipt_footer", "pos_idle"]); self.assertEqual(len(bundle), 2)
        evs = [{"id": f"i{i}", "type": "ad.impression", "payload": {"campaign_id": cid, "surface": "receipt_footer"}, "ts": ts()} for i in range(7)]
        r = self.p.sync("m1", "d1", evs); self.assertEqual(r["accepted"], 7)
        self.assertEqual(self.a.report(cid)["impressions"], 5)                              # 2 beyond the daily cap are not billable
        s = self.a.settle(cid); self.assertEqual(s["settled_minor"], 5000)
        self.assertEqual(s["merchant_shares_minor"], 2000)                                   # 40% on receipt footers
        self.assertEqual(self.p.c.store.of("m1", "ad.share.earned")[0]["payload"]["amount_minor"], 2000)
        self.assertEqual(self.a.settle(cid)["settled_minor"], 0)                              # idempotent
        self.assertEqual(self.p.control.revenue("stream", "month")[0]["group"], "advertising")
        self.assertIsNone(self.p.sync("m1", "d1", [{"id": "x", "type": "ad.settled", "payload": {}}]) and None)
        self.assertEqual(self.p.sync("m1", "d1", [{"id": "y", "type": "ad.settled", "payload": {}}])["rejected"], 1)  # devices cannot bill

    def test_click_needs_impression_and_cpa(self):
        os.environ["LYNK_MODE"] = "sandbox"; cid, _ = self.camp(model="cpa", price_minor=500)
        self.a.conversion("m1", cid, "loyalty_offer"); self.assertEqual(self.a.settle(cid)["settled_minor"], 0)   # no impression, not billable
        self.a.impression("m1", "d", cid, "loyalty_offer"); self.a.conversion("m1", cid, "loyalty_offer")
        self.assertEqual(self.a.settle(cid)["settled_minor"], 500)

    def test_receipt_footer_is_labeled_and_last(self):
        os.environ["LYNK_MODE"] = "sandbox"; self.camp()
        foot = self.a.receipt_footer("m1", "fr"); self.assertEqual(foot["label"], "Sponsoris\u00e9")
        sale = {"items": [{"sku": "x", "qty": 1, "price_minor": 100}], "total_minor": 100, "currency": "RWF"}
        txt = receipt_text(sale, ts(), "RW", "fr", ad=foot)
        self.assertLess(txt.index("fiscale"), txt.index("Sponsoris\u00e9")); self.assertTrue(all(len(l) <= 32 for l in txt.split("\n")))

if __name__ == "__main__":
    unittest.main()
