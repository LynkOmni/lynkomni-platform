#!/usr/bin/env python3
"""Every country, from public standards, never typed by hand (owner rule 2026-11-09: one global platform; each country plugs in).

  python3 tools/country_packs.py           writes the generated packs, contract/countries.v1.json, contract/currencies.v1.json
                                           and design/fonts/language_waves.v1.json
  python3 tools/country_packs.py --check   fails when any of them is out of date (tests/test_countries.py)

Sources: the IANA time zone database's ISO 3166 country list (zone.tab) for the official list of countries and their time zones;
CLDR through Babel for country names in every interface language, legal-tender currencies (ISO 4217), currency decimals and
official languages with their share of speakers. A hand-curated pack (contract/country-packs/<CC>.json with "source": "curated")
is never overwritten: it holds facts a person confirmed. A generated pack carries only standards facts and marks the rest
unconfirmed: tax rate 0 until the lawyer confirms it, no fiscal workflow, the default price index, no partners.
The interface languages are design/fonts/scripts.v1.json; every official language not yet there is placed in a wave, by speakers."""
import json, os, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS = os.path.join(ROOT, "contract", "country-packs")
ZONE_TAB = "/usr/share/zoneinfo/zone.tab"
WAVE_SIZE = 10
BLOCKED_MCC = ["7995", "7801", "7802", "6051", "4829", "6211"]
FALLBACK_UI = "en"


def _zone_tab():
    """ISO 3166-1 alpha-2 code -> [time zones], from the IANA database (the same list the whole industry uses)."""
    out = defaultdict(list)
    with open(ZONE_TAB, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip(): continue
            code, _coords, zone = line.rstrip("\n").split("\t")[:3]
            out[code].append(zone)
    return dict(out)


def _registry():
    with open(os.path.join(ROOT, "design", "fonts", "scripts.v1.json"), encoding="utf-8") as f:
        return json.load(f)


def build():
    from babel import Locale
    from babel.core import get_global
    zones = _zone_tab()
    tender, langs_by_terr, fractions = get_global("territory_currencies"), get_global("territory_languages"), get_global("currency_fractions")
    reg = _registry(); ui = sorted(reg["languages"])
    names = {lang: Locale.parse(lang.replace("-", "_")) for lang in ui}
    countries, packs, currencies, unsupported = {}, {}, {}, defaultdict(float)
    for code in sorted(zones):
        cur = [c for c, start, end, is_tender in tender.get(code, []) if end is None and is_tender]
        currency = cur[0] if cur else "USD"                       # Antarctica has no tender currency
        for c in cur: currencies[c] = fractions.get(c, fractions["DEFAULT"])[0]
        spoken = langs_by_terr.get(code, {})
        official = sorted((l for l, v in spoken.items() if v.get("official_status") == "official"), key=lambda l: -spoken[l].get("population_percent", 0))
        regional = sorted((l for l, v in spoken.items() if v.get("official_status") in ("official_regional", "de_facto_official")), key=lambda l: -spoken[l].get("population_percent", 0))
        regional = [x for x in dict.fromkeys(_ui_code(l) for l in regional if l != "und") if x not in {_ui_code(o) for o in official}]
        if not official: official = sorted(spoken, key=lambda l: -spoken[l].get("population_percent", 0))[:1] or [FALLBACK_UI]
        official = list(dict.fromkeys(_ui_code(l) for l in official if l != "und")) or [FALLBACK_UI]   # "und" is CLDR for undetermined; Antarctica has no official language
        supported = [l for l in official if l in reg["languages"]]
        for l in official:
            if l not in reg["languages"]: unsupported[l] += 1 + sum(v.get("population_percent", 0) for k, v in spoken.items() if _ui_code(k) == l) / 100
        ui_first = supported[0] if supported else FALLBACK_UI
        countries[code] = {"code": code, "name": names["en"].territories.get(code, code), "names": {lang: loc.territories.get(code, names["en"].territories.get(code, code)) for lang, loc in names.items()},
                           "currency": currency, "currencies": cur, "tz": zones[code], "languages": official, "regional_languages": regional, "ui_language": ui_first}
        path = os.path.join(PACKS, f"{code}.json")
        old = json.load(open(path, encoding="utf-8")) if os.path.isfile(path) else {}
        if old.get("source") == "curated": continue
        packs[code] = {
            "name": countries[code]["name"], "code": code, "source": "standards",
            "currency": currency, "currencies": cur, "locale": f"{ui_first}-{code}", "languages": official, "regional_languages": regional, "ui_language": ui_first,
            "tz": zones[code][0], "time_zones": zones[code],
            "tax_rate": "0", "tax_confirmed": False, "fiscal": None, "fiscal_confirmed": False,
            "providers": ["card", "bank_transfer", "qr"], "flags": {}, "price_index": 1.0, "price_index_source": "default until finance sets it from purchasing power",
            "bbox": None, "payment_methods_note": "payment methods are the providers list: every product reads the same list",
            "card_networks": [], "wallets": [],
            "vcard": {"enabled": False, "issuer": None, "bin_sponsor": None, "blocked_mcc": BLOCKED_MCC, "monthly_cap_usd_max": 100000,
                      "note": "A pack alone never turns cards on. Needs a signed issuer agreement, legal sign-off and the activation checklist."},
            "vcard_card_networks_note": "set from the issuer contract, never assumed",
            "note": "Generated from ISO 3166, ISO 4217, IANA tz and CLDR by tools/country_packs.py. Tax, fiscal workflow, partners and price index stay unconfirmed until a person confirms them; then copy the facts in and set source to curated.",
        }
        # rule 0.5 fields written by tools/country_holidays.py (holidays, invoice numbering, legal text) are kept as they are
        packs[code].update({k: old[k] for k in ("holidays", "invoice_numbering", "legal_text", "storefront") if k in old})
    # curated packs must still list every currency they use
    for f in os.listdir(PACKS):
        p = json.load(open(os.path.join(PACKS, f), encoding="utf-8"))
        currencies[p["currency"]] = fractions.get(p["currency"], fractions["DEFAULT"])[0]
    waves = _waves(unsupported, reg)
    return countries, packs, dict(sorted(currencies.items())), waves


def _ui_code(lang):
    """CLDR language codes as the registry writes them: zh -> zh-Hans and zh_Hant -> zh-Hant; other script variants (sr_Latn,
    bs_Cyrl) fold into the base language, since one interface translation serves the language."""
    if lang == "zh": return "zh-Hans"
    if lang == "zh_Hant": return "zh-Hant"
    return lang.split("_")[0]


# Blueprint 43 G names wave 2 exactly (agreed 7 November 2026). Waves 1 and 2 are the only waves the blueprint defines; every
# other official language of a country pack is listed after them as "planned" so no country is forgotten, without a wave
# number or build section the blueprint has not given.
WAVE_2 = ("bn", "ta", "th", "am", "ha", "yo", "zu", "fil", "pl", "nl", "uk", "ms")


def _waves(unsupported, reg):
    """Wave 2 is the blueprint's list (43 G), minus any language already supported. Every other national official language not
    yet an interface language follows as planned, ordered by how many countries list it, then by share of speakers (CLDR
    gives shares per country, not head counts, so this is an order of work, not a census)."""
    supported = set(reg["languages"])
    wave2 = [l for l in WAVE_2 if l not in supported]
    rest = sorted((l for l in unsupported if l not in WAVE_2), key=lambda l: (-unsupported[l], l))
    out = []
    if wave2:
        out.append({"wave": 2, "source": "blueprint 43 G", "languages": [{"code": l, "name": _lang_name(l)} for l in wave2]})
    return {"version": 1, "description": "Interface languages still to add (design/fonts/scripts.v1.json holds the ones done). Wave 2 is the list in blueprint 43 G. 'planned' lists every other official language of a country pack, generated by tools/country_packs.py, so no country is left out; the blueprint has not placed them in a wave yet. Each language added: its script and fonts in scripts.v1.json, every emulator translated, the layout test passed. A country opens in its best supported language until its own arrives.",
            "supported": sorted(supported), "waves": out, "planned": [{"code": l, "name": _lang_name(l), "weight": round(unsupported[l], 3)} for l in rest]}


# English names CLDR does not carry (ISO 639-3 reference names).
_MORE_NAMES = {"zdj": "Ngazidja Comorian", "wni": "Ndzwani Comorian"}


def _lang_name(l):
    """The language's English name: its own locale when CLDR has one, else CLDR's English list of language names, else ISO 639-3."""
    from babel import Locale
    try: return Locale.parse(l.replace("-", "_")).get_display_name("en")
    except Exception: pass
    return Locale("en").languages.get(l) or _MORE_NAMES.get(l) or l


def main(check=False):
    countries, packs, currencies, waves = build()
    files = {os.path.join(ROOT, "contract", "countries.v1.json"): {"version": 1, "description": "Every country (ISO 3166-1, the IANA tz list) with its names in every interface language, currencies, time zones, official languages and the interface language it opens in. Generated by tools/country_packs.py; never typed by hand.", "count": len(countries), "countries": countries},
             os.path.join(ROOT, "design", "fonts", "language_waves.v1.json"): waves}
    for code, p in packs.items(): files[os.path.join(PACKS, f"{code}.json")] = p
    cur_path = os.path.join(ROOT, "contract", "currencies.v1.json")
    with open(cur_path, encoding="utf-8") as f: cur = json.load(f)
    cur["decimals"] = {**currencies, **{k: v for k, v in cur["decimals"].items()}}      # a hand-set decimal wins; every tender currency is present
    cur["decimals"] = dict(sorted(cur["decimals"].items()))
    files[cur_path] = cur
    stale = []
    for path, data in files.items():
        text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
        if check:
            if not os.path.isfile(path) or open(path, encoding="utf-8").read() != text: stale.append(os.path.relpath(path, ROOT))
        else:
            with open(path, "w", encoding="utf-8") as f: f.write(text)
    if check:
        if stale: print("out of date (run python3 tools/country_packs.py): " + ", ".join(stale[:8]) + (" ..." if len(stale) > 8 else "")); return 1
        print(f"country packs are current ({len(countries)} countries)"); return 0
    print(f"wrote {len(packs)} generated packs, contract/countries.v1.json ({len(countries)} countries), {len(cur['decimals'])} currencies, {len(waves['waves'])} language waves"); return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
