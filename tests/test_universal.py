"""Rules for all services apply to every service, existing or new (owner rule 2026-11-19; catalog/universal.v1.json read through
core/universal.py). A new billing family fails here until it has a home build section; from then on every rule is checked for it
by itself. A rule is met, not applicable with a written reason (only where allowed), or due in the home section, and a section
cannot lock while anything is due there."""
import os, unittest
from core import build_sections as b, universal as u
from services import billing

ORDER = [str(n) for n in b.ORDER]
FAMILIES = sorted(billing.FAMILIES)


class Universal(unittest.TestCase):
    def test_every_family_has_a_home_section_in_the_build_order(self):
        homes = u.REGISTER["home_sections"]
        self.assertEqual(sorted(homes), FAMILIES, "every billing family, and only them, needs a home build section")
        for f, s in homes.items():
            self.assertIn(s, ORDER, f)
        for f in u.REGISTER["bundles"]:
            self.assertIn(f, homes)

    def test_rules_are_well_formed(self):
        for r in u.REGISTER["rules"]:
            self.assertEqual(r["check"], "auto", r["id"])
            self.assertTrue(r["what"] and r["blueprint"], r["id"])
        for e in u.REGISTER["everywhere"]:
            self.assertTrue(e["what"] and e["enforced_by"], e["id"])
        self.assertIn("tracking", u.RULES)

    def test_reasons_are_real_and_only_where_allowed(self):
        for rule, fams in u.REGISTER["not_applicable"].items():
            self.assertIn(rule, u.RULES)
            self.assertTrue(u.RULES[rule]["na_allowed"], f"{rule} has no exceptions")
            for f, why in fams.items():
                self.assertIn(f, FAMILIES, f"{rule}: {f} is not a family")
                self.assertGreaterEqual(len(why), 15, f"{rule} {f}: give a real reason")
                self.assertNotEqual(u.status(f, rule)[0], "due", f"{rule} {f}")

    def test_every_family_and_rule_has_an_answer(self):
        for f, row in u.table(FAMILIES).items():
            self.assertEqual(set(row), set(u.RULES))
            for r, (state, where) in row.items():
                self.assertIn(state, ("met", "not_applicable", "due"))
                if state == "due":
                    self.assertIn(str(where), ORDER, f"{f} {r}")

    def test_a_locked_section_has_nothing_due(self):
        for s in b.SECTIONS:
            if s.get("status") == "locked":
                self.assertEqual(u.due(s["n"]), [], f"section {s['n']} is locked but rules for all services are still due there")

    def test_a_new_family_is_checked_by_every_rule_at_once(self):
        row = u.table(["lynkexample"])["lynkexample"]
        self.assertEqual({r: s for r, (s, _) in row.items()}, {r: "due" for r in u.RULES})


if __name__ == "__main__":
    unittest.main()
