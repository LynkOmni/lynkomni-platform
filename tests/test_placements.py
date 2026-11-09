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
