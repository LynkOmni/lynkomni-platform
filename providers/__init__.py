"""Provider ledger: what waits on a provider, and whether a service may be on for a country.

A provider item is a working SANDBOX stand-in behind an interface. The real adapter is added later next to it, behind the same
interface, so nothing else changes. Until an item is `contract_signed` (or `live`) for a country, every service that needs it is
OFF there, and the app shows the "not available yet" state instead of a broken screen. The merge below also includes every
sub-service in services/catalog.py, so a new sub-service can never be left out.

    providers.ready("vcard", "RW")        -> (False, ["vcard_issuer: sandbox, needs signed issuer agreement ..."])
    providers.go_live_report("payments", "KE")
    providers.when_off("vcard")           -> {"visual": "state-coming-soon", "message": "Coming to your country soon."}
Registry file: providers/registry.v1.json. Gate: python3 providers/check.py."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REGISTRY = os.path.join(HERE, "registry.v1.json")
OK_STATUS = ("contract_signed", "live")
OFF = {"visual": "state-coming-soon", "message": "Coming to your country soon."}
_CACHE = {}


def registry():
    if "r" not in _CACHE:
        with open(REGISTRY, encoding="utf-8") as f:
            _CACHE["r"] = json.load(f)
    return _CACHE["r"]


def catalog_items():
    """One provider item per sub-service in services/catalog.py (generated, so none can be forgotten)."""
    from services import catalog
    out = []
    for sid, (cat, name, ptype, needs) in catalog.SUBS.items():
        out.append({"id": f"catalog_{sid}", "name": f"{name} provider ({ptype})", "kind": "catalog", "used_by": ["marketplace"], "countries": "all", "status": "sandbox",
                    "interface": "services.catalog:SandboxProvider", "sandbox": "services.catalog:SandboxProvider", "needed_from_provider": [needs], "placeholders": [],
                    "when_off": OFF, "notes": "Generated from services/catalog.py SUBS.", "integrate": []})
    return out


def items():
    return registry()["items"] + catalog_items()


def phase1():
    """Services that are on by default in every country (Phase 1). A provider never switches these off: they work offline without one."""
    from core.regions import DEFAULT_FLAGS
    return {s for s, on in DEFAULT_FLAGS.items() if on}


def gates(item):
    """The services this provider item keeps OFF until it is signed. Phase 1 services are only listed in `used_by`, never gated."""
    p1 = phase1()
    return [s for s in item["used_by"] if s not in p1]


def item_status(item, country):
    return (item.get("country_status") or {}).get(country, item["status"])


def applies(item, country):
    c = item["countries"]
    return c == "all" or country in c


def needs(service, country):
    return [i for i in items() if service in gates(i) and applies(i, country)]


def ready(service, country):
    """(True, []) when every provider the service needs is signed for this country; otherwise (False, reasons)."""
    reasons = [f"{i['id']}: {item_status(i, country)}, needs " + "; ".join(i["needed_from_provider"][:2]) for i in needs(service, country) if item_status(i, country) not in OK_STATUS]
    return (not reasons), reasons


def blocked_by_later(service):
    return [x for x in registry()["later"] if service in x["blocks"] and x["status"] != "done"]


def go_live_report(service, country):
    ok, reasons = ready(service, country)
    later = [f"{x['id']}: {x['done_when']}" for x in blocked_by_later(service)]
    return {"service": service, "country": country, "provider_ready": ok, "missing_providers": reasons, "later_work": later, "may_go_live": ok and not later}


def when_off(service):
    for i in items():
        if service in gates(i):
            return i["when_off"]
    return OFF


def availability(service, country):
    """Global availability rule (owner approved 2026-11-06): every LynkOmni service is designed for the whole world and shown in
    every country. Services that need no licensed partner are available everywhere. Regulated services (payments, cards,
    lending, insurance, crypto, exchange, tax receipts and the like) are shown everywhere too, and say "Coming to your country
    soon." with a Notify me option until their licensed partner is signed for that country; then they switch on by themselves."""
    from core.regions import enabled
    code = (country or "").upper()
    if enabled(code, service):
        return {"service": service, "country": code, "state": "available", "message": None, "visual": None, "notify_me": False}
    off = when_off(service)
    return {"service": service, "country": code, "state": "coming_soon", "message": off["message"], "visual": off["visual"], "notify_me": True}


def pending_services():
    """Every service that still waits on something, for status reports."""
    from core.regions import SERVICES
    return sorted(s for s in SERVICES if any(s in gates(i) for i in items()))
