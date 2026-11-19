"""Nothing is cut, squeezed or blocked on any emulator, at any size (owner report 2026-11-19, two phone screenshots: the Account
side menu's labels were cut on a tablet, the owner's "Is this right?" card looked cut off on the laptop, and the laptop screen
ignored mouse clicks). For every emulator in web/emulators/dist, at every size it offers and in the light and dark theme:

- menus: every menu item keeps its full height (a long menu scrolls, it never squeezes), its label is never cut sideways, and no
  item hangs outside a menu that cannot scroll;
- pop-ups: every open dialog or sheet sits fully inside its screen; on anything wider than a phone it does not touch the
  screen's edges (a phone slides its sheet up from the bottom edge); its first button can really be pressed;
- input: a screen that has a mouse, trackpad, stylus or touch takes clicks and taps (only buttons-only screens ignore them).

Needs Playwright with Chromium (installed in CI's layout job); skipped where it is missing."""
import glob, os, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "web", "emulators", "dist")
try:
    from playwright.sync_api import sync_playwright
except ImportError:          # pragma: no cover
    sync_playwright = None

SETTLE = "() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))"
SIZE_CONTROLS = ("#cSize", "#cView")                 # the emulator panel's size or view choice, where an emulator has one
PANELS = ("first", "search", "help", "account", "sync", "bell")
SHELL_OVERLAYS = ("launcher", "account", "globe", "search", "help", "bell", "sync")

VISIBLE = """const shown = (e) => { if (!e || !e.getClientRects().length) return false; const cs = getComputedStyle(e);
  return cs.display !== 'none' && cs.visibility !== 'hidden'; };
const name = (e) => ((e.innerText || e.getAttribute('aria-label') || e.className || e.tagName) + '').trim().replace(/\\s+/g, ' ').slice(0, 40);"""

MENUS = "() => {" + VISIBLE + """
  const bad = [];
  for (const el of document.querySelectorAll('.shell-nav .navitem, .rail button, nav.side button, .tabbar button')) {
    if (!shown(el)) continue;
    if (el.scrollHeight > el.clientHeight + 1) bad.push('menu item squeezed: ' + name(el));
    const lab = el.querySelector('.nlabel') || el;
    if (lab.scrollWidth > lab.clientWidth + 1) bad.push('menu label cut sideways: ' + name(el));
    const nav = el.closest('.shell-nav, .rail, nav.side, .tabbar');
    if (nav && !/(auto|scroll)/.test(getComputedStyle(nav).overflowY)) {
      const n = nav.getBoundingClientRect(), r = el.getBoundingClientRect();
      if (r.bottom > n.bottom + 1 || r.top < n.top - 1) bad.push('menu item outside a menu that cannot scroll: ' + name(el));
    }
  }
  return [...new Set(bad)];
}"""

DIALOGS = "() => {" + VISIBLE + """
  const bad = [];
  const SEL = '.dsh-panel, .overlay > *, [role="dialog"]:not(.dsh-locale)';
  for (const el of document.querySelectorAll(SEL)) {
    if (!shown(el) || (el.parentElement && el.parentElement.closest(SEL))) continue;   // the outer pop-up only; what is inside it scrolls
    const root = el.closest('[data-device-class]') || el.closest('#display, #screen');
    if (!root) continue;
    const s = root.getBoundingClientRect(), r = el.getBoundingClientRect(), cls = root.dataset.deviceClass || '';
    const k = root.offsetHeight ? s.height / root.offsetHeight : 1;      // a screen drawn smaller to fit the page
    if (r.top < s.top - 1 || r.bottom > s.bottom + 1 || r.left < s.left - 1 || r.right > s.right + 1) bad.push('dialog outside its screen: ' + name(el));
    const drawer = r.height >= s.height - 2;                  // a side drawer runs the full height on purpose
    const phone = !cls || cls === 'phone' || cls === 'watch';
    if (!phone && !drawer && (s.bottom - r.bottom) / k < 6) bad.push('dialog glued to the bottom edge on a ' + cls + ': ' + name(el));
    const inView = (x) => { const q = x.getBoundingClientRect(); return q.height > 0 && q.top >= r.top && q.bottom <= r.bottom; };
    for (const b of [...el.querySelectorAll('button')].filter((x) => shown(x) && inView(x))) {
      const q = b.getBoundingClientRect(), hit = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
      if (!hit || !(hit === b || b.contains(hit))) bad.push('dialog button covered or blocked: ' + name(b));
    }
  }
  return [...new Set(bad)];
}"""

INPUT = """() => {
  const bad = [];
  for (const el of document.querySelectorAll('[data-interface]')) {
    const i = el.dataset.interface || '';
    if ((i.startsWith('computer.') || i.endsWith('.touch') || i === 'universal') && el.dataset.touch === 'no') bad.push('screen ignores clicks: ' + i);
  }
  return bad;
}"""


class BrowserTestsRun(unittest.TestCase):
    """A browser test skips itself where Chromium is missing, so it only protects anything if the layout job (which installs
    Chromium) runs it. Every test file that uses Playwright must be named in that job (the owner-web click bug of 2026-11-19
    sat in tests/test_device_shell.py, which no job with a browser ran)."""
    def test_every_browser_test_runs_in_the_layout_job(self):
        ci = open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8").read()
        for f in sorted(glob.glob(os.path.join(ROOT, "tests", "test_*.py"))):
            mod = os.path.basename(f)[:-3]
            if "playwright" in open(f, encoding="utf-8").read():
                self.assertIn(f"tests.{mod}", ci, f"{mod} uses a browser but no job with a browser runs it")


@unittest.skipUnless(sync_playwright and glob.glob(os.path.join(DIST, "*.html")), "Playwright with Chromium is needed")
class FitGuard(unittest.TestCase):
    def check(self, pg, where, found):
        pg.evaluate(SETTLE)
        bad = list(pg.evaluate(MENUS)) + list(pg.evaluate(DIALOGS)) + list(pg.evaluate(INPUT))
        if bad:
            found[where] = bad

    def open_dialogs(self, pg, where, found):
        """Opens each shell pop-up the emulator has, checks it and closes it again."""
        if pg.evaluate("!!window.__dsh"):
            for p in PANELS:
                try:
                    pg.evaluate("(p) => window.__dsh.show(p)", p)
                except Exception:
                    continue
                self.check(pg, f"{where}, {p}", found)
            pg.evaluate("window.__dsh.settle(); window.__settle && window.__settle()")
            return
        for ov in SHELL_OVERLAYS:
            btn = pg.locator(f'[data-act="shell:{ov}"]')
            if btn.count() == 0 or not btn.first.is_visible():
                continue
            btn.first.click()
            self.check(pg, f"{where}, {ov}", found)
            pg.keyboard.press("Escape")

    def test_nothing_cut_squeezed_or_blocked_anywhere(self):
        files = sorted(glob.glob(os.path.join(DIST, "*.html")))
        self.assertGreater(len(files), 10)
        found = {}
        with sync_playwright() as p:
            b = p.chromium.launch()
            for f in files:
                emu = os.path.basename(f)[len("lynkomni-"):-len(".html")]
                for dark in (False, True):
                    pg = b.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="reduce")
                    errors = []
                    pg.on("pageerror", lambda e: errors.append(str(e)))
                    pg.goto("file://" + f)
                    pg.wait_for_timeout(300)
                    if dark:
                        box = pg.locator('#cDark, #cDarkTheme, input[type="checkbox"][id*="Dark"]')
                        if box.count() == 0:
                            pg.close(); continue
                        box.first.check()
                    control = next((c for c in SIZE_CONTROLS if pg.locator(c).count()), None)
                    sizes = pg.eval_on_selector_all(f"{control} option", "o => o.map(x => x.value)") if control else [None]
                    for size in sizes:
                        if size is not None:
                            pg.select_option(control, size)
                        where = f"{emu}{' dark' if dark else ''}{f' at {size}' if size else ''}"
                        self.check(pg, where, found)
                        self.open_dialogs(pg, where, found)
                    self.assertEqual(errors, [], emu)
                    pg.close()
            b.close()
        self.assertEqual(found, {}, "\n".join(f"{k}: {v}" for k, v in found.items()))

    def test_business_app_signed_in_at_every_size(self):
        """The Business app's menus (phone tabs, tablet side rail, computer view) appear only after signing in."""
        found = {}
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="reduce")
            pg.goto("file://" + os.path.join(DIST, "lynkomni-merchant-phone.html"))
            pg.fill("#phoneIn", "0788123456"); pg.click('[data-act="sendcode"]')
            pg.fill("#codeIn", "123456"); pg.click('[data-act="verify"]')
            pg.click('[data-act="business:0"]'); pg.wait_for_selector('[data-act="start"]'); pg.click('[data-act="start"]')
            self.check(pg, "language and region card", found)
            pg.click('[data-act="localeok"]'); pg.evaluate("__go('home')")
            sizes = pg.eval_on_selector_all("#cSize option", "o => o.map(x => x.value)")
            for kind in ("shop", "no_till", "agent_point", "restaurant"):
                pg.select_option("#cType", kind)
                for size in sizes:
                    pg.select_option("#cSize", size)
                    pg.evaluate("__go('home')")
                    if size == "tablet":
                        self.assertGreater(pg.locator(".rail button").count(), 0, "the tablet side rail is checked")
                    self.check(pg, f"business app {kind} at {size}", found)
                    self.open_dialogs(pg, f"business app {kind} at {size}", found)
            b.close()
        self.assertEqual(found, {}, "\n".join(f"{k}: {v}" for k, v in found.items()))


if __name__ == "__main__":
    unittest.main()
