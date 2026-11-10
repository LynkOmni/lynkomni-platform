"""The build sections, in build order (web/showcase/showcase.v1.json is the one list). Section "7B" (LynkMotion and LynkGuard,
NEW UPDATE 1, owner approved 2026-11-10) is built right after section 7 and before section 8; every register that names a build
section (automations, placements, APIs, tracking kinds) takes its value from this list."""
import json, os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "web", "showcase", "showcase.v1.json"), encoding="utf-8") as _f:
    ORDER = [s["n"] for s in json.load(_f)["sections"]]
WITH_PEOPLE = [n for n in ORDER if n != 0]          # every section after Step 0 has screens people use


def after(a, b):
    """True when section a is built after section b."""
    return ORDER.index(a) > ORDER.index(b)
