#!/usr/bin/env python3
"""Writes the screen-text language packs that Claude translated (owner decision 2026-11-07).

    python tools/translation/claude_packs.py <emulator> <folder with <lang>.json files of {key: translation}>

Each input file must have exactly the keys of web/emulators/<emulator>/strings.en.json (or web/shell/strings.en.json when
the emulator is "shell": the shared shell's own words, merged into every emulator that uses the shell). Every translation passes the
automatic checks of services/translation.run (names, {placeholders} and numbers unchanged; no repetition; no added
words or sentences) and must be written in its language's script, or the tool stops and writes nothing. The packs go
to web/emulators/<emulator>/i18n/<lang>.json with engine "claude-opus-5-5" and the fingerprint of the English, so
tests/test_translation_packs.py catches any pack made from older English. When English screen text changes, Claude
translates the changed keys for every language and runs this tool again."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from services import translation as t  # noqa: E402


def main(emulator, folder):
    SHARED = {"shell": os.path.join(ROOT, "web", "shell"), "pos": os.path.join(ROOT, "web", "pos"), "footer": os.path.join(ROOT, "web", "footer"), "tracking": os.path.join(ROOT, "web", "tracking")}   # shared word packs: the shell's, the POS devices' and the footer's words
    base = SHARED.get(emulator) or os.path.join(ROOT, "web", "emulators", emulator)
    catalog = json.load(open(os.path.join(base, "strings.en.json"), encoding="utf-8"))
    table, errors = {}, []
    for lang in t.languages():
        if lang == "en":
            continue
        path = os.path.join(folder, f"{lang}.json")
        if not os.path.isfile(path):
            errors.append(f"{lang}: missing {path}")
            continue
        tr = json.load(open(path, encoding="utf-8"))
        if set(tr) != set(catalog):
            errors.append(f"{lang}: keys differ from strings.en.json: {sorted(set(tr) ^ set(catalog))}")
            continue
        table[lang] = {catalog[k]: tr[k] for k in catalog}
        for k in catalog:
            why = t.problems(catalog[k], t.ascii_digits(tr[k]).strip())
            if why:
                errors.append(f"{lang}/{k}: {why}: {tr[k]!r}")
            elif not t.in_own_script(tr[k], lang):
                errors.append(f"{lang}/{k}: not written in its own script: {tr[k]!r}")
    if errors:
        print("\n".join(errors))
        return 1
    engine = t.TableTranslator(table)
    os.makedirs(os.path.join(base, "i18n"), exist_ok=True)
    for lang in t.languages():
        why = {}
        pack = t.build_pack(catalog, lang, engine, reasons=why)
        if why:
            print(f"{lang}: refused {why}")
            return 1
        with open(os.path.join(base, "i18n", f"{lang}.json"), "w", encoding="utf-8") as f:
            json.dump(pack, f, indent=1, ensure_ascii=False, sort_keys=True)
            f.write("\n")
    print(f"wrote {len(t.languages())} packs for {emulator}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
