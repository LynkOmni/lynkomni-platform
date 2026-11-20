"""LynkAssist in LynkAcc, LynkInv, LynkCRM and LynkStat (ASSIST UPDATE 75.6; section 4 step D4c): the office skills, run through
the same decisions, confirmations, offline rules, history and Undo as every Business app action (services/assist_business.py).
Every action is in catalog/assist.v1.json; nothing here runs outside it.

What LynkAssist may do here: suggest a category and a match (labelled suggestions), explain a statement line by line from the
books' own figures, show the month-end checklist with what is missing, draft an invoice or quote from a conversation, draft a
polite plan for a late payer, summarise a customer, suggest who to contact next and why, explain why a chart changed, and issue
a credit note after Confirm. What it never does: post an entry without the person, close a period, file tax or run payroll
(those are only prepared for a person), send a reminder the business did not approve, message a customer who has not opted in,
or present an estimate as a fact."""
from collections import Counter

from core import books as B
from services.assist_business import BusinessAssist

OFFICE_ACTIONS = ("acc_suggest_category", "acc_suggest_match", "acc_explain_statement", "acc_month_end_checklist", "inv_draft_from_chat",
                  "inv_draft_from_photo", "inv_late_payer_plan", "crm_customer_summary", "crm_next_contact", "stat_why_changed", "issue_credit_note")


class OfficeAssist(BusinessAssist):
    def __init__(self, platform, merchant, owner, acting_as, **kw):
        super().__init__(merchant, owner, **kw)
        self.p, self.m, self.by = platform, merchant, acting_as

    def _run(self, action_id, args):
        p, m = self.p, self.m
        if action_id == "acc_suggest_category":
            # the account this business used most for the same supplier, otherwise nothing: never a guess shown as fact
            seen = Counter(v["account"] for _, v in p.books.bills.items() if v["merchant"] == m and v.get("supplier") and v["supplier"] == args.get("supplier"))
            best = seen.most_common(1)[0][0] if seen else None
            return {"suggestion": best, "label": "suggestion", "posted": False}, None
        if action_id == "acc_suggest_match":
            return {"matches": p.books.match_bank(m, args["items"]), "label": "suggestion", "matched": False}, None
        if action_id == "acc_explain_statement":
            st = p.books.statements(m)["statements"]
            order = ("income", "other_income", "cost_of_sales", "gross", "expenses", "profit")
            return {"lines": [{"line": k, "amount_minor": st[k]} for k in order], "balanced": st["balanced"]}, None
        if action_id == "acc_month_end_checklist":
            missing = B.close_missing(args.get("done", []))
            return {"missing": missing, "ready": not missing, "closed": False}, None
        if action_id in ("inv_draft_from_chat", "inv_draft_from_photo"):
            lines = [ln for ln in args.get("lines", []) if ln.get("qty_milli", 0) > 0 and ln.get("unit_minor", 0) >= 0]
            if not lines:
                return {"draft": None, "why": "no line with a quantity was found; nothing is drafted"}, None
            draft = {"kind": args.get("kind", "invoice"), "customer": args.get("customer"), "lines": lines, "totals": p.invoicing.totals(m, lines)}
            return {"draft": draft, "issued": False, "suggestion": True}, (lambda: None)       # nothing is kept until the person issues it
        if action_id == "inv_late_payer_plan":
            iid = args["invoice"]
            owed = p.invoicing.outstanding(iid)
            count = max(2, min(int(args.get("instalments", 3)), 12))
            plan = {"invoice": iid, "owed_minor": owed, "instalments": B.split(owed, count) if owed > 0 else [],
                    "reminders": "only the steps the business approved", "sent": False}
            return {"plan": plan, "suggestion": True}, (lambda: None)
        if action_id == "crm_customer_summary":
            view = p.crm.view(m, {"user": self.by, "role": args.get("role", "owner"), "team": args.get("team")}, args["record"])
            inv = [v for _, v in p.invoicing.inv.items() if v["merchant"] == m and v["customer"] == args["record"]]
            return {"record": view["id"], "kind": view["kind"], "tags": view["tags"], "invoices": len(inv),
                    "owed_minor": sum(max(p.invoicing.outstanding(k), 0) for k, v in p.invoicing.inv.items() if v["merchant"] == m and v["customer"] == args["record"])}, None
        if action_id == "crm_next_contact":
            out = []
            for k, v in p.invoicing.inv.items():
                if v["merchant"] != m or v["customer"] not in p.crm.recs or p.invoicing.outstanding(k) <= 0:
                    continue
                may = p.crm.may_message(m, v["customer"], args.get("channel", "email"))
                out.append({"record": v["customer"], "why": "owes_on_invoice", "invoice": k, "may_message": may, "suggest": "message" if may else "call_or_visit"})
            return {"next": out[:10], "label": "suggestion"}, None
        if action_id == "stat_why_changed":
            notes = p.stats.notes_on(m, args["start"], args["end"])
            before, after = args["before"], args["after"]
            return {"change": after - before, "notes": notes, "estimate": bool(args.get("estimate")),
                    "label": "estimate" if args.get("estimate") else "from the records"}, None
        if action_id == "issue_credit_note":
            r = p.invoicing.credit_note(m, args["invoice"], args["amount_minor"], args["reason"])
            return {"credit": r["credit"], "outstanding_minor": r["outstanding_minor"]}, None
        return super()._run(action_id, args)
