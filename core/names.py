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


# ---------------------------------------------------------------- the 15 improvements (owner, 21 November 2026, v0.81.0)
FAMILY = {f: n for n in NAMES for f in ([n["family"]] if n.get("family") else n.get("families", []))}   # LynkMotion has three ladders (Land, Sea, Air)
NOW_CALLED = {x["old"]: x for x in REGISTER["now_called"]}
SIMILAR = REGISTER["similar"]
FAMILIAR_AFTER = REGISTER["familiar_after"]
CHECK = REGISTER["plain_word_check"]
_CAPS = re.compile(r"(?<![A-Za-z])[A-Z]{2,}(?![A-Za-z])")


def for_family(family):
    """The registered name of a billing family (or None, e.g. for the Storefront plan, which is a plain word)."""
    e = FAMILY.get(family)
    return e["name"] if e else None


def icon_of(name):
    """The product mark a name shows beside it (brand.icon id), or None."""
    return BY_NAME[name].get("icon")


def spoken(name):
    """How to say a name aloud: "Link Stat", "Link P O S"."""
    return BY_NAME[name]["spoken"]


def speakable(text):
    """A text ready to be read aloud: every registered name replaced by its spoken form."""
    return PATTERN.sub(lambda m: spoken(m.group(1)), text)


def now_called(old):
    """The name a retired name is now called, or None."""
    x = NOW_CALLED.get(old)
    return BY_ID[x["id"]]["name"] if x else None


def similar(name):
    """The other names a name could be confused with, in register order."""
    i = BY_NAME[name]["id"]
    out = []
    for g in SIMILAR:
        if i in g["names"]:
            out += [BY_ID[x]["name"] for x in g["names"] if x != i and BY_ID[x]["name"] not in out]
    return out


def check_plain(word):
    """Why a plain word is not plain enough ([] when it is): a short form in capitals, a Lynk name or a technical word."""
    bad = [c for c in _CAPS.findall(word) if c not in CHECK["allowed_short"]]
    bad += [w for w in CHECK["words_never"] if re.search(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", word, re.I)]
    if "Lynk" in word:
        bad.append("Lynk")
    return sorted(set(bad))


def explain_text(text, texts=None, mode="brand_first", seen=None):
    """A message or document text with the first mention of each name followed by its plain word in brackets (or the plain word
    first). seen carries the names already explained earlier in the same message, so a title and its lines explain each name once."""
    seen = set() if seen is None else seen
    def one(m):
        n = m.group(1)
        if n in seen:
            return n
        seen.add(n)
        return label(n, texts, mode)
    return PATTERN.sub(one, text)


def paper_lines(lines, texts=None, width=32):
    """The lines a printed receipt or a document sent to a customer ends with: one "LynkCheckout: Pay links & QR" line for each
    name it shows, wrapped to the paper's width. Nothing when it shows none."""
    out = []
    for n in dict.fromkeys(f["name"] for line in lines for f in find(line)):
        words, row = f"{n}: {plain(n, texts)}".split(" "), ""
        for w in words:
            if row and len(row) + 1 + len(w) > width:
                out.append(row)
                row = "  " + w
            else:
                row = f"{row} {w}" if row else w
        out.append(row)
    return out


def bill_label(family, tier_word, texts=None):
    """A line of LynkOmni's own bill: "LynkStat Plus (Analytics)"; the Storefront plan is a plain word already."""
    n = for_family(family)
    return f"{n} {tier_word} ({plain(n, texts)})" if n else tier_word


def asks_report(counts, min_shown=None):
    """Staff view of how often each name had to be explained: totals only, nothing below the minimum (5)."""
    low = REGISTER["asks"]["min_shown"] if min_shown is None else min_shown
    return {k: v for k, v in sorted(counts.items()) if v >= low}
