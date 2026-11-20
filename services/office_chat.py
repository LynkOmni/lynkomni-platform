"""The office services in a customer conversation (CHAT UPDATE 74.5; section 4 step D4c), on the rules of core/chat.py and the
links of catalog/connections.v1.json (inv-chat, acc-chat, crm-chat, stat-chat).

Into the chat: LynkInv's invoice, quote and credit-note cards, LynkAcc's statement and reminder cards, and LynkStat's report card
with the chat figures. From the chat: make a quote or an invoice, note a payment promise, add a new customer, a note or a
follow-up. Every card comes from its own service and follows its rules, states and prices: a card only shows the service's
words, and its actions (Pay, Accept) open that service's own step; the chat never does them. Every conversation goes on the
customer's LynkCRM timeline and on the record it is about. The chats behind a figure open only for the roles allowed.

A card is sent by the cloud alone (chat.card_sent, ConversationCardSent in the contract); a message's words are never in an
event."""
import time, uuid

from core import chat as CH
from services.improvements import Table

OFFICE_CARDS = {k: v for k, v in CH.CARDS.items() if v["service"] in ("lynkinv", "lynkacc", "lynkstat")}
OPEN_CHATS_ROLES = ("owner", "manager")          # who may open the chats behind a figure (74.5: by role)


class OfficeChat:
    def __init__(s, p, now=time.time):
        s.p, s.now, db = p, now, p.c.store.db
        s.convs, s.follow, s.notes = Table(db, "oc_convs"), Table(db, "oc_follow"), Table(db, "oc_notes")

    # ---- conversations on the record they are about ----------------------------------------------------------------------------
    def open(s, m, customer=None, about=None, side="internal"):
        """A conversation with a customer, optionally about a record ('Chat about this'); it goes on the customer's timeline."""
        if about is not None and about[0] not in CH.CHAT["chat_about"]["records"]:
            raise ValueError("that record cannot be chatted about")
        cid = uuid.uuid4().hex
        s.convs.put(cid, {"merchant": m, "customer": customer, "about": list(about) if about else None, "side": side, "cards": [], "opened": s.now(),
                          "first_reply_min": None, "solved_min": None, "reopened": 0, "solved_by_assist": False})
        if customer:
            s.p.crm.add_activity(m, customer, "chats", s.now(), cid)
        if about:
            s.p.c.store.append(m, "server", "chat.about", {"conversation": cid, "kind": about[0], "record": about[1]})
        return cid

    # ---- cards into the chat -----------------------------------------------------------------------------------------------------
    def _body(s, m, kind, rec):
        """The card's facts, read from its own service; the words and states are the service's."""
        inv = s.p.invoicing
        if kind == "invoice":
            v = inv.inv[rec]
            if v["merchant"] != m:
                raise PermissionError("not this business's invoice")
            return {"number": v["number"], "label": v["label"], "currency": v["currency"], "total_minor": v["total_minor"],
                    "to_pay_minor": max(inv.outstanding(rec), 0), "state": inv.state(rec)}
        if kind == "credit_note":
            n = inv.notes.get(rec)
            if not n or inv.inv[n["invoice"]]["merchant"] != m:
                raise ValueError("no credit note with that id")
            return {"invoice_number": inv.inv[n["invoice"]]["number"], "amount_minor": n["amount_minor"], "reason": n["reason"]}
        if kind in ("quote", "statement"):
            d = inv.docs.get(rec)
            if not d or d["merchant"] != m or d["kind"] != kind:
                raise ValueError(f"no {kind} with that id")
            return {"kind": kind, "total_minor": d.get("total_minor"), "from": d.get("from")}
        if kind == "reminder":
            v = inv.inv[rec]
            return {"number": v["number"], "to_pay_minor": max(inv.outstanding(rec), 0), "promise": v.get("promise"), "step": (v.get("reminders") or [None])[-1]}
        if kind == "report":
            return s.chat_figures(m)
        raise ValueError("not an office card")

    def card(s, m, conv, kind, record, online=True):
        """Send a card into a conversation: only an office card, only from its own service, with only the actions its service
        lists that are offered right now (Pay and Accept are never offered offline)."""
        if kind not in OFFICE_CARDS:
            raise ValueError("not an office card")
        c = s.convs.get(conv)
        if not c or c["merchant"] != m:
            raise PermissionError("not this business's conversation")
        body = s._body(m, kind, record)
        actions = [a for a in OFFICE_CARDS[kind]["actions"] if CH.card_action(kind, a, online)]
        if kind == "invoice" and "pay" in actions and body["to_pay_minor"] <= 0:
            actions.remove("pay")                                     # nothing to pay: the Pay button is not shown
        c["cards"] = c["cards"] + [{"kind": kind, "record": record}]
        s.p.c.store.append(m, "server", "chat.card_sent", {"conversation": conv, "card": kind, "record": record, "side": c["side"]})
        if c["customer"]:
            s.p.crm.add_activity(m, c["customer"], "invoices" if OFFICE_CARDS[kind]["service"] == "lynkinv" else "payments" if kind in ("statement", "reminder") else "chats", s.now(), record)
        return {"kind": kind, "service": OFFICE_CARDS[kind]["service"], "record": record, "body": body, "actions": actions}

    def act(s, m, conv, kind, record, action, online=True, **kw):
        """A card's action opens its service's own step; the chat only passes the person on."""
        if not CH.card_action(kind, action, online):
            raise PermissionError("that action is not offered on this card now")
        if action == "pay":
            return {"opens": "lynkcheckout", "pay_link": s.p.invoicing.pay_link(m, record)}
        if action == "accept":
            return {"opens": "lynkinv", "quote": record}
        if action == "chat_about":
            return {"opens": "lynkchat", "conversation": s.open(m, s.convs.get(conv)["customer"], (kind, record))}
        if action == "promise_to_pay":
            return {"promise": s.p.invoicing.promise(m, record, kw["date"])}
        if action == "open_chats":
            return {"conversations": s.chats_behind(m, kw["figure"], kw["role"])}
        raise ValueError("unknown action")

    # ---- from the chat into the office services ---------------------------------------------------------------------------------
    def make_quote(s, m, conv, total_minor):
        did = s.p.invoicing.document(m, "quote", total_minor=int(total_minor))
        return s.card(m, conv, "quote", did)

    def make_invoice(s, m, conv, lines, preparer):
        c = s.convs.get(conv)
        if not c["customer"]:
            raise ValueError("add the customer first")
        r = s.p.invoicing.issue(m, c["customer"], lines, preparer=preparer)
        if r.get("state") == "awaiting_approval":
            return r                                                  # approval before sending: no card until it is issued
        return s.card(m, conv, "invoice", r["id"])

    def new_customer(s, m, conv, by, name=None, email=None, phone=None):
        """A new customer from a message; names and contacts go to the vault; the conversation joins their timeline."""
        rid = s.p.crm.create(m, by, "customer", name=name, email=email, phone=phone, source="chat")
        c = s.convs.get(conv); c["customer"] = rid
        s.p.crm.add_activity(m, rid, "chats", s.now(), conv)
        return rid

    def note(s, m, conv, by, text):
        c = s.convs.get(conv)
        if not c["customer"]:
            raise ValueError("add the customer first")
        text = str(text).strip()
        if not text or len(text) > 500:
            raise ValueError("a note has 1 to 500 characters")
        nid = uuid.uuid4().hex
        s.notes.put(nid, {"merchant": m, "customer": c["customer"], "conversation": conv, "by": by, "text": text, "at": s.now()})
        s.p.crm.add_activity(m, c["customer"], "notes", s.now(), nid)
        return nid

    def follow_up(s, m, conv, by, due, owner=None):
        c = s.convs.get(conv)
        fid = uuid.uuid4().hex
        s.follow.put(fid, {"merchant": m, "conversation": conv, "customer": c["customer"], "due": due, "owner": owner or by, "done": False})
        if c["customer"]:
            s.p.crm.add_activity(m, c["customer"], "notes", s.now(), fid)
        return fid

    # ---- chat figures and the chats behind them ----------------------------------------------------------------------------------
    def record(s, conv, first_reply_min=None, solved_min=None, reopened=False, solved_by_assist=None):
        c = s.convs.get(conv)
        if first_reply_min is not None:
            c["first_reply_min"] = int(first_reply_min)
        if solved_min is not None:
            c["solved_min"] = int(solved_min)
        if reopened:
            c["reopened"] = c["reopened"] + 1
        if solved_by_assist is not None:
            c["solved_by_assist"] = bool(solved_by_assist)

    def chat_figures(s, m):
        """First reply, time to solve, reopened and solved by LynkAssist alone, from real conversations; 'usually replies within'
        only from at least 20 replies (core/chat.py reply_time), never invented."""
        cs = [v for _, v in s.convs.items() if v["merchant"] == m]
        firsts = [v["first_reply_min"] for v in cs if v["first_reply_min"] is not None]
        solved = sorted(v["solved_min"] for v in cs if v["solved_min"] is not None)
        return {"conversations": len(cs), "usually_replies_within": CH.reply_time(firsts),
                "median_solve_min": solved[len(solved) // 2] if solved else None,
                "reopened": sum(1 for v in cs if v["reopened"]), "solved_by_assist": sum(1 for v in cs if v["solved_by_assist"])}

    def chats_behind(s, m, figure, role):
        if role not in OPEN_CHATS_ROLES:
            raise PermissionError("the chats behind a figure open only for the owner and managers")
        test = {"reopened": lambda v: v["reopened"] > 0, "solved_by_assist": lambda v: v["solved_by_assist"],
                "conversations": lambda v: True}.get(figure)
        if not test:
            raise ValueError("unknown figure")
        return [k for k, v in s.convs.items() if v["merchant"] == m and test(v)]
