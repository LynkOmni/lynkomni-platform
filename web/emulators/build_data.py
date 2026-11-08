#!/usr/bin/env python3
"""Everything an emulator needs from the rest of LynkOmni, printed as JSON for web/build.mjs.
Logos and icons come from the brand module, pictures from the visuals module, words from the design tokens, the country
from the country pack and the on/off state from the provider ledger. Nothing here is typed by hand."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import brand, providers, visuals  # noqa: E402
from services import translation  # noqa: E402

SAMPLE = "XX"                                     # the neutral sample pack: the emulator opens on it, never on a real country (Step 0, blueprint 42 A)
METHOD_ITEMS = {"mobile_money": ["momo_mtn", "airtel_money"], "card": ["card_acquirer"]}


def svg(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def language_packs(emulator):
    """English from strings.en.json plus every machine-translated pack in i18n/ that was made from that exact English.
    A missing or out-of-date pack is left out here (the screen falls back to English) and fails tests/test_translation_packs.py."""
    base = os.path.join(ROOT, "web", "emulators", emulator)
    with open(os.path.join(base, "strings.en.json"), encoding="utf-8") as f:
        source = json.load(f)
    fresh = translation.build_pack(source, "en")["source_sha256"]
    out = {}
    for lang in translation.languages():
        if lang == "en":
            pack = translation.build_pack(source, "en")
        else:
            path = os.path.join(base, "i18n", f"{lang}.json")
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as f:
                pack = json.load(f)
            if pack.get("source_sha256") != fresh:
                continue
        out[lang] = {"native": pack["native"], "dir": pack["dir"], "texts": pack["texts"]}
    return out


# The services shown in the merchant app's Business tab: (service in core.regions, product family name, icon).
# LynkInv and LynkCRM join this list in build section 4, once their product icons are released in lynkomni-icons;
# LynkStat keeps the product-dash icon until its own mark is released there in the same section (provider ledger: ops_product_icons).
SERVICES = [("pos", "LynkPOS", "product-pos"), ("accountant", "LynkAcc", "product-ledger"), ("inventory", "LynkStock", "product-stock"),
            ("dashboard", "LynkStat", "product-dash"), ("intelligence", "LynkGrow", "product-grow"), ("chat", "LynkChat", "product-chat"),
            ("payments", "LynkMPay", "product-mpay"), ("paylinks", "LynkCheckout", "product-checkout"), ("loyalty", "LynkRewards", "product-rewards"),
            ("recovery", "LynkRecover", "product-recover"), ("vcard", "LynkVCard", "product-vcard")]


def icons_used(emulator):
    """Only the icons an emulator can show go into its file (size budget): every id written in its sources and in the shared
    TypeScript it bundles, plus the five status icons and the product marks, which screens pick by name at run time."""
    import re
    text = ""
    for folder in (os.path.join(ROOT, "web", "emulators", emulator), os.path.join(ROOT, "ts", "src")):
        for name in os.listdir(folder):
            if name.endswith((".ts", ".html")) and not name.endswith(".generated.ts"):
                with open(os.path.join(folder, name), encoding="utf-8") as f:
                    text += f.read()
    all_ids = [i["id"] if isinstance(i, dict) else i for i in brand.manifest()["icons"]]
    return sorted(i for i in all_ids if i.startswith(("status-", "product-")) or re.search(r"[\"'`/:]" + re.escape(i) + r"[\"'`@]", text))


def country_packs():
    """Every country pack as the emulator's country chooser sees it, the sample pack first. What works in a country is read
    from the provider ledger, so a pack alone never switches a partner-backed method or service on."""
    ITEMS = {i["id"]: i for i in providers.items()}
    off = providers.when_off("payments")
    packs_dir = os.path.join(ROOT, "contract", "country-packs")
    out = {}
    for name in sorted(os.listdir(packs_dir)):
        with open(os.path.join(packs_dir, name), encoding="utf-8") as f:
            pack = json.load(f)
        code = pack["code"]
        out[code] = {
            "code": code, "name": pack["name"], "currency": pack["currency"], "tz": pack["tz"], "locale": pack.get("locale", "en"),
            "sample": code == SAMPLE,
            "ready": {m: {"ok": all(providers.item_status(ITEMS[i], code) in providers.OK_STATUS for i in items), "message": off["message"]} for m, items in METHOD_ITEMS.items()},
            "services": [{"service": sv, "name": nm, "icon": ic, "state": providers.availability(sv, code)["state"]} for sv, nm, ic in SERVICES],
        }
    return {SAMPLE: out.pop(SAMPLE), **out}


def main(emulator):
    with open(os.path.join(ROOT, "design", "tokens.v1.json"), encoding="utf-8") as f:
        states = json.load(f)["states"]
    icons = {i: brand.icon_svg(i) for i in icons_used(emulator)}
    packs = country_packs()
    off = providers.when_off("payments")
    pic = {th: visuals.get(off["visual"], th) for th in ("light", "dark")}
    # every screen state's picture (blueprint 41 B: every state is designed), in both themes and the sunlight contrast set
    state_pics = {}
    for need_id in ("state-offline", "state-error", "state-not-found", "state-no-results", "state-success", "state-permission", "state-maintenance", "state-sync-pending", "state-coming-soon"):
        state_pics[need_id] = {}
        for th in ("light", "dark"):
            v = visuals.get(need_id, th)
            state_pics[need_id][th] = {"svg": svg(v.path), "alt": v.alt}
            if th == "light":                                   # sunlight is a light mode: its contrast set rides on the light picture
                state_pics[need_id][th]["contrast"] = svg(visuals.get(need_id, th, "sunlight").path)
    with open(os.path.join(ROOT, "catalog", "addresses.v1.json"), encoding="utf-8") as f:
        addresses = json.load(f)
    out = {
        "icons": icons,
        "brand": {"body": svg(brand.for_surface("device-body", "light").path),
                  "topLight": svg(brand.for_surface("app-top-bar", "light").path), "topDark": svg(brand.for_surface("app-top-bar", "dark").path),
                  "receipt": svg(brand.for_surface("receipt-header", "light", printing=True).path)},
        "pictures": {"offLight": svg(pic["light"].path), "offDark": svg(pic["dark"].path), "offAlt": pic["light"].alt},
        "states": {k: {"label": v["label"], "meaning": v["meaning"]} for k, v in states.items()},
        "packs": packs, "packOrder": list(packs),   # the country chooser: the sample pack first, then every real pack
        "statePictures": state_pics,
        "addresses": {k: addresses[k] for k in ("hosts", "website_paths", "app_paths", "account_paths", "pay_paths", "shop_paths", "staff_paths", "redirects")},
        "i18n": language_packs(emulator),
    }
    json.dump(out, sys.stdout, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "pos-terminal")
