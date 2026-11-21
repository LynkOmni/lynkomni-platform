"""LynkSchool's register for every kind and level of school (SCHOOL UPDATE, master blueprint section 80; limits and registers built
in section 4, row 80.15): catalog/school.v1.json with the tier features of services/billing.py FEATURES lynkschool (80.13).

A school picks its kind and sees only what it needs; what changes by kind is which tools are shown, never prices, limits or rules.
The safety rules, the school year and offline working are on every tier. The screens come in their own build sections (80.15)."""
import json, os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "catalog", "school.v1.json"), encoding="utf-8") as _f:
    SCHOOL = json.load(_f)

TIERS = ("free", "plus", "pro", "max")


def group_of(kind):
    for group, kinds in SCHOOL["kinds"].items():
        if kind in kinds:
            return group
    raise ValueError(f"unknown kind of school {kind}")


def kind_tools_tier(kind):
    """The lowest tier whose tools fit this kind in full (the further-education and centre tools are on Pro, 80.13); every kind
    can still use LynkSchool on every tier."""
    return SCHOOL["kind_tier"].get(group_of(kind), "free")


def features(tier):
    """The section 80 features a tier has: everything of the tiers below it plus its own (80.13)."""
    if tier not in TIERS:
        raise ValueError("unknown tier")
    out = list(SCHOOL["every_tier"])
    for t in TIERS[1:TIERS.index(tier) + 1]:
        out += SCHOOL["features_by_tier"].get(t, [])
    return out


def assist_may(action):
    """False for anything LynkAssist never does in LynkSchool (80.16): a named person decides."""
    return action not in SCHOOL["assist"]["never"]
