"""Staff PIN with a duress PIN on every shared staff device (owner rule 2026-11-24, catalog/emulators.v1.json staff_lock,
catalog/universal.v1.json everywhere staff_pin).

Every built emulator whose user is "needed" or "optional" signs each person in with their own PIN through the shared device kit
(ts/src/devicekit.ts StaffLock, StaffGate), has a sample duress PIN and sends DuressSignalled; basic phones take a duress PIN at
sign-in and at a sale, with the same page as a normal one."""
import json
import os
import re
import unittest

from core import channels as CH
from identity import basic_phone as BP
from identity import device_access as DA

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = json.load(open(os.path.join(ROOT, "catalog", "emulators.v1.json"), encoding="utf-8"))


def source(folder):
    with open(os.path.join(ROOT, "web", "emulators", folder, "app.ts"), encoding="utf-8") as f:
        return f.read()


class StaffLockEverywhere(unittest.TestCase):
    def test_the_rule_is_written_down(self):
        self.assertIn("duress", REG["staff_lock"])
        universal = json.load(open(os.path.join(ROOT, "catalog", "universal.v1.json"), encoding="utf-8"))
        self.assertIn("staff_pin", [r["id"] for r in universal["everywhere"]])

    def test_every_shared_staff_emulator_has_the_staff_lock_with_a_duress_pin(self):
        folders = {e["built_in"] for e in REG["emulators"] if e["built_in"] and not e["customer_facing"] and e["user"] in ("needed", "optional")}
        self.assertTrue({"pos-terminal", "counter-tablet", "merchant-phone", "kitchen-screen", "rider-phone", "stock-scanner", "bet-counter"} <= folders)
        for folder in sorted(folders):
            with self.subTest(folder):
                src = source(folder)
                self.assertIn("new StaffLock(", src, "each person signs in with their own PIN (ts/src/devicekit.ts)")
                self.assertRegex(src, r'duress: "\d{4,8}"', "a sample duress PIN")
                self.assertTrue("DuressSignalled" in src or "new StaffGate(" in src, "the duress PIN sends the silent alert")

    def test_every_screen_opened_with_a_staff_pin_can_be_locked_at_once(self):
        """Owner, 2026-11-25: every screen a person opened with their PIN shows who is signed in with Lock beside the name
        (ts/src/devicekit.ts staffWhoRow, act gate:lock), not only the two-minute idle lock or a Lock buried in a menu."""
        folders = {e["built_in"] for e in REG["emulators"] if e["built_in"] and not e["customer_facing"] and e["user"] in ("needed", "optional")}
        for folder in sorted(folders):
            with self.subTest(folder):
                src = source(folder)
                self.assertTrue("staffWhoRow(" in src or "GATE.whoRow()" in src, "the who row with Lock is drawn")
                self.assertTrue('"gate:lock"' in src or "new StaffGate(" in src or '"gate": if (v === "lock")' in src, "Lock locks at once")

    def test_customer_screens_have_no_staff_lock(self):
        for e in REG["emulators"]:
            if e["built_in"] and e["customer_facing"] and e["user"] == "none" and e["built_in"] not in {x["built_in"] for x in REG["emulators"] if not x["customer_facing"]}:
                with self.subTest(e["id"]):
                    self.assertNotIn("new StaffGate(", source(e["built_in"]))

    def test_the_new_roles_are_managed_and_limited(self):
        for role in ("rider", "kitchen_staff"):
            self.assertIn(role, DA.ROLES)
            self.assertIn(role, DA.CAN_MANAGE["owner"])
            self.assertIn(role, DA.CAN_MANAGE["manager"])
            self.assertEqual(DA.OFFLINE_LIMITS[role], {"void_minor": 0, "refund_minor": 0, "discount_bps": 0})


class BasicPhoneDuress(unittest.TestCase):
    CTX = {"products": [["Rice", "1,500", "20"]], "today": [0, "0"]}

    def sell(self, pin):
        ctx = dict(self.CTX, pin_ok=lambda t: t == "1234", pin_duress=lambda t: t == "8642")
        st = CH.start()
        for x in ("1", "1", "2"):
            st, _, _ = CH.step(st, x, ctx)
        return CH.step(st, pin, ctx)

    def test_a_duress_pin_sells_with_the_same_page_and_raises_the_alert(self):
        normal, duress = self.sell("1234"), self.sell("8642")
        self.assertEqual(CH.page(normal[0], self.CTX), CH.page(duress[0], self.CTX))
        self.assertNotIn("duress", normal[2])
        self.assertTrue(duress[2]["duress"])
        self.assertIsNone(self.sell("9999")[2])

    def test_a_duress_sign_in_shows_the_same_home_without_messages(self):
        ctx = {"age": 18, "lines": [["n1", "New sign-in"]], "pin_check": lambda t: "ok" if t == "4719" else "duress" if t == "8642" else ("wrong", 9),
               "username_check": lambda u: None, "taken": lambda u: False}
        st, _, action = BP.step(BP.step(BP.start(), "1", ctx)[0], "8642", ctx)
        self.assertEqual(st["screen"], "home")
        self.assertEqual(action, {"sign_in": True, "duress": True})
        self.assertEqual(BP.page(st, ctx)[1], ("bp_messages", {"n": 1, "count": 0}))
        ok, _, _ = BP.step(BP.step(BP.start(), "1", ctx)[0], "4719", ctx)
        self.assertEqual(BP.page(ok, ctx)[1], ("bp_messages", {"n": 1, "count": 1}))


if __name__ == "__main__":
    unittest.main()
