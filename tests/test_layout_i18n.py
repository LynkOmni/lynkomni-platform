"""Translations never break a screen (owner decision 2026-11-06): every emulator screen keeps its size and nothing spills
over, in English, French, a long-text test (about 40% longer, accented) and a right-to-left test, at desktop and phone size.
Needs Playwright with Chromium (installed in CI's layout job); skipped where it is missing."""
import os, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = os.path.join(ROOT, "web", "emulators", "dist", "lynkomni-pos-terminal.html")
PAGE = "file://" + FILE
try:
    from playwright.sync_api import sync_playwright
except ImportError:          # pragma: no cover
    sync_playwright = None

# Elements inside the screen whose content is wider than their box, ignoring boxes that scroll on purpose or end in "...".
OVERFLOW = """() => {
  const d = document.querySelector('#display'), bad = [];
  for (const el of d.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (el.closest('svg') || el.closest('.sr') || cs.display === 'none') continue;   // .sr = text only for screen readers, hidden on purpose
    const scrolls = /(auto|scroll)/.test(cs.overflowX) || cs.textOverflow === 'ellipsis';
    if (!scrolls && el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0) bad.push((el.className || el.tagName) + ': ' + (el.textContent || '').trim().slice(0, 40));
    const r = el.getBoundingClientRect(), b = d.getBoundingClientRect();
    if (r.width && (r.left < b.left - 1 || r.right > b.right + 1) && !el.closest('.tabs')) bad.push('outside screen: ' + (el.className || el.tagName));
  }
  return [...new Set(bad)];
}"""
SIZE = "() => { const r = document.querySelector('#device').getBoundingClientRect(), s = document.querySelector('#display').getBoundingClientRect(); return [Math.round(r.width / (window.devicePixelRatio || 1)), Math.round(s.width), Math.round(s.height)]; }"


@unittest.skipUnless(sync_playwright and os.path.isfile(FILE), "Playwright with Chromium is needed")
class TranslationLayout(unittest.TestCase):
    def walk(self, pg):
        """Every screen of a sale and the menu. Returns {screen: problems}."""
        found = {}
        def check(name):
            p = pg.evaluate(OVERFLOW)
            if p:
                found[name] = p
        for k in "1234":
            pg.keyboard.press(k)
        check("sell")
        pg.locator(".tile").nth(5).click(); pg.locator(".tile").nth(3).click()
        pg.click('[data-act="go:cart"]'); check("basket")
        pg.click('[data-act="go:pay"]'); check("payment")
        pg.click('[data-act="method:cash"]'); pg.locator(".quick button").nth(1).click(); check("cash")
        pg.keyboard.press("Escape"); pg.click('[data-act="method:mobile_money"]')
        for k in "0788123456":
            pg.keyboard.press(k)
        check("mobile money")
        pg.keyboard.press("Escape"); pg.click('[data-act="method:card"]'); check("card")
        pg.keyboard.press("Escape"); pg.click('[data-act="method:cash"]'); pg.locator(".quick button").nth(0).click()
        pg.click('.foot [data-act="enter"]'); pg.wait_for_timeout(50); check("sale complete")
        pg.click('.foot [data-act="enter"]'); pg.click('.keypad [data-act="menu"]'); check("menu")
        pg.click('[data-act="go:sales"]'); check("sales")
        pg.keyboard.press("Escape"); pg.click('[data-act="go:count"]')
        for k in "5000":
            pg.keyboard.press(k)
        check("cash count")
        pg.keyboard.press("Escape"); pg.keyboard.press("Escape"); pg.click("#cReal")
        pg.locator(".tile").nth(1).click(); pg.click('[data-act="go:cart"]'); pg.click('[data-act="go:pay"]'); pg.click('[data-act="method:card"]'); check("coming soon")
        return found

    def test_no_screen_breaks_in_any_language_or_size(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            sizes = {}
            for width in (1280, 390):
                for lang in ("en", "fr", "xx", "xx-rtl"):
                    pg = b.new_page(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
                    pg.goto(PAGE)
                    pg.select_option("#cLang", lang)
                    sizes[(width, lang)] = tuple(pg.evaluate(SIZE))
                    problems = self.walk(pg)
                    self.assertEqual(problems, {}, f"{lang} at {width}px")
                    if lang == "xx-rtl":
                        self.assertEqual(pg.get_attribute("#display", "dir"), "rtl")
                    self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), width, f"{lang} at {width}px scrolls sideways")
                    pg.close()
            b.close()
        for width in (1280, 390):   # the device and its screen keep exactly the same size in every language
            self.assertEqual(len({sizes[(width, l)] for l in ("en", "fr", "xx", "xx-rtl")}), 1, f"size changed at {width}px: {sizes}")


if __name__ == "__main__":
    unittest.main()
