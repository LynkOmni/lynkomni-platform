"""The shared username check (blueprint 44 B, Step 0): Instagram format 3 to 30, reserved words, look-alikes held for review,
one owner forever, never reissued, old names redirect. The TypeScript port is proved by the same vectors (ts/test/usernames.test.ts)."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core import usernames as u


class Rule(unittest.TestCase):
    def test_instagram_format_three_to_thirty(self):
        self.assertTrue(u.check("mamas.kitchen")["ok"]); self.assertEqual(u.check("@MAMAS.KITCHEN")["username"], "mamas.kitchen")
        self.assertTrue(u.check("a_b")["ok"]); self.assertTrue(u.check("x" * 30)["ok"])
        for bad, why in (("ab", "too_short"), ("x" * 31, "too_long"), ("mamas-kitchen", "bad_character"), ("mamás", "bad_character"),
                         (".abc", "leading_or_trailing_dot"), ("abc.", "leading_or_trailing_dot"), ("a..b", "double_dot"), ("", "empty"),
                         ("mamas.com", "web_address_ending"), ("joe.rw", "web_address_ending")):
            self.assertEqual(u.check(bad)["reason"], why, bad)

    def test_reserved_words_come_from_the_rule_catalog_hosts_and_partners(self):
        for w in ("lynkomni", "cruxomni", "lynkpos", "pos", "lynkstat", "admin", "support", "pay", "help", "official", "tables", "track",
                  "reviews", "orders", "academy", "shop", "staff", "partners", "status", "mtn", "mpesa", "airtel"):
            self.assertEqual(u.check(w)["reason"], "reserved_word", w)
        self.assertEqual(u.check("l.y.n.k.o.m.n.i")["reason"], "reserved_word")                      # separators do not hide a reserved word
        self.assertEqual(u.check("lynk_omni")["reason"], "reserved_word")
        self.assertTrue(u.check("support_1")["ok"]); self.assertTrue(u.check("the.corner.shop")["ok"])

    def test_look_alikes_are_held_for_review(self):
        for w, like in (("adm1n", "admin"), ("5upport", "support"), ("lynk0mni", "lynkomni"), ("rn.pesa", "mpesa")):
            c = u.check(w); self.assertEqual(c["reason"], "held_for_review", w); self.assertEqual(c["looks_like"], like)

    def test_vectors_and_typescript_data_are_current(self):
        out = subprocess.run([sys.executable, "tools/usernames_generate.py", "--check"], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0, out.stdout)
        v = json.loads((ROOT / "contract" / "vectors" / "usernames.v1.json").read_text())
        for case in v["cases"]:
            got = u.check(case["input"]); self.assertEqual((got["ok"], got["reason"], got["username"]), (case["ok"], case["reason"], case["username"]), case)

    def test_suggestions_are_free_and_valid(self):
        s = u.suggestions("Mama's Kitchen", taken=lambda x: x == "mamas.kitchen")
        self.assertTrue(s and "mamas.kitchen" not in s and all(u.check(x)["ok"] for x in s))


class Registry(unittest.TestCase):
    def test_free_before_taken_one_owner_never_reissued(self):
        r = u.UsernameRegistry()
        self.assertEqual(r.status("mamas.kitchen"), "available")
        r.take("Mamas.Kitchen", "LOOID-1", "shop", now="2026-11-08T00:00:00Z")
        self.assertEqual(r.status("mamas.kitchen"), "taken")
        with self.assertRaises(ValueError): r.take("mamas.kitchen", "LOOID-2", "shop")            # taken
        with self.assertRaises(ValueError): r.take("admin", "LOOID-2", "shop")                    # reserved
        r.change("LOOID-1", "mamas.kitchen", "mamas.bakery", now="2026-11-09T00:00:00Z")
        self.assertEqual(r.resolve("mamas.kitchen")["username"], "mamas.bakery")                  # old link and QR redirect
        self.assertEqual(r.status("mamas.kitchen"), "reserved")
        with self.assertRaises(ValueError): r.take("mamas.kitchen", "LOOID-2", "shop")            # never reissued to anyone else
        r.take("mamas.kitchen", "LOOID-1", "shop")                                                # the same owner may take it back
        r.change("LOOID-1", "mamas.kitchen", "mamas.cafe"); r.change("LOOID-1", "mamas.cafe", "mamas.place")
        self.assertEqual(r.resolve("mamas.cafe")["username"], "mamas.place")                      # chains follow to the newest name
        r.release("LOOID-1", "mamas.place")
        self.assertIsNone(r.resolve("mamas.place")); self.assertEqual(r.status("mamas.place"), "reserved")
        with self.assertRaises(ValueError): r.take("mamas.place", "LOOID-9", "shop")

    def test_dispute_is_the_only_transfer_and_is_recorded(self):
        r = u.UsernameRegistry(); r.take("acme.store", "LOOID-5", "shop", now="2026-11-08T00:00:00Z")
        rec = r.transfer_by_dispute("acme.store", "LOOID-7", "business", staff_id="LOSTF-1", reason="trademark claim via safety@", now="2026-11-08T00:00:00Z")
        self.assertEqual((rec["from"], rec["to"], rec["old_owner_redirect_until"]), ("LOOID-5", "LOOID-7", "2027-02-06T00:00:00Z"))
        self.assertEqual(r.resolve("acme.store")["owner"], "LOOID-7")


if __name__ == "__main__": unittest.main()
