"""LynkAssist Ask and Resolve: the rules around the AI (MASTER UPDATE, master blueprint section 54).

The AI understands the request and picks a registered action or an answer topic; this module alone decides whether it may run
and how. The rules are enforced here, by the system, never by the AI's judgement, so no wording ("ignore your rules", "I am
staff") can change the outcome:

- An action outside catalog/assist.v1.json never runs. An off switch (per action, per area, per country) stops it at once.
- The asker's own role decides; LynkAssist never acts with more rights than the person asking.
- Classes: A runs; B needs Confirm; C needs a fresh identity check and Confirm; D is prepared for a person or licensed partner.
  The owner can lower B to "ask me first" for staff. Past a daily or amount limit an action moves one class up.
- Answers: open (1), personal (2), verified (3), by role (4) and never (5). An unknown topic is never guessed.
- Every decision is returned with its reason, so "Why did this happen?" can always be answered."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "assist.v1.json"), encoding="utf-8") as _f:
    REG = json.load(_f)
ACTIONS = {a["id"]: a for a in REG["actions"]}
ORDER = ["A", "B", "C", "D"]
AUTOMATION_LEVEL = {k: v["level"] for k, v in REG["classes"].items()}


def _up(cls):
    return ORDER[min(ORDER.index(cls) + 1, len(ORDER) - 1)]


def decide(action_id, role, done_today=0, amount_minor=None, confirmed=False, fresh_check=False,
           switched_off=(), country=None, ask_owner_first=(), standing=()):
    """Returns {"run": bool, "class": ..., "needs": ..., "why": ...}. 'needs' is one of: none, confirm, fresh_check,
    ask_owner, hand_over, refused."""
    a = ACTIONS.get(action_id)
    if a is None:
        return {"run": False, "needs": "refused", "why": "not in the LynkAssist register"}
    if {action_id, a["area"], f"country:{country}"} & set(switched_off):
        return {"run": False, "needs": "refused", "why": "switched off"}
    if role not in a["roles"]:
        return {"run": False, "needs": "refused", "why": f"a {role} may not do this"}
    cls = a["class"]
    lim = a["limits"]
    if done_today >= lim["per_day"] or (amount_minor is not None and lim.get("max_minor") is not None and amount_minor > lim["max_minor"]):
        cls = _up(cls)
    if set(a["touches"]) & set(REG["only_hand_over"]):
        cls = "D"
    if cls == "D":
        return {"run": False, "class": "D", "needs": "hand_over", "why": "a person or the licensed partner decides this"}
    if cls == "B" and role != "owner" and action_id in ask_owner_first:
        return {"run": False, "class": "B", "needs": "ask_owner", "why": "the owner asked to approve this first"}
    if cls == "C" and not fresh_check:
        return {"run": False, "class": "C", "needs": "fresh_check", "why": "a quick check that it is you"}
    if cls in ("B", "C") and not confirmed and not (cls == "B" and action_id in standing):
        return {"run": False, "class": cls, "needs": "confirm", "why": "shown first, then Confirm or Deny"}
    return {"run": True, "class": cls, "needs": "none", "why": "allowed by the register", "undo": a["undo"]}


def answer(topic, signed_in=False, fresh_check=False, role=None):
    """Who may be told what. Returns {"answer": bool, "class": n, "why": ...}."""
    t = REG["topics"].get(topic)
    if t is None:
        return {"answer": False, "class": None, "why": "I do not know; here is where to find out"}
    c = t["class"]
    if c == 5:
        return {"answer": False, "class": 5, "why": "never given out, to protect you"}
    if c >= 2 and not signed_in:
        return {"answer": False, "class": c, "why": "sign in first"}
    if c == 3 and not fresh_check:
        return {"answer": False, "class": 3, "why": "after a quick check that it is you"}
    if c == 4 and role not in t["roles"]:
        return {"answer": False, "class": 4, "why": "only some roles can see this; ask the owner"}
    return {"answer": True, "class": c, "why": "allowed"}
