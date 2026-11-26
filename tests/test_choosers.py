"""Every choice is LynkOmni's own drop-down, and every device says how it is used (owner, 2026-11-26).

In a real browser, on every emulator page: no select shows the phone's built-in picker (each one sits hidden under LynkOmni's
button and list, ts/src/chooser.ts), choosing from the list sets the select's value, and the panel either offers the touch
screen or buttons choice or says in a plain line why there is none (ts/src/devicemode.ts deviceChoiceHtml, anyDeviceHtml).
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
NATIVE = "() => [...document.querySelectorAll('select:not([data-native])')].filter((s) => !s.multiple && !s.classList.contains('lo-src')).length"


@unittest.skipIf(sync_playwright is None, "needs the browser (CI layout job)")
class Choosers(unittest.TestCase):
    def test_every_page_uses_lynkomnis_drop_down_and_says_how_the_device_is_used(self):
        self.assertGreaterEqual(len(PAGES), 21)
        with sync_playwright() as p:
            b = p.chromium.launch()
            for name in PAGES:
                with self.subTest(page=name):
                    pg = b.new_page(viewport={"width": 390, "height": 844})
                    pg.set_default_timeout(8000)
                    errors = []
                    pg.on("pageerror", lambda e, errors=errors: errors.append(str(e)))
                    pg.goto("file://" + os.path.join(DIST, f"lynkomni-{name}.html"))
                    pg.wait_for_timeout(300)
                    self.assertEqual(errors, [], "the page runs without errors")
                    self.assertEqual(pg.evaluate(NATIVE), 0, "no select shows the phone's built-in picker")
                    self.assertGreater(pg.locator('select[data-ctl="version"], .vonly').count(), 0, "the panel says how the device is used")
                    pg.close()
            b.close()

    def test_the_kiosk_checker_list_opens_and_chooses(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 390, "height": 844}, color_scheme="dark")
            pg.set_default_timeout(8000)
            pg.goto("file://" + os.path.join(DIST, "lynkomni-lynk-kiosk.html"))
            if pg.locator('[data-act="dsh:localeok"]').count():
                pg.click('[data-act="dsh:localeok"]')
            pg.click('#stateButtons [data-state="door-idcn"]')
            pg.click('.lo-sel:has(#checker) .lo-selbtn')
            names = pg.locator(".lo-pop .lo-opt").all_inner_texts()
            self.assertIn("Aline", names)
            self.assertIn("Grace", names)
            pg.locator(".lo-pop .lo-opt", has_text="Grace").click()
            self.assertEqual(pg.eval_on_selector("#checker", "s => s.value"), "Grace")
            self.assertEqual(pg.locator(".lo-pop").count(), 0, "the list closes after a choice")
            b.close()


if __name__ == "__main__":
    unittest.main()
