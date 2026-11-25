#!/usr/bin/env python3
"""Phone numbering rules in every country pack (section 4C point 1, owner 2026-11-25). Rule 0.5: a country adds only data.

  phone.code        the dialling code, digits only (e.g. "237")
  phone.prefix      the national trunk prefix people may type first (e.g. "0"), cleaned away; "" when there is none
  phone.main        true for the country a shared dialling code belongs to first (e.g. "1"), so a pasted number picks it
  phone.mobile      {lengths, groups, sample}: numbers that can receive a text message
  phone.any         the same for every kind of number (landlines included), for fields that are not sent a text
      lengths       how many digits the number has after the dialling code
      groups        how the number is written in groups, per length (e.g. {"9": [1, 2, 2, 2, 2]})
      sample        an example number of the country, national digits only (shown labelled as an example)
  phone.source      where the rules come from

The rules come from the public worldwide numbering data (the phonenumbers package, Apache 2.0, a port of Google's
libphonenumber), read only by this tool, never by app code. A territory with no numbering plan of its own gets "phone": null
and its people choose the country whose numbers they use. The neutral sample pack XX gets labelled sample rules.
Owner, 2026-11-25: there is no rule about how a number starts (new networks can start numbers with any digit); only the length,
the groups, the sample and the dialling code are kept.
  python3 tools/country_phone.py          writes the rules into every pack
  python3 tools/country_phone.py --check  fails when a pack lacks them (tests/test_phone.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS = os.path.join(ROOT, "contract", "country-packs")
SAMPLE = {"code": "999", "prefix": "0", "main": True, "source": "sample rules for the neutral sample pack, never a real country",
          "mobile": {"lengths": [9], "groups": {"9": [3, 3, 3]}, "sample": "612345678"},
          "any": {"lengths": [9], "groups": {"9": [3, 3, 3]}, "sample": "612345678"}}


def _groups(region, digits):
    import phonenumbers
    try:
        n = phonenumbers.parse("+" + str(phonenumbers.country_code_for_region(region)) + digits, None)
        text = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        parts = text.split(" ", 1)[1] if " " in text else ""
        parts = [len("".join(c for c in g if c.isdigit())) for g in parts.replace("-", " ").split()]
        if parts and sum(parts) == len(digits) and (len(parts) > 1 or len(digits) <= 6): return parts
    except Exception:
        pass
    out, left = [], len(digits)
    while left > 4: out.append(3); left -= 3
    return out + ([left] if left else [])


def _kind(region, desc, general, example_desc):
    lengths = sorted(l for l in (desc.possible_length if desc and desc.possible_length and desc.possible_length[0] != -1 else general.possible_length) if l > 0)
    sample = (example_desc.example_number if example_desc and example_desc.example_number else None) or ""
    groups = {}
    for L in lengths:
        base = (sample + "0" * L)[:L] if sample else ""
        groups[str(L)] = _groups(region, base) if base else _groups(region, "0" * L)
    return {"lengths": lengths, "groups": groups, "sample": sample}


def rules(region):
    if region == "XX": return json.loads(json.dumps(SAMPLE))
    import phonenumbers
    from phonenumbers import PhoneMetadata
    md = PhoneMetadata.metadata_for_region(region)
    if not md: return None
    g = md.general_desc
    mob = md.mobile if md.mobile and md.mobile.national_number_pattern else None
    fixed = md.fixed_line if md.fixed_line and md.fixed_line.example_number else mob
    return {"code": str(md.country_code), "prefix": md.national_prefix or "", "main": phonenumbers.region_code_for_country_code(md.country_code) == region,
            "mobile": _kind(region, mob, g, mob), "any": _kind(region, g, g, mob or fixed),
            "source": f"worldwide numbering data (phonenumbers {phonenumbers.__version__}, Apache 2.0)"}


def main(argv):
    names = sorted(n for n in os.listdir(PACKS) if n.endswith(".json"))
    if "--check" in argv:
        bad = [n for n in names if "phone" not in json.load(open(os.path.join(PACKS, n), encoding="utf-8"))]
        if bad:
            print(f"{len(bad)} packs lack phone rules (run python3 tools/country_phone.py)"); return 1
        print("every pack has its phone rules"); return 0
    for n in names:
        path = os.path.join(PACKS, n)
        with open(path, encoding="utf-8") as f: p = json.load(f)
        p["phone"] = rules(p["code"])
        with open(path, "w", encoding="utf-8") as f: f.write(json.dumps(p, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote phone rules into {len(names)} packs"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
