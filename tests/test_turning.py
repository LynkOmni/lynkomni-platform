"""TURN UPDATE (master blueprint 76.2 and 76.6, section 4 step B2b): turning the device in the middle of a task changes the layout
only. The basket, the screen, typed text and the event log stay exactly as they were; nothing is repeated or cancelled; turning
back gives the same screen again. Runs in the browser (CI layout job, part 3)."""
import os, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "web", "emulators", "dist")
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


def signed_in(pg):
    pg.goto("file://" + os.path.join(DIST, "lynkomni-merchant-phone.html"))
    pg.fill("#phoneIn", "0788123456"); pg.click('[data-act="sendcode"]')
    pg.fill("#codeIn", "123456"); pg.click('[data-act="verify"]')
    pg.click('[data-act="business:0"]'); pg.wait_for_selector('[data-act="start"]'); pg.click('[data-act="start"]')
    pg.click('[data-act="localeok"]'); pg.evaluate("__go('home')")


@unittest.skipIf(sync_playwright is None, "needs the browser (CI layout job)")
class Turning(unittest.TestCase):
    def test_a_turn_in_the_middle_of_a_sale_keeps_everything(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="reduce")
            signed_in(pg)
            pg.click('[data-act="tab:sell"]')
            tiles = pg.locator('#display [data-act^="add:"]')
            tiles.nth(0).click(); tiles.nth(1).click(); tiles.nth(1).click()
            def snapshot():
                return {"screen": pg.eval_on_selector(".screen", "e => e.dataset.screen"),
                        "basket": pg.inner_text("#display .grid"),
                        "events": pg.locator("#log li").count()}
            before = snapshot()
            self.assertEqual(pg.eval_on_selector("#display", "e => e.dataset.nav"), "bottom_bar")
            pg.select_option("#cSize", "side")
            self.assertEqual(pg.eval_on_selector("#display", "e => [e.dataset.nav, e.dataset.orientation]"), ["side_rail", "sideways"])
            self.assertEqual(snapshot(), before, "turning sideways keeps the screen, the basket and the log, and repeats nothing")
            self.assertGreater(pg.locator("#display .rail button").count(), 0, "the side rail replaces the bottom tabs")
            pg.select_option("#cSize", "phone")
            self.assertEqual(snapshot(), before, "turning back gives the same screen again")
            self.assertEqual(pg.eval_on_selector("#display", "e => e.dataset.nav"), "bottom_bar")
            b.close()

    def test_typed_text_survives_a_turn(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="reduce")
            signed_in(pg)
            pg.click('[data-act="tab:sell"]')
            pg.fill("#searchIn", "sug")
            pg.select_option("#cSize", "side")
            self.assertEqual(pg.input_value("#searchIn"), "sug", "typed text is kept when the phone turns")
            pg.select_option("#cSize", "phone")
            self.assertEqual(pg.input_value("#searchIn"), "sug")
            b.close()

    def test_a_payment_keeps_its_step_and_its_calm_header_when_turned(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="reduce")
            signed_in(pg)
            pg.evaluate("__go('pay')")
            pg.select_option("#cSize", "side")
            self.assertEqual(pg.eval_on_selector(".screen", "e => e.dataset.screen"), "pay")
            self.assertEqual(pg.locator(".top.focus").count(), 1, "the focus header stays during a payment")
            self.assertEqual(pg.locator("#display .tabbar, #display .rail").count(), 0, "no tabs or rail during a payment, either way round")
            b.close()


if __name__ == "__main__":
    unittest.main()

class BothDirections(unittest.TestCase):
    """TURN UPDATE 76.8: every emulator of a device a person can turn offers it upright and sideways (its size choice, id cSize),
    so the fit guard tries every screen both ways. Fixed devices that may be held to one direction (catalog/devices.v1.json lockable)
    and devices that cannot turn (a card, a button phone, a computer window) are not listed."""
    TURNABLE = {"merchant-phone": ('value="phone"', 'value="side"'), "account-site": ('value="phone"', 'value="phone_side"'),
                "counter-tablet": ('value="sideways"', 'value="upright"'), "rider-phone": ('"turn"',), "track-page": ('"turn"',),
                "queue-page": ('"turn"',), "survey-page": ('"turn"',), "stock-scanner": ('"turn"',)}

    def test_every_turnable_emulator_offers_both_directions(self):
        for emu, marks in self.TURNABLE.items():
            page = open(os.path.join(DIST, f"lynkomni-{emu}.html"), encoding="utf-8").read()
            for m in marks:
                self.assertIn(m, page, emu)
            self.assertIn('cSize', page, f"{emu}: the fit guard walks the size choice")
