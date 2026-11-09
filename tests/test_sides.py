"""The two sides (BIZZ & DEVICE, owner approved 2026-11-09): the workspace keeps every path; the Storefront is /external +
the path; every app path is classified exactly once; the side is read from the address alone; Python and TypeScript agree."""
import json, os, subprocess, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import sides as S
from core import usernames

ADDR = json.load(open(os.path.join(ROOT, "catalog", "addresses.v1.json"), encoding="utf-8"))
R = ADDR["storefront"]


class Addresses(unittest.TestCase):
    def test_every_app_path_is_classified_exactly_once(self):
        groups = [set(R["mirrors"]), set(R["storefront_only"]), set(R["shared"]), set(R["workspace_only"])]
        for i, a in enumerate(groups):
            for b in groups[i + 1:]:
                self.assertEqual(a & b, set())
        for p in ADDR["app_paths"]:
            S.kind(p)                                                       # raises when a path has no class

    def test_every_mirror_has_its_storefront_twin_in_the_map(self):
        for m in R["mirrors"]:
            self.assertIn(m, ADDR["app_paths"], m)
            self.assertIn(R["prefix"] + m, ADDR["app_paths"], m)
        for p in R["storefront_only"] + R["shared"] + R["workspace_only"]:
            self.assertIn(p, ADDR["app_paths"], p)
        self.assertTrue(all(p.startswith(R["prefix"] + "/") for p in R["storefront_only"]))

    def test_the_prefix_is_the_only_side_word_and_never_a_service(self):
        self.assertEqual(R["prefix"], "/external")
        self.assertFalse(any(p.startswith("/external") and S.kind(p) in ("shared", "workspace_only") for p in ADDR["app_paths"]))

    def test_public_storefront_pages_are_in_the_map(self):
        self.assertIn("/explore/{list}", ADDR["shop_paths"]); self.assertIn("/{username}/{list}/{LOLST}", ADDR["shop_paths"])
        self.assertIn("/listings/{LOLST}", ADDR["pay_paths"]); self.assertIn("/download/driver", ADDR["website_paths"])
        self.assertEqual(R["public"]["lists"], ["products", "courses", "services", "events", "apps"])

    def test_side_words_are_reserved_usernames(self):
        for w in ("external", "explore", "storefront"):
            self.assertEqual(usernames.check(w)["reason"], "reserved_word", w)


class Reading(unittest.TestCase):
    def test_side_from_the_address(self):
        self.assertEqual(S.side_of("/sell"), "internal")
        self.assertEqual(S.side_of("/external/sell"), "external")
        self.assertEqual(S.side_of("/externality"), "internal")
        self.assertEqual(S.side_of("shop.lynkomni.com/grace/courses/LOLST-6837-8950-1932"), "external")
        self.assertEqual(S.side_of("shop.lynkomni.com/grace/tables/4"), "internal")
        self.assertEqual(S.side_of("shop.lynkomni.com/track/LOORD-5499-1341-4781"), "internal")
        self.assertEqual(S.side_of("pay.lynkomni.com/listings/LOLST-6837-8950-1932"), "external")
        self.assertEqual(S.side_of("pay.lynkomni.com/r/LORCP-2176-0474-0548"), "internal")

    def test_twins_round_trip(self):
        for m in R["mirrors"]:
            self.assertEqual(S.workspace_path(S.storefront_path(m)), m)
        with self.assertRaises(ValueError): S.storefront_path("/sell/basket")
        with self.assertRaises(ValueError): S.workspace_path("/external/support")

    def test_vectors_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "sides_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__": unittest.main()


class Ledger(unittest.TestCase):
    def test_one_legal_ledger_labelled_by_side(self):
        from core import accounts as A
        sale = next(k for k, v in A.POSTINGS.items() if "reverse_of" not in v and v.get("amount", "total_minor") == "total_minor")
        evs = [{"id": "1", "type": sale, "payload": {"total_minor": 1000, "method": "cash"}},
               {"id": "2", "type": sale, "payload": {"total_minor": 500, "method": "cash", "side": "external"}}]
        j = A.journal(evs, lambda p, f: p[f])
        self.assertEqual([e["side"] for e in j], ["internal", "external"])
        self.assertEqual(len(A.side_entries(j, "external")), 1)
        self.assertEqual(A.profit(j), A.profit(A.side_entries(j, "internal")) + A.profit(A.side_entries(j, "external")))   # statutory = both sides
        with self.assertRaises(ValueError): A.side_entries(j, "both")


class CountryPacks(unittest.TestCase):
    def test_every_pack_has_unconfirmed_storefront_settings(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "country_storefront.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        from core.regions import country
        sf = country("XX")["storefront"]
        self.assertFalse(sf["seller_income_reporting"]["confirmed"]); self.assertIsNone(sf["age_of_majority"])
