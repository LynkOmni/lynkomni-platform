#!/usr/bin/env python3
"""Makes the self-hosted WOFF2 font files that design/fonts.css names, from the official variable fonts.

Run:  python3 design/fonts/build_fonts.py --inter /path/Inter[opsz,wght].ttf --montserrat /path/Montserrat[wght].ttf
Source: github.com/google/fonts (ofl/inter, ofl/montserrat), SIL Open Font License 1.1. sources.json records the exact
commit and SHA-256 of the files used, so anyone can rebuild the same files.

What it does, per family:
  1. keeps only the weights we use (Inter 400-700, Montserrat 500-700) and pins Inter's optical size to text size;
  2. cuts one file per script group, using the unicode-range lines in fonts.css (so a page downloads only what it shows);
  3. compresses to WOFF2. When the Python brotli package is missing it uses Node's built-in Brotli encoder instead."""
import argparse, hashlib, io, json, os, re, subprocess, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.dirname(HERE)
AXES = {"inter": {"wght": (400, 700), "opsz": 14}, "montserrat": {"wght": (500, 700)}}
FAMILY = {"inter": "Inter", "montserrat": "Montserrat"}


def _node_brotli():
    """A stand-in for the brotli module (only what fontTools uses), backed by Node's zlib."""
    js_c = ("const z=require('zlib');const c=[];process.stdin.on('data',d=>c.push(d)).on('end',()=>{const b=Buffer.concat(c);"
            "process.stdout.write(z.brotliCompressSync(b,{params:{[z.constants.BROTLI_PARAM_MODE]:+process.argv[1],"
            "[z.constants.BROTLI_PARAM_QUALITY]:+process.argv[2],[z.constants.BROTLI_PARAM_SIZE_HINT]:b.length}}))})")
    js_d = "const z=require('zlib');const c=[];process.stdin.on('data',d=>c.push(d)).on('end',()=>process.stdout.write(z.brotliDecompressSync(Buffer.concat(c))))"
    m = types.ModuleType("brotli")
    m.MODE_GENERIC, m.MODE_TEXT, m.MODE_FONT = 0, 1, 2
    m.compress = lambda data, mode=0, quality=11, lgwin=22, lgblock=0: subprocess.run(["node", "-e", js_c, str(mode), str(quality)], input=data, capture_output=True, check=True).stdout
    m.decompress = lambda data: subprocess.run(["node", "-e", js_d], input=data, capture_output=True, check=True).stdout
    m.error = Exception
    return m


try:
    import brotli  # noqa: F401
except ImportError:
    sys.modules["brotli"] = _node_brotli()

from fontTools.ttLib import TTFont  # noqa: E402
from fontTools.varLib import instancer  # noqa: E402
from fontTools import subset  # noqa: E402


def ranges():
    """fonts.css -> {(family, file): [codepoints]} read from each @font-face block."""
    with open(os.path.join(DESIGN, "fonts.css"), encoding="utf-8") as f:
        css = f.read()
    out = {}
    for block in re.findall(r"@font-face\s*\{(.*?)\}", css, re.S):
        fam = re.search(r"font-family:\s*'([^']+)'", block).group(1)
        fname = re.search(r"/fonts/([\w-]+\.woff2)", block).group(1)
        cps = []
        for a, b in re.findall(r"U\+([0-9A-Fa-f]+)(?:-([0-9A-Fa-f]+))?", re.search(r"unicode-range:([^;]+);", block).group(1)):
            lo = int(a, 16); hi = int(b, 16) if b else lo
            cps.extend(range(lo, hi + 1))
        out[(fam, fname)] = cps
    return out


def build(key, src):
    base = TTFont(src)
    base = instancer.instantiateVariableFont(base, dict(AXES[key]))   # tuples narrow an axis, a number pins it
    made = {}
    for (fam, fname), cps in ranges().items():
        if fam != FAMILY[key]:
            continue
        buf = io.BytesIO(); base.save(buf); buf.seek(0)
        font = TTFont(buf)
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern", "liga", "calt", "ccmp", "locl", "mark", "mkmk", "tnum", "lnum", "case", "cv05", "ss01"]
        opts.name_IDs = ["*"]           # keep the copyright, licence and designer names (OFL requires the notices)
        opts.name_languages = ["*"]
        opts.notdef_outline = True
        opts.hinting = False             # browsers on phones ignore TrueType hints; dropping them keeps files small
        opts.desubroutinize = True
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=cps)
        sub.subset(font)
        out = io.BytesIO(); font.flavor = "woff2"; font.save(out)
        with open(os.path.join(HERE, fname), "wb") as f:
            f.write(out.getvalue())
        made[fname] = len(out.getvalue())
    return made


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--inter", required=True); ap.add_argument("--montserrat", required=True); ap.add_argument("--upstream-commit", default="")
    a = ap.parse_args(argv)
    made = {**build("inter", a.inter), **build("montserrat", a.montserrat)}
    rec = {"source": "https://github.com/google/fonts", "licence": "SIL Open Font License 1.1 (see LICENSES/)", "upstream_commit": a.upstream_commit,
           "inputs": {"inter": {"path": "ofl/inter/" + os.path.basename(a.inter), "sha256": sha(a.inter), "axes_kept": {"wght": [400, 700], "opsz": 14}},
                      "montserrat": {"path": "ofl/montserrat/" + os.path.basename(a.montserrat), "sha256": sha(a.montserrat), "axes_kept": {"wght": [500, 700]}}},
           "outputs": {f: {"bytes": made[f], "sha256": sha(os.path.join(HERE, f))} for f in sorted(made)}}
    with open(os.path.join(HERE, "sources.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1); f.write("\n")
    for f in sorted(made):
        print(f"{f}: {made[f] / 1024:.1f} KB")


if __name__ == "__main__":
    main(sys.argv[1:])
