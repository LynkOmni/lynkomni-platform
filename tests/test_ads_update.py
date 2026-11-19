"""ADS UPDATE (owner 2026-11-19, master blueprint section 77): one ads register (catalog/ads.v1.json) is an allow-list of places;
the never list covers every protected screen; families that show ads on Free have places; seen-only impressions, caps,
merchant and person controls, children and household spaces, and totals-only reports all follow the register."""
import json, os, unittest
from core.build_sections import ORDER
from services import billing
from services.ads import REGISTER, PLACES, HOSTED_BY_CHOICE
from services.platform import Platform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = "2026-10-25"
def ts(h=10, m=0): return f"{D}T{h:02d}:{m:02d}:00Z"


class Register(unittest.TestCase):
    def test_places_name_real_families_sections_and_owners(self):
        for p in REGISTER["places"]:
            self.assertTrue(p["family"] in billing.FAMILIES or p["family"] in ("platform", "storefront"), p["id"])
            self.assertIn(p["build_section"], [str(n) for n in ORDER], p["id"])
            self.assertIn(p["owner"], ("merchant", "lynkomni"), p["id"])
            self.assertIn(p["audience"], ("customer", "staff", "public"), p["id"])
            self.assertEqual(p["share_bps"] > 0, p["owner"] == "merchant", f"{p['id']}: a share only where the merchant owns the place")
            self.assertTrue(0 <= p["share_bps"] < 10000, p["id"])
        for r in REGISTER["revenue"]:
            self.assertIn(r["build_section"], [str(n) for n in ORDER], r["id"])

    def test_every_family_with_ads_on_free_has_a_place(self):
        with_ads = {f for f, tiers in billing.FEATURES.items() if any(isinstance(x, dict) and x.get("ads") for x in tiers)}
        placed = {p["family"] for p in REGISTER["places"]}
        self.assertEqual(with_ads - placed, set())

    def test_never_list_covers_every_protected_screen(self):
        never = set(REGISTER["never"])
        for must in ("payment", "checkout", "cash_count", "void", "refund", "fiscal_receipt_body", "chat_thread", "exchange", "vcard",
                     "agent_point", "sign_in", "security", "account_recovery", "consent", "signature", "assist_answer", "notification",
                     "message", "email", "booking_checkout", "household", "school", "child", "legal"):
            self.assertIn(must, never)
        self.assertEqual(set(REGISTER["never_audiences"]), {"child", "household"})
        self.assertFalse(set(PLACES) & never, "a place can never also be a protected screen")

    def test_categories_and_numbers(self):
        c = REGISTER["categories"]
        for must in ("gambling", "adult", "tobacco", "weapons", "political"):
            self.assertIn(must, c["blocked"])
        self.assertFalse(set(c["blocked"]) & set(c["age_sensitive"]) or set(c["blocked"]) & set(c["regulated"]))
        self.assertEqual(REGISTER["report_minimum"], 5)                     # the same floor as survey results
        self.assertEqual(REGISTER["caps"]["per_screen"], 1)
        self.assertGreaterEqual(REGISTER["viewability"]["min_visible_pct"], 50)
        self.assertGreaterEqual(REGISTER["viewability"]["min_visible_ms"], 1000)
        self.assertTrue(REGISTER["seamless"] and REGISTER["person_controls"] and REGISTER["merchant_controls"])


class Rules(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"; self.p = Platform(); self.a = self.p.ads
        for m in ("m1", "m2", "m3"): self.p.register(m, "RW")
    def tearDown(self): os.environ.pop("LYNK_MODE", None)
    def camp(self, **kw):
        base = dict(advertiser="TelcoX", category="telecom", creative={"en": "Free data bonus"}, countries=["RW"],
                    model="cpm", price_minor=1000, budget_minor=10 ** 9, currency="RWF")
        cid = self.a.create_campaign(**{**base, **kw}); self.a.review(cid); return cid

    def test_children_households_and_protected_screens_get_nothing(self):
        self.camp()
        self.assertIsNotNone(self.a.select("m1", "pos_idle"))
        self.assertIsNone(self.a.select("m1", "pos_idle", audience="child"))
        self.assertIsNone(self.a.select("m1", "pos_idle", workspace="household"))
        for screen in REGISTER["never"]:
            self.assertIsNone(self.a.select("m1", "pos_idle", screen=screen), screen)

    def test_age_sensitive_needs_the_country_and_blocked_never_passes(self):
        self.assertFalse(self.a.review(self.a.create_campaign("B", "alcohol", {"en": "x"}, ["RW"], "cpm", 1, 1, "RWF"))["approved"])
        self.assertFalse(self.a.review(self.a.create_campaign("B", "get_rich_quick", {"en": "x"}, ["RW"], "cpm", 1, 1, "RWF"))["approved"])

    def test_customer_facing_places_wait_for_the_merchant_and_staff_places_do_not(self):
        self.camp()
        for place in HOSTED_BY_CHOICE:
            self.assertIsNone(self.a.select("m1", place), place)
        self.a.set_hosting("m1", "receipt_footer"); self.assertIsNotNone(self.a.select("m1", "receipt_footer"))
        self.a.set_hosting("m1", "receipt_footer", False); self.assertIsNone(self.a.select("m1", "receipt_footer"))
        with self.assertRaises(ValueError): self.a.set_hosting("m1", "pos_idle")

    def test_blocking_an_advertiser_and_relevance_ranking(self):
        a = self.camp(advertiser="Loud", price_minor=1500)
        b = self.camp(advertiser="Useful", price_minor=1000, contexts=["low_stock"])
        self.assertEqual(self.a.select("m1", "pos_idle", context="low_stock")["campaign_id"], b)   # 1,000 x 2 beats 1,500
        self.assertEqual(self.a.select("m1", "pos_idle", context="sale")["campaign_id"], a)
        self.a.block_advertiser("m1", "Loud"); self.assertIsNone(self.a.select("m1", "pos_idle", context="sale"))

    def test_only_seen_impressions_count_and_device_hour_cap(self):
        cid = self.camp(model="cpm", price_minor=1000000)
        self.a.impression("m1", "d1", cid, "pos_idle")                                 # not reported as seen
        self.a.impression("m1", "d1", cid, "pos_idle", visible_pct=40, visible_ms=5000)  # less than half on screen
        self.a.impression("m1", "d1", cid, "pos_idle", visible_pct=90, visible_ms=400)   # too short
        self.assertEqual(self.a.settle(cid)["settled_minor"], 0)
        for i in range(10):
            self.p.c.store.append("m2", "d9", "ad.impression", {"campaign_id": cid, "surface": "pos_idle", "visible_pct": 100, "visible_ms": 2000}, ts=ts(9, i))
        self.assertEqual(self.a.settle(cid)["settled_minor"], 5 * 1000)              # the daily cap of 5 wins over the hour cap of 6

    def test_reports_hide_small_numbers_and_why_never_names_the_person(self):
        cid = self.camp()
        self.a.impression("m1", "d", cid, "pos_idle", visible_pct=100, visible_ms=1500)
        r = self.a.report(cid); self.assertIsNone(r["impressions"]); self.assertIn("fewer than 5", r["note"])
        self.assertIn("never", self.a.why(cid))

    def test_reports_from_three_shops_pause_the_campaign(self):
        cid = self.camp()
        self.assertFalse(self.a.report_ad("m1", cid, "misleading")["paused"])
        self.a.report_ad("m2", cid, "misleading")
        self.assertTrue(self.a.report_ad("m3", cid, "misleading")["paused"])
        self.assertIsNone(self.a.select("m1", "pos_idle"))

    def test_merchant_earnings_add_up(self):
        cid = self.camp(model="cpm", price_minor=1000000)
        self.a.set_hosting("m1", "receipt_footer")
        for i in range(5):
            self.p.c.store.append("m1", "d", "ad.impression", {"campaign_id": cid, "surface": "receipt_footer", "visible_pct": 100, "visible_ms": 2000}, ts=ts(10, i))
        self.a.settle(cid)
        self.assertEqual(self.a.earnings("m1"), {"RWF": 2000})                         # 40% placeholder share of 5,000


if __name__ == "__main__":
    unittest.main()
