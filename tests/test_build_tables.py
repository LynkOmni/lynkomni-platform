"""The "where every part is built" tables of the master blueprint (64.11 onward) in catalog/build-tables.v1.json, read
through core/build_sections.py (section 4 part 1c, owner 2026-11-19). A build section is not locked until every row naming it
is done there (blueprint 44 L), and nothing is marked done ahead of the build order."""
import json, os, re, unittest
from core import build_sections as b

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE_IDS = ["64.11", "65.9", "66.10", "67.17", "68.14", "69.14", "70.16", "71.9", "72.9", "73.9", "74.9", "75.9", "76.8", "78.16", "79.10", "80.15", "81.4", "83.6", "84.6", "85.6", "86.12", "87.6", "88.6", "89.10", "90.7", "91.9", "92.4", "93.5", "94.9"]
CHANGELOG = open(os.path.join(ROOT, "docs", "lynkomni-changelog.md"), encoding="utf-8").read()
ORDER = [str(n) for n in b.ORDER]


def building():
    return next(str(s["n"]) for s in b.SECTIONS if s.get("status") != "locked")


class BuildTables(unittest.TestCase):
    def test_the_tables_in_blueprint_order(self):
        self.assertEqual([t["id"] for t in b.TABLES], TABLE_IDS)
        for t in b.TABLES:
            self.assertEqual(t["blueprint_section"], int(t["id"].split(".")[0]))
            self.assertTrue(t["update"].endswith("UPDATE"), t["id"])
            self.assertTrue(t["rows"], t["id"])

    def test_every_row_names_real_sections_once_per_table(self):
        for t in b.TABLES:
            seen = []
            for r in t["rows"]:
                self.assertTrue(r["sections"], t["id"])
                self.assertTrue(r["part"].strip(), t["id"])
                for s in r["sections"]:
                    self.assertIn(s, ORDER, f"{t['id']}: section {s} is not in the build order")
                    self.assertNotIn(s, seen, f"{t['id']}: section {s} is named twice")
                    seen.append(s)
                self.assertTrue(r.get("nothing") or "done" in r, f"{t['id']} {r['sections']}: a part needs its done map")
                if r.get("nothing"):
                    self.assertFalse(r.get("done") or r.get("progress"), f"{t['id']} {r['sections']}: nothing to build there")
                for s in list(r.get("done", {})) + list(r.get("progress", {})):
                    self.assertIn(s, r["sections"], f"{t['id']}: {s} is marked but the row does not name it")

    def test_a_locked_section_has_every_part_done(self):
        for s in b.SECTIONS:
            if s.get("status") == "locked":
                left = [f"{tid} {upd}" for tid, upd, _ in b.missing(s["n"])]
                self.assertEqual(left, [], f"section {s['n']} is locked but parts are still to build")

    def test_nothing_is_done_ahead_of_the_build_order(self):
        now = ORDER.index(building())
        for t in b.TABLES:
            for r in t["rows"]:
                for s in list(r.get("done", {})) + list(r.get("progress", {})):
                    self.assertLessEqual(ORDER.index(s), now, f"{t['id']}: section {s} is marked before its turn")

    def test_every_done_version_is_in_the_change_log(self):
        for t in b.TABLES:
            for r in t["rows"]:
                for s, v in r.get("done", {}).items():
                    self.assertRegex(v, r"^v0\.\d+\.\d+$", t["id"])
                    self.assertIn(f"## {v} ", CHANGELOG, f"{t['id']} {s}: {v} is not in the change log")
                for s, items in r.get("progress", {}).items():
                    for item in items:
                        v = re.match(r"^(v0\.\d+\.\d+): ", item)
                        self.assertTrue(v, f"{t['id']} {s}: progress lines start with their version")
                        self.assertIn(f"## {v.group(1)} ", CHANGELOG, f"{t['id']} {s}: {v.group(1)} is not in the change log")

    def test_every_section_from_4_has_its_parts_listed(self):
        """Each build section from 4 onward has at least one part across the tables, so the lock rule has something to check."""
        for n in ORDER[ORDER.index("4"):]:
            self.assertGreater(b.tally(n)[1], 0, f"section {n} has no part in the tables")

    def test_the_helpers_agree(self):
        done, work = b.tally("3A")
        self.assertEqual((done, work), (3, 3))
        self.assertEqual(b.status("4"), "locked")              # locked 25 November 2026 (v0.107.0)
        self.assertEqual(b.missing("4"), [])
        self.assertEqual(len(b.missing("4")), b.tally("4")[1] - b.tally("4")[0])


if __name__ == "__main__":
    unittest.main()
