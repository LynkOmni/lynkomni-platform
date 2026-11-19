"""LynkAssist in LynkAttend, LynkQueue and LynkSurvey (CONNECT UPDATE 71.6 and 71.9, build section 3B): the actions of the three
services, run through the same decisions, confirmations, offline rules, history and Undo as every Business app action
(services/assist_business.py). Every action is in catalog/assist.v1.json; nothing here runs outside it.

What LynkAssist may do here: open a counter on this device (and close it again), put a missed ticket back in line after Confirm,
fix a missed check-out with a reason after Confirm, write a survey draft from one sentence (the creator changes anything), pause a
survey (Undo opens it again) and send the reminders a survey already allows. What it never does: choose who is served next, decide
anything about a person, see an anonymous answer's author, or check someone in. A flag is only explained, for a person to decide."""
from services.assist_business import BusinessAssist

PEOPLE_ACTIONS = ("queue_open_counter", "queue_put_back_ticket", "attend_fix_check_out", "attend_explain_flag", "survey_write_it_for_me", "survey_pause", "survey_send_reminders")


class PeopleAssist(BusinessAssist):
    def __init__(self, platform, merchant, owner, acting_as, keeper=None, **kw):
        super().__init__(merchant, owner, **kw)
        self.p, self.m, self.by, self.keeper = platform, merchant, acting_as, keeper

    def _run(self, action_id, args):
        if action_id == "queue_open_counter":
            k = self.keeper; was = k.counters[args["counter"]]["state"]
            k.counter_state(args["counter"], "open", by=self.by)
            return {"counter": args["counter"], "was": was}, (lambda: k.counter_state(args["counter"], was, by=self.by)) if was != "open" else None
        if action_id == "queue_put_back_ticket":
            self.keeper.put_back(args["ticket"], by=self.by)
            return {"ticket": args["ticket"], "state": "waiting"}, None
        if action_id == "attend_fix_check_out":
            self.p.attendance.correct(self.m, args["record"], self.by, "missed_check_out", out_at=args["out_at"])
            return {"record": args["record"], "kept": "old line kept beside the new one"}, None
        if action_id == "survey_write_it_for_me":
            draft = self.p.survey.write_it_for_me(self.m, self.by, args["sentence"], args.get("language", "en"))
            return {"draft": draft["kind"], "questions": len(draft["questions"]), "suggestion": True}, (lambda: None)    # nothing is saved until the creator saves it
        if action_id == "survey_pause":
            self.p.survey.set_state(self.m, args["survey"], self.by, "paused")
            return {"survey": args["survey"], "state": "paused"}, (lambda: self.p.survey.set_state(self.m, args["survey"], self.by, "open"))
        if action_id == "survey_send_reminders":
            return {"reminded": len(self.p.survey.reminders(self.m))}, None
        return super()._run(action_id, args)
