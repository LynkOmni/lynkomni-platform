"""Every emulator ships a real, current language pack for every language (owner request 2026-11-06).

Packs are made by the MADLAD-400 engine in the "translation" workflow (tools/translation/build_packs.py) and committed to
web/emulators/<id>/i18n/. This test needs no engine: it checks that each pack exists, was made from the current English,
came from the real engine (not the sandbox), has the language's writing direction, and kept every protected part
(brand, product and provider names, {placeholders}, numbers) exactly."""
import glob, json, os, unittest
from services import translation as t

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = sorted(glob.glob(os.path.join(ROOT, "web", "emulators", "*", "strings.en.json")))


class LanguagePacks(unittest.TestCase):
    def test_there_is_screen_text_to_translate(self):
        self.assertTrue(SOURCES)

    def test_every_language_has_a_current_pack_from_the_real_engine(self):
        for src in SOURCES:
            catalog = json.load(open(src, encoding="utf-8"))
            fresh = t.build_pack(catalog, "en")["source_sha256"]
            for lang in t.languages():
                with self.subTest(emulator=os.path.basename(os.path.dirname(src)), lang=lang):
                    path = os.path.join(os.path.dirname(src), "i18n", f"{lang}.json")
                    self.assertTrue(os.path.isfile(path), "missing: run the translation workflow and commit its packs")
                    pack = json.load(open(path, encoding="utf-8"))
                    self.assertEqual(pack["source_sha256"], fresh, "made from older English: run the translation workflow")
                    self.assertEqual(pack["dir"], t._dir(lang))
                    self.assertEqual(set(pack["texts"]), set(catalog))
                    if lang == "en":
                        self.assertEqual(pack["texts"], catalog)
                        continue
                    self.assertEqual(pack["engine"], t.MadladTranslator.name)
                    for k, en in catalog.items():
                        _, tokens = t.protect(en)
                        for tok in tokens:
                            self.assertEqual(pack["texts"][k].count(tok), en.count(tok), f"{k}: {tok!r} changed")
                    self.assertLessEqual(len(pack["kept_in_english"]), len(catalog) // 10, "too much left in English")


if __name__ == "__main__":
    unittest.main()
