"""Software only (owner rule, blueprint 48 and 89.1, 27 November 2026).

LynkOmni gives software only. Every piece of hardware comes from the user and connects through open standards or
LynkDriver; any applicable hardware works. LynkOmni hardware is supplied only when the user orders it: never needed to
start a service and never part of a plan. Every hardware kind has a stand-in on a phone or screen, or a written reason why
it cannot have one, so no service waits on hardware."""
import glob
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import drivers as D  # noqa: E402
from services import billing as B  # noqa: E402


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


class SoftwareOnly(unittest.TestCase):
    def test_the_rule_is_in_the_driver_register(self):
        so = D.REGISTER["software_only"]
        self.assertEqual(so["supplied_by"], "user")
        self.assertEqual(so["lynkomni_hardware"], "only_when_ordered")
        self.assertEqual(D.validate(), [])

    def test_every_hardware_kind_has_a_stand_in_or_a_reason(self):
        for k in D.REGISTER["kinds"]:
            with self.subTest(kind=k["id"]):
                self.assertTrue(k.get("virtual") or k.get("no_stand_in"), "a stand-in on a phone or screen, or why none")

    def test_the_check_catches_a_missing_reason(self):
        kind = next(k for k in D.REGISTER["kinds"] if not k.get("virtual"))
        saved = kind.pop("no_stand_in")
        try:
            self.assertTrue(any(kind["id"] in p for p in D.validate()))
        finally:
            kind["no_stand_in"] = saved

    def test_no_plan_includes_lynkomni_hardware(self):
        # Plans may let a business use its OWN hardware (own_hardware); a plan never comes with LynkOmni hardware.
        bad = re.compile(r"(hardware|terminal|device|tracker|camera|barrier)s?_(included|supplied|free)|free_(hardware|terminal|device)")
        found = []
        for fam, tiers in B.FEATURES.items():
            for t in (tiers if isinstance(tiers, list) else tiers.values()):
                if isinstance(t, dict):
                    found += [f"{fam}.{k}" for k in t if bad.search(k)]
        self.assertEqual(found, [])

    def test_no_screen_promises_hardware_from_lynkomni(self):
        claim = re.compile(r"(hardware|terminal|device)s? (is |are )?included|free (hardware|terminal)|we (send|supply|ship) (you )?(a |the )?(hardware|terminal|device)", re.I)
        found = []
        for p in glob.glob(os.path.join(ROOT, "web", "**", "strings.en.json"), recursive=True):
            for k, v in load(os.path.relpath(p, ROOT)).items():
                if isinstance(v, str) and claim.search(v):
                    found.append(f"{os.path.relpath(p, ROOT)} {k}")
        self.assertEqual(found, [])

    def test_it_is_a_rule_for_everything(self):
        ids = [r["id"] for r in load("catalog/universal.v1.json")["everywhere"]]
        self.assertIn("software_only", ids)


if __name__ == "__main__":
    unittest.main()
