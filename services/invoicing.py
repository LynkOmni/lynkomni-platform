"""LynkInv, the invoicing service (standalone since 2026-11-07, also inside LynkOps and LynkSuite). Public ids are LOINV- (and LOQUO- for quotes) from core/ids.py; payments go through LynkCheckout pay links.

Rules: an issued invoice never changes (fix with a credit note); an electronic payment is 'paid' only when the provider confirms it; the printed
number is a sequential number in the merchant's own series, separate from the random public id; reserved numbers that go unused are voided with a
reason; nothing is called a tax invoice unless the country's workflow is confirmed in writing (default: never).
Providers are sandbox; legal invoice content and retention need a local adviser per country."""
import time, uuid
from core import books, invoices
from core.regions import country
from services.einvoice import SandboxEInvoiceNetwork, next_state
from services.improvements import Table, _cur

REMINDER_CHANNELS = ("in_app", "chat", "sms", "email")

class Invoicing:
    def __init__(s, p, now=time.time):
        s.p, s.now, db = p, now, p.c.store.db
        s.inv, s.series, s.blocks, s.notes, s.sched = Table(db, "inv"), Table(db, "inv_series"), Table(db, "inv_blocks"), Table(db, "inv_credit"), Table(db, "inv_recurring")
        s.held, s.docs, s.settings, s.credit, s.subs = Table(db, "inv_held"), Table(db, "inv_docs"), Table(db, "inv_settings"), Table(db, "inv_creditbal"), Table(db, "inv_subs")
        s.network = SandboxEInvoiceNetwork()      # services/einvoice.py; the real connector replaces it per country when signed
    # ---- plan
    def ent(s, m): return s.p.billing.entitlement(m, "lynkinv")
    def used(s, m, month): return sum(1 for _, v in s.inv.items() if v["merchant"] == m and v["month"] == month)
    def _quota(s, m, month):
        lim = s.ent(m).get("invoices_per_month")
        if lim is not None and s.used(m, month) >= lim: raise PermissionError("invoice limit for this plan reached this month; upgrade LynkInv")
    def _series_ok(s, m, name):
        lim, have = s.ent(m).get("invoice_series"), {k.split("|")[1] for k, _ in s.series.items() if k.startswith(m + "|")}
        if name not in have and lim is not None and len(have) >= lim: raise PermissionError("series limit for this plan reached; upgrade LynkInv")
    # ---- numbers
    def _next(s, m, name):
        k = f"{m}|{name}"; r = s.series.get(k) or {"next": 1}; n = r["next"]; s.series.put(k, {"next": n + 1}); return n
    def lease_block(s, m, device, name="A", size=40):
        """A device reserves a block of numbers to use offline. Unused numbers are voided later, never silently dropped."""
        s._series_ok(m, name); first = None
        for _ in range(size):
            n = s._next(m, name); first = first or n
        s.blocks.put(f"{m}|{name}|{device}|{first}", {"first": first, "last": first + size - 1, "used": [], "voided": {}})
        return {"series": name, "first": first, "last": first + size - 1}
    def release_block(s, m, device, name, first, reason="unused"):
        k = f"{m}|{name}|{device}|{first}"; b = s.blocks[k]
        for n in range(b["first"], b["last"] + 1):
            if n not in b["used"] and str(n) not in b["voided"]: b["voided"][str(n)] = reason
        s.blocks.put(k, dict(b)); return b["voided"]
    def _block_for(s, m, device, name, number):
        for k, b in s.blocks.items():
            if k.startswith(f"{m}|{name}|{device}|") and b["first"] <= number <= b["last"]: return k, b
        return None, None
    # ---- amounts
    def totals(s, m, lines, taxes=None):
        """Integer totals through LynkInv's rules (core/invoices.py): the country's sales tax read exactly as basis points, or
        the invoice's own taxes (several on a line, tax held back, the reverse charge)."""
        rate = books.rate_bp(country(s.p.c.profile(m)["country"])["tax_rate"])
        doc = taxes if taxes is not None else ([{"kind": "sales", "rate_bp": rate}] if rate else [])
        t = invoices.totals([{"qty": ln["qty_milli"], "unit_minor": ln["unit_minor"], "discount_minor": ln.get("discount_minor", 0), **({"taxes": ln["taxes"]} if "taxes" in ln else {})}
                             for ln in lines], doc)
        tax = sum(v for k, v in t["taxes"].items() if k in books.ADDED_TAXES)
        return {"net_minor": t["net"], "tax_minor": tax, "total_minor": t["total"], "withheld_minor": t["withheld"], "to_pay_minor": t["to_pay"]}
    def label(s, m):
        """Only 'Invoice'. The word 'tax invoice' needs the country's workflow confirmed in writing, which no pack states yet."""
        confirmed = country(s.p.c.profile(m)["country"]).get("flags", {}).get("tax_invoice_confirmed", False)
        return "Tax invoice" if confirmed else "Invoice (not a tax invoice)"
    # ---- issue
    def issue(s, m, customer, lines, series="A", due_days=14, device=None, number=None, month=None, accepted=True, taxes=None, preparer=None,
              currency_rate=None):
        """Online: the cloud numbers the invoice. Offline: the device passes a number from its leased block and the cloud accepts it later.
        An invoice over the owner's approval amount (Pro and up) waits for approval before it is numbered and sent; once issued it
        posts to the books as owed by the customer (OFFICE UPDATE, journal kind invoice)."""
        month = month or time.strftime("%Y-%m", time.gmtime(s.now())); s._quota(m, month); s._series_ok(m, series)
        if not lines: raise ValueError("an invoice needs at least one line")
        if preparer is not None and s.ent(m).get("approval_before_sending"):
            rule = s.settings.get(f"{m}|approval") or {}
            if invoices.needs_approval(s.totals(m, lines, taxes)["total_minor"], rule.get("over_minor"), preparer, rule.get("named", [])):
                hid = uuid.uuid4().hex
                s.held.put(hid, {"merchant": m, "customer": customer, "lines": lines, "series": series, "due_days": due_days, "taxes": taxes, "preparer": preparer, "month": month})
                return {"held": hid, "state": "awaiting_approval"}
        if device is not None and number is not None:
            k, b = s._block_for(m, device, series, number)
            if b is None or number in b["used"] or str(number) in b["voided"]: raise ValueError("number is not available in this device's block")
            b["used"].append(number); s.blocks.put(k, dict(b))
        else: number = s._next(m, series)
        tot, iid = s.totals(m, lines, taxes), s.p.ids.assign("INV", uuid.uuid4().hex)
        rec = {"merchant": m, "customer": customer, "series": series, "number": number, "currency": _cur(s.p, m), "lines": lines, **tot, "state": "issued", "month": month,
               "issued_at": s.now(), "due_at": s.now() + due_days * 86400, "paid_minor": 0, "payments": [], "credited_minor": 0, "label": s.label(m), "sent_state": "accepted" if accepted else "sent"}
        s.inv.put(iid, rec); s.p.c.store.append(m, "server", "invoice.issued", {"invoice": iid, "total_minor": tot["total_minor"], "currency": rec["currency"], "number": number, "series": series})
        s._journal(m, s._issue_lines(tot), preparer or "staff")
        s._e_invoice(m, iid)
        return {"id": iid, "number": number, **tot, "label": rec["label"]}
    def approve(s, m, hid, approver):
        """Approval before sending: the preparer never approves their own invoice."""
        h = s.held[hid]
        if not books.may_approve(h["preparer"], approver): raise PermissionError("the person who prepared an invoice never approves it")
        s.held.pop(hid)
        return s.issue(m, h["customer"], h["lines"], h["series"], h["due_days"], month=h["month"], taxes=h["taxes"])
    # ---- books (the journal is the event log's projection; services/accounting.py checks and posts it)
    @staticmethod
    def _issue_lines(tot):
        lines = [["1100", tot["to_pay_minor"], 0]] if tot["to_pay_minor"] else []
        if tot["withheld_minor"]: lines.append(["1410", tot["withheld_minor"], 0])
        lines.append(["4000", 0, tot["net_minor"]])
        if tot["tax_minor"]: lines.append(["2100", 0, tot["tax_minor"]])
        return lines
    @staticmethod
    def _money_in(method):
        """Cash lands in the till; anything electronic sits in the payments clearing account until the provider's payout,
        as card and mobile-money sales already do (chart 1010)."""
        return "1000" if method == "cash" else "1010"
    def _journal(s, m, lines, by, kind="invoice"):
        return s.p.books._post_journal(m, kind, lines, by)
    def accept_offline(s, m, device, customer, lines, series, number, month=None):
        """Cloud side of an offline invoice: same rules, number must come from the device's own block."""
        r = s.issue(m, customer, lines, series, device=device, number=number, month=month); return r
    def pay_link(s, m, iid):
        v = s.inv[iid]
        if v["sent_state"] != "accepted": raise PermissionError("the pay link exists only after the cloud accepts the invoice")
        if v["state"] in ("paid", "void", "credited"): raise ValueError(f"invoice is {v['state']}")
        return s.p.paylinks.create(m, v["total_minor"] - v["paid_minor"] - v["credited_minor"], iid)
    def mark_viewed(s, iid):
        v = s.inv[iid]
        if v["state"] == "issued": v["state"] = "viewed"
    # ---- payment
    def outstanding(s, iid): v = s.inv[iid]; return v.get("to_pay_minor", v["total_minor"]) - v["paid_minor"] - v["credited_minor"]
    def record_payment(s, m, iid, method, amount_minor, provider_confirmed=False, payment_ref=None):
        v = s.inv[iid]
        if v["state"] in ("void", "credited", "paid"): raise ValueError(f"invoice is {v['state']}")
        if method != "cash" and not provider_confirmed: raise PermissionError("an electronic payment counts only after the provider confirms it")
        if amount_minor <= 0 or amount_minor > s.outstanding(iid): raise ValueError("amount must be positive and not above what is owed")
        if amount_minor < s.outstanding(iid) and not s.ent(m).get("partial_payments"): raise PermissionError("partial payments need a higher LynkInv plan")
        if payment_ref and any(p.get("ref") == payment_ref for p in v["payments"]): return {"state": v["state"], "duplicate": True}   # a retry never counts twice
        v["payments"] = v["payments"] + [{"method": method, "amount_minor": amount_minor, "ref": payment_ref}]; v["paid_minor"] += amount_minor
        v["state"] = "paid" if s.outstanding(iid) == 0 else "partially_paid"
        s.p.c.store.append(m, "server", "invoice.payment", {"invoice": iid, "amount_minor": amount_minor, "method": method, "state": v["state"]})
        s._journal(m, [[s._money_in(method), amount_minor, 0], ["1100", 0, amount_minor]], "staff")
        return {"state": v["state"], "outstanding_minor": s.outstanding(iid)}
    def state(s, iid):
        v = s.inv[iid]
        if v["state"] in ("issued", "viewed", "partially_paid") and s.now() > v["due_at"]: return "overdue"
        return v["state"]
    # ---- corrections
    def credit_note(s, m, iid, amount_minor, reason):
        if not s.ent(m).get("credit_notes"): raise PermissionError("credit notes need a higher LynkInv plan")
        v = s.inv[iid]
        if not reason: raise ValueError("a credit note needs a reason")
        if amount_minor <= 0 or amount_minor > s.outstanding(iid): raise ValueError("a credit note cannot exceed what is still owed")
        cid = uuid.uuid4().hex; s.notes.put(cid, {"invoice": iid, "amount_minor": amount_minor, "reason": reason}); v["credited_minor"] += amount_minor
        if s.outstanding(iid) == 0: v["state"] = "credited" if v["paid_minor"] == 0 else "paid"
        s.p.c.store.append(m, "server", "invoice.credited", {"invoice": iid, "amount_minor": amount_minor, "reason": reason})
        net, tax = (books.allocate(amount_minor, [v["net_minor"], v["tax_minor"]]) if v["tax_minor"] else [amount_minor, 0])
        s._journal(m, [l for l in (["4000", net, 0], ["2100", tax, 0], ["1100", 0, amount_minor]) if l[1] or l[2]], "staff")
        return {"credit": cid, "outstanding_minor": s.outstanding(iid)}
    def void_unpaid(s, m, iid, reason):
        v = s.inv[iid]
        if v["paid_minor"] or not reason: raise ValueError("only an unpaid invoice can be voided, with a reason")
        v["state"] = "void"; v["void_reason"] = reason
        s._journal(m, books.reverse(s._issue_lines({k: v.get(k, 0) for k in ("to_pay_minor", "withheld_minor", "net_minor", "tax_minor")})), "staff")
    def edit(s, iid, **changes): raise PermissionError("an issued invoice never changes; issue a credit note and a new invoice")
    # ---- reminders (consent first)
    def remind(s, m, iid, channel, consented_channels, automatic=False):
        if automatic and not s.ent(m).get("auto_reminders"): raise PermissionError("automatic reminders need a higher LynkInv plan")
        if channel not in REMINDER_CHANNELS: raise ValueError("unknown channel")
        if channel != "in_app" and channel not in consented_channels: raise PermissionError("the customer has not agreed to this channel")
        s.p.c.store.append(m, "server", "invoice.reminder", {"invoice": iid, "channel": channel, "automatic": automatic}); return True
    # ---- recurring
    def schedule(s, m, customer, lines, every_days, start):
        if not s.ent(m).get("recurring_invoices"): raise PermissionError("recurring invoices need a higher LynkInv plan")
        sid = uuid.uuid4().hex; s.sched.put(sid, {"merchant": m, "customer": customer, "lines": lines, "every_days": every_days, "next": start, "runs": []}); return sid
    def run_due(s, today):
        out = []
        for sid, r in s.sched.items():
            while r["next"] <= today:
                period = r["next"]
                if period not in r["runs"]:   # one invoice per period, even if run twice
                    r["runs"] = r["runs"] + [period]; out.append(s.issue(r["merchant"], r["customer"], r["lines"]))
                r["next"] = period + r["every_days"]
        return out
    # ---- OFFICE UPDATE 66.3 (section 4 step D2b): documents, getting paid on time, ways to bill, e-invoices --------------------
    def document(s, m, kind, from_id=None, total_minor=None):
        """Another document (quote, pro-forma, sales order, delivery note, receipt, debit note, statement of account, buyer-issued
        invoice where the law allows): its public id from core/ids.py; it never changes; only invoices and notes post."""
        pack = country(s.p.c.profile(m)["country"])
        if not invoices.may_make(s.docs[from_id]["kind"] if from_id in s.docs else ("invoice" if from_id in s.inv else None), kind, pack):
            raise PermissionError("that document cannot be made from this one here")
        feat = {"pro_forma": "pro_forma", "receipt": "receipts", "delivery_note": "delivery_notes", "sales_order": "sales_orders",
                "debit_note": "debit_notes", "statement": "statements_of_account"}.get(kind)
        if feat and not s.ent(m).get(feat): raise PermissionError("that document needs a higher LynkInv plan")
        did = s.p.ids.assign(invoices.INV["documents"][kind]["id"], uuid.uuid4().hex)
        s.docs.put(did, {"merchant": m, "kind": kind, "from": from_id, "total_minor": total_minor, "issued_at": s.now()})
        s.p.c.store.append(m, "server", "document.issued", {"document": did, "kind": kind, "from": from_id, "total_minor": total_minor, "currency": _cur(s.p, m)})
        return did
    def remind_due(s, m, today, consented):
        """Today's stepped reminders: once per step, paused by a promise or a dispute, only on a channel the customer agreed to."""
        if not s.ent(m).get("stepped_reminders"): return []
        out = []
        for iid, v in s.inv.items():
            if v["merchant"] != m or v["state"] in ("paid", "void", "credited", "written_off") or s.outstanding(iid) <= 0: continue
            due = time.strftime("%Y-%m-%d", time.gmtime(v["due_at"]))
            disputed = v.get("disputed_minor", 0) >= s.outstanding(iid)
            step = invoices.reminder_due(due, today, v.get("reminders", []), v.get("promise"), disputed)
            channel = next((c for c in consented.get(v["customer"], []) if c in REMINDER_CHANNELS), "in_app")
            if step:
                v["reminders"] = v.get("reminders", []) + [step]
                s.p.c.store.append(m, "server", "invoice.reminder", {"invoice": iid, "channel": channel, "automatic": True, "step": step})
                out.append({"invoice": iid, "step": step, "channel": channel})
        return out
    def promise(s, m, iid, date):
        v = s.inv[iid]; v["promise"] = date
        s.p.c.store.append(m, "server", "invoice.promise", {"invoice": iid, "promise_on": date}); return date
    def dispute(s, m, iid, amount_minor, reason, line=None):
        if not s.ent(m).get("disputes"): raise PermissionError("disputes need LynkInv Pro")
        v = s.inv[iid]
        if amount_minor <= 0 or amount_minor > s.outstanding(iid): raise ValueError("a dispute is within what is owed")
        v["disputed_minor"] = v.get("disputed_minor", 0) + amount_minor
        s.p.c.store.append(m, "server", "invoice.disputed", {"invoice": iid, "amount_minor": amount_minor, "reason": reason, "line": line})
        return v["disputed_minor"]
    def resolve_dispute(s, m, iid):
        s.inv[iid]["disputed_minor"] = 0; return 0
    def write_off(s, m, iid, preparer, approver):
        """An amount nobody will pay goes to bad debts: prepared by one person, approved by another."""
        if not s.ent(m).get("write_offs"): raise PermissionError("write-offs need LynkInv Pro")
        if not books.two_person("write_off", preparer, approver)["ok"]: raise PermissionError("a write-off is approved by a second person")
        v = s.inv[iid]; amt = s.outstanding(iid)
        if amt <= 0: raise ValueError("nothing left to write off")
        v["credited_minor"] += amt; v["state"] = "written_off"
        s.p.c.store.append(m, "server", "bad_debt.written_off", {"invoice": iid, "amount_minor": amt})
        return amt
    def pay_several(s, m, customer, amount_minor, method, provider_confirmed=False, order=None):
        """One payment across a customer's invoices, oldest first; what is left becomes their credit balance (never income)."""
        if method != "cash" and not provider_confirmed: raise PermissionError("an electronic payment counts only after the provider confirms it")
        open_ = [{"id": k, "outstanding": s.outstanding(k), "due": time.strftime("%Y-%m-%d", time.gmtime(v["due_at"]))}
                 for k, v in s.inv.items() if v["merchant"] == m and v["customer"] == customer and v["state"] not in ("void", "credited", "written_off")]
        r = invoices.apply_payment(amount_minor, open_, order)
        for u in r["used"]:
            v = s.inv[u["id"]]
            v["payments"] = v["payments"] + [{"method": method, "amount_minor": u["amount"]}]; v["paid_minor"] += u["amount"]
            v["state"] = "paid" if s.outstanding(u["id"]) == 0 else "partially_paid"
            s.p.c.store.append(m, "server", "invoice.payment", {"invoice": u["id"], "amount_minor": u["amount"], "method": method, "state": v["state"]})
        cash = s._money_in(method)
        used = sum(u["amount"] for u in r["used"])
        lines = ([[cash, amount_minor, 0]] + ([["1100", 0, used]] if used else []) + ([["2510", 0, r["credit_balance"]]] if r["credit_balance"] else []))
        s._journal(m, lines, "staff")
        if r["credit_balance"]: s._credit(m, customer, r["credit_balance"], "overpayment")
        return r
    def _credit(s, m, customer, change, reason, iid=None):
        k = f"{m}|{customer}"; bal = (s.credit.get(k) or {"amount": 0})["amount"] + change
        s.credit.put(k, {"amount": bal})
        s.p.c.store.append(m, "server", "credit_balance.changed", {"customer": customer, "change_minor": change, "amount_minor": bal, "reason": reason, "invoice": iid})
        return bal
    def credit_balance(s, m, customer): return (s.credit.get(f"{m}|{customer}") or {"amount": 0})["amount"]
    def apply_credit(s, m, customer, iid):
        amt = min(s.credit_balance(m, customer), s.outstanding(iid))
        if amt <= 0: return 0
        v = s.inv[iid]; v["paid_minor"] += amt; v["state"] = "paid" if s.outstanding(iid) == 0 else "partially_paid"
        s._journal(m, [["2510", amt, 0], ["1100", 0, amt]], "staff"); s._credit(m, customer, -amt, "applied", iid)
        return amt
    def instalment_plan(s, m, iid, count, start, every="month"):
        if not s.ent(m).get("instalment_plans"): raise PermissionError("instalment plans need LynkInv Pro")
        parts = invoices.instalments(s.outstanding(iid), count, start, every)
        if not parts: raise ValueError("between 1 and the most instalments allowed")
        s.inv[iid]["instalments"] = parts
        s.p.c.store.append(m, "server", "instalment_plan.agreed", {"invoice": iid, "count": count, "first_on": start, "every": every})
        return parts
    def subscribe(s, m, customer, price_minor, period_days=30):
        if not s.ent(m).get("subscriptions"): raise PermissionError("subscriptions need LynkInv Pro")
        sid = s.p.ids.assign("SUB", uuid.uuid4().hex)
        s.subs.put(sid, {"merchant": m, "customer": customer, "price": price_minor, "period_days": period_days, "state": "active"})
        s.p.c.store.append(m, "server", "subscription.changed", {"subscription": sid, "change": "start"}); return sid
    def change_subscription(s, m, sid, change, new_price=None, days_left=0):
        """Upgrade or downgrade for the whole days left (charged or credited); pause, resume, cancel."""
        sub = s.subs[sid]; amount = None
        if change in ("upgrade", "downgrade"):
            amount = invoices.prorate(sub["price"], new_price, sub["period_days"], days_left); sub["price"] = new_price
        elif change == "pause" and sub["state"] == "active": sub["state"] = "paused"
        elif change == "resume" and sub["state"] == "paused": sub["state"] = "active"
        elif change == "cancel": sub["state"] = "cancelled"
        else: raise ValueError(f"cannot {change} a {sub['state']} subscription")
        s.p.c.store.append(m, "server", "subscription.changed", {"subscription": sid, "change": change, "amount_minor": amount})
        return {"state": sub["state"], "amount": amount}
    def usage_line(s, m, qty_thousandths, bands, mode="graduated"):
        """A line for billing by use from a meter (Max)."""
        if not s.ent(m).get("usage_billing"): raise PermissionError("billing by use needs LynkInv Max")
        return {"qty_milli": 1000, "unit_minor": invoices.usage(qty_thousandths, bands, mode)}
    def _e_invoice(s, m, iid):
        """Where the country requires e-invoices (pack office.e_invoice.required), hand the invoice to the network once the
        partner is signed; until then it waits as queued, said plainly. Only the network moves it on."""
        pack = country(s.p.c.profile(m)["country"])
        if invoices.e_invoice_required(pack) is not True: return None
        import providers
        v = s.inv[iid]; v["e_invoice"] = "queued"
        item = next(i for i in providers.items() if i["id"] == "e_invoice_network")
        if providers.item_status(item, pack["code"]) not in providers.OK_STATUS: return "queued"     # partner not signed yet: waits
        return s.send_e_invoice(m, iid)
    def send_e_invoice(s, m, iid):
        v = s.inv[iid]
        lines = [{"total": v["total_minor"]}]                 # the network checks the document adds up; the full format comes with the real connector
        ans = s.network.submit({"lines": lines, "total_minor": v["total_minor"]})
        return s._e_state(m, iid, ans)
    def poll_e_invoice(s, m, iid):
        v = s.inv[iid]
        if not v.get("e_ref"): return v.get("e_invoice")
        return s._e_state(m, iid, s.network.poll(v["e_ref"]))
    def _e_state(s, m, iid, ans):
        v = s.inv[iid]
        if ans.get("ref"): v["e_ref"] = ans["ref"]
        new = next_state(v.get("e_invoice", "queued"), ans)
        if new != v.get("e_invoice"):
            v["e_invoice"] = new
            s.p.c.store.append(m, "server", "e_invoice.state", {"invoice": iid, "state": new, "reason": ans.get("reason")})
        return new
