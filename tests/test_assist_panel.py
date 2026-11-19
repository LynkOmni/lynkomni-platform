"""LynkAssist in the Emulator Panel (CONNECT UPDATE 71.9, build section 3A): every action is in the register, connecting and
disconnecting wait for the manager's Confirm and can be undone, practice mode never counts against the plan, a cashier is refused,
and "Why?" explains a device in plain words."""
import os, unittest

from contract.tools.validate_contract import uuid4
from services import assist_register as AR
from services.assist_panel import PANEL_ACTIONS, PanelAssist
from dv.panel_device import PanelDevice
from dv.box import LynkDVBox
from datetime import datetime, timezone
from services.platform import Platform

T0 = 1_800_000_000.0
PHONE = {"touch": True, "short_side": 390, "printer": False, "scanner": "camera", "drawer": False}


class PanelAssistTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None)
        self.p = Platform(); self.e = self.p.panel; self.m = uuid4(); self.boss = uuid4(); self.branch = uuid4()
        self.e.add_role(self.m, self.boss, "owner")
        self.phone = self.e.add_device(self.m, self.branch, "Counter 2", "LynkMobile", "android", PHONE, now=T0)
        self.spare = self.e.add_device(self.m, self.branch, "Spare", "LynkMobile", "android", PHONE, now=T0)
        self.a = PanelAssist(self.p, self.m, self.boss, self.boss)

    def test_every_action_is_in_the_register_and_built(self):
        for a in PANEL_ACTIONS:
            self.assertIn(a, AR.ACTIONS); self.assertEqual((AR.ACTIONS[a]["status"], AR.ACTIONS[a]["build_section"]), ("built", "3A"), a)
            if a != "panel_explain_device": self.assertEqual(AR.ACTIONS[a]["class"], "B", a)       # a person always confirms

    def test_connect_waits_for_confirm_and_undo_disconnects(self):
        self.assertEqual(self.a.do("dev", self.boss, "manager", "panel_connect_device", device=self.phone, emulator="pos.merchant_phone", now=T0)["state"], "not_done")
        r = self.a.do("dev", self.boss, "manager", "panel_connect_device", confirmed=True, device=self.phone, emulator="pos.merchant_phone", now=T0)
        self.assertEqual(r["state"], "done")
        self.assertTrue(self.a.undo(r["entry"], now=T0 + 10))
        self.assertEqual(self.e.device_view(self.phone, "pos.merchant_phone")["screen"], "disconnected")
        self.assertEqual(self.a.do("dev", self.boss, "cashier", "panel_disconnect_device", confirmed=True, device=self.phone, now=T0)["needs"], "refused")

    def test_practice_mode_never_counts_against_the_plan(self):
        self.a.do("dev", self.boss, "manager", "panel_connect_device", confirmed=True, device=self.phone, emulator="pos.merchant_phone", now=T0)
        r = self.a.do("dev", self.boss, "manager", "panel_practice_mode", confirmed=True, device=self.spare, emulator="pos.merchant_phone", now=T0)
        self.assertEqual(r["state"], "done")
        self.assertEqual(self.e.usage(self.m, self.boss)["lynkpos"]["in_use"], 1)                # LynkPOS Free: 1 device, the practice one is free

    def test_why_explains_a_device_in_plain_words(self):
        self.e.connect(self.m, [self.phone], "pos.merchant_phone", self.boss)
        b = LynkDVBox(self.m, self.branch, self.phone, uuid4(), "manager", now=datetime.fromtimestamp(T0, timezone.utc))
        PanelDevice(b).health(True, 0, battery_pct=5, printer="out_of_paper"); self.e.ingest(self.m, b.log[-1], now=T0 + 5)
        r = self.a.do("dev", self.boss, "staff", "panel_explain_device", device=self.phone, now=T0 + 6)
        self.assertEqual(r["state"], "done")
        self.assertEqual(self.a.explain(self.phone)["reasons"], ["printer", "battery"])
        self.a.do("dev", self.boss, "manager", "panel_mark_lost", confirmed=True, device=self.phone, now=T0 + 7)
        self.assertIn("lost", self.a.explain(self.phone)["reasons"])


if __name__ == "__main__":
    unittest.main()
