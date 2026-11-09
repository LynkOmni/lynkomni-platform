"""Text, USSD and voice channels for phones with no apps (BIZZ & DEVICE 48.17: the basic-phone device, interface phone.text).
One menu engine serves all three: a USSD session (the phone shows the pages the network sends), text messages (one command
per message) and a voice-call menu (the same pages read aloud, digits pressed). The engine is pure: it returns the page as word
keys with values, so every channel shows it in the person's language; the TypeScript port is ts/src/channels.ts and
contract/vectors/channels.v1.json proves they agree. The network side (USSD code, short code, voice number) belongs to a
licensed gateway per country (providers/registry.v1.json ussd_gateway), so the channel stays off until one is signed.

Rules: a sale is recorded only after the person's PIN; quantities are integer thousandths; a page fits one USSD screen
(USSD_MAX characters in English); agent, collection and partner requests are never offered here (online-only, enrolled devices).
"""
import re

USSD_MAX = 182
MENU = ("sell", "today", "stock", "help")
SCREENS = ("menu", "product", "qty", "pin", "done", "today", "stock", "help", "bye")


def start():
    return {"screen": "menu", "prod": None, "qty": None}


def page(state, ctx):
    """The page for a state: a list of (word key, values) lines. ctx: products [(name_key, price_text, level_text)], today (count, total_text)."""
    s = state["screen"]
    if s == "menu":
        return [("ch_title", {})] + [(f"ch_menu_{k}", {"n": i + 1}) for i, k in enumerate(MENU)] + [("ch_end", {"n": 0})]
    if s == "product":
        return [("ch_pick_product", {})] + [("ch_product_line", {"n": i + 1, "name": p[0], "price": p[1]}) for i, p in enumerate(ctx["products"])] + [("ch_back", {"n": 0})]
    if s == "qty":
        return [("ch_qty", {"name": ctx["products"][state["prod"]][0]})]
    if s == "pin":
        return [("ch_pin", {"qty": state["qty"], "name": ctx["products"][state["prod"]][0]})]
    if s == "done":
        return [("ch_sale_saved", {"receipt": ctx.get("receipt", "")})]
    if s == "today":
        return [("ch_today", {"count": ctx["today"][0], "total": ctx["today"][1]}), ("ch_back", {"n": 0})]
    if s == "stock":
        return [("ch_stock_line", {"name": p[0], "level": p[2]}) for p in ctx["products"]] + [("ch_back", {"n": 0})]
    if s == "help":
        return [("ch_help", {}), ("ch_back", {"n": 0})]
    return [("ch_bye", {})]


def step(state, text, ctx):
    """One reply from the person. Returns (new state, ends, action or None). The action {"sale": prod, "qty_milli": n} is
    returned only after a correct PIN (ctx["pin_ok"](text))."""
    s, t = dict(state), (text or "").strip()
    scr = s["screen"]
    if scr == "menu":
        if t == "0": s["screen"] = "bye"; return s, True, None
        if t.isdigit() and 1 <= int(t) <= len(MENU):
            s["screen"] = {"sell": "product", "today": "today", "stock": "stock", "help": "help"}[MENU[int(t) - 1]]
        return s, False, None
    if scr == "product":
        if t == "0": return start(), False, None
        if t.isdigit() and 1 <= int(t) <= len(ctx["products"]): s["prod"] = int(t) - 1; s["screen"] = "qty"
        return s, False, None
    if scr == "qty":
        if t.isdigit() and 1 <= int(t) <= 999: s["qty"] = int(t); s["screen"] = "pin"
        return s, False, None
    if scr == "pin":
        if ctx["pin_ok"](t):
            s["screen"] = "done"
            return s, True, {"sale": s["prod"], "qty_milli": s["qty"] * 1000}
        return start(), False, None                               # a wrong PIN records nothing and goes back to the menu
    if scr in ("today", "stock", "help"):
        return (start(), False, None) if t == "0" else (s, False, None)
    return s, True, None


def parse_sms(text):
    """A text-message command, the same numbers as the menu so it works in every language: "1 <product> <quantity> <PIN>" sells,
    "2" today's sales, "3" stock, "4" help. None when the message is not a command."""
    parts = re.split(r"\s+", (text or "").strip())
    if not parts or not parts[0].isdigit() or not 1 <= int(parts[0]) <= len(MENU):
        return None
    what = MENU[int(parts[0]) - 1]
    if what == "sell":
        if len(parts) != 4 or not all(x.isdigit() for x in parts[1:]) or int(parts[1]) < 1 or not 1 <= int(parts[2]) <= 999:
            return {"command": "help"}
        return {"command": "sell", "product": int(parts[1]) - 1, "qty_milli": int(parts[2]) * 1000, "pin": parts[3]}
    return {"command": what}


def render(lines, words):
    """English (or any language) text of a page; words maps keys to templates with {name} values."""
    out = []
    for key, vals in lines:
        w = words[key]
        out.append(re.sub(r"\{(\w+)\}", lambda m: str(vals.get(m.group(1), m.group(0))), w))
    return "\n".join(out)


class ChannelGateway:
    """A licensed gateway per country that gives LynkOmni a USSD code, a text-message short code and a voice-menu number, and
    passes each session to the engine above (providers/registry.v1.json ussd_gateway)."""
    def numbers(self, country):
        raise NotImplementedError


class SandboxChannelGateway(ChannelGateway):
    """SANDBOX: no real code or number exists until a gateway is signed, so it returns none and says so; screens show the
    channel's when_off state ("Coming to your country soon.") to real users and a labelled sample in the emulators."""
    def numbers(self, country):
        return {"country": country, "ussd": None, "sms": None, "voice": None, "status": "sandbox"}
