"""LynkHR in the cloud (SIX SERVICES UPDATE, master blueprint 69.3, 69.11 and 69.12; build section 4B step 2), on the rules of core/hr.py.

Staff records (public id LOSTF-) for every kind of worker, with the name and contacts only in the PII vault; who sees which field;
special details only where the country allows; corrections the person asks for; joining and leaving checklists; leave in half days
with balances, clashes and answers from someone else; review cycles with anonymous answers shown only from 3; pay changes approved
by a different person (and a third over the budget); payroll figures handed to LynkAcc as a draft a second person posts; HR cases
seen only by HR and the named investigator; expiry reminders; training from LynkAcademy joining the skills record; absences from
LynkAttend when the business switches that link on. LynkAssist drafts and explains and never decides about a person.
No event carries a name, contact, ID number, bank details, health, family or union detail, or anybody's words."""
import time

from contract.tools.validate_contract import uuid7
from core import hr as H
from core.regions import country
from services.improvements import Table


class People:
    def __init__(s, p, now=time.time):
        s.p, s.now, db = p, now, p.c.store.db
        s.staff, s.leave, s.bal = Table(db, "hr_staff"), Table(db, "hr_leave"), Table(db, "hr_balance")
        s.cycles, s.answers, s.pay, s.cases = Table(db, "hr_cycles"), Table(db, "hr_answers"), Table(db, "hr_pay"), Table(db, "hr_cases")

    # ---- plumbing ------------------------------------------------------------------------------------------------------------
    def ent(s, m):
        return s.p.billing.entitlement(m, "lynkhr")

    def _need(s, m, feature, words):
        if not s.ent(m).get(feature):
            raise PermissionError(f"{words} need a higher LynkHR plan")

    def _emit(s, m, type_, payload):
        s.p.c.store.append(m, "server", type_, payload)

    def _pack(s, m):
        return country(s.p.c.profile(m)["country"])

    def _today(s):
        return time.strftime("%Y-%m-%d", time.gmtime(s.now()))

    def _staff(s, m, sid):
        r = s.staff.get(sid)
        if not r or r["merchant"] != m:
            raise KeyError("no such staff record")
        return r

    def _staff_uuid(s, m, sid):
        return s._staff(m, sid)["uuid"]

    # ---- records -------------------------------------------------------------------------------------------------------------
    def add(s, m, by, worker_kind, start_date, name, role="staff", manager=None, branch=None, department=None, salary=0, hourly_minor=0):
        if worker_kind not in H.HR["workers"]:
            raise ValueError("unknown kind of worker")
        limit = s.ent(m).get("staff_included")
        active = sum(1 for _, v in s.staff.items() if v["merchant"] == m and not v.get("left"))
        if s.p.billing.tier(m, "lynkhr") == "free" and limit is not None and active >= limit:
            raise PermissionError("the staff limit of LynkHR Free is reached; Plus adds more")
        u = uuid7()
        sid = s.p.ids.assign("STF", u.replace("-", ""))
        s.staff.put(sid, {"merchant": m, "uuid": u, "kind": worker_kind, "start": start_date, "role": role, "manager": manager, "branch": branch,
                          "department": department, "name_ref": s.p.vault.put(sid, "staff_name", name), "salary": salary, "hourly_minor": hourly_minor,
                          "special": {}, "skills": [], "documents": {}, "done": {"joining": [], "leaving": []}, "left": None,
                          "probation_end": H.probation_end(start_date)})
        s._emit(m, "StaffRecordCreated", {"staff_id": u, "worker_kind": worker_kind, "start_date": start_date})
        s._emit(m, "staff.joining", {"staff_id": sid, "state": "started"})              # the joining tracker (catalog/tracking.v1.json)
        return sid

    def record(s, m, sid, viewer_role, is_self=False):
        """The staff record as a role sees it: sensitive fields only for the fewest roles; the person sees their own."""
        r = s._staff(m, sid)
        shown = set(H.visible_fields(viewer_role, is_self))
        full = {"name_ref": r["name_ref"], "role": r["role"], "manager": r["manager"], "start_date": r["start"], "worker_kind": r["kind"],
                "branch": r["branch"], "department": r["department"], "salary": r["salary"]}
        out = {k: v for k, v in full.items() if k in shown}
        out["skills"] = list(r["skills"])
        return out

    def set_special(s, m, sid, kind, value, by):
        if not H.special_allowed(kind, s._pack(m)):
            raise PermissionError("this detail is kept only where the country's law allows it")
        s._staff(m, sid)["special"][kind] = bool(value)
        s.staff.put(sid, s._staff(m, sid))

    def ask_correction(s, m, sid, field):
        """A staff member can always ask for a correction to their own record; it becomes a tracked help-desk case."""
        return s.open_case(m, "help_desk", sid, about=field)

    # ---- joining and leaving -------------------------------------------------------------------------------------------------
    def step_done(s, m, sid, which, step, by):
        r = s._staff(m, sid)
        if which not in ("joining", "leaving") or step not in [i["id"] for i in H.HR["checklists"][which]]:
            raise ValueError("unknown checklist step")
        if which == "leaving" and step == "final_pay_figures" and not H.final_pay_ready(r["done"]["leaving"]):
            raise PermissionError("final pay figures wait for notice, equipment back and access closed")
        if step not in r["done"][which]:
            r["done"][which].append(step)
            s.staff.put(sid, r)
            s._emit(m, "StaffChecklistStepDone", {"staff_id": r["uuid"], "checklist": which, "step": step})
            state = {"contract_signed": "contract_signed", "notice_recorded": "notice", "equipment_back": "equipment_back", "access_closed": "access_closed"}.get(step)
            if which == "joining" and not H.checklist("joining", r["done"]["joining"])["musts_left"]:
                state = "ready"
            if state:
                s._emit(m, f"staff.{which}", {"staff_id": sid, "state": state})
        return H.checklist(which, r["done"][which])

    def leave_org(s, m, sid, last_day, by):
        r = s._staff(m, sid)
        left = H.checklist("leaving", r["done"]["leaving"])["musts_left"]
        if left:
            raise PermissionError("still to do before the last day: " + ", ".join(left))
        r["left"] = last_day
        s.staff.put(sid, r)
        s._emit(m, "StaffLeft", {"staff_id": r["uuid"], "last_day": last_day})
        s._emit(m, "staff.leaving", {"staff_id": sid, "state": "left"})

    # ---- leave ---------------------------------------------------------------------------------------------------------------
    def set_entitlement(s, m, sid, kind, half_days, carried=0):
        s._staff(m, sid)
        s.bal.put(f"{sid}|{kind}", {"entitled": half_days, "taken": 0, "carried": H.carry_over(carried)})

    def balance(s, m, sid, kind):
        b = s.bal.get(f"{sid}|{kind}") or {"entitled": 0, "taken": 0, "carried": 0}
        return H.leave_balance(b["entitled"], b["taken"], b["carried"])

    def request_leave(s, m, sid, kind, half_days, first_day, last_day, team=None):
        r = s._staff(m, sid)
        if not H.leave_request_ok(kind, half_days, s.balance(m, sid, kind)):
            raise ValueError("more than the balance, or not a kind of leave")
        rid = uuid7()
        s.leave.put(rid, {"merchant": m, "staff": sid, "kind": kind, "half_days": half_days, "first": first_day, "last": last_day, "state": "asked"})
        s._emit(m, "LeaveRequested", {"request_id": rid, "staff_id": r["uuid"], "kind": kind, "half_days": half_days, "first_day": first_day, "last_day": last_day})
        clashes = []
        if team:
            days = [H.iso(d) for d in range(H.day(first_day), H.day(last_day) + 1)]
            away = {}
            for _, v in s.leave.items():
                if v["merchant"] == m and v["state"] == "approved" and v["staff"] in team:
                    for d in range(H.day(v["first"]), H.day(v["last"]) + 1):
                        away[H.iso(d)] = away.get(H.iso(d), 0) + 1
            clashes = H.clashes(len(team), away, days)
        return {"request": rid, "clashes": clashes}                                   # a clash is shown, never a refusal

    def answer_leave(s, m, rid, by, answer):
        q = s.leave[rid]
        if not H.may_approve(q["staff"], by):
            raise PermissionError("nobody answers their own leave request")
        if q["state"] != "asked":
            return q["state"]
        q["state"] = "approved" if answer == "approved" else "declined"
        s.leave.put(rid, q)
        if q["state"] == "approved" and H.has_balance(q["kind"]):
            key = f"{q['staff']}|{q['kind']}"
            b = s.bal.get(key) or {"entitled": 0, "taken": 0, "carried": 0}
            b["taken"] += q["half_days"]
            s.bal.put(key, b)
        s._emit(m, "LeaveAnswered", {"request_id": rid, "answer": q["state"], "by": by})
        return q["state"]

    def absence_counts(s, m, sid):
        return H.absence_counts([{"kind": v["kind"]} for _, v in s.leave.items() if v["staff"] == sid and v["state"] == "approved"])

    def from_attendance(s, m, sid, kind, half_days, day):
        """attend-hr: an absence recorded by LynkAttend becomes a leave request, only when the business switched the link on."""
        if not s.p.shared.link_on(m, "attend-hr"):
            raise PermissionError("the link from LynkAttend to LynkHR is off for this business")
        return s.request_leave(m, sid, kind, half_days, day, day)

    # ---- reviews -------------------------------------------------------------------------------------------------------------
    def open_cycle(s, m, kinds, closes, by):
        s._need(m, "reviews", "Reviews")
        cid = uuid7()
        s.cycles.put(cid, {"merchant": m, "kinds": list(kinds), "closes": closes})
        s._emit(m, "ReviewCycleOpened", {"cycle_id": cid, "kinds": list(kinds), "closes": closes})
        return cid

    def answer_review(s, m, cid, sid, kind, words_sha256):
        if kind not in s.cycles[cid]["kinds"]:
            raise ValueError("this cycle does not ask for that kind of answer")
        key = uuid7()
        s.answers.put(key, {"cycle": cid, "staff": sid, "kind": kind, "sha256": words_sha256})   # the words stay in LynkHR's store, never in the event
        s._emit(m, "ReviewAnswered", {"cycle_id": cid, "staff_id": s._staff_uuid(m, sid), "kind": kind})

    def review_results(s, m, cid, sid):
        """How many answers of each kind; peer and upward are shown only from 3 and never with names."""
        counts = {}
        for _, v in s.answers.items():
            if v["cycle"] == cid and v["staff"] == sid:
                counts[v["kind"]] = counts.get(v["kind"], 0) + 1
        return {k: (n if H.review_shown(k, n) else None) for k, n in sorted(counts.items())}

    def sign_off(s, m, cid, sid, by):
        if by == sid:
            raise PermissionError("a named manager signs off a review, never the person reviewed")
        s._emit(m, "ReviewSignedOff", {"cycle_id": cid, "staff_id": s._staff_uuid(m, sid), "by": by})

    # ---- pay -----------------------------------------------------------------------------------------------------------------
    def propose_pay(s, m, by, sid, kind, amount, currency=None):
        if kind == "pay_review":
            s._need(m, "pay_reviews", "Pay reviews")
        cid = uuid7()
        cur = currency or s._pack(m)["currency"]
        s.pay.put(cid, {"merchant": m, "by": by, "staff": sid, "kind": kind, "amount": amount, "currency": cur, "state": "proposed"})
        s._emit(m, "PayChangeProposed", {"change_id": cid, "staff_id": s._staff_uuid(m, sid), "kind": kind, "amount": amount, "currency": cur})
        return cid

    def approve_pay(s, m, cid, approver, budget, second=None):
        c = s.pay[cid]
        total = sum(v["amount"] for _, v in s.pay.items() if v["merchant"] == m and v["state"] == "approved" and v["kind"] == c["kind"]) + c["amount"]
        if not H.pay_change_ok(c["by"], approver, total, budget, second):
            raise PermissionError("a pay change is approved by someone else, and by a third person when over the budget")
        c["state"] = "approved"
        s.pay.put(cid, c)
        r = s._staff(m, c["staff"])
        if c["kind"] == "pay_review":
            r["salary"] += c["amount"]
            s.staff.put(c["staff"], r)
        s._emit(m, "PayChangeApproved", {"change_id": cid, "by": approver, **({"second_by": second} if second else {})})

    def payroll(s, m, period, by, week_minutes=None, commission=None):
        """One period's figures for LynkAcc's payroll: people on payroll only; the totals become a payroll draft in LynkAcc that a
        second person posts. LynkHR never pays anyone."""
        week_minutes, commission = week_minutes or {}, commission or {}
        rows = []
        for sid, v in s.staff.items():
            if v["merchant"] != m or v.get("left"):
                continue
            extra = [c["amount"] for _, c in s.pay.items() if c["merchant"] == m and c["staff"] == sid and c["state"] == "approved" and c["kind"] in ("allowance", "bonus")]
            rows.append({"id": sid, "kind": v["kind"], "salary": v["salary"], "allowances": extra, "week_minutes": week_minutes.get(sid, 0),
                         "hourly_minor": v["hourly_minor"], "commission": commission.get(sid, 0)})
        figs = H.payroll_figures(rows, s._pack(m))
        gross = sum(f["gross"] for f in figs)
        cur = s._pack(m)["currency"]
        s._emit(m, "PayrollFiguresSent", {"period": period, "staff_count": len(figs), "gross_total": gross, "currency": cur})
        draft = s.p.books.payroll_draft(m, period, gross, by) if gross else None
        return {"figures": figs, "gross": gross, "draft": draft}

    # ---- cases ---------------------------------------------------------------------------------------------------------------
    def open_case(s, m, kind, sid=None, about=None, anonymous=False):
        if kind not in H.HR["cases"]["kinds"]:
            raise ValueError("unknown kind of case")
        if kind in ("grievance", "discipline", "investigation"):
            s._need(m, "cases", "Cases")
        cid = uuid7()
        s.cases.put(cid, {"merchant": m, "kind": kind, "staff": None if anonymous else sid, "step": "opened", "about": about, "investigator": None,
                          "since": H.day(s._today())})
        payload = {"case_id": cid, "kind": kind}
        if sid and not anonymous:
            payload["staff_id"] = s._staff_uuid(m, sid)
        s._emit(m, "HrCaseOpened", payload)
        return cid

    def case(s, m, cid, viewer_role, viewer=None):
        c = s.cases[cid]
        if not H.case_may_see(viewer_role, named=viewer is not None and viewer == c["investigator"]):
            raise PermissionError("cases are seen only by HR and the named investigator")
        return {"kind": c["kind"], "step": c["step"], "due": H.iso(H.case_deadline(c["step"], c["since"])) if H.case_deadline(c["step"], c["since"]) else None}

    def name_investigator(s, m, cid, person):
        c = s.cases[cid]; c["investigator"] = person; s.cases.put(cid, c)

    def next_step(s, m, cid, by_role):
        c = s.cases[cid]
        if not H.case_may_see(by_role, True):
            raise PermissionError("only HR or the named investigator moves a case")
        nxt = H.case_next(c["step"])
        if nxt is None:
            return c["step"]
        c["step"], c["since"] = nxt, H.day(s._today())
        s.cases.put(cid, c)
        s._emit(m, "HrCaseStepMoved", {"case_id": cid, "step": nxt})
        return nxt

    # ---- reminders, training and LynkAssist ----------------------------------------------------------------------------------
    def add_document(s, m, sid, kind, expiry):
        if kind not in H.HR["expiry"]["kinds"]:
            raise ValueError("unknown kind of document")
        r = s._staff(m, sid); r["documents"][kind] = expiry; s.staff.put(sid, r)

    def expiries(s, m, today=None):
        today = today or s._today()
        out = []
        for sid, v in s.staff.items():
            if v["merchant"] != m:
                continue
            for kind, exp in sorted(v["documents"].items()):
                st = H.expiry_stage(exp, today)
                if st is not None:
                    out.append({"staff": sid, "kind": kind, "stage": st})
                    s._emit(m, "StaffDocumentExpiring", {"staff_id": sid, "kind": kind, "stage": st})   # the reminder message (catalog/messages.v1.json)
        return out

    def course_completed(s, m, sid, course_ref, person_agreed):
        """academy-hr: finished training joins the skills record, with the person's consent."""
        if not person_agreed:
            raise PermissionError("training joins the record only with the person's consent")
        r = s._staff(m, sid)
        if course_ref not in r["skills"]:
            r["skills"].append(course_ref); s.staff.put(sid, r)

    def assist(s, m, action):
        """LynkAssist drafts and explains; it never decides about a person."""
        if not H.assist_may(action):
            raise PermissionError("LynkAssist never decides hiring, pay, promotion, discipline or dismissal")
        return {"action": action, "suggestion": True}
