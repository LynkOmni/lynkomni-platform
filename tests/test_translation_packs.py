"""Every emulator ships a real, current language pack for every language (owner request 2026-11-06).

Screen-text packs are translated by Claude (owner decision 2026-11-07) and written by tools/translation/claude_packs.py
into web/emulators/<id>/i18n/. This test checks that each pack exists, was made from the current English, is a real
translation (not the sandbox), has the language's writing direction, keeps every protected part (brand, product and
provider names, {placeholders}, numbers) exactly, passes every automatic check (no repetition, no added words or
sentences), is written in its own script, and leaves nothing in English."""
import glob, json, os, unittest
from services import translation as t

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = sorted(glob.glob(os.path.join(ROOT, "web", "emulators", "*", "strings.en.json"))) + [os.path.join(ROOT, "web", d, "strings.en.json") for d in ("shell", "pos", "footer", "tracking")]   # the shared shell, POS, footer and tracker words too


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
                    self.assertTrue(pack["engine"].startswith("claude-"), pack["engine"])
                    self.assertEqual(pack["kept_in_english"], [])
                    for k, en in catalog.items():
                        text = pack["texts"][k]
                        _, tokens = t.protect(en)
                        for tok in tokens:
                            self.assertEqual(text.count(tok), en.count(tok), f"{k}: {tok!r} changed")
                        self.assertIsNone(t.problems(en, text), f"{k}: {text!r}")
                        self.assertTrue(t.in_own_script(text, lang), f"{k}: {text!r}")


if __name__ == "__main__":
    unittest.main()
