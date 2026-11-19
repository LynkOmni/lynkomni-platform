"""Rules for all services apply to every service, existing or new (owner rule 2026-11-19; catalog/universal.v1.json).

For every billing family and every rule in the register this answers: met (the rule's own register shows it), not applicable
(a written reason, only where the rule allows it), or due in the family's home build section. A new family is checked by every
rule the moment it exists; it only needs its home section. tests/test_universal.py keeps it honest and refuses to let a build
section lock while anything is due there."""
import json, os
from core import build_sections as b

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _load(*p):
    with open(os.path.join(_ROOT, *p), encoding="utf-8") as f:
        return json.load(f)

REGISTER = _load("catalog", "universal.v1.json")
RULES = {r["id"]: r for r in REGISTER["rules"]}
BUNDLE_RULES = ("catalog", "places", "picture", "navigation")


def _facts():
    products = _load("catalog", "products.v1.json")["products"]
    needs = {n["id"] for n in _load("visuals", "needs.v1.json")["needs"]}
    tracking = _load("catalog", "tracking.v1.json")
    autos = _load("catalog", "automations.v1.json")["automations"]
    emus = json.dumps(_load("catalog", "emulators.v1.json"))
    conns = json.dumps(_load("catalog", "connections.v1.json"))
    tables = json.dumps(_load("catalog", "build-tables.v1.json")).lower()
    ads = {p["family"] for p in _load("catalog", "ads.v1.json")["places"]}
    cash = json.dumps(_load("catalog", "cash.v1.json"))
    assist_areas = {a.get("area") for a in _load("catalog", "assist.v1.json")["actions"]}
    message_areas = {k.get("area") for k in _load("catalog", "messages.v1.json")["kinds"]}
    areas = REGISTER.get("areas", {})
    return {
        "catalog": {p["family"] for p in products},
        "places": {i["id"] for i in _load("catalog", "placements.v1.json")["items"] if i.get("kind") == "product"},
        "picture": {p["family"] for p in products if p.get("illustration") in needs},
        "api": {a["family"] for a in _load("catalog", "apis.v1.json")["apis"]},
        "tracking": {k.get("family") for k in tracking["kinds"] + tracking.get("planned", [])},
        "automations": {a.get("family") for a in autos},
        "emulator": lambda f: f'"{f}"' in emus,
        "connections": lambda f: f'"{f}"' in conns or f in conns,
        "build_tables": lambda f: f in tables,
        "ads": ads,
        "cash": lambda f: f'"{f}"' in cash,
        "storefront_side": {p["family"] for p in products if p.get("sides")},
        "assist": lambda f: bool(set(areas.get(f, ())) & assist_areas),
        "messages": lambda f: bool(set(areas.get(f, ())) & message_areas),
        "navigation": {fam for g in _load("catalog", "navigation.v1.json")["groups"] for fam in g["families"]},
    }


def status(family, rule, facts=None):
    """("met", None), ("not_applicable", reason) or ("due", build section)."""
    facts = facts or _facts()
    if family in REGISTER["bundles"] and rule not in BUNDLE_RULES:
        return ("not_applicable", REGISTER["bundles_note"])
    f = facts[rule]
    met = f(family) if callable(f) else family in f
    if met:
        return ("met", None)
    reason = REGISTER["not_applicable"].get(rule, {}).get(family)
    if reason and RULES[rule]["na_allowed"]:
        return ("not_applicable", reason)
    return ("due", REGISTER["home_sections"].get(family))


def table(families):
    facts = _facts()
    return {f: {r: status(f, r, facts) for r in RULES} for f in families}


def due(section, families=None):
    """Everything still due in a build section: (family, rule, what)."""
    from services import billing
    out = []
    for f, row in table(families or sorted(billing.FAMILIES)).items():
        for r, (state, where) in row.items():
            if state == "due" and str(where) == str(section):
                out.append((f, r, RULES[r]["what"]))
    return out
