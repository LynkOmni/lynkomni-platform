"""The device's own on-screen keyboard (owner, 2026-11-27: every emulator matches its real device exactly).

Touching a typing field on a touch-screen emulator opens the keyboard drawn inside that device's screen, never the tester's own
phone keyboard: the field asks for no system keyboard (inputmode none), the keys type into it, the field stays visible above the
keys, the keyboard follows the field's kind and the language picked, and Done closes it. A computer keeps its own keyboard.
The rules themselves are proved the same in Python and TypeScript. Browser parts run in the CI layout job."""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "web", "emulators", "dist")
sys.path.insert(0, ROOT)
from core import keyboards as KB  # noqa: E402
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

SET_LANG = "l => { const s = document.querySelector('[data-ctl=lang]'); s.value = l; s.dispatchEvent(new Event('change', { bubbles: true })); }"


def page(b, name):
    pg = b.new_page(viewport={"width": 400, "height": 900}, has_touch=True)
    pg.set_default_timeout(8000)
    errors = []
    pg.on("pageerror", lambda e, errors=errors: errors.append(str(e)))
    pg.goto("file://" + os.path.join(DIST, f"lynkomni-{name}.html"))
    pg.wait_for_timeout(400)
    return pg, errors


def to_name_box(pg):
    for d in "4826":                                                      # the staff member's own PIN opens the tablet (sample cashier)
        pg.locator(f'#screen [data-act="pin:{d}"]').click()
    pg.wait_for_timeout(200)
    pg.locator('#screen [data-act="fs:start"]').click(); pg.wait_for_timeout(200)
    pg.locator('#screen [data-in="fs:read"]').first.check(); pg.wait_for_timeout(200)
    pg.locator('#screen [data-act="fs:tosign"]').click(); pg.wait_for_timeout(200)
    pg.locator("#fsName").click(); pg.wait_for_timeout(300)


class Rules(unittest.TestCase):
    def test_register_and_vectors(self):
        self.assertEqual(KB.validate(), [])
        self.assertEqual(len(KB.REGISTER["languages"]), 38)
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "keyboards_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_every_page_language_has_a_keyboard(self):
        import json
        with open(os.path.join(ROOT, "design", "fonts", "scripts.v1.json"), encoding="utf-8") as f:
            langs = list(json.load(f)["languages"])
        for lang in langs:
            self.assertIn(lang, KB.REGISTER["languages"], f"{lang} has no keyboard")


@unittest.skipIf(sync_playwright is None, "needs the browser (CI layout job)")
class Keyboard(unittest.TestCase):
    def test_the_signing_tablet_types_a_name_with_its_own_keyboard(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg, errors = page(b, "files-signing")
            to_name_box(pg)
            self.assertEqual(pg.locator("#fsName").get_attribute("inputmode"), "none", "the tester's own keyboard never opens")
            self.assertEqual(pg.locator(".lkb").count(), 1)
            kb, sc = pg.locator(".lkb").bounding_box(), pg.locator("#screen").bounding_box()
            full = pg.evaluate("(() => { const s = document.querySelector('#screen'); return Number(s.dataset.kbH) * s.getBoundingClientRect().width / s.offsetWidth; })()")
            self.assertTrue(abs(kb["y"] - (sc["y"] + sc["height"])) <= 2, "the screen shrinks to just above the keys, like a real tablet")
            self.assertTrue(abs(kb["y"] + kb["height"] - (sc["y"] + full)) <= 2, "the keys fill the bottom of the tablet's own screen")
            pg.locator('.lkb [data-kbx="shift"]').click(); pg.locator('.lkb [data-kb="A"]').click()
            for ch in "mina":
                pg.locator(f'.lkb [data-kb="{ch}"]').click()
            self.assertEqual(pg.locator("#fsName").input_value(), "Amina")
            fb = pg.locator("#fsName").bounding_box()
            self.assertLessEqual(fb["y"] + fb["height"], kb["y"] + 1, "the field stays visible above the keys")
            pg.locator('.lkb [data-kbx="done"]').click(); pg.wait_for_timeout(200)
            self.assertEqual(pg.locator(".lkb").count(), 0)
            self.assertEqual(errors, [])
            b.close()

    def test_the_business_app_gives_an_email_box_its_email_keys(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg, errors = page(b, "merchant-phone")
            pg.locator('[data-act="wy:si:via:email"]').click(); pg.wait_for_timeout(300)
            box = pg.locator('#app input[type="email"]').first
            box.click(); pg.wait_for_timeout(300)
            self.assertEqual(pg.locator('.lkb [data-kb="@"]').count(), 1, "an email box gets the @ key")
            for ch in "amina":
                pg.locator(f'.lkb [data-kb="{ch}"]').click()
            pg.locator('.lkb [data-kb="@"]').click()
            self.assertTrue(pg.locator('#app input[type="email"]').first.input_value().startswith("amina@"))
            self.assertEqual(errors, [])
            b.close()

    def test_each_language_gets_its_own_letters(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            for lang, key in (("ar", "ب"), ("ko", "ㅎ"), ("ru", "ж"), ("am", "ለ"), ("hi", "क"), ("he", "ש"), ("th", "ก")):
                with self.subTest(lang=lang):
                    pg, errors = page(b, "files-signing")
                    pg.evaluate(SET_LANG, lang); pg.wait_for_timeout(300)
                    to_name_box(pg)
                    self.assertEqual(pg.locator(".lkb").count(), 1)
                    self.assertGreater(pg.locator(f'.lkb [data-kb="{key}"]').count(), 0, f"{lang} keyboard shows its own letters")
                    self.assertGreater(pg.locator('.lkb [data-kbx="globe"]').count(), 0, "a key switches to English letters")
                    if lang == "ko":                                    # letters join into a syllable as on a real Korean phone
                        for j in "ㅎㅏㄴ":
                            pg.locator(f'.lkb [data-kb="{j}"]').click()
                        self.assertEqual(pg.locator("#fsName").input_value(), "한")
                    self.assertEqual(errors, [])
                    pg.close()
            b.close()

    def test_a_computer_keeps_its_own_keyboard(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg, errors = page(b, "owner-web")
            box = pg.locator("input[type=text], input[type=email]").first
            if box.count():
                box.click(force=True); pg.wait_for_timeout(200)
            self.assertEqual(pg.locator(".lkb").count(), 0)
            b.close()


if __name__ == "__main__":
    unittest.main()
