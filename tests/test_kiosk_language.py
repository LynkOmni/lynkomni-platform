"""Owner report 2026-11-27 ("LynkKiosk has its languages mixed up"): once the kiosk knows who is at the door, the whole screen
speaks that person's language, title and buttons included, never half the kiosk's language and half theirs; before that,
and for tickets and answers, everything is in the kiosk's own language."""
import os, unittest
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIOSK = "file://" + os.path.join(ROOT, "web", "emulators", "dist", "lynkomni-lynk-kiosk.html")


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class KioskLanguage(unittest.TestCase):
    def door(self, b, kiosk_lang, pin):
        pg = b.new_page(viewport={"width": 1400, "height": 1000})
        pg.goto(KIOSK); pg.wait_for_selector("html[data-ready]")
        pg.locator("select").nth(1).select_option(kiosk_lang, force=True); pg.wait_for_timeout(200)
        pg.click('#screen [data-act="go:door"]')
        for d in pin:
            pg.click(f'#screen [data-act="at:digit:{d}"]')
        pg.wait_for_timeout(200)
        text = pg.inner_text("#screen")
        langs = set(pg.evaluate("[...document.querySelectorAll('#screen [lang]')].map(e => e.lang)"))
        pg.close()
        return text, langs

    def test_the_person_sees_one_language(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            for pin, own in (("482913", "fr"), ("739154", "en")):                # sample Aline speaks French, sample Eric English
                for kiosk in ("en", "fr", "sw"):
                    with self.subTest(person=own, kiosk=kiosk):
                        text, langs = self.door(b, kiosk, pin)
                        same, _ = self.door(b, own, pin)
                        self.assertEqual(text, same, "the screen is wholly in the person's own language")
                        self.assertEqual(langs, {own}, "every part of the screen says the person's language")
