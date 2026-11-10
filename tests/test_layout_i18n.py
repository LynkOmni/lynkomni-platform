"""Translations never break a screen (owner decision 2026-11-06): every emulator screen keeps its size and nothing spills
over, in every language of design/fonts/scripts.v1.json (real machine translations from the language packs), a long-text
test (about 40% longer, accented) and a right-to-left test, at desktop and phone size.
Needs Playwright with Chromium (installed in CI's layout job); skipped where it is missing."""
import json, os, unittest
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


VIEW_OF = {"computer": "computer.pointer", "tablet": "tablet.touch", "phone": "phone.touch"}   # browser-frame test views (DEVICE 48.17)
SHELL_PANELS = ("first", "search", "help", "account", "sync")


def shell_parts(pg, check):
    """The 41 B shell parts on a device (ts/src/deviceshell.ts): the first-run language card and each panel, checked like any
    screen, then closed so the walk goes on."""
    if not pg.evaluate("!!window.__dsh"):
        return
    for panel in SHELL_PANELS:
        pg.evaluate("(p) => window.__dsh.show(p)", panel)
        check(f"shell {panel}")
    pg.evaluate("window.__dsh.settle(); window.__settle && window.__settle()")


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
        shell_parts(pg, check)
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
    """The Business app on a phone (blueprint 41 E): getting in, then every screen of catalog/business-app.v1.json for every
    business type, the tablet side rail and the computer web view, in every language: the size never changes and nothing spills over."""
    SCREENS = [s["id"] for s in json.load(open(os.path.join(ROOT, "catalog", "business-app.v1.json"), encoding="utf-8"))["screens"]]

    def walk(self, pg, lang="en"):
        found = {}
        def check(name):
            p = problems(pg, lang)
            if p:
                found[name] = p
        check("sign in")
        pg.fill("#phoneIn", "0788123456"); pg.click('[data-act="sendcode"]'); check("code")
        pg.fill("#codeIn", "123456"); pg.click('[data-act="verify"]'); check("choose business")
        pg.click('[data-act="business:0"]'); pg.wait_for_selector('[data-act="start"]'); check("registered")
        pg.click('[data-act="start"]'); check("language and region card")
        pg.click('[data-act="localeok"]'); check("setup, who it is for")
        pg.click('[data-act="entity:organisation"]'); check("setup, an organisation and its kinds")
        pg.click('[data-act="entity:company"]'); pg.click('[data-act="donestep:who_for"]'); check("setup")
        pg.click('[data-act="donestep:business_name_type"]'); pg.click('[data-act="donestep:currency"]'); check("setup, first products")
        pg.click('[data-act="skipstep:first_products"]'); pg.click('[data-act="skipstep:invite_staff"]'); check("setup, shop QR")
        pg.click('[data-act="skipstep:print_shop_qr"]'); pg.click('[data-act="firstsale"]')
        for sid in self.SCREENS:
            pg.evaluate(f"__go('{sid}')"); check(sid)
        pg.evaluate("__go('pay')"); pg.click('[data-act="way:mobile_money"]'); pg.fill("#momoIn", "0788123456"); check("mobile money")
        pg.click('.top [data-act="view:pay"]'); pg.click('[data-act="view:split"]'); check("split payment")
        pg.click('.top [data-act="view:pay"]'); pg.click('[data-act="way:credit"]'); check("credit")
        pg.click(".netchip"); check("sync sheet"); pg.click('.sheet [data-act="closesheet"]')
        for panel in ("search", "help"):   # the 41 B parts inside the Business app: Find or do anything, and help (?)
            pg.evaluate("(p) => window.__dsh.show(p)", panel); check(f"shell {panel}")
        pg.evaluate("window.__dsh.settle(); __go('home')")
        for kind in ("no_till", "agent_point", "restaurant"):
            pg.select_option("#cType", kind)
            for tab in ("home",) + {"no_till": ("invoices", "customers"), "agent_point": ("services", "float"), "restaurant": ("tables", "kitchen")}[kind]:
                pg.click(f'[data-act="tab:{tab}"]'); check(f"{kind} {tab}")
            if kind == "agent_point":
                pg.click('[data-act="tab:services"]'); pg.click('[data-act="svc:cash_withdrawal"]'); check("agent service")
                pg.click('.top [data-act="tab:services"]'); pg.click('[data-act="tab:home"]'); pg.click('[data-act="view:cashcheck"]'); check("cash check")
            if kind == "restaurant":
                pg.click('[data-act="tab:tables"]'); pg.click('[data-act="opentable"]'); check("table open")
        pg.select_option("#cType", "shop")
        for size in ("tablet", "web"):
            pg.select_option("#cSize", size)
            for sid in ("home", "sell", "stock", "business", "settings"):
                pg.evaluate(f"__go('{sid}')"); check(f"{size} {sid}")
        pg.select_option("#cSize", "phone")
        pg.select_option("#cRole", "cashier"); pg.evaluate("__go('home')"); check("cashier home")
        pg.check("#cReal"); pg.evaluate("__go('pay')"); check("payment, providers not signed"); pg.click('[data-act="way:mobile_money"]'); check("coming soon")
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
                    pg.select_option("#cView", VIEW_OF[size]); pg.select_option("#cLang", lang)
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
        pg.fill("#usernameIn", "grace.k"); check("signup username, age not confirmed"); pg.check("#adultIn"); pg.click('[data-act="signup:username"]'); check("signup contact")
        pg.click('[data-act="signup:contact"]'); check("signup passkey")
        pg.click('[data-act="signup:passkey"]'); check("signup recovery code")
        pg.click('[data-act="signup:code"]'); check("signup done")
        for answers, name in ((["device:yes"], "recover device"), (["device:no", "code:yes"], "recover code"), (["device:no", "code:no"], "recover assisted")):
            pg.click('#stateButtons button[data-state="recover"]'); check("recover question")
            for a in answers:
                pg.click(f'[data-act="recover:{a}"]')
            check(name)
            pg.click('[data-act^="recover:start:"]'); check(name + " started")
        pg.click('#stateButtons button[data-state="storefront"]'); check("my storefront"); pg.click('[data-act="idcheck:start"]'); check("identity sent")
        pg.click('#stateButtons button[data-state="support"]'); pg.click('[data-act="support:external"]'); check("seller support case")
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
    "track-page": (["#screen"], '[data-ctl="lang"]', '[data-ctl="dark"]'),
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
        def check(name):
            for r in roots:
                if not pg.evaluate("(r) => { const e = document.querySelector(r); return !!e && e.getClientRects().length > 0; }", r):
                    continue
                pg.evaluate(SETTLE)
                bad = list(pg.evaluate(OVERFLOW_IN, r))
                if lang in A11Y_LANGS:
                    pg.evaluate("(r) => { window.__a11yRoot = r; }", r)
                    bad += [f"a11y: {x}" for x in pg.evaluate(A11Y)]
                if bad:
                    found[f"{name} {r}"] = bad
        shell_parts(pg, check)
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

@unittest.skipUnless(sync_playwright and os.path.isfile(BROWSER), "Playwright with Chromium is needed")
class BrandPlaces(unittest.TestCase):
    """Each screen shows the mark its place calls for (brand/surfaces.v1.json): the full logo where the brand introduces
    itself and there is room (web header on computer and tablet, sign-in, sidebar), the emblem in app bars (under 96 px the
    logo falls back to the emblem), the wordmark on printed receipts."""
    CASES = [("browser-frame", 1280, {"web-header": "logo"}), ("account-site", 1280, {"web-header": "logo"}),
             ("merchant-phone", 1280, {"auth-onboarding": "logo"}), ("pos-terminal", 1280, {"auth-onboarding": "logo"}),
             ("counter-tablet", 1280, {"app-top-bar": "emblem", "auth-onboarding": "logo"}), ("customer-display", 1280, {"customer-welcome": "logo"}), ("owner-web", 1280, {"side-menu": "logo"})]

    def test_each_place_shows_its_mark(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            for emulator, width, want in self.CASES:
                pg = b.new_page(viewport={"width": width, "height": 900})
                pg.goto("file://" + os.path.join(ROOT, "web", "emulators", "dist", f"lynkomni-{emulator}.html"))
                pg.wait_for_selector("html[data-ready]", state="attached")
                got = dict(pg.eval_on_selector_all("[data-brand-place]", "els => els.map(e => [e.dataset.brandPlace, e.dataset.brandAsset])"))
                for place, asset in want.items():
                    self.assertEqual(got.get(place), asset, f"{emulator}: {place}")
                pg.close()
            pg = b.new_page(viewport={"width": 1280, "height": 900})   # a phone-sized shell writes the page title next to its mark: emblem
            pg.goto("file://" + BROWSER); pg.wait_for_selector("html[data-ready]", state="attached")
            pg.select_option("#cView", "phone.touch")   # 41 B and 30: the logo falls back to the emblem only under 96 px; a phone header has room
            self.assertEqual(pg.eval_on_selector("[data-brand-place='web-header']", "e => e.dataset.brandAsset"), "logo")
            pg.select_option("#cView", "tablet.touch")
            self.assertEqual(pg.eval_on_selector("[data-brand-place='web-header']", "e => e.dataset.brandAsset"), "logo")
            b.close()


@unittest.skipUnless(sync_playwright and os.path.isfile(BROWSER), "Playwright with Chromium is needed")
class TextAt200(unittest.TestCase):
    """Blueprint 41 B: text can grow to 200%. Browser zoom at 200% on a 1280 px window lays the page out at 640 px, so every
    emulator is opened at 640 px in English and the long-text test: nothing spills over and the page never scrolls sideways."""
    ROOTS = {**{e: v[0] for e, v in DEVICES.items()}, "pos-terminal": ["#display"], "merchant-phone": ["#display"], "browser-frame": ["#display"], "account-site": ["#display"]}
    LANG = {**{e: v[1] for e, v in DEVICES.items()}, "pos-terminal": "#cLang", "merchant-phone": "#cLang", "browser-frame": "#cLang", "account-site": "#cLang"}

    def test_every_emulator_at_200_percent_text(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            for emulator, roots in self.ROOTS.items():
                pg = b.new_page(viewport={"width": 640, "height": 900}, device_scale_factor=2, reduced_motion="reduce")
                pg.goto("file://" + DEVICE_FILE(emulator)); pg.wait_for_selector("html[data-ready]", state="attached")
                for lang in ("en", "xx"):
                    if pg.query_selector(self.LANG[emulator]):
                        pg.select_option(self.LANG[emulator], lang)
                    pg.evaluate(SETTLE)
                    bad = [x for r in roots if pg.query_selector(r) for x in pg.evaluate(OVERFLOW_IN, r)]
                    self.assertEqual(bad, [], f"{emulator} {lang} at 200% text")
                    self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), 640, f"{emulator} {lang} scrolls sideways at 200% text")
                pg.close()
            b.close()


# Distortion and fit (DEVICE, 48.17): interactive things never overlap, pictures keep their shape, and nothing is cut off.
FIT = """() => {
  const d = document.querySelector('#display'), bad = [];
  const shown = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
  const hits = [...d.querySelectorAll('button, a[href], input, select, [role="button"]')].filter(shown).filter((el) => !el.closest('[hidden]'));
  const box = (el) => el.getBoundingClientRect();
  const pinned = (el) => { for (let e = el; e && e !== d; e = e.parentElement) { const p = getComputedStyle(e).position; if (p === 'fixed' || p === 'sticky') return e; } return null; };
  for (let i = 0; i < hits.length; i++) for (let j = i + 1; j < hits.length; j++) {
    const a = hits[i], b = hits[j];
    if (a.contains(b) || b.contains(a)) continue;
    if (pinned(a) !== pinned(b)) continue;                      // content scrolling under a fixed or sticky bar is not an overlap
    const r = box(a), s = box(b), w = Math.min(r.right, s.right) - Math.max(r.left, s.left), h = Math.min(r.bottom, s.bottom) - Math.max(r.top, s.top);
    if (w > 2 && h > 2) {
      const top = document.elementFromPoint(Math.max(r.left, s.left) + w / 2, Math.max(r.top, s.top) + h / 2);
      if (top && (a.contains(top) || b.contains(top)) && !(a.closest('.overlay, [role=dialog]') ? !b.closest('.overlay, [role=dialog]') : b.closest('.overlay, [role=dialog]')))
        bad.push('overlap: ' + (a.dataset.act || a.textContent.trim().slice(0, 20)) + ' / ' + (b.dataset.act || b.textContent.trim().slice(0, 20)));
    }
  }
  for (const img of d.querySelectorAll('img')) {
    if (!shown(img) || !img.naturalWidth) continue;
    const r = box(img), want = img.naturalWidth / img.naturalHeight, got = r.width / r.height, fit = getComputedStyle(img).objectFit;
    if (fit !== 'contain' && fit !== 'cover' && Math.abs(got - want) / want > 0.02) bad.push('stretched: ' + (img.alt || img.src.slice(0, 30)));
  }
  return [...new Set(bad)];
}"""


@unittest.skipUnless(sync_playwright and os.path.isfile(BROWSER), "Playwright with Chromium is needed")
class DeviceFit(unittest.TestCase):
    """Every view the browser can be given fits every screen width from a 240 px watch to a 3840 px television: nothing spills
    over, nothing interactive overlaps, no picture is stretched and the page never scrolls sideways, in English, long text and
    right-to-left. The view chosen on a real phone and a real computer comes from the device facts, never the browser's name."""
    VIEWS = ("universal", "phone.touch", "tablet.touch", "computer.touch", "computer.pointer")
    WIDTHS = ("240", "320", "360", "390", "412", "600", "768", "1024", "1280", "1920", "3840")

    def check(self, pg, lang, where, found):
        p = list(pg.evaluate(OVERFLOW)) + list(pg.evaluate(FIT))
        if p:
            found[where] = p

    def test_every_view_fits_every_width(self):
        found = {}
        with sync_playwright() as p:
            b = p.chromium.launch()
            for lang in ("en", "xx", "xx-rtl"):
                pg = b.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="reduce")
                pg.goto("file://" + BROWSER); pg.wait_for_selector("html[data-ready]", state="attached")
                pg.select_option("#cLang", lang)
                for view in self.VIEWS:
                    pg.select_option("#cView", view)
                    for w in self.WIDTHS:
                        pg.select_option("#cSize", w); pg.evaluate(SETTLE)
                        where = f"{lang} {view} {w}"
                        self.assertEqual(pg.get_attribute("#display", "data-interface"), view, where)
                        self.check(pg, lang, where, found)
                        pg.click('[data-act="shell:launcher"]'); self.check(pg, lang, where + " launcher", found)
                        pg.keyboard.press("Escape")
                pg.close()
            # the outer page holding the window never scrolls sideways, at any real viewport
            for vw in (240, 320, 390, 768, 1280, 1920):
                pg = b.new_page(viewport={"width": vw, "height": 900}); pg.goto("file://" + BROWSER)
                pg.wait_for_selector("html[data-ready]", state="attached")
                self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), vw, f"page at {vw}")
                pg.close()
            b.close()
        self.assertEqual(found, {})

    def test_real_devices_pick_their_view(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            ctx = b.new_context(**p.devices["Pixel 7"]); pg = ctx.new_page(); pg.goto("file://" + BROWSER)
            pg.wait_for_selector("html[data-ready]", state="attached")
            self.assertEqual(pg.get_attribute("#display", "data-interface"), "phone.touch")
            ctx.close()
            pg = b.new_page(viewport={"width": 1440, "height": 900}); pg.goto("file://" + BROWSER)
            pg.wait_for_selector("html[data-ready]", state="attached")
            self.assertEqual(pg.get_attribute("#display", "data-interface"), "computer.pointer")
            b.close()


@unittest.skipUnless(sync_playwright and os.path.isfile(BROWSER), "Playwright with Chromium is needed")
class SwitchAccess(unittest.TestCase):
    """Switch access, keyboard and remote (DEVICE 48.17): every control on the home screen, in the launcher and in the account
    menu is reached with Tab alone and shows a visible focus ring; arrows move inside the launcher grid."""
    def test_everything_reached_by_keyboard(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            for view in ("universal", "computer.pointer", "phone.touch"):
                pg = b.new_page(viewport={"width": 1500, "height": 1100}, reduced_motion="reduce")
                pg.goto("file://" + BROWSER); pg.wait_for_selector("html[data-ready]", state="attached")
                pg.select_option("#cView", view)
                for panel in (None, "launcher", "account"):
                    if panel:
                        pg.click(f'[data-act="shell:{panel}"]')
                    want = set(pg.eval_on_selector_all("#display button:not([disabled]), #display a[href]",
                        "els => els.filter(e => e.getBoundingClientRect().width > 0 && !e.closest('[hidden]') && !e.closest('[inert]')).map(e => e.dataset.act || e.getAttribute('href') || e.textContent.trim())"))
                    pg.focus("#display [data-act='shell:launcher']") if not panel else None
                    seen, rings = set(), True
                    for _ in range(len(want) * 2 + 40):
                        info = pg.evaluate("() => { const e = document.activeElement; if (!e || !document.querySelector('#display').contains(e)) return null; const cs = getComputedStyle(e); return [e.dataset.act || e.getAttribute('href') || e.textContent.trim(), cs.outlineStyle !== 'none' || cs.boxShadow !== 'none']; }")
                        if info:
                            seen.add(info[0]); rings = rings and info[1]
                        pg.keyboard.press("Tab")
                    self.assertTrue(want <= seen, f"{view} {panel}: not reached by Tab: {sorted(want - seen)[:6]}")
                    self.assertTrue(rings, f"{view} {panel}: a focused control shows no focus ring")
                    if panel:
                        pg.keyboard.press("Escape")
                pg.close()
            b.close()


@unittest.skipUnless(sync_playwright, "Playwright with Chromium is needed")
class NonTouchVersions(unittest.TestCase):
    """Every device made in a buttons-only version (DEVICE 48.17.14) works by its keys alone: the screen takes no taps, the
    navigation pad (or bump bar and remote) is on the body, and every control on the first screen is reached with the arrows."""
    CASES = (("pos-terminal", "#display"), ("stock-scanner", "#screen"), ("kitchen-screen", "#screen"))
    REACH = """(root) => { const r = document.querySelector(root); return [...r.querySelectorAll("button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), [tabindex='0']")]
      .filter((e) => { const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0 && !e.closest('[hidden]'); }).map((e, i) => e.dataset.act || e.id || ('#' + i)); }"""
    WHO = "(root) => { const a = document.activeElement, r = document.querySelector(root); if (!a || !r.contains(a)) return null; const all = [...r.querySelectorAll(\"button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), [tabindex='0']\")]; return a.dataset.act || a.id || ('#' + all.indexOf(a)); }"

    def test_buttons_only_versions_work_by_keys(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            for emu, root in self.CASES:
                pg = b.new_page(viewport={"width": 1400, "height": 1100}, reduced_motion="reduce")
                pg.goto("file://" + os.path.join(ROOT, "web", "emulators", "dist", f"lynkomni-{emu}.html")); pg.wait_for_selector("html[data-ready]", state="attached")
                pg.evaluate("window.__settle && window.__settle()")
                pg.select_option('[data-ctl="version"]', "non_touch")
                self.assertEqual(pg.get_attribute(root, "data-touch"), "no", emu)
                self.assertGreater(pg.locator('[data-act="pad:ok"]').count(), 0, f"{emu}: navigation pad on the body")
                pe = pg.evaluate(f"getComputedStyle(document.querySelector('{root}').querySelector('button') || document.querySelector('{root}')).pointerEvents")
                self.assertEqual(pe, "none", f"{emu}: the screen takes no taps")
                want = set(pg.evaluate(self.REACH, root))
                pg.mouse.click(1, 1); pg.keyboard.press("ArrowDown")
                seen, todo = set(), [pg.evaluate(self.WHO, root)]
                while todo:
                    cur = todo.pop()
                    if cur is None or cur in seen: continue
                    seen.add(cur)
                    for k in ("ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight"):
                        pg.evaluate("([root, id]) => { const r = document.querySelector(root); const all = [...r.querySelectorAll(\"button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), [tabindex='0']\")]; const el = all.find((e, i) => (e.dataset.act || e.id || ('#' + i)) === id); el && el.focus(); }", [root, cur])
                        pg.keyboard.press(k); todo.append(pg.evaluate(self.WHO, root))
                self.assertEqual(want - seen, set(), f"{emu}: not reached by the arrows")
                pg.close()
            b.close()

    def test_pad_keys_pressed_by_finger_or_mouse_move_the_focus(self):
        """The pad on the device body is pressed with a finger or a mouse, which must never take the focus away from the screen
        (owner report 2026-11-10: every press jumped back to the first control). Real clicks, not keyboard keys."""
        with sync_playwright() as p:
            b = p.chromium.launch()
            for emu, root in self.CASES:
                for touch in (False, True):
                    cx = b.new_context(viewport={"width": 1400, "height": 1100}, reduced_motion="reduce", has_touch=touch)
                    pg = cx.new_page()
                    pg.goto("file://" + os.path.join(ROOT, "web", "emulators", "dist", f"lynkomni-{emu}.html")); pg.wait_for_selector("html[data-ready]", state="attached")
                    pg.select_option('[data-ctl="version"]', "non_touch")
                    press = (lambda k: pg.tap(f'[data-act="pad:{k}"]')) if touch else (lambda k: pg.click(f'[data-act="pad:{k}"]'))
                    seen = []
                    for k in ("down", "down", "down", "down"):
                        press(k); seen.append(pg.evaluate(self.WHO, root))
                    self.assertNotIn(None, seen, f"{emu} touch={touch}: the focus left the screen")
                    self.assertGreaterEqual(len(set(seen)), 2, f"{emu} touch={touch}: the pad does not move the focus: {seen}")
                    self.assertNotEqual(seen[0], seen[1], f"{emu} touch={touch}: the second press went back to the first control: {seen}")
                    before = pg.evaluate(self.WHO, root)
                    press("up")
                    self.assertNotEqual(pg.evaluate(self.WHO, root), before, f"{emu} touch={touch}: Up did nothing")
                    press("ok")
                    self.assertIsNotNone(pg.evaluate(self.WHO, root), f"{emu} touch={touch}: OK lost the focus")
                    cx.close()
            b.close()
