"""Size follows how far people stand, never how they press (owner report 2026-11-27).

The kiosk's buttons-only version used the TV setup, so its words and keys were 1.5 times bigger than the touch version of
the same kiosk. A device used at arm's length keeps the same type size whether it is used by touch or by buttons."""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SameSize(unittest.TestCase):
    def test_touch_and_buttons_versions_of_one_device_share_a_size(self):
        with open(os.path.join(ROOT, "catalog", "devices.v1.json"), encoding="utf-8") as f:
            d = json.load(f)
        cls = {k: v["class"] for k, v in d["interfaces"].items()}
        # the one exception: a ring scanner with buttons is a different, larger body than the touch ring on a finger
        different_body = {"ring-scanner"}
        for dev in d["devices"]:
            if dev.get("touch") and dev.get("non_touch") and dev["id"] not in different_body:
                with self.subTest(device=dev["id"]):
                    self.assertEqual(cls[dev["touch"]], cls[dev["non_touch"]], "the same type size by touch and by buttons")


if __name__ == "__main__":
    unittest.main()
