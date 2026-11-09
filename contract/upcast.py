"""Reference upcaster: reads an older contract event as the current version (contract/upcasters.v1.json).
Upcasting happens on the way in and is never written back: the stored event, its signature and its hash chain stay as they were."""
import copy, json, os

_ROOT = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_ROOT, "upcasters.v1.json"), encoding="utf-8") as _f:
    UPCASTERS = {u["from_schema_version"]: u for u in json.load(_f)["upcasters"]}
CURRENT = max(u["to_schema_version"] for u in UPCASTERS.values())


def upcast(event):
    """Returns a copy of the event at the current schema version, or the event itself when it is already current."""
    v = event.get("schema_version")
    if v == CURRENT:
        return event
    if v not in UPCASTERS:
        return event                       # unknown versions are left alone; the validator quarantines them
    u = UPCASTERS[v]
    out = copy.deepcopy(event)
    if v == 1:
        if out["type"] in u["adds_currency_to"]:
            out["payload"].setdefault("currency", u["default_currency"])
    if v == 2:
        out["payload"].setdefault("side", u["adds_side"])      # written before Storefronts existed: the workspace side
    out["schema_version"] = u["to_schema_version"]
    return upcast(out)
