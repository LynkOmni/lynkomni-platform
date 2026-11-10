"""Cash everywhere it applies (owner rule 2026-11-10): catalog/cash.v1.json lists every place money is taken in person. A built
place really shows the cash choice on its device screens; a planned place names the build section that builds it."""
import json, os, unittest
from core import build_sections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = json.load(open(os.path.join(ROOT, "catalog", "cash.v1.json"), encoding="utf-8"))
SHOW = json.load(open(os.path.join(ROOT, "web", "showcase", "showcase.v1.json"), encoding="utf-8"))
LOCKED = {s["n"] for s in SHOW["sections"] if s.get("status") == "locked"}


class TestCashEverywhere(unittest.TestCase):
    def test_every_point_is_complete_and_works_offline(self):
        ids = [p["id"] for p in REG["points"]]
        self.assertEqual(len(ids), len(set(ids)))
        for p in REG["points"]:
            self.assertTrue(p["what"] and p["service"], p["id"])
            self.assertIn(p["whose_cash"], REG["whose_cash"], p["id"])
            self.assertIs(p["offline"], True, f"{p['id']}: cash never needs the network")
            self.assertIn(p["build_section"], build_sections.ORDER, p["id"])
            self.assertIn(p["status"], ("built", "planned"), p["id"])

    def test_built_points_are_in_locked_sections_and_planned_ones_come_later(self):
        for p in REG["points"]:
            if p["status"] == "built":
                self.assertIn(p["build_section"], LOCKED, f"{p['id']}: built but its section is not locked")
            else:
                self.assertNotIn(p["build_section"], LOCKED, f"{p['id']}: its section is locked, so cash must be built there now")
                self.assertNotIn("shown_in", p, p["id"])

    def test_built_points_show_the_cash_choice_on_their_screens(self):
        for p in REG["points"]:
            if p["status"] != "built": continue
            self.assertTrue(p.get("shown_in"), p["id"])
            for s in p["shown_in"]:
                src = open(os.path.join(ROOT, "web", "emulators", s["emulator"], "app.ts"), encoding="utf-8").read()
                self.assertIn(s["marker"], src, f"{p['id']}: no cash choice in {s['emulator']}")

    def test_pickup_cash_is_recorded_and_never_waits_for_the_network(self):
        src = open(os.path.join(ROOT, "web", "emulators", "merchant-phone", "app.ts"), encoding="utf-8").read()
        body = src[src.index("function payCash()"):src.index("function payElectronic()")]
        self.assertIn('emit("PaymentRecorded"', body); self.assertIn('"cash"', body)
        self.assertNotIn("online()", body, "cash on collection must work offline")
        electronic = src[src.index("function payElectronic()"):src.index("const ppState")]
        self.assertIn("online()", electronic); self.assertIn('S.outcome === "confirm"', electronic)

    def test_cash_for_someone_else_is_never_held_by_lynkomni(self):
        text = " ".join(REG["rules"])
        self.assertIn("LynkOmni never holds", text)
        self.assertTrue(any(p["whose_cash"] == "held_for_seller" for p in REG["points"]))

    def test_places_where_cash_does_not_apply_say_why(self):
        ids = {n["id"] for n in REG["not_applicable"]}
        self.assertLessEqual({"remote_payment", "agent_point_services", "lynkomni_plans"}, ids)
        for n in REG["not_applicable"]: self.assertGreater(len(n["why"]), 20, n["id"])


if __name__ == "__main__": unittest.main()
