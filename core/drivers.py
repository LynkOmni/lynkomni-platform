"""LynkDriver: one driver pack for every kind of hardware (catalog/drivers.v1.json; TypeScript port ts/src/drivers.ts, shared
vectors contract/vectors/drivers.v1.json). Pure rules:
  update_state(installed, now)   current, available (with its deadline), or overdue (hardware paused, virtual devices on)
  needs_install(kinds, installed) the attached kinds that need the pack, so the app asks to install it at once
  fallback(kind)                 the virtual device that stands in while the hardware is paused or missing
A sale is never blocked by a driver: overdue hardware pauses and its virtual device takes over (fiscal devices excepted: they
have no stand-in, so the screen says the fiscal device is waiting for the update, and the sale is still recorded)."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "drivers.v1.json"), encoding="utf-8") as _f:
    REGISTER = json.load(_f)
PACK, DAYS, KINDS = REGISTER["pack"], REGISTER["update_days"], {k["id"]: k for k in REGISTER["kinds"]}
DAY = 86400


def _v(s):
    return tuple(int(x) for x in s.split("."))


def releases():
    """Every release newer than nothing, newest last: the previous ones and the current pack."""
    return sorted(REGISTER["previous"] + [{"version": PACK["version"], "kind": PACK["kind"], "released_at": PACK["released_at"]}], key=lambda r: _v(r["version"]))


def update_state(installed, now):
    """installed: the version on the device (None = not installed). The strictest missing release sets the deadline."""
    if installed is None:
        return {"state": "not_installed", "latest": PACK["version"], "deadline": None, "hardware": "virtual"}
    missing = [r for r in releases() if _v(r["version"]) > _v(installed)]
    if not missing:
        return {"state": "current", "latest": PACK["version"], "deadline": None, "hardware": "on"}
    deadline = min(r["released_at"] + DAYS[r["kind"]] * DAY for r in missing)
    kind = min(missing, key=lambda r: r["released_at"] + DAYS[r["kind"]] * DAY)["kind"]
    if now >= deadline:
        return {"state": "overdue", "latest": PACK["version"], "deadline": deadline, "kind": kind, "hardware": "virtual"}
    return {"state": "available", "latest": PACK["version"], "deadline": deadline, "kind": kind, "hardware": "on"}


def needs_install(kinds, installed):
    """The attached hardware kinds that need LynkDriver while it is not installed (empty when it is)."""
    if installed is not None:
        return []
    return [k for k in kinds if k in KINDS]


def fallback(kind):
    return KINDS[kind]["virtual"]


def validate():
    problems = []
    for k in REGISTER["kinds"]:
        for c in k["connections"]:
            if c not in REGISTER["connections"]: problems.append(f"{k['id']}: unknown connection {c}")
    for r in releases():
        if r["kind"] not in DAYS: problems.append(f"{r['version']}: unknown kind {r['kind']}")
    if set(DAYS) != {"security", "required", "normal"}: problems.append("update kinds must be security, required and normal")
    return problems
