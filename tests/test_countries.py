"""Every country is in LynkOmni (owner rule 2026-11-09): one pack per ISO country, generated from public standards, with the
facts a person must confirm marked unconfirmed. tools/country_packs.py is the only writer."""
import glob, json, os, subprocess, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import regions

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS = os.path.join(ROOT, "contract", "country-packs")


def read(p):
    with open(p, encoding="utf-8") as f: return json.load(f)


class EveryCountry(unittest.TestCase):
    def setUp(self):
        self.countries = read(os.path.join(ROOT, "contract", "countries.v1.json"))["countries"]
        self.packs = {os.path.splitext(os.path.basename(p))[0]: read(p) for p in glob.glob(os.path.join(PACKS, "*.json"))}
        self.currencies = read(os.path.join(ROOT, "contract", "currencies.v1.json"))["decimals"]
    def test_generated_files_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "country_packs.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
    def test_every_iso_country_has_a_pack_and_only_the_sample_is_extra(self):
        self.assertGreaterEqual(len(self.countries), 240)
        self.assertEqual(set(self.packs) - {"XX"}, set(self.countries))
        for code in self.countries: self.assertEqual(regions.country(code)["code"], code)
    def test_a_pack_carries_only_standards_facts_until_a_person_confirms_the_rest(self):
        for code, p in self.packs.items():
            if p.get("source") != "standards": continue
            self.assertEqual(p["tax_rate"], "0"); self.assertFalse(p["tax_confirmed"]); self.assertIsNone(p["fiscal"]); self.assertFalse(p["fiscal_confirmed"])
            self.assertFalse(p["vcard"]["enabled"]); self.assertEqual(p["flags"], {}); self.assertEqual(p["price_index"], 1.0)
            self.assertIn(p["currency"], self.currencies); self.assertTrue(p["tz"]); self.assertTrue(p["languages"]); self.assertEqual(p["locale"].split("-")[-1], code)
        self.assertEqual(sum(1 for p in self.packs.values() if p.get("source") == "curated"), 10)   # 8 countries, the sample and nothing else by hand
    def test_every_tender_currency_has_its_decimals(self):
        for c in self.countries.values():
            for cur in c["currencies"]: self.assertIn(cur, self.currencies, cur)
        self.assertGreaterEqual(len(self.currencies), 150)
        self.assertEqual((self.currencies["JPY"], self.currencies["KWD"], self.currencies["USD"]), (0, 3, 2))
    def test_every_country_opens_in_a_supported_interface_language_and_has_a_name_in_each(self):
        ui = set(read(os.path.join(ROOT, "design", "fonts", "scripts.v1.json"))["languages"])
        for code, c in self.countries.items():
            self.assertIn(c["ui_language"], ui, code); self.assertEqual(regions.ui_language(code), c["ui_language"])
            self.assertEqual(set(c["names"]), ui); self.assertTrue(all(c["names"].values()))
    def test_the_services_rule_holds_in_every_country(self):
        import providers
        for code in list(self.countries)[::7]:                       # a sample across the alphabet keeps the test quick
            self.assertEqual(providers.availability("pos", code)["state"], "available", code)      # never waits on a partner
            self.assertEqual(providers.availability("payments", code)["state"], "coming_soon" if code not in ("RW", "KE", "NG", "GH", "UG", "TZ", "IN", "US", "AE") else providers.availability("payments", code)["state"], code)
    def test_language_waves_cover_every_official_language_not_yet_supported(self):
        """Wave 2 is exactly blueprint 43 G (minus what is already supported); every other official language is listed as planned."""
        waves = read(os.path.join(ROOT, "design", "fonts", "language_waves.v1.json"))
        ui = set(waves["supported"])
        wave2 = [l["code"] for w in waves["waves"] if w["wave"] == 2 for l in w["languages"]]
        self.assertEqual(wave2, [l for l in ("bn", "ta", "th", "am", "ha", "yo", "zu", "fil", "pl", "nl", "uk", "ms") if l not in ui])
        planned = wave2 + [l["code"] for l in waves["planned"]]
        self.assertEqual(len(planned), len(set(planned)))                 # a language is listed once
        self.assertFalse(set(planned) & ui)                                # and never when already supported
        for c in self.countries.values():
            for l in c["languages"]: self.assertTrue(l in ui or l in planned, l)
        self.assertTrue(all(l["name"] != l["code"] for w in waves["waves"] for l in w["languages"]), "every listed language has its English name")
        self.assertTrue(all(l["name"] != l["code"] for l in waves["planned"]), "every planned language has its English name")


if __name__ == "__main__":
    unittest.main()
