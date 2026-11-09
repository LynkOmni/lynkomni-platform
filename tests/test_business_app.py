"""The Business app as the blueprint lays it out (41 E, with 42 C, 42 I and 44 L row 3): catalog/business-app.v1.json lists every
screen with what it must hold and its address. The merchant phone emulator must show each screen, with each item, at its
address, for the business types that have it, with no script error. Needs Playwright with Chromium (CI's layout job)."""
import json, os, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHONE = os.path.join(ROOT, "web", "emulators", "dist", "lynkomni-merchant-phone.html")
with open(os.path.join(ROOT, "catalog", "business-app.v1.json"), encoding="utf-8") as f:
    REG = json.load(f)
with open(os.path.join(ROOT, "catalog", "addresses.v1.json"), encoding="utf-8") as f:
    ADDR = json.load(f)
try:
    from playwright.sync_api import sync_playwright
except ImportError:          # pragma: no cover
    sync_playwright = None


class Register(unittest.TestCase):
    def test_every_screen_has_an_address_in_the_address_map(self):
        paths = set(ADDR["app_paths"]) | {"/"}
        for s in REG["screens"]:
            if s["path"].startswith("account."):
                continue
            self.assertIn(s["path"].split("?")[0], paths, s["id"])

    def test_tabs_and_getting_in_match_the_rules(self):
        src = open(os.path.join(ROOT, "ts", "src", "business.ts"), encoding="utf-8").read()
        for kind, tabs in REG["tabs"].items():
            self.assertTrue(f'{kind}: {json.dumps(tabs)}' in src, kind)
        for step in REG["getting_in"]:
            self.assertTrue(f'"{step}"' in src, step)


@unittest.skipUnless(sync_playwright and os.path.isfile(PHONE), "Playwright with Chromium is needed")
class Screens(unittest.TestCase):
    def test_every_screen_and_item_is_shown_at_its_address(self):
        missing, errors = {}, []
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1280, "height": 1000}, reduced_motion="reduce")
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto("file://" + PHONE)
            pg.wait_for_selector("html[data-ready]")
            for s in REG["screens"]:
                pg.evaluate(f"__go({json.dumps(s['id'])})")
                shown = pg.get_attribute(".screen", "data-screen")
                if shown != s["id"]:
                    missing[s["id"]] = [f"shows {shown}"]
                    continue
                gone = [i for i in s["items"] if not pg.locator(f'#display [data-item="{i}"]').count()]
                if gone:
                    missing[s["id"]] = gone
                want = s["path"] if s["path"].startswith("account.") else "app.lynkomni.com" + s["path"]
                got = pg.text_content("#address")
                if "{" not in want and got != want:
                    missing.setdefault(s["id"], []).append(f"address {got}")
            b.close()
        self.assertEqual(errors, [])
        self.assertEqual(missing, {})

    def test_getting_in_runs_in_the_blueprint_order(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1280, "height": 1000}, reduced_motion="reduce")
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto("file://" + PHONE)
            seen = [pg.get_attribute("[data-gi]", "data-gi")]
            pg.fill("#phoneIn", "0788123456"); pg.click('[data-act="sendcode"]')
            pg.fill("#codeIn", "123456"); pg.click('[data-act="verify"]'); seen.append(pg.get_attribute("[data-gi]", "data-gi"))
            pg.click('[data-act="business:0"]'); pg.wait_for_selector('[data-act="start"]'); seen.append(pg.get_attribute("[data-gi]", "data-gi"))
            pg.click('[data-act="start"]'); seen.append(pg.get_attribute("[data-gi]", "data-gi"))
            pg.click('[data-act="localeok"]'); seen.append(pg.get_attribute("[data-gi]", "data-gi"))
            for step in [x["id"] for x in REG["setup_steps"]]:
                if step == "first_products":
                    pg.click('[data-act="firstway:scan"]')
                pg.click(f'[data-act="donestep:{step}"]')
            seen.append(pg.get_attribute('[data-act="firstsale"]', "data-gi"))
            pg.click('[data-act="firstsale"]')
            self.assertEqual(seen, REG["getting_in"])
            self.assertEqual(pg.get_attribute(".screen", "data-screen"), "sell")
            self.assertEqual(errors, [])
            b.close()

    def test_tabs_follow_the_business_type_and_a_tablet_uses_a_side_rail(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1280, "height": 1000}, reduced_motion="reduce")
            pg.goto("file://" + PHONE)
            pg.evaluate("__go('home')")
            for kind, tabs in REG["tabs"].items():
                pg.select_option("#cType", kind)
                self.assertEqual(pg.eval_on_selector_all(".tabbar [data-act]", "els => els.map(e => e.dataset.act.slice(4))"), tabs, kind)
                for tab in tabs:
                    pg.click(f'[data-act="tab:{tab}"]')
                    self.assertTrue(pg.locator(".top").count(), f"{kind}/{tab} has the top bar")
            pg.select_option("#cSize", "tablet")
            self.assertEqual(pg.locator(".rail").count(), 1)
            pg.select_option("#cSize", "web")
            pg.select_option("#cType", "shop"); pg.evaluate("__go('business')")
            self.assertEqual(pg.locator('[data-item="web_view"]').count(), 1)
            b.close()

    def test_top_bar_holds_the_five_parts(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1280, "height": 1000}, reduced_motion="reduce")
            pg.goto("file://" + PHONE)
            pg.evaluate("__go('home')")
            top = pg.locator(".top")
            self.assertEqual(top.locator('[data-brand-place="app-top-bar"]').count(), 1)
            self.assertEqual(top.locator("h1").count(), 1)
            self.assertEqual(top.locator(".netchip").count(), 1)
            self.assertEqual(top.locator('[data-act="view:notifications"]').count(), 1)
            self.assertEqual(top.locator('[data-act="view:account"]').count(), 1)
            b.close()

    def test_agent_point_never_hands_over_cash_before_the_partner_confirms(self):
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1280, "height": 1000}, reduced_motion="reduce")
            pg.goto("file://" + PHONE)
            pg.select_option("#cType", "agent_point"); pg.select_option("#cOutcome", "silent"); pg.evaluate("__go('home')")
            pg.click('[data-act="tab:services"]'); pg.click('[data-act="svc:cash_withdrawal"]')
            pg.fill("#anumIn", "0788123456"); pg.fill("#aamtIn", "500"); pg.click('[data-act="agentsend"]')
            pg.wait_for_timeout(800)
            self.assertTrue(pg.is_disabled('[data-act="handcash"]'))
            self.assertEqual(pg.locator('[data-item="one_receipt"]').count(), 1)
            b.close()
