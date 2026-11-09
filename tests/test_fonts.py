"""Font system: every LynkOmni language has its script's fonts, in the right direction, self-hosted and small.
Source of truth: design/fonts/scripts.v1.json. Built by design/fonts/build_fonts.py."""
import glob, hashlib, json, os, re, subprocess, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "design", "fonts")
sys.path.insert(0, FONTS)
import build_fonts as bf  # noqa: E402  (also installs the brotli stand-in when needed)


def read(p, mode="r"):
    with open(p, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()


REG = bf.registry()


class Registry(unittest.TestCase):
    def test_every_country_pack_language_is_an_interface_language_or_in_a_wave(self):
        """Every country opens in a supported interface language; every official language not yet supported is scheduled in a wave."""
        waves = json.loads(read(os.path.join(ROOT, "design", "fonts", "language_waves.v1.json")))
        planned = {l["code"] for w in waves["waves"] for l in w["languages"]} | {l["code"] for l in waves["planned"]}
        for p in glob.glob(os.path.join(ROOT, "contract", "country-packs", "*.json")):
            pack = json.loads(read(p))
            self.assertIn(pack.get("ui_language", pack.get("languages", ["en"])[0]), REG["languages"], f"{os.path.basename(p)}: opens in an unsupported interface language")
            for lang in pack.get("languages", []):
                self.assertTrue(lang in REG["languages"] or lang in planned, f"{os.path.basename(p)}: {lang} is neither an interface language nor in a wave (run tools/country_packs.py)")
    def test_registry_is_consistent(self):
        for code, L in REG["languages"].items():
            self.assertIn(L["script"], REG["scripts"], code)
            for k in ("name", "native", "sample", "letters"):
                self.assertTrue(L[k], f"{code}: {k}")
        for s, v in REG["scripts"].items():
            self.assertIn(v["dir"], ("ltr", "rtl"))
            for role in ("heading", "body"):
                self.assertIn(v[role], REG["families"], f"{s} {role}")

    def test_right_to_left_scripts(self):
        self.assertEqual({s for s, v in REG["scripts"].items() if v["dir"] == "rtl"}, {"arabic", "hebrew"})
        css = read(os.path.join(ROOT, "design", "generated", "tokens.css")) + read(os.path.join(ROOT, "design", "fonts.css"))
        for code, L in REG["languages"].items():
            if REG["scripts"][L["script"]]["dir"] == "rtl":
                self.assertIn(f"lang({code})", css, code)

    def test_token_font_stacks_name_every_family(self):
        fonts = json.loads(read(os.path.join(ROOT, "design", "tokens.v1.json")))["fonts"]
        for s in REG["scripts"].values():
            self.assertIn(f"'{REG['families'][s['heading']]['name']}'", fonts["heading"])
            self.assertIn(f"'{REG['families'][s['body']]['name']}'", fonts["body"])


class Files(unittest.TestCase):
    def test_every_file_exists_is_woff2_and_matches_its_source(self):
        rec = json.loads(read(os.path.join(FONTS, "sources.json")))
        self.assertTrue(rec["upstream_commit"])
        expected = {bf.filename(f, s) for f, s, _, _ in bf.faces(REG)}
        self.assertEqual(set(rec["outputs"]), expected)
        self.assertEqual({os.path.basename(p) for p in glob.glob(os.path.join(FONTS, "*.woff2"))}, expected)
        for f, v in rec["outputs"].items():
            b = read(os.path.join(FONTS, f), "rb")
            self.assertEqual(b[:4], b"wOF2", f)
            self.assertEqual(hashlib.sha256(b).hexdigest(), v["sha256"], f"{f} changed: rebuild with build_fonts.py")

    def test_every_language_letter_is_in_its_fonts(self):
        from fontTools.ttLib import TTFont
        cmaps = {}
        for fam, sub, _, script in bf.faces(REG):        # a browser merges every file of one family (unicode-range), so coverage is per family
            cmaps.setdefault(fam, set()).update(TTFont(os.path.join(FONTS, bf.filename(fam, sub))).getBestCmap())
        for code, L in REG["languages"].items():
            s = REG["scripts"][L["script"]]
            for role in ("heading", "body"):
                have = cmaps[s[role]]
                missing = [c for c in L["letters"] + L["sample"] + L["native"] if not c.isspace() and ord(c) > 0x7F and ord(c) not in have]
                self.assertEqual(missing, [], f"{code} {role}")

    def test_budgets(self):
        b = REG["budgets_kb"]
        latin = sum(os.path.getsize(os.path.join(FONTS, f)) for f in ("inter-latin.woff2", "montserrat-latin.woff2"))
        self.assertLessEqual(latin, b["latin_first_load"] * 1024)
        self.assertEqual(b["latin_first_load"], json.loads(read(os.path.join(ROOT, "design", "tokens.v1.json")))["fonts"]["first_load_budget_kb"])
        for script, v in REG["scripts"].items():
            if "slices" in v:           # a sliced CJK script: the base file within per_script, every slice within per_slice (loaded only when used)
                for f, s, _, sc in bf.faces(REG):
                    if sc == script:
                        self.assertLessEqual(os.path.getsize(os.path.join(FONTS, bf.filename(f, s))), b["per_slice" if not s.endswith("-base") else "per_script"] * 1024, s)
                continue
            size = sum(os.path.getsize(os.path.join(FONTS, bf.filename(f, s))) for f, s, _, sc in bf.faces(REG) if sc == script and not s.endswith("-ext"))
            self.assertLessEqual(size, b["per_script"] * 1024, script)

    def test_licences_are_kept(self):
        for fam in REG["families"]:
            self.assertIn("SIL OPEN FONT LICENSE", read(os.path.join(FONTS, "LICENSES", f"{fam}-OFL.txt")).upper(), fam)

    def test_generated_css_and_typescript_are_current(self):
        before = {p: read(p) for p in (bf.CSS_PATH, bf.TS_PATH)}
        bf.write_css(REG); bf.write_ts(REG)
        for p, txt in before.items():
            self.assertEqual(read(p), txt, f"{p} was out of date: run python3 design/fonts/build_fonts.py --css-only")

    def test_no_font_is_loaded_from_another_site(self):
        bad = re.compile(r"fonts\.googleapis|fonts\.gstatic|use\.typekit|fonts\.bunny|cdnfonts")
        for base, dirs, names in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "dist", ".build", "__pycache__", "target", "vendor")]
            for n in names:
                if n.endswith((".css", ".html", ".ts", ".js", ".mjs", ".py", ".kt", ".swift", ".json")) and n != os.path.basename(__file__):
                    self.assertIsNone(bad.search(read(os.path.join(base, n))), os.path.join(base, n))


if __name__ == "__main__":
    unittest.main()
