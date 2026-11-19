"""The build sections, in build order (web/showcase/showcase.v1.json is the one list). Section "7B" (LynkMotion and LynkGuard,
NEW UPDATE 1, owner approved 2026-11-10) is built right after section 7 and before section 8; "3A" (the Emulator Panel), "4B",
"8B" and "9B" (SIX SERVICES UPDATE) joined the same way. Every register that names a build section (automations, placements,
APIs, tracking kinds) takes its value from this list.

The "where every part is built" tables of the master blueprint (64.11 onward) live in catalog/build-tables.v1.json.
A build section is not locked until every row naming it is done there (blueprint 44 L; tests/test_build_tables.py)."""
import json, os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "web", "showcase", "showcase.v1.json"), encoding="utf-8") as _f:
    SECTIONS = json.load(_f)["sections"]
ORDER = [s["n"] for s in SECTIONS]
WITH_PEOPLE = [n for n in ORDER if n != 0]          # every section after Step 0 has screens people use
with open(os.path.join(_ROOT, "catalog", "build-tables.v1.json"), encoding="utf-8") as _f:
    TABLES = json.load(_f)["tables"]


def after(a, b):
    """True when section a is built after section b."""
    return ORDER.index(a) > ORDER.index(b)


def status(n):
    """The section's status in the one build order: "locked", "building" or "" (still to come)."""
    return next(s.get("status", "") for s in SECTIONS if str(s["n"]) == str(n))


def parts(n):
    """Every row of the tables that names section n, as (table id, update, row)."""
    return [(t["id"], t["update"], r) for t in TABLES for r in t["rows"] if str(n) in r["sections"]]


def missing(n):
    """The parts of section n still to build: rows that name it, have a part, and are not done there."""
    return [(tid, upd, r) for tid, upd, r in parts(n) if not r.get("nothing") and str(n) not in r.get("done", {})]


def tally(n):
    """(parts done, parts with work) for section n."""
    work = [r for _, _, r in parts(n) if not r.get("nothing")]
    return sum(1 for r in work if str(n) in r.get("done", {})), len(work)
