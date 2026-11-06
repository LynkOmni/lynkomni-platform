"""Machine translation rules (owner decision 2026-11-06): names, placeholders and numbers never change; a damaged translation
is refused and the English text is kept; every language comes from the language registry."""
import re, unittest
from services.translation import GLOSSARY, SandboxTranslator, Translator, protect, pseudo, restore, translate_catalog


class Translation(unittest.TestCase):
    def test_names_placeholders_and_numbers_are_protected(self):
        text, toks = protect("Pay {amount} with MTN MoMo on LynkPOS, 2 items, total 1,500")
        for kept in ("{amount}", "MTN MoMo", "LynkPOS", "2", "1,500"):
            self.assertIn(kept, toks)
            self.assertNotIn(kept, re.sub(r"\u27e6\d+\u27e7", "", text))
        self.assertEqual(restore(text, toks), "Pay {amount} with MTN MoMo on LynkPOS, 2 items, total 1,500")
        for brand in ("LynkOmni", "CruxOmni Group", "Visa", "Mastercard", "LynkVCard"):
            self.assertIn(brand, GLOSSARY)

    def test_a_damaged_translation_is_refused_and_english_kept(self):
        class Broken(Translator):
            def translate(self, texts, source, target):
                return [t.replace("⟦0⟧", "") for t in texts]       # drops the amount
        out, kept = translate_catalog({"change": "Change: {amount}", "done": "Sale complete"}, "fr", Broken())
        self.assertEqual(out["change"], "Change: {amount}")
        self.assertEqual([k for k, _ in kept], ["change"])

    def test_sandbox_makes_longer_accented_text_for_layout_tests(self):
        out, kept = translate_catalog({"a": "Sale complete"}, "sw", SandboxTranslator())
        self.assertEqual(kept, [])
        self.assertGreater(len(out["a"]), len("Sale complete") * 1.3)
        self.assertEqual(pseudo("Total"), "[Tötàl ~~]")

    def test_only_registry_languages(self):
        with self.assertRaises(ValueError):
            translate_catalog({"a": "Hi"}, "zz")


if __name__ == "__main__":
    unittest.main()
