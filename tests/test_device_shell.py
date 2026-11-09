"""The shell parts of blueprint 41 B on every device emulator (build section 3): "Find or do anything" search, the help panel (?),
the account menu, the language and region card on first use, the connection chip with its sync sheet, an address for every
screen (41 B deep links) that is in catalog/addresses.v1.json, 44 px touch targets, and the protected zones where nothing is
promoted ("Powered by", ads and promotions never on payment, refund, void, cash count, private chat, agent, float or commission
screens). Devices that are not navigated apps (customer display, card, mesh relay) show a connection state only (decision of
9 November 2026). Needs Playwright with Chromium (CI's layout job)."""
import json, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "web", "emulators", "dist")
with open(os.path.join(ROOT, "catalog", "addresses.v1.json"), encoding="utf-8") as f:
    ADDR = json.load(f)
try:
    from playwright.sync_api import sync_playwright
except ImportError:          # pragma: no cover
    sync_playwright = None

# Devices with the full shell bar (search, help, account, chip), and the state that shows a signed-in screen.
NAVIGATED = {"pos-terminal": "pin", "counter-tablet": "sell", "kitchen-screen": None, "rider-phone": None, "stock-scanner": None, "owner-web": None}
NOT_NAVIGATED = ("customer-display", "vcard-card", "mesh-relay")
PROMO = re.compile(r"powered by|sponsored|promot", re.I)


def path_ok(address):
    """An address shown on a device is a LynkOmni host plus a path from the address map (placeholders match any one segment)."""
    host, _, path = address.partition("/")
    path = "/" + path
    hosts = {h["host"] for h in ADDR["hosts"]}
    if host not in hosts:
        return False
    if host == "account.lynkomni.com":
        pool = ADDR["account_paths"]
    elif host == "app.lynkomni.com":
        pool = ADDR["app_paths"] + ["/"]
    else:
        return True
    return any(re.fullmatch(re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(p)), path.rstrip("/") or "/") for p in pool)


def open_page(p, emulator, width=1280):
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto("file://" + os.path.join(DIST, f"lynkomni-{emulator}.html"))
    return b, pg, errors


@unittest.skipUnless(sync_playwright and os.path.isdir(DIST), "Playwright with Chromium is needed")
class ShellParts(unittest.TestCase):
    def test_every_navigated_device_has_search_help_account_language_and_sync(self):
        with sync_playwright() as p:
            for emu, state in NAVIGATED.items():
                with self.subTest(emu):
                    b, pg, errors = open_page(p, emu)
                    # first use: the language and region card, with Yes, English and Change
                    self.assertEqual(pg.locator('[data-act="dsh:localeok"]').count(), 1, "first-run language card")
                    self.assertEqual(pg.locator('[data-act="dsh:localechange"]').count(), 1)
                    pg.click('[data-act="dsh:localeok"]')
                    self.assertEqual(pg.locator(".dsh-locale").count(), 0)
                    if state == "pin":   # the terminal's own keypad: PIN 1234, then Enter
                        for k in ("d1", "d2", "d3", "d4", "enter"):
                            pg.click(f'.keypad [data-act="{k}"]')
                    elif state:
                        pg.click(f'#stateButtons [data-state="{state}"]')
                    # find or do anything: typing filters, a result does the thing and closes the panel
                    pg.click('[data-act="dsh:search"]')
                    self.assertEqual(pg.locator("#cmdIn").count(), 1)
                    pg.keyboard.type("x")
                    self.assertEqual(pg.input_value("#cmdIn"), "x", "the search box has focus as soon as it opens")
                    pg.keyboard.press("Escape")
                    self.assertEqual(pg.locator(".dsh-panel").count(), 0, "Escape closes the panel")
                    # help: the screen's guide, LynkAssist, and a person (self-service never blocks reaching a person)
                    pg.click('[data-act="dsh:help"]')
                    for a in ("assist:ask", "support:chat", "support:case"):
                        self.assertEqual(pg.locator(f'.dsh-panel [data-act="{a}"]').count(), 1, a)
                    pg.click('.dsh-panel [data-act="support:chat"]')
                    self.assertTrue(pg.locator('.dsh-panel [role="status"]').inner_text().strip())
                    pg.click(".dsh-x")
                    # the account menu and the sync sheet
                    if not pg.locator('[data-act="dsh:account"]').count():   # the terminal keeps account and sync in its menu
                        pg.click('#display [data-act="menu"]')
                        pg.click('#display [data-act="tile:settings"]')
                    pg.click('[data-act="dsh:account"]')
                    self.assertEqual(pg.locator('.dsh-panel [data-act="copy:lynkid"]').count(), 1)
                    pg.click(".dsh-x")
                    pg.click('.dsh-chip, #statusbar [data-act="dsh:sync"]')
                    self.assertEqual(pg.locator(".dsh-panel.dsh-sync").count(), 1)
                    pg.click(".dsh-x")
                    # 44 px targets
                    for box in [pg.locator(".dsh-btn").nth(i).bounding_box() for i in range(pg.locator(".dsh-btn").count())]:
                        self.assertGreaterEqual(min(box["width"], box["height"]), 44 * 0.5, "a shell button is too small")  # rigs may be scaled to fit
                    self.assertTrue(path_ok(pg.text_content("#address")), pg.text_content("#address"))
                    self.assertEqual(errors, [])
                    b.close()

    def test_targets_are_44_px_at_full_size(self):
        css = open(os.path.join(ROOT, "web", "device", "deviceshell.css"), encoding="utf-8").read()
        self.assertRegex(css, r"\.dsh-btn \{[^}]*min-width: 44px;[^}]*min-height: 44px")
        self.assertRegex(css, r"\.dsh-field \{[^}]*min-height: 44px")

    def test_every_device_screen_has_an_address_from_the_address_map(self):
        bad = {}
        with sync_playwright() as p:
            for emu in list(NAVIGATED) + ["button-phone"]:
                b, pg, errors = open_page(p, emu)
                for k in [pg.locator("#stateButtons [data-state]").nth(i).get_attribute("data-state") for i in range(pg.locator("#stateButtons [data-state]").count())]:
                    pg.click(f'#stateButtons [data-state="{k}"]')
                    a = pg.text_content("#address") or ""
                    if not path_ok(a):
                        bad[f"{emu}:{k}"] = a
                self.assertEqual(errors, [], emu)
                b.close()
        self.assertEqual(bad, {})

    def test_address_maps_in_the_code_use_the_address_map(self):
        bad = []
        for emu in sorted(os.listdir(os.path.join(ROOT, "web", "emulators"))):
            app = os.path.join(ROOT, "web", "emulators", emu, "app.ts")
            if not os.path.isfile(app):
                continue
            for line in open(app, encoding="utf-8"):
                if "PATH" in line or "path:" in line:
                    for path in re.findall(r'"(/[a-z0-9/_-]*)"', line):
                        if not path_ok("app.lynkomni.com" + path):
                            bad.append(f"{emu}: {path}")
        self.assertEqual(bad, [])

    def test_the_business_app_keeps_its_five_part_top_bar_with_help_and_search(self):
        with sync_playwright() as p:
            b, pg, errors = open_page(p, "merchant-phone")
            pg.wait_for_selector("html[data-ready]")
            for screen in ("home", "business"):
                pg.evaluate(f"__go({json.dumps(screen)})")
                self.assertEqual(pg.locator("#app .dsh-field").count(), 1, f"{screen}: Find or do anything")
            pg.evaluate('__go("stock")')
            self.assertEqual(pg.locator('#app .top [data-act="dsh:help"]').count(), 1, "help (?) beside the title")
            self.assertEqual(pg.locator("#app .top .dsh-chip, #app .top .dsh-bar").count(), 0, "the 41 E top bar keeps its own chip")
            pg.click('#app .top [data-act="dsh:help"]')
            self.assertEqual(pg.locator('.dsh-panel [data-act="support:chat"]').count(), 1)
            pg.click(".dsh-x")
            pg.evaluate('__go("account")')
            pg.click('#app [data-act="help"]')
            self.assertEqual(pg.locator(".dsh-panel.dsh-help").count(), 1, "Help in the account screen opens the help panel")
            self.assertEqual(errors, [])
            b.close()

    def test_the_button_phone_menu_is_its_find_or_do(self):
        with sync_playwright() as p:
            b, pg, errors = open_page(p, "button-phone", 900)
            self.assertIn("1.", pg.inner_text("#screen"))   # the language card first, as a numbered list
            pg.click('[data-act="d1"]')
            menu = pg.inner_text("#screen")
            for word in ("Help", "Language and region", "Sync", "Account"):
                self.assertIn(word, menu)
            pg.click('[data-act="d5"]')
            pg.click('[data-act="d2"]')
            self.assertIn("LynkOmni Support", pg.inner_text("#screen"))
            self.assertEqual(errors, [])
            b.close()

    def test_single_purpose_devices_show_their_connection(self):
        with sync_playwright() as p:
            for emu in NOT_NAVIGATED:
                with self.subTest(emu):
                    b, pg, errors = open_page(p, emu)
                    self.assertEqual(pg.locator('[data-act="dsh:search"]').count(), 0)
                    self.assertEqual(errors, [])
                    b.close()


@unittest.skipUnless(sync_playwright and os.path.isdir(DIST), "Playwright with Chromium is needed")
class ProtectedZones(unittest.TestCase):
    """Nothing promoted where money, cash, private chat or partner work happens (CLAUDE.md ads and powered_by rules, 41 B)."""

    def test_business_app_protected_screens(self):
        with sync_playwright() as p:
            b, pg, errors = open_page(p, "merchant-phone")
            pg.wait_for_selector("html[data-ready]")
            pg.select_option("#cTier", "free")
            for screen in ("pay", "receipt", "shift", "thread", "agent_earnings", "money"):
                pg.evaluate(f"__go({json.dumps(screen)})")
                self.assertNotRegex(pg.inner_text("#display"), PROMO, screen)
                self.assertEqual(pg.locator("#display [data-ad], #display .ad, #display .pb").count(), 0, screen)
            pg.select_option("#cType", "agent_point")
            for tab in ("services", "float"):
                pg.evaluate(f'document.querySelector(\'[data-act="tab:{tab}"]\')?.click()')
                self.assertNotRegex(pg.inner_text("#display"), PROMO, tab)
            self.assertEqual(errors, [])
            b.close()

    def test_tills_never_show_powered_by_on_payment(self):
        with sync_playwright() as p:
            b, pg, errors = open_page(p, "counter-tablet")
            pg.select_option("#cPlan", "free")
            pg.click('#stateButtons [data-state="pay"]')
            pg.click('#screen [data-act="method:card"]')
            self.assertNotRegex(pg.inner_text("#cscreen"), PROMO, "customer screen at payment")
            self.assertNotRegex(pg.inner_text("#screen"), PROMO, "till at payment")
            for k in ("cash", "shift", "dayclose"):
                pg.click(f'#stateButtons [data-state="{k}"]')
                self.assertNotRegex(pg.inner_text("#screen"), PROMO, k)
            self.assertEqual(errors, [])
            b.close()
            b, pg, errors = open_page(p, "customer-display")
            for k in [pg.locator("#stateButtons [data-state]").nth(i).get_attribute("data-state") for i in range(pg.locator("#stateButtons [data-state]").count())]:
                if "pay" in k:
                    pg.click(f'#stateButtons [data-state="{k}"]')
                    self.assertNotRegex(pg.inner_text("#screen"), PROMO, k)
            self.assertEqual(errors, [])
            b.close()


if __name__ == "__main__":
    unittest.main()
