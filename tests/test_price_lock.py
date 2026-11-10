"""Prices are LOCKED (version 3, 2026-11-08: LynkStat $0/$12/$29/$79 took over LynkDash, LynkOps $0/$20/$49/$129 with four services; version 2 was 2026-11-07, version 1 2026-11-06). This test pins every standard USD price. To change a price on purpose:
change services/billing.py, change LOCKED_PRICES below, re-run finance/revenue_model.py (tests/test_revenue_model.py
pins its output), then update the blueprint (pricing tables, LynkSuite table, revenue model parts E, F and G), the
project status doc and CLAUDE.md in the same task."""
import unittest

from services import billing

LOCKED_PRICES = {
    "lynkpos": (0, 12, 29, 79), "lynkacc": (0, 6, 15, 40), "lynkinv": (0, 5, 12, 32), "lynkcrm": (0, 6, 15, 40),
    "lynkops": (0, 20, 49, 129), "lynkstock": (0, 3, 9, 22), "lynkrewards": (0, 3, 9, 22),
    "lynkstat": (0, 12, 29, 79), "lynkgrow": (0, 4, 12, 32), "lynkchat": (0, 4, 11, 27), "lynkmpay": (0, 5, 15, 38),
    "lynkrecover": (0, 3, 7, 12), "lynkcheckout": (0, 3, 7, 15), "lynkassist": (0, 6, 15, 35), "lynkvcard": (0, 4, 12, 30),
    "lynkdev": (0, 500, 2500, 15000), "lynkbooking": (0, 4.99, 9.99, 19.99), "lynkessential": (0, 2.99, 5.99, 11.99),
    "lynksuite": (0, 29, 75, 195),
    "lynkmotion": (0, 9, 29, 79), "lynkguard": (0, 15, 49, 149),          # NEW UPDATE 1, 2026-11-10
}
# NEW UPDATE 1 (owner approved 2026-11-10): LynkMotion extras, LynkGuard extra vehicles, the pair discount and the API prices.
LOCKED_MOVEMENT = {"motion_extra_1000_tracked_cents": 500, "motion_extra_live_cents": 100, "guard_extra_asset_cents": (None, None, 150, 100),
                   "guard_assets": (1, 3, 25, 100), "pair_discount_bps": 2000}
LOCKED_API = {"prices": {"tracking_shipment_cents": 1, "geocoding_per_1000_cents": 100, "routing_per_1000_cents": 100,
                         "routing_25_stops_per_1000_cents": 200, "map_tiles_per_1000_cents": 50, "offline_region_month_cents": 1000,
                         "zone_events_per_1000_cents": 100, "lynkstat_queries_per_1000_cents": 100, "lynkassist_requests_per_1000_cents": 200,
                         "translation_per_million_chars_cents": 500},
              "free_monthly": {"tracked_shipments": 100, "geocoding": 10000, "routing": 10000, "map_tiles": 50000}, "business_discount_bps": 2000}


# Storefront plans (BIZZ & DEVICE, owner approved 2026-11-09): the external side's own locked price list, a plan type not a family.
LOCKED_STOREFRONT = {"tiers": ("free", "plus", "pro", "max", "enterprise"), "prices": (0, 12, 29, 79),
                     "share_bps": (800, 500, 300, 150), "cap_usd_cents": {"max": 5000}, "trial_days": {"plus": 14, "pro": 14}}


class TestPriceLock(unittest.TestCase):
    def test_storefront_plans_are_locked_too(self):
        self.assertEqual({"tiers": billing.STOREFRONT_TIERS, "prices": billing.STOREFRONT_PRICES, "share_bps": billing.STOREFRONT_SHARE_BPS,
                          "cap_usd_cents": billing.STOREFRONT_SHARE_CAP_USD_CENTS, "trial_days": billing.STOREFRONT_TRIAL_DAYS}, LOCKED_STOREFRONT)
        self.assertNotIn("storefront", billing.FAMILIES)                       # never a product family, never inside LynkSuite

    def test_movement_extras_and_api_prices_are_locked(self):
        f = billing.FEATURES["lynkguard"]
        self.assertEqual({"motion_extra_1000_tracked_cents": billing.SERVICE_FEES["motion_extra_1000_tracked_cents"],
                          "motion_extra_live_cents": billing.SERVICE_FEES["motion_extra_live_cents"],
                          "guard_extra_asset_cents": tuple(t.get("extra_asset_cents") for t in f), "guard_assets": tuple(t["assets"] for t in f),
                          "pair_discount_bps": billing.MOVEMENT_PAIR_DISCOUNT_BPS}, LOCKED_MOVEMENT)
        self.assertEqual({"prices": billing.API_PRICES, "free_monthly": billing.API_FREE_MONTHLY, "business_discount_bps": billing.API_BUSINESS_DISCOUNT_BPS}, LOCKED_API)
        self.assertNotIn("lynkmotion", billing.SUITE_MEMBERS); self.assertNotIn("lynkguard", billing.SUITE_MEMBERS)    # outside LynkSuite
        self.assertEqual(billing.movement_pair_discount_cents("pro", "plus"), 300)       # 20% of LynkGuard Plus ($15)
        self.assertEqual(billing.movement_pair_discount_cents("free", "max"), 0)          # only when both are paid

    def test_every_standard_price_matches_the_locked_list(self):
        self.assertEqual({k: v[3] for k, v in billing.FAMILIES.items()}, LOCKED_PRICES)

    def test_the_locked_list_covers_every_family(self):
        self.assertEqual(set(LOCKED_PRICES), set(billing.FAMILIES))


if __name__ == "__main__":
    unittest.main()
