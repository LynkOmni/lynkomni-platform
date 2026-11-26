"""Words keep their own capitals (owner, 2026-11-26).

Small letters only where a format requires them (usernames, web addresses, the domain of an email address) and capitals
only where a format requires them (codes, public ids, country codes). Everything else shows exactly as written: what a
person types keeps the capitals they typed, and translated words keep the capitals of their language. So no style may
force a case on words, and no code may change the case of a translated word to show it (comparing text in one case for a
search or a match is fine, because nothing changed is shown)."""
import glob
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lines(p):
    with open(p, encoding="utf-8") as f:
        return list(enumerate(f, 1))


def files(pattern):
    return [p for p in glob.glob(os.path.join(ROOT, pattern), recursive=True) if "/dist/" not in p and "node_modules" not in p and ".generated." not in p]


class LetterCase(unittest.TestCase):
    def test_no_style_forces_a_case_on_words(self):
        bad = []
        for p in files("web/**/*.css"):
            for n, line in lines(p):
                for m in re.finditer(r"text-transform:\s*([a-z-]+)", line):
                    if m.group(1) != "none":
                        bad.append(f"{os.path.relpath(p, ROOT)}:{n} text-transform: {m.group(1)}")
        self.assertEqual(bad, [], "words show as written: remove the forced case")

    def test_no_translated_word_has_its_case_changed_to_be_shown(self):
        bad = []
        ts_word = re.compile(r"\bt\(\s*[\"'`][^\"'`]+[\"'`][^)]*\)\s*\.\s*(toLowerCase|toUpperCase|toLocaleLowerCase|toLocaleUpperCase)\(")
        py_word = re.compile(r"\bt\(\s*\w+\s*,\s*[\"'][^\"']+[\"']\s*\)\s*\.\s*(lower|upper|title|capitalize)\(")
        for p in files("ts/src/*.ts") + files("web/emulators/*/app.ts"):
            for n, line in lines(p):
                if ts_word.search(line):
                    bad.append(f"{os.path.relpath(p, ROOT)}:{n}")
        for p in files("core/*.py") + files("services/*.py") + files("identity/*.py") + files("people/*.py"):
            for n, line in lines(p):
                if py_word.search(line):
                    bad.append(f"{os.path.relpath(p, ROOT)}:{n}")
        self.assertEqual(bad, [], "give the word its own wording in the packs instead of changing its case in code")

    def test_examples_of_free_text_start_like_a_sentence(self):
        # Examples of what a person types or says start with a capital where the language has capitals; usernames,
        # addresses and codes are not free text and keep their own format.
        for folder, key in (("web/waysin", "wy_hint_word"), ("web/emulators/merchant-phone", "voice_sample"), ("web/shell", "voice_sample_search")):
            with open(os.path.join(ROOT, folder, "strings.en.json"), encoding="utf-8") as f:
                v = json.load(f)[key]
            self.assertTrue(v[:1].isupper(), f"{folder} {key}: {v!r}")


if __name__ == "__main__":
    unittest.main()
