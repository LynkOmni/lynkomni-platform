"""The automations of LynkAttend, LynkQueue and LynkSurvey in build section 3B, each registered in catalog/automations.v1.json and
run by LynkFlow (services/flow.py). None moves money, changes a credential or decides anything about a person: they tell, mark and
remind. "Was this you?" and reminders are messages the person or manager already chose; warning signs are only "Please check"."""
from merchant.cloud import SIGNALS


def _signal(f, subject, type_, payload, automation_id, now):
    if type_ not in SIGNALS: raise ValueError(f"{type_} is not a Business app signal")
    return f.emit(subject, type_, payload, automation_id, now)


def register(flow, platform):
    at = platform.attendance

    # ---- LynkAttend
    def was_this_you(f, m, p, now):
        r = at._was_this_you(m, p["member_id"], f"{p['record_id']}:in", p["record_id"], now)
        return {"told": bool(r), "why": "after every check-in the person is asked \"Was this you?\", so a check-in made for them is found out at once"} if r else None

    def offers_till_shift(f, m, p, now):
        if at.role_of(p["member_id"]) != "staff": return None
        _signal(f, m, "AlertSent", {"kind": "open_till_shift", "ref": p["member_id"], "detail": {"record_id": p["record_id"]}}, "attend-offers-till-shift", now)
        return {"offered": "open_till_shift", "why": "a staff member checked in; LynkPOS offers to open their till shift (the two are never blocked by each other)"}

    def no_check_out(f, m, p, now):
        marked = at.mark_no_check_out(m, now)
        return {"marked": len(marked), "why": "a record was still open 2 hours after the shift ended; it is marked \"No check-out\" for the manager to fix"} if marked else None

    def request_reminders(f, m, p, now):
        out = at.requests_tick(now, merchant=m)
        if not out["reminded"] and not out["deleted"]: return None
        return {"reminded": len(out["reminded"]), "deleted": len(out["deleted"]), "why": "a deletion request or dispute is waiting; the manager is reminded at 7, 14 and 25 days, and after 30 days the details are deleted by themselves"}

    def warning_signs(f, m, p, now):
        found = at.warning_signs(m, now)
        return {"please_check": len(found), "why": "a pattern that may mean someone checked in for another person, or that a reader needs fixing; only a flag, the manager decides"} if found else None

    for aid, fn in {"attend-was-this-you": was_this_you, "attend-offers-till-shift": offers_till_shift, "attend-no-check-out": no_check_out,
                    "attend-request-reminders": request_reminders, "attend-warning-signs": warning_signs}.items():
        flow.handle(aid, fn)
