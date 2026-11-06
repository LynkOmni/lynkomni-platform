"""Machine translation for every LynkOmni screen, the way large platforms do it (owner decision 2026-11-06).

The engine sits behind one interface. The engine is Google's open MADLAD-400-3B-MT model (Apache 2.0, so commercial use is
allowed; 400+ languages; self-hosted, no per-word fee). Meta's NLLB-200 was the first choice but its licence (CC-BY-NC)
forbids commercial use, so the owner replaced it on 2026-11-06. SandboxTranslator below produces pseudo-translations
(longer, accented text) for tests and for any machine without the engine, to prove that no screen breaks.

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
                       "Apple Pay", "Google Pay", "WhatsApp", "QR"] + _families()), key=len, reverse=True)


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
    prepared = [protect(catalog[k]) for k in keys]
    raw = engine.translate([p[0] for p in prepared], source, target)
    out, kept = {}, []
    for k, (txt, toks), r in zip(keys, prepared, raw):
        try:
            out[k] = restore(r, toks)
        except ValueError as e:
            out[k] = catalog[k]
            kept.append((k, str(e)))
    return out, kept


# ---- the real engine and the offline design ---------------------------------------------------------------------------

def mt_code(lang):
    """The MADLAD-400 target-language code for a LynkOmni language, from design/fonts/scripts.v1.json ("mt")."""
    L = languages().get(lang)
    if not L or not L.get("mt"):
        raise ValueError(f"{lang} has no machine-translation code in design/fonts/scripts.v1.json")
    return L["mt"]


# Protected parts travel through the engine as plain Latin marks it copies unchanged (it would mangle the ⟦n⟧ brackets,
# and numbers could come back in another digit system). They are turned back into ⟦n⟧ before restore() checks them.
_MARK = "QZX"
_LETTERS = "ABCDEFGHJKLMNPRSTUVW"


def to_marks(text):
    return re.sub(r"⟦(\d+)⟧", lambda m: _MARK + _LETTERS[int(m.group(1))], text)


def from_marks(text):
    return re.sub(rf"{_MARK}\s?([{_LETTERS}])", lambda m: f"⟦{_LETTERS.index(m.group(1))}⟧", text, flags=0)


class MadladTranslator(Translator):
    """Google MADLAD-400-3B-MT (Apache 2.0 licence: commercial use allowed; 400+ languages), converted to CTranslate2 with
    int8 weights so it runs on ordinary processors. Chosen by the owner on 2026-11-06 instead of Meta NLLB-200, whose
    CC-BY-NC licence forbids commercial use. It is loaded ONLY from a local folder (LYNK_MT_DIR) made once by
    tools/translation/install_engine.py; nothing is downloaded while the app runs and no text leaves LynkOmni's machines.
    Needs the ctranslate2 and sentencepiece packages."""
    name = "madlad400-3b-mt-ct2-int8"

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
        batch = [[tag] + self.sp.encode(to_marks(t), out_type=str) + ["</s>"] for t in texts]
        res = self.model.translate_batch(batch, beam_size=4, max_decoding_length=256, max_batch_size=16)
        return [from_marks(self.sp.decode(r.hypotheses[0])) for r in res]


def build_pack(catalog, lang, engine=None):
    """A language pack for the apps: every screen text translated AHEAD of time and shipped inside the app, so screens work in
    every language with no internet and no engine on the phone. English source is fingerprinted so stale packs are caught."""
    import hashlib
    engine = engine or SandboxTranslator()
    if lang == "en":
        texts, kept = dict(catalog), []
    else:
        texts, kept = translate_catalog(catalog, lang, engine)
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
        protected, tokens = protect(text)
        try:
            out = restore(self.engine.translate([protected], source, target)[0], tokens)
        except Exception:
            return {"text": text, "translated": False, "state": "failed"}
        self.cache[key] = out
        return {"text": out, "translated": True, "state": None}
