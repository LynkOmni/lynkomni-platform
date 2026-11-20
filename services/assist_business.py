"""LynkAssist in the Business app and on LynkPOS devices (MASTER UPDATE, master blueprint section 54; build section 3).

What it adds to the register (services/assist_register.py decides; this file only carries out what the register allows):
- the selling, shift, cash, stock and device actions of catalog/assist.v1.json, each with its undo where the register has one;
- offline layer 2: every action says what it does without a network (the register's "offline" field): device-only fixes are
  done at once; actions that need the cloud are confirmed now, sealed on the device (services/sealing.py) and shown as queued,
  carried out when the network returns, verified and told, never shown as done before that, and they expire if the device stays
  offline past queue_expires_s; a fresh identity check waits for the cloud; providers, partners and people are never offered
  offline (the case is prepared to send later);
- the owner's controls: switch an action or a whole area off, ask to approve chosen fixes first, and standing permissions
  ("always do this without asking") for chosen class B fixes within limits the owner sets; every run is still recorded, told
  and undoable;
- Ask the owner: a staff request above their role reaches the owner with the facts (notification kind staff_request) and is
  confirmed or denied in one tap;
- one history: every decision, run or not, for the business ("Everything LynkAssist did" in the business settings);
- the trust layer (ASSIST UPDATE 75; core/assist_trust.py, build section 4 step C3a): only the person's own request can start an
  action (text LynkAssist reads is never obeyed); "Pause LynkAssist actions" stops every action while answers carry on; the owner
  chooses what LynkAssist may do for each role and sets limits that can only lower the register's; a big change (over 50 items
  or the amount) needs a second approver who is not the person asking; plans of several steps can be paused and carried on.
LynkAssist is never shown inside a payment, a cash count, a void or a signature (screens enforce it with NEVER_INSIDE)."""
import json, time, uuid

from core import assist_trust as AT
from services import assist_register as AR
from identity.device_access import emit_checked

NEVER_INSIDE = ("payment", "cash_count", "void", "signature")
QUEUE_EXPIRES_S = AR.REG.get("queue_expires_s", 7 * 86400)
UNDO_S = 30


def _now(n):
    return time.time() if n is None else n


def offline_of(action_id):
    return AR.ACTIONS[action_id].get("offline", "never")


class Books:
    """The sandbox business records the handlers change (the real ones are the Business app's projections)."""

    def __init__(self):
        self.prices, self.stock, self.sales, self.holds, self.devices, self.shift = {}, {}, {}, {}, {}, None


class BusinessAssist:
    def __init__(self, business_id, owner, books=None, emit=None, notifier=None, cloud_public=None):
        self.business, self.owner = business_id, owner
        self.books = books or Books()
        self.emit_fn = emit or (lambda t, p: None)
        self.notifier, self.cloud_public = notifier, cloud_public
        self.switched_off, self.ask_first, self.standing = set(), set(), {}
        self.done_today = {}
        self.history, self.queue, self.requests = [], [], {}
        self.paused, self.role_off, self.limits, self.plans = False, set(), {}, {}

    def emit(self, t, p):
        emit_checked(self.emit_fn, t, p)

    # ------------------------------------------------------------------ the owner's controls
    def _owner(self, role):
        if role != "owner":
            raise PermissionError("only the owner changes LynkAssist's controls")

    def switch(self, role, target, on, by):
        """target: an action id, an area, or "country:XX"."""
        self._owner(role)
        (self.switched_off.discard if on else self.switched_off.add)(target)
        self.emit("AssistSwitched", {"target": target, "on": on, "by": by})

    def ask_owner_first(self, role, action_id, on=True):
        self._owner(role)
        (self.ask_first.add if on else self.ask_first.discard)(action_id)

    def set_standing(self, role, action_id, on, per_day=None, max_minor=None, by=None):
        """Standing permissions only for class B fixes, within the register's own limits (never above them)."""
        self._owner(role)
        a = AR.ACTIONS[action_id]
        if a["class"] != "B":
            raise ValueError("only class B fixes can run without asking")
        lim = a["limits"]
        per_day = min(per_day or lim["per_day"], lim["per_day"])
        if lim.get("max_minor") is not None:
            max_minor = min(max_minor if max_minor is not None else lim["max_minor"], lim["max_minor"])
        if on:
            self.standing[action_id] = {"per_day": per_day, "max_minor": max_minor}
        else:
            self.standing.pop(action_id, None)
        self.emit("StandingPermissionSet", {"action": action_id, "on": on, "per_day": per_day, "max_minor": max_minor, "by": by})

    def pause(self, role, on, by):
        """'Pause LynkAssist actions': nothing changes anywhere in the business while on; answers carry on."""
        self._owner(role)
        self.paused = bool(on)
        self.emit("AssistPaused", {"on": self.paused, "by": by})

    def set_role(self, role, for_role, target, on, by):
        """What LynkAssist may do for one role (an action or an area); never more than the register allows that role."""
        self._owner(role)
        (self.role_off.discard if on else self.role_off.add)((for_role, target))
        self.emit("AssistRoleSet", {"role": for_role, "target": target, "on": bool(on), "by": by})

    def set_limit(self, role, action_id, max_items=None, max_minor=None, by=None):
        """The owner's limits for one action; they can only lower the register's own."""
        self._owner(role)
        reg = AR.ACTIONS[action_id]["limits"]
        lim = {"max_items": max_items, "max_minor": AT.effective_limit(reg.get("max_minor"), max_minor)}
        self.limits[action_id] = lim
        self.emit("AssistLimitSet", {"action": action_id, "max_items": max_items, "max_minor": lim["max_minor"], "by": by})

    def plan(self, plan_id, state, by, steps=None):
        """A plan of several steps: draft, running, paused, done or cancelled; carried on from any device."""
        old = self.plans.get(plan_id, {}).get("state", "draft")
        if plan_id in self.plans and not AT.plan_move(old, state):
            raise ValueError(f"a plan cannot go from {old} to {state}")
        self.plans[plan_id] = {"state": state, "steps": steps if steps is not None else self.plans.get(plan_id, {}).get("steps", [])}
        self.emit("AssistPlanChanged", {"plan": plan_id, "state": state, "by": by})
        return self.plans[plan_id]

    def _role_off(self, role, action_id):
        a = AR.ACTIONS.get(action_id, {})
        return (role, action_id) in self.role_off or (role, a.get("area")) in self.role_off

    # ------------------------------------------------------------------ deciding
    def decide(self, action_id, role, amount_minor=None, confirmed=False, fresh_check=False, online=True, country=None):
        n = self.done_today.get(action_id, 0)
        st = self.standing.get(action_id)
        standing = [action_id] if st and n < st["per_day"] and (amount_minor is None or st["max_minor"] is None or amount_minor <= st["max_minor"]) else []
        d = AR.decide(action_id, role, done_today=n, amount_minor=amount_minor, confirmed=confirmed, fresh_check=fresh_check,
                      switched_off=self.switched_off, country=country, ask_owner_first=self.ask_first, standing=standing)
        if online or d["needs"] == "refused" or action_id not in AR.ACTIONS:
            return d
        mode = offline_of(action_id)
        if mode == "never" or d["needs"] == "hand_over":
            return {**d, "run": False, "needs": "prepare_for_later", "why": "needs the network and a person or partner: prepared to send later"}
        if mode == "cloud_check" and d["run"] is False and d["needs"] == "fresh_check":
            return {**d, "needs": "wait_for_network", "why": "the identity check needs the network"}
        if mode == "cloud_check":
            return {**d, "run": False, "needs": "wait_for_network", "why": "this touches the account and waits for the network"}
        return {**d, "offline": mode}

    # ------------------------------------------------------------------ doing
    def do(self, device_id, person, role, action_id, confirmed=False, fresh_check=False, online=True, now=None, amount_minor=None,
           source="person", items=0, approver=None, approver_role=None, **args):
        d = self.decide(action_id, role, amount_minor=amount_minor, confirmed=confirmed, fresh_check=fresh_check, online=online)
        lim = self.limits.get(action_id, {})
        g = AT.guard(d["needs"], d["run"], d.get("class"), source=source, paused=self.paused, role_off=self._role_off(role, action_id),
                     confirmed=confirmed, items=items, amount_minor=amount_minor, max_items=lim.get("max_items"), max_amount_minor=lim.get("max_minor"),
                     asker=person, approver=approver, approver_role=approver_role)
        entry = {"id": uuid.uuid4().hex, "action": action_id, "person": person, "role": role, "device": device_id,
                 "class": d.get("class"), "needs": d["needs"], "why": d["why"], "at": _now(now), "state": "not_done", "result": None, "undo": None,
                 "trust": g["outcome"]}
        if g["outcome"] in ("content_not_instructions", "paused", "role_off", "over_limit"):
            entry["needs"], entry["why"] = g["outcome"], g["why"]       # the trust layer stops it before anything runs
            self.history.insert(0, entry)
            return {**d, "run": False, "needs": g["outcome"], "why": g["why"], "entry": entry["id"], "state": "not_done", "result": None}
        if g["outcome"] == "second_approver":
            entry["state"] = "asked_owner"
            entry["request"] = self.ask_owner(person, role, action_id, {"args": sorted(args), "reason": "big_change", "items": items, "amount_minor": amount_minor}, now=now)
            self.history.insert(0, entry)
            return {**d, "run": False, "needs": "second_approver", "why": g["why"], "entry": entry["id"], "state": "asked_owner", "result": None}
        if d["needs"] == "ask_owner":
            entry["state"] = "asked_owner"
            entry["request"] = self.ask_owner(person, role, action_id, {"args": sorted(args)}, now=now)
        elif d["run"] and online:
            entry["result"], entry["undo"] = self._run(action_id, args)
            entry["state"] = "done"
            self.done_today[action_id] = self.done_today.get(action_id, 0) + 1
        elif d["run"] and d.get("offline") == "device":
            entry["result"], entry["undo"] = self._run(action_id, args)
            entry["state"] = "done"
        elif d["run"] and d.get("offline") == "queue":
            entry["state"] = "queued"                         # never "done" before the cloud carries it out
            item = {"entry": entry["id"], "action": action_id, "args": args, "person": person, "at": _now(now), "expires": _now(now) + QUEUE_EXPIRES_S}
            if self.cloud_public:
                from services.sealing import seal
                item["sealed"] = seal(json.dumps(item, sort_keys=True, default=str).encode(), self.cloud_public)
            self.queue.append(item)
            self.emit("AssistActionQueued", {"device_id": device_id, "action": action_id, "person": person, "expires_at": item["expires"]})
        self.history.insert(0, entry)
        return {**d, "entry": entry["id"], "state": entry["state"], "result": entry["result"]}

    def settle(self, device_id, now=None, changed_since=()):
        """The network returned: carry out what was queued. Expired items are told; if the cloud already changed the same
        record, the person chooses (conflict); the rest are done, verified and told."""
        out = []
        for item in list(self.queue):
            e = next(x for x in self.history if x["id"] == item["entry"])
            if _now(now) > item["expires"]:
                e["state"] = outcome = "expired"
            elif set(item["args"].values()) & set(changed_since):
                e["state"] = outcome = "conflict"
            else:
                e["result"], e["undo"] = self._run(item["action"], item["args"])
                e["state"] = outcome = "done"
            self.queue.remove(item)
            self.emit("AssistActionSettled", {"device_id": device_id, "action": item["action"], "outcome": outcome})
            if self.notifier and outcome == "done":
                self.notifier.notify("assist_fix_done", item["person"], f"settle-{item['entry']}", _now(now), role="person")
            out.append((item["action"], outcome))
        return out

    def undo(self, entry_id, now=None):
        for e in self.history:
            if e["id"] == entry_id and e["state"] == "done" and e["undo"] and _now(now) - e["at"] <= UNDO_S:
                e["undo"]()
                e["state"] = "undone"
                return True
        return False

    def everything_done(self):
        return [{k: v for k, v in e.items() if k != "undo"} for e in self.history]

    # ------------------------------------------------------------------ Ask the owner
    def ask_owner(self, person, role, action_id, facts, now=None):
        rid = uuid.uuid4().hex
        self.requests[rid] = {"person": person, "role": role, "action": action_id, "facts": facts, "answer": None}
        self.emit("OwnerAsked", {"request_id": rid, "action": action_id, "person": person, "role": role, "facts": facts})
        if self.notifier:
            self.notifier.notify("staff_request", self.owner, f"ask-{rid}", _now(now), role="owner", business=self.business)
        return rid

    def owner_answer(self, rid, answer, by, by_role, args=None, now=None):
        """One tap: approve or deny. Approving runs the action as it was confirmed, still through the register and the trust layer.
        A big change may be approved by the owner or a manager, but never by the person who asked."""
        r = self.requests[rid]
        big = r["facts"].get("reason") == "big_change"
        if by_role not in (AT.SAFE["second_approver"]["approver_roles"] if big else ("owner",)):
            raise PermissionError("only the owner answers" if not big else "only the owner or a manager approves a big change")
        if big and by == r["person"]:
            raise PermissionError("the person who asked never approves their own request")
        if r["answer"] is not None:
            return r["answer"]
        r["answer"] = answer
        self.emit("OwnerAnswered", {"request_id": rid, "answer": answer, "by": by})
        if answer == "approve" and big:
            f = r["facts"]
            return self.do("owner", r["person"], r["role"], r["action"], confirmed=True, now=now, items=f.get("items", 0), amount_minor=f.get("amount_minor"),
                           approver=by, approver_role=by_role, **(args or {}))
        if answer == "approve":
            return self.do("owner", by, "owner", r["action"], confirmed=True, now=now, **(args or {}))
        return "denied"

    # ------------------------------------------------------------------ handlers: only reached when the register allows
    def _run(self, action_id, args):
        b = self.books
        if action_id == "correct_price":
            was = b.prices.get(args["product"]); b.prices[args["product"]] = args["price_minor"]
            return {"product": args["product"], "was": was}, lambda: b.prices.__setitem__(args["product"], was)
        if action_id == "correct_stock_quantity":
            was = b.stock.get(args["product"]); b.stock[args["product"]] = args["qty_milli"]
            return {"product": args["product"], "was": was}, lambda: b.stock.__setitem__(args["product"], was)
        if action_id == "void_sale_within_rules":
            was = b.sales[args["sale"]]; b.sales[args["sale"]] = "voided"
            return {"sale": args["sale"], "was": was}, lambda: b.sales.__setitem__(args["sale"], was)
        if action_id == "release_stale_hold":
            b.holds.pop(args["hold"], None)
            return {"released": args["hold"]}, None
        if action_id == "retire_device":
            was = b.devices.get(args["device"]); b.devices[args["device"]] = "retired"
            return {"device": args["device"]}, lambda: b.devices.__setitem__(args["device"], was)
        if action_id in ("enrol_device", "wipe_lost_device"):
            b.devices[args["device"]] = "enrolled" if action_id == "enrol_device" else "wipe_sent"
            return {"device": args["device"], "state": "sent"}, None
        if action_id == "hand_over_shift":
            b.shift = args["to"]
            return {"to": args["to"]}, None
        if action_id in ("reprint_receipt", "recount_cash", "rerun_sync", "reconnect_device", "resend_receipt"):
            return {"done": action_id}, None
        raise KeyError(f"{action_id} has no business handler")
