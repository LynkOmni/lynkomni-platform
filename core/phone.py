"""Phone number and email checks (section 4C point 1, owner 2026-11-25). The rules come only from the country pack's "phone"
block (tools/country_phone.py); nothing here names a country. ts/src/phone.ts is the TypeScript port and
contract/vectors/phone.v1.json (python3 tools/phone_vectors.py) keeps the two the same.

A phone field keeps national digits only and the chosen country. As the person types it says:
  empty      nothing typed yet (the field shows the country's sample as its placeholder)
  long       more digits than the country's numbers have (the field never takes them)
  typing     fine so far, not complete yet
  ok         a number of one of the country's lengths
and on submit a "typing" number is "short". There is no rule about how a number starts (owner, 2026-11-25: new networks can start
numbers with any digit). Every number is saved one way: + dialling code + national digits."""
import json, os, re, unicodedata

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PACKS = os.path.join(_ROOT, "contract", "country-packs")
_CACHE = {}
GENERIC = {"code": "", "prefix": "", "main": False, "mobile": {"lengths": list(range(4, 16)), "groups": {}, "sample": ""},
           "any": {"lengths": list(range(4, 16)), "groups": {}, "sample": ""}}


def rules(country):
    """The phone rules of a country pack; a territory with no numbering plan of its own gets the general rules (4 to 15 digits)."""
    if country not in _CACHE:
        path = os.path.join(_PACKS, f"{country}.json")
        r = None
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f: r = json.load(f).get("phone")
        _CACHE[country] = r or GENERIC
    return _CACHE[country]


def all_codes():
    """Every pack's dialling code, for reading a number pasted with + and a code."""
    out = {}
    for n in sorted(os.listdir(_PACKS)):
        if not n.endswith(".json") or n == "XX.json": continue
        r = rules(n[:-5])
        if r.get("code"): out.setdefault(r["code"], []).append(n[:-5])
    return out


def _kind(r, mobile):
    return r["mobile"] if mobile else r["any"]


def ascii_digits(text):
    """Every decimal digit of any script (Arabic-Indic, Devanagari, Bengali, Thai, full width and the rest) as 0 to 9."""
    return "".join(str(unicodedata.decimal(c)) if not c.isascii() and unicodedata.decimal(c, None) is not None else c for c in (text or ""))


def clean(r, text):
    """Digits only, with the trunk prefix people dial at home taken off: a leading 0 as soon as more digits follow it (a number
    after the dialling code never starts with the 0 people dial at home), any other prefix (1, 8, 06) only when the number is too
    long with it and the right length without it, since some numbers there do start with that digit."""
    d = re.sub(r"[^0-9]", "", ascii_digits(text))
    p = r.get("prefix") or ""
    m = r["mobile"]["lengths"]
    if p and d.startswith(p) and len(d) > len(p) and (p == "0" or len(d) > max(r["any"]["lengths"]) or (len(d) not in m and len(d) - len(p) in m)):
        d = d[len(p):]
    return d


def read_pasted(text, current, codes=None):
    """A number pasted or typed with + and a dialling code: (country, national digits). The current country is kept when its
    code matches; otherwise the country the code belongs to first (phone.main), else the first with that code."""
    t = ascii_digits(text or "").strip()
    if not t.startswith("+") and not t.startswith("00"):
        return current, clean(rules(current), t)
    d = re.sub(r"[^0-9]", "", t)
    if t.startswith("00"): d = d[2:]
    codes = codes or all_codes()
    for n in (3, 2, 1):
        cc, rest = d[:n], d[n:]
        if cc in codes:
            if rules(current).get("code") == cc: return current, clean(rules(current), rest)
            best = next((c for c in codes[cc] if rules(c).get("main")), codes[cc][0])
            return best, clean(rules(best), rest)
    return current, clean(rules(current), d)


def check(r, digits, mobile=True, submit=False):
    """{"state", "lengths", "max"} for national digits typed so far (see the module notes)."""
    k = _kind(r, mobile)
    out = {"lengths": k["lengths"], "max": max(k["lengths"])}
    if not digits: return {**out, "state": "empty"}
    if len(digits) > out["max"]: return {**out, "state": "long"}
    if len(digits) in k["lengths"]: return {**out, "state": "ok"}
    return {**out, "state": "short" if submit else "typing"}


def accept(r, digits, mobile=True):
    """What a field keeps of what was typed: never more digits than the country's longest number."""
    return digits[:max(_kind(r, mobile)["lengths"])]


def groups(r, digits, mobile=True):
    """The number written in the country's groups; a partial number follows the groups of the longest length it can still be."""
    k = _kind(r, mobile)
    g = k["groups"].get(str(len(digits)))
    if not g:
        fits = [int(L) for L in k["groups"] if int(L) >= len(digits)]
        g = k["groups"].get(str(min(fits))) if fits else None
    if not g: return digits
    out, i = [], 0
    for n in g:
        if i >= len(digits): break
        out.append(digits[i:i + n]); i += n
    if i < len(digits): out.append(digits[i:])
    return " ".join(out)


def sample(r, mobile=True):
    k = _kind(r, mobile)
    return groups(r, k["sample"], mobile) if k["sample"] else ""


def international(r, digits):
    """The one saved form: + dialling code + national digits."""
    return "+" + (r.get("code") or "") + digits


def lengths_text(lengths):
    """"9", "8 or 9", "4 to 15": the lengths as the error says them (digits only; the words come from the screen's language)."""
    ls = sorted(lengths)
    if len(ls) == 1: return {"one": ls[0]}
    if ls == list(range(ls[0], ls[-1] + 1)) and len(ls) > 2: return {"from": ls[0], "to": ls[-1]}
    return {"list": ls}


# ---- email -----------------------------------------------------------------------------------------------------------------
with open(os.path.join(_ROOT, "catalog", "email-domains.v1.json"), encoding="utf-8") as _f:
    _DOMAINS = json.load(_f)
COMMON, THROWAWAY = _DOMAINS["common"], set(_DOMAINS["throwaway"])
_EMAIL = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\.[A-Za-z]{2,}$")


def _distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def check_email(text, deep=False):
    """{"state": "empty" | "format" | "throwaway" | "ok", "suggest": a corrected address or ""}. A domain one or two letters
    away from a common one is offered as "Did you mean"; throwaway domains are refused only for deep identity (point 4)."""
    t = (text or "").strip()
    if not t: return {"state": "empty", "suggest": ""}
    if len(t) > 254 or not _EMAIL.match(t) or ".." in t: return {"state": "format", "suggest": ""}
    local, domain = t.rsplit("@", 1)
    d = domain.lower()
    suggest = ""
    if d not in COMMON:
        near = sorted((_distance(d, c), c) for c in COMMON)
        if near and 0 < near[0][0] <= (2 if len(d) >= 8 else 1): suggest = f"{local}@{near[0][1]}"
    if deep and d in THROWAWAY: return {"state": "throwaway", "suggest": ""}
    return {"state": "ok", "suggest": suggest}
