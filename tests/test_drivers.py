"""LynkDriver (BIZZ & DEVICE): one pack for every hardware kind, installed online or offline, prompted when hardware needs it,
updates strongly enforced (security now, required in 3 days, normal in 7), and overdue hardware hands over to a virtual device
so a sale is never blocked. The TypeScript port agrees with the vectors."""
import json, os, subprocess, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import drivers as D

ADDR = json.load(open(os.path.join(ROOT, "catalog", "addresses.v1.json"), encoding="utf-8"))


class Drivers(unittest.TestCase):
    def test_register_and_vectors(self):
        self.assertEqual(D.validate(), [])
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "drivers_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_one_pack_named_lynkdriver_in_both_places(self):
        self.assertEqual(D.PACK["name"], "LynkDriver")
        self.assertIn(D.REGISTER["where"]["online"], ADDR["app_paths"]); self.assertIn(D.REGISTER["where"]["offline"], ADDR["website_paths"])

    def test_update_deadlines(self):
        self.assertEqual(D.DAYS, {"security": 0, "required": 3, "normal": 7})
        sec = next(r for r in D.releases() if r["kind"] == "security")
        before = max(r["version"] for r in D.releases() if r["released_at"] < sec["released_at"])
        self.assertEqual(D.update_state(before, sec["released_at"])["state"], "overdue")          # a security update is required now
        t0 = D.PACK["released_at"]
        self.assertEqual(D.update_state("1.3.2", t0 + 7 * D.DAY - 1)["state"], "available")
        self.assertEqual(D.update_state("1.3.2", t0 + 7 * D.DAY)["state"], "overdue")

    def test_overdue_hardware_never_blocks_a_sale(self):
        st = D.update_state("1.0.0", D.PACK["released_at"])
        self.assertEqual(st["hardware"], "virtual")
        for k in ("receipt_printer", "barcode_scanner", "cash_drawer", "customer_display", "scale", "card_reader"):
            self.assertIsNotNone(D.fallback(k), k)
        self.assertIsNone(D.fallback("fiscal_device"))                                              # certified by the authority: no stand-in
        self.assertEqual(D.KINDS["card_reader"]["certified_by"], "payment_provider")

    def test_install_prompt(self):
        self.assertEqual(D.needs_install(["receipt_printer", "unknown"], None), ["receipt_printer"])
        self.assertEqual(D.needs_install(["receipt_printer"], "1.4.0"), [])


if __name__ == "__main__":
    unittest.main()
