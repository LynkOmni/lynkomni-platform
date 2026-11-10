"""Text, USSD and voice channels (BIZZ & DEVICE 48.17, interface phone.text): one engine, every page fits a USSD screen, a sale
needs the PIN, the commands are numbers so they work in every language, and the TypeScript port agrees with the vectors."""
import json, os, subprocess, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import channels as C, interfaces as I

EN = json.load(open(os.path.join(ROOT, "web", "pos", "strings.en.json"), encoding="utf-8"))
CTX = {"products": [["Cooking oil 1 L", "12,500", "2"], ["Sugar 1 kg", "1,400", "6"], ["Rice 1 kg", "1,500", "24"], ["Bread", "1,000", "12"], ["Soap", "500", "18"]],
       "today": [14, "42,000"], "receipt": "BP-14", "pin_ok": lambda t: t == "1234"}


class Channels(unittest.TestCase):
    def test_vectors_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "channels_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_every_page_fits_one_ussd_screen(self):
        for scr in C.SCREENS:
            st = {"screen": scr, "prod": 0, "qty": 999}
            text = C.render(C.page(st, CTX), EN)
            self.assertLessEqual(len(text), C.USSD_MAX, f"{scr}: {len(text)} characters")

    def test_a_sale_needs_the_pin_and_a_wrong_pin_records_nothing(self):
        st = C.start()
        for x in ("1", "3", "2"): st, ends, action = C.step(st, x, CTX); self.assertIsNone(action)
        _, ends, action = C.step(st, "0000", CTX); self.assertIsNone(action); self.assertFalse(ends)
        _, ends, action = C.step(st, "1234", CTX); self.assertEqual(action, {"sale": 2, "qty_milli": 2000}); self.assertTrue(ends)

    def test_commands_are_numbers_and_no_partner_request_is_offered(self):
        self.assertEqual(C.parse_sms("1 3 2 1234")["command"], "sell"); self.assertIsNone(C.parse_sms("SELL 3 2 1234"))
        self.assertNotIn("agent", C.MENU)
        self.assertIn("ch_help", EN); self.assertIn("1", EN["ch_help"])

    def test_the_basic_phone_uses_this_channel(self):
        self.assertEqual(I.DEVICES["basic-phone"]["non_touch"], "phone.text")
        self.assertEqual(I.choose({"registered": {"device": "basic-phone", "version": "non_touch"}})["interface"], "phone.text")


if __name__ == "__main__":
    unittest.main()
