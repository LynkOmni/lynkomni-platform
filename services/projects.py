"""LynkProject in the cloud (SIX SERVICES UPDATE, master blueprint 69.4, 69.11 and 69.12; build section 4B step 2), on the rules of core/project.py.

Projects (public id LOPRJ-) from templates, tasks (LOTSK-) captured any way and moved through their states, tasks that wait on other
tasks (never in a circle), milestones and baselines, time in whole minutes approved by someone else and billed through LynkInv once,
costs posted through LynkAcc, change requests decided by a named person, guests who see only their project and never money, and
minutes from a meeting (LynkFiles) turned into tasks for named people. Titles, notes and minutes stay in LynkProject's store; events
carry ids, kinds, whole numbers and dates only. LynkAssist suggests and a person confirms every change."""
import time

from contract.tools.validate_contract import uuid7
from core import project as P
from core.regions import country
from services.improvements import Table


class Projects:
    def __init__(s, p, now=time.time):
        s.p, s.now, db = p, now, p.c.store.db
        s.projects, s.tasks, s.time, s.changes, s.guests = (Table(db, "pj_projects"), Table(db, "pj_tasks"), Table(db, "pj_time"),
                                                            Table(db, "pj_changes"), Table(db, "pj_guests"))
        s.sheets = Table(db, "pj_sheets")

    # ---- plumbing ------------------------------------------------------------------------------------------------------------
    def ent(s, m):
        return s.p.billing.entitlement(m, "lynkproject")

    def _need(s, m, feature, words):
        if not s.ent(m).get(feature):
            raise PermissionError(f"{words} need a higher LynkProject plan")

    def _emit(s, m, type_, payload):
        s.p.c.store.append(m, "server", type_, payload)

    def _cur(s, m):
        return country(s.p.c.profile(m)["country"])["currency"]

    def _project(s, m, pid):
        r = s.projects.get(pid)
        if not r or r["merchant"] != m:
            raise KeyError("no such project")
        return r

    def _task(s, m, tid):
        r = s.tasks.get(tid)
        if not r or r["merchant"] != m:
            raise KeyError("no such task")
        return r

    def _day(s):
        return int(s.now()) // 86400

    # ---- projects and tasks --------------------------------------------------------------------------------------------------
    def create(s, m, by, name, method="list", template=None, budget=0):
        if method not in P.PJ["methods"] or (template and template not in P.PJ["templates"]):
            raise ValueError("unknown method or template")
        if method == "agile":
            s._need(m, "agile", "Agile boards")
        u = uuid7()
        pid = s.p.ids.assign("PRJ", u.replace("-", ""))
        s.projects.put(pid, {"merchant": m, "uuid": u, "name": name, "method": method, "by": by, "budget": budget, "costs": [], "invoiced": 0,
                             "milestones": {}, "baseline": {}, "members": [by]})
        s._emit(m, "ProjectCreated", {"project_id": u, "method": method, **({"template": template} if template else {})})
        return pid

    def add_task(s, m, pid, by, title, priority="normal", source="typed", due=None, owner=None, days=1):
        pr = s._project(m, pid)
        if priority not in P.PJ["priorities"] or source not in P.PJ["capture"]:
            raise ValueError("unknown priority or source")
        u = uuid7()
        tid = s.p.ids.assign("TSK", u.replace("-", ""))
        s.tasks.put(tid, {"merchant": m, "project": pid, "uuid": u, "title": title, "state": "todo", "priority": priority, "due": due,
                          "owner": owner, "days": days, "waits_on": []})
        ev = {"task_id": u, "project_id": pr["uuid"], "priority": priority, "source": source}
        if due is not None:
            ev["due"] = time.strftime("%Y-%m-%d", time.gmtime(due * 86400))
        if owner:
            ev["owner"] = owner
        s._emit(m, "TaskCreated", ev)
        return tid

    def _as_task(s, tid, t):
        return {"id": tid, "state": t["state"], "waits_on": list(t["waits_on"]), "days": t["days"], "due": t["due"], "owner": t["owner"]}

    def project_tasks(s, m, pid):
        return [s._as_task(k, v) for k, v in s.tasks.items() if v["merchant"] == m and v["project"] == pid]

    def move(s, m, tid, to, by):
        t = s._task(m, tid)
        tasks = s.project_tasks(m, t["project"])
        if not P.move_ok(t["state"], to):
            raise ValueError("a task cannot move that way")
        if to == "done" and not P.done_ok(s._as_task(tid, t), tasks):
            raise PermissionError("this task waits on others that are not done yet")
        frm, t["state"] = t["state"], to
        s.tasks.put(tid, t)
        s._emit(m, "TaskStateChanged", {"task_id": t["uuid"], "from": frm, "to": to})

    def wait_on(s, m, tid, other):
        t, o = s._task(m, tid), s._task(m, other)
        deps = {k: list(v["waits_on"]) for k, v in s.tasks.items() if v["merchant"] == m}
        if not P.wait_ok(deps, tid, other):
            raise ValueError("a task never waits on itself or in a circle")
        t["waits_on"].append(other)
        s.tasks.put(tid, t)
        s._emit(m, "TaskWaitAdded", {"task_id": t["uuid"], "waits_on": o["uuid"]})

    def schedule(s, m, pid):
        return P.schedule(s.project_tasks(m, pid))

    def late(s, m, pid, today=None):
        today = s._day() if today is None else today
        tasks = s.project_tasks(m, pid)
        return {"late": P.late(tasks, today), "at_risk": P.at_risk(tasks, today)}

    def my_work(s, m, person, today=None):
        today = s._day() if today is None else today
        return P.my_work([s._as_task(k, v) for k, v in s.tasks.items() if v["merchant"] == m], person, today)

    def milestone(s, m, pid, name, planned_day, reached=False):
        s._need(m, "milestones", "Milestones")
        pr = s._project(m, pid)
        mid = pr["milestones"].get(name, {}).get("id") or uuid7()
        pr["milestones"][name] = {"id": mid, "day": planned_day, "reached": reached}
        new = name not in pr["baseline"]
        pr["baseline"].setdefault(name, planned_day)
        s.projects.put(pid, pr)
        if new:
            s._emit(m, "milestone.state", {"milestone_id": mid, "state": "planned"})       # the milestone tracker
        if reached:
            s._emit(m, "MilestoneReached", {"project_id": pr["uuid"], "milestone_id": mid})
        return mid

    def variance(s, m, pid):
        pr = s._project(m, pid)
        return P.variance(pr["baseline"], {k: v["day"] for k, v in pr["milestones"].items()})

    # ---- time and money ------------------------------------------------------------------------------------------------------
    def log_time(s, m, pid, by, minutes, billable=True, rate=0, task=None):
        s._need(m, "time_tracking", "Time tracking")
        if not P.entry_ok(minutes):
            raise ValueError("time is whole minutes, at most a day per entry")
        pr = s._project(m, pid)
        eid = uuid7()
        s.time.put(eid, {"merchant": m, "project": pid, "by": by, "minutes": minutes, "billable": bool(billable), "rate": rate, "approved": False, "billed": False})
        ev = {"entry_id": eid, "project_id": pr["uuid"], "minutes": minutes, "billable": bool(billable)}
        if task:
            ev["task_id"] = s._task(m, task)["uuid"]
        s._emit(m, "TimeLogged", ev)
        return eid

    def submit_sheet(s, m, person):
        """A person sends their open time for approval as one sheet."""
        mine = [k for k, v in s.time.items() if v["merchant"] == m and v["by"] == person and not v["approved"] and not v.get("sheet")]
        if not mine:
            return None
        sid = uuid7()
        for k in mine:
            v = s.time[k]; v["sheet"] = sid; s.time.put(k, v)
        s.sheets.put(sid, {"merchant": m, "person": person, "entries": mine, "state": "submitted"})
        s._emit(m, "time_sheet.state", {"sheet_id": sid, "state": "submitted"})
        return sid

    def answer_sheet(s, m, sheet_id, approver, answer="approved"):
        """A manager approves or returns a time sheet, never the person who logged it."""
        sh = s.sheets[sheet_id]
        if sh["merchant"] != m or sh["state"] != "submitted":
            raise PermissionError("this sheet is not waiting for an answer")
        if not P.time_approve_ok(sh["person"], approver):
            raise PermissionError("time is approved by a manager, never by the person who logged it")
        ok = answer == "approved"
        for k in sh["entries"]:
            v = s.time[k]
            if ok:
                v["approved"] = True
            else:
                v["sheet"] = None
            s.time.put(k, v)
        sh["state"] = "approved" if ok else "returned"
        s.sheets.put(sheet_id, sh)
        s._emit(m, "TimeSheetAnswered", {"sheet_id": sheet_id, "answer": sh["state"], "minutes": sum(s.time[k]["minutes"] for k in sh["entries"]), "by": approver})
        return sh["state"]

    def bill_time(s, m, pid, customer):
        """project-inv: approved billable time becomes LynkInv invoice lines once; it is never billed twice."""
        pr = s._project(m, pid)
        entries = [{"id": k, **v} for k, v in s.time.items() if v["merchant"] == m and v["project"] == pid]
        b = P.billable(entries)
        if not b["ids"]:
            return None
        by_id = {e["id"]: e for e in entries}
        lines = [{"qty_milli": 1000, "unit_minor": (2 * by_id[i]["minutes"] * by_id[i]["rate"] + 60) // 120} for i in b["ids"]]
        inv = s.p.invoicing.issue(m, customer, lines)
        for i in b["ids"]:
            v = s.time[i]; v["billed"] = True; s.time.put(i, v)
        pr["invoiced"] += b["amount"]
        s.projects.put(pid, pr)
        s._emit(m, "ProjectTimeBilled", {"project_id": pr["uuid"], "invoice": inv["id"], "minutes": b["minutes"], "amount": b["amount"], "currency": s._cur(m)})
        return {"invoice": inv["id"], **b}

    def add_cost(s, m, pid, by, amount, account="6000"):
        """A project cost goes to LynkAcc as a bill to pay (project-acc), and counts against the project's budget."""
        pr = s._project(m, pid)
        cid = uuid7()
        s.p.books.record_bill(m, by, amount, account=account, bill_id=cid)
        pr["costs"].append(amount)
        s.projects.put(pid, pr)
        s._emit(m, "ProjectCostRecorded", {"project_id": pr["uuid"], "cost_id": cid, "amount": amount, "currency": s._cur(m)})
        return cid

    def money(s, m, pid):
        pr = s._project(m, pid)
        return P.money(pr["budget"], pr["costs"], pr["invoiced"])

    # ---- change requests, guests and meetings ---------------------------------------------------------------------------------
    def raise_change(s, m, pid, by, cost_change=0, days_change=0):
        s._need(m, "change_requests", "Change requests")
        pr = s._project(m, pid)
        rid = uuid7()
        s.changes.put(rid, {"merchant": m, "project": pid, "by": by, "state": "raised"})
        s._emit(m, "ChangeRequestRaised", {"request_id": rid, "project_id": pr["uuid"], "cost_change": cost_change, "days_change": days_change})
        return rid

    def decide_change(s, m, rid, by, decision):
        c = s.changes[rid]
        if by == c["by"]:
            raise PermissionError("a named person decides a change request, never the person who raised it")
        c["state"] = decision
        s.changes.put(rid, c)
        s._emit(m, "ChangeRequestDecided", {"request_id": rid, "decision": decision, "by": by})

    def invite_guest(s, m, pid, guest):
        s._need(m, "guests", "Guests")
        s._project(m, pid)
        g = s.guests.get(f"{m}|{guest}") or {"projects": []}
        if pid not in g["projects"]:
            g["projects"].append(pid)
        s.guests.put(f"{m}|{guest}", g)

    def guest_view(s, m, guest, pid, part):
        g = s.guests.get(f"{m}|{guest}") or {"projects": []}
        if not P.guest_sees(part, g["projects"], pid):
            raise PermissionError("a guest sees only the project they were invited to, and never its money")
        if part == "tasks":
            return [{"id": t["id"], "state": t["state"]} for t in s.project_tasks(m, pid)]
        return []

    def actions_from_minutes(s, m, pid, by, actions):
        """files-project: the actions in a meeting's minutes become tasks for named people (a person confirms the list first)."""
        return [s.add_task(m, pid, by, a["title"], source="meeting", owner=a.get("owner"), due=a.get("due")) for a in actions]

    def assist(s, m, action):
        if not P.assist_may(action):
            raise PermissionError("LynkAssist suggests; a person confirms every change")
        return {"action": action, "suggestion": True}
