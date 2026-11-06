"""Machine translation for every LynkOmni screen, the way large platforms do it (owner decision 2026-11-06).

The engine sits behind one interface. The intended engine is Meta's open NLLB-200 model (the translation model behind
Facebook's own translations, about 200 languages, self-hosted, no per-word fee). Until it can be installed, the
SandboxTranslator below produces pseudo-translations: longer, accented text used to prove that no screen breaks.

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
    """SANDBOX engine until NLLB-200 is installed: returns pseudo-translations so layouts are tested in every language."""
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
