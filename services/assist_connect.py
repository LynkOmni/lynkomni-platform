"""LynkAssist across services (CONNECT UPDATE 71.6; section 4 row 71.9 step 3): a question across services, a plan of several steps,
the morning brief, saved questions and the usage meter. Every action is in catalog/assist.v1.json and runs through the same
decisions, confirmations, history and trust layer as every Business app action (services/assist_business.py).

What it never does: show a part the person's role may not see (one role system, catalog/shared.v1.json), act inside a plan
without that step's own Confirm, send a brief or a saved answer to anyone but the person who switched it on, send anything when
there is nothing to say, or count help-topic answers against the plan's questions."""
import time

from core import shared as SH
from services.assist_office import OfficeAssist

DAY = 86400
QUESTION_ACTIONS = ("ask_across", "stat_why_changed", "crm_customer_summary", "acc_explain_statement")
KINDS = {"week": ("sales", "payments", "owed", "bills"), "owed": ("owed", "overdue"), "due_soon": ("due_today", "bills", "drafts")}
PART_AREA = {"sales": "pos", "payments": "inv", "owed": "inv", "overdue": "inv", "bills": "acc", "due_today": "inv", "drafts": "assist", "needs_person": "assist"}
GOALS = ("chase_overdue", "month_end")


def _base(role):
    """A role as one of the five base roles (catalog/shared.v1.json); an unknown role is treated as staff, never as more."""
    for kind in ("base", "device", "account_deputy"):
        try:
            return SH.base_role(kind, role)
        except KeyError:
            continue
    return "staff"


class ConnectAssist(OfficeAssist):
    def __init__(self, platform, merchant, owner, acting_as, now=time.time, **kw):
        super().__init__(platform, merchant, owner, acting_as, **kw)
        self.now, self.saved = now, {}

    def do(self, device_id, person, role, action_id, **kw):
        self._role = role                       # what the part may show follows the asking person's own role
        return super().do(device_id, person, role, action_id, **kw)

    # ---- parts, each from its own service ------------------------------------------------------------------------------------------
    def _parts(self, names, since, role):
        p, m, t = self.p, self.m, self.now()
        day = lambda x: time.strftime("%Y-%m-%d", time.gmtime(x))
        out, hidden = {}, []
        for n in names:
            if not SH.may("base", _base(role), PART_AREA[n], "view"):
                hidden.append(n); continue
            if n == "sales":
                s = [e for e in p.c.store.of(m, "sale.recorded") if (e["ts"] or "") >= since]
                out[n] = {"count": len(s), "total_minor": sum(e["payload"]["total_minor"] for e in s), "source": "lynkpos"}
            elif n == "payments":
                s = [e for e in p.c.store.of(m, "invoice.payment") if (e["ts"] or "") >= since]
                out[n] = {"count": len(s), "source": "lynkinv"}
            elif n in ("owed", "overdue"):
                rows = [(k, v) for k, v in p.invoicing.inv.items() if v["merchant"] == m and p.invoicing.outstanding(k) > 0]
                if n == "overdue": rows = [(k, v) for k, v in rows if v["due_at"] < t]
                out[n] = {"count": len(rows), "total_minor": sum(p.invoicing.outstanding(k) for k, _ in rows), "source": "lynkinv"}
            elif n == "bills":
                cal = [x for x in p.shared.calendar(m, day(t), day(t + 7 * DAY)) if x["source"] == "bill_due"]
                out[n] = {"count": len(cal), "source": "lynkacc"}
            elif n == "due_today":
                cal = [x for x in p.shared.calendar(m, day(t), day(t)) if x["source"] in ("invoice_due", "promise_to_pay")]
                out[n] = {"count": len(cal), "source": "lynkinv"}
            elif n == "drafts":
                out[n] = {"count": len(p.flow.drafts(m)), "source": "lynkflow"}
            elif n == "needs_person":
                out[n] = {"count": len(p.tracking.t.exceptions(m, t)) + len(p.flow.paused(m)), "source": "lynkflow"}
        return out, hidden

    def used_this_month(self):
        month = time.strftime("%Y-%m", time.gmtime(self.now()))
        return sum(1 for e in self.history if e["action"] in QUESTION_ACTIONS and e["state"] == "done" and not (e["result"] or {}).get("over_limit")
                   and time.strftime("%Y-%m", time.gmtime(e["at"])) == month)

    def question_limit(self):
        return self.p.billing.entitlement(self.m, "lynkassist").get("ai_questions")

    # ---- the skills ----------------------------------------------------------------------------------------------------------------
    def _run(self, action_id, args):
        p, m, t = self.p, self.m, self.now()
        role = getattr(self, "_role", "staff")
        if action_id == "ask_across":
            kind = args["kind"]
            if kind not in KINDS: raise ValueError("a question across services is one of " + ", ".join(KINDS))
            limit = self.question_limit()
            if limit is not None and self.used_this_month() >= limit:
                return {"over_limit": True, "limit": limit, "parts": {}}, None
            since = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t - (7 if kind == "week" else 1) * DAY))
            parts, hidden = self._parts(KINDS[kind], since, role)
            return {"kind": kind, "parts": parts, "hidden": hidden, "label": "from the records"}, None
        if action_id == "assist_plan":
            goal = args["goal"]
            if goal not in GOALS: raise ValueError("a plan's goal is one of " + ", ".join(GOALS))
            if goal == "chase_overdue":
                steps = [{"step": "inv_late_payer_plan", "invoice": k, "confirm": True}
                         for k, v in p.invoicing.inv.items() if v["merchant"] == m and v["due_at"] < t and p.invoicing.outstanding(k) > 0]
            else:
                from core import books as B
                steps = [{"step": "acc_month_end_checklist", "missing": x, "confirm": True} for x in B.close_missing(args.get("done", []))]
            pid = f"plan-{goal}-{int(t)}"
            self.plan(pid, "draft", self.by, steps=steps)
            return {"plan": pid, "goal": goal, "steps": steps, "state": "draft", "acted": False}, None
        if action_id == "morning_brief":
            since = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t - DAY))
            parts, hidden = self._parts(("sales", "payments", "due_today", "bills", "drafts", "needs_person"), since, role)
            say = any(v.get("count") for v in parts.values())
            return {"parts": parts, "hidden": hidden, "send": say}, None
        if action_id == "save_question":
            if args["kind"] not in KINDS or args.get("every") not in ("daily", "weekly"): raise ValueError("a saved question has a kind and daily or weekly")
            qid = f"q{len(self.saved) + 1}"
            self.saved[qid] = {"kind": args["kind"], "every": args["every"], "person": self.by, "last": None}
            self.emit("AssistQuestionSaved", {"person": self.by, "question": args["kind"], "every": args["every"]})
            return {"saved": qid}, (lambda: self.saved.pop(qid, None))
        if action_id == "assist_usage":
            limit = self.question_limit()
            return {"used": self.used_this_month(), "limit": limit, "left": None if limit is None else max(0, limit - self.used_this_month())}, None
        return super()._run(action_id, args)

    # ---- the opt-in automations (catalog/automations.v1.json assist-morning-brief and assist-saved-questions) ---------------------------
    def run_morning_brief(self, person, role, opted_in):
        if not opted_in: return None
        r = self.do("cloud", person, role, "morning_brief")
        if r["state"] != "done" or not r["result"]["send"]: return None          # nothing to say: nothing is sent
        self.emit("AssistBriefSent", {"person": person, "parts": sorted(r["result"]["parts"]), "by_automation": "assist-morning-brief"})
        return r["result"]

    def run_saved_questions(self, person, role, weekday):
        sent = []
        for qid, q in self.saved.items():
            if q["person"] != person or (q["every"] == "weekly" and weekday != 0): continue
            r = self.do("cloud", person, role, "ask_across", kind=q["kind"])
            if r["state"] == "done" and not r["result"].get("over_limit"):
                q["last"] = self.now(); sent.append(qid)
                self.emit("AssistSavedAnswered", {"person": person, "question": q["kind"], "by_automation": "assist-saved-questions"})
        return sent
