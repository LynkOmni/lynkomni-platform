"""Translation works offline (owner request 2026-11-06): screen text ships as ahead-of-time language packs; typed text is
translated online, cached, and shown in the original with 'queued' when offline. The MADLAD-400 engine is never fetched at run time."""
import os, unittest
from services import translation as t

CAT = {"done": "Sale complete", "pay": "Pay {amount} with MTN MoMo", "count": "3 items"}


class Engine(t.Translator):
    name = "test"
    def __init__(s): s.calls = 0
    def translate(s, texts, source, target):
        s.calls += 1
        return ["<" + x + ">" for x in texts]


class Offline(unittest.TestCase):
    def test_every_language_has_an_engine_code(self):
        for lang in t.languages():
            self.assertRegex(t.mt_code(lang), r"^[a-z]{2,3}(_[A-Za-z]+)?$", lang)  # MADLAD-400 tags: <2zh>, <2zh_Hant>

    def test_engines_that_see_plain_names_must_return_every_protected_part(self):
        class Plain(t.Translator):
            name, plain_tokens = "plain", True
            def __init__(s, out): s.out = out
            def translate(s, texts, source, target): return [s.out]
        src = "Pay {amount} with MTN MoMo, 3 items"
        class Echo(Plain):    # its "translation back to English" is the English itself, so the round trip matches
            def translate(s, texts, source, target): return [src] if target == "en" else [s.out]
        self.assertEqual(t.run(Echo("Payer {amount} avec MTN MoMo, ٣ articles"), [src], "en", "fr")[0][:2], ("Payer {amount} avec MTN MoMo, 3 articles", None))
        self.assertIsNotNone(t.run(Plain("Payer {montant} avec MTN MoMo, 3 articles"), [src], "en", "fr")[0][1])
        self.assertIsNotNone(t.run(Plain("Payer {amount} avec MoMo, 3 articles"), [src], "en", "fr")[0][1])

    def test_repeated_padded_or_drifted_translations_are_refused(self):
        class Fixed(t.Translator):
            name, plain_tokens = "fixed", True
            def __init__(s, out, back): s.out, s.back = out, back
            def translate(s, texts, source, target): return [s.back if target == "en" else s.out]
        self.assertIn("repeats", t.run(Fixed("Synchro Synchro", "Sync"), ["Sync"], "en", "fr")[0][1])
        self.assertIn("longer", t.run(Fixed("Tout le monde est membre d'un grand parti politique", "All"), ["All"], "en", "fr")[0][1])
        self.assertIn("adds a sentence", t.run(Fixed("Le panier est vide. Ajoutez un produit.", "x"), ["The basket is empty"], "en", "fr")[0][1])
        self.assertIn("drifted", t.run(Fixed("Tout le monde", "Everyone"), ["All"], "en", "fr")[0][1])
        self.assertEqual(t.run(Fixed("Vente terminée", "Sale complete"), ["Sale complete"], "en", "fr")[0][:2], ("Vente terminée", None))

    def test_language_packs_carry_direction_and_protect_names_numbers_placeholders(self):
        ar = t.build_pack(CAT, "ar")
        self.assertEqual(ar["dir"], "rtl")
        self.assertIn("{amount}", ar["texts"]["pay"])
        self.assertIn("MTN MoMo", ar["texts"]["pay"])
        self.assertIn("3", ar["texts"]["count"])
        self.assertEqual(t.build_pack(CAT, "en")["texts"], CAT)
        self.assertEqual(ar["source_sha256"], t.build_pack(CAT, "fr")["source_sha256"])
        self.assertNotEqual(ar["source_sha256"], t.build_pack({**CAT, "x": "New"}, "fr")["source_sha256"])

    def test_typed_text_offline_shows_the_original_queued(self):
        c = t.ContentTranslator(Engine())
        r = c.show("Do you have rice?", "en", "fr", online=False)
        self.assertEqual((r["text"], r["translated"], r["state"]), ("Do you have rice?", False, "queued"))

    def test_typed_text_online_is_translated_once_then_cached_for_offline(self):
        e = Engine(); c = t.ContentTranslator(e)
        self.assertTrue(c.show("Do you have rice?", "en", "fr", online=True)["translated"])
        r = c.show("Do you have rice?", "en", "fr", online=False)
        self.assertTrue(r["translated"]); self.assertEqual(e.calls, 1)

    def test_a_broken_translation_is_never_shown(self):
        class Broken(t.Translator):
            name = "broken"
            def translate(s, texts, source, target): return ["oops" for _ in texts]
        r = t.ContentTranslator(Broken()).show("Pay {amount}", "en", "fr", online=True)
        self.assertEqual((r["text"], r["state"]), ("Pay {amount}", "failed"))

    def test_the_real_engine_never_downloads_at_run_time(self):
        os.environ.pop("LYNK_MT_DIR", None)
        with self.assertRaises(RuntimeError):
            t.MadladTranslator()
        src = open(t.__file__, encoding="utf-8").read()
        self.assertNotRegex(src, r"https?://|from_pretrained|hf_hub_download")


if __name__ == "__main__":
    unittest.main()
