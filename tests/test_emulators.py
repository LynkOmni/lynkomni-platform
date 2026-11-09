"""Interface emulators (web/emulators): built, offline, on-brand and honest.
Each emulator is one self-contained HTML file. These checks keep them that way."""
import glob, json, os, re, shutil, subprocess, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUDGETS = json.load(open(os.path.join(ROOT, "web", "budgets.v1.json"), encoding="utf-8"))   # one size budget per emulator
WEB = os.path.join(ROOT, "web", "emulators")
SOURCES = [f for d in sorted(glob.glob(os.path.join(WEB, "*", ""))) if not d.rstrip("/").endswith("dist") for f in sorted(glob.glob(os.path.join(d, "*"))) if f.endswith((".ts", ".css", ".html"))]
BUILT = sorted(glob.glob(os.path.join(WEB, "dist", "*.html")))
FAKE_MARKS = re.compile(r"\b(visa|mastercard|amex|mtn|airtel|m-pesa|mpesa|paypal|apple pay|google pay|sunmi|pax|ingenico|verifone)\b", re.I)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def built_data(p):
    """The DATA of a built emulator with its compressed part (web/build.mjs packData) unpacked, as the browser sees it."""
    import base64, zlib
    d = json.loads(re.search(r"const DATA = (\{.*?\});\n", read(p), re.S).group(1))
    x = json.loads(zlib.decompress(base64.b64decode(d.pop("Z")), -15))
    return {**d, **x, "i18n": {**d["i18n"], **x["i18n"]}}


def built_text(p):
    """The built file with its compressed data written out in full, so every scan below also sees the packed words and pictures."""
    return read(p) + "\n" + json.dumps(built_data(p), ensure_ascii=False)


class Emulators(unittest.TestCase):
    def test_every_emulator_is_built(self):
        ids = sorted(os.path.basename(os.path.dirname(f)) for f in SOURCES if f.endswith("shell.html"))
        self.assertTrue(ids)
        for i in ids:
            self.assertTrue(os.path.isfile(os.path.join(WEB, "dist", f"lynkomni-{i}.html")), f"run node web/build.mjs for {i}")

    def test_identifiers_in_emulators_come_only_from_the_registry(self):
        """Every public id an emulator shows uses a type from core/ids.py (never an invented prefix such as LOSEC-; fixed in build section 2)."""
        from core.ids import TYPES
        for f in SOURCES + [p for p in glob.glob(os.path.join(WEB, "*", "strings.en.json"))]:
            for m in set(re.findall(r"\bLO([A-Z]{2,5})-", read(f))):
                self.assertIn(m, TYPES, f"{f}: LO{m}- is not a registered identifier type")

    def test_country_chooser_opens_on_the_sample_country_and_lists_every_pack(self):
        """Step 0 (blueprint 42 A): emulators are built for no country. The chooser lists every country pack with the neutral
        sample pack first, and no country code is written into an emulator's source."""
        import json
        packs = sorted(os.path.splitext(f)[0] for f in os.listdir(os.path.join(ROOT, "contract", "country-packs")) if f.endswith(".json"))
        for f in BUILT:
            data = built_data(f)
            self.assertEqual(data["packOrder"][0], "XX", f); self.assertTrue(data["packs"]["XX"]["sample"])
            self.assertEqual(sorted(data["packs"]), packs, f)
        for src in SOURCES:
            self.assertNotRegex(read(src), r"\b(Rwanda|Kenya|Nigeria|Ghana|Uganda|Tanzania|India|RWF|KES|NGN)\b", src)

    def test_sources_use_tokens_only(self):
        for f in SOURCES:
            txt = read(f)
            self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,8}\b(?![\w-])", re.sub(r"&#\d+;", "", txt)) if f.endswith(".css") else None, f"{f}: hex colour, use a token")
            self.assertNotRegex(txt, r"\brgba?\(|\bhsla?\(", f"{f}: colour function, use a token")
            self.assertNotIn("7C4DFF", txt.upper(), f)

    def test_every_css_variable_is_a_real_token(self):
        """A misspelled or invented token silently falls back to another colour (found in build section 3: --text-on-brand
        gave dark text on the brand colour in the dark theme). Every var(--x) must be a design token, set in the same file,
        or one of the values the runtime sets (RUNTIME_VARS)."""
        tokens = set(re.findall(r"(--[\w-]+)\s*:", read(os.path.join(ROOT, "design", "generated", "tokens.css"))))
        RUNTIME_VARS = {"--fit"}   # emulator.ts fitToWidth: how much a device is shown smaller to fit the window
        files = SOURCES + glob.glob(os.path.join(ROOT, "web", "device", "*.css")) + glob.glob(os.path.join(ROOT, "web", "shell", "*.css")) + [os.path.join(ROOT, "ts", "src", "emulator.ts")]
        for f in files:
            txt = read(f); own = set(re.findall(r"(--[\w-]+)\s*:", txt))
            unknown = set(re.findall(r"var\((--[\w-]+)", txt)) - tokens - own - RUNTIME_VARS
            self.assertEqual(unknown, set(), f"{f}: not a design token")

    def test_no_fake_provider_or_maker_marks(self):
        for f in SOURCES:
            m = FAKE_MARKS.search(read(f))
            self.assertIsNone(m, f"{f}: {m and m.group(0)} (never show provider or device-maker names or marks)")

    def test_built_files_are_offline_and_honest(self):
        self.assertTrue(BUILT)
        for f in BUILT:
            txt = built_text(f)
            urls = set(re.findall(r"https?://[^\s\"')<\\]+", txt)) - {"http://www.w3.org/2000/svg", "http://www.w3.org/1999/xlink"}
            urls = {u for u in urls if not re.match(r"https://([a-z]+\.)?lynkomni\.com(/|\$|$)", u)}   # LynkOmni addresses may be shown (address bar, deep links), never loaded
            self.assertEqual(urls, set(), f"{f}: must not load anything from the web")
            self.assertNotRegex(txt, r"""(src|href)=["']https?://|url\(["']?https?://|fetch\(|XMLHttpRequest|navigator\.sendBeacon""", f"{f}: must not load anything from the web")
            self.assertNotRegex(txt, r"<img|@import|fonts\.googleapis|<link ", f)
            self.assertIn("Draft design", txt, f"{f}: must say it is a draft until a designer reviews it")
            self.assertNotRegex(txt.lower(), r"todo image|lorem ipsum", f)
            budget = BUDGETS["emulators"].get(os.path.basename(f)[len("lynkomni-"):-len(".html")], {}).get("file_kb", BUDGETS["defaults"]["file_kb"])
            self.assertLess(len(read(f).encode()), budget * 1024, f"{f}: over its {budget} KB size budget (web/budgets.v1.json)")

    def test_terminal_never_claims_a_tax_receipt_or_end_to_end_encryption(self):
        txt = built_text(os.path.join(WEB, "dist", "lynkomni-pos-terminal.html")).lower()
        self.assertIn("not a tax receipt", txt)
        self.assertIn("provisional receipt", txt)
        self.assertNotIn("end-to-end", txt)

    @unittest.skipUnless(shutil.which("node") and shutil.which("tsc"), "node and tsc are needed to rebuild")
    def test_built_files_are_up_to_date(self):
        r = subprocess.run(["node", os.path.join(ROOT, "web", "build.mjs"), "--check"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
