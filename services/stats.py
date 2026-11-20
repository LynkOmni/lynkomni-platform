"""LynkStat's additions in the cloud (SERVICES UPDATE, master blueprint 67.5; section 4 step D4b), on the rules of core/stats.py.

Figures are read, never copied: sales, cost of sales and expenses come from the books (the journal projected from the event
log), invoice counts from LynkInv and customer counts from LynkCRM. Groups over time, "what if" (always an estimate), the
owner's own measures, seeing only your part, freshness, scheduled exports, goals, notes on a chart and public reports with small
groups hidden. Which tier has what lives only in services/billing.py FEATURES["lynkstat"]."""
import time, uuid

from core import accounts as AC
from core import books as B
from core import stats as S
from services.improvements import Table


class Analytics:
    def __init__(s, p, now=time.time):
        s.p, s.now, db = p, now, p.c.store.db
        s.measures, s.scopes, s.goals = Table(db, "stat_measures"), Table(db, "stat_scopes"), Table(db, "stat_goals")
        s.exports, s.notes, s.sources = Table(db, "stat_exports"), Table(db, "stat_notes"), Table(db, "stat_sources")

    def ent(s, m):
        return s.p.billing.entitlement(m, "lynkstat")

    def _need(s, m, feature, words):
        if not s.ent(m).get(feature):
            raise PermissionError(f"{words} need a higher LynkStat plan")

    # ---- figures ---------------------------------------------------------------------------------------------------------------
    def figures(s, m):
        """The figures every chart, measure and export uses, in integer minor units and whole counts."""
        st = B.statements(AC.trial_balance(s.p.accountant.journal(m)))
        inv = [v for _, v in s.p.invoicing.inv.items() if v["merchant"] == m]
        recs = [v for _, v in s.p.crm.recs.items() if v["merchant"] == m and v.get("kind") == "customer"]
        refunds = sum(e["payload"].get("amount_minor", 0) for e in s.p.c.store.of(m, "refund.recorded"))
        return {"sales": st["income"], "refunds": refunds, "cost_of_sales": st["cost_of_sales"], "expenses": st["expenses"],
                "orders": len(inv), "customers": len(recs), "invoices_paid": sum(1 for v in inv if v["state"] == "paid"),
                "invoices_open": sum(1 for v in inv if v["state"] in ("issued", "part_paid", "overdue")),
                "new_customers": 0, "visits": 0, "staff_hours": 0, "stock_value": st["current_assets"] - st["cash"]}

    # ---- groups over time and what if ------------------------------------------------------------------------------------------
    def cohorts(s, m):
        s._need(m, "cohorts", "Groups over time")
        buys = [{"customer": v["customer"], "month": v["month"]} for _, v in s.p.invoicing.inv.items() if v["merchant"] == m and v.get("customer")]
        return S.cohorts(buys)

    def what_if(s, m, base, changes, elasticity_bp=None):
        s._need(m, "what_if", "What if")
        return S.what_if(base, changes, elasticity_bp)

    # ---- own measures ----------------------------------------------------------------------------------------------------------
    def define_measure(s, m, name, expr):
        s._need(m, "own_measures", "Your own measures")
        S.measure_names(expr)                                         # refuses anything that is not a formula of figures
        s.measures.put(f"{m}|{name}", {"expr": expr}); return name

    def measure(s, m, name):
        r = s.measures.get(f"{m}|{name}")
        if not r:
            raise KeyError(name)
        return S.evaluate(r["expr"], s.figures(m))

    # ---- see only your part ----------------------------------------------------------------------------------------------------
    def set_scope(s, m, role, rule):
        if rule not in ("branch", "all"):
            raise ValueError("a role sees its branch or everything")
        if rule == "branch":
            s._need(m, "scope_by_branch", "Seeing only your branch")
        s.scopes.put(f"{m}|{role}", {"rule": rule}); return rule

    def rules(s, m):
        return {k.split("|", 1)[1]: v["rule"] for k, v in s.scopes.items() if k.startswith(m + "|")}

    def visible(s, m, rows, viewer):
        return S.scope(rows, viewer, s.rules(m))

    # ---- fresh and correct -----------------------------------------------------------------------------------------------------
    def reported(s, m, source, minute):
        s.sources.put(f"{m}|{source}", {"minute": minute})

    def freshness(s, m, kind, expected, now_minute):
        got = {k.split("|", 1)[1]: v["minute"] for k, v in s.sources.items() if k.startswith(m + "|")}
        present = [x for x in expected if x in got]
        updated = max((got[x] for x in present), default=now_minute - S.STAT["freshness"]["max_age_minutes"][kind] - 1)
        return S.freshness(updated, now_minute, kind, expected, present)

    # ---- scheduled exports -----------------------------------------------------------------------------------------------------
    def schedule_export(s, m, every, fmt, start, connector):
        s._need(m, "scheduled_exports", "Scheduled exports")
        if every not in S.STAT["exports"]["every"] or fmt not in S.STAT["exports"]["formats"]:
            raise ValueError("unknown schedule or format")
        xid = uuid.uuid4().hex
        s.exports.put(xid, {"merchant": m, "every": every, "format": fmt, "start": start, "connector": connector}); return xid

    def export_rows(s, m, viewer):
        """What an export carries: figures only, the viewer's part only, never a customer's personal data."""
        if s.rules(m).get(viewer["role"], "all") == "branch":
            return {"figures": {}, "note": "branch figures only"} if viewer.get("branch") is None else {"figures": {}, "branch": viewer["branch"]}
        return {"figures": s.figures(m)}

    def next_exports(s, xid, count=3):
        x = s.exports.get(xid)
        return S.export_dates(x["start"], x["every"], count)

    # ---- goals, notes, public reports ------------------------------------------------------------------------------------------
    def set_goal(s, m, who, figure, target):
        s._need(m, "goals", "Goals")
        if figure not in S.STAT["measures"]["figures"]:
            raise ValueError("unknown figure")
        s.goals.put(f"{m}|{who}|{figure}", {"target": int(target)}); return figure

    def goal(s, m, who, figure, actual, elapsed_bp):
        g = s.goals.get(f"{m}|{who}|{figure}")
        return S.goal(actual, g["target"], elapsed_bp) if g else None

    def add_note(s, m, date, text):
        s._need(m, "chart_notes", "Notes on a chart")
        text = str(text).strip()
        if not text or len(text) > S.STAT["notes"]["max_length"]:
            raise ValueError("a note has 1 to 200 characters")
        nid = uuid.uuid4().hex; s.notes.put(nid, {"merchant": m, "date": date, "text": text}); return nid

    def notes_on(s, m, start, end):
        return sorted(({"date": v["date"], "text": v["text"]} for _, v in s.notes.items() if v["merchant"] == m and start <= v["date"] <= end), key=lambda n: n["date"])

    def public_report(s, m, groups):
        """A non-profit or public body publishes totals only; groups below the minimum are hidden."""
        s._need(m, "public_reports", "Public reports")
        return S.public_table(groups)
