"""LynkSurvey on an added device (LynkS; build section 3B): LynkKiosk, LynkTab, LynkPOS's customer screen and a field worker's
LynkMobile. The device only follows the cloud: it holds the open surveys it was given (people/survey.py device_pack) and records
each answer as a contract event on its own chain (dv/box.py), with or without internet; the cloud checks it when it arrives, in
the right order and never twice. A field worker's answers and paper entries carry who entered them. A device never decides who
may answer: the kiosk takes one answer at a time and starts again for the next person."""
from contract.tools.validate_contract import uuid7
from dv.box import LocalRejection


class SurveyDevice:
    def __init__(s, box, pack=None):
        s.box, s.pack = box, pack
    def _ready(s):
        if not s.pack or s.pack.get("locked"): raise LocalRejection("device_not_added")
    def surveys(s):
        s._ready(); return [x for x in s.pack["surveys"] if x["state"] in ("open", "test")]
    def answer(s, survey_id, way, answers, language="en", entered_by=None):
        """One person's answer, written at once to the device's log (the five user states: queued until it is sent)."""
        s._ready(); s.box._guard("AnswerSurvey")
        sv = next((x for x in s.pack["surveys"] if x["survey_id"] == survey_id), None)
        if not sv or sv["state"] not in ("open", "test"): raise LocalRejection("survey_closed")
        if way not in s.pack["ways"]: raise LocalRejection("way_not_on_this_device")
        known = {q["id"] for q in sv["questions"]}
        if any(a["q"] not in known for a in answers): raise LocalRejection("unknown_question")
        p = {"answer_id": uuid7(), "survey_id": survey_id, "version": sv["version"], "way": way, "device_id": s.box.d, "language": language, "answers": answers}
        if sv["state"] == "test": p["test"] = True
        if entered_by: p["entered_by"] = entered_by
        s.box._emit("SurveyAnswered", p)
        return p["answer_id"]
    def cash_reward(s, answer_id, amount, currency):
        """Cash given by a field worker for a full answer is recorded too (integers only; LynkOmni never holds it)."""
        s._ready(); s.box._guard("AnswerSurvey")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0: raise LocalRejection("whole_minor_units_only")
        rid = uuid7(); s.box._emit("SurveyCashRewardRecorded", {"reward_id": rid, "answer_id": answer_id, "amount": amount, "currency": currency}); return rid
