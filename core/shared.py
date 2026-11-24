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
