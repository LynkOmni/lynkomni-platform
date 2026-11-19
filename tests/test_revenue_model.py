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
        # Price version 3 (2026-11-08) with BOOKING UPDATE (2026-11-18: LynkBooking Pass at $1.99, $3.99 and $7.99, and no flat appointment fee; OFFICE UPDATE 2026-11-19: LynkAcc, LynkInv and LynkCRM top-up). The adoption mix is an ASSUMPTION.
        t = R.totals()
        self.assertEqual(t["stage1"]["grand"], 13890)
        self.assertEqual(t["stage2"]["grand"], 1142666)
        self.assertEqual(t["stage3"]["grand"], 40503613)
        self.assertEqual(t["stage3"]["subscriptions"], 17599563)
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
        self.assertEqual(s["yearly"]["stage3"], 486043356)
        self.assertEqual(s["range"]["stage3"], (20251807, 60755420))
        self.assertEqual(str(s["per_merchant"]["stage3"]), "20.25")
        self.assertEqual(s["cumulative"], 550438994)

    def test_new_section_28_lines_do_not_depend_on_subscription_prices(self):
        # LynkProof, LynkSplit, LynkAudit exports, bandwidth and seats are per-use fees, so the blueprint's $24,825 a month
        # (assumed tier mix) is unchanged by the price update.
        self.assertEqual(2300 + 6900 + 7050 + 3575 + 5000, 24825)



class EcosystemTotal(unittest.TestCase):
    """Whole-ecosystem total (review part 11, 2026-11-07); every new rate is an assumption, pinned so a change is seen."""
    def test_totals_per_day_month_year(self):
        t = R.ecosystem_totals()
        self.assertEqual({st: (t[st]["day"], t[st]["month"], t[st]["year"]) for st in R.STAGES},
                         {"stage1": (711, 21632, 259584), "stage2": (46470, 1413452, 16961424), "stage3": (1513870, 46046891, 552562692)})
        self.assertEqual(str(t["stage3"]["per_merchant"]), "23.02")
    def test_streams_add_up_and_costs_are_negative(self):
        for st in R.STAGES:
            rows = R.ecosystem(st)
            self.assertEqual(tuple(rows), R.ECO_ROWS)
            self.assertEqual(sum(rows.values()), R.ecosystem_totals()[st]["month"])
            self.assertLess(rows["yearly_billing"], 0); self.assertLess(rows["partner_costs"], 0)
        self.assertEqual(R.ecosystem("stage3")["agent_commissions"], 1_800_000)
    def test_seven_year_path(self):
        p = R.ecosystem_path()
        self.assertEqual(p[7]["year"], 402329565); self.assertEqual(sum(v["year"] for v in p.values()), 636773782)

    def test_second_review_rows(self):
        e = R.ecosystem("stage3")
        self.assertEqual((e["exchange_currency"], e["new_services"], e["stat_setup"]), (100000, 4710000, 101574))
        self.assertEqual(R.table()["lynkstat"]["stage3"], 1180300)


class ExpensesAndProfit(unittest.TestCase):
    """Expenses and net profit (blueprint 44 M, 2026-11-08); every figure is an assumption, pinned so a change is seen."""
    def test_profit_per_stage(self):
        from finance import expense_model as X
        got = {st: (X.profit(st)["expenses"]["month"], X.profit(st)["net"]["month"], X.profit(st)["net"]["year"]) for st in R.STAGES}
        self.assertEqual(got, {"stage1": (36872, -15240, -182880), "stage2": (1182798, 172990, 2075880), "stage3": (20175166, 19403794, 232845528)})
    def test_loss_pays_no_tax_and_rows_add_up(self):
        from finance import expense_model as X
        self.assertEqual(X.profit("stage1")["tax"], 0)
        for st in R.STAGES:
            self.assertEqual(tuple(X.expenses(st)), X.ROWS)
            p = X.profit(st); self.assertEqual(p["revenue"]["month"] - p["expenses"]["month"] - p["tax"], p["net"]["month"])


    def test_storefront_stream_is_separate_and_an_assumption(self):
        # BIZZ & DEVICE (2026-11-09): the Storefront is its own stream, outside the agreed totals until pilot data exists
        got = {st: R.storefront(st) for st in R.STAGES}
        self.assertEqual({st: (g["sellers"], g["plans"], g["shares"], g["month"]) for st, g in got.items()},
                         {"stage1": (150, 225, 2_048, 2_273), "stage2": (8_000, 20_563, 109_248, 129_811), "stage3": (200_000, 785_400, 2_731_200, 3_516_600)})
        self.assertTrue(all(g["assumption"] for g in got.values()))
        self.assertNotIn("storefront", R.ECO_ROWS)

    def test_movement_and_api_stream_is_separate_and_an_assumption(self):
        # NEW UPDATE 1 (2026-11-10): LynkMotion, LynkGuard and API usage are their own stream, outside the agreed totals until pilot data exists
        got = {st: R.movement(st) for st in R.STAGES}
        self.assertEqual({st: (g["motion"], g["guard"], g["api"], g["month"]) for st, g in got.items()},
                         {"stage1": (735, 712, 240, 1_687), "stage2": (42_012, 40_680, 8_000, 90_692), "stage3": (1_283_700, 1_243_000, 160_000, 2_686_700)})
        self.assertTrue(all(g["assumption"] for g in got.values()))
        self.assertNotIn("lynkmotion", R.ECO_ROWS); self.assertNotIn("lynkguard", R.ECO_ROWS)


    def test_lynka_lynkq_and_lynks_stream_is_separate_and_an_assumption(self):
        # NEW UPDATE 4 (2026-11-11): LynkAttend, LynkQueue and LynkSurvey are their own stream, outside the agreed totals until pilot data exists
        got = {st: R.people(st) for st in R.STAGES}
        self.assertEqual({st: (g["attend"], g["queue"], g["survey"], g["month"]) for st, g in got.items()},
                         {"stage1": (4_395, 1_648, 1_592, 7_634), "stage2": (251_115, 94_147, 90_989, 436_251),
                          "stage3": (7_672_962, 2_876_709, 2_780_206, 13_329_877)})
        self.assertTrue(all(g["assumption"] for g in got.values()))
        for f in ("lynkattend", "lynkqueue", "lynksurvey"): self.assertNotIn(f, R.ECO_ROWS)

    def test_emulator_extra_slot_stream_is_separate_and_an_assumption(self):
        # EMULATOR UPDATE (build section 3A; owner 2026-11-19): extra devices per family and day passes are their own stream,
        # outside the agreed totals until pilot data exists
        got = {st: R.emulator_slots(st) for st in R.STAGES}
        self.assertEqual({st: (g["extra"], g["day_passes"], g["month"]) for st, g in got.items()},
                         {"stage1": (202, 126, 328), "stage2": (11_556, 4_800, 16_356), "stage3": (353_100, 132_000, 485_100)})
        self.assertTrue(all(g["assumption"] for g in got.values()))

    def test_new_families_stream_is_separate_and_an_assumption(self):
        # Section 4 part 1b (2026-11-19): the eight new families and LynkJobs Pass are their own stream, outside the agreed totals
        # until pilot data exists; every figure is an assumption
        got = {st: R.new_families(st) for st in R.STAGES}
        self.assertEqual({st: (g["exchange"], g["vote"], g["hr"], g["project"], g["school"], g["property"], g["files"], g["jobs"], g["jobs_pass"], g["month"])
                          for st, g in got.items()},
                         {"stage1": (840, 137, 314, 209, 152, 169, 171, 207, 14, 2213),
                          "stage2": (48024, 7828, 17952, 11946, 8714, 9644, 9746, 11827, 789, 126470),
                          "stage3": (1467400, 239184, 548537, 365002, 266255, 294690, 297792, 361383, 24118, 3864361)})
        self.assertTrue(all(g["assumption"] for g in got.values()))
        self.assertNotIn("new_families", R.ECO_ROWS)

    def test_booking_update_stream_is_separate_and_an_assumption(self):
        # BOOKING UPDATE (2026-11-18): the LynkBooking business tiers and commission are their own stream, outside the agreed totals
        # until pilot data exists; LynkBooking Pass (the customer membership) is the "travel" line inside the totals
        got = {st: R.booking_update(st) for st in R.STAGES}
        self.assertEqual({st: (g["plans"], g["commission"], g["month"]) for st, g in got.items()},
                         {"stage1": (958, 900, 1858), "stage2": (54724, 50000, 104724), "stage3": (1672132, 1600000, 3272132)})
        self.assertTrue(all(g["assumption"] for g in got.values()))
        self.assertNotIn("booking_update", R.ECO_ROWS)
        self.assertEqual(tuple(R.table()["travel"][st] for st in R.STAGES), (88, 5021, 153423))
        self.assertEqual(tuple(R.booking_group(st) for st in R.STAGES), (299, 75855, 4172000))   # without the old flat appointment fee

if __name__ == "__main__":
    unittest.main()
