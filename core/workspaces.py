"""Who LynkOmni is for (owner request 9 November 2026; catalog/workspaces.v1.json). The office services (accounting, invoicing,
contacts, analytics and the rest) run the internal affairs of a person (household or freelance), a company of any size or an
organisation (non-profit, school, faith group, association or club, cooperative, public body). The entity changes words, tabs,
categories and suggestions only: records, events, prices, limits and rules are the same for everyone (one product for every size).
The TypeScript port is ts/src/business.ts (workspace functions); shared vectors in contract/vectors/pos.v1.json."""
import json, os

from core import accounts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "workspaces.v1.json"), encoding="utf-8") as _f:
    REGISTER = json.load(_f)
ENTITIES = tuple(REGISTER["entities"])
OFFICE_FAMILIES = tuple(REGISTER["office_families"])


def check(entity, kind=None):
    if entity not in REGISTER["entities"]: raise ValueError("unknown entity")
    if kind is not None and kind not in REGISTER["entities"][entity]["kinds"]: raise ValueError("unknown kind for this entity")
    return entity, kind or REGISTER["entities"][entity]["kinds"][0]


def default_type(entity):
    return REGISTER["entities"][check(entity)[0]]["default_type"]


def tabs(entity, business_type, type_tabs):
    """The bottom tabs: an office workspace (no till) of a person or an organisation shows its books, invoices and contacts or members;
    a company, and anyone who also sells at a till, keeps the tabs of its business type."""
    t = REGISTER["entities"][check(entity)[0]]["tabs"]
    return tuple(t) if t and business_type == "no_till" else tuple(type_tabs)


def word(entity, key):
    """The word a screen shows for `key` in this entity's workspace (presentation only): 'Customers' becomes 'Contacts' for a
    person and 'Members' for an organisation."""
    return REGISTER["entities"][check(entity)[0]]["words"].get(key, key)


def categories(entity):
    """Income and expense categories of this entity's workspace; each posts to one account of the global chart."""
    return REGISTER["entities"][check(entity)[0]]["categories"]


def account_for(entity, category):
    for side in ("income", "expense"):
        for c in categories(entity)[side]:
            if c["id"] == category: return c["account"]
    raise ValueError("unknown category")


def funds(entity):
    return tuple(REGISTER["entities"][check(entity)[0]].get("funds", ()))


def suggested(entity):
    return tuple(REGISTER["entities"][check(entity)[0]]["suggested"])


def office_ok(family):
    """True when a family is an office service that works for every entity in any signed-in browser."""
    return family in OFFICE_FAMILIES


def open_to(entity, family):
    """Every billing family is open to every entity (BIZZ & DEVICE, 2026-11-09); the law and licensed partners are the only limits."""
    from services.billing import FAMILIES
    check(entity)
    if family not in FAMILIES:
        raise ValueError("unknown family")
    return True


def identity_check(entity):
    """Which identity check a licensed partner runs for this kind of entity before money moves."""
    return REGISTER["open_to_all"]["identity_check"][check(entity)[0]]


def minimum_age(pack=None):
    """18, or the local age of majority when the country pack sets a higher one."""
    base = REGISTER["open_to_all"]["minimum_age"]["years"]
    local = (pack or {}).get("age_of_majority")
    return max(base, local) if isinstance(local, int) else base


def validate():
    """Register self-check (tests): categories post to real accounts of the right type; suggestions are office families."""
    problems = []
    for e, v in REGISTER["entities"].items():
        for side, want in (("income", ("income", "asset")), ("expense", ("expense", "asset"))):
            for c in v["categories"][side]:
                a = accounts.ACCOUNTS.get(c["account"])
                if not a or a["type"] not in want: problems.append(f"{e}.{c['id']} posts to {c['account']}")
        for f in v["suggested"]:
            if f not in OFFICE_FAMILIES: problems.append(f"{e} suggests {f}")
    return problems
