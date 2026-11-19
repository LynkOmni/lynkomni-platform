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

    # ---- LynkSurvey (each only after the manager switched it on; the rest period and "Don't ask me again" are always respected)
    sv = platform.survey

    def after_shift_question(f, m, p, now):
        asked = sv.ask_after(m, "lynkattend", person=p["member_id"], now=now)
        return {"asked": 1, "why": "a staff member checked out; one short question about the shift or class, as the manager chose"} if asked else None

    def after_queue_done(f, m, p, now):
        r = qu.db.execute("select contact_ref from qu_tickets where ticket_id=?", (p["ticket_id"],)).fetchone()
        asked = sv.ask_after(m, "lynkqueue", contact_ref=r[0] if r else None, now=now)
        return {"asked": 1, "by_message": bool(r and r[0]), "why": "a visit ended with Done in LynkQueue; one question about the service (by message only to someone who joined by phone)"} if asked else None

    def after_pos_sale(f, m, p, now):
        sid = sv.open_after(m, "lynkpos")
        if not sid: return None
        _signal(f, m, "AlertSent", {"kind": "survey_rating_after_payment", "ref": p["sale_id"], "detail": {"survey_id": sid}}, "survey-after-pos-sale", now)
        return {"shown_on": "customer_screen", "why": "a sale was paid; the customer screen asks \"How was your visit?\" (never required)"}

    def after_chat(f, m, p, now):
        asked = sv.ask_after(m, "lynkchat", person=p.get("customer_id"), now=now)
        return {"asked": 1, "why": "a support chat ended; \"Did we solve your problem?\""} if asked else None

    def call_back(f, m, p, now):
        if p.get("test"): return None
        r = sv.db.execute("select answers, survey_id from sv_answers where answer_id=?", (p["answer_id"],)).fetchone()
        if not r or not sv._unhappy(None, __import__("json").loads(r[0]), r[1]): return None
        tid = sv.call_back(m, p["answer_id"], now=now)
        return {"task": tid, "why": "an unhappy person left a contact and agreed to be called back; the task has a time limit"} if tid else None

    def reminders(f, m, p, now):
        told = sv.reminders(m, now)
        return {"reminded": len(told), "why": "invited people who have not answered get up to 2 reminders, then no more"} if told else None

    def summary(f, m, p, now):
        n = 0
        for (sid,) in sv.db.execute("select survey_id from sv_surveys where merchant=? and state='open'", (m,)).fetchall():
            owner = sv.db.execute("select by from sv_surveys where survey_id=?", (sid,)).fetchone()[0]
            if sv.summary(m, sid, owner)["shown"]: n += 1
        return {"summaries": n, "why": "LynkAssist says in plain words what people are saying (only from results of 5 answers or more); a suggestion"} if n else None

    def write_it(f, m, p, now):
        d = sv.write_it_for_me(m, p["by"], p["sentence"], p.get("language", "en"))
        return {"draft": d["kind"], "questions": len(d["questions"]), "why": "LynkAssist wrote a draft from one sentence; the creator changes anything before it is saved"}

    def repeat(f, m, p, now):
        again = sv.repeat_due(m, now)
        return {"opened_again": len(again), "why": "a repeating survey runs again by itself, as its creator set"} if again else None

    for aid, fn in {"attend-after-shift-question": after_shift_question, "queue-survey-after-done": after_queue_done, "survey-after-pos-sale": after_pos_sale,
                    "survey-after-chat": after_chat, "survey-call-back": call_back, "survey-reminders": reminders, "survey-summary": summary,
                    "survey-write-it-for-me": write_it, "survey-repeat": repeat}.items():
        flow.handle(aid, fn)

    for aid, fn in {"queue-please-come": please_come, "queue-not-served-today": not_served_today, "queue-open-counter": open_counter, "queue-busy-forecast": busy_forecast,
                    "queue-pickup-collection": pickup_collection, "attend-opens-queue-counter": opens_queue_counter}.items():
        flow.handle(aid, fn)

    for aid, fn in {"attend-was-this-you": was_this_you, "attend-offers-till-shift": offers_till_shift, "attend-no-check-out": no_check_out,
                    "attend-request-reminders": request_reminders, "attend-warning-signs": warning_signs}.items():
        flow.handle(aid, fn)
