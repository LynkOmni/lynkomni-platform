#!/usr/bin/env python3
"""Storefront settings in every country pack (BIZZ & DEVICE, owner approved 2026-11-09). Rule 0.5: a country adds only data.

  storefront.seller_income_reporting  whether the law makes LynkOmni report what sellers earn (for example EU DAC7), and to whom:
                                      unknown until a lawyer confirms it for that country
  storefront.data_location            whether personal data must stay in the country: unknown until confirmed
  storefront.age_of_majority          the local age of majority when higher than 18 (null keeps the global 18)

Nothing is invented: every value starts unknown and unconfirmed (ledger item storefront_legal_review), and paid Storefront
selling stays off in a country until its partners and that review are done.
  python3 tools/country_storefront.py          writes the field into every pack (keeps confirmed values)
  python3 tools/country_storefront.py --check  fails when a pack lacks it (tests/test_sides.py)"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS = os.path.join(ROOT, "contract", "country-packs")
DEFAULT = {"seller_income_reporting": {"required": None, "to": None, "confirmed": False},
           "data_location": {"in_country": None, "confirmed": False},
           "age_of_majority": None,
           "note": "Set per country after the lawyer review (ledger item storefront_legal_review); unknown until then."}


def main(argv):
    names = sorted(n for n in os.listdir(PACKS) if n.endswith(".json"))
    if "--check" in argv:
        bad = [n for n in names if "storefront" not in json.load(open(os.path.join(PACKS, n), encoding="utf-8"))]
        if bad:
            print(f"{len(bad)} packs lack storefront settings (run python3 tools/country_storefront.py)"); return 1
        print("every pack has its storefront settings"); return 0
    for n in names:
        path = os.path.join(PACKS, n)
        with open(path, encoding="utf-8") as f: p = json.load(f)
        if "storefront" not in p:
            p["storefront"] = json.loads(json.dumps(DEFAULT))
        with open(path, "w", encoding="utf-8") as f: f.write(json.dumps(p, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote storefront settings into {len(names)} packs"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
