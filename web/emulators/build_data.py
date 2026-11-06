#!/usr/bin/env python3
"""Everything an emulator needs from the rest of LynkOmni, printed as JSON for web/build.mjs.
Logos and icons come from the brand module, pictures from the visuals module, words from the design tokens, the country
from the country pack and the on/off state from the provider ledger. Nothing here is typed by hand."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import brand, providers, visuals  # noqa: E402

COUNTRY = "RW"                                    # the pilot country of the contract (integer RWF)
METHOD_ITEMS = {"mobile_money": ["momo_mtn", "airtel_money"], "card": ["card_acquirer"]}


def svg(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    with open(os.path.join(ROOT, "contract", "country-packs", f"{COUNTRY}.json"), encoding="utf-8") as f:
        pack = json.load(f)
    with open(os.path.join(ROOT, "design", "tokens.v1.json"), encoding="utf-8") as f:
        states = json.load(f)["states"]
    icons = {i["id"] if isinstance(i, dict) else i: None for i in brand.manifest()["icons"]}
    icons = {i: brand.icon_svg(i) for i in icons}
    ITEMS = {i["id"]: i for i in providers.items()}
    off = providers.when_off("payments")
    ready = {m: {"ok": all(providers.item_status(ITEMS[i], COUNTRY) in providers.OK_STATUS for i in items), "message": off["message"]} for m, items in METHOD_ITEMS.items()}
    pic = {th: visuals.get(off["visual"], th) for th in ("light", "dark")}
    out = {
        "icons": icons,
        "brand": {"body": svg(brand.for_surface("device-body", "light").path),
                  "topLight": svg(brand.for_surface("app-top-bar", "light").path), "topDark": svg(brand.for_surface("app-top-bar", "dark").path),
                  "receipt": svg(brand.for_surface("receipt-header", "light", printing=True).path)},
        "pictures": {"offLight": svg(pic["light"].path), "offDark": svg(pic["dark"].path), "offAlt": pic["light"].alt},
        "states": {k: {"label": v["label"], "meaning": v["meaning"]} for k, v in states.items()},
        "pack": {"code": COUNTRY, "name": pack["name"], "currency": pack["currency"], "tz": pack["tz"], "locale": pack.get("locale", "en")},
        "ready": ready,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
