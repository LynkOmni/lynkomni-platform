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

    # ---- LynkQueue
    qu = platform.queue

    def please_come(f, m, p, now):
        told = qu.please_come(m, p["place_id"], p["ticket_ids"], now)
        return {"told": len(told), "why": "5 people or fewer are ahead of someone who joined by phone, so they are told \"Please come now\" (once)"} if told else None

    def not_served_today(f, m, p, now):
        closed = sum(len(qu.close_day(m, pl, now)) for pl in qu.closing_due(m, now))
        return {"closed": closed, "why": "a ticket is for today only: tickets still waiting at closing are closed and marked \"Not served today\""} if closed else None

    def open_counter(f, m, p, now):
        _signal(f, m, "AlertSent", {"kind": "queue_open_another_counter", "ref": p["place_id"], "detail": {"section": p["section"], "longest_wait_minutes": p["longest_wait_minutes"]}}, "queue-open-counter", now)
        return {"suggested": p["section"], "why": "the longest wait in this section is over 30 minutes; LynkAssist suggests opening another counter and the manager decides"}

    def busy_forecast(f, m, p, now):
        import time
        if not qu._ent(m)["busy_forecast"]: return None
        tomorrow, found = (time.gmtime(now).tm_wday + 1) % 7, 0
        for pl in qu.places(m):
            busy = qu.forecast(m, pl, tomorrow, now)
            if busy:
                found += 1; _signal(f, m, "AlertSent", {"kind": "queue_busy_forecast", "ref": pl, "detail": {"busy": busy[:3]}}, "queue-busy-forecast", now)
        return {"places": found, "why": "from this place's own past days: tomorrow's busy hours for each section, so staff can be planned ahead (an estimate)"} if found else None

    def pickup_collection(f, m, p, now):
        if p.get("step") != "at_pickup_point": return None
        made = qu.collection(m, p["place_id"], p["shipment_id"], now)
        return {"ready": made["section"], "why": "a parcel reached the pickup point; its collection gets a queue ticket when the person comes"} if made else None

    def opens_queue_counter(f, m, p, now):
        counters = qu.counters_of(p["member_id"])
        if not counters: return None
        _signal(f, m, "AlertSent", {"kind": "queue_counter_follows_check_in", "ref": p["member_id"], "detail": {"counters": counters, "direction": "in"}}, "attend-opens-queue-counter", now)
        return {"counters": len(counters), "why": "the person who serves at this counter checked in, so the counter opens; it can be closed again with the counter's own buttons"}

    for aid, fn in {"queue-please-come": please_come, "queue-not-served-today": not_served_today, "queue-open-counter": open_counter, "queue-busy-forecast": busy_forecast,
                    "queue-pickup-collection": pickup_collection, "attend-opens-queue-counter": opens_queue_counter}.items():
        flow.handle(aid, fn)

    for aid, fn in {"attend-was-this-you": was_this_you, "attend-offers-till-shift": offers_till_shift, "attend-no-check-out": no_check_out,
                    "attend-request-reminders": request_reminders, "attend-warning-signs": warning_signs}.items():
        flow.handle(aid, fn)
