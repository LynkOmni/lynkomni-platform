"""The parts every service shares (CONNECT UPDATE 71.3; section 4 row 71.9 step 2): the rules only, read from catalog/shared.v1.json.
The cloud service that reads the services' events and methods is services/shared.py."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "shared.v1.json"), encoding="utf-8") as f:
    SHARED = json.load(f)
with open(os.path.join(ROOT, "catalog", "enterprise.v1.json"), encoding="utf-8") as f:
    BASE_ROLES = json.load(f)["roles"]["base"]
DAY = 86400


def base_role(kind, role):
    """The base role a service's role maps to (owner, manager, accountant, auditor or staff)."""
    if role in SHARED["roles"]["base"]:
        return role
    m = SHARED["roles"]["maps"].get(kind, {})
    if role not in m:
        raise KeyError(f"{kind} role {role} is not mapped in catalog/shared.v1.json")
    return m[role]


def may(kind, role, area, permission):
    """Whether a service's role may do something in an area: through its base role's permissions (catalog/enterprise.v1.json)."""
    return permission in BASE_ROLES[base_role(kind, role)].get(area, [])


def calendar_sources(built):
    """The calendar sources a section's progress allows: built(section) says whether that build section is done or being built."""
    return [s for s in SHARED["calendar"]["sources"] if built(s["build_section"])]


def binnable(kind):
    return kind in SHARED["recycle_bin"]["kinds"]


def purge_due(binned_at, now):
    """Removed for good once the bin's keeping time has passed (whole seconds)."""
    return now - binned_at >= SHARED["recycle_bin"]["keep_days"] * DAY


def may_audit(role):
    return role in SHARED["timeline"]["audit_roles"]


# ---- one set of offline clash rules (CONNECT UPDATE 71.3) ------------------------------------------------------------------
def clash_rule(kind):
    """The published rule for a kind of record; an unknown kind is an error (every kind is registered first)."""
    return SHARED["offline_clash"]["kinds"][kind]


def _later(x, y):
    """The later of two changes: the hybrid clock in the event, then the device id (so every service agrees)."""
    return x if (x["hlc"], x["device"]) > (y["hlc"], y["device"]) else y


def settle(kind, a, b):
    """Settle two offline changes to the same record. a and b: {"device", "hlc", "accepted" (cloud order), "fields": {...}}.
    Returns {"rule", "keep": [...] (both, or the winner), "fields" (merged, field_merge and safest_wins), "lost": [fields or
    changes kept only in history], "flag": a person is told}."""
    rule = clash_rule(kind)
    oc = SHARED["offline_clash"]
    if rule == "never_offline":
        raise ValueError(f"{kind} is never changed offline")
    if rule == "append":
        return {"rule": rule, "keep": ["a", "b"], "fields": None, "lost": [], "flag": False}
    if rule == "first_wins":
        first = "a" if (a["accepted"], a["device"]) <= (b["accepted"], b["device"]) else "b"
        return {"rule": rule, "keep": [first], "fields": None, "lost": ["b" if first == "a" else "a"], "flag": True}
    if rule == "safest_wins":
        order = oc["safest"][kind]
        va, vb = a["fields"]["state"], b["fields"]["state"]
        win = va if order.index(va) <= order.index(vb) else vb
        return {"rule": rule, "keep": ["a" if win == va else "b"], "fields": {"state": win}, "lost": [] if va == vb else ["state"], "flag": False}
    late, early = (a, b) if _later(a, b) is a else (b, a)
    merged, lost = dict(early["fields"]), []
    for f, v in late["fields"].items():
        if f in early["fields"] and early["fields"][f] != v:
            lost.append(f)
        merged[f] = v
    lost.sort()
    return {"rule": rule, "keep": ["a", "b"], "fields": dict(sorted(merged.items())), "lost": lost,
            "flag": any(f in oc["flag_fields"] for f in lost)}

