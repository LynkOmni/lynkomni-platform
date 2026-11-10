"""Everything has a place (BIZZ & DEVICE, 2026-11-09): every product and new item lists the places it must appear in, every
product has its two sides, and the places already built show what the register says (more checks join as places are built)."""
import json, os, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = json.load(open(os.path.join(ROOT, "catalog", "placements.v1.json"), encoding="utf-8"))
PRODUCTS = json.load(open(os.path.join(ROOT, "catalog", "products.v1.json"), encoding="utf-8"))["products"]
ADDR = json.load(open(os.path.join(ROOT, "catalog", "addresses.v1.json"), encoding="utf-8"))
HOSTS = {h["host"] for h in ADDR["hosts"]}
import sys; sys.path.insert(0, ROOT)
from core.build_sections import ORDER  # noqa: E402


class Register(unittest.TestCase):
    def test_every_item_has_known_places_and_a_section(self):
        ids = [i["id"] for i in REG["items"]]
        self.assertEqual(len(ids), len(set(ids)))
        for i in REG["items"]:
            self.assertTrue(i["places"], i["id"])
            for p in i["places"]: self.assertIn(p, REG["places"], i["id"])
            self.assertIn(i["section"], ORDER, i["id"])

    def test_every_product_is_placed(self):
        placed = {i["id"]: i for i in REG["items"] if i["kind"] == "product"}
        self.assertEqual(set(placed), {p["family"] for p in PRODUCTS})
        for p in PRODUCTS:
            want = "footer" in placed[p["family"]]["places"]
            self.assertEqual(want, bool(p["footer_id"]), p["family"])       # the footer place and the catalog agree
            for base in ("launcher", "search", "help", "product_page"):
                self.assertIn(base, placed[p["family"]]["places"], p["family"])

    def test_every_service_is_in_every_place_it_belongs(self):
        """Owner rule, 10 November 2026: every product, service and tier feature, existing and new, is in the headers, menus,
        footer and every other place it belongs. A new billing family fails here until it is placed everywhere."""
        from services import billing
        apps = {p["family"]: p["app"] for p in PRODUCTS}
        for i in REG["items"]:
            places = set(i["places"])
            if i["kind"] == "product":
                want = {"website_header", "launcher", "search", "help", "product_page", "sitemap", "footer"}
                if any(x > 0 for x in billing.FAMILIES[i["id"]][3]): want.add("pricing_page")
                if apps[i["id"]].startswith("app.lynkomni.com/"): want.add("app_nav")
                self.assertEqual(want - places, set(), f"{i['id']} is missing from places")
            elif i["kind"] in ("service", "feature"):
                self.assertEqual({"search", "help", "sitemap"} - places, set(), i["id"])
                self.assertTrue(i.get("what"), i["id"])
            if i.get("footer_ids"): self.assertIn("footer", places, i["id"])

    def test_the_footer_shows_exactly_what_the_register_places_there(self):
        """Every product-name link in the footer belongs to a placed product or service, and every product or service placed in
        the footer is there."""
        import re
        footer = open(os.path.join(ROOT, "ts", "src", "footer.ts"), encoding="utf-8").read()
        shown = set(re.findall(r'brand\("([a-z]+)", "Lynk\w+"', footer))
        want = {p["footer_id"] for p in PRODUCTS if p["footer_id"]}
        for i in REG["items"]:
            want |= set(i.get("footer_ids", [])) | set(i.get("also_footer", []))
        self.assertEqual(shown, want)


class Sides(unittest.TestCase):
    def test_every_product_has_both_sides(self):
        for p in PRODUCTS:
            s = p["sides"]
            self.assertEqual(s["internal"], p["app"], p["family"])
            if s["external"] is None:
                self.assertTrue(s.get("external_reason"), p["family"])
            elif s["external"].startswith("https://"):
                self.assertIn(s["external"][len("https://"):].split("/")[0], HOSTS, p["family"])
                self.assertTrue(s.get("external_reason"), p["family"])
            else:
                path = s["external"][len("app.lynkomni.com"):]
                self.assertTrue(path.startswith("/external/"), p["family"])
                self.assertIn(path, ADDR["app_paths"], p["family"])
            self.assertIn(s["external_section"], ORDER[1:], p["family"])


if __name__ == "__main__": unittest.main()


try:
    from playwright.sync_api import sync_playwright
except ImportError:          # pragma: no cover
    sync_playwright = None
BROWSER = os.path.join(ROOT, "web", "emulators", "dist", "lynkomni-browser-frame.html")


@unittest.skipUnless(sync_playwright and os.path.isfile(BROWSER), "Playwright with Chromium is needed")
class BuiltPlaces(unittest.TestCase):
    """The section-1 items are really in their places in the shell (browser-frame): the side in the header, the side switch in
    the launcher, the account menu and search, Change view in the account menu, search (as a setting) and help, and Why this
    view? in the account menu and help."""
    def test_section_1_items_are_where_the_register_says(self):
        items = {i["id"]: set(i["places"]) for i in REG["items"] if i.get("section") == 1 and i["kind"] == "item"}
        with sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1500, "height": 1100})
            pg.goto("file://" + BROWSER); pg.wait_for_selector("html[data-ready]", state="attached")
            found = {k: set() for k in items}
            if pg.locator('#display [data-act="shell:side"]').count(): found["side_indicator"].add("app_nav"); found["side_switch"].add("app_nav")
            pg.click('[data-act="shell:launcher"]')
            if pg.locator("#display .lsides [data-act^='side:']").count(): found["side_switch"].add("launcher")
            pg.keyboard.press("Escape"); pg.click('[data-act="shell:account"]')
            if pg.locator("#display [data-act^='side:']").count(): found["side_switch"].add("account_menu")
            for act, item in (("shell:view", "change_view"), ("shell:why", "why_this_view")):
                if pg.locator(f'#display [data-act="{act}"]').count(): found[item].add("account_menu")
            pg.keyboard.press("Escape"); pg.click('[data-act="shell:search"]')
            en = json.load(open(os.path.join(ROOT, "web", "shell", "strings.en.json"), encoding="utf-8"))
            for act, item, kind, q in (("shell:side", "side_switch", "search", "storefront"), ("shell:view", "change_view", "search", en["change_view"]), ("shell:view", "change_view", "settings", en["change_view"])):
                pg.fill("#cmdIn", q)
                if pg.locator(f'#cmdList [data-act="{act}"]').count(): found[item].add(kind)
            pg.keyboard.press("Escape")
            help_text = None
            if pg.locator('[data-act="shell:help"]').count():
                pg.click('[data-act="shell:help"]'); help_text = pg.inner_text("#display")
            en = json.load(open(os.path.join(ROOT, "web", "shell", "strings.en.json"), encoding="utf-8"))
            if help_text:
                if en["why_this_view"] in help_text: found["why_this_view"].add("help"); found["change_view"].add("help")
                if en["switch_side_group"] in help_text: found["side_indicator"].add("help")
            b.close()
        for item, want in items.items():
            self.assertEqual(want - found[item], set(), f"{item} is missing from its places")


ACCOUNT = os.path.join(ROOT, "web", "emulators", "dist", "lynkomni-account-site.html")


@unittest.skipUnless(sync_playwright and os.path.isfile(ACCOUNT), "Playwright with Chromium is needed")
class AccountPlaces(unittest.TestCase):
    """Section-2 items on the account site: My Storefront and Seller support in the account menu, search and help; the account
    site chooses its own view (touch or not) and offers Change view in the account menu."""
    def test_section_2_items_are_where_the_register_says(self):
        items = {i["id"]: set(i["places"]) for i in REG["items"] if i.get("section") == 2 and i["kind"] == "item"}
        en = json.load(open(os.path.join(ROOT, "web", "emulators", "dist", "..", "account-site", "strings.en.json"), encoding="utf-8"))
        with sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1500, "height": 1100})
            pg.goto("file://" + ACCOUNT); pg.wait_for_selector("html[data-ready]", state="attached")
            found = {k: set() for k in items}
            pg.click('[data-act="shell:account"]')
            if pg.locator('#display [data-act="go:storefront"]').count(): found["my_storefront"].add("account_menu")
            if pg.locator('#display [data-act="go:support"]').count(): found["seller_support"].add("account_menu")
            self.assertEqual(pg.locator('#display [data-act="shell:view"]').count(), 1, "Change view in the account menu")
            pg.keyboard.press("Escape"); pg.click('[data-act="shell:search"]')
            pg.fill("#cmdIn", en["page_storefront"])
            if pg.locator('#cmdList [data-act="go:storefront"]').count(): found["my_storefront"].add("search")
            pg.fill("#cmdIn", en["support_seller"])
            if pg.locator('#cmdList [data-act="support:external"]').count(): found["seller_support"].add("search")
            pg.keyboard.press("Escape")
            pg.click('[data-state="storefront"]'); pg.click('[data-act="shell:help"]')
            if en["help_storefront"] in pg.inner_text("#display"): found["my_storefront"].add("help"); found["seller_support"].add("help")
            pg.keyboard.press("Escape"); pg.click('[data-state="support"]'); pg.click('[data-act="support:external"]')
            self.assertIn(en["support_seller"], pg.inner_text("#display"))
            b.close()
        for item, want in items.items():
            self.assertEqual(want - found[item], set(), f"{item} is missing from its places")


PHONE = os.path.join(ROOT, "web", "emulators", "dist", "lynkomni-merchant-phone.html")
BUILT_BY_SECTION_3 = {"app_nav", "search", "help", "settings", "account_menu"}     # the website places (header, footer, pricing, sitemap, showcase) come with section 5


@unittest.skipUnless(sync_playwright and os.path.isfile(PHONE), "Playwright with Chromium is needed")
class BusinessAppPlaces(unittest.TestCase):
    """Section-3 items in the Business app: Storefront home and its service pages, Storefront plans and LynkDriver are in every
    place the register lists that exists by section 3 (the website places follow in section 5)."""
    def test_section_3_items_are_where_the_register_says(self):
        items = {i["id"]: set(i["places"]) & BUILT_BY_SECTION_3 for i in REG["items"] if i.get("section") == 3 and i["kind"] == "item"}
        acts = {"storefront_home": ("side:external",), "storefront_service_pages": ("view:sflistings", "view:sfstock"), "storefront_plans": ("hub:plans_billing",), "lynkdriver": ("view:driver",)}
        found = {k: set() for k in items}
        with sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 1000})
            pg.goto("file://" + PHONE); pg.wait_for_selector("html[data-ready]", state="attached")
            def look(place):
                for item, want in acts.items():
                    if item in found and any(pg.locator(f'#display [data-act="{a}"]').count() for a in want): found[item].add(place)
            pg.evaluate("__go('business')"); look("app_nav")
            pg.evaluate("__go('storefront')"); look("app_nav")
            pg.evaluate("__go('account')"); look("account_menu")
            pg.evaluate("__go('settings')"); look("settings")
            pg.evaluate("__go('branches_devices')"); look("settings")
            pg.evaluate("__go('business')"); pg.click('#display [data-act="dsh:search"]')
            for q in ("Storefront", "Offers", "Stock", "LynkDriver"):
                pg.fill("#cmdIn", q); look("search")
            pg.keyboard.press("Escape")
            for sid in ("storefront", "storefront_listings", "driver"):
                pg.evaluate(f"__go('{sid}')"); pg.click('#display .top [data-act="dsh:help"]')
                if pg.locator("#display .dsh-help").count():
                    {"storefront": found.get("storefront_home"), "storefront_listings": found.get("storefront_service_pages"), "driver": found.get("lynkdriver")}[sid].add("help")
                    if sid == "storefront" and "storefront_plans" in found: found["storefront_plans"].add("help")
                pg.keyboard.press("Escape")
            b.close()
        for item, want in items.items():
            self.assertEqual(want - found[item], set(), f"{item} is missing from its places")
