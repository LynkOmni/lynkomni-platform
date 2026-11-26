"""Sign-up, sign-in, help and notifications on phones with no apps (MASTER UPDATE, master blueprint sections 54, 55 and 62;
build section 3). The account side of the USSD, text and voice channels: core/channels.py sells, this file opens the account,
signs in, answers from the help menu and reads the bell.

One engine, three channels: a USSD session shows each page; by text message every reply moves the same session on (the
gateway keeps the session per number); a voice call reads each page aloud and takes key presses. The engine is pure: pages are
word keys with values, so every channel speaks the person's language; ts/src/basicphone.ts is the TypeScript port and
contract/vectors/basicphone.v1.json proves they agree.

Rules:
- the number the network gives is one proof, the PIN is the second: a number alone never opens an account (numbers are reused);
- sign-up asks the age first (18 or the country's higher age, never a birth date), a username by the one format, a PIN twice,
  and the terms; the account is created in the cloud only, and the recovery code is shown once;
- wrong PINs wait and then lock, never wipe; recovery is online, never on this menu;
- a duress PIN signs in to a home that looks the same but lists no messages, while the action carries duress so the cloud
  raises the silent alert (owner rule 2026-11-24);
- the help menu is numbered; fixes that need a smartphone are sent as a link or passed to a person, with a case number;
- the bell is read here too: unread lines, newest and most urgent first; reading one marks it read on every device;
- no secret ever appears on a page: no PIN, code or card number (only the recovery code, once, on the screen of the person
  who just created the account);
- the channel stays off for real users until a gateway is signed in the country (providers ussd_gateway), shown as
  "Coming to your country soon." by the screens."""
from identity.offline import pin_problem

SCREENS = ("welcome", "pin", "locked", "age", "too_young", "username", "new_pin", "pin_again", "terms", "created", "home",
           "messages", "read", "help", "states", "state", "pin_help", "pin_reset", "pin_reset_sent", "pin_reset_shop", "link_sent", "handed", "bye")
WELCOME = ("sign_in", "create", "help")
HOME = ("messages", "help")
HELP = ("states", "pin_help", "pin_reset", "link", "person")       # section 4C point 5: Reset my PIN by menu number
STATES = ("queued", "sent", "accepted", "confirmed", "failed")
MAX_LINES = 5                                   # messages listed on one page (a USSD screen holds about 182 characters)


def start():
    return {"screen": "welcome", "signed_in": False, "limited": False, "username": None, "pin": None, "note": None, "pick": None, "back": "welcome"}


def page(state, ctx):
    """The page for a state: [(word key, values)]. ctx: age (country's age of majority), lines [(nid, title)] unread newest first,
    recovery (shown once after sign-up), case (a support case reference after a hand-over), security_unread (an unread security
    alert waits: LynkOmni never texts its own alerts, so it is shown first on the home page)."""
    s, note = state["screen"], ([(state["note"][0], state["note"][1])] if state.get("note") else [])
    back = [("ch_back", {"n": 0})]
    if state.get("limited"):                                   # the duress home: the same pages, no messages
        ctx = dict(ctx, lines=[])
    if s == "welcome":
        return [("bp_title", {})] + [(f"bp_{k}", {"n": i + 1}) for i, k in enumerate(WELCOME)] + [("ch_end", {"n": 0})]
    if s == "pin":
        return note + [("bp_enter_pin", {})]
    if s == "locked":
        return [("bp_locked", {})]
    if s == "age":
        return [("bp_age", {"age": ctx["age"]}), ("bp_yes", {"n": 1}), ("bp_no", {"n": 2})]
    if s == "too_young":
        return [("bp_too_young", {"age": ctx["age"]})]
    if s == "username":
        return note + [("bp_username", {})]
    if s == "new_pin":
        return note + [("bp_new_pin", {})]
    if s == "pin_again":
        return [("bp_pin_again", {})]
    if s == "terms":
        return [("bp_terms", {}), ("bp_agree", {"n": 1})] + back
    if s == "created":
        return [("bp_created", {"username": state["username"]}), ("bp_recovery", {"code": ctx.get("recovery", "")}), ("bp_limits", {})]
    if s == "home":
        alert = [("bp_alert", {})] if ctx.get("security_unread") else []   # LynkOmni never texts: an unread security alert waits here
        return alert + [("bp_home", {}), ("bp_messages", {"n": 1, "count": len(ctx["lines"])}), ("bp_help", {"n": 2}), ("ch_end", {"n": 0})]
    if s == "messages":
        lines = ctx["lines"][:MAX_LINES]
        return ([("bp_msg_line", {"n": i + 1, "title": t}) for i, (_nid, t) in enumerate(lines)] or [("bp_no_messages", {})]) + back
    if s == "read":
        return [("bp_msg_read", {"title": ctx["lines"][state["pick"]][1]})] + back if state["pick"] is not None and state["pick"] < len(ctx["lines"]) else back
    if s == "help":
        return [("bp_help_title", {})] + [(f"bp_help_{k}", {"n": i + 1}) for i, k in enumerate(HELP)] + back
    if s == "states":
        return [("bp_states_title", {})] + [(f"bp_state_{k}", {"n": i + 1}) for i, k in enumerate(STATES)] + back
    if s == "state":
        return [(f"kp_state_{STATES[state['pick']]}", {})] + back
    if s == "pin_help":
        return [("bp_pin_help", {})] + back
    if s == "pin_reset":                                       # by menu: a code to this phone, then 24 hours; or at once in person
        return [("bp_pin_reset", {}), ("bp_pin_reset_menu", {"n": 1}), ("bp_pin_reset_shop", {"n": 2})] + back
    if s == "pin_reset_sent":
        return [("bp_pin_reset_sent", {})]
    if s == "pin_reset_shop":
        return [("bp_pin_reset_at_shop", {})]
    if s == "link_sent":
        return [("bp_link_sent", {})]
    if s == "handed":
        return [("bp_handed", {"case": ctx.get("case", "")})]
    return [("ch_bye", {})]


def _to(s, screen, note=None):
    s = dict(s)
    s["screen"], s["note"] = screen, note
    return s


def step(state, text, ctx):
    """One reply. Returns (state, ends, action or None). Actions: {"sign_in": True}, {"wrong_pin": n_left},
    {"create": {"username", "pin"}} (the cloud hashes the PIN and never stores it), {"read": nid}, {"send_link": "help"},
    {"hand_over": "help"}, {"pin_reset": "menu"} (identity/recover.py basic_pin_reset: a code to the phone, then 24 hours). ctx: pin_check(pin) -> "ok" | "duress" | ("wrong", left) | "locked"; username_check(u) -> None or a reason
    word key; taken(u) -> bool."""
    s, t = dict(state), (text or "").strip()
    scr = s["screen"]
    num = t.isdigit()
    if scr == "welcome":
        if t == "0": return _to(s, "bye"), True, None
        pick = WELCOME[int(t) - 1] if num and 1 <= int(t) <= len(WELCOME) else None
        if pick == "sign_in": return _to(s, "pin"), False, None
        if pick == "create": return _to(s, "age"), False, None
        if pick == "help": s["back"] = "welcome"; return _to(s, "help"), False, None
        return s, False, None
    if scr == "pin":
        r = ctx["pin_check"](t)
        if r == "ok":
            s["signed_in"] = True
            return _to(s, "home"), False, {"sign_in": True}
        if r == "duress":
            s["signed_in"] = True; s["limited"] = True
            return _to(s, "home"), False, {"sign_in": True, "duress": True}
        if r == "locked":
            return _to(s, "locked"), True, None
        return _to(s, "pin", ("bp_wrong_pin", {"left": r[1]})), False, {"wrong_pin": r[1]}
    if scr == "age":
        if t == "1": return _to(s, "username"), False, None
        if t == "2": return _to(s, "too_young"), True, None
        return s, False, None
    if scr == "username":
        u = t.lower().lstrip("@")
        why = ctx["username_check"](u)
        if why: return _to(s, "username", (f"username_{why}", {})), False, None
        if ctx["taken"](u): return _to(s, "username", ("username_taken", {})), False, None
        s["username"] = u
        return _to(s, "new_pin"), False, None
    if scr == "new_pin":
        why = pin_problem(t)
        if why: return _to(s, "new_pin", ("bp_pin_rule", {})), False, None
        s["pin"] = t
        return _to(s, "pin_again"), False, None
    if scr == "pin_again":
        if t != s["pin"]:
            s["pin"] = None
            return _to(s, "new_pin", ("bp_pin_mismatch", {})), False, None
        return _to(s, "terms"), False, None
    if scr == "terms":
        if t == "0": return start(), False, None
        if t == "1":
            action = {"create": {"username": s["username"], "pin": s["pin"]}}
            s["pin"] = None                                  # the PIN leaves the session with the request and is not kept
            return _to(s, "created"), True, action
        return s, False, None
    if scr == "home":
        if t == "0": return _to(s, "bye"), True, None
        if t == "1": return _to(s, "messages"), False, None
        if t == "2": s["back"] = "home"; return _to(s, "help"), False, None
        return s, False, None
    if scr == "messages":
        if t == "0": return _to(s, "home"), False, None
        lines = ctx["lines"][:MAX_LINES]
        if num and 1 <= int(t) <= len(lines):
            s["pick"] = int(t) - 1
            return _to(s, "read"), False, {"read": lines[int(t) - 1][0]}
        return s, False, None
    if scr == "read":
        return (_to(s, "messages"), False, None) if t == "0" else (s, False, None)
    if scr == "help":
        if t == "0": return _to(s, s.get("back") or "welcome"), False, None
        pick = HELP[int(t) - 1] if num and 1 <= int(t) <= len(HELP) else None
        if pick == "states": return _to(s, "states"), False, None
        if pick == "pin_help": return _to(s, "pin_help"), False, None
        if pick == "pin_reset": return _to(s, "pin_reset"), False, None
        if pick == "link": return _to(s, "link_sent"), True, {"send_link": "help"}
        if pick == "person": return _to(s, "handed"), True, {"hand_over": "help"}
        return s, False, None
    if scr == "states":
        if t == "0": return _to(s, "help"), False, None
        if num and 1 <= int(t) <= len(STATES):
            s["pick"] = int(t) - 1
            return _to(s, "state"), False, None
        return s, False, None
    if scr == "pin_reset":
        if t == "0": return _to(s, "help"), False, None
        if t == "1": return _to(s, "pin_reset_sent"), True, {"pin_reset": "menu"}
        if t == "2": return _to(s, "pin_reset_shop"), True, None
        return s, False, None
    if scr in ("state", "pin_help"):
        return (_to(s, "states" if scr == "state" else "help"), False, None) if t == "0" else (s, False, None)
    return s, True, None


def text_notification(title, record=None, words=None):
    """One notification as a text message for a basic phone: the title, the record number if any, and how to read the rest
    on the menu. Never a secret, a link to anywhere but lynkomni.com, or advertising (services/messages.py checks content)."""
    w = words or {}
    parts = [title]
    if record:
        parts.append(w.get("msg_record", "Record number:") + " " + record)
    parts.append(w.get("bp_read_more", "Dial the LynkOmni menu and choose Messages to read more."))
    return " ".join(parts)
