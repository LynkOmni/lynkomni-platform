"""Every Lynk name and its plain word (owner, 21 November 2026): catalog/names.v1.json is the one source.

Every Lynk name a person can see carries its plain word ("LynkStat (Analytics)"). Names stay the same in every language;
plain words (web/names, keys nm_<id>) and one-line descriptions (web/nameinfo, keys nma_<id>) are translated into every
language. ts/src/names.ts follows the same rules on every screen; tools/names_register.py writes the shared vectors and
ts/src/names.generated.ts, and tests/test_names.py keeps them in step."""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "names.v1.json"), encoding="utf-8") as _f:
    REGISTER = json.load(_f)
with open(os.path.join(ROOT, "web", "names", "strings.en.json"), encoding="utf-8") as _f:
    _PLAIN_EN = json.load(_f)
with open(os.path.join(ROOT, "web", "nameinfo", "strings.en.json"), encoding="utf-8") as _f:
    _INFO_EN = json.load(_f)

NAMES = REGISTER["names"]
BY_NAME = {n["name"]: n for n in NAMES}
BY_ID = {n["id"]: n for n in NAMES}
MAX_PLAIN = REGISTER["max_plain_chars"]
NOT_SHOWN = tuple(REGISTER["company"] + REGISTER["internal"] + REGISTER["retired"])
# Longest names first, so "LynkPOS" is never cut out of a longer name; a name never sits inside a longer word.
PATTERN = re.compile(r"(?<![A-Za-z])(" + "|".join(sorted((re.escape(n) for n in BY_NAME), key=len, reverse=True)) + r")(?![A-Za-z])")
ANY_LYNK = re.compile(r"(?<![A-Za-z])Lynk[A-Z][A-Za-z]*")


def plain_key(name):
    return f"nm_{BY_NAME[name]['id']}"


def about_key(name):
    e = BY_NAME[name]
    return f"nma_{e['id']}" if e.get("about", True) else None


def plain(name, texts=None):
    """The plain word in a language (texts = that language's names words); English when a word is missing."""
    k = plain_key(name)
    return (texts or {}).get(k) or _PLAIN_EN[k]


def about(name, texts=None):
    k = about_key(name)
    return ((texts or {}).get(k) or _INFO_EN[k]) if k else None


def find(text):
    """The registered names in a text, in order, with where each starts and ends."""
    return [{"name": m.group(1), "start": m.start(1), "end": m.end(1)} for m in PATTERN.finditer(text)]


def unknown(text):
    """Lynk words a person could see that the register does not know (the company name and internal or retired names aside)."""
    return [w for w in ANY_LYNK.findall(text) if w not in BY_NAME and not w.startswith(NOT_SHOWN)]


def label(name, texts=None, mode="brand_first"):
    """The words of a name label: "LynkStat (Analytics)", or "Analytics (LynkStat)" with plain words first."""
    p = plain(name, texts)
    return f"{p} ({name})" if mode == "plain_first" else f"{name} ({p})"


def part_of(name):
    """The product a service, feature or card group belongs to (its name), or None."""
    parent = BY_NAME[name].get("part_of")
    return BY_ID[parent]["name"] if parent else None
