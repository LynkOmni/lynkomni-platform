#!/usr/bin/env python3
"""Update some translated screen texts without retyping the rest.

    python3 tools/translation/update_keys.py <emulator|shell|pos|footer> <changes.json>

changes.json is {lang: {key: translation}} with Claude's translations of new or changed English keys. Every other key keeps the
translation already in web/.../i18n/<lang>.json, so a pack is rebuilt from: the existing translations, plus these changes, minus
keys no longer in strings.en.json. The result goes through tools/translation/claude_packs.py with all its checks (names,
placeholders and numbers unchanged, no repetition, no added sentences, the language's own script); nothing is written if any
translation fails. A key whose English changed since the last commit (or is new) must be in changes.json for every
language, or the tool stops."""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from services import translation as t  # noqa: E402

SHARED = {"shell": os.path.join(ROOT, "web", "shell"), "pos": os.path.join(ROOT, "web", "pos"), "footer": os.path.join(ROOT, "web", "footer")}


def main(target, changes_path):
    base = SHARED.get(target) or os.path.join(ROOT, "web", "emulators", target)
    with open(os.path.join(base, "strings.en.json"), encoding="utf-8") as f:
        english = json.load(f)
    with open(changes_path, encoding="utf-8") as f:
        changes = json.load(f)
    rel = os.path.relpath(os.path.join(base, "strings.en.json"), ROOT)
    try:   # the English the current translations were made from: the last committed strings.en.json
        before = json.loads(subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        before = {}
    changed = {k for k in english if before.get(k) != english[k]}
    missing = []
    with tempfile.TemporaryDirectory() as tmp:
        for lang in t.languages():
            if lang == "en":
                continue
            old, old_en = {}, {}
            path = os.path.join(base, "i18n", f"{lang}.json")
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as f:
                    old = json.load(f).get("texts", {})
            out = {}
            for k in english:
                if k in changes.get(lang, {}):
                    out[k] = changes[lang][k]
                elif k in old and k not in changed:
                    out[k] = old[k]                    # unchanged English keeps its translation (the pack's fingerprint is rebuilt)
                else:
                    missing.append(f"{lang}/{k}")
            with open(os.path.join(tmp, f"{lang}.json"), "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False)
        if missing:
            print(f"{len(missing)} keys have no translation (first: {missing[:8]})")
            return 1
        return subprocess.call([sys.executable, os.path.join(ROOT, "tools", "translation", "claude_packs.py"), target, tmp])


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
