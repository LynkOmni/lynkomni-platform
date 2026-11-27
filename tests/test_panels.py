"""Every emulator's panel has every control, or a plain line saying why not (owner, 2026-11-26).

The owner's rule: touch screen or buttons only, online or offline, language, country, light or dark and turning the
screen apply to every emulator, except where the device truly cannot have one; then its panel says so in a plain line
(ts/src/devicemode.ts deviceChoiceHtml, ts/src/devicenote.ts anyDeviceHtml and turnFixedHtml). In a real browser this
opens every emulator page and checks each control is there, and that a turned device and a touch display really work.
Runs in the browser (CI layout job)."""
import glob
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "web", "emulators", "dist")
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

PAGES = sorted(os.path.basename(p)[len("lynkomni-"):-len(".html")] for p in glob.glob(os.path.join(DIST, "lynkomni-*.html")))

# Each control and the ways a page may show it: the shared panel's data-ctl, a page's own control id, or the plain line.
CONTROLS = {
    "online": '[data-ctl="online"], #cOnline, #cLink, #bOnline',
    "language": '[data-ctl="lang"], #cLang',
    "country": '[data-ctl="country"], #cCountry',
    "light or dark": '[data-ctl="dark"], #cDark',
    "turning": '[data-ctl="turn"], #cSize, [data-ctl="turn-fixed"]',
    "touch or buttons": '[data-ctl="version"], [data-ctl="version-only"], .vonly',
    "hardware": '[data-ctl="hardware"], [data-ctl="hardware-none"]',
}
TURNS = ["customer-display", "kitchen-screen", "lynk-cdisplay", "lynk-dscreen", "lynk-kiosk", "files-signing"]


def open_page(b, name, width=1280):
    pg = b.new_page(viewport={"width": width, "height": 900})
    pg.set_default_timeout(8000)
    errors = []
    pg.on("pageerror", lambda e, errors=errors: errors.append(str(e)))
    pg.goto("file://" + os.path.join(DIST, f"lynkomni-{name}.html"))
    pg.wait_for_timeout(300)
    return pg, errors


@unittest.skipIf(sync_playwright is None, "needs the browser (CI layout job)")
class Panels(unittest.TestCase):
    def test_every_page_has_every_control_or_its_plain_line(self):
        self.assertGreaterEqual(len(PAGES), 21)
        with sync_playwright() as p:
            b = p.chromium.launch()
            for name in PAGES:
                pg, errors = open_page(b, name)
                for what, sel in CONTROLS.items():
                    with self.subTest(page=name, control=what):
                        self.assertGreater(pg.locator(sel).count(), 0, f"{name} has no {what} control and no line saying why")
                for line in pg.locator(".vonly, [data-ctl='hardware'] .plabel").all_text_contents():
                    with self.subTest(page=name, line=line):     # a plain line is words, never a raw word name such as version_only_web
                        self.assertNotRegex(line.strip(), r"^[a-z][a-z0-9_]*$")
                self.assertEqual(errors, [], f"{name} runs without errors")
                pg.close()
            b.close()

    def test_breaking_a_piece_of_hardware_shows_what_takes_over(self):
        """DRIVER UPDATE D12, D13, D18: the tester breaks or unplugs a piece of hardware and the device says, in words, what is used
        instead; putting it back clears the line. Nothing stops working and no error is raised."""
        with sync_playwright() as p:
            b = p.chromium.launch()
            tried = 0
            for name in PAGES:
                pg, errors = open_page(b, name)
                sel = pg.locator('[data-ctl="hardware"] select').first
                if not sel.count():
                    pg.close(); continue
                tried += 1
                with self.subTest(page=name):
                    sel.select_option("unplugged")
                    pg.wait_for_timeout(150)
                    line = pg.locator(".hwd-line").first
                    if line.count():                              # a page waiting on its PIN shows the line after sign-in
                        self.assertNotRegex(line.inner_text(), r"\b[a-z]+_[a-z_]+\b", "words, never raw word names")
                    pg.locator('[data-ctl="hardware"] select').first.select_option("connected")
                    pg.wait_for_timeout(150)
                    self.assertEqual(pg.locator(".hwd-line").count(), 0)
                    self.assertEqual(errors, [])
                pg.close()
            self.assertGreaterEqual(tried, 6)
            b.close()

    def test_a_device_turned_sideways_takes_its_other_shape(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            for name in TURNS:
                with self.subTest(page=name):
                    pg, errors = open_page(b, name)
                    upright = pg.evaluate("() => [(document.querySelector('[data-turn] .cdframe') || document.querySelector('[data-turn]')).getBoundingClientRect().width, document.querySelector('[data-turn]').dataset.turn]")
                    self.assertEqual(upright[1], "upright")
                    pg.select_option('[data-ctl="turn"]', "sideways")
                    pg.wait_for_timeout(150)
                    turned = pg.evaluate("() => [(document.querySelector('[data-turn] .cdframe') || document.querySelector('[data-turn]')).getBoundingClientRect().width, document.querySelector('[data-turn]').dataset.turn, document.querySelector('#screen, .cdscreen').dataset.orientation || '']")
                    self.assertEqual(turned[1], "sideways")
                    self.assertNotEqual(round(turned[0]), round(upright[0]), "the body changes shape")
                    self.assertEqual(errors, [])
                    pg.close()
            b.close()

    def test_the_two_displays_take_taps_in_touch_mode(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            for name in ("lynk-dscreen", "lynk-cdisplay"):
                with self.subTest(page=name):
                    pg, errors = open_page(b, name)
                    values = pg.eval_on_selector('select[data-ctl="version"]', "s => [...s.options].map((o) => o.value)")
                    self.assertTrue(any("touch" in v and "non" not in v for v in values), values)
                    pg.select_option('select[data-ctl="version"]', next(v for v in values if "touch" in v and "non" not in v))
                    pg.wait_for_timeout(150)
                    self.assertEqual(pg.evaluate("() => document.querySelector('[data-interface]')?.dataset.interface"), "tablet.touch")
                    self.assertEqual(errors, [])
                    pg.close()
            b.close()


if __name__ == "__main__":
    unittest.main()
