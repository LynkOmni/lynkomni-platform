"""Translations never break a screen (owner decision 2026-11-06): every emulator screen keeps its size and nothing spills
over, in every language of design/fonts/scripts.v1.json (real machine translations from the language packs), a long-text
test (about 40% longer, accented) and a right-to-left test, at desktop and phone size.
Needs Playwright with Chromium (installed in CI's layout job); skipped where it is missing."""
import os, unittest
from services import translation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANGS = list(translation.languages()) + ["xx", "xx-rtl"]
FILE = os.path.join(ROOT, "web", "emulators", "dist", "lynkomni-pos-terminal.html")
PAGE = "file://" + FILE
PHONE = os.path.join(ROOT, "web", "emulators", "dist", "lynkomni-merchant-phone.html")
BROWSER = os.path.join(ROOT, "web", "emulators", "dist", "lynkomni-browser-frame.html")
ACCOUNT = os.path.join(ROOT, "web", "emulators", "dist", "lynkomni-account-site.html")
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
A11Y = open(os.path.join(ROOT, "tools", "a11y", "check.js"), encoding="utf-8").read()   # the automatic accessibility check (build section 1)
A11Y_LANGS = ("en", "xx-rtl")                                                        # contrast and names are the same in every language; direction matters


def problems(pg, lang):
    """Layout problems on the current screen, plus accessibility problems in the languages the a11y check runs for."""
    out = list(pg.evaluate(OVERFLOW))
    if lang in A11Y_LANGS:
        out += [f"a11y: {x}" for x in pg.evaluate(A11Y)]
    return out


# Chromium applies a changed `zoom` custom property on the next frame, so the measurement waits for one (people only ever see the settled frame).
SETTLE = "() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))"
SIZE = "() => { const r = document.querySelector('#device').getBoundingClientRect(), s = document.querySelector('#display').getBoundingClientRect(); return [Math.round(r.width / (window.devicePixelRatio || 1)), Math.round(s.width), Math.round(s.height)]; }"


def measure(pg):
    pg.evaluate(SETTLE)
    return tuple(pg.evaluate(SIZE))


class DarkPass:
    """The accessibility check again with the dark theme on: contrast differs by theme."""
    def dark_pass(self, b, url):
        pg = b.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="reduce")
        pg.goto(url); pg.check("#cDark"); pg.evaluate("document.activeElement.blur()")
        self.assertEqual(self.walk(pg, "en"), {}, "dark theme")
        pg.close()


@unittest.skipUnless(sync_playwright and os.path.isfile(FILE), "Playwright with Chromium is needed")
class TranslationLayout(DarkPass, unittest.TestCase):
    def walk(self, pg, lang="en"):
        """Every screen of a sale and the menu. Returns {screen: problems}."""
        found = {}
        def check(name):
            p = problems(pg, lang)
            if p:
                found[name] = p
        for k in "1234":
            pg.keyboard.press(k)
        check("home, 12 tiles")
        pg.click('[data-act="tile:sell"]'); check("sell")
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
        pg.click('.foot [data-act="enter"]'); pg.click('.keypad [data-act="menu"]'); check("home after a sale")
        pg.click('[data-act="tile:reports"]'); check("sales")
        pg.keyboard.press("Escape"); pg.click('[data-act="tile:settings"]'); check("settings")
        pg.click('[data-act="go:count"]')
        for k in "5000":
            pg.keyboard.press(k)
        check("cash count")
        pg.click('.keypad [data-act="menu"]'); pg.click('[data-act="tile:agent"]'); check("agent services")
        pg.click('[data-act="svc:cash_withdrawal"]')
        for k in "0788999111":
            pg.keyboard.press(k)
        check("agent number"); pg.keyboard.press("Enter")
        for k in "20000":
            pg.keyboard.press(k)
        check("agent amount"); pg.keyboard.press("Enter"); check("agent confirm")
        pg.keyboard.press("Enter"); check("agent sent"); pg.wait_for_selector('.foot [data-act="enter"]:not([disabled])'); check("agent confirmed")
        pg.click('.keypad [data-act="menu"]'); pg.click('[data-act="tile:collect"]'); check("collection point")
        pg.click('[data-act="svc:voucher"]')
        for k in "48213":
            pg.keyboard.press(k)
        check("voucher code")
        pg.click('.keypad [data-act="menu"]'); pg.click('[data-act="tile:partner_finance"]'); check("partner finance")
        pg.click('.keypad [data-act="menu"]'); pg.click('[data-act="tile:customers_credit"]')
        for k in "2000":
            pg.keyboard.press(k)
        check("credit book")
        pg.click('.keypad [data-act="menu"]'); pg.click('[data-act="tile:settings"]'); pg.click('[data-act="lowlit"]'); pg.click('.keypad [data-act="menu"]'); check("low-literacy home")
        pg.click('[data-act="tile:bills"]'); check("bills")
        pg.click('.keypad [data-act="menu"]'); pg.click("#cReal")
        pg.click('[data-act="tile:sell"]'); pg.locator(".tile").nth(1).click(); pg.click('[data-act="go:cart"]'); pg.click('[data-act="go:pay"]'); pg.click('[data-act="method:card"]'); check("coming soon")
        return found

    def test_no_screen_breaks_in_any_language_or_size(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            sizes = {}
            for width in (1280, 390):
                for lang in LANGS:
                    pg = b.new_page(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
                    pg.goto(PAGE)
                    pg.select_option("#cLang", lang)
                    sizes[(width, lang)] = measure(pg)
                    self.assertEqual(self.walk(pg, lang), {}, f"{lang} at {width}px")
                    want = "rtl" if lang == "xx-rtl" else "ltr" if lang == "xx" else translation._dir(lang)
                    self.assertEqual(pg.get_attribute("#display", "dir"), want, lang)
                    self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), width, f"{lang} at {width}px scrolls sideways")
                    pg.close()
            self.dark_pass(b, PAGE)
            b.close()
        for width in (1280, 390):   # the device and its screen keep exactly the same size in every language
            self.assertEqual(len({sizes[(width, l)] for l in LANGS}), 1, f"size changed at {width}px: {sizes}")


@unittest.skipUnless(sync_playwright and os.path.isfile(PHONE), "Playwright with Chromium is needed")
class PhoneLayout(DarkPass, unittest.TestCase):
    """The merchant app on a phone: every screen, in every language, keeps its size and nothing spills over."""
    def walk(self, pg, lang="en"):
        found = {}
        def check(name):
            p = problems(pg, lang)
            if p:
                found[name] = p
        check("sign in")
        pg.fill("#phoneIn", "0788123456"); pg.click('[data-act="sendcode"]'); check("code")
        pg.fill("#codeIn", "123456"); pg.click('[data-act="verify"]'); pg.wait_for_selector('[data-act="start"]'); check("registered")
        pg.click('[data-act="start"]'); check("home")
        pg.click('[data-act="newsale"]'); pg.locator(".tile").nth(5).click(); pg.locator(".tile").nth(5).click(); pg.locator(".tile").nth(0).click(); check("sell")
        pg.click('[data-act="view:basket"]'); check("basket")
        pg.click('[data-act="view:pay"]'); check("payment")
        pg.click('[data-act="method:mobile_money"]'); pg.fill("#momoIn", "0788123456"); check("mobile money")
        pg.click('.top [data-act="view:pay"]'); pg.click('[data-act="method:cash"]'); pg.locator(".quick button").nth(1).click(); check("cash")
        pg.click('[data-act="paycash"]'); check("sale complete")
        pg.click('[data-act="tab:home"]'); check("home after a sale")
        pg.click('[data-act="tab:stock"]'); check("stock")
        pg.locator(".rowbtn").first.click(); check("stock item")
        pg.click('[data-act="tab:chats"]'); check("chats")
        pg.click('[data-act="thread:t2"]'); pg.fill("#msgIn", "Yes"); pg.click('[data-act="send"]'); check("chat")
        pg.click('.top [data-act="view:main"]'); pg.click('[data-act="tab:business"]'); check("business")
        pg.click(".netchip"); check("sync sheet"); pg.click('.sheet [data-act="closesheet"]')
        pg.select_option("#cRole", "cashier"); pg.click('[data-act="tab:home"]'); check("cashier home")
        pg.check("#cReal"); pg.click('[data-act="tab:sell"]'); pg.locator(".tile").nth(1).click(); pg.click('[data-act="view:basket"]'); pg.click('[data-act="view:pay"]')
        check("payment, providers not signed"); pg.click('[data-act="method:mobile_money"]'); check("coming soon")
        return found

    def test_no_phone_screen_breaks_in_any_language_or_size(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            sizes = {}
            for width in (1280, 390):
                for lang in LANGS:
                    pg = b.new_page(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
                    pg.goto("file://" + PHONE)
                    pg.select_option("#cLang", lang)
                    sizes[(width, lang)] = measure(pg)
                    self.assertEqual(self.walk(pg, lang), {}, f"{lang} at {width}px")
                    want = "rtl" if lang == "xx-rtl" else "ltr" if lang == "xx" else translation._dir(lang)
                    self.assertEqual(pg.get_attribute("#display", "dir"), want, lang)
                    self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), width, f"{lang} at {width}px scrolls sideways")
                    pg.close()
            self.dark_pass(b, "file://" + PHONE)
            b.close()
        for width in (1280, 390):
            self.assertEqual(len({sizes[(width, l)] for l in LANGS}), 1, f"size changed at {width}px: {sizes}")


@unittest.skipUnless(sync_playwright and os.path.isfile(BROWSER), "Playwright with Chromium is needed")
class ShellLayout(DarkPass, unittest.TestCase):
    """The shared shell in a browser (build section 1): every part and every state, at computer, tablet and phone size, in every
    language, keeps the window size and nothing spills over. The browser window itself never scrolls sideways."""
    STATES = ["home", "payment", "state:loading", "state:empty", "state:offline", "state:error", "state:not_found", "state:no_results",
              "state:permission", "state:maintenance", "state:sync_pending", "state:coming_soon", "state:success"]

    def walk(self, pg, lang="en"):
        found = {}
        def check(name):
            p = problems(pg, lang)
            if p:
                found[name] = p
        for st in self.STATES:
            pg.click(f'#stateButtons button[data-state="{st}"]'); check(st)
        pg.click('#stateButtons button[data-state="home"]')
        for ov in ("launcher", "account", "globe", "search", "help", "bell", "sync"):
            if pg.locator(f'[data-act="shell:{ov}"]').count() == 0:      # on a phone the globe and help live in the account menu
                pg.click('[data-act="shell:account"]')
            pg.locator(f'[data-act="shell:{ov}"]').first.click(); check(ov)
            if ov == "search":
                pg.fill("#cmdIn", "new"); check("search results")
            pg.keyboard.press("Escape")
        pg.click('[data-act="archive"]'); check("undo toast")
        pg.click('[data-act="chart:week:table"]'); check("chart table")
        pg.fill("#usernameIn", "adm1n"); check("username held"); pg.fill("#usernameIn", "mamas.kitchen"); check("username taken")
        pg.click('[data-act="chat:lang:original"]'); check("chat original")
        return found

    def test_shell_breaks_nowhere_at_any_size_or_language(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            sizes = {}
            for size in ("computer", "tablet", "phone"):
                for lang in LANGS:
                    pg = b.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="reduce")
                    pg.goto("file://" + BROWSER)
                    pg.select_option("#cSize", size); pg.select_option("#cLang", lang)
                    sizes[(size, lang)] = measure(pg)
                    self.assertEqual(self.walk(pg, lang), {}, f"{lang} on {size}")
                    want = "rtl" if lang == "xx-rtl" else "ltr" if lang == "xx" else translation._dir(lang)
                    self.assertEqual(pg.get_attribute("#display", "dir"), want, lang)
                    pg.close()
            self.dark_pass(b, "file://" + BROWSER)
            # the page that holds the window never scrolls sideways at a narrow viewport either
            pg = b.new_page(viewport={"width": 390, "height": 900}); pg.goto("file://" + BROWSER)
            self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), 390)
            b.close()
        for size in ("computer", "tablet", "phone"):
            self.assertEqual(len({sizes[(size, l)] for l in LANGS}), 1, f"size changed on {size}: {sizes}")


@unittest.skipUnless(sync_playwright and os.path.isfile(ACCOUNT), "Playwright with Chromium is needed")
class AccountLayout(DarkPass, unittest.TestCase):
    """LynkOmni Account (build section 2): sign-in, the four sign-up steps, the three recovery paths, every account page, the
    step-up sheet and the shell's overlays, at computer, tablet and phone size, in every language."""
    PAGES = ["overview", "profile", "security", "businesses", "orders", "transactions", "wallet", "billing", "memberships", "privacy", "notifications", "support", "payslips", "payments", "start"]

    def walk(self, pg, lang="en"):
        found = {}
        def check(name):
            p = problems(pg, lang)
            if p:
                found[name] = p
        for st in ["signin"] + self.PAGES:
            pg.click(f'#stateButtons button[data-state="{st}"]'); check(st)
        pg.click('#stateButtons button[data-state="signup"]'); check("signup username")
        pg.fill("#usernameIn", "grace.k"); pg.click('[data-act="signup:username"]'); check("signup contact")
        pg.click('[data-act="signup:contact"]'); check("signup passkey")
        pg.click('[data-act="signup:passkey"]'); check("signup recovery code")
        pg.click('[data-act="signup:code"]'); check("signup done")
        for answers, name in ((["device:yes"], "recover device"), (["device:no", "code:yes"], "recover code"), (["device:no", "code:no"], "recover assisted")):
            pg.click('#stateButtons button[data-state="recover"]'); check("recover question")
            for a in answers:
                pg.click(f'[data-act="recover:{a}"]')
            check(name)
            pg.click('[data-act^="recover:start:"]'); check(name + " started")
        pg.click('#stateButtons button[data-state="security"]')
        pg.locator('[data-act^="passkey:remove:"]').first.click(); check("step-up sheet"); pg.click('[data-act="stepup:ok"]'); check("passkey removed")
        pg.click('#stateButtons button[data-state="start"]'); pg.click('[data-act="start:begin"]'); check("start steps")
        for st in ("profile", "registration", "tax_number"):
            pg.click(f'[data-act="start:step:{st}"]')
        pg.click('[data-act="start:submit"]'); check("start submitted"); pg.click('[data-act="start:poll"]'); check("start approved")
        pg.click('#stateButtons button[data-state="privacy"]'); pg.click('[data-act="data:request"]'); check("data requested")
        pg.click('[data-act="stepup:close"]'); pg.click('[data-act="stepup:ok"]'); check("closing")
        pg.click('#stateButtons button[data-state="overview"]')
        for ov in ("launcher", "account", "globe", "search", "help", "bell", "sync"):
            if pg.locator(f'[data-act="shell:{ov}"]').count() == 0:
                pg.click('[data-act="shell:account"]')
            pg.locator(f'[data-act="shell:{ov}"]').first.click(); check(ov)
            if ov == "search":
                pg.fill("#cmdIn", "sec"); check("search results")
            pg.keyboard.press("Escape")
        if pg.locator('[data-act="nav:more"]').count():
            pg.click('[data-act="nav:more"]'); check("more pages"); pg.keyboard.press("Escape")
        return found

    def test_account_breaks_nowhere_at_any_size_or_language(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            sizes = {}
            for size in ("computer", "tablet", "phone"):
                for lang in LANGS:
                    pg = b.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="reduce")
                    pg.goto("file://" + ACCOUNT)
                    pg.select_option("#cSize", size); pg.select_option("#cLang", lang)
                    sizes[(size, lang)] = measure(pg)
                    self.assertEqual(self.walk(pg, lang), {}, f"{lang} on {size}")
                    want = "rtl" if lang == "xx-rtl" else "ltr" if lang == "xx" else translation._dir(lang)
                    self.assertEqual(pg.get_attribute("#display", "dir"), want, lang)
                    pg.close()
            self.dark_pass(b, "file://" + ACCOUNT)
            pg = b.new_page(viewport={"width": 390, "height": 900}); pg.goto("file://" + ACCOUNT)
            self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), 390)
            b.close()
        for size in ("computer", "tablet", "phone"):
            self.assertEqual(len({sizes[(size, l)] for l in LANGS}), 1, f"size changed on {size}: {sizes}")


# Build section 3 devices: each names its screens (two for the mesh relay and the counter tablet's customer screen) and
# its language and dark controls (the shared panel uses data-ctl, the counter tablet its own ids).
DEVICES = {
    "counter-tablet": (["#screen", "#cscreen"], "#cLang", "#cDark"),
    "kitchen-screen": (["#screen"], '[data-ctl="lang"]', '[data-ctl="dark"]'),
    "customer-display": (["#screen", "#till"], '[data-ctl="lang"]', '[data-ctl="dark"]'),
    "rider-phone": (["#screen"], '[data-ctl="lang"]', '[data-ctl="dark"]'),
    "stock-scanner": (["#screen"], '[data-ctl="lang"]', '[data-ctl="dark"]'),
    "button-phone": (["#screen"], '[data-ctl="lang"]', '[data-ctl="dark"]'),
    "vcard-card": (["#screen"], '[data-ctl="lang"]', '[data-ctl="dark"]'),
    "mesh-relay": (["#screenA", "#screenB"], '[data-ctl="lang"]', '[data-ctl="dark"]'),
    "owner-web": (["#screen"], '[data-ctl="lang"]', '[data-ctl="dark"]'),
}
DEVICE_FILE = lambda e: os.path.join(ROOT, "web", "emulators", "dist", f"lynkomni-{e}.html")
OVERFLOW_IN = OVERFLOW.replace("() => {\n  const d = document.querySelector('#display')", "(sel) => {\n  const d = document.querySelector(sel)")


@unittest.skipUnless(sync_playwright and all(os.path.isfile(DEVICE_FILE(e)) for e in DEVICES), "Playwright with Chromium is needed")
class DeviceLayout(unittest.TestCase):
    """Every screen of every build-section-3 device (each state button), in every language, long text and right to left, at
    desktop and phone size: nothing spills over, the page never scrolls sideways, no script error, and the accessibility
    check passes in English, right to left and the dark theme."""
    def walk(self, pg, emulator, lang, width):
        roots, found = DEVICES[emulator][0], {}
        states = pg.eval_on_selector_all("[data-state]", "els => els.map(e => e.dataset.state)")
        self.assertTrue(states, f"{emulator}: no state buttons to walk")
        for st in states:
            pg.click(f'[data-state="{st}"]'); pg.evaluate(SETTLE)
            for r in roots:
                if not pg.evaluate("(r) => { const e = document.querySelector(r); return !!e && e.getClientRects().length > 0; }", r):
                    continue
                bad = list(pg.evaluate(OVERFLOW_IN, r))
                if lang in A11Y_LANGS:
                    pg.evaluate("(r) => { window.__a11yRoot = r; }", r)
                    bad += [f"a11y: {x}" for x in pg.evaluate(A11Y)]
                if bad:
                    found[f"{st} {r}"] = bad
            if pg.evaluate("document.documentElement.scrollWidth") > width:
                found[f"{st} page"] = ["scrolls sideways"]
        return found

    def test_devices_break_nowhere_in_any_language_or_size(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            for emulator, (roots, lang_sel, dark_sel) in DEVICES.items():
                for width in (1280, 390):
                    pg = b.new_page(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
                    errors = []; pg.on("pageerror", lambda e: errors.append(str(e)))
                    pg.goto("file://" + DEVICE_FILE(emulator)); pg.wait_for_selector("html[data-ready]", state="attached")
                    for lang in LANGS:
                        pg.select_option(lang_sel, lang)
                        self.assertEqual(self.walk(pg, emulator, lang, width), {}, f"{emulator}, {lang} at {width}px")
                    self.assertEqual(errors, [], f"{emulator} at {width}px")
                    pg.close()
                pg = b.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="reduce")
                pg.goto("file://" + DEVICE_FILE(emulator)); pg.wait_for_selector("html[data-ready]", state="attached")
                pg.check(dark_sel); pg.evaluate("document.activeElement.blur()")
                self.assertEqual(self.walk(pg, emulator, "en", 1500), {}, f"{emulator}, dark theme")
                pg.close()
            b.close()


if __name__ == "__main__":
    unittest.main()
