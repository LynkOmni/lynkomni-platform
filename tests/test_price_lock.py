"""Prices are LOCKED (version 3, 2026-11-08; BOOKING UPDATE 2026-11-18 set the LynkBooking membership to $0/$1.99/$3.99/$7.99 and locked the LynkBooking business tiers and commission: LynkStat $0/$12/$29/$79 took over LynkDash, LynkOps $0/$20/$49/$129 with four services; version 2 was 2026-11-07, version 1 2026-11-06). This test pins every standard USD price. To change a price on purpose:
change services/billing.py, change LOCKED_PRICES below, re-run finance/revenue_model.py (tests/test_revenue_model.py
pins its output), then update the blueprint (pricing tables, LynkSuite table, revenue model parts E, F and G), the
project status doc and CLAUDE.md in the same task."""
import unittest

from services import billing

LOCKED_PRICES = {
    "lynkpos": (0, 12, 29, 79), "lynkacc": (0, 6, 19, 49), "lynkinv": (0, 5, 15, 39), "lynkcrm": (0, 6, 19, 49),
    "lynkops": (0, 20, 49, 129), "lynkstock": (0, 3, 9, 22), "lynkrewards": (0, 3, 9, 22),
    "lynkstat": (0, 12, 29, 79), "lynkgrow": (0, 4, 12, 32), "lynkchat": (0, 4, 11, 27), "lynkmpay": (0, 5, 15, 38),
    "lynkrecover": (0, 3, 7, 12), "lynkcheckout": (0, 3, 7, 15), "lynkassist": (0, 6, 15, 35), "lynkvcard": (0, 4, 12, 30),
    "lynkdev": (0, 500, 2500, 15000), "lynkbooking": (0, 1.99, 3.99, 7.99), "lynkessential": (0, 2.99, 5.99, 11.99),
    "lynksuite": (0, 29, 75, 195),
    "lynkmotion": (0, 9, 29, 79), "lynkguard": (0, 15, 49, 149),          # NEW UPDATE 1, 2026-11-10
    "lynkattend": (0, 49.5, 95, 179), "lynkqueue": (0, 55, 115, 249), "lynksurvey": (0, 59, 155, 249),   # NEW UPDATE 4, 2026-11-11
    # Section 4 part 1b, 2026-11-19 (owner approved 2026-11-18; blueprint 65.6, 68.11 and 69.11)
    "lynkexchange": (0, 9, 29, 79), "lynkvote": (0, 9, 29, 99), "lynkhr": (0, 9, 29, 79), "lynkproject": (0, 5, 15, 39),
    "lynkschool": (0, 19, 55, 139), "lynkproperty": (0, 9, 29, 79), "lynkfiles": (0, 4, 11, 29), "lynkjobs": (0, 15, 45, 129),
    # Section 4 part 1d, 2026-11-19 (owner "Price rise agreed", blueprint 78.12 and 78.18): LynkSchool Pro $55 (was $49) and Max $139
    # (was $129); the new LynkAcademy family
    "lynkacademy": (0, 19, 49, 129),
}
# Section 4 part 1b (owner approved 2026-11-18): what each tier includes, every extra, the levels, the fees and the bundles.
LOCKED_NEW_FAMILIES = {
    "exchange_part_bps": (50, 40, 30, 20), "exchange_people": (1, 3, 10, None), "exchange_batch_payees": (0, 50, 1000, None),
    "exchange_scheduled": (1, 10, None, None), "exchange_rate_alerts": (3, 25, None, None),
    "exchange_levels": ((0, 50), (100_000, 40), (1_000_000, 30), (10_000_000, 20)), "exchange_crypto_referral_cents": 200,
    "vote_voters": (100, 1000, 10000, 100000), "vote_extra_1000_voters_cents": (None, 300, 200, 100), "vote_contest": (500, 10),
    "vote_government_guide_cents": 10, "vote_bundle": (("lynkattend", "lynkqueue", "lynksurvey", "lynkbooking"), 2000),
    "hr_staff": (5, 50, 250, 1000), "hr_extra_100_cents": (None, 400, 400, 400),
    "project_members": (5, 25, 100, 500), "project_extra_50_cents": (None, 300, 300, 300),
    "school_learners": (100, 500, 2500, 10000), "school_extra_500_cents": (None, 500, 500, 500),
    "property_units": (5, 50, 250, 1000), "property_extra_100_cents": (None, 500, 500, 500),
    "docs_storage_gb": (5, 100, 500, 2048), "docs_signatures": (5, 50, 500, None), "docs_extra_100_gb_cents": (None, 200, 200, 200),
    "jobs_open_jobs": (2, 10, 50, None), "jobs_extra_open_job_cents": (None, 300, 300, 300),
    "jobs_pass": (("free", "plus", "pro", "max"), (0, 1.99, 3.99, 7.99)), "jobs_featured_week_cents": 500, "jobs_freelance_bps": 500,
    "six_bundle_bps": 2000,
    "verified_school_free": {"lynkschool": ("plus", {"learners_included": 500}), "lynkvote": ("plus", {"voters_per_vote": 1000})},
    # Section 4 part 1d (blueprint 78.12, 78.17): LynkAcademy's units and extras, and the LynkAcademy tier each LynkSchool tier includes
    "academy_learners": (10, 50, 250, 1000), "academy_extra_100_cents": (None, 500, 500, 500), "academy_own_courses": (3, None, None, None),
    "school_includes_academy": {"plus": "plus", "pro": "pro", "max": "max"},
}
# NEW UPDATE 4 (owner locked 2026-11-11, blueprint 63.5): what each paid tier includes, the price of each extra, and the bundle discount.
LOCKED_PEOPLE = {"attend_people": (15, 50, 50, 50), "attend_extra_person_cents": (None, 150, 250, 400),
                 "queue_places": (1, 5, 5, 5), "queue_extra_place_cents": (None, 1000, 2000, 4000), "queue_extra_1000_tickets_cents": 200,
                 "survey_creators": (1, 5, 5, 5), "survey_extra_creator_cents": (None, 1000, 2500, 4000), "survey_extra_1000_answers_cents": 100,
                 "bundle_discount_bps": 2000}
# NEW UPDATE 1 (owner approved 2026-11-10): LynkMotion extras, LynkGuard extra vehicles, the pair discount and the API prices.
LOCKED_MOVEMENT = {"motion_extra_1000_tracked_cents": 500, "motion_extra_live_cents": 100, "guard_extra_asset_cents": (None, None, 150, 100),
                   "guard_assets": (1, 3, 25, 100), "pair_discount_bps": 2000}
LOCKED_API = {"prices": {"tracking_shipment_cents": 1, "geocoding_per_1000_cents": 100, "routing_per_1000_cents": 100,
                         "routing_25_stops_per_1000_cents": 200, "map_tiles_per_1000_cents": 50, "offline_region_month_cents": 1000,
                         "zone_events_per_1000_cents": 100, "lynkstat_queries_per_1000_cents": 100, "lynkassist_requests_per_1000_cents": 200,
                         "translation_per_million_chars_cents": 500},
              "free_monthly": {"tracked_shipments": 100, "geocoding": 10000, "routing": 10000, "map_tiles": 50000}, "business_discount_bps": 2000}


# EMULATOR UPDATE (owner accepted 2026-11-18, blueprint 70.12; pinned in build section 3A): staff emulator slots per tier and the one
# new price, $2 a month for each extra slot on a paid tier. LynkAttend, LynkQueue and LynkSurvey keep their own locked units.
LOCKED_EMULATORS = {"ladder": (1, 2, 5, None), "lynkpos": (1, 2, 5, None), "own_units": ("lynkbooking", "lynkattend", "lynkqueue", "lynksurvey"),
                    # owner 2026-11-19: extra devices priced so the next tier stays the better deal, and a day pass for events
                    "extra_cents": {"lynkpos": 800, "lynkmpay": 400, "lynkstock": 300, "lynkrewards": 300, "lynkcheckout": 200, "lynkessential": 200,
                                    "lynkmotion": 800, "lynkguard": 1400},
                    "day_pass": (100, 7)}


# Storefront plans (BIZZ & DEVICE, owner approved 2026-11-09): the external side's own locked price list, a plan type not a family.
LOCKED_STOREFRONT = {"tiers": ("free", "plus", "pro", "max", "enterprise"), "prices": (0, 12, 29, 79),
                     "share_bps": (800, 500, 300, 150), "cap_usd_cents": {"max": 5000}, "trial_days": {"plus": 14, "pro": 14}}


# BOOKING UPDATE (owner locked 2026-11-18, blueprint 64.7): the LynkBooking business tiers, their extras and the commission.
LOCKED_BOOKING = {"tiers": ("free", "plus", "pro", "max"), "prices": (0, 19, 49, 119), "places_included": (1, 3, 3, 3),
                  "extra_place_cents": (None, 500, 1000, 2000), "units_per_place": (3, 15, None, None),
                  "bookings_per_place": (150, 2000, 10000, 50000), "extra_1000_bookings_cents": 100, "bundle_discount_bps": 2000,
                  "commission": {"appointment_first_visit_bps": 500, "appointment_first_visit_cap_cents": 500, "stay_bps": 800,
                                 "tour_bps": 1000, "event_bps": 200, "event_ticket_cents": 25, "transport_bps": 300,
                                 "rental_and_space_bps": 600, "table_guest_cents": 25, "class_bps": 500, "own_customers_bps": 0}}


class TestPriceLock(unittest.TestCase):
    def test_booking_update_prices_and_commission_are_locked(self):
        b = billing
        self.assertEqual({"tiers": b.BOOKING_BUSINESS_TIERS, "prices": b.BOOKING_BUSINESS_PRICES, "places_included": b.BOOKING_PLACES_INCLUDED,
                          "extra_place_cents": b.BOOKING_EXTRA_PLACE_CENTS, "units_per_place": b.BOOKING_UNITS_PER_PLACE,
                          "bookings_per_place": b.BOOKING_BOOKINGS_PER_PLACE, "extra_1000_bookings_cents": b.BOOKING_EXTRA_1000_BOOKINGS_CENTS,
                          "bundle_discount_bps": b.BOOKING_BUNDLE_DISCOUNT_BPS, "commission": b.BOOKING_COMMISSION}, LOCKED_BOOKING)
        self.assertNotIn("lynkbooking", b.SUITE_MEMBERS)                       # outside LynkSuite
        self.assertEqual(b.BOOKING_COMMISSION["own_customers_bps"], 0)         # never a commission on a business's own customers

    def test_lynka_lynkq_and_lynks_extras_and_bundle_are_locked(self):
        F = billing.FEATURES
        def col(fam, key):
            out, last = [], None
            for t in F[fam]:
                last = t.get(key, last); out.append(last)
            return tuple(out)
        self.assertEqual({"attend_people": col("lynkattend", "people_included"), "attend_extra_person_cents": col("lynkattend", "extra_person_cents"),
                          "queue_places": col("lynkqueue", "places_included"), "queue_extra_place_cents": col("lynkqueue", "extra_place_cents"),
                          "queue_extra_1000_tickets_cents": billing.SERVICE_FEES["queue_extra_1000_tickets_cents"],
                          "survey_creators": col("lynksurvey", "creators_included"), "survey_extra_creator_cents": col("lynksurvey", "extra_creator_cents"),
                          "survey_extra_1000_answers_cents": billing.SERVICE_FEES["survey_extra_1000_answers_cents"],
                          "bundle_discount_bps": billing.PEOPLE_BUNDLE_DISCOUNT_BPS}, LOCKED_PEOPLE)
        for f in billing.PEOPLE_FAMILIES: self.assertNotIn(f, billing.SUITE_MEMBERS)          # outside LynkSuite
        self.assertEqual(billing.people_bundle_discount_cents({"lynkattend": "plus", "lynkqueue": "pro"}), 990 + 2300)
        self.assertEqual(billing.people_bundle_discount_cents({"lynkattend": "max", "lynkqueue": "free"}), 0)   # two paid plans needed

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

    def test_emulator_slots_and_the_extra_slot_are_locked(self):
        F = billing.FEATURES
        got = {"ladder": billing.EMULATOR_LADDER, "lynkpos": tuple(t["emulator_slots"] for t in F["lynkpos"]),
               "own_units": tuple(f for f in billing.EMULATOR_FAMILIES if F[f][0]["emulator_slots"] == "own_units"),
               "extra_cents": billing.EMULATOR_EXTRA_CENTS,
               "day_pass": (billing.SERVICE_FEES["emulator_day_pass_cents"], billing.SERVICE_FEES["emulator_day_pass_max_days"])}
        self.assertEqual(got, LOCKED_EMULATORS)
        from core import emulators as E
        for f in billing.EMULATOR_FAMILIES:
            if f not in LOCKED_EMULATORS["own_units"]:
                for t in ("plus", "pro"):                                    # stacking extras never beats the next tier
                    nxt = billing.MT[billing.MT.index(t) + 1]
                    i = billing.MT.index(t)
                    plus3 = round(billing.FAMILIES[f][3][i] * 100) + 3 * LOCKED_EMULATORS["extra_cents"][f]
                    if E.slots(f, t) + 3 >= (E.slots(f, nxt) or 99): self.assertGreater(plus3, round(billing.FAMILIES[f][3][i + 1] * 100), f"{f} {t}")
                self.assertEqual(tuple(t["emulator_slots"] for t in F[f]), LOCKED_EMULATORS["ladder"], f)

    def test_new_families_units_extras_levels_fees_and_bundles_are_locked(self):
        b, F = billing, billing.FEATURES
        def col(fam, key):
            out, last = [], None
            for t in F[fam]:
                last = t.get(key, last); out.append(last)
            return tuple(out)
        got = {
            "exchange_part_bps": col("lynkexchange", "lynkomni_part_bps"), "exchange_people": col("lynkexchange", "people"),
            "exchange_batch_payees": col("lynkexchange", "batch_payees"), "exchange_scheduled": col("lynkexchange", "scheduled_and_targets"),
            "exchange_rate_alerts": col("lynkexchange", "rate_alerts"), "exchange_levels": b.EXCHANGE_LEVELS,
            "exchange_crypto_referral_cents": b.EXCHANGE_CRYPTO_REFERRAL_CENTS,
            "vote_voters": col("lynkvote", "voters_per_vote"), "vote_extra_1000_voters_cents": col("lynkvote", "extra_1000_voters_cents"),
            "vote_contest": (b.VOTE_CONTEST_SHARE_BPS, b.VOTE_CONTEST_SHARE_CAP_CENTS), "vote_government_guide_cents": b.VOTE_GOVERNMENT_GUIDE_CENTS_PER_VOTER,
            "vote_bundle": (b.VOTE_BUNDLE_FAMILIES, b.VOTE_BUNDLE_DISCOUNT_BPS),
            "hr_staff": col("lynkhr", "staff_included"), "hr_extra_100_cents": col("lynkhr", "extra_100_staff_cents"),
            "project_members": col("lynkproject", "members_included"), "project_extra_50_cents": col("lynkproject", "extra_50_members_cents"),
            "school_learners": col("lynkschool", "learners_included"), "school_extra_500_cents": col("lynkschool", "extra_500_learners_cents"),
            "property_units": col("lynkproperty", "units_included"), "property_extra_100_cents": col("lynkproperty", "extra_100_units_cents"),
            "docs_storage_gb": col("lynkfiles", "storage_gb"), "docs_signatures": col("lynkfiles", "signature_requests"),
            "docs_extra_100_gb_cents": col("lynkfiles", "extra_100_gb_cents"),
            "jobs_open_jobs": col("lynkjobs", "open_jobs"), "jobs_extra_open_job_cents": col("lynkjobs", "extra_open_job_cents"),
            "jobs_pass": (b.JOBS_PASS_TIERS, b.JOBS_PASS_PRICES), "jobs_featured_week_cents": b.JOBS_FEATURED_FROM_CENTS_PER_WEEK,
            "jobs_freelance_bps": b.JOBS_FREELANCE_SHARE_BPS, "six_bundle_bps": b.SIX_BUNDLE_DISCOUNT_BPS,
            "verified_school_free": b.VERIFIED_SCHOOL_FREE,
            "academy_learners": col("lynkacademy", "learners_included"), "academy_extra_100_cents": col("lynkacademy", "extra_100_learners_cents"),
            "academy_own_courses": col("lynkacademy", "own_courses"),
            "school_includes_academy": {t: g["lynkacademy"] for (f, t), g in b.INCLUDES.items() if f == "lynkschool"},
        }
        self.assertEqual(got, LOCKED_NEW_FAMILIES)
        for f in ("lynkexchange", "lynkvote", "lynkacademy") + b.SIX_FAMILIES: self.assertNotIn(f, b.SUITE_MEMBERS)     # all outside LynkSuite
        self.assertEqual(b.exchange_part_bps("plus", 500_000), 40); self.assertEqual(b.exchange_part_bps("free", 20_000_000), 20)   # the lower of tier and level
        self.assertEqual(b.vote_contest_share_cents(1000), 10)                                    # 5%, capped at $0.10 a vote
        self.assertEqual(b.six_bundle_discount_cents({"lynkhr": "plus", "lynkfiles": "pro"}), 180 + 220)
        self.assertEqual(b.six_bundle_discount_cents({"lynkhr": "plus", "lynkattend": "plus"}), 180)      # one of the six with LynkAttend
        self.assertEqual(b.six_bundle_discount_cents({"lynkhr": "plus", "lynkfiles": "free"}), 0)           # two paid plans needed
        self.assertEqual(b.vote_bundle_discount_cents({"lynkvote": "pro", "lynkqueue": "plus"}), 580)

    def test_every_standard_price_matches_the_locked_list(self):
        self.assertEqual({k: v[3] for k, v in billing.FAMILIES.items()}, LOCKED_PRICES)

    def test_the_locked_list_covers_every_family(self):
        self.assertEqual(set(LOCKED_PRICES), set(billing.FAMILIES))


if __name__ == "__main__":
    unittest.main()
