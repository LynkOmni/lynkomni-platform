"""Service 10 (Chat) and the section 7 additions: Credit, ShopQR, Receipts, Staff, Assistant."""
import hashlib, hmac, time, uuid
from core.locale import in_quiet_hours
from core.money import fmt
from services.suite import PayLinks

KINDS = {"text", "voice", "image", "document", "product_card", "quote", "pay_link", "receipt", "debt_reminder", "marketing"}
def _id(): return uuid.uuid4().hex
def _now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
def _sig(body): return hmac.new(PayLinks.SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()[:24]

class Deferred(Exception):
    """Message held back (for example quiet hours). Try again later."""

class Chat:  # 10
    MAX_PER_MIN = 30
    def __init__(s, c, paylinks, rights, ids=None): s.c, s.pl, s.rights, s.recent, s.ids = c, paylinks, rights, {}, ids   # business conversations only: no personal or group chat
    def blocked(s, m): return {e["payload"]["who"] for e in s.c.store.of(m, "chat.blocked")}
    def block(s, m, who): s.c.store.append(m, "server", "chat.blocked", {"who": who})
    def report(s, m, who, reason): s.c.store.append(m, "server", "chat.reported", {"who": who, "reason": reason})
    def _check(s, m, sender):
        s.c.gate(m, "chat")
        if sender in s.blocked(m):
            raise PermissionError("sender is blocked")
        now = time.time()
        q = [t for t in s.recent.get((m, sender), []) if now - t < 60]
        if len(q) >= s.MAX_PER_MIN:
            raise PermissionError("rate limit reached")
        s.recent[(m, sender)] = q + [now]
    def open_thread(s, m, customer, ref_type=None, ref_id=None, device="server"):
        s.c.gate(m, "chat")
        tid = _id()
        s.c.store.append(m, device, "chat.thread.opened", {"thread_id": tid, "customer": customer, "ref_type": ref_type, "ref_id": ref_id, "public_id": s.ids.assign("CNV", tid) if s.ids else None, "route": "business"})
        return tid
    def send(s, m, device, thread_id, sender, kind, body="", quiet_country=None, **extra):
        if kind not in KINDS:
            raise ValueError(f"unknown message kind {kind}")
        if kind == "marketing" and not s.rights.has_consent(m, f"marketing:{extra.get('customer')}"):
            raise PermissionError("no marketing consent from this customer")
        if kind in ("marketing", "debt_reminder") and quiet_country and in_quiet_hours(_now(), quiet_country):
            raise Deferred("quiet hours for the customer")
        s._check(m, sender)
        mid = _id()
        s.c.store.append(m, device, "chat.message", {"thread_id": thread_id, "msg_id": mid, "from": sender, "kind": kind, "body": body, **extra}, mid)
        return mid
    def state(s, m, msg_id):
        """queued (still only on the device), sent, delivered, read. Only what is verifiable."""
        st = None
        for e in s.c.store.of(m, "chat.message", "chat.delivered", "chat.read"):
            p = e["payload"]
            if e["type"] == "chat.message" and p["msg_id"] == msg_id:
                st = "sent"
            elif p.get("msg_id") == msg_id and st:
                st = "read" if e["type"] == "chat.read" else ("delivered" if st == "sent" else st)
        return st or "queued"
    def mark_delivered(s, m, msg_id, via): s.c.store.append(m, "server", "chat.delivered", {"msg_id": msg_id, "via": via})
    def mark_read(s, m, device, msg_id, reader):
        msg = next(e["payload"] for e in s.c.store.of(m, "chat.message") if e["payload"]["msg_id"] == msg_id)
        if msg["from"] == reader:
            raise PermissionError("you cannot mark your own message as read")
        s.c.store.append(m, device, "chat.read", {"msg_id": msg_id, "reader": reader})
    # chat-to-commerce: quote -> draft order -> payment link -> confirmed only by a settled payment
    def quote(s, m, device, thread_id, sender, items):
        total, qid = sum(i["qty"] * i["price_minor"] for i in items), _id()
        s.send(m, device, thread_id, sender, "quote", quote_id=qid, public_quote_id=(s.ids.assign("QUO", qid) if s.ids else None), items=items, total_minor=total, currency=s.c.profile(m)["currency"])
        return qid
    def accept_quote(s, m, thread_id, customer, quote_id):
        q = next(e["payload"] for e in s.c.store.of(m, "chat.message") if e["payload"].get("quote_id") == quote_id)
        oid = _id()
        s.c.store.append(m, "server", "order.drafted", {"order_id": oid, "thread_id": thread_id, "customer": customer, "quote_id": quote_id,
                         "items": q["items"], "total_minor": q["total_minor"], "currency": q["currency"]})
        return oid
    def pay_link(s, m, device, thread_id, sender, order_id):
        o = next(e["payload"] for e in s.c.store.of(m, "order.drafted") if e["payload"]["order_id"] == order_id)
        link = s.pl.create(m, o["total_minor"], order_id)
        s.send(m, device, thread_id, sender, "pay_link", url=link["url"], order_id=order_id)
        return link
    def confirm_order(s, m, order_id):
        o = next((e["payload"] for e in s.c.store.of(m, "order.drafted") if e["payload"]["order_id"] == order_id), None)
        if o is None:
            raise KeyError("unknown order")
        paid = any(e["payload"]["ref"].endswith("-" + order_id) and e["payload"]["amount_minor"] >= o["total_minor"]
                   for e in s.c.store.of(m, "payment.settled"))
        if not paid:
            raise PermissionError("order is not paid: a chat message cannot confirm it")
        s.c.store.append(m, "server", "order.confirmed", {"order_id": order_id})
        return True
    # merchant team inbox
    def assign(s, m, thread_id, staff): s.c.store.append(m, "server", "chat.assigned", {"thread_id": thread_id, "staff": staff})
    def save_reply(s, m, key, text): s.c.store.append(m, "server", "chat.reply_saved", {"key": key, "text": text})
    def saved_reply(s, m, key):
        r = [e["payload"]["text"] for e in s.c.store.of(m, "chat.reply_saved") if e["payload"]["key"] == key]
        return r[-1] if r else None
    def inbox(s, m, staff=None):
        th = {e["payload"]["thread_id"]: {"thread_id": e["payload"]["thread_id"], "customer": e["payload"]["customer"],
              "assigned_to": None, "unread": 0, "last": None} for e in s.c.store.of(m, "chat.thread.opened")}
        for e in s.c.store.of(m, "chat.assigned"):
            th[e["payload"]["thread_id"]]["assigned_to"] = e["payload"]["staff"]
        read = {e["payload"]["msg_id"] for e in s.c.store.of(m, "chat.read")}
        for e in s.c.store.of(m, "chat.message"):
            p = e["payload"]
            if p["thread_id"] in th:
                th[p["thread_id"]]["last"] = p["kind"]
                if p["from"].startswith("cust:") and p["msg_id"] not in read:
                    th[p["thread_id"]]["unread"] += 1
        return [x for x in th.values() if staff is None or x["assigned_to"] == staff]

class Credit:  # customer credit and collections
    def __init__(s, c): s.c = c
    def sell(s, m, device, customer, amount_minor, due, limit_minor=None):
        if limit_minor is not None and s.balance(m, customer) + amount_minor > limit_minor:
            return {"ok": False, "reason": "credit limit"}
        s.c.store.append(m, device, "credit.sale", {"customer": customer, "amount_minor": amount_minor, "due": due, "currency": s.c.profile(m)["currency"]})
        return {"ok": True}
    def pay(s, m, device, customer, amount_minor):
        s.c.store.append(m, device, "credit.payment", {"customer": customer, "amount_minor": amount_minor})
    def balances(s, m):
        b = {}
        for e in s.c.store.of(m, "credit.sale", "credit.payment"):
            p = e["payload"]
            b[p["customer"]] = b.get(p["customer"], 0) + (p["amount_minor"] if e["type"] == "credit.sale" else -p["amount_minor"])
        return {k: v for k, v in b.items() if v > 0}
    def balance(s, m, customer): return s.balances(m).get(customer, 0)
    def overdue(s, m, now):
        sales, paid = {}, {}
        for e in s.c.store.of(m, "credit.sale", "credit.payment"):
            p = e["payload"]
            if e["type"] == "credit.sale":
                sales.setdefault(p["customer"], []).append([p["due"], p["amount_minor"]])
            else:
                paid[p["customer"]] = paid.get(p["customer"], 0) + p["amount_minor"]
        out = {}
        for cust, lst in sales.items():
            left = paid.get(cust, 0)
            for due, amt in sorted(lst):  # payments settle the oldest debts first
                used = min(left, amt); left -= used
                if amt - used > 0 and due < now:
                    out[cust] = out.get(cust, 0) + amt - used
        return out
    def remind(s, m, device, chat, customer, now, quiet_country=None):
        owed = s.overdue(m, now).get(customer)
        if not owed:
            return None
        tid = next((e["payload"]["thread_id"] for e in s.c.store.of(m, "chat.thread.opened") if e["payload"]["customer"] == customer), None) \
            or chat.open_thread(m, customer, "debt", customer)
        try:
            return chat.send(m, device, tid, "shop", "debt_reminder", quiet_country=quiet_country,
                             customer=customer, amount_minor=owed, currency=s.c.profile(m)["currency"])
        except Deferred:
            return None

class ShopQR:  # the shop's front door
    ACTIONS = ["chat", "pay", "loyalty", "catalog", "verify_receipt"]
    def __init__(s, c): s.c = c
    def payload(s, m): return {"qr_payload": f"lynk://shop?m={m}&s={_sig('shop|' + m)}", "actions": s.ACTIONS}
    def verify(s, qr):
        try:
            q = dict(kv.split("=", 1) for kv in qr.split("?", 1)[1].split("&"))
            return q["m"] if hmac.compare_digest(q["s"], _sig("shop|" + q["m"])) else None
        except Exception:
            return None

class Receipts:  # verified receipts. HMAC today: checked by LynkOmni online. See README for offline verification.
    def __init__(s, c): s.c = c
    def _body(s, m, sale_id):
        e = next(e for e in s.c.store.of(m, "sale.recorded") if e["id"] == sale_id)
        return f"{m}|{sale_id}|{e['payload']['total_minor']}|{e['payload']['currency']}|{e['ts']}"
    def issue(s, m, sale_id):
        sig = _sig(s._body(m, sale_id))
        s.c.store.append(m, "server", "receipt.issued", {"sale_id": sale_id, "sig": sig})
        return {"receipt_id": sale_id, "sig": sig, "qr_payload": f"lynk://receipt?m={m}&r={sale_id}&s={sig}", "fiscal": False}
    def verify(s, m, sale_id, sig):
        try:
            return hmac.compare_digest(sig, _sig(s._body(m, sale_id)))
        except StopIteration:
            return False

PERMS = {"owner": {"*"}, "manager": {"sell", "void", "stock", "expense", "view_profit", "shift"}, "cashier": {"sell", "shift"}}

class Staff:  # roles, voids, shifts and cash control, audit trail
    DISCREPANCY_ALERT_MINOR = 0
    def __init__(s, c): s.c = c
    def can(s, role, action): return "*" in PERMS.get(role, set()) or action in PERMS.get(role, set())
    def audit(s, m, device, staff, action, detail=None):
        s.c.store.append(m, device, "audit.logged", {"staff": staff, "action": action, "detail": detail})
    def void_sale(s, m, device, staff, role, sale_id, reason):
        if not s.can(role, "void"):
            raise PermissionError(f"{role} cannot void sales")
        if any(e["payload"]["sale_id"] == sale_id for e in s.c.store.of(m, "sale.voided")):
            raise ValueError("sale already voided")
        sale = next(e["payload"] for e in s.c.store.of(m, "sale.recorded") if e["id"] == sale_id)
        s.c.store.append(m, device, "sale.voided", {"sale_id": sale_id, "items": sale["items"], "total_minor": sale["total_minor"],
                         "currency": sale["currency"], "method": sale["method"], "staff": staff, "reason": reason})
        s.audit(m, device, staff, "void_sale", sale_id)
    def open_shift(s, m, device, staff, float_minor):
        sid = _id()
        s.c.store.append(m, device, "shift.opened", {"shift_id": sid, "staff": staff, "float_minor": float_minor})
        return sid
    def close_shift(s, m, device, shift_id, counted_minor):
        opened = next(e for e in s.c.store.of(m, "shift.opened") if e["payload"]["shift_id"] == shift_id)
        expected = opened["payload"]["float_minor"]
        for e in s.c.store.of(m, "sale.recorded", "sale.voided"):
            if e["seq"] > opened["seq"] and e["payload"]["method"] == "cash":
                expected += e["payload"]["total_minor"] * (1 if e["type"] == "sale.recorded" else -1)
        diff = counted_minor - expected
        s.c.store.append(m, device, "shift.closed", {"shift_id": shift_id, "counted_minor": counted_minor, "expected_minor": expected, "difference_minor": diff})
        return {"expected_minor": expected, "difference_minor": diff, "alert": abs(diff) > s.DISCREPANCY_ALERT_MINOR}

class Assistant:  # answers from the merchant's own numbers. Rules today; an AI provider can plug in with consent.
    def __init__(s, c, acct, inv, credit, rights, ai=None): s.c, s.acct, s.inv, s.credit, s.rights, s.ai = c, acct, inv, credit, rights, ai
    def ask(s, m, question, online=True):
        q, a = question.lower(), s.acct.summary(m)
        cur = a["currency"]
        if any(k in q for k in ("earn", "profit", "made")):
            return {"answer": f"Profit so far: {fmt(a['profit_minor'], cur)} on sales of {fmt(a['revenue_minor'], cur)}.", "figures": a, "source": "accountant"}
        if any(k in q for k in ("owe", "debt")):
            b = s.credit.balances(m)
            return {"answer": f"{len(b)} customers owe you {fmt(sum(b.values()), cur)}.", "figures": b, "source": "credit ledger"}
        if any(k in q for k in ("stock", "reorder", "low")):
            lo = s.inv.low(m)
            return {"answer": f"{len(lo)} items are low: {', '.join(sorted(lo)) or 'none'}.", "figures": lo, "source": "inventory"}
        if s.ai and online and s.rights.has_consent(m, "ai_assistant"):
            return {"answer": s.ai.answer(question, a), "figures": a, "source": "ai"}
        return {"answer": "I can answer questions about profit, debts and stock.", "figures": {}, "source": "rules"}
    def propose(s, m, action, params):
        pid = _id()
        s.c.store.append(m, "server", "assistant.proposed", {"proposal_id": pid, "action": action, "params": params})
        return {"proposal_id": pid, "status": "needs_confirmation", "action": action, "params": params}
    def confirm(s, m, proposal_id):
        p = next((e["payload"] for e in s.c.store.of(m, "assistant.proposed") if e["payload"]["proposal_id"] == proposal_id), None)
        if p is None or any(e["payload"]["proposal_id"] == proposal_id for e in s.c.store.of(m, "assistant.confirmed")):
            raise ValueError("unknown or already confirmed proposal")
        s.c.store.append(m, "server", "assistant.confirmed", {"proposal_id": proposal_id})
        return p  # the caller performs the action; the assistant never acts on its own
