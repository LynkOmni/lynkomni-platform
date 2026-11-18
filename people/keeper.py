"""LynkQueue on the devices of one place (LynkQ; build section 3B): the queue keeper.

Inside each building one device is the queue keeper (a LynkTab, LynkPC or LynkPOS the manager picked). Every other device, kiosk,
printer, screen or counter, only follows it, so the order stays exactly right with or without internet. The keeper gives out ticket
numbers from the block of codes the cloud set aside for it (a code is never used twice), keeps the fair order (staff press Call next
and never choose), moves people between sections and writes every step as a contract event on its own chain (dv/box.py). If the
keeper switches off, another added device takes over with the same queue and its own block of codes."""
import copy

from contract.tools.validate_contract import uuid7
from core import queue_tickets as R
from dv.box import LocalRejection


class QueueKeeper:
    def __init__(s, box, pack=None):
        s.box, s.pack = box, None
        s.tickets, s.seq, s.next_code, s.counters, s.served_since_priority, s.avg = {}, 0, {}, {}, 0, {}
        if pack: s.setup(pack)
    def setup(s, pack):
        """What the cloud gives an added device: the place's sections, counters, hours, priority balance and this device's blocks."""
        s.pack = pack
        for code, b in pack["blocks"].items():
            if code not in s.next_code or R.index(b["first"]) > R.index(s.next_code[code]["last"]): s.next_code[code] = {"next": b["first"], "last": R.code(min(R.index(b["first"]) + b["count"] - 1, R.CAPACITY - 1))}
        for c in pack["counters"]: s.counters.setdefault(c["counter_id"], {"state": "closed", "serving": None, "sections": c["sections"]})["sections"] = c["sections"]
    def _ready(s):
        if not s.pack: raise LocalRejection("device_not_added")                # only an added device can give out or call tickets
    def _minute(s): return s.box.clock.hour * 60 + s.box.clock.minute
    def _section(s, code):
        sec = next((x for x in s.pack["sections"] if x["code"] == code), None)
        if not sec: raise LocalRejection("section_closed")
        return sec

    # ---- getting a ticket
    def may_not_be_served(s, section):
        """Told before the ticket is taken when the wait is longer than the time left before closing."""
        sec = s._section(section); wait = R.wait_minutes(len(s.order(section)) + 1, s.avg.get(section, sec.get("average_minutes", 4)), max(1, s.open_counters(section)))
        return wait is not None and s._minute() + wait > sec["closes_min"]
    def issue(s, section, via="reception", priority=False, by=None, phone_mark=None, appointment=None):
        s._ready(); s.box._guard("IssueTicket"); sec = s._section(section); now = s._minute()
        if not sec["opens_min"] <= now < sec["closes_min"]: raise LocalRejection("section_closed")          # "Laboratory is closed. Opens tomorrow at 8:00."
        if now >= sec["closes_min"] - sec.get("last_ticket_before_min", 0): raise LocalRejection("after_last_ticket_time")
        if s.pack.get("free_limit_reached"): raise LocalRejection("free_limit_reached")                      # LynkQueue Free: the day the limit is reached still works; later days need a paid tier
        if phone_mark and any(t["phone"] == phone_mark and t["section"] == section and t["state"] == "waiting" for t in s.tickets.values()): raise LocalRejection("one_waiting_ticket_per_phone")
        slot = s.next_code.get(section)
        if not slot or slot["next"] is None: raise LocalRejection("no_codes_left_on_this_device")           # the cloud gives the next block when online
        code = slot["next"]; nxt = R.next_code(code)
        while R.rude(code): code, nxt = nxt, R.next_code(nxt)
        slot["next"] = nxt if nxt and R.index(nxt) <= R.index(slot["last"]) else None
        tid = uuid7(); s.seq += 1
        s.tickets[tid] = {"id": tid, "section": section, "first": section, "code": code, "seq": s.seq, "priority": bool(priority), "appointment": appointment, "held": False, "state": "waiting", "calls": 0, "counter": None,
                          "phone": phone_mark, "late_used": False, "missed_min": None, "via": via}
        s.box._emit("TicketIssued", {"ticket_id": tid, "place_id": s.pack["place_id"], "section": section, "code": code, "via": via, "priority": bool(priority), "device_id": s.box.d})
        if priority and by: s.box._emit("TicketPriorityMarked", {"ticket_id": tid, "by": by})
        return {"ticket_id": tid, "number": R.ticket_number(section, code), "place": s.place(tid), "wait_minutes": s.wait(tid)}
    def mark_priority(s, ticket, by):
        t = s._waiting(ticket); t["priority"] = True; s.box._emit("TicketPriorityMarked", {"ticket_id": ticket, "by": by})
    def _waiting(s, ticket):
        t = s.tickets.get(ticket)
        if not t or t["state"] != "waiting": raise LocalRejection("ticket_finished")
        return t

    # ---- the fair order
    def order(s, section=None, sections=None):
        """The order Call next will follow for one section (or a counter's sections, in the order the manager set)."""
        secs = sections or ([section] if section else [x["code"] for x in s.pack["sections"]])
        out, since = [], s.served_since_priority
        for code in secs:
            left = [t for t in s.tickets.values() if t["state"] == "waiting" and t["section"] == code]
            while left:
                tid = R.pick_next(left, since, s._minute(), s.pack.get("priority_balance", R.PRIORITY_BALANCE))
                if tid is None: break
                t = next(x for x in left if x["id"] == tid); out.append(tid); left.remove(t); since = 0 if t["priority"] else since + 1
        return out
    def open_counters(s, section=None): return sum(1 for c in s.counters.values() if c["state"] == "open" and (section is None or section in c["sections"]))
    def place(s, ticket):
        t = s.tickets[ticket]; o = s.order(t["section"])
        return R.place_of(ticket, o) if ticket in o else None
    def wait(s, ticket):
        t = s.tickets[ticket]; p = s.place(ticket)
        return None if p is None else R.wait_minutes(p, s.avg.get(t["section"], 4), s.open_counters(t["section"]))

    # ---- the counter
    def counter_state(s, counter, state, by=None):
        s._ready(); s.box._guard("SetCounterState"); c = s.counters[counter]
        if state not in ("open", "paused", "closed"): raise ValueError("open, paused or closed")
        if c["state"] == state: return
        c["state"] = state
        s.box._emit("CounterStateChanged", {"counter_id": counter, "place_id": s.pack["place_id"], "state": state, **({"by": by} if by else {})})
    def call_next(s, counter):
        s._ready(); s.box._guard("ServeTicket"); c = s.counters[counter]
        if c["state"] != "open": raise LocalRejection("counter_closed")
        if c["serving"]: raise LocalRejection("still_serving")
        o = s.order(sections=c["sections"])
        if not o: raise LocalRejection("no_one_waiting")
        t = s.tickets[o[0]]; t.update(state="called", calls=1, counter=counter); c["serving"] = t["id"]
        s.served_since_priority = 0 if t["priority"] else s.served_since_priority + 1
        s.box._emit("TicketCalled", {"ticket_id": t["id"], "counter_id": counter, "call": 1, "by_number": True})
        return {"ticket_id": t["id"], "number": R.ticket_number(t["first"], t["code"])}
    def _serving(s, counter):
        c = s.counters[counter]; t = s.tickets.get(c["serving"])
        if not t: raise LocalRejection("no_one_waiting")
        return c, t
    def call_again(s, counter):
        c, t = s._serving(counter)
        if t["calls"] >= R.CALLS_BEFORE_MISSED: raise LocalRejection("called_three_times")
        t["calls"] += 1; s.box._emit("TicketCalled", {"ticket_id": t["id"], "counter_id": counter, "call": t["calls"], "by_number": True})
    def served(s, counter):
        c, t = s._serving(counter); t["state"] = "served"; c["serving"] = None
        s.box._emit("TicketServed", {"ticket_id": t["id"], "counter_id": counter})
    def missed(s, counter):
        c, t = s._serving(counter)
        if t["calls"] < R.CALLS_BEFORE_MISSED: raise LocalRejection("call_three_times_first")
        t.update(state="missed", missed_min=s._minute()); c["serving"] = None
        s.box._emit("TicketMissed", {"ticket_id": t["id"]})
    def send_to(s, counter, to_section):
        """The same ticket and the same arrival time go on to another section: one ticket for the whole visit."""
        c, t = s._serving(counter); s._section(to_section)
        if to_section == t["section"]: raise ValueError("another section")
        t.update(section=to_section, state="waiting", calls=0, counter=None); c["serving"] = None
        s.box._emit("TicketSentTo", {"ticket_id": t["id"], "to_section": to_section})
    def put_back(s, ticket, by):
        """Within 15 minutes a missed ticket goes back in after the next 3 people (reception)."""
        t = s.tickets.get(ticket)
        if not t or t["state"] != "missed": raise LocalRejection("ticket_finished")
        o = R.put_back(s.order(t["section"]) + [ticket], ticket, t["missed_min"], s._minute())
        if o is None: raise LocalRejection("too_late_to_put_back")
        s._reseq(t, o); t.update(state="waiting", calls=0, counter=None)
        s.box._emit("TicketPutBack", {"ticket_id": ticket, "by": by})
    def _reseq(s, t, order):
        """Places a ticket where the new order puts it: just after the ticket before it (arrival order is a number, so it can sit between two)."""
        i = order.index(t["id"]); before = s.tickets[order[i - 1]]["seq"] if i else 0; after = s.tickets[order[i + 1]]["seq"] if i + 1 < len(order) else before + 2
        t["seq"] = (before + after) / 2
        t["priority"] = False if i else t["priority"]
    def check_ticket(s, number):
        """Real, for this place and for today, or "Not valid here"."""
        sec, _, code = number.partition("-")
        t = next((x for x in s.tickets.values() if x["first"] == sec and x["code"] == code), None) if R.valid_code(code) else None
        return {"valid": bool(t) and t["state"] in ("waiting", "called"), "state": t["state"] if t else "not_valid_here"}

    # ---- the person on their phone (relayed by the cloud or the building's own network)
    def running_late(s, ticket, from_cloud=False):
        """from_cloud: the person asked on the internet and the cloud already wrote it, so the keeper only moves the ticket."""
        t = s._waiting(ticket)
        if t["late_used"]: raise LocalRejection("already_used_once")
        o = s.order(t["section"]); s._reseq(t, R.running_late(o, ticket)); t["late_used"] = True
        if not from_cloud: s.box._guard("ChangeTicketPlace"); s.box._emit("TicketRunningLate", {"ticket_id": ticket})
    def leave(s, ticket, from_cloud=False):
        t = s._waiting(ticket); t["state"] = "left"
        if not from_cloud: s.box._emit("TicketLeft", {"ticket_id": ticket})
    def close_day(s):
        """Closing: the keeper clears today's queue (the cloud writes "Not served today") and closes the counters."""
        left = [t["id"] for t in s.tickets.values() if t["state"] in ("waiting", "missed")]
        for t in s.tickets.values():
            if t["id"] in left: t["state"] = "not_served_today"
        for cid, c in s.counters.items():
            if c["state"] != "closed" and not c["serving"]: s.counter_state(cid, "closed")
        return left
    def please_come(s):
        """Tickets taken by phone that have 5 people or fewer ahead: "Please come now" (sent once each)."""
        out = []
        for t in s.tickets.values():
            if t["state"] == "waiting" and t["phone"] and not t.get("told") and (s.place(t["id"]) or 99) <= R.PLEASE_COME_AT: t["told"] = True; out.append(t["id"])
        return out

    # ---- LynkAttend link (only when switched on): a counter opens when its person checks in and closes when they check out
    def on_check(s, member, direction, counters):
        """counters: the counters this person serves (from the cloud's setup). It can be undone with the counter's own buttons."""
        done = []
        for cid in counters:
            c = s.counters.get(cid)
            if not c or c["serving"]: continue                                 # never closes a counter in the middle of serving someone
            want = "open" if direction == "in" else "closed"
            if c["state"] != want: s.counter_state(cid, want, by=member); done.append(cid)
        return done

    # ---- another device takes over as queue keeper, with the same queue and its own codes
    def take_over_from(s, old):
        s._ready(); s.box._guard("TakeOverQueueKeeper")
        s.tickets, s.seq, s.served_since_priority, s.avg = copy.deepcopy(old.tickets), old.seq, old.served_since_priority, dict(old.avg)
        for cid, c in old.counters.items(): s.counters[cid] = dict(c)
        s.box._emit("QueueKeeperChanged", {"place_id": s.pack["place_id"], "device_id": s.box.d})
        unused = {code: v for code, v in old.next_code.items() if v["next"]}
        for code, v in unused.items(): s.box._emit("TicketCodesVoided", {"place_id": s.pack["place_id"], "device_id": old.box.d, "section": code, "first": v["next"], "last": v["last"], "reason": "block_not_used"})
        return sorted(unused)
