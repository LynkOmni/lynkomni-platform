#!/usr/bin/env python3
"""Everything an emulator needs from the rest of LynkOmni, printed as JSON for web/build.mjs.
Logos and icons come from the brand module, pictures from the visuals module, words from the design tokens, the country
from the country pack and the on/off state from the provider ledger. Nothing here is typed by hand."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import brand, providers, visuals  # noqa: E402
from services import billing, translation  # noqa: E402
from core.money import USD_RATES  # noqa: E402

SAMPLE = "XX"                                     # the neutral sample pack: the emulator opens on it, never on a real country (Step 0, blueprint 42 A)
METHOD_ITEMS = {"mobile_money": ["momo_mtn", "airtel_money"], "card": ["card_acquirer"]}


def svg(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# Shared word packs: an emulator that imports the module carries the folder's words too (one translation, used everywhere).
SHARED_WORDS = (("ts/src/shell.js", os.path.join("web", "shell")), ("ts/src/deviceshell.js", os.path.join("web", "shell")), ("ts/src/trackview.js", os.path.join("web", "tracking")), ("ts/src/emulator.js", os.path.join("web", "pos")), ("ts/src/footer.js", os.path.join("web", "footer")))


def uses_shell(emulator):
    """An emulator built on the shared shell (ts/src/shell.ts) also carries the shell's own words (web/shell)."""
    with open(os.path.join(ROOT, "web", "emulators", emulator, "app.ts"), encoding="utf-8") as f:
        return "ts/src/shell.js" in f.read()


def shared_folders(emulator):
    with open(os.path.join(ROOT, "web", "emulators", emulator, "app.ts"), encoding="utf-8") as f:
        src = f.read()
    return list(dict.fromkeys(folder for module, folder in SHARED_WORDS if module in src and os.path.isdir(os.path.join(ROOT, folder))))


def _packs(base):
    """English from strings.en.json plus every pack in i18n/ that was made from that exact English.
    A missing or out-of-date pack is left out here (the screen falls back to English) and fails tests/test_translation_packs.py."""
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


def used_keys(emulator, keys):
    """The shared POS words an emulator can show: every key written as a string in its app.ts or in the shared TypeScript it
    bundles, and every key under a prefix it builds at run time (t(`svc_${...}`)). Only those travel in its file (size budget)."""
    import re
    src = ""
    for path in [os.path.join(ROOT, "web", "emulators", emulator, "app.ts")] + [os.path.join(ROOT, "ts", "src", f) for f in os.listdir(os.path.join(ROOT, "ts", "src")) if f.endswith(".ts") and not f.endswith(".generated.ts")]:
        with open(path, encoding="utf-8") as f: src += f.read()
    literal = set(re.findall(r"[\"'`]([a-z][a-z0-9_]*)[\"'`]", src))
    prefixes = set(re.findall(r"`([a-z][a-z0-9_]*_)\$\{", src))
    return {k for k in keys if k in literal or any(k.startswith(p) for p in prefixes)}



def storefront_plans():
    """Storefront plans for My Storefront (services/billing.py, locked) and the minimum account age (core/workspaces.py)."""
    from services import billing
    from core import workspaces
    return {"tiers": list(billing.STOREFRONT_TIERS), "prices_usd": dict(zip(billing.STOREFRONT_TIERS, billing.STOREFRONT_PRICES)),
            "share_bps": dict(zip(billing.STOREFRONT_TIERS, billing.STOREFRONT_SHARE_BPS)), "min_age": workspaces.minimum_age()}

def language_packs(emulator):
    """The emulator's own words, plus the shared shell's or POS devices' words when it uses them (one translation, used everywhere)."""
    own = _packs(os.path.join(ROOT, "web", "emulators", emulator))
    for folder in shared_folders(emulator):
        shared = _packs(os.path.join(ROOT, folder))
        if folder.endswith("pos") or (folder.endswith("shell") and emulator not in ("browser-frame", "account-site")):   # devices carry only the shell words they can show
            keep = used_keys(emulator, shared.get("en", {}).get("texts", {}).keys())
            shared = {lang: {**v, "texts": {k: x for k, x in v["texts"].items() if k in keep}} for lang, v in shared.items()}
        own = {lang: {**own[lang], "texts": {**shared[lang]["texts"], **own[lang]["texts"]}} for lang in own if lang in shared}
    return own


# The services shown in the merchant app's Business tab: (service in core.regions, product family name, icon).
# LynkInv and LynkCRM join this list in build section 4, once their product icons are released in lynkomni-icons;
# LynkStat keeps the product-dash icon until its own mark is released there in the same section (provider ledger: ops_product_icons).
SERVICES = [("pos", "LynkPOS", "product-pos"), ("accountant", "LynkAcc", "product-ledger"), ("inventory", "LynkStock", "product-stock"),
            ("dashboard", "LynkStat", "product-dash"), ("intelligence", "LynkGrow", "product-grow"), ("chat", "LynkChat", "product-chat"),
            ("payments", "LynkMPay", "product-mpay"), ("paylinks", "LynkCheckout", "product-checkout"), ("loyalty", "LynkRewards", "product-rewards"),
            ("recovery", "LynkRecover", "product-recover"), ("vcard", "LynkVCard", "product-vcard")]


# Each product's footer id, whose plain word ("Accounting") travels beside its short name everywhere it is listed (web/footer ft_plain_<id>).
PLAIN_ID = {"LynkPOS": "pos", "LynkAcc": "acc", "LynkStock": "stock", "LynkStat": "stat", "LynkGrow": "grow", "LynkChat": "chat", "LynkMPay": "mpay",
            "LynkCheckout": "checkout", "LynkRewards": "rewards", "LynkRecover": "recover", "LynkVCard": "vcard"}


# The brand places the screens ask for (brand/surfaces.v1.json): each place lists its choices in order with the smallest
# width each needs, so the screen picks by the room it has (ts/src/brand.ts markFor). Screens never name a logo file.
BRAND_PLACES = ("app-top-bar", "web-header", "side-menu", "auth-onboarding", "customer-welcome", "web-footer")


def brand_places():
    out = {}
    for sid in BRAND_PLACES:
        s = brand.surface(sid)
        out[sid] = [{"asset": c["asset"], "minWidthPx": c.get("minWidthPx", 0),
                     **{th: svg(brand.asset(c["asset"], th).path) for th in ("light", "dark")}} for c in s["choose"]]
    return out


def entitlement(family, tier):
    out = {}
    for d in billing.FEATURES[family][: billing.FAMILIES[family][2].index(tier) + 1]:
        out.update(d)
    return out


def automations(section):
    """The automations of a build section as the owner's control panel lists them (catalog/automations.v1.json is the register)."""
    with open(os.path.join(ROOT, "catalog", "automations.v1.json"), encoding="utf-8") as f:
        reg = json.load(f)["automations"]
    return [{"id": a["id"], "level": a["level"], "assist": a.get("assist"), "trigger": a["trigger"], "min_tier": a.get("min_tier"), "default": a.get("default", "on")} for a in reg if a["build_section"] == section]


def business_app():
    """The Business app register (catalog/business-app.v1.json: every screen, its items and its address), the section 3
    automations and the LynkPOS standard prices from billing (locked prices) for the plans screen."""
    with open(os.path.join(ROOT, "catalog", "business-app.v1.json"), encoding="utf-8") as f:
        reg = json.load(f)
    return {"screens": [{"id": s["id"], "path": s["path"], "items": s["items"]} for s in reg["screens"]],
            "plans": list(billing.FAMILIES["lynkpos"][3]), "automations": [{"id": a["id"], "level": a["level"]} for a in automations(3)],
            "workspaces": json.load(open(os.path.join(ROOT, "catalog", "workspaces.v1.json"), encoding="utf-8"))}


def cards():
    """The LynkVCard faces and backs (visuals/cards.py, approved spec) and the tier limits, labelled placeholders, from billing."""
    out = {}
    for tier, face in zip(billing.FAMILIES["lynkvcard"][2], ("edge", "hub", "core", "omni")):
        f, b = visuals.get(f"vcard-{face}", "light"), visuals.get(f"vcard-{face}-back", "light")
        out[tier] = {"face": face, "front": svg(f.path), "front_alt": f.alt, "back": svg(b.path), "back_alt": b.alt, "price_usd": billing.FAMILIES["lynkvcard"][3][billing.FAMILIES["lynkvcard"][2].index(tier)],
                     "limits": entitlement("lynkvcard", tier)}
    near = visuals.get("vcard-core-near-limit", "light")
    return {"cards": out, "nearLimit": {"svg": svg(near.path), "alt": near.alt}}


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
        # Every country (247 ISO countries plus the sample) travels in each emulator, so the data is kept compact: the service
        # catalog is listed once (serviceCatalog) and a pack carries only its state letters; web/build.mjs inflates them back
        # into pack.services and pack.ready before the app starts. Country names in the person's language come from the
        # browser's own Intl.DisplayNames at run time (no 26-language name table in the file).
        out[code] = {
            "code": code, "name": pack["name"], "currency": pack["currency"], "tz": pack["tz"], "locale": pack.get("locale", "en"), "ui": pack.get("ui_language", "en"),
            "sample": code == SAMPLE,
            "ok": "".join("1" if all(providers.item_status(ITEMS[i], code) in providers.OK_STATUS for i in items) else "0" for items in METHOD_ITEMS.values()),
            "st": "".join("a" if providers.availability(sv, code)["state"] == "available" else "c" for sv, _, _ in SERVICES),
            # the payment methods the footer lists for this country (section 26 D: only what its pack supports)
            "card_networks": pack.get("card_networks") or [], "wallets": pack.get("wallets") or [], "providers": pack.get("providers") or [],
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
                  "receipt": svg(brand.for_surface("receipt-header", "light", printing=True).path),
                  "places": brand_places(),
                  # the browser tab icon (brand surface "favicon"): the light-theme emblem for light browsers, the dark-theme emblem for dark ones
                  "favicon": {th: svg(brand.for_surface("favicon", th).path) for th in ("light", "dark")}},
        "pictures": {"offLight": svg(pic["light"].path), "offDark": svg(pic["dark"].path), "offAlt": pic["light"].alt},
        "states": {k: {"label": v["label"], "meaning": v["meaning"]} for k, v in states.items()},
        "packs": packs, "packOrder": list(packs),   # the country chooser: the sample pack first, then every real pack
        "serviceCatalog": [{"service": sv, "name": nm, "icon": ic, "plain": PLAIN_ID[nm]} for sv, nm, ic in SERVICES], "methods": list(METHOD_ITEMS), "offMessage": off["message"],
        # what each LynkPOS plan allows (billing FEATURES merged up to the tier) and the PLACEHOLDER rates behind the second-currency estimate (core/money.py, ledger fx_rates)
        "entitlements": {tier: entitlement("lynkpos", tier) for tier in billing.FAMILIES["lynkpos"][2]}, "checkout": {tier: entitlement("lynkcheckout", tier) for tier in billing.FAMILIES["lynkcheckout"][2]},
        "fx": {k: float(v) for k, v in USD_RATES.items()},
        **(cards() if emulator == "vcard-card" else {}),
        **({"automations": automations(3)} if emulator == "owner-web" else {}),
        **({"storefront": storefront_plans()} if emulator in ("account-site", "merchant-phone") else {}),
        **(business_app() if emulator == "merchant-phone" else {}),
        # the agent point picture on the agent home (visuals need agent-point), in both themes; its text alternative is a translated screen text
        **({"agentPicture": {th: svg(visuals.get("agent-point", th).path) for th in ("light", "dark")}} if emulator == "merchant-phone" else {}),
        "statePictures": state_pics,
        "addresses": {k: addresses[k] for k in ("hosts", "website_paths", "app_paths", "account_paths", "pay_paths", "shop_paths", "staff_paths", "redirects")},
        "i18n": language_packs(emulator),
    }
    json.dump(out, sys.stdout, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "pos-terminal")
