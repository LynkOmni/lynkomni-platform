#!/usr/bin/env python3
"""Builds every language pack with the real translation engine and checks the engine in every language.

    LYNK_MT_DIR=/path/to/engine python tools/translation/build_packs.py [report.json]

For every emulator with a web/emulators/<id>/strings.en.json, writes web/emulators/<id>/i18n/<lang>.json for every
language in design/fonts/scripts.v1.json (English included, as the source). Then checks, and fails if any check fails:
  1. the engine knows every language's tag;
  2. sample sentences full of names, {placeholders} and numbers pass every check of services/translation.run (protected
     parts, no repetition, no added words, round trip back to English), in every language;
  3. each translated pack is written in its own script (an Arabic pack has Arabic letters, and so on), so the engine did
     not just copy the English;
  4. no pack keeps more than a few texts in English (texts the engine damaged are kept in English, never shown broken).
Run by the "translation" workflow; the report is uploaded with the packs."""
import glob, json, os, sys, time, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from services import translation as t  # noqa: E402

SAMPLES = {
    "pay": "Pay {amount} with MTN MoMo",
    "items": "You have 3 items in the basket.",
    "sent": "LynkPOS sent receipt {number} to {phone}.",
    "offline": "No internet. The sale is saved and will be sent when you are back online.",
    "brand": "Thank you for using LynkOmni.",
}
SCRIPT_WORD = {"arabic": "ARABIC", "hebrew": "HEBREW", "devanagari": "DEVANAGARI"}
MAX_KEPT = 0.10          # at most 10% of a pack may stay in English
ALIASES = {"he": ["iw"], "yi": ["ji"], "fa": ["pes", "prs"], "ckb": ["ku"], "ug": ["uig"], "hi": [], "sd": [], "ps": ["pbt"]}
PROBE = "Thank you for your purchase. Your receipt is ready."


def in_script(text, word):
    return any(unicodedata.name(c, "").startswith(word) for c in text)


def main(report_path):
    engine = t.MadladTranslator()
    langs = t.languages()
    failures, report = [], {"engine": engine.name, "revision": engine.revision, "languages": {}}
    for lang in langs:
        if not engine.has_language(lang):
            failures.append(f"{lang}: engine has no tag <2{t.mt_code(lang)}>")
    if failures:
        tags = sorted(p for p in (engine.sp.id_to_piece(i) for i in range(engine.sp.get_piece_size())) if p.startswith("<2") and p.endswith(">"))
        report["engine_tags"] = tags
        return finish(report, failures, report_path)

    for path in sorted(glob.glob(os.path.join(ROOT, "web", "emulators", "*", "strings.en.json"))):
        catalog = json.load(open(path, encoding="utf-8"))
        out_dir = os.path.join(os.path.dirname(path), "i18n")
        os.makedirs(out_dir, exist_ok=True)
        emu = os.path.basename(os.path.dirname(path))
        for lang, L in langs.items():
            start = time.time()
            why = {}
            pack = t.build_pack(catalog, lang, engine, reasons=why)
            with open(os.path.join(out_dir, f"{lang}.json"), "w", encoding="utf-8") as f:
                json.dump(pack, f, indent=1, ensure_ascii=False, sort_keys=True)
                f.write("\n")
            if lang == "en":
                continue
            r = report["languages"].setdefault(lang, {})
            word = SCRIPT_WORD.get(L["script"])
            translated = [k for k in catalog if k not in pack["kept_in_english"]]
            wrong_script = [k for k in translated if word and not in_script(pack["texts"][k], word) and any(c.isalpha() for c in pack["texts"][k])]
            r[emu] = {"kept_in_english": why, "wrong_script": wrong_script, "seconds": round(time.time() - start, 1)}
            if len(pack["kept_in_english"]) > MAX_KEPT * len(catalog):
                failures.append(f"{emu}/{lang}: {len(pack['kept_in_english'])} of {len(catalog)} texts kept in English")
            if word and len(wrong_script) > MAX_KEPT * len(catalog):
                failures.append(f"{emu}/{lang}: {len(wrong_script)} texts not written in {L['script']} script")
            print(f"{emu} {lang}: kept {len(pack['kept_in_english'])}, wrong script {len(wrong_script)}, {r[emu]['seconds']} s", flush=True)

    for lang in langs:
        if lang == "en":
            continue
        out, kept = t.translate_catalog(SAMPLES, lang, engine)
        report["languages"][lang]["samples"] = out
        report["languages"][lang]["samples_kept"] = dict(kept)
        for k, why in kept:
            failures.append(f"sample {k} in {lang}: {why}")
    weak = sorted({f.split("/")[1].split(":")[0] for f in failures if "script" in f})
    if weak:
        tags = [engine.sp.id_to_piece(i) for i in range(engine.sp.get_piece_size())]
        tags = [p for p in tags if p.startswith("<2") and p.endswith(">")]
        report["probe"] = {}
        for lang in weak:
            want = {t.mt_code(lang), lang, *ALIASES.get(lang, [])}
            cands = [p for p in tags if p[2:-1].split("_")[0].split("-")[0] in want]
            report["probe"][lang] = {c: engine.model.translate_batch([engine.sp.encode(f"{c} {PROBE}", out_type=str)], beam_size=4)[0].hypotheses[0] for c in cands}
            report["probe"][lang] = {c: engine.sp.decode(v) for c, v in report["probe"][lang].items()}
            print("probe", lang, json.dumps(report["probe"][lang], ensure_ascii=False), flush=True)
    return finish(report, failures, report_path)


def finish(report, failures, report_path):
    report["failures"] = failures
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    for line in failures:
        print("FAIL", line)
    print("all languages pass" if not failures else f"{len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "translation-report.json"))
