"""Country configuration, geo resolution and feature flags.
Add a country by adding one entry. No code changes elsewhere."""
import os
import pathlib

SERVICES = ["pos", "accountant", "invoicing", "crm", "inventory", "dashboard", "intelligence", "payments",
            "recovery", "paylinks", "loyalty", "marketplace", "financing", "protection", "chat", "ads", "vcard", "registration"]
# Live by default = Phase 1. The rest are built but OFF until a country integrates them.
# "accountant" is LynkAcc, "invoicing" LynkInv (issuing works without a provider; being paid uses "paylinks"), "crm" LynkCRM.
# "registration" is Start a business (N14, build section 2): a government gateway or bank in the Partner Hub; off until one is signed.
DEFAULT_FLAGS = {s: s in ("pos", "accountant", "invoicing", "crm", "inventory", "dashboard", "intelligence", "chat") for s in SERVICES}

import json, glob
def _load_packs():
    """Country packs are JSON files shared by every language (contract/country-packs). Adding XX.json is the whole job of adding a country."""
    d, packs = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contract", "country-packs"), {}
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        p = json.loads(pathlib.Path(f).read_text()); p["bbox"] = tuple(p["bbox"]) if p.get("bbox") else None; p.setdefault("flags", {}); packs[p["code"]] = p
    return packs
_PACKS = _load_packs()
GENERIC = _PACKS.pop("XX")
COUNTRIES = _PACKS

def country(code):
    return COUNTRIES.get((code or "").upper(), GENERIC)

def resolve_country(lat=None, lon=None, hint=None):
    """Explicit choice (hint) always wins. Otherwise the smallest matching bounding box.
    Boxes are CRUDE and overlap at borders: replace with a real geo lookup (and keep the merchant's
    explicit choice as the source of truth) before relying on this for tax or payments."""
    if hint and hint.upper() in COUNTRIES:
        return hint.upper()
    if lat is None or lon is None:
        return None
    hits = [(abs((c["bbox"][1] - c["bbox"][0]) * (c["bbox"][3] - c["bbox"][2])), k)
            for k, c in COUNTRIES.items() if c["bbox"][0] <= lat <= c["bbox"][1] and c["bbox"][2] <= lon <= c["bbox"][3]]
    return min(hits)[1] if hits else None

def enabled(code, service):
    if os.environ.get("LYNK_MODE") == "sandbox":  # dev: everything on, providers are simulators
        return True
    on = {**DEFAULT_FLAGS, **country(code)["flags"]}.get(service, False)
    if on:   # a flag alone is not enough: the providers the service needs must be signed for this country (providers/registry.v1.json)
        from providers import ready
        on = ready(service, (code or "").upper())[0]
    return on
