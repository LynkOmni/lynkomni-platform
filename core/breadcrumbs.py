"""Breadcrumb trails from the one address map (MASTER UPDATE, master blueprint section 57; Step 0 part).

Every address knows its parent: the nearest shorter address on the same host that exists in catalog/addresses.v1.json, or the
host's home. Nobody types a trail by hand, so a trail can never disagree with the menus. Storefront trails start at the
Storefront home (/external); a record (a path ending in a public identifier such as {LOINV}) ends with that record. The
breadcrumb part on screens is built in section 1 from this function; labels come from the translated menu names there.
TypeScript gets the same rules in section 1, checked by shared vectors."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "addresses.v1.json"), encoding="utf-8") as _f:
    ADDR = json.load(_f)

HOSTS = {
    "lynkomni.com": ADDR["website_paths"],
    "app.lynkomni.com": ADDR["app_paths"],
    "account.lynkomni.com": ADDR["account_paths"],
    "shop.lynkomni.com": ADDR["shop_paths"],
    "pay.lynkomni.com": ADDR["pay_paths"],
    "staff.lynkomni.com": ADDR["staff_paths"],
}
STOREFRONT = ADDR.get("storefront", {}).get("prefix", "/external")


def home(host, path):
    """The first step of every trail on a host."""
    if host == "app.lynkomni.com" and (path == STOREFRONT or path.startswith(STOREFRONT + "/")):
        return STOREFRONT
    if host == "shop.lynkomni.com" and path.startswith("/{username}"):
        return "/{username}"
    return "/"


def parent(host, path):
    """The nearest shorter address that exists on the host, else the host's home. The home has no parent."""
    known = set(HOSTS.get(host, []))
    h = home(host, path)
    if path == h:
        return None
    parts = path.rstrip("/").split("/")
    while len(parts) > 1:
        parts = parts[:-1]
        cand = "/".join(parts) or "/"
        if cand in known and (cand.startswith(h) or h == "/"):
            return cand
        if cand == h:
            return h
    return h


def trail(host, path):
    """The full trail, home first and the page itself last."""
    steps = [path]
    while True:
        p = parent(host, steps[0])
        if p is None:
            return steps
        if p in steps:
            raise ValueError(f"loop in the trail of {host}{path}")
        steps.insert(0, p)


def every_address():
    for host, paths in HOSTS.items():
        for p in paths:
            yield host, p
