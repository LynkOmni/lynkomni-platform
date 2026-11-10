"""One product catalog, one address map and one contacts map (review P1, A0 and M0, agreed 2026-11-07).
The footer, billing, visuals and every email address in the code must agree with them."""
import json, pathlib, re, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services import billing

def load(name): return json.loads((ROOT / "catalog" / name).read_text())
PRODUCTS, ADDR, CONTACTS = load("products.v1.json"), load("addresses.v1.json"), load("contacts.v1.json")
FOOTER = (ROOT / "ts" / "src" / "footer.ts").read_text()
HOSTS = {h["host"] for h in ADDR["hosts"]}
PATHS = set(ADDR["website_paths"]) | set(ADDR["redirects"])

def known(href):
    if href.startswith("https://"): return href[len("https://"):].split("/")[0] in HOSTS
    if href.startswith("account.lynkomni.com"): return True
    return href in PATHS

class Catalog(unittest.TestCase):
    def test_every_billing_family_once_with_its_picture(self):
        fams = [p["family"] for p in PRODUCTS["products"]]
        self.assertEqual(sorted(fams), sorted(billing.FAMILIES)); self.assertEqual(len(fams), len(set(fams)))
        needs = {n["id"] for n in json.loads((ROOT / "visuals" / "needs.v1.json").read_text())["needs"]}
        for p in PRODUCTS["products"]:
            self.assertIn(p["illustration"], needs, p["family"])
            self.assertTrue(known(p["page"]), p["page"])

    def test_footer_products_match_the_catalog(self):
        """Every product with a footer place is in the footer once, linked to its page, in the column that suits it (Products,
        Solutions or Developers); the Products column holds only products."""
        shown = re.findall(r'brand\("([a-z]+)", "Lynk\w+", "([^"]+)"\)', FOOTER)
        want = {p["footer_id"]: p["page"] for p in PRODUCTS["products"] if p["footer_id"]}
        for fid, page in want.items():
            self.assertEqual([h for i, h in shown if i == fid], [page], fid)
        col = FOOTER[FOOTER.index('id: "products"'):FOOTER.index('id: "solutions"')]
        self.assertTrue(set(re.findall(r'brand\("([a-z]+)"', col)) <= set(want))

    def test_every_footer_link_is_a_known_address(self):
        for href in re.findall(r'(?:brand|txt)\([^)]*"((?:/|https://)[^"]*)"\)', FOOTER):
            self.assertTrue(known(href), href)

    def test_every_product_app_place_is_in_the_address_map(self):
        """Blueprint 43 D: one address map. A product's place in the Business app must be a registered app path,
        and a product on its own host must be a registered host."""
        for p in PRODUCTS["products"]:
            app = p["app"]
            if app.startswith("https://"): self.assertIn(app[len("https://"):], HOSTS, p["family"])
            else:
                self.assertTrue(app.startswith("app.lynkomni.com/"), app)
                self.assertIn(app[len("app.lynkomni.com"):], ADDR["app_paths"], p["family"])

    def test_redirects_land_on_real_pages(self):
        for old, new in ADDR["redirects"].items():
            self.assertIn(new, ADDR["website_paths"], old)
            self.assertNotIn(old, ADDR["website_paths"], old)

class Contacts(unittest.TestCase):
    def test_the_agreed_counts(self):
        self.assertEqual(len(CONTACTS["inbound"]), 28)           # the 28 Google Groups (blueprint section 39)
        self.assertEqual(len(CONTACTS["senders"]), 9)            # 8 on mail. and 1 on news.
        self.assertTrue(all(s["address"].endswith(("@mail.lynkomni.com", "@news.lynkomni.com")) for s in CONTACTS["senders"]))

    def test_every_shown_address_has_a_page(self):
        for c in CONTACTS["inbound"]:
            if c["shown_on"]: self.assertTrue(known(c["shown_on"]), c)

    def test_no_reply_is_only_for_codes_and_alerts(self):
        nr = [s for s in CONTACTS["senders"] if s["address"].startswith("no-reply@")]
        self.assertEqual(len(nr), 1); self.assertIn("sign-in codes and security alerts only", nr[0]["sends"])

    def test_every_address_in_the_code_is_in_the_map(self):
        listed = {c["address"] for c in CONTACTS["inbound"]} | {s["address"] for s in CONTACTS["senders"]} | {CONTACTS["owner_inbox"], CONTACTS["emergency_admin"]}
        pat = re.compile(r"\b[a-z][a-z-]*@(?:mail\.|news\.)?(?:lynkomni|cruxomni)\.com\b")
        for f in list(ROOT.glob("services/*.py")) + list(ROOT.glob("ts/src/*.ts")) + list(ROOT.glob("providers/*.json")) + list(ROOT.glob("brand/*.py")):
            for a in pat.findall(f.read_text(errors="ignore")):
                self.assertIn(a, listed, f"{a} in {f.name}")

class BlueprintNumbers(unittest.TestCase):
    def test_numbers_come_from_the_code(self):
        sys.path.insert(0, str(ROOT / "tools")); import blueprint_numbers as bn
        n = bn.numbers()
        self.assertEqual(n["billing_families"], len(billing.FAMILIES)); self.assertTrue(n["version"].startswith("v0."))
        self.assertIn("stage3", n["ecosystem_revenue"])

if __name__ == "__main__": unittest.main()
