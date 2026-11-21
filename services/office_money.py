"""The office side of gift cards, store credit, deposits, matching and payment costs in LynkAcc (SERVICES UPDATE 67.2 and 67.8;
section 4 step F, row 67.17), on core/office_money.py and the events of contract version 16. It reads events (never another service's
storage) and posts each money fact once through LynkAcc's checked journals (Books._post_journal):

- Gift cards and store credit are a debt of the shop: a gift card sold is owed to its holder (2200), store credit to the customer
  (2510); spending either is a sale (4000). A balance spent below nothing (sales made offline are never blocked) is flagged for the
  owner with StoredValueConflictFlagged; nothing is posted twice.
- A deposit is received in advance (2500) until it is used (4000), kept under terms shown before (4200) or returned (cash 1000; an
  electronic return only on the provider's confirmation, DepositRefunded).
- The matching centre lists every provider payment matched to its sale, invoice or booking: by reference at once, a single candidate
  by amount within the window as a suggestion a person confirms (or the Plus automation settlement-match accepts, undoable), and
  everything else unmatched. A payment matched to an invoice is recorded on it as provider confirmed.
- Payment costs come only from the provider's settlement report: the provider's fee and LynkOmni's part (6100 from 1010).
- The payout calendar: expected and arrived only from the provider (1020 from 1010 on arrival); late after two days, never "lost".
"""
import time

from core import office_money as O
from services.improvements import Table

_DAY = "%Y-%m-%d"


class OfficeMoney:
    def __init__(s, p, now=time.time):
        s.p, s.now = p, now
        s.sv = Table(p.c.store.db, "office_stored_value")        # merchant|voucher -> {"kind", "moves": [...], "flagged": bool}
        s.dep = Table(p.c.store.db, "office_deposits")            # merchant|deposit -> {"taken", "settled": [...], "for"}
        s.pay = Table(p.c.store.db, "office_settlements")         # merchant|reference -> settlement line, match
        s.out = Table(p.c.store.db, "office_payouts")             # merchant|payout -> payout
        p.c.store.observers.append(s._observe)

    # ---- helpers -------------------------------------------------------------------------------------------------------------------
    def _today(s):
        return time.strftime(_DAY, time.gmtime(s.now()))

    def _post(s, m, kind, lines):
        lines = [l for l in lines if l[1] or l[2]]
        if lines:
            s.p.books._post_journal(m, kind, lines, "lynkacc")

    def _emit(s, m, type_, payload):
        s.p.c.store.append(m, "server", type_, payload)

    def _ent(s, m):
        return s.p.billing.entitlement(m, "lynkacc")

    @staticmethod
    def _in(method):
        return "1000" if method == "cash" else "1010"

    def _rows(s, table, m):
        return [(k.split("|", 1)[1], r) for k, r in table.items() if k.startswith(m + "|")]

    # ---- the books -----------------------------------------------------------------------------------------------------------------
    def _observe(s, m, type_, p, at):
        R = O.MONEY
        if type_ == "GiftCardSold":
            s._move(m, p["card_id"], "gift_card", "issue", p["amount"])
            s._post(m, "gift_card", [(s._in(p["method"]), p["amount"], 0), (R["stored_value"]["kinds"]["gift_card"]["account"], 0, p["amount"])])
        elif type_ == "StoreCreditIssued":
            s._move(m, p["credit_id"], "store_credit", "issue", p["amount"])
            s._post(m, "store_credit", [(R["stored_value"]["issue_debit"][p["reason"]], p["amount"], 0), (R["stored_value"]["kinds"]["store_credit"]["account"], 0, p["amount"])])
        elif type_ == "VoucherRedeemed":
            kind = (s.sv.get(f"{m}|{p['voucher_id']}") or {}).get("kind", "gift_card")     # a voucher from before version 16 is a gift card
            s._move(m, p["voucher_id"], kind, "spend", p["amount"])
            s._post(m, "stored_value", [(R["stored_value"]["kinds"][kind]["account"], p["amount"], 0), (R["stored_value"]["spend_credit"], 0, p["amount"])])
        elif type_ == "DepositTaken":
            s.dep.put(f"{m}|{p['deposit_id']}", {"for": p["for"], "taken": p["amount"], "settled": [], "currency": p["currency"]})
            s._post(m, "deposit", [(s._in(p["method"]), p["amount"], 0), (R["deposits"]["account"], 0, p["amount"])])
        elif type_ in ("DepositSettled", "DepositRefunded"):
            d = s.dep.get(f"{m}|{p['deposit_id']}")
            if not d:
                return
            left = d["taken"] - sum(d["settled"])
            part = min(p["amount"], left)                      # never more than is still held; a device checks the same before writing
            if type_ == "DepositSettled":
                s._post(m, "deposit", [(R["deposits"]["account"], part, 0), (R["deposits"]["outcomes"][p["outcome"]]["credit"], 0, part)])
            else:
                s._post(m, "deposit", [(R["deposits"]["account"], part, 0), ("6400", p["amount"] - part, 0), ("1010", 0, p["amount"])])
            if part:
                s.dep.put(f"{m}|{p['deposit_id']}", {**d, "settled": d["settled"] + [part]})
        elif type_ == "PaymentSettled":
            done = {e["payload"].get("ref") for e in s.p.c.store.of(m, "payment.settled")}
            cost = p["provider_fee"] + p["lynkomni_part"]
            if p["provider_reference"] not in done:            # a payment the cloud charged itself already posted its fee
                s._post(m, "payment_costs", [("6100", cost, 0), ("1010", 0, cost)])
        elif type_ == "ProviderPayoutArrived":
            s._post(m, "payout", [(R["payouts"]["arrived_debit"], p["amount"], 0), (R["payouts"]["arrived_credit"], 0, p["amount"])])

    def _move(s, m, vid, kind, what, amount):
        key = f"{m}|{vid}"
        r = s.sv.get(key) or {"kind": kind, "moves": [], "flagged": False}
        moves = r["moves"] + [{"id": vid, "kind": what, "amount": amount}]
        held = O.balances(moves)["held"][vid]
        flag = held < 0 and not r["flagged"]
        s.sv.put(key, {**r, "moves": moves, "flagged": r["flagged"] or flag})
        if flag:
            s._emit(m, "StoredValueConflictFlagged", {"voucher_id": vid, "held": held, "currency": s.p.c.profile(m)["currency"]})

    # ---- gift cards, store credit and deposits ------------------------------------------------------------------------------------
    def balance(s, m, vid):
        r = s.sv.get(f"{m}|{vid}")
        return O.balances(r["moves"])["held"][vid] if r else 0

    def stored_value(s, m):
        """Every gift card and store credit with what it still holds, and the ones spent below nothing."""
        rows = [{"id": vid, "kind": r["kind"], "held": O.balances(r["moves"])["held"][vid]} for vid, r in s._rows(s.sv, m)]
        return {"cards": sorted(rows, key=lambda x: x["id"]), "owed": {k: sum(x["held"] for x in rows if x["kind"] == k) for k in ("gift_card", "store_credit")},
                "conflicts": [x["id"] for x in rows if x["held"] < 0]}

    def deposits(s, m):
        return sorted(({"id": did, "for": d["for"], "taken": d["taken"], "left": O.deposit_left(d["taken"], d["settled"])} for did, d in s._rows(s.dep, m)),
                      key=lambda x: x["id"])

    def deposit_refunded(s, m, deposit_id, amount, provider_reference):
        """Cloud only, on the provider's confirmation: a deposit returned electronically. A repeated answer changes nothing."""
        if any(e["payload"]["provider_reference"] == provider_reference for e in s.p.c.store.of(m, "DepositRefunded")):
            return False
        s._emit(m, "DepositRefunded", {"deposit_id": deposit_id, "amount": amount, "currency": s.p.c.profile(m)["currency"], "provider_reference": provider_reference})
        return True

    # ---- the provider's report: costs and payouts ----------------------------------------------------------------------------------
    def provider_report(s, m, lines):
        """Cloud only: the provider's settlement report. Each line once (by its reference); whole minor units only."""
        new = 0
        for l in lines:
            O.costs([{"ref": l["provider_reference"], "on": l["settled_on"], "currency": l["currency"], "amount": l["amount"],
                      "provider_fee": l["provider_fee"], "lynkomni_part": l["lynkomni_part"]}])          # refuses fractions and impossible costs
            key = f"{m}|{l['provider_reference']}"
            if s.pay.get(key):
                continue
            s.pay.put(key, {**l, "match": None})
            s._emit(m, "PaymentSettled", {k: v for k, v in l.items() if k in ("provider_reference", "amount", "currency", "provider_fee", "lynkomni_part", "settled_on", "payout_id")})
            new += 1
        return new

    def payout_scheduled(s, m, payout_id, expected_on, amount, currency):
        if s.out.get(f"{m}|{payout_id}"):
            return False
        s.out.put(f"{m}|{payout_id}", {"expected_on": expected_on, "amount": amount, "currency": currency, "arrived": None})
        s._emit(m, "ProviderPayoutScheduled", {"payout_id": payout_id, "expected_on": expected_on, "amount": amount, "currency": currency})
        return True

    def payout_arrived(s, m, payout_id, provider_reference):
        r = s.out.get(f"{m}|{payout_id}")
        if not r or r["arrived"]:
            return False                                           # a repeated answer changes nothing
        s.out.put(f"{m}|{payout_id}", {**r, "arrived": s._today()})
        s._emit(m, "ProviderPayoutArrived", {"payout_id": payout_id, "amount": r["amount"], "currency": r["currency"], "provider_reference": provider_reference})
        return True

    def costs(s, m):
        lines = [{"ref": ref, "on": l["settled_on"], "currency": l["currency"], "amount": l["amount"], "provider_fee": l["provider_fee"],
                  "lynkomni_part": l["lynkomni_part"]} for ref, l in sorted(s._rows(s.pay, m), key=lambda x: (x[1]["settled_on"], x[0]))]
        return O.costs(lines)

    def payout_calendar(s, m, today=None):
        rows = s._rows(s.out, m)
        return O.payouts([{"id": pid, "expected_on": r["expected_on"], "amount": r["amount"], "currency": r["currency"]} for pid, r in rows],
                         {pid: r["arrived"] for pid, r in rows if r["arrived"]}, today or s._today())

    # ---- the matching centre -------------------------------------------------------------------------------------------------------
    def _targets(s, m):
        """Open sales (an electronic payment waiting for its provider), open invoices and bookings not yet paid, never matched twice."""
        taken = {(r["match"][0], r["match"][1]) for _, r in s._rows(s.pay, m) if r["match"]}
        day = lambda at: (at or s._today())[:10]
        out = []
        for e in s.p.c.store.of(m, "PaymentRecorded"):
            q = e["payload"]
            if q["status"] == "pending_confirmation":
                out.append({"kind": "sale", "id": q["sale_id"], "ref": q.get("provider_reference"), "amount": q["amount"], "currency": q["currency"], "on": day(e.get("ts"))})
        for iid, v in s.p.invoicing.inv.items():
            if v.get("merchant") == m and v["state"] in ("issued", "viewed", "partially_paid"):
                out.append({"kind": "invoice", "id": iid, "amount": s.p.invoicing.outstanding(iid), "currency": v["currency"],
                            "on": time.strftime(_DAY, time.gmtime(v["issued_at"]))})
        paid = {e["payload"]["booking_id"]: e["payload"].get("provider_reference") for e in s.p.c.store.of(m, "BookingPaid")}
        for e in s.p.c.store.of(m, "BookingConfirmed"):
            q = e["payload"]
            out.append({"kind": "booking", "id": q["booking_id"], "ref": paid.get(q["booking_id"]), "amount": q["total"], "currency": q["currency"], "on": q["starts_at"][:10]})
        return [t for t in out if (t["kind"], t["id"]) not in taken]

    def _record(s, m, ref, kind, tid, how):
        key = f"{m}|{ref}"
        r = s.pay.get(key)
        s.pay.put(key, {**r, "match": [kind, tid, how]})
        s._emit(m, "PaymentMatched", {"provider_reference": ref, "target": kind, "target_id": tid, "how": how})
        if kind == "invoice":                                      # the provider already confirmed this payment
            s.p.invoicing.record_payment(m, tid, "provider", r["amount"], provider_confirmed=True, payment_ref=ref)

    def matching_centre(s, m):
        """Matches what can be matched for certain (by reference), accepts single suggestions on Plus and up (undoable), and lists the rest."""
        open_p = [{"ref": ref, "amount": l["amount"], "currency": l["currency"], "on": l["settled_on"]} for ref, l in sorted(s._rows(s.pay, m)) if not l["match"]]
        res = O.match(open_p, s._targets(m))
        for ref, kind, tid in res["matched"]:
            s._record(m, ref, kind, tid, "reference")
        suggested = res["suggested"]
        if s._ent(m).get("auto_match"):
            person = lambda ref, kind: kind == "invoice" or s.pay.get(f"{m}|{ref}").get("undone")
            for ref, kind, tid in suggested:                      # an invoice payment, or one a person undid, waits for a person
                if not person(ref, kind):
                    s._record(m, ref, kind, tid, "automatic")
            suggested = [x for x in suggested if person(x[0], x[1])]
        matched = [[ref, *r["match"]] for ref, r in sorted(s._rows(s.pay, m)) if r["match"]]
        return {"matched": matched, "suggested": suggested, "unmatched": res["unmatched"]}

    def confirm(s, m, ref, kind, tid):
        """A person confirms a suggestion (or matches by hand on any tier)."""
        r = s.pay.get(f"{m}|{ref}")
        if not r or r["match"]:
            raise ValueError("no unmatched payment with that reference")
        if not any(t["kind"] == kind and t["id"] == tid for t in s._targets(m)):
            raise ValueError("that sale, invoice or booking is not open")
        s._record(m, ref, kind, tid, "confirmed")

    def undo(s, m, ref):
        """Undoes an automatic or confirmed match (a reference match is certain and stays); the payment is listed again."""
        r = s.pay.get(f"{m}|{ref}")
        if not r or not r["match"] or r["match"][2] == "reference":
            raise ValueError("only an automatic or confirmed match can be undone")
        if r["match"][0] == "invoice":
            raise ValueError("a payment recorded on an invoice is corrected with a credit note or a refund, never undone here")
        s.pay.put(f"{m}|{ref}", {**r, "match": None, "undone": True})
        s._emit(m, "PaymentMatchUndone", {"provider_reference": ref})
