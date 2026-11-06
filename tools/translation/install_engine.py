#!/usr/bin/env python3
"""Installs the LynkOmni translation engine ONCE into a local folder (used as LYNK_MT_DIR).

Engine: Google MADLAD-400-3B-MT, Apache 2.0 licence (commercial use allowed), converted to CTranslate2 with int8 weights.
This is the only place that downloads anything; the apps and services never download the model while running.

    pip install ctranslate2 sentencepiece huggingface_hub "transformers<5" torch   (torch and transformers: conversion only)
    python tools/translation/install_engine.py /path/to/engine

Steps: look up the exact model revision and refuse it unless its licence is Apache 2.0; download only the weight and
tokenizer files of that revision; convert to CTranslate2 int8; write engine.json (model, revision, licence, file hashes)
so every language pack can say exactly which engine made it. The weights are about 12 GB to download and 3 GB once
converted, so this runs on a build machine (GitHub Actions, workflow "translation"), never on a phone."""
import hashlib, json, os, sys

MODEL = "google/madlad400-3b-mt"
LICENCE = "apache-2.0"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main(out):
    from huggingface_hub import HfApi, snapshot_download
    info = HfApi().model_info(MODEL)
    licence = (info.card_data or {}).get("license") if isinstance(info.card_data, dict) else getattr(info.card_data, "license", None)
    if licence != LICENCE:
        sys.exit(f"refused: {MODEL} licence is {licence!r}, LynkOmni needs {LICENCE!r} (commercial use)")
    src = snapshot_download(MODEL, revision=info.sha, allow_patterns=["*.json", "*.safetensors", "spiece.model"])
    from ctranslate2.converters import TransformersConverter
    TransformersConverter(src, copy_files=["spiece.model"], load_as_float16=True, low_cpu_mem_usage=True).convert(out, quantization="int8", force=True)
    files = {f: sha256(os.path.join(out, f)) for f in sorted(os.listdir(out)) if f != "engine.json"}
    with open(os.path.join(out, "engine.json"), "w", encoding="utf-8") as f:
        json.dump({"engine": "madlad400-3b-mt-ct2-int8", "model": MODEL, "revision": info.sha, "licence": licence,
                   "quantization": "int8", "files_sha256": files}, f, indent=1)
    print(f"installed {MODEL}@{info.sha} ({licence}) into {out}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(os.path.abspath(sys.argv[1]))
