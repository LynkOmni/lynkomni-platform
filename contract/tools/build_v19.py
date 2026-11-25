#!/usr/bin/env python3
"""Builds contract version 19 from version 18 (SIX SERVICES UPDATE, owner 2026-11-18, master blueprint section 69; built in build
section 4B: LynkFiles, LynkHR and LynkProject in full).

Version 19 adds the events of LynkHR (staff records, joining and leaving steps, leave, review cycles, pay changes, payroll figures,
HR cases), LynkProject (projects, tasks and their states and waiting, milestones, time, time sheets, billing time once, change
requests, project costs) and two LynkFiles flows (approval routes and document requests).

Offline (blueprint 69.9): leave requests and their answers, joining and leaving steps, review answers, HR cases, projects, tasks,
task states and waiting, milestones, time and time sheets and change requests may come from a device. Pay, payroll figures,
billing time, project costs, cycle openings, decisions on change requests, the steps of an HR case, approval routes and document
requests are written by the cloud alone.

What is never in an event: a person's name, contact, ID number, bank details, health, family or union details, a review's or a case's
words, a task's title or notes, a file's content or name, a position. Events carry ids, kinds, whole numbers and dates only.

Nothing older changes: version 18 events read as version 19 as they are (upcaster 18 to 19 only raises the version).

    python3 contract/tools/build_v19.py          writes contract/event-payloads.v19.json and contract/command-policy-register.v19.json
    python3 contract/tools/build_v19.py --check  fails when either file is out of date (tests/test_contract_v19.py runs it)
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(os.path.dirname(ROOT), "catalog")
U7 = {"$ref": "#/$defs/uuid7"}
UU = {"$ref": "#/$defs/uuid"}
DATE = {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"}
MINOR = {"type": "integer", "minimum": 0}
CUR = {"type": "string", "pattern": "^[A-Z]{3}$"}


def _cat(name):
    with open(os.path.join(CAT, name), encoding="utf-8") as f:
        return json.load(f)


HR, PJ = _cat("hr.v1.json"), _cat("project.v1.json")
# A published version never reads a later register change: the review kinds version 19 was published with (2026-11-25). Later kinds
# (lesson_observation, SCHOOL UPDATE 80.15) join version 20 (build_v20.py).
HR["reviews"]["kinds"] = ["self", "manager", "peer", "upward"]


def ev(origins, note, required, props, blueprint="69 SIX SERVICES UPDATE"):
    return {"origins": origins, "since": "v19", "blueprint": blueprint, "note": note,
            "payload": {"type": "object", "additionalProperties": False, "required": required, "properties": props}}


DEV = ["device", "server"]
SRV = ["server"]
EVENTS = {
    # ---- LynkHR (69.3) ------------------------------------------------------------------------------------------------------
    "StaffRecordCreated": ev(SRV, "A staff record (LOSTF-) in LynkHR. The name and contact stay in the PII vault; the event carries the kind of worker only.",
                             ["staff_id", "worker_kind", "start_date"], {"staff_id": U7, "worker_kind": {"enum": HR["workers"]}, "start_date": DATE, "branch_id": U7}),
    "StaffChecklistStepDone": ev(DEV, "A joining or leaving step done (offline too). Final pay figures go to LynkAcc only after notice, equipment back and access closed.",
                                 ["staff_id", "checklist", "step"], {"staff_id": U7, "checklist": {"enum": ["joining", "leaving"]},
                                                                     "step": {"enum": sorted({i["id"] for c in HR["checklists"].values() if isinstance(c, list) for i in c})}, "by": UU}),
    "StaffLeft": ev(SRV, "A staff member's last day, after the leaving checklist's musts are done.", ["staff_id", "last_day"], {"staff_id": U7, "last_day": DATE}),
    "LeaveRequested": ev(DEV, "A leave request in half days (offline too). A clash is shown, never a refusal.",
                         ["request_id", "staff_id", "kind", "half_days", "first_day", "last_day"],
                         {"request_id": U7, "staff_id": U7, "kind": {"enum": HR["leave"]["kinds"]}, "half_days": {"type": "integer", "minimum": 1, "maximum": 730},
                          "first_day": DATE, "last_day": DATE}),
    "LeaveAnswered": ev(DEV, "The manager's answer to a leave request (offline too); never the person who asked.",
                        ["request_id", "answer", "by"], {"request_id": U7, "answer": {"enum": ["approved", "declined"]}, "by": UU}),
    "LeaveCancelled": ev(DEV, "A leave request withdrawn by the person or cancelled before it starts.", ["request_id"], {"request_id": U7}),
    "ReviewCycleOpened": ev(SRV, "A review cycle opened by HR with the kinds of answers it asks for.", ["cycle_id", "kinds", "closes"],
                            {"cycle_id": U7, "kinds": {"type": "array", "items": {"enum": HR["reviews"]["kinds"]}, "minItems": 1, "uniqueItems": True}, "closes": DATE}),
    "ReviewAnswered": ev(DEV, "One answer given in a review cycle (its words stay in LynkHR; peer and upward answers carry nobody).",
                         ["cycle_id", "staff_id", "kind"], {"cycle_id": U7, "staff_id": U7, "kind": {"enum": HR["reviews"]["kinds"]}}),
    "ReviewSignedOff": ev(SRV, "A person's review signed off by the named manager; the person can ask for a human review of it.",
                          ["cycle_id", "staff_id", "by"], {"cycle_id": U7, "staff_id": U7, "by": UU}),
    "PayChangeProposed": ev(SRV, "A pay change proposed (figures only; payroll runs in LynkAcc).", ["change_id", "staff_id", "kind", "amount", "currency"],
                            {"change_id": U7, "staff_id": U7, "kind": {"enum": HR["pay"]["changes"]}, "amount": {"type": "integer"}, "currency": CUR}),
    "PayChangeApproved": ev(SRV, "A pay change approved by a different person (and a third when over the budget).", ["change_id", "by"],
                            {"change_id": U7, "by": UU, "second_by": UU}),
    "PayrollFiguresSent": ev(SRV, "One period's payroll figures handed to LynkAcc: totals only, never a person's pay in the event.",
                             ["period", "staff_count", "gross_total", "currency"], {"period": {"type": "string", "pattern": "^\\d{4}-\\d{2}$"},
                                                                                   "staff_count": {"type": "integer", "minimum": 0}, "gross_total": MINOR, "currency": CUR}),
    "HrCaseOpened": ev(DEV, "An HR case (grievance, discipline, investigation, concern, help desk). An anonymous concern carries nobody.",
                       ["case_id", "kind"], {"case_id": U7, "kind": {"enum": HR["cases"]["kinds"]}, "staff_id": U7}),
    "HrCaseStepMoved": ev(SRV, "An HR case moved to its next step, each with its deadline; a decision is always a named person's.", ["case_id", "step"],
                          {"case_id": U7, "step": {"enum": HR["cases"]["steps"]}}),
    # ---- LynkProject (69.4) -------------------------------------------------------------------------------------------------
    "ProjectCreated": ev(DEV, "A project (LOPRJ-) from a template or blank (offline too). Its name stays in LynkProject.", ["project_id", "method"],
                         {"project_id": U7, "method": {"enum": PJ["methods"]}, "template": {"enum": PJ["templates"]}}),
    "TaskCreated": ev(DEV, "A task (LOTSK-) in a project, captured any way (offline too). Its title and notes never travel in the event.",
                      ["task_id", "project_id", "priority", "source"], {"task_id": U7, "project_id": U7, "priority": {"enum": PJ["priorities"]},
                                                                         "source": {"enum": PJ["capture"]}, "due": DATE, "owner": UU}),
    "TaskStateChanged": ev(DEV, "A task moved (offline too); done only when what it waits on is done.", ["task_id", "from", "to"],
                           {"task_id": U7, "from": {"enum": PJ["states"]}, "to": {"enum": PJ["states"]}}),
    "TaskWaitAdded": ev(DEV, "A task now waits on another task; never itself and never in a circle.", ["task_id", "waits_on"], {"task_id": U7, "waits_on": U7}),
    "MilestoneReached": ev(DEV, "A project milestone reached (offline too).", ["project_id", "milestone_id"], {"project_id": U7, "milestone_id": U7}),
    "TimeLogged": ev(DEV, "Time on a project in whole minutes (offline too).", ["entry_id", "project_id", "minutes", "billable"],
                     {"entry_id": U7, "project_id": U7, "task_id": U7, "minutes": {"type": "integer", "minimum": 1, "maximum": PJ["time"]["max_entry_minutes"]}, "billable": {"type": "boolean"}}),
    "TimeSheetAnswered": ev(DEV, "A week's time sheet approved or sent back by a manager, never the person who logged it.", ["sheet_id", "answer", "minutes", "by"],
                            {"sheet_id": U7, "answer": {"enum": ["approved", "returned"]}, "minutes": {"type": "integer", "minimum": 0}, "by": UU}),
    "ProjectTimeBilled": ev(SRV, "Approved billable time put on a LynkInv invoice, once.", ["project_id", "invoice", "minutes", "amount", "currency"],
                            {"project_id": U7, "invoice": {"type": "string", "pattern": "^LOINV-\\d{4}-\\d{4}-\\d{4}$"}, "minutes": {"type": "integer", "minimum": 1}, "amount": MINOR, "currency": CUR}),
    "ProjectCostRecorded": ev(SRV, "A cost or purchase for a project, posted through LynkAcc.", ["project_id", "cost_id", "amount", "currency"],
                              {"project_id": U7, "cost_id": U7, "amount": MINOR, "currency": CUR}),
    "ChangeRequestRaised": ev(DEV, "A change request on a project (offline too).", ["request_id", "project_id"], {"request_id": U7, "project_id": U7, "cost_change": {"type": "integer"}, "days_change": {"type": "integer"}}),
    "ChangeRequestDecided": ev(SRV, "A change request accepted or refused by the named person.", ["request_id", "decision", "by"],
                               {"request_id": U7, "decision": {"enum": ["accepted", "refused"]}, "by": UU}),
    # ---- LynkFiles flows (69.7) ---------------------------------------------------------------------------------------------
    "ApprovalRouteStarted": ev(SRV, "An approval route for a document, bill, expense or invoice, with its approvers in order.", ["route_id", "document_id", "steps"],
                               {"route_id": U7, "document_id": U7, "steps": {"type": "integer", "minimum": 1, "maximum": 10}}),
    "ApprovalStepAnswered": ev(SRV, "One approver's answer on a route; never the person who sent it.", ["route_id", "step", "answer", "by"],
                               {"route_id": U7, "step": {"type": "integer", "minimum": 1, "maximum": 10}, "answer": {"enum": ["approved", "returned"]}, "by": UU}),
    "DocumentRequested": ev(SRV, "A request for someone to upload a document into a folder (a staff file, a certificate).", ["request_id", "kind", "due"],
                            {"request_id": U7, "kind": {"enum": ["id_document", "certificate", "contract", "staff_file", "other"]}, "due": DATE}),
    "DocumentRequestAnswered": ev(SRV, "The requested document arrived (it is a DocumentFiled) and was checked, or the request was closed.", ["request_id", "result"],
                                  {"request_id": U7, "result": {"enum": ["received", "checked", "closed"]}, "document_id": U7}),
}

DEVICE_ONLY = [n for n, e in EVENTS.items() if "device" in e["origins"]]
COMMANDS = [{"name": f"Record{n}", "class": "A", "v19": True, "emits": [n], "permission": None, "channels": ["mobile", "web"], "local_only": True,
             "local_rejections": ["not_allowed_for_role"], "offline": {"allowed": True}, "cloud_may_reject": False, "cloud_outcomes": ["accepted"],
             "ui_states": ["recorded", "pending_sync", "accepted"]} for n in DEVICE_ONLY]


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    v = copy.deepcopy(load("event-payloads.v18.json"))
    v["$id"] = "lynkomni/event-payloads.v19"
    v["description"] = ("Contract version 19 (SIX SERVICES UPDATE, master blueprint section 69, built in section 4B): version 18 plus the events of LynkHR, "
                        "LynkProject and LynkFiles' approval routes and document requests. Upcaster 18 to 19 in contract/upcasters.v1.json only raises the version.")
    for e in v["events"].values():
        e["schema_version"] = 19
    # the cards and tracking kinds added in build section 4B join here; older versions keep the lists they were published with
    with open(os.path.join(CAT, "chat.v1.json"), encoding="utf-8") as f:
        cards = list(json.load(f)["cards"]["kinds"])
    enum = v["events"]["ConversationCardSent"]["payload"]["properties"]["card"]["enum"]
    enum += [k for k in cards if k not in enum]
    with open(os.path.join(CAT, "tracking.v1.json"), encoding="utf-8") as f:
        kinds = [k["id"] for k in json.load(f)["kinds"]]
    enum = v["events"]["TrackingStepMarked"]["payload"]["properties"]["kind"]["enum"]
    enum += [k for k in kinds if k not in enum]
    for name, e in EVENTS.items():
        if name in v["events"]:
            raise SystemExit(f"{name} already exists in version 18")
        e = copy.deepcopy(e)
        e["payload"]["properties"]["side"] = {"$ref": "#/$defs/side"}
        v["events"][name] = {"schema_version": 19, **e}
    reg = copy.deepcopy(load("command-policy-register.v18.json"))
    reg["$id"] = "lynkomni/command-policy-register.v19"
    reg["description"] = ("Command register version 19 (SIX SERVICES UPDATE, master blueprint section 69): version 18's commands plus the LynkHR and LynkProject "
                          "steps a device may record offline (class A: recorded on the device, accepted by the cloud).")
    names = {c["name"] for c in reg["commands"]}
    for c in COMMANDS:
        if c["name"] in names:
            raise SystemExit(f"command {c['name']} already exists")
        reg["commands"].append(copy.deepcopy(c))
    return {"event-payloads.v19.json": v, "command-policy-register.v19.json": reg}


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
        print("out of date: " + ", ".join(stale) + " (run python3 contract/tools/build_v19.py)")
        return 1
    print("contract v19 is current" if check else "wrote contract v19")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
