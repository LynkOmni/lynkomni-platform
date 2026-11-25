"""LynkAssist in LynkHR, LynkProject and LynkFiles (SIX SERVICES UPDATE 69.3, 69.4 and 69.7; ASSIST UPDATE 75.9; build section 4B):
the skills, run through the same decisions, confirmations, offline rules, history and Undo as every Business app action
(services/assist_business.py). Every action is in catalog/assist.v1.json; nothing here runs outside it.

What LynkAssist may do here: draft a letter or a review summary (labelled drafts), answer a staff question from the organisation's
own handbook, explain a leave balance, list documents about to expire, suggest training for a new staff member for the manager to
confirm (78.19), write a project status report, spot tasks at risk, suggest a new date, turn the actions in meeting minutes into
tasks after Confirm, summarise a document, find key dates in a contract, and file a scan in the right record after Confirm.
What it never does: decide hiring, pay, promotion, discipline or dismissal, score a person, approve time or leave, send an invoice,
sign or share a document, or change anything without the person's Confirm."""
from core import hr as H, project as P
from services.assist_business import BusinessAssist

WORK_ACTIONS = ("hr_draft_letter", "hr_answer_from_handbook", "hr_explain_balance", "hr_expiring_documents", "hr_summarise_review", "hr_suggest_training",
                "pj_status_report", "pj_spot_risk", "pj_suggest_date", "pj_actions_from_minutes",
                "files_summarise", "files_key_dates", "files_file_scan")


class WorkAssist(BusinessAssist):
    def __init__(self, platform, merchant, owner, acting_as, **kw):
        super().__init__(merchant, owner, **kw)
        self.p, self.m, self.by = platform, merchant, acting_as

    def _run(self, action_id, args):
        p, m = self.p, self.m
        if action_id == "hr_draft_letter":
            if args.get("kind") not in ("offer", "contract", "reference", "certificate_of_service", "policy"):
                return {"draft": None, "why": "unknown kind of letter; nothing is drafted"}, None
            return {"draft": {"kind": args["kind"], "staff": args.get("staff"), "template": f"{args['kind']}:{args.get('country', '')}"}, "label": "draft", "sent": False}, (lambda: None)
        if action_id == "hr_answer_from_handbook":
            hits = [s for s in args.get("handbook", []) if any(w.lower() in s.lower() for w in args.get("question", "").split() if len(w) > 3)]
            return {"answer_from": hits[:3], "found": bool(hits), "label": "from your handbook" if hits else "not in your handbook; ask HR"}, None
        if action_id == "hr_explain_balance":
            b = p.hr.bal.get(f"{args['staff']}|{args['kind']}") or {"entitled": 0, "taken": 0, "carried": 0}
            return {"entitled": b["entitled"], "carried": b["carried"], "taken": b["taken"], "left": H.leave_balance(b["entitled"], b["taken"], b["carried"]), "unit": "half_day"}, None
        if action_id == "hr_expiring_documents":
            return {"soon": p.hr.expiries(m, args.get("today")), "blocked": False}, None
        if action_id == "hr_summarise_review":
            return {"counts": p.hr.review_results(m, args["cycle"], args["staff"]), "label": "draft", "signed_off": False}, (lambda: None)
        if action_id == "hr_suggest_training":
            return {"suggest": list(args.get("from_role", []))[:5], "label": "suggestion", "enrolled": False, "who_decides": "manager"}, (lambda: None)
        if action_id == "pj_status_report":
            tasks = p.projects.project_tasks(m, args["project"])
            late = p.projects.late(m, args["project"], args.get("today"))
            done = sum(1 for t in tasks if t["state"] == "done")
            return {"tasks": len(tasks), "done": done, "late": late["late"], "at_risk": late["at_risk"], "money": p.projects.money(m, args["project"])}, None
        if action_id == "pj_spot_risk":
            return {"at_risk": p.projects.late(m, args["project"], args.get("today"))["at_risk"], "label": "suggestion"}, None
        if action_id == "pj_suggest_date":
            sch = p.projects.schedule(m, args["project"])
            return {"finish_day_from_start": sch["length"], "critical": sch["critical"], "label": "suggestion", "changed": False}, (lambda: None)
        if action_id == "pj_actions_from_minutes":
            made = p.projects.actions_from_minutes(m, args["project"], self.by, args.get("actions", []))
            return {"tasks": made}, None
        if action_id == "files_summarise":
            return {"summary_of": args["document"], "label": "draft", "shared": False}, None
        if action_id == "files_key_dates":
            text = args.get("text", "")
            import re
            return {"dates": sorted(set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text))), "label": "suggestion"}, None
        if action_id == "files_file_scan":
            did = p.files.store(m, self.by, args["record_kind"], args["record_id"], args.get("kind", "other"), args["data"])
            return {"document": did}, None
        return super()._run(action_id, args)
