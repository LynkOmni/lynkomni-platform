#!/usr/bin/env python3
"""The LynkAssist knowledge pack (MASTER UPDATE, master blueprint section 54, offline layer 1).

The pack holds the open answers (answer class 1) that every device can give with no network: prices, plans, where each product
lives, what the status words mean. It is built only from the sources of truth (services/billing.py, catalog/products.v1.json,
the five user states), never typed by hand, so offline and online answers cannot disagree. Every pack carries the date it was
built and a digest, and is signed; a device refuses a pack whose signature does not match, so a fake pack passed through
LynkMesh is useless. Screen words are added per language when the pack is shown (section 1).

    python3 tools/assist/knowledge_pack.py      -> prints a summary of the English pack"""
import hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from services import billing  # noqa: E402
from identity.offline import signature_ok  # noqa: E402

STATES = {"queued": "saved on this device and waiting to be sent",
          "sent": "sent, waiting for an answer",
          "accepted": "received by LynkOmni or the partner, not yet final",
          "confirmed": "final: the provider or partner confirmed it",
          "failed": "it did not go through; nothing was charged or changed"}


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def build(built_on):
    with open(os.path.join(ROOT, "catalog", "products.v1.json"), encoding="utf-8") as f:
        cat = json.load(f)
    products = {p["family"]: p for p in (cat.get("products") or cat)}
    entries = []
    for fam, (full, name, tiers, prices, _who, _suite) in billing.FAMILIES.items():
        plans = ", ".join(f"{t.title()} ${p}" for t, p in zip(tiers, prices))
        entries.append({"id": f"price-{fam}", "topic": "price", "q": f"How much is {name}?",
                        "a": f"{name} ({full}): {plans} a month.", "source": "services/billing.py"})
        page = products.get(fam, {}).get("page")
        if page:
            entries.append({"id": f"where-{fam}", "topic": "how_to", "q": f"Where is {name}?",
                            "a": f"{name} is described at lynkomni.com{page}" if page.startswith("/") else f"{name} is at {page}",
                            "source": "catalog/products.v1.json"})
    for state, meaning in STATES.items():
        entries.append({"id": f"state-{state}", "topic": "status_word", "q": f"What does '{state}' mean?", "a": meaning,
                        "source": "the five user states"})
    body = {"version": 1, "lang": "en", "built_on": built_on, "entries": entries}
    return {**body, "digest": hashlib.sha256(_canon(body)).hexdigest()}


def sign(pack, key):
    return {**pack, "sig": key.sign({k: v for k, v in pack.items() if k != "sig"})}


def verify(pack, public_hex):
    """A device keeps a pack only when its digest matches its content and the build key signed it."""
    body = {k: v for k, v in pack.items() if k not in ("sig", "digest")}
    if hashlib.sha256(_canon(body)).hexdigest() != pack.get("digest"):
        return False
    return signature_ok(public_hex, {k: v for k, v in pack.items() if k != "sig"}, pack.get("sig", ""))


def lookup(pack, query):
    """Offline search by plain words: the entries whose question shares the most words with the query."""
    words = {w.strip("?.,'").lower() for w in query.split()} - {"", "is", "the", "a", "what", "how", "much", "does", "where"}
    scored = sorted(((len(words & {w.strip("?.,'").lower() for w in e["q"].split()}), e) for e in pack["entries"]),
                    key=lambda x: -x[0])
    return [e for s, e in scored if s > 0][:3]


if __name__ == "__main__":
    p = build("unsigned-preview")
    print(f"{len(p['entries'])} entries, digest {p['digest'][:12]}")
