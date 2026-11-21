"""LynkAcc in the cloud (OFFICE UPDATE, master blueprint 66.2; section 4 step D2b), on the rules of core/books.py and the chart of
contract/chart-of-accounts.v2.json.

Bills to pay (entered, approved step by step, matched with the order and the goods received, paid only when the provider
confirms), expense claims (receipts, mileage, allowances; approved by someone else; repaid), assets and their loss of value,
journals (balanced, named accounts, two people for sensitive kinds, never on a locked date), the lock date, the year-end close,
revaluation, bank matching and the statements. Every fact is an event in the log (contract version 11), and the journal is the
log's projection (services/suite.py Accountant.journal), so nothing here keeps a second ledger. Tiers follow 66.7
(services/billing.py FEATURES lynkacc). LynkOmni never holds funds: money moves only through the licensed provider."""
import time, uuid

from core import accounts as AC
from core import books as B
from core.regions import country
from services.improvements import Table, _cur

SENSITIVE = {"manual": "manual_journal", "reversal": "reversal", "opening_balance": "opening_balance", "write_off": "write_off"}


class Books:
    def __init__(s, p, now=time.time):
        s.p, s.now, db = p, now, p.c.store.db
        s.bills, s.claims, s.assets = Table(db, "acc_bills"), Table(db, "acc_claims"), Table(db, "acc_assets")
        s.pending, s.settings, s.bank = Table(db, "acc_pending"), Table(db, "acc_settings"), Table(db, "acc_bank")

    # ---- plan, settings, events ----------------------------------------------------------------------------------------------
    def ent(s, m):
        return s.p.billing.entitlement(m, "lynkacc")

    def _need(s, m, feature, words):
        if not s.ent(m).get(feature):
            raise PermissionError(f"{words} need a higher LynkAcc plan")

    def _pack(s, m):
        return country(s.p.c.profile(m)["country"])

    def lock_date(s, m):
        r = s.settings.get(f"{m}|lock")
        return r["date"] if r else None

    def _today(s):
        return time.strftime("%Y-%m-%d", time.gmtime(s.now()))

    def _emit(s, m, type_, payload):
        s.p.c.store.append(m, "server", type_, payload)

    def _post_journal(s, m, kind, lines, prepared_by, approved_by=None, date=None):
        """A balanced journal of named accounts, never on a locked date (accounts.checked_lines refuses anything else)."""
        date = date or s._today()
        if not B.may_post(date, s.lock_date(m)):
            raise PermissionError("that date is locked; post it in the next open period")
        ok = AC.checked_lines([list(l) for l in lines])
        if not ok:
            raise ValueError("a journal must balance and name real accounts")
        jid = uuid.uuid4().hex
        s._emit(m, "journal.posted", {"journal_id": jid, "kind": kind, "lines": [list(l) for l in ok], "currency": _cur(s.p, m),
                                       "prepared_by": prepared_by, "approved_by": approved_by, "date": date})
        return jid

    # ---- bills to pay --------------------------------------------------------------------------------------------------------
    def record_bill(s, m, by, total_minor, source="hand", account="6000", due=None, order=None, supplier=None, dims=None, bill_id=None):
        """A supplier bill joins Bills to pay. It is posted as owed at once (accrual), and waits for approval before payment."""
        if total_minor <= 0:
            raise ValueError("a bill needs a total")
        if source not in B.BOOKS["bills"]["sources"]:
            raise ValueError("unknown source")
        if dims and (not B.dims_ok(dims) or not s.ent(m).get("dimensions")):
            raise PermissionError("departments, projects and funds on entries need LynkAcc Pro")
        bid = bill_id or uuid.uuid4().hex
        if bid in s.bills:
            return {"bill": bid, "duplicate": True}
        rec = {"merchant": m, "by": by, "total": total_minor, "paid": 0, "account": account, "due": due, "order": order, "supplier": supplier,
               "dims": dims or {}, "state": "draft", "approvals": [], "match": None}
        s.bills.put(bid, rec)
        s._emit(m, "bill.recorded", {"bill_id": bid, "total_minor": total_minor, "account": account, "source": source, "currency": _cur(s.p, m), "state": "draft"})
        return {"bill": bid, "state": "draft"}

    def submit_bill(s, m, bid):
        b = s.bills[bid]
        nxt = B.bill_move(b["state"], "submit")
        if not nxt:
            raise ValueError(f"bill is {b['state']}")
        b["state"] = nxt if s.ent(m).get("approval_steps") else "approved"     # one person on Free: no approval steps to wait for
        s._emit(m, "bill.submitted", {"bill_id": bid, "state": b["state"]})
        return b["state"]

    def approve_bill(s, m, bid, approver, role):
        """One approval step. The person who entered the bill never approves it; steps follow the amount (books register)."""
        b = s.bills[bid]
        if b["state"] != "awaiting_approval":
            raise ValueError(f"bill is {b['state']}")
        if not B.may_approve(b["by"], approver):
            raise PermissionError("the person who entered a bill never approves it")
        need = B.approvers(b["total"], (s.settings.get(f"{m}|approval") or {}).get("rules"))
        step = len(b["approvals"])
        if step >= len(need) or role != need[step]:
            raise PermissionError(f"this step needs the {need[step] if step < len(need) else 'nobody'}")
        if any(a["who"] == approver for a in b["approvals"]):
            raise PermissionError("each step is a different person")
        b["approvals"] = b["approvals"] + [{"who": approver, "role": role}]
        if len(b["approvals"]) == len(need):
            b["state"] = B.bill_move("awaiting_approval", "approve")
        s._emit(m, "bill.approved", {"bill_id": bid, "step": step + 1, "by": role, "state": b["state"]})
        return b["state"]

    def match_bill(s, m, bid, po, received, bill_lines, tolerance_bp=0):
        r = B.match3(po, received, bill_lines, tolerance_bp)
        s.bills[bid]["match"] = r
        return r

    def pay_bill(s, m, bid, amount_minor, method="bank", provider_confirmed=False, ref=None):
        """Paid only when the licensed provider confirms (cash is counted at once); a bill with an order must match it first."""
        b = s.bills[bid]
        if b["state"] not in ("approved", "scheduled", "part_paid"):
            raise ValueError(f"bill is {b['state']}; it is approved before it is paid")
        if b["order"] and not (b["match"] or {}).get("ok"):
            raise PermissionError("check the bill against its order and the goods received first")
        if method != "cash" and not provider_confirmed:
            raise PermissionError("a payment counts only after the provider confirms it")
        left = b["total"] - b["paid"]
        if amount_minor <= 0 or amount_minor > left:
            raise ValueError("amount must be positive and not above what is owed")
        b["paid"] = b["paid"] + amount_minor
        b["state"] = B.bill_move(b["state"], "pay_all" if b["paid"] == b["total"] else "pay_part")
        s._emit(m, "bill.paid", {"bill_id": bid, "amount_minor": amount_minor, "method": method, "ref": ref, "state": b["state"]})
        return {"state": b["state"], "left": b["total"] - b["paid"]}

    def payment_run(s, m, bill_ids, approver):
        """Many approved bills in one approved run; each is paid when the provider confirms it (pay_bill)."""
        s._need(m, "payment_runs", "payment runs")
        run = []
        for bid in bill_ids:
            b = s.bills[bid]
            if b["state"] == "approved" and b["by"] != approver:
                b["state"] = B.bill_move("approved", "schedule")
                run.append({"bill": bid, "amount": b["total"] - b["paid"]})
        return {"run": uuid.uuid4().hex, "bills": run, "total": sum(r["amount"] for r in run)}

    # ---- staff spending ------------------------------------------------------------------------------------------------------
    def submit_claim(s, m, by, kind, total_minor=None, km_thousandths=None, days=None, rate_minor=None, account="6000"):
        """A receipt, mileage or allowance claim. The rate comes from the country pack, or the owner's lower rate."""
        pack = (s._pack(m).get("office") or {})
        if kind == "mileage":
            rate = min(x for x in (rate_minor, pack.get("mileage_rate_minor")) if x is not None) if (rate_minor or pack.get("mileage_rate_minor")) else None
            if rate is None or km_thousandths is None:
                raise ValueError("mileage needs a distance and a rate")
            total_minor = B.mileage(km_thousandths, rate)
        elif kind == "allowance":
            rate = min(x for x in (rate_minor, pack.get("daily_allowance_minor")) if x is not None) if (rate_minor or pack.get("daily_allowance_minor")) else None
            if rate is None or days is None:
                raise ValueError("an allowance needs days and a rate")
            total_minor = B.allowance(days, rate)
        elif kind != "receipt" or not total_minor:
            raise ValueError("a receipt claim needs a total")
        cid = uuid.uuid4().hex
        s.claims.put(cid, {"merchant": m, "by": by, "kind": kind, "total": total_minor, "account": account, "state": "submitted"})
        s._emit(m, "expense_claim.submitted", {"claim_id": cid, "kind": kind, "total_minor": total_minor, "state": "submitted"})
        return {"claim": cid, "total": total_minor}

    def approve_claim(s, m, cid, approver, role):
        c = s.claims[cid]
        if c["state"] != "submitted":
            raise ValueError(f"claim is {c['state']}")
        if c["by"] == approver:
            raise PermissionError("nobody approves their own claim")
        c["state"] = "approved"
        s._emit(m, "expense_claim.approved", {"claim_id": cid, "total_minor": c["total"], "account": c["account"], "by": role, "state": "approved"})
        return "approved"

    def repay_claim(s, m, cid, provider_confirmed=False):
        c = s.claims[cid]
        if c["state"] != "approved":
            raise ValueError(f"claim is {c['state']}")
        if not provider_confirmed:
            raise PermissionError("a repayment counts only after the provider confirms it")
        c["state"] = "repaid"
        s._emit(m, "expense_claim.repaid", {"claim_id": cid, "amount_minor": c["total"], "state": "repaid"})
        return "repaid"

    # ---- assets --------------------------------------------------------------------------------------------------------------
    def add_asset(s, m, cost_minor, years, method="straight_line", residual_minor=0, rate_bp=0):
        s._need(m, "assets", "assets")
        allowed = (s._pack(m).get("office") or {}).get("depreciation_methods")
        if allowed and method not in allowed:
            raise ValueError("this country does not allow that method")
        schedule = B.depreciation(cost_minor, residual_minor, years, method, rate_bp)
        if not schedule:
            raise ValueError("an asset needs years and a value left below its cost")
        aid = s.p.ids.assign("AST", uuid.uuid4().hex)
        s.assets.put(aid, {"merchant": m, "cost": cost_minor, "schedule": schedule, "posted": [], "state": "in_use"})
        s._emit(m, "asset.added", {"asset_id": aid, "cost_minor": cost_minor, "method": method, "years": years})
        return {"asset": aid, "schedule": schedule}

    def post_depreciation(s, m, aid, period):
        """Loss of value for the next year of the schedule; once per period."""
        a = s.assets[aid]
        if period in [p["period"] for p in a["posted"]]:
            return {"duplicate": True}
        n = len(a["posted"])
        if n >= len(a["schedule"]) or a["state"] != "in_use":
            raise ValueError("nothing left to lose")
        amt = a["schedule"][n]
        a["posted"] = a["posted"] + [{"period": period, "amount": amt}]
        s._emit(m, "depreciation.posted", {"asset_id": aid, "period": period, "amount_minor": amt})
        return {"amount": amt}

    def dispose_asset(s, m, aid, proceeds_minor, method, by, approver):
        a = s.assets[aid]
        so_far = sum(p["amount"] for p in a["posted"])
        lines = B.disposal(a["cost"], so_far, proceeds_minor, method)
        jid = s._post_journal(m, "disposal", lines, by, approver)
        a["state"] = "sold" if proceeds_minor else "written_off"
        return {"journal": jid, "lines": lines}

    # ---- journals, lock date, close ------------------------------------------------------------------------------------------
    def prepare_journal(s, m, kind, lines, by, date=None):
        """A journal waits for a second person when its kind is sensitive (manual, reversal, opening balances, write-off)."""
        if kind == "manual":
            s._need(m, "full_books", "manual journals")
        if not AC.checked_lines([list(l) for l in lines]):
            raise ValueError("a journal must balance and name real accounts")
        sensitive = SENSITIVE.get(kind)
        if not sensitive:
            return {"journal": s._post_journal(m, kind, lines, by, date=date), "state": "posted"}
        pid = uuid.uuid4().hex
        s.pending.put(pid, {"merchant": m, "kind": kind, "lines": [list(l) for l in lines], "by": by, "date": date})
        return {"pending": pid, "state": "awaiting_approval"}

    def approve_journal(s, m, pid, approver):
        j = s.pending[pid]
        if not B.two_person(SENSITIVE[j["kind"]], j["by"], approver)["ok"]:
            raise PermissionError("a sensitive entry is approved by someone other than the person who prepared it")
        jid = s._post_journal(m, j["kind"], j["lines"], j["by"], approver, j["date"])
        s.pending.pop(pid)
        return jid

    def set_lock_date(s, m, date, preparer, approver):
        s._need(m, "period_close", "the period lock")
        if not B.two_person("lock_date_change", preparer, approver)["ok"]:
            raise PermissionError("moving the lock date needs two people")
        s.settings.put(f"{m}|lock", {"date": date})
        s._emit(m, "lock_date.set", {"lock_date": date})
        return date

    def close_year(s, m, done, preparer, approver, date):
        s._need(m, "period_close", "the year-end close")
        missing = B.close_missing(done)
        if missing:
            return {"closed": False, "missing": missing}
        if not B.two_person("lock_date_change", preparer, approver)["ok"]:
            raise PermissionError("the close needs two people")
        tb = AC.trial_balance(s.p.accountant.journal(m))
        lines = B.year_end_lines(tb)
        jid = s._post_journal(m, "year_end", lines, preparer, approver, date) if lines else None
        s.settings.put(f"{m}|lock", {"date": date})
        s._emit(m, "lock_date.set", {"lock_date": date})
        return {"closed": True, "journal": jid}

    def revalue(s, m, items, num, den, by):
        s._need(m, "revaluation", "period-end revaluation")
        r = B.revalue(items, num, den)
        return {**r, "journal": s._post_journal(m, "revaluation", r["lines"], by) if r["lines"] else None}

    # ---- banks and statements ------------------------------------------------------------------------------------------------
    def import_statement(s, m, lines):
        """Statement lines from a file (live bank connections come through the bank partner, provider ledger)."""
        s.bank.put(m, {"lines": list(lines)})
        return len(lines)

    def match_bank(s, m, book_items, days=None):
        return B.bank_match((s.bank.get(m) or {"lines": []})["lines"], book_items, days)

    def statements(s, m):
        entries = s.p.accountant.journal(m)
        tb = AC.trial_balance(entries)
        return {"statements": B.statements(tb), "cash_flow": B.cash_flow(entries), "balanced": AC.balanced(entries)}
