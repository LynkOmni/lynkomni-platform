"""Country configuration, geo resolution and feature flags.
Add a country by adding one entry. No code changes elsewhere."""
import os
import pathlib

SERVICES = ["pos", "accountant", "invoicing", "crm", "inventory", "dashboard", "intelligence", "payments",
            "recovery", "paylinks", "loyalty", "marketplace", "financing", "protection", "chat", "ads", "vcard", "registration",
            "agent", "collection", "delivery", "movement", "vehicle_data", "monitoring", "transport_data", "satellite", "iot_sim",
            "attendance", "queue", "survey", "people_messages", "survey_voice", "survey_rewards",
            "voting", "vote_identity", "vote_seal", "vote_post", "vote_mirror", "files", "sign_identity", "sign_qualified", "file_scan", "booking", "exchange",
            "hr_checks", "tenant_screening", "exam_boards", "notary", "pensions", "deposit_protection", "rent_insurance", "property_listings",
            "job_listings", "employer_of_record", "employment_services",
            "chat_channels", "chat_calls", "pay_in_parts", "listing_sync", "outside_warehouses", "shop_plugins", "transport_bills", "government_fees"]
# SERVICES UPDATE (67.18, section 4 row 67.17): the partner parts of the improved services, each off until its partner is signed
# (services/services_partners.py). Delivery firms use "delivery"; phone wallets come through the card issuer ("vcard").
# SIX SERVICES UPDATE (69.13, section 4 row 69.14): the six services' partner parts, each off until its partner is signed (services/six_partners.py).
# EXCHANGE UPDATE (2026-11-18, section 4 step E4b): "exchange" (LynkExchange conversions and transfers) needs a licensed currency or
# money-transfer partner per country and stays off until it is signed (services/exchange_partners.py; practice mode works everywhere).
# BOOKING UPDATE (2026-11-18, section 4 step E4a): "booking" (LynkBooking with direct listings) needs no partner and is on everywhere;
# partner supply, pay later and cancellation cover join with their own partner parts in their build sections (8 and 9).
# SIX SERVICES UPDATE (2026-11-18, section 4 step E3): "files" (LynkFiles' document engine) needs no partner and is on everywhere.
# Its partner parts are off until signed: "sign_identity" (identity-checked signatures), "sign_qualified" (qualified signatures)
# and "file_scan" (scanning office files and archives) (services/files_partners.py).
# VOTE UPDATE (2026-11-18, section 4 step E2): "voting" (LynkVote) needs no partner and is on everywhere. Its partner parts are off until
# signed: "vote_identity" (national identity connectors), "vote_seal" (the trust-service seal on results) and "vote_post" (printing and
# postal ballots) (services/vote_partners.py).
# NEW UPDATE 4 (2026-11-11): "attendance" (LynkAttend), "queue" (LynkQueue) and "survey" (LynkSurvey) need no partner and are on
# everywhere. Their partner parts are off until signed: "people_messages" (text and USSD), "survey_voice" (voice calls) and
# "survey_rewards" (reward and panel payments) (services/people_partners.py).
# NEW UPDATE 1 (2026-11-10): "movement" is LynkMotion and LynkGuard (LynkTrace, LynkGPS, LynkSentry). It needs no partner (the phone is the
# tracker, maps are LynkOmni's own), so it is on everywhere. Its partner parts are off until signed: "vehicle_data" (connected cars),
# "monitoring" (24/7 monitoring centres), "transport_data" (ship and flight data), "satellite" (satellite messaging), "iot_sim" (tracker
# data plans). Partner carriers use "delivery"; the insurer pack uses "protection" (insurance).
# Live by default = Phase 1. The rest are built but OFF until a country integrates them.
# "accountant" is LynkAcc, "invoicing" LynkInv (issuing works without a provider; being paid uses "paylinks"), "crm" LynkCRM.
# "registration" is Start a business (N14, build section 2): a government gateway or bank in the Partner Hub; off until one is signed.
# "agent" (agent point services), "collection" (collection point and partner finance) and "delivery" (N8 partner deliveries) are build
# section 3: every one needs a licensed partner per country and stays off until it is signed; own riders and pickup codes never need one.
DEFAULT_FLAGS = {s: s in ("pos", "accountant", "invoicing", "crm", "inventory", "dashboard", "intelligence", "chat", "movement",
                                "attendance", "queue", "survey", "voting", "files", "booking") for s in SERVICES}

import json, glob
def _load_packs():
    """Country packs are JSON files shared by every language (contract/country-packs). Adding XX.json is the whole job of adding a country."""
    d, packs = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contract", "country-packs"), {}
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        p = json.loads(pathlib.Path(f).read_text()); p["bbox"] = tuple(p["bbox"]) if p.get("bbox") else None; p.setdefault("flags", {}); packs[p["code"]] = p
    return packs
_PACKS = _load_packs()
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contract", "countries.v1.json"), encoding="utf-8") as _f:
    _COUNTRY_LIST = json.load(_f)["countries"]      # every ISO country: names in every interface language, currencies, time zones, official languages (tools/country_packs.py)
def countries_list(): return _COUNTRY_LIST
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
            for k, c in COUNTRIES.items() if c["bbox"] and c["bbox"][0] <= lat <= c["bbox"][1] and c["bbox"][2] <= lon <= c["bbox"][3]]
    return min(hits)[1] if hits else None

def ui_language(code):
    """The interface language a country opens in: its first official language that the interface supports, else the pack's fallback.
    The person can change it with one tap; a country's own language arrives with its wave (design/fonts/language_waves.v1.json)."""
    p = country(code)
    if p.get("ui_language"): return p["ui_language"]
    return _COUNTRY_LIST.get((code or "").upper(), {}).get("ui_language") or (p.get("languages") or ["en"])[0]

def enabled(code, service):
    if os.environ.get("LYNK_MODE") == "sandbox":  # dev: everything on, providers are simulators
        return True
    on = {**DEFAULT_FLAGS, **country(code)["flags"]}.get(service, False)
    if on:   # a flag alone is not enough: the providers the service needs must be signed for this country (providers/registry.v1.json)
        from providers import ready
        on = ready(service, (code or "").upper())[0]
    return on
