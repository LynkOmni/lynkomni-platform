"""LynkSchool's limits and registers (SCHOOL UPDATE, master blueprint 80.13 and 80.15; section 4 row 80.15): every kind of school,
the school year, offline working and the safety rules on every tier; Plus, Pro and Max add their tools; the register and billing
agree; LynkAssist never grades, admits, promotes, disciplines, expels or reports on a child by itself."""
import unittest

from core import school as S
from services import billing as B


def merged(tier):
    out = {}
    for row in B.FEATURES["lynkschool"][:S.TIERS.index(tier) + 1]:
        out.update(row)
    return out


class SchoolRegister(unittest.TestCase):
    def test_the_register_and_billing_agree_on_every_tier(self):
        for tier in S.TIERS:
            have = merged(tier)
            for f in S.features(tier):
                self.assertTrue(have.get(f), f"{tier}: {f}")
            later = [f for t in S.TIERS[S.TIERS.index(tier) + 1:] for f in S.SCHOOL["features_by_tier"].get(t, [])]
            for f in later:
                self.assertFalse(have.get(f), f"{tier} must not have {f}")

    def test_safety_rules_school_year_and_offline_are_on_every_tier(self):
        for tier in S.TIERS:
            for f in ("safety_rules", "school_year", "offline_keeper", "every_kind_of_school"):
                self.assertIn(f, S.features(tier))

    def test_every_kind_of_school_belongs_to_one_group(self):
        kinds = [k for ks in S.SCHOOL["kinds"].values() for k in ks]
        self.assertEqual(len(kinds), len(set(kinds)))
        self.assertEqual(S.kind_tools_tier("university"), "pro")
        self.assertEqual(S.kind_tools_tier("primary"), "free")
        with self.assertRaises(ValueError):
            S.group_of("spaceship_academy")

    def test_lynkassist_never_decides_about_a_child(self):
        for act in ("grade", "admit", "promote", "discipline", "expel", "report on a child by itself"):
            self.assertFalse(S.assist_may(act), act)
        self.assertTrue(S.assist_may("draft report comments for the teacher"))
        self.assertIn("advertising", S.SCHOOL["children"]["never"])


if __name__ == "__main__":
    unittest.main()
