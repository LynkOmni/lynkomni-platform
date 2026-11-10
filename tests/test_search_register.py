"""The search register and breadcrumb trails (MASTER UPDATE, master blueprint section 57)."""
import json, os, unittest
from core import breadcrumbs as bc
from core import build_sections
from tools import search_register as sr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = json.load(open(os.path.join(ROOT, "catalog", "search.v1.json"), encoding="utf-8"))
ADDR = bc.ADDR


class TestBreadcrumbs(unittest.TestCase):
    def test_every_address_has_a_trail_home_through_real_pages(self):
        for host, path in bc.every_address():
            t = bc.trail(host, path)
            self.assertEqual(t[-1], path)
            self.assertEqual(t[0], bc.home(host, path), f"{host}{path}")
            for step in t[1:-1]:
                self.assertIn(step, bc.HOSTS[host], f"{host}{path}: the trail names {step}, which is not a page")

    def test_storefront_trails_start_at_storefront_and_records_end_the_trail(self):
        t = bc.trail("app.lynkomni.com", "/external/business/academy")
        self.assertEqual(t[0], "/external")
        self.assertNotIn("/", t)
        self.assertEqual(bc.trail("account.lynkomni.com", "/orders/{LOORD}"), ["/", "/orders", "/orders/{LOORD}"])
        self.assertEqual(bc.trail("app.lynkomni.com", "/business/automations/history"),
                         ["/", "/business", "/business/automations", "/business/automations/history"])
        self.assertIsNone(bc.parent("lynkomni.com", "/"))


class TestSearchRegister(unittest.TestCase):
    def test_the_register_is_generated_and_up_to_date(self):
        self.assertEqual(REG, sr.build(), "run python3 tools/search_register.py")

    def test_only_public_pages_of_indexed_hosts(self):
        private = set(REG["never_indexed_hosts"])
        self.assertTrue({"app.lynkomni.com", "account.lynkomni.com", "pay.lynkomni.com", "staff.lynkomni.com",
                         "partners.lynkomni.com", "api.lynkomni.com"} <= private)
        urls = [p["url"] for p in REG["pages"]]
        self.assertEqual(len(urls), len(set(urls)))
        for p in REG["pages"]:
            host = p["url"].split("/")[2]
            self.assertNotIn(host, private, p["url"])
            self.assertNotIn("/track/", p["url"], "a parcel tracker is private")
            self.assertNotIn("{table}", p["url"])
            self.assertTrue(p["title_key"].startswith("seo_title_") and p["description_key"].startswith("seo_desc_"))
            self.assertIn(p["build_section"], build_sections.ORDER, p["url"])
        for path in ADDR["website_paths"]:
            self.assertIn(f"https://lynkomni.com{path}", urls)

    def test_every_product_page_is_listed_as_a_product(self):
        cat = json.load(open(os.path.join(ROOT, "catalog", "products.v1.json"), encoding="utf-8"))
        for p in (cat.get("products") or cat):
            if p["page"].startswith("/"):
                hit = [x for x in REG["pages"] if x["url"] == f"https://lynkomni.com{p['page']}"]
                self.assertEqual([x["kind"] for x in hit], ["product"], p["family"])

    def test_page_families_name_their_build_section(self):
        for f in REG["families"]:
            self.assertTrue(build_sections.after(f["build_section"], 3), f["id"])
        self.assertIn("Bing", REG["change_notices"]["indexnow"])


if __name__ == "__main__":
    unittest.main()
