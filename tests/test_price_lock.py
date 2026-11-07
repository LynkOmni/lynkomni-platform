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
}


class TestPriceLock(unittest.TestCase):
    def test_every_standard_price_matches_the_locked_list(self):
        self.assertEqual({k: v[3] for k, v in billing.FAMILIES.items()}, LOCKED_PRICES)

    def test_the_locked_list_covers_every_family(self):
        self.assertEqual(set(LOCKED_PRICES), set(billing.FAMILIES))


if __name__ == "__main__":
    unittest.main()
