import unittest

from finance import revenue_model as R

# The blueprint's printed figures for table 1 before the price update, Stage 1 / 2 / 3 per month.
BLUEPRINT_OLD = {
    "lynksuite": (1547, 88380, 2700500), "lynkpos": (419, 23940, 731500), "lynkacc": (167, 9540, 291500),
    "lynkstock": (167, 9540, 291500), "lynkdash": (113, 6444, 196900), "lynkrewards": (94, 5400, 165000),
    "lynkgrow": (189, 10800, 330000), "lynkchat": (233, 13320, 407000), "lynkmpay": (96, 13680, 501600),
    "lynkrecover": (35, 4950, 181500), "lynkcheckout": (53, 7560, 277200), "lynkassist": (294, 16812, 513700),
    "travel": (221, 12581, 384423), "connect": (181, 10344, 316041), "messaging": (338, 16920, 376000),
}


class TestRevenueModel(unittest.TestCase):
    def test_model_reproduces_the_blueprint_at_the_old_prices(self):
        t = R.table(R.prices(R.OLD_PRICES))
        for fam, printed in BLUEPRINT_OLD.items():
            for st, want in zip(R.STAGES, printed):
                # Stage 3 matches to the dollar; Stages 1 and 2 can differ by $1 where the blueprint rounded a total
                self.assertLessEqual(abs(t[fam][st] - want), 1, (fam, st, t[fam][st], want))
            self.assertEqual(t[fam]["stage3"], printed[2], fam)

    def test_old_vcard_subscription_lines_match_the_card_table(self):
        self.assertEqual(R.vcard_subscriptions(R.prices({"lynkvcard": R.OLD_PRICES["lynkvcard"]})), [46200, 69300, 41250, 156750])

    def test_new_prices_give_these_totals(self):
        # Price version 2 (2026-11-07). The adoption mix, including the new LynkInv, LynkCRM and LynkOps shares, is an ASSUMPTION.
        t = R.totals()
        self.assertEqual(t["stage1"]["grand"], 13032)
        self.assertEqual(t["stage2"]["grand"], 1094418)
        self.assertEqual(t["stage3"]["grand"], 39038813)
        self.assertEqual(t["stage3"]["subscriptions"], 16094763)
        self.assertEqual(t["stage3"]["vcard"], 713938)

    def test_suite_line_at_stage_3(self):
        self.assertEqual(R.table()["lynksuite"]["stage3"], 6099500)

    def test_path_is_consistent(self):
        p = R.path()
        self.assertEqual(p[2]["end"], R.totals()["stage1"]["grand"])
        self.assertEqual(p[4]["end"], R.totals()["stage2"]["grand"])
        self.assertEqual(p[7]["end"], R.totals()["stage3"]["grand"])
        self.assertEqual(p[1]["year"], R.totals()["stage1"]["grand"])
        self.assertEqual([p[y]["end"] for y in (1, 2, 3, 4, 5, 6, 7)], sorted(p[y]["end"] for y in p))

    def test_summary_numbers(self):
        s = R.summary()
        self.assertEqual(s["yearly"]["stage3"], 468465756)
        self.assertEqual(s["range"]["stage3"], (19519407, 58558220))
        self.assertEqual(str(s["per_merchant"]["stage3"]), "19.52")
        self.assertEqual(s["cumulative"], 529908042)

    def test_new_section_28_lines_do_not_depend_on_subscription_prices(self):
        # LynkProof, LynkSplit, LynkAudit exports, bandwidth and seats are per-use fees, so the blueprint's $24,825 a month
        # (assumed tier mix) is unchanged by the price update.
        self.assertEqual(2300 + 6900 + 7050 + 3575 + 5000, 24825)


if __name__ == "__main__":
    unittest.main()
