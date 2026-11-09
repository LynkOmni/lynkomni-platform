"""Machine translation for every LynkOmni screen, the way large platforms do it (owner decision 2026-11-06).

The engine sits behind one interface. The engine is Google's open MADLAD-400-3B-MT model (Apache 2.0, so commercial use is
allowed; 400+ languages; self-hosted, no per-word fee). Meta's NLLB-200 was the first choice but its licence (CC-BY-NC)
forbids commercial use, so the owner replaced it on 2026-11-06. MADLAD-400 (3B) proved weak on short screen labels, so
since 2026-11-07 screen text is translated by Claude (TableTranslator, tools/translation/claude_packs.py) and MADLAD is
the engine for text people type (ContentTranslator). SandboxTranslator produces pseudo-translations (longer, accented
text) for tests and for any machine without the engine, to prove that no screen breaks.

Rules every translation passes before it is used:
  - brand, product and provider names are never translated (GLOSSARY);
  - placeholders such as {amount} and every number survive unchanged;
  - nothing is left out or added (each protected token returns exactly once);
  - a translation that fails a rule is refused and the English text is kept, so a screen never shows broken words.
Language, writing direction and fonts come from design/fonts/scripts.v1.json. Locale changes presentation only."""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PLACEHOLDER = re.compile(r"\{[a-z_][a-z0-9_]*\}")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def _families():
    try:
        from services.billing import FAMILIES
        return [v[1] for v in FAMILIES.values()] + [v[0] for v in FAMILIES.values()]
    except Exception:
        return []


GLOSSARY = sorted(set(["LynkOmni", "CruxOmni Group", "CruxOmni", "Visa", "Mastercard", "MTN MoMo", "Airtel Money", "M-Pesa", "UPI",
                       "Apple Pay", "Google Pay", "App Store", "Google Play", "WhatsApp", "QR"] + _families()), key=len, reverse=True)


def languages():
    with open(os.path.join(ROOT, "design", "fonts", "scripts.v1.json"), encoding="utf-8") as f:
        return json.load(f)["languages"]


def protect(text):
    """Swap names, placeholders and numbers for tokens the engine leaves alone. Returns (text, tokens)."""
    tokens = []
    def keep(m):
        tokens.append(m.group(0))
        return f"⟦{len(tokens) - 1}⟧"
    out = _PLACEHOLDER.sub(keep, text)
    for name in GLOSSARY:
        out = re.sub(rf"(?<![\w⟦]){re.escape(name)}(?!\w)", keep, out)
    out = _NUMBER.sub(lambda m: m.group(0) if re.search(r"⟦\d*$", out[:m.start()]) else keep(m), out)
    return out, tokens


def restore(text, tokens):
    """Put the tokens back. Refuses a translation where any token is missing or repeated."""
    for i in range(len(tokens)):
        if text.count(f"⟦{i}⟧") != 1:
            raise ValueError(f"translation lost or repeated a protected part ({tokens[i]!r})")
    if re.search(r"⟦\d+⟧", re.sub(r"⟦(\d+)⟧", lambda m: "" if int(m.group(1)) < len(tokens) else m.group(0), text)):
        raise ValueError("translation added an unknown protected part")
    return re.sub(r"⟦(\d+)⟧", lambda m: tokens[int(m.group(1))], text)


class Translator:
    """Interface for a translation engine. translate() gets protected text and must keep every ⟦n⟧ token."""
    name = "interface"
    def translate(self, texts, source, target):
        raise NotImplementedError


_PSEUDO = str.maketrans("aceinosuyACEINOSUY", "àçéîñöšüýÀÇÉÎÑÖŠÜÝ")


def pseudo(text, grow=0.4):
    """Pseudo-translation: accented letters and about 40% more length (long languages such as German or Swahili run longer)."""
    parts = re.split(r"(⟦\d+⟧)", text)
    body = "".join(p if p.startswith("⟦") else p.translate(_PSEUDO) for p in parts)
    pad = "~" * max(1, round(len(re.sub(r"⟦\d+⟧", "", text)) * grow))
    return f"[{body} {pad}]"


class SandboxTranslator(Translator):
    """SANDBOX engine for tests and machines without the MADLAD-400 model: returns pseudo-translations so layouts are tested in every language."""
    name = "sandbox-pseudo"
    def translate(self, texts, source, target):
        return [pseudo(t) for t in texts]


def translate_catalog(catalog, target, engine=None, source="en"):
    """{key: English text} -> ({key: translated text}, [keys kept in English and why]). Never returns broken text."""
    if target not in languages():
        raise ValueError(f"{target} is not in design/fonts/scripts.v1.json")
    engine = engine or SandboxTranslator()
    keys = list(catalog)
    out, kept = {}, []
    for k, (text, err, _) in zip(keys, run(engine, [catalog[k] for k in keys], source, target)):
        out[k] = catalog[k] if err else text
        if err:
            kept.append((k, err))
    return out, kept


def ascii_digits(text):
    """Digits from any script (Arabic-Indic, Persian, Devanagari...) back to 0-9. Numbers are formatted by the app per locale."""
    import unicodedata
    return "".join(str(unicodedata.decimal(c)) if c.isdecimal() and not c.isascii() else c for c in text)


ROUND_TRIP_MIN = 0.45    # chrF of English vs the translation translated back; below this the meaning probably drifted


def stutters(text):
    """True when a text repeats a word, a phrase or a sentence back to back (a known machine-translation failure)."""
    import unicodedata   # words split on spaces and punctuation (\w would cut Devanagari words at their vowel signs)
    w = [x for x in ("".join(" " if unicodedata.category(c)[0] in "PZ" else c for c in text.lower())).split() if x]
    if any(w[i:i + n] == w[i + n:i + 2 * n] for n in range(1, 7) for i in range(len(w) - 2 * n + 1)):
        return True
    sentences = [x.strip() for x in re.split(r"[.!?\u061F\u06D4\u0964]+", text.lower()) if x.strip()]
    return len(sentences) != len(set(sentences))


def chrf(ref, hyp, n=4, beta=2.0):
    """Character n-gram F-score (chrF, 0 to 1): how close two texts in the same language are."""
    from collections import Counter
    a, b = re.sub(r"\s+", "", ref.lower()), re.sub(r"\s+", "", hyp.lower())
    scores = []
    for k in range(1, n + 1):
        ga, gb = Counter(a[i:i + k] for i in range(len(a) - k + 1)), Counter(b[i:i + k] for i in range(len(b) - k + 1))
        if not ga or not gb:
            continue
        hit = sum((ga & gb).values())
        p, r = hit / sum(gb.values()), hit / sum(ga.values())
        scores.append(0.0 if not hit else (1 + beta ** 2) * p * r / (beta ** 2 * p + r))
    return sum(scores) / len(scores) if scores else 0.0


def problems(src, out):
    """Why a machine translation must not be shown (None when it may be shown)."""
    if not out:
        return "empty translation"
    _, toks = protect(src)
    bad = [tok for tok in dict.fromkeys(toks) if out.count(tok) != src.count(tok)]
    if bad:
        return f"translation lost or repeated a protected part ({bad[0]!r})"
    if stutters(out) and not stutters(src):
        return "translation repeats itself"
    if len(out) > 3 * len(src) + 15:
        return "translation is much longer than the English (added words)"
    ends = lambda x: len(re.findall(r"[.!?\u061F\u06D4\u0964]+(?=\s|$)", x.strip()))
    if ends(out) > max(1, ends(src)):
        return "translation adds a sentence"
    return None


_SCRIPT_WORD = {"arabic": "ARABIC", "hebrew": "HEBREW", "devanagari": "DEVANAGARI", "cyrillic": "CYRILLIC",
                "han-simplified": "CJK UNIFIED", "han-traditional": "CJK UNIFIED", "japanese": ("CJK UNIFIED", "HIRAGANA", "KATAKANA"), "korean": "HANGUL"}


def in_own_script(text, lang):
    """True when a text is written in its language's script (always true for Latin-script languages)."""
    import unicodedata
    with open(os.path.join(ROOT, "design", "fonts", "scripts.v1.json"), encoding="utf-8") as f:
        word = _SCRIPT_WORD.get(json.load(f)["languages"][lang]["script"])
    rest, _ = protect(text)                                                              # a text of only names, placeholders and numbers has nothing to write in any script
    if not word or not any(c.isalpha() for c in re.sub(r"⟦\d+⟧", "", rest)):
        return True
    return any(unicodedata.name(c, "").startswith(word) for c in text)   # str.startswith accepts a tuple of words


class TableTranslator(Translator):
    """Screen-text translations written by Claude (owner decision 2026-11-07: Claude translates the screens; the MADLAD
    engine stays for text people type). It only looks texts up; run() still applies every automatic check (protected
    parts, no repetition, no added words or sentences) and tools/translation/claude_packs.py adds the script check."""
    plain_tokens, round_trip = True, False

    def __init__(self, table, name="claude-opus-5-5"):
        self.table, self.name = table, name

    def translate(self, texts, source, target):
        return [self.table[target][t] for t in texts]


def run(engine, texts, source, target):
    """Translate texts and check them. Returns [(translation, None, score) or (None, why it was refused, score)].

    Engines with plain_tokens=True (real models) see names, {placeholders} and numbers as they are and must return each
    exactly as often as the English. They offer several candidates per text; a candidate is refused if it loses a
    protected part, repeats itself or adds words, and the survivors are translated BACK into the source language: the
    one whose round trip is closest to the original wins, and only if that closeness (chrF) is at least ROUND_TRIP_MIN.
    Otherwise the text is refused and the caller keeps the original, so a drifted or invented meaning is never shown."""
    if getattr(engine, "plain_tokens", False):
        cands = engine.candidates(texts, source, target) if hasattr(engine, "candidates") else [[r] for r in engine.translate(texts, source, target)]
        valid, res = [], []
        for text, cs in zip(texts, cands):
            ok, why = [], None
            for c in dict.fromkeys(ascii_digits(c).strip() for c in cs):
                why_c = problems(text, c)
                ok.append(c) if not why_c else None
                why = why or why_c
            valid.append(ok)
            res.append([None, why or "no usable translation", -1.0])
        if not getattr(engine, "round_trip", True):     # reviewed translations (TableTranslator): first valid candidate
            return [(ok[0], None, 1.0) if ok else (None, r[1], 0.0) for ok, r in zip(valid, res)]
        flat = [(i, c) for i, ok in enumerate(valid) for c in ok]
        if not flat:
            back = []
        elif hasattr(engine, "candidates"):    # several ways back: a one-word label ("Espèces") may come back as a synonym
            back = engine.candidates([c for _, c in flat], target, source)
        else:
            back = [[b] for b in engine.translate([c for _, c in flat], target, source)]
        for (i, c), bs in zip(flat, back):
            score = max(chrf(texts[i], ascii_digits(b)) for b in bs)
            if score > res[i][2]:
                res[i] = [c, None, score] if score >= ROUND_TRIP_MIN else [None, f"meaning drifted (round trip {score:.2f})", score]
        return [(r[0], r[1], max(r[2], 0.0)) for r in res]
    prepared = [protect(t) for t in texts]
    raw = engine.translate([p[0] for p in prepared], source, target)
    res = []
    for (_, toks), r in zip(prepared, raw):
        try:
            res.append((restore(r, toks), None, 1.0))
        except ValueError as e:
            res.append((None, str(e), 0.0))
    return res



# ---- the real engine and the offline design ---------------------------------------------------------------------------

def mt_code(lang):
    """The MADLAD-400 target-language code for a LynkOmni language, from design/fonts/scripts.v1.json ("mt")."""
    L = languages().get(lang)
    if not L or not L.get("mt"):
        raise ValueError(f"{lang} has no machine-translation code in design/fonts/scripts.v1.json")
    return L["mt"]


class MadladTranslator(Translator):
    """Google MADLAD-400-3B-MT (Apache 2.0 licence: commercial use allowed; 400+ languages), converted to CTranslate2 with
    int8 weights so it runs on ordinary processors. Chosen by the owner on 2026-11-06 instead of Meta NLLB-200, whose
    CC-BY-NC licence forbids commercial use. It is loaded ONLY from a local folder (LYNK_MT_DIR) made once by
    tools/translation/install_engine.py; nothing is downloaded while the app runs and no text leaves LynkOmni's machines.
    Needs the ctranslate2 and sentencepiece packages."""
    name = "madlad400-3b-mt-ct2-int8"
    plain_tokens = True

    def __init__(self, model_dir=None):
        model_dir = model_dir or os.environ.get("LYNK_MT_DIR")
        if not model_dir or not os.path.isdir(model_dir):
            raise RuntimeError("MADLAD-400 model folder not found: set LYNK_MT_DIR (see tools/translation/install_engine.py)")
        import ctranslate2, sentencepiece   # noqa: E401  (installed with the model, never at run time)
        self.model = ctranslate2.Translator(model_dir, device="cpu", compute_type="int8")
        self.sp = sentencepiece.SentencePieceProcessor(model_file=os.path.join(model_dir, "spiece.model"))
        meta = os.path.join(model_dir, "engine.json")
        self.revision = json.load(open(meta, encoding="utf-8")).get("revision") if os.path.isfile(meta) else None

    def has_language(self, lang):
        return self.sp.piece_to_id(f"<2{mt_code(lang)}>") != self.sp.unk_id()

    def translate(self, texts, source, target):
        tag = f"<2{mt_code(target)}>"
        if not self.has_language(target):
            raise ValueError(f"the engine does not know the language tag {tag}")
        return [c[0] for c in self.candidates(texts, source, target, n=1)]

    def candidates(self, texts, source, target, n=4):
        """The n best translations of each text (beam search with a repetition penalty), best first."""
        tag = f"<2{mt_code(target)}>"
        if not self.has_language(target):
            raise ValueError(f"the engine does not know the language tag {tag}")
        # The answer may be at most about twice as long as the question: a short label must not grow into a sentence.
        src = [self.sp.encode(f"{tag} {t}", out_type=str) for t in texts]
        out = [None] * len(texts)
        groups = {}
        for i, toks in enumerate(src):
            groups.setdefault(min(256, 2 * len(toks) + 8), []).append(i)
        for limit, idx in groups.items():
            res = self.model.translate_batch([src[i] for i in idx], beam_size=max(4, n), num_hypotheses=n, repetition_penalty=1.15,
                                             max_decoding_length=limit, max_batch_size=16)
            for i, r in zip(idx, res):
                out[i] = [self.sp.decode(h) for h in r.hypotheses]
        return out


def build_pack(catalog, lang, engine=None, reasons=None):
    """A language pack for the apps: every screen text translated AHEAD of time and shipped inside the app, so screens work in
    every language with no internet and no engine on the phone. English source is fingerprinted so stale packs are caught."""
    import hashlib
    engine = engine or SandboxTranslator()
    if lang == "en":
        texts, kept = dict(catalog), []
    else:
        texts, kept = translate_catalog(catalog, lang, engine)
        if reasons is not None:
            reasons.update(dict(kept))
    src = hashlib.sha256(json.dumps(catalog, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    L = languages()[lang]
    pack = {"lang": lang, "dir": _dir(lang), "native": L["native"], "engine": "source" if lang == "en" else engine.name,
            "source_sha256": src, "texts": texts, "kept_in_english": [k for k, _ in kept]}
    if lang != "en" and getattr(engine, "revision", None):
        pack["engine_revision"] = engine.revision
    return pack


def _dir(lang):
    with open(os.path.join(ROOT, "design", "fonts", "scripts.v1.json"), encoding="utf-8") as f:
        reg = json.load(f)
    return reg["scripts"][reg["languages"][lang]["script"]]["dir"]


class ContentTranslator:
    """Text people type (chat messages, product names, notes): translated by the server engine when online and cached on the
    device. Offline, or when the engine is unavailable, the ORIGINAL text is shown with the state "queued" and translated once
    back online; a broken or partial translation is never shown."""
    def __init__(self, engine=None):
        self.engine, self.cache = engine, {}

    def show(self, text, source, target, online):
        if source == target:
            return {"text": text, "translated": False, "state": None}
        key = (text, source, target)
        if key in self.cache:
            return {"text": self.cache[key], "translated": True, "state": None}
        if not online or self.engine is None:
            return {"text": text, "translated": False, "state": "queued", "note": "translates when online"}
        try:
            out, err, _ = run(self.engine, [text], source, target)[0]
        except Exception:
            out, err = None, "engine error"
        if err:
            return {"text": text, "translated": False, "state": "failed"}
        self.cache[key] = out
        return {"text": out, "translated": True, "state": None}
