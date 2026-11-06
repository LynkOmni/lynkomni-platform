"""Brand fonts: Montserrat (headings) and Inter (body), self-hosted, small, licensed, and never loaded from another site."""
import glob, hashlib, json, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "design", "fonts")


def read(p, mode="r"):
    with open(p, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()


class Fonts(unittest.TestCase):
    def test_every_file_in_fonts_css_exists_and_is_woff2(self):
        files = set(re.findall(r"/fonts/([\w-]+\.woff2)", read(os.path.join(ROOT, "design", "fonts.css"))))
        self.assertEqual(len(files), 9)
        for f in files:
            self.assertEqual(read(os.path.join(FONTS, f), "rb")[:4], b"wOF2", f)

    def test_files_match_their_recorded_sources(self):
        rec = json.loads(read(os.path.join(FONTS, "sources.json")))
        self.assertTrue(rec["upstream_commit"])
        for f, v in rec["outputs"].items():
            self.assertEqual(hashlib.sha256(read(os.path.join(FONTS, f), "rb")).hexdigest(), v["sha256"], f"{f} changed: rebuild with build_fonts.py")

    def test_first_load_budget(self):
        budget = json.loads(read(os.path.join(ROOT, "design", "tokens.v1.json")))["fonts"]["first_load_budget_kb"] * 1024
        self.assertLessEqual(sum(os.path.getsize(p) for p in glob.glob(os.path.join(FONTS, "*-latin.woff2"))), budget)

    def test_licences_are_kept(self):
        for fam in ("inter", "montserrat"):
            self.assertIn("SIL OPEN FONT LICENSE", read(os.path.join(FONTS, "LICENSES", f"{fam}-OFL.txt")).upper())

    def test_no_font_is_loaded_from_another_site(self):
        bad = re.compile(r"fonts\.googleapis|fonts\.gstatic|use\.typekit|fonts\.bunny|cdnfonts")
        for base, dirs, names in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "dist", ".build", "__pycache__", "target", "vendor")]
            for n in names:
                if n.endswith((".css", ".html", ".ts", ".js", ".mjs", ".py", ".kt", ".swift", ".json")) and n != os.path.basename(__file__):
                    self.assertIsNone(bad.search(read(os.path.join(base, n))), os.path.join(base, n))


if __name__ == "__main__":
    unittest.main()
