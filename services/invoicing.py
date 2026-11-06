"""Invoicing inside LynkCheckout (approved proposal). Not a separate product, family or id prefix: public ids are LOINV- from core/ids.py.

Rules: an issued invoice never changes (fix with a credit note); an electronic payment is 'paid' only when the provider confirms it; the printed
number is a sequential number in the merchant's own series, separate from the random public id; reserved numbers that go unused are voided with a
reason; nothing is called a tax invoice unless the country's workflow is confirmed in writing (default: never).
Providers are sandbox; legal invoice content and retention need a local adviser per country."""
import time, uuid
from decimal import Decimal as D, ROUND_HALF_UP
from core.regions import country
from services.improvements import Table, _cur

REMINDER_CHANNELS = ("in_app", "chat", "sms", "whatsapp", "email")

class Invoicing:
    def __init__(s, p, now=time.time):
        s.p, s.now, db = p, now, p.c.store.db
        s.inv, s.series, s.blocks, s.notes, s.sched = Table(db, "inv"), Table(db, "inv_series"), Table(db, "inv_blocks"), Table(db, "inv_credit"), Table(db, "inv_recurring")
    # ---- plan
    def ent(s, m): return s.p.billing.entitlement(m, "lynkcheckout")
    def used(s, m, month): return sum(1 for _, v in s.inv.items() if v["merchant"] == m and v["month"] == month)
    def _quota(s, m, month):
        lim = s.ent(m).get("invoices_per_month")
        if lim is not None and s.used(m, month) >= lim: raise PermissionError("invoice limit for this plan reached this month; upgrade LynkCheckout")
    def _series_ok(s, m, name):
        lim, have = s.ent(m).get("invoice_series"), {k.split("|")[1] for k, _ in s.series.items() if k.startswith(m + "|")}
        if name not in have and lim is not None and len(have) >= lim: raise PermissionError("series limit for this plan reached; upgrade LynkCheckout")
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
    def totals(s, m, lines):
        rate = D(str(country(s.p.c.profile(m)["country"])["tax_rate"])); net = tax = 0
        for ln in lines:
            n = (D(ln["qty_milli"]) * D(ln["unit_minor"]) / 1000).quantize(D(1), ROUND_HALF_UP) - ln.get("discount_minor", 0)
            net += int(n); tax += int((D(n) * rate).quantize(D(1), ROUND_HALF_UP))
        return {"net_minor": net, "tax_minor": tax, "total_minor": net + tax}
    def label(s, m):
        """Only 'Invoice'. The word 'tax invoice' needs the country's workflow confirmed in writing, which no pack states yet."""
        confirmed = country(s.p.c.profile(m)["country"]).get("flags", {}).get("tax_invoice_confirmed", False)
        return "Tax invoice" if confirmed else "Invoice (not a tax invoice)"
    # ---- issue
    def issue(s, m, customer, lines, series="A", due_days=14, device=None, number=None, month=None, accepted=True):
        """Online: the cloud numbers the invoice. Offline: the device passes a number from its leased block and the cloud accepts it later."""
        month = month or time.strftime("%Y-%m", time.gmtime(s.now())); s._quota(m, month); s._series_ok(m, series)
        if not lines: raise ValueError("an invoice needs at least one line")
        if device is not None and number is not None:
            k, b = s._block_for(m, device, series, number)
            if b is None or number in b["used"] or str(number) in b["voided"]: raise ValueError("number is not available in this device's block")
            b["used"].append(number); s.blocks.put(k, dict(b))
        else: number = s._next(m, series)
        tot, iid = s.totals(m, lines), s.p.ids.assign("INV", uuid.uuid4().hex)
        rec = {"merchant": m, "customer": customer, "series": series, "number": number, "currency": _cur(s.p, m), "lines": lines, **tot, "state": "issued", "month": month,
               "issued_at": s.now(), "due_at": s.now() + due_days * 86400, "paid_minor": 0, "payments": [], "credited_minor": 0, "label": s.label(m), "sent_state": "accepted" if accepted else "sent"}
        s.inv.put(iid, rec); s.p.c.store.append(m, "server", "invoice.issued", {"invoice": iid, "total_minor": tot["total_minor"], "currency": rec["currency"], "number": number, "series": series})
        return {"id": iid, "number": number, **tot, "label": rec["label"]}
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
    def outstanding(s, iid): v = s.inv[iid]; return v["total_minor"] - v["paid_minor"] - v["credited_minor"]
    def record_payment(s, m, iid, method, amount_minor, provider_confirmed=False, payment_ref=None):
        v = s.inv[iid]
        if v["state"] in ("void", "credited", "paid"): raise ValueError(f"invoice is {v['state']}")
        if method != "cash" and not provider_confirmed: raise PermissionError("an electronic payment counts only after the provider confirms it")
        if amount_minor <= 0 or amount_minor > s.outstanding(iid): raise ValueError("amount must be positive and not above what is owed")
        if amount_minor < s.outstanding(iid) and not s.ent(m).get("partial_payments"): raise PermissionError("partial payments need a higher LynkCheckout plan")
        if payment_ref and any(p.get("ref") == payment_ref for p in v["payments"]): return {"state": v["state"], "duplicate": True}   # a retry never counts twice
        v["payments"] = v["payments"] + [{"method": method, "amount_minor": amount_minor, "ref": payment_ref}]; v["paid_minor"] += amount_minor
        v["state"] = "paid" if s.outstanding(iid) == 0 else "partially_paid"
        s.p.c.store.append(m, "server", "invoice.payment", {"invoice": iid, "amount_minor": amount_minor, "method": method, "state": v["state"]})
        return {"state": v["state"], "outstanding_minor": s.outstanding(iid)}
    def state(s, iid):
        v = s.inv[iid]
        if v["state"] in ("issued", "viewed", "partially_paid") and s.now() > v["due_at"]: return "overdue"
        return v["state"]
    # ---- corrections
    def credit_note(s, m, iid, amount_minor, reason):
        if not s.ent(m).get("credit_notes"): raise PermissionError("credit notes need a higher LynkCheckout plan")
        v = s.inv[iid]
        if not reason: raise ValueError("a credit note needs a reason")
        if amount_minor <= 0 or amount_minor > s.outstanding(iid): raise ValueError("a credit note cannot exceed what is still owed")
        cid = uuid.uuid4().hex; s.notes.put(cid, {"invoice": iid, "amount_minor": amount_minor, "reason": reason}); v["credited_minor"] += amount_minor
        if s.outstanding(iid) == 0: v["state"] = "credited" if v["paid_minor"] == 0 else "paid"
        s.p.c.store.append(m, "server", "invoice.credited", {"invoice": iid, "amount_minor": amount_minor, "reason": reason})
        return {"credit": cid, "outstanding_minor": s.outstanding(iid)}
    def void_unpaid(s, m, iid, reason):
        v = s.inv[iid]
        if v["paid_minor"] or not reason: raise ValueError("only an unpaid invoice can be voided, with a reason")
        v["state"] = "void"; v["void_reason"] = reason
    def edit(s, iid, **changes): raise PermissionError("an issued invoice never changes; issue a credit note and a new invoice")
    # ---- reminders (consent first)
    def remind(s, m, iid, channel, consented_channels, automatic=False):
        if automatic and not s.ent(m).get("auto_reminders"): raise PermissionError("automatic reminders need a higher LynkCheckout plan")
        if channel not in REMINDER_CHANNELS: raise ValueError("unknown channel")
        if channel != "in_app" and channel not in consented_channels: raise PermissionError("the customer has not agreed to this channel")
        s.p.c.store.append(m, "server", "invoice.reminder", {"invoice": iid, "channel": channel, "automatic": automatic}); return True
    # ---- recurring
    def schedule(s, m, customer, lines, every_days, start):
        if not s.ent(m).get("recurring_invoices"): raise PermissionError("recurring invoices need a higher LynkCheckout plan")
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
