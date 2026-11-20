"""LynkAssist's trust layer (ASSIST UPDATE, master blueprint 75; build section 4 step C3a), read from catalog/assist-trust.v1.json.

It sits on top of services/assist_register.py (what may run, who may be told what) and decides how sure an answer is, works
figures out exactly, keeps content from ever acting as an instruction, keeps memory under the person's control, and puts every
change behind a preview, the owner's limits, per-role permission, a second approver for big changes, the pause switch and
practice mode. It also decides when a warning may be shown and whether a release, a language or a new skill passes its quality
bar. This module is the Python reference; ts/src/assisttrust.ts must agree on every case of contract/vectors/assist-trust.v1.json
(python3 tools/assist_trust_vectors.py after a change). Every answer comes with its reason, so 'Why?' can always be answered."""
import json, os

from core import chat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "assist-trust.v1.json"), encoding="utf-8") as _f:
    TRUST = json.load(_f)

LEVELS = tuple(TRUST["certainty"]["levels"])
SAFE = TRUST["safety"]
MEM = TRUST["memory"]
Q = TRUST["quality"]


# ---- better answers --------------------------------------------------------------------------------------------------------
def certainty(sources=0, estimate=False, missing=False, disagree=False, unconfirmed=False, checked=True):
    """How sure an answer is, in the register's four words. Never 'certain' unless every figure was checked."""
    if sources <= 0:
        return "dont_know"
    if disagree or unconfirmed or not checked:
        return "not_sure"
    if estimate or missing:
        return "likely"
    return "certain"


def work(parts):
    """Works a figure out from its parts ([{"minor": int, "currency": "USD"}]): integer minor units of one currency, added up
    twice in two orders. Returns {"ok", "total", "currency", "checked", "why"}; a figure that fails is never shown."""
    if not parts:
        return {"ok": False, "total": None, "currency": None, "checked": False, "why": "no_records"}
    curs = {p.get("currency") for p in parts}
    if len(curs) != 1:
        return {"ok": False, "total": None, "currency": None, "checked": False, "why": "mixed_currencies"}
    vals = [p.get("minor") for p in parts]
    if any(not isinstance(v, int) or isinstance(v, bool) for v in vals):
        return {"ok": False, "total": None, "currency": None, "checked": False, "why": "not_whole_minor_units"}
    first = 0
    for v in vals:
        first += v
    second = 0
    for v in reversed(vals):
        second += v
    if first != second:
        return {"ok": False, "total": None, "currency": None, "checked": False, "why": "checks_differ"}
    return {"ok": True, "total": first, "currency": curs.pop(), "checked": True, "why": "worked_out_twice"}


def needs_not_adviser(topic):
    """Tax, law, money, investment and health questions carry the 'not an adviser' line and the offer of a professional."""
    return topic in TRUST["not_adviser"]["topics"]


# ---- cannot be tricked -----------------------------------------------------------------------------------------------------
def may_act(source):
    """Only the person's own request can choose an action; text LynkAssist reads (a document, an email, a chat message, a
    product name, a web page) is content and is never obeyed."""
    c = TRUST["content"]
    if source in c["instruction_sources"]:
        return {"ok": True, "why": "person"}
    if source in c["content_sources"]:
        return {"ok": False, "why": "content_not_instructions"}
    return {"ok": False, "why": "unknown_source"}


# ---- memory with control ---------------------------------------------------------------------------------------------------
def remember(kind, scope, text, ctx_scope, memory_on=True, asked=False, sensitive=(), count=0, code_words=()):
    """Whether a line may be kept. Never a card number or code (the chat masking rule finds them), sensitive things only when
    the person asked, never across scopes, never when memory is off or full."""
    if not memory_on:
        return {"keep": False, "why": "memory_off"}
    if kind not in MEM["kinds"] or scope not in MEM["scopes"] or scope != ctx_scope:
        return {"keep": False, "why": "kept_apart"}
    if chat.mask(text, code_words)["found"]:
        return {"keep": False, "why": "never_secrets"}
    if any(s in MEM["sensitive_unless_asked"] for s in sensitive) and not asked:
        return {"keep": False, "why": "sensitive_not_asked"}
    if count >= MEM["max_items"]:
        return {"keep": False, "why": "full"}
    return {"keep": True, "why": "kept"}


def recall(items, scope, role):
    """What the assistant may use now: only lines of this scope, and only those the role may see (memory follows the role)."""
    rank = MEM["role_rank"]
    mine = rank.get(role, 0)
    return [i["id"] for i in items if i["scope"] == scope and rank.get(i.get("role_min", "cashier"), 0) <= mine]


# ---- doing things safely ---------------------------------------------------------------------------------------------------
def effective_limit(register_limit, owner_limit):
    """The owner's limit can only make LynkAssist do less than the register allows."""
    vals = [v for v in (register_limit, owner_limit) if v is not None]
    return min(vals) if vals else None


def bulk(items):
    """Many changes at once show a sample first ('This will change 240 products; here are 5 of them')."""
    b = SAFE["bulk"]
    return {"sample": min(b["sample"], items) if items >= b["from"] else items, "show_all": items < b["from"]}


def is_big(items=0, amount_minor=None, owner_amount=None):
    """A big change needs a second approver: over the item count, or over the amount (the owner may set a lower amount)."""
    s = SAFE["second_approver"]
    limit = effective_limit(s["amount_over_minor"], owner_amount)
    return items > s["items_over"] or (amount_minor is not None and amount_minor > limit)


def guard(register_needs, register_run, cls, source="person", paused=False, role_off=False, practice=False, confirmed=False,
          items=0, amount_minor=None, max_items=None, max_amount_minor=None, owner_amount=None,
          asker=None, approver=None, approver_role=None):
    """The trust layer's answer for one action, after the register's own decision (register_needs, register_run). Returns the
    first step still to do: content_not_instructions, paused, role_off, over_limit, register (the register refused, hands it
    over or needs a fresh check), preview (Confirm or Deny after before-and-after), second_approver, practice (nothing real) or
    run; with the sample to show for many changes."""
    out = lambda o, why: {"outcome": o, "why": why, **bulk(items)}
    if not may_act(source)["ok"]:
        return out("content_not_instructions", may_act(source)["why"])
    if paused:
        return out("paused", "lynkassist_actions_paused")
    if role_off:
        return out("role_off", "owner_switched_off_for_role")
    if (max_items is not None and items > max_items) or (max_amount_minor is not None and amount_minor is not None and amount_minor > max_amount_minor):
        return out("over_limit", "over_owner_limit")
    if register_needs in ("refused", "hand_over", "ask_owner", "fresh_check"):
        return out("register", register_needs)
    if cls in SAFE["preview_classes"] and not confirmed:
        return out("preview", "before_and_after_first")
    if is_big(items, amount_minor, owner_amount):
        s = SAFE["second_approver"]
        if approver is None or approver == asker or approver_role not in s["approver_roles"]:
            return out("second_approver", "another_person_confirms")
    if practice:
        return out("practice", "nothing_real_changes")
    if not register_run and register_needs != "confirm":
        return out("register", register_needs)
    return out("run", "allowed")


def plan_move(old, new):
    """A plan of several steps: draft, running, paused, done, cancelled."""
    return new in SAFE["plans"]["next"].get(old, [])


def later_ok(days):
    """'Do it later' up to 90 days ahead."""
    return 0 < days <= SAFE["later"]["max_days"]


# ---- help before being asked -----------------------------------------------------------------------------------------------
def warning(check, screen="home", shown_today=0, pace="normal", told=False, fine=False):
    """Whether a warning line may be shown now: a registered check, told once, not after 'It is fine', never inside a payment
    or count, and within the person's daily pace ('tell me less' or 'tell me more')."""
    w = TRUST["warnings"]
    c = w["checks"].get(check)
    if not c:
        return {"show": False, "why": "not_registered"}
    if screen in w["never_in"]:
        return {"show": False, "why": "protected_screen"}
    if told or fine:
        return {"show": False, "why": "told_once"}
    if shown_today >= w["pace"].get(pace, w["pace"]["normal"]):
        return {"show": False, "why": "daily_limit"}
    return {"show": True, "why": "show", "words": c["words"], "fix": c["fix"]}


def ask_about(target, rows=1):
    """'Ask about this' on a number, word, chart, row or several rows (at most 50)."""
    a = TRUST["ask_about"]
    if target not in a["targets"]:
        return {"ok": False, "why": "not_a_target"}
    if target == "rows" and not 1 <= rows <= a["max_rows"]:
        return {"ok": False, "why": "too_many_rows"}
    return {"ok": True, "why": "ask"}


# ---- quality you can measure -----------------------------------------------------------------------------------------------
def gate(before, after):
    """No release if any scorecard gets worse by more than the allowed drop (basis points). Returns {"pass", "worse"}."""
    worse = []
    for m, direction in Q["metrics"].items():
        if m not in before or m not in after:
            continue
        drop = (before[m] - after[m]) if direction == "up" else (after[m] - before[m])
        if drop > Q["max_drop_bp"]:
            worse.append(m)
    return {"pass": not worse, "worse": worse}


def language_ready(samples, solved_alone_bp, wrong_bp):
    """A language is switched on only when it passes its bar."""
    b = Q["language_bar"]
    return samples >= b["min_samples"] and solved_alone_bp >= b["solved_alone_min_bp"] and wrong_bp <= b["wrong_max_bp"]


def skill_level(runs, accepted_bp, wrong_bp):
    """A new skill starts as suggestions only; it may act after it has proved itself."""
    a = Q["new_skill"]["act_after"]
    return "act" if runs >= a["runs"] and accepted_bp >= a["accepted_min_bp"] and wrong_bp <= a["wrong_max_bp"] else Q["new_skill"]["starts"]
