"""Ads on screens (ADS UPDATE, master blueprint 79; section 4 row 79.10): the device-side rules agree in Python and TypeScript, the
till's idle and after-sale slots and the receipt line are on the POS emulators, LynkStat Free carries one card, and Business settings
hold the hosting switch, the category blocks, blocked advertisers and the earnings card. An ad is always labelled with Why and Report,
never on a blocked screen, never on a paid plan and never before the country's legal sign-off."""
import os, subprocess, sys, unittest

from services import ads as A

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "web", "emulators", "dist")


def page(name):
    return open(os.path.join(DIST, f"lynkomni-{name}.html"), encoding="utf-8").read()


class AdScreens(unittest.TestCase):
    def test_vectors_and_typescript_data_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ads_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_the_rule_never_shows_an_ad_where_it_must_not(self):
        for screen in ("payment", "cash_count", "void", "refund", "settings", "chat_thread"):
            self.assertFalse(A.may_show("pos_idle", screen=screen, country_on=True), screen)
        self.assertFalse(A.may_show("pos_idle", country_on=False), "off until the country's legal sign-off")
        self.assertFalse(A.may_show("pos_idle", country_on=True, ad_free=True), "a paid plan shows none")
        self.assertFalse(A.may_show("receipt_footer", screen="receipt", country_on=True), "a customer-facing place only once the shop hosts it")
        self.assertTrue(A.may_show("receipt_footer", screen="receipt", country_on=True, hosting=True))
        self.assertFalse(A.may_show("dashboard_card", country_on=True, workspace="household"))
        self.assertFalse(A.counts(49, 5000)); self.assertTrue(A.counts(50, 1000))

    def test_every_screen_place_is_drawn_by_the_shared_slot(self):
        for emu, places in (("pos-terminal", ("pos_idle", "pos_after_sale", "receipt_footer")), ("counter-tablet", ("pos_idle", "pos_after_sale", "receipt_footer")),
                            ("owner-web", ("dashboard_card",))):
            html = page(emu)
            self.assertIn("ad-slot", html, emu)
            for p in places:
                self.assertIn(f'"{p}"', html, f"{emu}: {p}")
            for k in ("ad_sponsored", "ad_why", "ad_report"):
                self.assertIn(f'"{k}"', html, f"{emu} carries the word {k}")
        mp = page("merchant-phone")
        for item in ("ads_host", "ads_block_age", "ads_block_regulated", "ads_blocked", "ads_earnings"):
            self.assertIn(item, mp)


if __name__ == "__main__":
    unittest.main()
