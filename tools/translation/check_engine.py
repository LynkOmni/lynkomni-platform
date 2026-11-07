#!/usr/bin/env python3
"""Checks the installed MADLAD-400 engine in every language (the engine for text people type: chat, product names).

    LYNK_MT_DIR=/path/to/engine python tools/translation/check_engine.py [report.json]

Screen text is NOT made here: Claude translates it (tools/translation/claude_packs.py, owner decision 2026-11-07).
This check fails if the engine lacks a language. For each language it also translates sample sentences full of names,
{placeholders} and numbers through services/translation.run (protected parts, no repetition, no added words or
sentences, round trip back to English) and reports how many pass; refused text is shown to people in the original.
Run by the "translation" workflow, which uploads the report."""
import json, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from services import translation as t  # noqa: E402

SAMPLES = [
    "Pay {amount} with MTN MoMo",
    "Do you still have rice in stock?",
    "LynkPOS sent receipt {number} to {phone}.",
    "No internet. The sale is saved and will be sent when you are back online.",
    "Thank you for using LynkOmni.",
    "I will come to the shop tomorrow at 3.",
]


def main(report_path):
    engine = t.MadladTranslator()
    report, missing = {"engine": engine.name, "revision": engine.revision, "languages": {}}, []
    for lang in t.languages():
        if lang == "en":
            continue
        if not engine.has_language(lang):
            missing.append(lang)
            continue
        start = time.time()
        res = t.run(engine, SAMPLES, "en", lang)
        report["languages"][lang] = {"passed": sum(1 for r in res if not r[1]), "of": len(SAMPLES), "seconds": round(time.time() - start, 1),
                                     "results": [{"en": s, "text": r[0], "refused": r[1], "round_trip": round(r[2], 2)} for s, r in zip(SAMPLES, res)]}
        print(f"{lang}: {report['languages'][lang]['passed']} of {len(SAMPLES)} pass", flush=True)
    report["missing_languages"] = missing
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    if missing:
        print("FAIL: the engine has no language tag for", ", ".join(missing))
        return 1
    print("every language is known to the engine (see the report for quality)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "translation-report.json"))
