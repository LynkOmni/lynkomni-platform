"""LynkExchange in the office services (EXCHANGE UPDATE, master blueprint 65.9; section 4 step E4b), on core/exchange.py and the
events of contract version 15. LynkOmni never holds money: every order goes through the licensed partner (services/exchange_partners.py),
which alone confirms money received, settled or refunded. Nothing about an exchange is queued offline.

- A quote is one full price for a short countdown: the partner's rate after LynkOmni's part (the lower of the plan's part and the
  level reached by the last 30 days' volume), shown beside the mid-market rate. Where no partner is signed the answer is
  "Coming to your country soon."; Practice mode works everywhere with the practice partner and never moves money or posts to the books.
- Two people approve an order above the owner's amount on the plans that allow it; the person who placed it never approves it.
- LynkAcc: money sent to the partner sits in the payments clearing account (1010) until the order settles. Foreign money is held at
  what it cost in the book currency (average cost); a rate gain (4400) or loss (6700) is booked only when foreign money comes back into
  the book currency; money sent to someone with no bill is spending (6000). A refund puts the cost back.
- LynkInv: an invoice paid from abroad is recorded as paid when the partner settles it in the invoice's currency.
- LynkAcc bills: a bill paid abroad is recorded as paid when the partner settles it.
- LynkCRM: payees are records of the kind "payee"; their name and bank details stay in the PII vault.
- LynkStat: the Exchange report (volume per pair, LynkOmni's part paid, gains and losses, orders by state).
- Proof of exchange: a certificate kept in LynkFiles with a code anyone can check.
"""
import time

from contract.tools.validate_contract import uuid7
from core import exchange as X
from services import billing as BL
from services.exchange_partners import SandboxExchangePartner
from services.improvements import Table

KINDS = ("convert", "send", "invoice_in", "bill_out")


class ExchangeOffice:
    def __init__(s, p, now=time.time, partner=None):
        s.p, s.now, db = p, now, p.c.store.db
        s.partner = partner or SandboxExchangePartner()
        s.quotes, s.orders, s.held, s.payees, s.settings = (Table(db, n) for n in ("ex_quotes", "ex_orders", "ex_held", "ex_payees", "ex_settings"))
        p.c.store.observers.append(s._observe)

    # ---- helpers -----------------------------------------------------------------------------------------------------------------
    def _emit(s, m, type_, payload):
        s.p.c.store.append(m, "server", type_, payload)

    def _book(s, m):
        return s.p.c.profile(m).get("currency") or "USD"

    def _tier_bps(s, m):
        return s.p.billing.entitlement(m, "lynkexchange")["lynkomni_part_bps"]

    def volume_30d(s, m):
        """USD cents settled in the last 30 days, from orders paid in or into USD (other pairs count once the partner reports their USD value)."""
        since = s.now() - 30 * 86400
        return sum(o.get("usd", 0) for _, o in s.orders.items() if o["merchant"] == m and o.get("settled_at", 0) >= since)

    def _post(s, m, lines):
        lines = [l for l in lines if l[1] or l[2]]
        if lines:
            s.p.books._post_journal(m, "exchange", lines, "lynkexchange")

    def _holding(s, m, cur):
        return s.held.get(f"{m}|{cur}") or s.held.put(f"{m}|{cur}", {"amount": 0, "cost": 0}) or s.held.get(f"{m}|{cur}")

    # ---- quotes and orders -------------------------------------------------------------------------------------------------------
    def quote(s, m, from_currency, to_currency, amount, kind="convert", practice=False, for_id=None):
        if kind not in KINDS:
            raise ValueError("unknown kind of order")
        if not practice:
            from providers import availability
            a = availability("exchange", s.p.c.profile(m)["country"])
            if a["state"] != "available":
                return {"state": "coming_soon", "message": a["message"], "notify_me": a["notify_me"]}
        q = s.partner.quote(from_currency, to_currency, amount)
        if not q.get("ok"):
            return {"state": "no_price", "reason": q.get("reason")}
        part = X.part_bps(s._tier_bps(m), BL.EXCHANGE_LEVELS, s.volume_30d(m))
        price = X.quote(amount, q["rate"][0], q["rate"][1], part)
        qid = uuid7()
        s.quotes.put(qid, {"merchant": m, "kind": kind, "from": from_currency, "to": to_currency, "amount": amount, "rate": q["rate"], "part_bps": part,
                           **price, "until": s.now() + q["seconds"], "practice": bool(practice or q.get("practice")), "for_id": for_id})
        return {"state": "quoted", "quote_id": qid, "amount": amount, "currency": from_currency, "to_amount": price["to_amount"], "to_currency": to_currency,
                "part": price["part"], "part_bps": part, "seconds": q["seconds"], "above_mid_bps": X.above_mid_bps(amount, price["to_amount"], *q["mid"]),
                "practice": bool(practice or q.get("practice"))}

    def set_approval(s, m, over_minor):
        """The owner's amount above which a second person approves (plans with more than one person)."""
        if (s.p.billing.entitlement(m, "lynkexchange").get("people") or 2) < 2:
            raise PermissionError("two people approving needs a plan with more than one person")
        s.settings.put(m, {"over": over_minor})

    def place(s, m, quote_id, by, payee=None, approver=None):
        q = s.quotes.get(quote_id)
        if not q or q["merchant"] != m:
            raise KeyError("no such quote")
        if s.now() > q["until"]:
            raise ValueError("price_expired: ask for a new price")
        rule = s.settings.get(m)
        if rule and q["amount"] > rule["over"] and (approver is None or approver == by):
            raise PermissionError("a second person approves this amount; never the person who placed it")
        payee_ref = None
        if payee is not None:
            pe = s.payees.get(f"{m}|{payee}")
            if not pe:
                raise KeyError("no such payee")
            payee_ref = pe["bank_ref"]
        oid = uuid7()
        public = s.p.ids.assign("TXN", oid)
        s.orders.put(oid, {"merchant": m, "public_id": public, "kind": q["kind"], "from": q["from"], "to": q["to"], "amount": q["amount"], "to_amount_quoted": q["to_amount"],
                           "part": q["part"], "rate": q["rate"], "practice": q["practice"], "for_id": q["for_id"], "state": "placed", "by": by})
        ev = {"order_id": oid, "kind": q["kind"], "amount": q["amount"], "currency": q["from"], "to_currency": q["to"], "part_bps": q["part_bps"], "practice": q["practice"]}
        if q["for_id"]:
            ev["for_id"] = q["for_id"]
        s._emit(m, "ExchangeOrderPlaced", ev)
        s.partner.place(oid, q, "vault:" + s.p.vault.put(oid, "payer", by), payee_ref)
        s.quotes.pop(quote_id)
        return {"order_id": oid, "public_id": public, "state": "placed"}

    # ---- the partner's answers (cloud only) ------------------------------------------------------------------------------------------
    def _order(s, oid):
        o = s.orders.get(oid)
        if not o:
            raise KeyError("no such order")
        return o

    # A partner may send the same answer twice: a repeat changes nothing (never a second payment, posting or event).
    def partner_paid(s, oid, ref):
        o = s._order(oid)
        if o["state"] != "placed":
            return o["state"]
        if o["practice"]:
            o["state"] = "paid"; return o["state"]
        s._emit(o["merchant"], "ExchangeOrderPaid", {"order_id": oid, "provider_reference": ref})
        return s._order(oid)["state"]

    def partner_settled(s, oid, to_amount, ref):
        o = s._order(oid)
        if o["state"] in ("settled", "failed", "refunded"):
            return o["state"]
        if o["practice"]:
            o.update({"state": "settled", "to_amount": to_amount}); return o["state"]
        s._emit(o["merchant"], "ExchangeSettled", {"order_id": oid, "amount": o["amount"], "currency": o["from"], "to_amount": to_amount,
                                                   "to_currency": o["to"], "provider_reference": ref})
        return s._order(oid)["state"]

    def partner_failed(s, oid, reason):
        o = s._order(oid)
        if o["state"] in ("settled", "failed", "refunded"):
            return
        o["state"] = "failed"
        if not o["practice"]:
            s._emit(o["merchant"], "ExchangeOrderFailed", {"order_id": oid, "reason": reason})

    def partner_refunded(s, oid, amount, ref):
        o = s._order(oid)
        if o["state"] in ("settled", "refunded"):
            return
        if o["practice"]:
            o["state"] = "refunded"; return
        s._emit(o["merchant"], "ExchangeRefunded", {"order_id": oid, "amount": amount, "currency": o["from"], "provider_reference": ref})

    # ---- the books, invoices and bills (from the events) ----------------------------------------------------------------------------
    def _observe(s, m, type_, payload, at):
        if type_ not in ("ExchangeOrderPaid", "ExchangeSettled", "ExchangeRefunded"):
            return
        o = s.orders.get(payload["order_id"])
        if not o:
            return
        B = s._book(m)
        if type_ == "ExchangeOrderPaid":
            o["state"] = "paid"
            if o["kind"] in ("invoice_in", "bill_out"):
                return                                      # posted by the invoice or the bill when it settles
            if o["from"] == B:
                cost = o["amount"]
            else:
                h = s._holding(m, o["from"])
                cost = X.cost_out(h["amount"], h["cost"], o["amount"]) if h["amount"] >= o["amount"] else o["amount"]
                if h["amount"] >= o["amount"]:
                    h.update({"amount": h["amount"] - o["amount"], "cost": h["cost"] - cost})
            o["cost"] = cost
            s._post(m, [("1010", cost, 0), ("1020", 0, cost)])
        elif type_ == "ExchangeSettled":
            o.update({"state": "settled", "to_amount": payload["to_amount"], "settled_at": s.now(), "ref": payload["provider_reference"],
                      "usd": o["amount"] if o["from"] == "USD" else (payload["to_amount"] if o["to"] == "USD" else 0)})
            if o["kind"] == "invoice_in":
                s.p.invoicing.record_payment(m, o["for_id"], "exchange", payload["to_amount"], provider_confirmed=True, payment_ref=payload["provider_reference"])
                return
            if o["kind"] == "bill_out":
                s.p.books.pay_bill(m, o["for_id"], o["amount"], method="exchange", provider_confirmed=True, ref=payload["provider_reference"])
                return
            cost = o.get("cost", o["amount"])
            if o["kind"] == "send":
                s._post(m, [("6000", cost, 0), ("1010", 0, cost)])
            elif o["to"] == B:
                gain = payload["to_amount"] - cost
                s._post(m, [("1020", payload["to_amount"], 0), ("1010", 0, cost), ("4400", 0, max(gain, 0)), ("6700", max(-gain, 0), 0)])
                o["gain"] = gain
            else:
                h = s._holding(m, o["to"])
                h.update({"amount": h["amount"] + payload["to_amount"], "cost": h["cost"] + cost})
                s._post(m, [("1020", cost, 0), ("1010", 0, cost)])
        elif type_ == "ExchangeRefunded":
            o["state"] = "refunded"
            cost = o.get("cost")
            if cost:
                s._post(m, [("1020", cost, 0), ("1010", 0, cost)])
                if o["from"] != B:
                    h = s._holding(m, o["from"])
                    h.update({"amount": h["amount"] + o["amount"], "cost": h["cost"] + cost})

    # ---- invoices and bills abroad -------------------------------------------------------------------------------------------------
    def invoice_from_abroad(s, m, iid, payer_currency):
        """A customer abroad pays a LynkInv invoice in their own money: the price for what is still owed, in the invoice's currency."""
        owed = s.p.invoicing.outstanding(iid)
        cur = s.p.invoicing.inv[iid]["currency"]
        q = s.partner.quote(cur, payer_currency, owed)
        if not q.get("ok"):
            return {"state": "no_price", "reason": q.get("reason")}
        need = -(-owed * q["rate"][0] // q["rate"][1])            # what the payer sends, rounded up
        return s.quote(m, payer_currency, cur, need, kind="invoice_in", for_id=iid)

    def bill_abroad(s, m, bid, to_currency):
        """Pay an approved LynkAcc bill to a supplier abroad: the price for what is left to pay, in the book currency."""
        b = s.p.books.bills[bid]
        return s.quote(m, s._book(m), to_currency, b["total"] - b["paid"], kind="bill_out", for_id=bid)

    # ---- payees ------------------------------------------------------------------------------------------------------------------
    def add_payee(s, m, by, name, bank_details, entity_kind="business"):
        rid = s.p.crm.create(m, by, "payee", entity_kind=entity_kind, name=name)
        s.payees.put(f"{m}|{rid}", {"bank_ref": "vault:" + s.p.vault.put(rid, "bank", bank_details)})
        return rid

    # ---- the Exchange report for LynkStat ------------------------------------------------------------------------------------------
    def report(s, m, since=0):
        mine = [o for _, o in s.orders.items() if o["merchant"] == m and not o["practice"]]
        pairs, states = {}, {}
        for o in mine:
            states[o["state"]] = states.get(o["state"], 0) + 1
            if o["state"] == "settled":
                k = f"{o['from']}-{o['to']}"
                p = pairs.setdefault(k, {"orders": 0, "amount": 0, "to_amount": 0, "part": 0})
                p.update({"orders": p["orders"] + 1, "amount": p["amount"] + o["amount"], "to_amount": p["to_amount"] + o["to_amount"], "part": p["part"] + o["part"]})
        gains = sum(o.get("gain", 0) for o in mine if o.get("gain", 0) > 0)
        losses = -sum(o.get("gain", 0) for o in mine if o.get("gain", 0) < 0)
        return {"pairs": pairs, "states": states, "gains": gains, "losses": losses, "book_currency": s._book(m)}

    # ---- proof of exchange ---------------------------------------------------------------------------------------------------------
    def proof(s, m, oid):
        o = s._order(oid)
        if o["merchant"] != m or o["state"] != "settled" or o["practice"]:
            raise ValueError("a proof is issued only for a settled order")
        if o.get("proof"):
            return o["proof"]
        text = (f"Proof of exchange {o['public_id']}\nPaid: {o['amount']} {o['from']} (minor units)\nReceived: {o['to_amount']} {o['to']} (minor units)\n"
                f"Rate: {o['rate'][0]}/{o['rate'][1]}\nLynkOmni's part: {o['part']} {o['from']} (minor units)\nPartner reference: {o['ref']}\n"
                f"Settled: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(o['settled_at']))}\n")
        did = s.p.files.store(m, "lynkexchange", "other", oid, "certificate", text.encode())
        code = s.p.files.issue_certificate(m, did, "lynkexchange")
        import hashlib
        s._emit(m, "ExchangeProofIssued", {"order_id": oid, "document_id": did, "code_sha256": hashlib.sha256(code.encode()).hexdigest()})
        o["proof"] = {"document_id": did, "code": code}
        return o["proof"]
