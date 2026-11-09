"""Everything has a place (BIZZ & DEVICE, 2026-11-09): every product and new item lists the places it must appear in, every
product has its two sides, and the places already built show what the register says (more checks join as places are built)."""
import json, os, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = json.load(open(os.path.join(ROOT, "catalog", "placements.v1.json"), encoding="utf-8"))
PRODUCTS = json.load(open(os.path.join(ROOT, "catalog", "products.v1.json"), encoding="utf-8"))["products"]
ADDR = json.load(open(os.path.join(ROOT, "catalog", "addresses.v1.json"), encoding="utf-8"))
HOSTS = {h["host"] for h in ADDR["hosts"]}


class Register(unittest.TestCase):
    def test_every_item_has_known_places_and_a_section(self):
        ids = [i["id"] for i in REG["items"]]
        self.assertEqual(len(ids), len(set(ids)))
        for i in REG["items"]:
            self.assertTrue(i["places"], i["id"])
            for p in i["places"]: self.assertIn(p, REG["places"], i["id"])
            self.assertIn(i["section"], range(0, 15), i["id"])

    def test_every_product_is_placed(self):
        placed = {i["id"]: i for i in REG["items"] if i["kind"] == "product"}
        self.assertEqual(set(placed), {p["family"] for p in PRODUCTS})
        for p in PRODUCTS:
            want = "footer" in placed[p["family"]]["places"]
            self.assertEqual(want, bool(p["footer_id"]), p["family"])       # the footer place and the catalog agree
            for base in ("launcher", "search", "help", "product_page"):
                self.assertIn(base, placed[p["family"]]["places"], p["family"])


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
            self.assertIn(s["external_section"], range(1, 15), p["family"])


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
