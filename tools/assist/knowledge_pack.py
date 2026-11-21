#!/usr/bin/env python3
"""The LynkAssist knowledge pack (MASTER UPDATE, master blueprint section 54, offline layer 1).

The pack holds the open answers (answer class 1) that every device can give with no network: prices, plans, where each product
lives, what the status words mean. It is built only from the sources of truth (services/billing.py, catalog/products.v1.json,
the five user states, catalog/names.v1.json), never typed by hand, so offline and online answers cannot disagree. Every pack carries the date it was
built and a digest, and is signed; a device refuses a pack whose signature does not match, so a fake pack passed through
LynkMesh is useless. There is one pack per language, written from the same translated shell words as the screens.

    python3 tools/assist/knowledge_pack.py      -> prints a summary of the pack in every language"""
import hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from services import billing  # noqa: E402
from identity.offline import signature_ok  # noqa: E402
from core import names  # noqa: E402

STATES = ("queued", "sent", "accepted", "confirmed", "failed")
LANGS = sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, "web", "shell", "i18n")) if f.endswith(".json"))


def words(lang):
    """The pack's sentences in one language, from the same translated shell words as the screens (web/shell/i18n)."""
    with open(os.path.join(ROOT, "web", "shell", "i18n", f"{lang}.json"), encoding="utf-8") as f:
        return json.load(f)["texts"]


def _words(folder, lang):
    """A shared word pack in one language (English from strings.en.json)."""
    path = os.path.join(ROOT, "web", folder, "strings.en.json" if lang == "en" else os.path.join("i18n", f"{lang}.json"))
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return d.get("texts", d)


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def build(built_on, lang="en"):
    """One pack per language; every language of design/fonts/scripts.v1.json has its own."""
    w = words(lang)
    with open(os.path.join(ROOT, "catalog", "products.v1.json"), encoding="utf-8") as f:
        cat = json.load(f)
    products = {p["family"]: p for p in (cat.get("products") or cat)}
    entries = []
    for fam, (_full, name, tiers, prices, _who, _suite) in billing.FAMILIES.items():
        plans = ", ".join(f"{t.title()} ${p}" for t, p in zip(tiers, prices))
        entries.append({"id": f"price-{fam}", "topic": "price", "q": w["kp_price_q"].format(name=name),
                        "a": w["kp_price_a"].format(name=name, plans=plans), "source": "services/billing.py"})
        page = products.get(fam, {}).get("page")
        if page:
            where = f"lynkomni.com{page}" if page.startswith("/") else page.replace("https://", "")
            entries.append({"id": f"where-{fam}", "topic": "how_to", "q": w["kp_where_q"].format(name=name),
                            "a": w["kp_where_a"].format(name=name, page=where), "source": "catalog/products.v1.json"})
    # "What is LynkStat?" for every Lynk name, from the names register and its translated words (catalog/names.v1.json).
    nw, iw = _words("names", lang), _words("nameinfo", lang)
    for n in names.NAMES:
        if n["kind"] == "device" or n.get("about") is False:
            continue
        p, a = names.plain(n["name"], nw), names.about(n["name"], iw)
        entries.append({"id": f"what-{n['id']}", "topic": "how_to", "q": iw.get("nmi_what_q", "What is {name}?").replace("{name}", n["name"]),
                        "a": iw.get("nmi_what_a", "{name} ({plain}): {about}").replace("{name}", n["name"]).replace("{plain}", p).replace("{about}", a),
                        "source": "catalog/names.v1.json"})
    for state in STATES:
        entries.append({"id": f"state-{state}", "topic": "status_word", "q": w["kp_state_q"].format(state=w[f"st_{state}"]),
                        "a": w[f"kp_state_{state}"], "source": "the five user states"})
    body = {"version": 1, "lang": lang, "built_on": built_on, "entries": entries}
    return {**body, "digest": hashlib.sha256(_canon(body)).hexdigest()}


def sign(pack, key):
    return {**pack, "sig": key.sign({k: v for k, v in pack.items() if k != "sig"})}


def verify(pack, public_hex):
    """A device keeps a pack only when its digest matches its content and the build key signed it."""
    body = {k: v for k, v in pack.items() if k not in ("sig", "digest")}
    if hashlib.sha256(_canon(body)).hexdigest() != pack.get("digest"):
        return False
    return signature_ok(public_hex, {k: v for k, v in pack.items() if k != "sig"}, pack.get("sig", ""))


def _tokens(text):
    """Words, plus three-letter pieces so the search also works in languages written without spaces (Chinese, Japanese, Thai)."""
    t = "".join(c.lower() if c.isalnum() else " " for c in text)
    words_ = {w for w in t.split() if len(w) > 1}
    flat = t.replace(" ", "")
    return words_ | {flat[i:i + 3] for i in range(max(0, len(flat) - 2))}


def lookup(pack, query):
    """Offline search: the entries whose question shares the most with the query, in any script."""
    q = _tokens(query)
    scored = sorted(((len(q & _tokens(e["q"])), e) for e in pack["entries"]), key=lambda x: -x[0])
    return [e for s, e in scored if s > 0][:3]


if __name__ == "__main__":
    for lang in LANGS:
        p = build("unsigned-preview", lang)
        print(f"{lang}: {len(p['entries'])} entries, digest {p['digest'][:12]}")
