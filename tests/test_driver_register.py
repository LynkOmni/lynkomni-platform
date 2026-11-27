"""DRIVER UPDATE (blueprint 95, owner 27 November 2026), the hardware register: one hardware list for the whole ecosystem (D1),
open standards for every kind (D2), what can be sent instead (D19), the ladder (D18), roles not devices (D43), speed targets
(D41) and the promise to older hardware (D55)."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import drivers as D  # noqa: E402
from core import emulators as E  # noqa: E402


class DriverRegister(unittest.TestCase):
    def test_the_register_is_valid(self):
        self.assertEqual(D.validate(), [])

    def test_every_emulator_names_hardware_the_driver_knows(self):
        with open(os.path.join(ROOT, "catalog", "emulators.v1.json"), encoding="utf-8") as f:
            ems = json.load(f)["emulators"]
        for e in ems:
            for h in e["hardware"]:
                with self.subTest(emulator=e["id"], hardware=h):
                    self.assertIn(h, D.REGISTER["roles"], "a role in catalog/drivers.v1.json")
                    self.assertIn(D.role_kind(h), D.KINDS)

    def test_emulator_ways_come_from_the_one_list(self):
        self.assertEqual(set(E.HARDWARE_WAYS), set(D.REGISTER["roles"]))

    def test_the_hardware_of_sections_88_to_91_is_known(self):
        for k in ("video_recorder", "gate_controller", "relay_board", "tag_reader", "plate_camera", "weighbridge", "pump_controller",
                  "tank_gauge", "ev_charger", "led_sign", "alarm_panel", "backup_power", "intercom", "turnstile", "ballot_scanner",
                  "security_key", "cash_acceptor"):
            self.assertIn(k, D.KINDS)

    def test_the_ladder_runs_in_its_fixed_order(self):
        step, seen = "hardware", []
        while step:
            seen.append(step)
            step = D.ladder_next(step)
        self.assertEqual(seen, ["hardware", "same_kind", "nearby_device", "stand_in", "by_hand", "file_or_paper"])

    def test_money_law_and_identity_are_never_a_file(self):
        for k in ("ballot_scanner", "security_key", "card_reader", "fiscal_device"):
            self.assertIn(D.KINDS[k]["file_instead"], (None, "never"), k)

    def test_speed_targets(self):
        t = D.REGISTER["speed_targets_ms"]
        self.assertEqual(t, {"find_first_device": 2000, "pair": 5000, "scan_to_screen": 100, "print_after_confirmed": 500,
                             "stand_in_switch": 1000, "reconnect": 3000, "keeper_takeover": 10000, "app_ready": 2000})

    def test_older_hardware_keeps_working(self):
        f = D.REGISTER["future"]
        self.assertTrue(f["never_dropped_while_used"] and f["new_kinds_by_register_only"])
        self.assertGreaterEqual(f["retire_notice_months"], 12)

    def test_the_check_catches_a_role_with_an_unknown_kind(self):
        D.REGISTER["roles"]["x_role"] = {"kind": "no_such_kind", "ways": []}
        try:
            self.assertTrue(any("x_role" in p for p in D.validate()))
        finally:
            del D.REGISTER["roles"]["x_role"]


if __name__ == "__main__":
    unittest.main()
