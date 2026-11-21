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


# ---- LynkQueue for a person with a basic phone (NEW UPDATE 4, LynkQ; build section 3B): the place's short code or number.
# The same number menu by USSD, by text message and read aloud on a voice call. No account and no name; the phone number is
# kept only for that ticket's messages. The queue keeper alone gives the ticket number: the menu only asks.
Q_LATE, Q_LEAVE = 8, 9             # by text message: 8 is Running late, 9 is Leave queue (so a place can offer up to 7 sections by text)


def queue_start(has_ticket=False):
    return {"screen": "ticket" if has_ticket else "sections"}


def queue_page(state, ctx):
    """ctx: place (text), sections [[name, waiting, about_minutes, open]], ticket None or {"number", "place", "minutes", "state", "late_used"}."""
    s = state["screen"]
    if s == "sections":
        return [("ch_q_title", {"place": ctx["place"]})] + [("ch_q_section" if sec[3] else "ch_q_section_closed", {"n": i + 1, "name": sec[0], "waiting": sec[1], "minutes": sec[2]})
                                                              for i, sec in enumerate(ctx["sections"])] + [("ch_end", {"n": 0})]
    if s == "ticket":
        tk = ctx["ticket"]
        if tk["state"] != "waiting":
            return [("ch_q_called" if tk["state"] == "called" else "ch_q_over", {"number": tk["number"], "counter": tk.get("counter", "")})]
        return [("ch_q_ticket", {"number": tk["number"], "place": tk["place"], "minutes": tk["minutes"]})] + ([] if tk["late_used"] else [("ch_q_late", {"n": 1})]) + [("ch_q_leave", {"n": 2}), ("ch_end", {"n": 0})]
    if s == "left":
        return [("ch_q_left", {})]
    return [("ch_bye", {})]


def queue_step(state, text, ctx):
    """One reply. Returns (new state, ends, action or None). Actions: {"join": section index}, {"running_late": True}, {"leave": True};
    the caller asks the cloud, which passes it to the place's queue keeper."""
    s, t = dict(state), (text or "").strip()
    if s["screen"] == "sections":
        if t == "0": s["screen"] = "bye"; return s, True, None
        if t.isdigit() and 1 <= int(t) <= len(ctx["sections"]) and ctx["sections"][int(t) - 1][3]:
            s["screen"] = "ticket"; return s, False, {"join": int(t) - 1}
        return s, False, None
    if s["screen"] == "ticket":
        tk = ctx["ticket"]
        if t == "0" or tk["state"] != "waiting": s["screen"] = "bye"; return s, True, None
        if t == "1" and not tk["late_used"]: return s, False, {"running_late": True}
        if t == "2": s["screen"] = "left"; return s, True, {"leave": True}
        return s, False, None
    return s, True, None


def parse_queue_sms(text, sections):
    """A text message to the place's number: the section's number joins, 8 is Running late, 9 is Leave queue. None when it is not a command."""
    t = (text or "").strip()
    if not t.isdigit(): return None
    n = int(t)
    if n == Q_LATE: return {"command": "running_late"}
    if n == Q_LEAVE: return {"command": "leave"}
    if 1 <= n <= min(sections, Q_LATE - 1): return {"command": "join", "section": n - 1}
    return None


# ---- LynkSurvey for a person with a basic phone (NEW UPDATE 4, LynkS; build section 3B): the organisation's short code or number.
# The same number menu by USSD, by text message and read aloud on a voice call; one question a page; no account needed. Only the
# question types that fit a number reply are asked here (a 1 to 5 rating with words, a 0 to 10 score, yes or no, one choice);
# written answers are left to the other ways. The answers go to the cloud, which checks them like every other answer.
S_TYPES = ("rating", "stars", "score", "yes_no", "choice")


def survey_start():
    return {"screen": "intro", "i": 0, "answers": []}


def _asked(ctx):
    return [q for q in ctx["questions"] if q["type"] in S_TYPES]


def survey_page(state, ctx):
    """ctx: org (text), minutes, anonymous (bool), questions [{"id", "type", "text", "choices"?}] in the person's language."""
    s, qs = state["screen"], _asked(ctx)
    if s == "intro":
        return [("ch_s_intro", {"org": ctx["org"], "count": len(qs), "minutes": ctx["minutes"]})] + ([("ch_s_anon", {})] if ctx["anonymous"] else []) + [("ch_s_start", {"n": 1}), ("ch_end", {"n": 0})]
    if s == "question":
        q = qs[state["i"]]
        head = [("ch_s_q", {"i": state["i"] + 1, "of": len(qs), "text": q["text"]})]
        if q["type"] in ("rating", "stars"): return head + [("ch_s_rate", {})]
        if q["type"] == "score": return head + [("ch_s_score", {})]
        if q["type"] == "yes_no": return head + [("ch_s_yes", {"n": 1}), ("ch_s_no", {"n": 2})]
        return head + [("ch_s_choice", {"n": i + 1, "name": c}) for i, c in enumerate(q["choices"])]
    if s == "done":
        return [("ch_s_done", {})]
    return [("ch_bye", {})]


def _reply(q, t):
    """The answer a reply gives, or None when the reply does not fit the question."""
    if not t.isdigit(): return None
    n = int(t)
    if q["type"] in ("rating", "stars") and 1 <= n <= 5: return {"q": q["id"], "number": n}
    if q["type"] == "score" and 0 <= n <= 10: return {"q": q["id"], "number": n}
    if q["type"] == "yes_no" and n in (1, 2): return {"q": q["id"], "choice": "yes" if n == 1 else "no"}
    if q["type"] == "choice" and 1 <= n <= len(q["choices"]): return {"q": q["id"], "choice": q["choices"][n - 1]}
    return None


def survey_step(state, text, ctx):
    """One reply. Returns (new state, ends, action or None); the action {"answers": [...]} comes once, when the last question is answered."""
    s, t, qs = {**state, "answers": list(state["answers"])}, (text or "").strip(), _asked(ctx)
    if s["screen"] == "intro":
        if t == "0" or not qs: s["screen"] = "bye"; return s, True, None
        if t == "1": s["screen"] = "question"; return s, False, None
        return s, False, None
    if s["screen"] == "question":
        a = _reply(qs[s["i"]], t)
        if a is None: return s, False, None
        s["answers"].append(a)
        if s["i"] + 1 < len(qs): s["i"] += 1; return s, False, None
        s["screen"] = "done"; return s, True, {"answers": s["answers"]}
    return s, True, None


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


def aloud(text):
    """A page read aloud on a voice call says each Lynk name the way people say it ("Link P O S"), from the names register."""
    from core import names
    return names.speakable(text)
