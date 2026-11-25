"""LynkProject's rules (SIX SERVICES UPDATE, master blueprint 69.4, 69.11 and 69.12; build section 4B), read from catalog/project.v1.json.

Task states and moves, tasks that wait on other tasks (never in a circle), the critical path, late and at-risk work, "My work",
workload against what a person can give, time sheets approved by someone else and billed once, budgets and profit, baselines,
sprints, what a guest may see, and what LynkAssist may suggest. Durations are whole days, time whole minutes, money integer
minor units; days are whole day numbers (days since 1970-01-01).

This module is the Python reference; ts/src/project.ts must agree on every case of contract/vectors/project.v1.json
(python3 tools/project_vectors.py after a change)."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "catalog", "project.v1.json"), encoding="utf-8") as _f:
    PJ = json.load(_f)


def _finished(t):
    return t.get("state") in PJ["finished"]


# ---- states and waiting --------------------------------------------------------------------------------------------------------
def move_ok(frm, to):
    return to in PJ["moves"].get(frm, [])


def blockers(task, tasks):
    """The tasks this one waits on that are not done yet (a cancelled task no longer holds anything up)."""
    by = {t["id"]: t for t in tasks}
    return [b for b in task.get("waits_on", []) if b in by and by[b].get("state") != "done" and by[b].get("state") != "cancelled"]


def done_ok(task, tasks):
    return move_ok(task.get("state", "todo"), "done") and not blockers(task, tasks)


def wait_ok(deps, a, b):
    """May task a wait on task b? Never on itself and never in a circle. deps maps a task to what it waits on."""
    if a == b:
        return False
    seen, stack = set(), [b]
    while stack:
        x = stack.pop()
        if x == a:
            return False
        if x in seen:
            continue
        seen.add(x)
        stack.extend(deps.get(x, []))
    return True


def schedule(tasks):
    """Earliest start and finish for each task (in days from the project start), the project's length and the critical tasks
    (no slack), in the tasks' order. Tasks must not wait in a circle."""
    by = {t["id"]: t for t in tasks}
    order, mark = [], {}

    def visit(i):
        if mark.get(i) == 2:
            return
        mark[i] = 1
        for d in by[i].get("waits_on", []):
            if d in by:
                visit(d)
        mark[i] = 2
        order.append(i)
    for t in tasks:
        visit(t["id"])
    es, ef = {}, {}
    for i in order:
        es[i] = max([ef[d] for d in by[i].get("waits_on", []) if d in by] or [0])
        ef[i] = es[i] + by[i].get("days", 0)
    length = max(ef.values() or [0])
    after = {t["id"]: [] for t in tasks}
    for t in tasks:
        for d in t.get("waits_on", []):
            if d in after:
                after[d].append(t["id"])
    lf = {}
    for i in reversed(order):
        lf[i] = min([lf[n] - by[n].get("days", 0) for n in after[i]] or [length])
    return {"start": {t["id"]: es[t["id"]] for t in tasks}, "finish": {t["id"]: ef[t["id"]] for t in tasks}, "length": length,
            "critical": [t["id"] for t in tasks if lf[t["id"]] == ef[t["id"]]]}


# ---- late, at risk and My work -------------------------------------------------------------------------------------------------
def late(tasks, today):
    return [t["id"] for t in tasks if not _finished(t) and t.get("due") is not None and t["due"] < today]


def at_risk(tasks, today):
    late_ids = set(late(tasks, today))
    by = {t["id"]: t for t in tasks}
    out = []
    for t in tasks:
        if _finished(t) or t["id"] in late_ids or t.get("due") is None:
            continue
        for b in blockers(t, tasks):
            bt = by[b]
            if b in late_ids or (bt.get("due") is not None and bt["due"] + t.get("days", 0) > t["due"]):
                out.append(t["id"])
                break
    return out


def my_work(tasks, person, today):
    """A person's open tasks in buckets: overdue, today, this week, later, no date (each in the tasks' order)."""
    out = {b: [] for b in PJ["my_work"]["buckets"]}
    for t in tasks:
        if t.get("owner") != person or _finished(t):
            continue
        d = t.get("due")
        b = ("no_date" if d is None else "overdue" if d < today else "today" if d == today
             else "this_week" if d < today + PJ["my_work"]["week_days"] else "later")
        out[b].append(t["id"])
    return out


def workload(planned, leave_half_days=None, week_minutes=None):
    """Planned minutes per person against what they can give this week (working week less leave). Over is shown, never blocked."""
    leave_half_days = leave_half_days or {}
    out = {}
    for p in sorted(planned):
        can = max(0, (week_minutes or {}).get(p, PJ["workload"]["default_week_minutes"]) - 240 * leave_half_days.get(p, 0))
        out[p] = {"planned": planned[p], "can": can, "over": max(0, planned[p] - can)}
    return out


# ---- time and money ------------------------------------------------------------------------------------------------------------
def entry_ok(minutes):
    return isinstance(minutes, int) and not isinstance(minutes, bool) and 0 < minutes <= PJ["time"]["max_entry_minutes"]


def time_approve_ok(logger, approver):
    return bool(approver) and logger != approver


def billable(entries):
    """Approved, billable, not yet billed entries, and their amount: minutes × hourly rate / 60, rounded half up per entry."""
    pick = [e for e in entries if e.get("approved") and e.get("billable") and not e.get("billed")]
    return {"ids": [e["id"] for e in pick], "minutes": sum(e["minutes"] for e in pick),
            "amount": sum((2 * e["minutes"] * e["rate"] + 60) // 120 for e in pick)}


def money(budget, costs, invoiced):
    spent = sum(costs)
    return {"spent": spent, "left": budget - spent, "over": max(0, spent - budget), "profit": invoiced - spent}


def variance(baseline, current):
    """Days each milestone moved from its baseline (positive is later), for milestones in both."""
    return {k: current[k] - baseline[k] for k in sorted(baseline) if k in current}


def sprint(items, days):
    """Velocity (points done) and the burndown: points left at the end of each day 1..days."""
    total = sum(i["points"] for i in items)
    done = sum(i["points"] for i in items if i.get("done_day") is not None)
    return {"velocity": done, "burndown": [total - sum(i["points"] for i in items if i.get("done_day") is not None and i["done_day"] <= d) for d in range(1, days + 1)]}


# ---- who sees what -------------------------------------------------------------------------------------------------------------
def guest_sees(part, invited_to, project):
    return project in invited_to and part in PJ["guests"]["see"]


def field_place_ok(on_shift, agreed):
    return bool(on_shift and agreed)


def assist_may(action):
    return action in PJ["assist"]["may"] and action not in PJ["assist"]["never"]


def tier_has(tier, feature):
    order = ["free", "plus", "pro", "max"]
    if tier not in order:
        return False
    return any(feature in PJ["tiers"][t] for t in order[: order.index(tier) + 1])
