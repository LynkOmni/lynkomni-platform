#!/usr/bin/env python3
"""Provider ledger gate. Run: python3 providers/check.py
Fails when: an entry is stale or malformed, a placeholder in the code is not in the ledger, a service is switched on for a country
before its providers are signed, or an off-by-default service has no provider entry."""
import glob, importlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import providers  # noqa: E402

CODE_DIRS = ("services", "core", "finance", "identity", "dv", "cc")
MARKERS = re.compile(r"PLACEHOLDER|SANDBOX")
KINDS_LATER = ("pending", "done")


def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def _importable(ref):
    mod, _, attr = ref.partition(":")
    try:
        return hasattr(importlib.import_module(mod), attr)
    except Exception:
        return False


def entry_problems(reg=None, root=ROOT):
    from core.regions import SERVICES, COUNTRIES
    reg = reg or providers.registry()
    out, seen = [], set()
    visuals_ids = set(json.loads(_read(os.path.join(root, "visuals", "generated", "index.json")))["needs"]) if os.path.isfile(os.path.join(root, "visuals", "generated", "index.json")) else set()
    for i in reg["items"]:
        iid = i.get("id", "?")
        if iid in seen: out.append(f"{iid}: duplicate id")
        seen.add(iid)
        if i["status"] not in reg["statuses"]: out.append(f"{iid}: unknown status {i['status']}")
        if not i.get("needed_from_provider") and i["status"] != "live": out.append(f"{iid}: list what is needed from the provider")
        for k in ("interface", "sandbox"):
            if not _importable(i[k]): out.append(f"{iid}: {k} {i[k]} cannot be imported (stale entry)")
        if i["status"] in providers.OK_STATUS and not (i.get("real_adapter") and _importable(i["real_adapter"])): out.append(f"{iid}: status {i['status']} needs an importable real_adapter")
        for s in i["used_by"]:
            if s not in SERVICES: out.append(f"{iid}: unknown service {s}")
        if i["countries"] != "all":
            for c in i["countries"]:
                if c not in COUNTRIES: out.append(f"{iid}: unknown country {c}")
        for c, st in (i.get("country_status") or {}).items():
            if st not in reg["statuses"]: out.append(f"{iid}: bad status for {c}")
        if visuals_ids and i["when_off"]["visual"] not in visuals_ids: out.append(f"{iid}: when_off visual {i['when_off']['visual']} does not exist")
        if not i["when_off"].get("message"): out.append(f"{iid}: needs a when_off message")
        for ph in i["placeholders"]:
            p = os.path.join(root, ph["file"])
            if not os.path.isfile(p) or ph["token"] not in _read(p): out.append(f"{iid}: placeholder {ph['token']!r} is no longer in {ph['file']} (update the ledger)")
    for x in reg["later"]:
        if x["status"] not in KINDS_LATER: out.append(f"later {x['id']}: bad status")
        if not x.get("done_when"): out.append(f"later {x['id']}: say when it is done")
        for s in x["blocks"]:
            if s not in SERVICES: out.append(f"later {x['id']}: unknown service {s}")
        for ph in x["placeholders"]:
            p = os.path.join(root, ph["file"])
            if not os.path.isfile(p) or ph["token"] not in _read(p): out.append(f"later {x['id']}: {ph['token']!r} is no longer in {ph['file']}")
    return out


def unregistered_markers(reg=None, root=ROOT):
    """Any PLACEHOLDER or SANDBOX note in the code must belong to a file the ledger knows about."""
    reg = reg or providers.registry()
    known = {ph["file"] for i in reg["items"] for ph in i["placeholders"]} | {ph["file"] for x in reg["later"] for ph in x["placeholders"]}
    known |= {i["interface"].partition(":")[0].replace(".", "/") + ".py" for i in reg["items"]} | {i["sandbox"].partition(":")[0].replace(".", "/") + ".py" for i in reg["items"]}
    known |= {"services/catalog.py"}   # sub-services are generated into the ledger from SUBS
    out = []
    for d in CODE_DIRS:
        for f in sorted(glob.glob(os.path.join(root, d, "**", "*.py"), recursive=True)):
            rel = os.path.relpath(f, root).replace(os.sep, "/")
            for n, line in enumerate(_read(f).splitlines(), 1):
                if MARKERS.search(line) and rel not in known:
                    out.append(f"{rel}:{n}: placeholder or sandbox note not in providers/registry.v1.json")
                    break
    return out


def country_problems(packs=None):
    """A flag, or vcard.enabled, may be true only when every provider the service needs is signed for that country."""
    from core.regions import SERVICES, COUNTRIES
    out = []
    for code, pack in (packs or COUNTRIES).items():
        for service, on in (pack.get("flags") or {}).items():
            if on and service not in providers.phase1():
                ok, reasons = providers.ready(service, code)
                if not ok: out.append(f"{code}: {service} is switched on but {reasons[0]}")
        v = pack.get("vcard") or {}
        if v.get("enabled"):
            ok, reasons = providers.ready("vcard", code)
            if not ok: out.append(f"{code}: vcard.enabled is true but {reasons[0]}")
            if not v.get("issuer") or not v.get("bin_sponsor"): out.append(f"{code}: vcard.enabled needs issuer and bin_sponsor")
    return out


def coverage_problems():
    from core.regions import SERVICES
    off_by_default = {s for s in SERVICES if s not in providers.phase1()}
    gated = set(providers.pending_services())
    return [f"service {s} is off by default but no provider item gates it" for s in sorted(off_by_default - gated)]


def problems(root=ROOT):
    return entry_problems(root=root) + unregistered_markers(root=root) + country_problems() + coverage_problems()


if __name__ == "__main__":
    p = problems()
    print("\n".join(p) if p else "provider ledger: ok (every placeholder is registered; no service is on without its provider)")
    sys.exit(1 if p else 0)
