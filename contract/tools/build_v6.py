#!/usr/bin/env python3
"""Builds contract version 6 from version 5 (NEW UPDATE 4, owner locked 2026-11-11, master blueprint section 63).

Version 6 adds the events of LynkAttend (LynkA), LynkQueue (LynkQ) and LynkSurvey (LynkS) and the commands that issue the ones a
device may write. What never goes into an event: a PIN, an IDCN, an ID number, a face or finger pattern, a phone number, a
position, or who gave an anonymous answer. A PIN is created, sent, blocked and re-created only by the cloud. A partner's answer
(a reward or panel payment) is written by the cloud alone. Ticket numbers are the section code and a 6-character Lynk Code from
the Lynk Alphabet (2 to 9 and A to Z without O, 0, I and 1); they are not public identifiers.

Nothing in an older event changes: version 5 events read as version 6 as they are (upcaster 5 to 6 only raises the version).

    python3 contract/tools/build_v6.py          writes contract/event-payloads.v6.json and contract/command-policy-register.v6.json
    python3 contract/tools/build_v6.py --check  fails when either file is out of date (tests/test_contract_v6.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
U7, U = {"$ref": "#/$defs/uuid7"}, {"$ref": "#/$defs/uuid"}
INT0 = {"type": "integer", "minimum": 0}
INT1 = {"type": "integer", "minimum": 1}
BOOL = {"type": "boolean"}
SECTION = {"type": "string", "pattern": "^[2-9A-HJ-NP-Z]{3}$"}          # a section code, Lynk Alphabet
CODE = {"type": "string", "pattern": "^[2-9A-HJ-NP-Z]{6}$"}             # the 6-character Lynk Code of a ticket
SETS = ("face_finger_idcn", "face_idcn", "finger_idcn", "idcn")
MEANS = ("face", "finger", "idcn", "hand")
WAYS = ("smartphone", "website", "whatsapp", "lynkchat", "basic_phone", "voice", "kiosk", "pos", "email", "field", "paper")


def enum(*v):
    return {"enum": list(v)}


def arr(*v):
    return {"type": "array", "uniqueItems": True, "items": {"enum": list(v)}}


def ev(origins, required, props, note, part):
    return {"origins": origins, "since": "v6", "blueprint": f"63 {part}", "note": note,
            "payload": {"type": "object", "additionalProperties": False, "required": required, "properties": props}}


D, S, DS = ["device"], ["server"], ["device", "server"]
EVENTS = {
    # LynkAttend (LynkA)
    "AttendancePersonRegistered": ev(DS, ["member_id", "place_id", "set", "id_document"],
        {"member_id": U, "place_id": U, "set": enum(*SETS), "id_document": enum("official", "work"), "pin_group_id": U, "role": enum("staff", "student", "member", "attendee")},
        "A manager registered a person with their set. The ID number and the IDCN made from it go to the protected store, never into an event.", "LynkA"),
    "AttendanceSetChanged": ev(DS, ["member_id", "set"], {"member_id": U, "set": enum(*SETS)}, "The manager changed a person's set, with the person's agreement.", "LynkA"),
    "AttendanceConsentRecorded": ev(DS, ["member_id", "consent_id", "method", "covers"],
        {"member_id": U, "consent_id": U, "method": enum("email_link", "code_text", "code_whatsapp", "code_lynkchat", "finger_signature", "full_id_number"),
         "covers": arr("face", "finger", "no_sharing")},
        "The person agreed: the use of their face or finger if in their set, and that sharing a PIN or IDCN is cheating.", "LynkA"),
    "BiometricEnrolled": ev(D, ["member_id", "means", "device_id"], {"member_id": U, "means": enum("face", "finger"), "device_id": U},
        "Face or Finger was enrolled on the organisation's own device. The pattern stays encrypted on that device and is never in an event.", "LynkA"),
    "AttendancePinCreated": ev(S, ["member_id", "pin_group_id"], {"member_id": U, "pin_group_id": U}, "Cloud only: LynkOmni created the person's 6-digit PIN. The PIN is never in an event.", "LynkA"),
    "AttendancePinSent": ev(S, ["member_id", "channel"], {"member_id": U, "channel": enum("email", "whatsapp", "lynkchat", "text")}, "Cloud only: the PIN and IDCN were sent to the person's own contact.", "LynkA"),
    "AttendancePinShown": ev(S, ["member_id", "by"], {"member_id": U, "by": U}, "Cloud only: a manager pressed Show; every view is recorded.", "LynkA"),
    "AttendancePinBlocked": ev(DS, ["member_id", "reason"], {"member_id": U, "reason": enum("idcn_wrong_5_times", "manager")}, "The PIN was blocked; it is never used again.", "LynkA"),
    "AttendancePinRecreated": ev(S, ["member_id"], {"member_id": U}, "Cloud only: a new PIN replaced a blocked one.", "LynkA"),
    "CheckedIn": ev(D, ["record_id", "member_id", "device_id", "means"],
        {"record_id": U7, "member_id": U, "device_id": U, "means": enum(*MEANS),
         "backup_from": enum("face_failed", "finger_failed", "face_not_working", "finger_not_working"), "checker_id": U,
         "flags": arr("checker_not_checked_in", "by_hand", "device_clock_wrong"), "hand_by": U, "hand_reason": enum("all_means_failed", "device_broken", "other")},
        "A person checked in at a registered door device. The time is the door device's.", "LynkA"),
    "CheckedOut": ev(D, ["record_id", "member_id", "device_id", "means", "minutes"],
        {"record_id": U, "member_id": U, "device_id": U, "means": enum(*MEANS), "minutes": INT0, "backup_from": enum("face_failed", "finger_failed", "face_not_working", "finger_not_working"),
         "checker_id": U, "flags": arr("checker_not_checked_in", "by_hand", "device_clock_wrong")},
        "A person checked out; minutes is the time since check-in.", "LynkA"),
    "CheckInFlagged": ev(DS, ["record_id", "flag"], {"record_id": U, "flag": enum("not_me", "warning_sign", "device_clock_wrong", "no_check_out")},
        "A record was flagged for the manager. It is only a flag, never an accusation.", "LynkA"),
    "AttendanceCorrected": ev(DS, ["record_id", "by", "reason"], {"record_id": U, "by": U, "reason": enum("missed_check_out", "device_clock_wrong", "other")},
        "The manager corrected a record with a reason; the old record is kept.", "LynkA"),
    "VisitorSignedIn": ev(D, ["visitor_id", "place_id", "host_id", "id_document"],
        {"visitor_id": U7, "place_id": U, "host_id": U, "id_document": enum("official", "work", "none"), "allowed_by": U, "with_guardian": BOOL},
        "Door staff signed in a visitor after checking their ID document; with none, the manager allowed it. The ID number is never in an event.", "LynkA"),
    "VisitorDecision": ev(DS, ["visitor_id", "decision", "by"], {"visitor_id": U, "decision": enum("allow", "refuse"), "by": U}, "The manager allowed or refused a visitor without an ID document.", "LynkA"),
    "VisitorSignedOut": ev(D, ["visitor_id"], {"visitor_id": U}, "A visitor left.", "LynkA"),
    "AttendanceRequestRaised": ev(S, ["member_id", "request_id", "kind"], {"member_id": U, "request_id": U, "kind": enum("delete_my_details", "dispute")},
        "Cloud only: the person asked for deletion or raised a dispute from My details; the manager is told.", "LynkA"),
    "AttendanceDetailsDeleted": ev(S, ["member_id", "by"], {"member_id": U, "by": enum("manager", "thirty_days_passed")},
        "Cloud only: all of a person's details were deleted; hours records the law requires stay without personal details.", "LynkA"),
    "FireListOpened": ev(D, ["place_id", "by"], {"place_id": U, "by": U}, "The fire list of everyone inside was opened.", "LynkA"),
    # LynkQueue (LynkQ)
    "TicketIssued": ev(D, ["ticket_id", "place_id", "section", "code", "via"],
        {"ticket_id": U7, "place_id": U, "section": SECTION, "code": CODE, "via": enum("reception", "kiosk", "smartphone", "whatsapp", "lynkchat", "basic_phone", "api", "appointment"),
         "priority": BOOL, "device_id": U},
        "A ticket was given out. The number shown is section and code; the code is never used twice for that section at that place.", "LynkQ"),
    "TicketCalled": ev(D, ["ticket_id", "counter_id", "call"], {"ticket_id": U, "counter_id": U, "call": {"type": "integer", "minimum": 1, "maximum": 3}, "by_number": BOOL},
        "A counter called a ticket (Call next, or Call again).", "LynkQ"),
    "TicketServed": ev(D, ["ticket_id", "counter_id"], {"ticket_id": U, "counter_id": U}, "Done.", "LynkQ"),
    "TicketSentTo": ev(D, ["ticket_id", "to_section"], {"ticket_id": U, "to_section": SECTION}, "Send to: the same ticket and the same arrival time in the next section.", "LynkQ"),
    "TicketMissed": ev(D, ["ticket_id"], {"ticket_id": U}, "Not there after 3 calls.", "LynkQ"),
    "TicketPutBack": ev(D, ["ticket_id", "by"], {"ticket_id": U, "by": U}, "Reception put a missed ticket back, after the next 3 people.", "LynkQ"),
    "TicketPriorityMarked": ev(D, ["ticket_id", "by"], {"ticket_id": U, "by": U}, "Reception marked a ticket as priority.", "LynkQ"),
    "TicketRunningLate": ev(DS, ["ticket_id"], {"ticket_id": U}, "The person moved back a few places, once per ticket.", "LynkQ"),
    "TicketLeft": ev(DS, ["ticket_id"], {"ticket_id": U}, "The person left the queue.", "LynkQ"),
    "TicketNotServedToday": ev(S, ["ticket_id"], {"ticket_id": U}, "Cloud only: still waiting at closing; closed by itself.", "LynkQ"),
    "CounterStateChanged": ev(D, ["counter_id", "place_id", "state"], {"counter_id": U, "place_id": U, "state": enum("open", "paused", "closed"), "by": U}, "A counter opened, paused or closed.", "LynkQ"),
    "QueueKeeperChanged": ev(D, ["place_id", "device_id"], {"place_id": U, "device_id": U}, "Another device in the building became the queue keeper.", "LynkQ"),
    "TicketCodesReserved": ev(S, ["place_id", "device_id", "section", "first", "count"], {"place_id": U, "device_id": U, "section": SECTION, "first": CODE, "count": INT1},
        "Cloud only: a block of codes was set aside for one device to use if it is cut off.", "LynkQ"),
    "TicketCodesVoided": ev(DS, ["place_id", "device_id", "section", "first", "last", "reason"],
        {"place_id": U, "device_id": U, "section": SECTION, "first": CODE, "last": CODE, "reason": enum("block_not_used", "device_locked")},
        "Unused codes of a block were closed with a reason; they are never reused.", "LynkQ"),
    # LynkSurvey (LynkS)
    "SurveySaved": ev(DS, ["survey_id", "version", "kind", "rule", "anonymous"],
        {"survey_id": U, "version": INT1, "kind": enum("quick_rating", "satisfaction", "recommend", "staff_pulse", "staff_journey", "poll", "event_feedback", "research",
                                                         "consultation", "what_matters_most", "trade_off", "form"),
         "rule": enum("open", "one_per_phone", "invited", "verified"), "anonymous": BOOL, "languages": {"type": "array", "items": {"$ref": "#/$defs/language"}}},
        "A survey or a new version of it was saved; once answers arrive, a change makes a new version.", "LynkS"),
    "SurveyApproval": ev(DS, ["survey_id", "version", "decision", "by"], {"survey_id": U, "version": INT1, "decision": enum("approve", "send_back"), "by": U},
        "An approver approved or sent back a survey.", "LynkS"),
    "SurveyStateChanged": ev(DS, ["survey_id", "state"], {"survey_id": U, "state": enum("open", "paused", "closed", "test")}, "A survey opened, paused, closed or went into test mode.", "LynkS"),
    "SurveyAnswered": ev(D, ["answer_id", "survey_id", "version", "way", "answers"],
        {"answer_id": U7, "survey_id": U, "version": INT1, "way": enum(*WAYS), "device_id": U, "test": BOOL, "entered_by": U, "language": {"$ref": "#/$defs/language"},
         "answers": {"type": "array", "maxItems": 500, "items": {"type": "object", "additionalProperties": False, "required": ["q"],
                     "properties": {"q": {"type": "string", "maxLength": 64}, "choice": {"type": "string", "maxLength": 200}, "number": {"type": "integer"},
                                    "text": {"type": "string", "maxLength": 4000}}}}},
        "One answer from a device (kiosk, POS screen, field interview, paper entry). Never who answered an anonymous survey.", "LynkS"),
    "SurveyAnswerReceived": ev(S, ["answer_id", "survey_id", "version", "way"],
        {"answer_id": U, "survey_id": U, "version": INT1, "way": enum(*WAYS), "test": BOOL},
        "Cloud only: an answer arrived online (link, chat, text, voice, email). Its content is stored with the answer, never who answered an anonymous survey.", "LynkS"),
    "SurveyAnswerChecked": ev(S, ["answer_id", "result"], {"answer_id": U, "result": enum("accepted", "please_check", "set_aside"),
        "reason": enum("too_fast", "same_pattern", "many_from_one_device", "robot_like")}, "Cloud only: the real-answers check; please_check stays apart until the manager decides.", "LynkS"),
    "SurveyAnswerDeleted": ev(S, ["answer_id"], {"answer_id": U}, "Cloud only: the person deleted their own (non-anonymous) answer.", "LynkS"),
    "SurveyOptOut": ev(S, ["organisation_id"], {"organisation_id": U}, "Cloud only: the person pressed Don't ask me again for an organisation.", "LynkS"),
    "SurveyCallBack": ev(DS, ["task_id", "answer_id", "state"], {"task_id": U, "answer_id": U, "state": enum("created", "done"), "by": U},
        "A Call back task for an unhappy person who agreed to be contacted.", "LynkS"),
    "SurveyRewardRequested": ev(S, ["reward_id", "answer_id", "kind"], {"reward_id": U, "answer_id": U, "kind": enum("airtime", "credit", "voucher")},
        "Cloud only: a reward was asked of the payment partner after the answer passed the check.", "LynkS"),
    "SurveyRewardAnswered": ev(S, ["reward_id", "result"], {"reward_id": U, "result": enum("paid", "failed", "coming_to_country")}, "Cloud only: the partner's answer.", "LynkS"),
    "SurveyCashRewardRecorded": ev(D, ["reward_id", "answer_id", "amount", "currency"], {"reward_id": U7, "answer_id": U, "amount": {"$ref": "#/$defs/money"}, "currency": {"$ref": "#/$defs/currency"}},
        "A field worker gave a cash reward; integer minor units with the currency.", "LynkS"),
    "PanelMembership": ev(S, ["member_ref", "state"], {"member_ref": U, "state": enum("joined", "left")}, "Cloud only: a person joined or left the LynkSurvey Panel; leaving deletes their panel details.", "LynkS"),
    "SurveyResultsVerified": ev(S, ["survey_id", "version", "digest"], {"survey_id": U, "version": INT1, "digest": {"$ref": "#/$defs/sha256"}},
        "Cloud only: the results report and its research record were sealed for the check link.", "LynkS"),
}

def cmd(name, emits, rejections, permission=None, how=None, channels=("mobile",)):
    c = {"name": name, "class": "A", "v6": True, "emits": emits, "permission": permission, "channels": list(channels),
         "offline": {"allowed": True}, "cloud_may_reject": False, "cloud_outcomes": ["accepted", "accepted_flagged"],
         "local_rejections": rejections, "ui_states": ["recorded", "pending_sync", "accepted"]}
    if how: c[how] = True
    return c


COMMANDS = [
    cmd("RegisterAttendancePerson", ["AttendancePersonRegistered", "AttendanceSetChanged", "AttendanceConsentRecorded"], ["means_not_allowed_in_country", "id_document_too_few_digits", "permission_denied"], "settings.change"),
    cmd("EnrolBiometric", ["BiometricEnrolled"], ["no_consent", "no_reader", "permission_denied"], "settings.change"),
    cmd("CheckIn", ["CheckedIn", "CheckInFlagged", "AttendancePinBlocked"], ["pin_not_recognised", "means_failed", "already_checked_in", "device_not_registered"], how="local_only"),
    cmd("CheckOut", ["CheckedOut"], ["pin_not_recognised", "means_failed", "not_checked_in", "device_not_registered"], how="local_only"),
    cmd("CorrectAttendance", ["AttendanceCorrected"], ["reason_missing", "own_record", "permission_denied"], "settings.change"),
    cmd("SignInVisitor", ["VisitorSignedIn", "VisitorDecision", "VisitorSignedOut"], ["manager_not_allowed_yet", "permission_denied"], "sale.record"),
    cmd("OpenFireList", ["FireListOpened"], ["permission_denied"], "sale.record"),
    cmd("IssueTicket", ["TicketIssued", "TicketPriorityMarked"], ["section_closed", "after_last_ticket_time", "one_waiting_ticket_per_phone"], how="local_only"),
    cmd("ServeTicket", ["TicketCalled", "TicketServed", "TicketSentTo", "TicketMissed", "TicketPutBack"], ["no_one_waiting", "counter_closed", "not_valid_here"], "sale.record"),
    cmd("ChangeTicketPlace", ["TicketRunningLate", "TicketLeft"], ["already_used_once", "ticket_finished"], how="any_authenticated"),
    cmd("SetCounterState", ["CounterStateChanged"], ["permission_denied"], "sale.record"),
    cmd("TakeOverQueueKeeper", ["QueueKeeperChanged", "TicketCodesVoided"], ["device_not_added"], how="local_only"),
    cmd("SaveSurvey", ["SurveySaved", "SurveyApproval", "SurveyStateChanged", "SurveyCallBack"], ["approval_needed", "not_a_creator"], how="any_authenticated", channels=("mobile", "web")),
    cmd("AnswerSurvey", ["SurveyAnswered", "SurveyCashRewardRecorded"], ["survey_closed", "already_answered", "group_full"], how="local_only"),
]


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v5 = load("event-payloads.v5.json")
    v6 = copy.deepcopy(v5)
    v6["$id"] = "lynkomni/event-payloads.v6"
    v6["description"] = ("Contract version 6 (NEW UPDATE 4, 2026-11-11): version 5 plus the events of LynkAttend, LynkQueue and LynkSurvey. "
                         "No PIN, IDCN, ID number, face or finger pattern, phone number, position or anonymous identity is ever part of an event. "
                         "Upcaster 5 to 6 in contract/upcasters.v1.json only raises the version.")
    for e in v6["events"].values():
        e["schema_version"] = 6
    for name, e in EVENTS.items():
        if name in v6["events"]:
            raise SystemExit(f"{name} already exists in version 5")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v6["events"][name] = {"schema_version": 6, **e}
    reg = copy.deepcopy(load("command-policy-register.v5.json"))
    reg["$id"] = "lynkomni/command-policy-register.v6"
    reg["description"] = ("Command register version 6 (NEW UPDATE 4, 2026-11-11): version 5's commands unchanged plus the class A commands of "
                          "LynkAttend, LynkQueue and LynkSurvey (each works offline on the device). PINs, reward payments and the partner's answers are "
                          "written by the cloud alone.")
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(copy.deepcopy(c))
    return {"event-payloads.v6.json": v6, "command-policy-register.v6.json": reg}


def main(check=False):
    stale = []
    for name, data in build().items():
        text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
        path = os.path.join(ROOT, name)
        if check:
            if not os.path.isfile(path) or open(path, encoding="utf-8").read() != text:
                stale.append(name)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
    if stale:
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v6.py)")
        return 1
    print("contract v6 is current" if check else "wrote contract v6")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
