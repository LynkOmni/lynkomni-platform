"""The automation register (master blueprint section 45, owner approved 2026-11-08) and its safety rules."""
import json, pathlib, re, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from services import billing
R = json.loads((ROOT / "catalog" / "automations.v1.json").read_text())
A = R["automations"]
NON_FAMILY = {"platform", "customer", "staff", "partner"}

class Automations(unittest.TestCase):
    def test_ids_are_unique_and_kebab_case(self):
        ids = [a["id"] for a in A]
        self.assertEqual(len(ids), len(set(ids)))
        for i in ids: self.assertRegex(i, r"^[a-z0-9]+(-[a-z0-9]+)*$")

    def test_every_automation_has_a_build_section_level_and_valid_plan(self):
        for a in A:
            self.assertIn(a["build_section"], range(0, 15), a["id"])
            self.assertIn(a["level"], R["levels"], a["id"])
            if a["assist"] is not None: self.assertIn(a["assist"], R["assist_roles"], a["id"])
            if a["family"] not in NON_FAMILY:
                self.assertIn(a["family"], billing.FAMILIES, a["id"])
                self.assertIn(a["min_tier"], billing.FAMILIES[a["family"]][2], a["id"])
            self.assertRegex(a["trigger"], r"^(event|schedule|user|metric):", a["id"])

    def test_sensitive_work_is_never_automatic(self):
        for a in A:
            if set(a["touches"]) & set(R["sensitive"]):
                self.assertIn(a["level"], ("inform", "draft"), a["id"])
            if set(a["touches"]) & set(R["careful"]):
                self.assertNotEqual(a["level"], "auto", a["id"])

    def test_money_moves_only_on_confirmation_or_standing_instruction(self):
        for a in A:
            if "money" in a["touches"] and a["level"] != "draft":
                self.assertTrue(a["standing_instruction"], a["id"])
                self.assertEqual(a["level"], "auto", a["id"])
                self.assertTrue(a["customer_message"], a["id"])          # told every time

    def test_customer_messages_have_a_basis(self):
        for a in A:
            if a["customer_message"]: self.assertIn(a.get("consent"), ("transactional", "opt_in"), a["id"])

    def test_every_build_section_with_people_is_covered(self):
        self.assertEqual({a["build_section"] for a in A} >= set(range(1, 15)), True)

    def test_assist_never_on_forbidden_actions(self):
        for a in A:
            if a["assist"] and a["level"] in ("auto", "auto_undo"):
                self.assertFalse(set(a["touches"]) & set(R["sensitive"]) | ({"money"} & set(a["touches"])), a["id"])

    def test_assist_limits_live_in_billing(self):
        f = billing.FEATURES["lynkassist"]
        self.assertEqual([t.get("custom_automations") for t in f], [0, 3, 20, None])

if __name__ == "__main__": unittest.main()
