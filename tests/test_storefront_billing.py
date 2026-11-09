"""Storefront plans (BIZZ & DEVICE, owner approved 2026-11-09): one plan per account for every service's Storefront, the
share taken only on Storefront sales, integers only, the Max cap, workspace prices untouched, nothing billed twice."""
import os, unittest
from core.money import to_minor
from services import billing
from services.billing import STOREFRONT_FEATURES, STOREFRONT_TIERS, storefront_share
from services.platform import Platform


class Share(unittest.TestCase):
    def test_share_per_plan_in_whole_minor_units(self):
        self.assertEqual([storefront_share(t, 10_000) for t in ("free", "plus", "pro", "max")], [800, 500, 300, 150])
        self.assertEqual(storefront_share("plus", 1), 0)                     # 0.05 of a minor unit rounds to nothing
        self.assertEqual(storefront_share("free", 7), 1)                     # 0.56 rounds half up
        self.assertEqual(storefront_share("pro", 0), 0)
        self.assertEqual(storefront_share("free", 10_000, free_item=True), 0)  # free material is never charged
        self.assertIsNone(storefront_share("enterprise", 10_000))            # by contract

    def test_max_cap_and_bad_input(self):
        self.assertEqual(storefront_share("max", 1_000_000, cap_minor=5_000), 5_000)
        self.assertEqual(storefront_share("max", 100_000, cap_minor=5_000), 1_500)
        self.assertEqual(storefront_share("pro", 1_000_000, cap_minor=5_000), 30_000)   # the cap is only on Max
        for bad in (-1, 1.5, True, "100"):
            with self.assertRaises(ValueError): storefront_share("plus", bad)
        with self.assertRaises(ValueError): storefront_share("gold", 100)

    def test_each_plan_gives_at_least_the_one_below(self):
        for i in range(1, 4):
            lo, hi = STOREFRONT_FEATURES[i - 1], STOREFRONT_FEATURES[i]
            self.assertTrue(hi["items"] is None or (lo["items"] is not None and hi["items"] > lo["items"]))
            self.assertGreater(hi["team"], lo["team"]); self.assertGreater(hi["live_seats"], lo["live_seats"]) if lo["live_seats"] else None
        self.assertEqual(STOREFRONT_FEATURES[0]["powered_by"], "required")
        self.assertTrue(all(f["powered_by"] == "removable" for f in STOREFRONT_FEATURES[1:]))   # the existing rule: removable on paid


class Bill(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.b = self.p.billing
        self.p.register("a", "RW")

    def rwf(self, usd): return self.p.c.fx.convert(to_minor(usd * .35, "USD"), "USD", "RWF")

    def test_one_storefront_line_beside_the_workspace_plans(self):
        self.b.set_plan("a", "lynkpos", "plus"); self.b.set_storefront_plan("a", "pro")
        lines = self.b.bill("a")["lines"]
        self.assertEqual([(l["family"], l["side"]) for l in lines], [("lynkpos", "internal"), ("storefront", "external")])
        self.assertEqual(lines[1]["amount_minor"], self.rwf(29))
        self.assertEqual(lines[0]["amount_minor"], self.rwf(12))               # the workspace price never changes

    def test_free_and_enterprise_add_no_line_and_suite_never_covers_storefront(self):
        self.b.set_plan("a", "lynksuite", "max")
        self.assertNotIn("storefront", [l["family"] for l in self.b.bill("a")["lines"]])
        self.b.set_storefront_plan("a", "enterprise")
        self.assertNotIn("storefront", [l["family"] for l in self.b.bill("a")["lines"]])
        self.b.set_storefront_plan("a", "plus")
        self.assertIn("storefront", [l["family"] for l in self.b.bill("a")["lines"]])
        with self.assertRaises(ValueError): self.b.set_storefront_plan("a", "gold")

    def test_support_priority_is_the_highest_across_all_plans(self):
        self.assertEqual(self.b.support_level("a"), "help")
        self.b.set_storefront_plan("a", "max")
        self.assertEqual(self.b.support_level("a"), "dedicated")
        self.assertEqual(self.b.storefront_entitlement("a")["items"], None)


if __name__ == "__main__": unittest.main()
