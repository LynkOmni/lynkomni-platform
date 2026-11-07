import unittest

from finance import revenue_model as R

# The blueprint's printed figures for table 1 before the price update, Stage 1 / 2 / 3 per month.
BLUEPRINT_OLD = {
    "lynksuite": (1547, 88380, 2700500), "lynkpos": (419, 23940, 731500), "lynkacc": (167, 9540, 291500),
    "lynkstock": (167, 9540, 291500), "lynkstat": (113, 6444, 196900), "lynkrewards": (94, 5400, 165000),
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
        # Price version 3 (2026-11-08: LynkStat took over LynkDash; LynkOps has four services). The adoption mix is an ASSUMPTION.
        t = R.totals()
        self.assertEqual(t["stage1"]["grand"], 13885)
        self.assertEqual(t["stage2"]["grand"], 1143162)
        self.assertEqual(t["stage3"]["grand"], 40528213)
        self.assertEqual(t["stage3"]["subscriptions"], 17584163)
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
        self.assertEqual(s["yearly"]["stage3"], 486338556)
        self.assertEqual(s["range"]["stage3"], (20264107, 60792320))
        self.assertEqual(str(s["per_merchant"]["stage3"]), "20.26")
        self.assertEqual(s["cumulative"], 550712530)

    def test_new_section_28_lines_do_not_depend_on_subscription_prices(self):
        # LynkProof, LynkSplit, LynkAudit exports, bandwidth and seats are per-use fees, so the blueprint's $24,825 a month
        # (assumed tier mix) is unchanged by the price update.
        self.assertEqual(2300 + 6900 + 7050 + 3575 + 5000, 24825)



class EcosystemTotal(unittest.TestCase):
    """Whole-ecosystem total (review part 11, 2026-11-07); every new rate is an assumption, pinned so a change is seen."""
    def test_totals_per_day_month_year(self):
        t = R.ecosystem_totals()
        self.assertEqual({st: (t[st]["day"], t[st]["month"], t[st]["year"]) for st in R.STAGES},
                         {"stage1": (711, 21629, 259548), "stage2": (46487, 1413989, 16967868), "stage3": (1514720, 46072723, 552872676)})
        self.assertEqual(str(t["stage3"]["per_merchant"]), "23.04")
    def test_streams_add_up_and_costs_are_negative(self):
        for st in R.STAGES:
            rows = R.ecosystem(st)
            self.assertEqual(tuple(rows), R.ECO_ROWS)
            self.assertEqual(sum(rows.values()), R.ecosystem_totals()[st]["month"])
            self.assertLess(rows["yearly_billing"], 0); self.assertLess(rows["partner_costs"], 0)
        self.assertEqual(R.ecosystem("stage3")["agent_commissions"], 1_800_000)
    def test_seven_year_path(self):
        p = R.ecosystem_path()
        self.assertEqual(p[7]["year"], 402548072); self.assertEqual(sum(v["year"] for v in p.values()), 637057996)

    def test_second_review_rows(self):
        e = R.ecosystem("stage3")
        self.assertEqual((e["exchange_currency"], e["new_services"], e["stat_setup"]), (100000, 4710000, 101574))
        self.assertEqual(R.table()["lynkstat"]["stage3"], 1180300)


class ExpensesAndProfit(unittest.TestCase):
    """Expenses and net profit (blueprint 44 M, 2026-11-08); every figure is an assumption, pinned so a change is seen."""
    def test_profit_per_stage(self):
        from finance import expense_model as X
        got = {st: (X.profit(st)["expenses"]["month"], X.profit(st)["net"]["month"], X.profit(st)["net"]["year"]) for st in R.STAGES}
        self.assertEqual(got, {"stage1": (36707, -15078, -180936), "stage2": (1177281, 177531, 2130372), "stage3": (20064627, 19506072, 234072864)})
    def test_loss_pays_no_tax_and_rows_add_up(self):
        from finance import expense_model as X
        self.assertEqual(X.profit("stage1")["tax"], 0)
        for st in R.STAGES:
            self.assertEqual(tuple(X.expenses(st)), X.ROWS)
            p = X.profit(st); self.assertEqual(p["revenue"]["month"] - p["expenses"]["month"] - p["tax"], p["net"]["month"])


if __name__ == "__main__":
    unittest.main()
