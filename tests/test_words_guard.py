"""No screen ever shows a raw word name such as "ppl_at_way_whatsapp" (owner report 2026-11-19: the LynkQueue phone page showed
two, because it borrowed LynkAttend's words and the page builder left LynkAttend's words out). For every emulator: every word
name its own code, or any code it imports, writes out must be packed into that emulator's file, in English and in every
language pack it carries. Runs without a browser, so it runs in every check."""
import os, re, unittest
from web.emulators import build_data as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMULATORS = sorted(d for d in os.listdir(os.path.join(ROOT, "web", "emulators")) if os.path.isfile(os.path.join(ROOT, "web", "emulators", d, "app.ts")))
IMPORT = re.compile(r'^import\s+(?!type\b)[^;]*?from\s+"[./]*(?:ts/src/)?([a-z]+)\.js";', re.M)
LITERAL = re.compile(r"[\"'`]([a-z][a-z0-9]*_[a-z0-9_]+)[\"'`]")


def imported_sources(emulator):
    """The emulator's app.ts and every TypeScript module it imports, directly or through another module."""
    seen, todo, out = set(), [os.path.join(ROOT, "web", "emulators", emulator, "app.ts")], []
    while todo:
        path = todo.pop()
        if path in seen or not os.path.isfile(path):
            continue
        seen.add(path)
        with open(path, encoding="utf-8") as f:
            src = f.read()
        out.append(src)
        todo += [os.path.join(ROOT, "ts", "src", f"{n}.ts") for n in IMPORT.findall(src)]
    return "\n".join(out)


def word_names(emulator):
    """Every word name in the word lists this page carries: its own and the shared lists it uses (a code that merely looks like a
    word name elsewhere, such as the payment method "bank_transfer", is data, not a word on screen)."""
    import json
    names = set()
    folders = [os.path.join(ROOT, "web", "emulators", emulator)] + [os.path.join(ROOT, f) for f in B.shared_folders(emulator)]
    for folder in folders:
        p = os.path.join(folder, "strings.en.json")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                names |= set(json.load(f))
    return names


class WordsGuard(unittest.TestCase):
    def test_every_word_a_page_uses_is_packed_into_it(self):
        missing = {}
        for emu in EMULATORS:
            used = set(B.imported_literals(emu)) & word_names(emu)
            packs = B.language_packs(emu)
            for lang, pack in packs.items():
                gone = sorted(used - set(pack["texts"]))
                if gone:
                    missing[f"{emu} ({lang})"] = gone
        self.assertEqual(missing, {}, "\n".join(f"{k}: {v[:8]}{' ...' if len(v) > 8 else ''}" for k, v in missing.items()))


if __name__ == "__main__":
    unittest.main()
