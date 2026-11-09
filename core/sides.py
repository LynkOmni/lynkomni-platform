"""The two sides of every service (BIZZ & DEVICE, owner approved 2026-11-09; catalog/addresses.v1.json "storefront").

internal  the workspace: a person, company or organisation using a service for its own affairs (everything built before
          2026-11-09, at today's paths and locked prices; shown with the workspace word: Business, My space, Organisation).
external  the Storefront: using a service to offer to others and earn (Storefront plans; shown as "Storefront").

The side is read from the address alone, so billing, records, support channels, automations and reports switch by
themselves and never guess. The TypeScript port is ts/src/sides.ts; contract/vectors/sides.v1.json proves both agree."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "addresses.v1.json"), encoding="utf-8") as _f:
    _ADDR = json.load(_f)
RULE = _ADDR["storefront"]
PREFIX = RULE["prefix"]
SIDES = ("internal", "external")
PUBLIC_HOSTS = ("shop.lynkomni.com", "pay.lynkomni.com")
LISTS = tuple(RULE["public"]["lists"])


def _match(pattern, path):
    a, b = pattern.strip("/").split("/"), path.strip("/").split("/")
    return len(a) == len(b) and all(x == y or (x.startswith("{") and x.endswith("}")) for x, y in zip(a, b))


def side_of(address):
    """The side of an address: 'external' for /external... in the app and for the public Storefront pages (a seller's page,
    an offer, Explore, buying an offer); 'internal' for everything else. Takes a path or host + path."""
    host, path = ("", address)
    if not address.startswith("/"):
        host, _, rest = address.partition("/")
        path = "/" + rest
    path = path.split("?", 1)[0].split("#", 1)[0] or "/"
    if host in ("", "app.lynkomni.com"):
        return "external" if path == PREFIX or path.startswith(PREFIX + "/") else "internal"
    if host == "pay.lynkomni.com":
        return "external" if _match("/listings/{LOLST}", path) else "internal"
    if host == "shop.lynkomni.com":
        seg = path.strip("/").split("/") if path.strip("/") else []
        if len(seg) == 2 and seg[0] == "explore":
            return "external" if seg[1] in LISTS else "internal"
        if len(seg) == 1 and seg[0] not in ("explore", "track"):
            return "external"                              # a seller's Storefront page
        if len(seg) == 3 and seg[1] in LISTS:
            return "external"                              # one offer
        return "internal"                                  # tables, reviews and following a purchase (/track) are not selling
    return "internal"


def storefront_path(workspace_path):
    """The Storefront twin of a workspace app path (fixed format: /external + the path). Only mirrored paths have one."""
    if workspace_path not in RULE["mirrors"]:
        raise ValueError(f"{workspace_path} has no Storefront side (shared or workspace only)")
    return PREFIX + workspace_path


def workspace_path(storefront):
    if not storefront.startswith(PREFIX + "/"):
        raise ValueError("not a Storefront path")
    w = storefront[len(PREFIX):]
    if w not in RULE["mirrors"]:
        raise ValueError(f"{storefront} is Storefront only")
    return w


def kind(app_path):
    """mirrored, storefront_only, shared or workspace_only: every app path is exactly one of these (tests check)."""
    if app_path in RULE["storefront_only"]: return "storefront_only"
    if app_path.startswith(PREFIX + "/") and app_path[len(PREFIX):] in RULE["mirrors"]: return "mirrored"
    if app_path in RULE["mirrors"]: return "mirrored"
    if app_path in RULE["shared"]: return "shared"
    if app_path in RULE["workspace_only"]: return "workspace_only"
    raise ValueError(f"{app_path} is not classified in catalog/addresses.v1.json storefront")
