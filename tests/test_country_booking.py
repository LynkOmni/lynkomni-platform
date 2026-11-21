"""LynkBooking's settings in every country pack (BOOKING UPDATE, master blueprint 64; section 4 step E4a): tools/country_booking.py.
Every value starts unknown and unconfirmed until the lawyer and accountant confirm it (ledger later booking_country_rules); the
pack generator keeps the section."""
import json, os, subprocess, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS = os.path.join(ROOT, "contract", "country-packs")


class CountryBooking(unittest.TestCase):
    def test_every_pack_has_its_booking_settings_and_the_packs_are_current(self):
        for tool in ("country_booking.py", "country_packs.py"):
            r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", tool), "--check"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_nothing_is_invented(self):
        for name in os.listdir(PACKS):
            b = json.load(open(os.path.join(PACKS, name), encoding="utf-8"))["booking"]
            if not b["confirmed"]:
                self.assertEqual(b["commission_fixed_minor"], {"cap": None, "ticket": None, "guest": None}, name)
                self.assertTrue(all(b[k] is None for k in ("tourist_tax", "travel_seller_licence", "deposit_max_bp", "cancel_notice_hours_min")), name)
        ledger = json.load(open(os.path.join(ROOT, "providers", "registry.v1.json"), encoding="utf-8"))
        self.assertIn("booking_country_rules", [x["id"] for x in ledger["later"]])


if __name__ == "__main__":
    unittest.main()
