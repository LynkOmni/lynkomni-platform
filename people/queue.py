"""LynkQueue, the cloud side (LynkQ; master blueprint section 63; build section 3B).

One system controls everything: it sets up places, sections and counters, adds the devices (only an added device can give out or
call tickets), sets a block of ticket codes aside for each device (a code is never used twice for a section at a place), takes in
what the building's queue keeper recorded (people/keeper.py, also after hours offline), tells the person waiting, closes the day
("Not served today"), and keeps the live view, the history, the reports and the public queue page.

A ticket shows only its number: never a name. A phone number is kept only in the PII vault, by reference, for that ticket's
messages, and is removed after 30 days. No event carries one. The person on the phone (link, WhatsApp, LynkChat, basic phone) asks
the cloud; the cloud checks the plan and passes the request to the place's queue keeper, which alone gives the number."""
import hashlib, hmac, json, time

from contract.tools.validate_contract import uuid4
from core import queue_tickets as R
from services import billing

DAY = 86400
CONTACT_KEPT_DAYS = 30
PLEASE_CHECK_TIMES = 3             # a staff member using Priority or Put back 3 times as often as the others: "Please check"
LONG_WAIT_MINUTES = 30             # LynkAssist suggests opening another counter (the manager decides)
JOIN_WAYS = ("link", "whatsapp", "lynkchat", "basic_phone")
PARTNER_WAYS = ("whatsapp", "basic_phone")          # need the people_messages partner in that country; the link and LynkChat never do
DEVICE_KINDS = ("reception", "counter", "kiosk", "screen", "counter_display", "printer", "counter_keypad", "call_button", "pager_set", "scanner")
KEEPER_KINDS = ("reception", "counter")             # a LynkTab, LynkPC or LynkPOS; a kiosk, screen or display only follows
SETUPS = {"just_me": {"sections": [("GEN", 1)]}, "one_place": {"sections": [("GEN", 2)]}, "many_places": {"sections": [("GEN", 3)]}}


def _now(n): return time.time() if n is None else n
def _day(n): return int(n // DAY)


class Queue:
    def __init__(s, cloud, platform, notifier=None, messages=None):
        s.cloud, s.p, s.db, s.vault = cloud, platform, platform.c.store.db, platform.vault
        s.n, s.partner = notifier, messages
        s.db.executescript("""
        create table if not exists qu_managers(merchant text, manager text, primary key(merchant, manager));
        create table if not exists qu_places(place_id text primary key, merchant text, country text, join_from text, balance int, keeper text, public_page int, mark_key text, opened int);
        create table if not exists qu_sections(place text, code text, opens_min int, closes_min int, last_before int, avg_minutes int, last_code text, primary key(place, code));
        create table if not exists qu_counters(counter_id text primary key, place text, sections text, state text, staff text, serving text);
        create table if not exists qu_devices(device_id text primary key, merchant text, place text, kind text, locked int, seen real, health text);
        create table if not exists qu_blocks(place text, device text, section text, first text, last text, used text, voided int);
        create table if not exists qu_tickets(ticket_id text primary key, merchant text, place text, section text, first_section text, code text, via text, priority int, state text,
          issued real, called real, done real, counter text, calls int, device text, contact_ref text, contact_until real, lang text, sent_to int, told int);
        create table if not exists qu_joins(join_id text primary key, merchant text, place text, section text, way text, contact_ref text, mark text, lang text, at real, ticket text);
        create table if not exists qu_history(merchant text, place text, at real, by text, what text, ticket text);
        create table if not exists qu_seen(event_id text primary key);
        create table if not exists qu_checks(merchant text, staff text, sign text, at real);
        create table if not exists qu_pickup(point text primary key, merchant text, place text, section text);
        create table if not exists qu_staff(counter text primary key, member text);""")

    # ---- small helpers
    def _ent(s, merchant): return billing.Billing(s.p.c).entitlement(merchant, "lynkqueue")
    def _log(s, merchant, place, by, what, ticket=None, now=None): s.db.execute("insert into qu_history values(?,?,?,?,?,?)", (merchant, place, _now(now), by, what, ticket))
    def _need_manager(s, merchant, who):
        if not s.db.execute("select 1 from qu_managers where merchant=? and manager=?", (merchant, who)).fetchone(): raise PermissionError("only_the_manager")
    def _managers(s, merchant): return [r[0] for r in s.db.execute("select manager from qu_managers where merchant=?", (merchant,))]
    def _tell(s, kind, person, event_id, now, record=None, business=None, role=None, facts=None, lang="en"):
        if s.n: return s.n.notify(kind, person, event_id, _now(now), facts=facts, record=record, business=business, role=role, lang=lang)
    def _place(s, place):
        r = s.db.execute("select merchant, country, join_from, balance, keeper, public_page, mark_key, opened from qu_places where place_id=?", (place,)).fetchone()
        if not r: raise KeyError("no such place")
        return dict(zip(("merchant", "country", "join_from", "balance", "keeper", "public_page", "mark_key", "opened"), r))
    def _sections(s, place): return [dict(zip(("code", "opens_min", "closes_min", "last_ticket_before_min", "average_minutes"), r)) for r in s.db.execute("select code, opens_min, closes_min, last_before, avg_minutes from qu_sections where place=? order by rowid", (place,))]
    def _counters(s, place): return [{"counter_id": r[0], "sections": json.loads(r[1])} for r in s.db.execute("select counter_id, sections from qu_counters where place=? order by rowid", (place,))]

    # ---- setting up: managers, places, sections, counters
    def add_manager(s, merchant, manager): s.db.execute("insert or ignore into qu_managers values(?,?)", (merchant, manager))
    def add_place(s, merchant, by, country=None, setup="one_place", join_from="anywhere", now=None):
        """A branch, an event, or simply "my place". The setup kind fills in a ready setup the manager can change."""
        s._need_manager(merchant, by); ent = s._ent(merchant)
        if setup not in SETUPS or join_from not in ("anywhere", "only_at_the_place"): raise ValueError("unknown setup")
        have = s.db.execute("select count(*) from qu_places where merchant=?", (merchant,)).fetchone()[0]
        if ent["max_places"] is not None and have >= ent["max_places"]: raise PermissionError("plan_limit_places")
        pid = uuid4()
        s.db.execute("insert into qu_places values(?,?,?,?,?,null,0,?,0)", (pid, merchant, country, join_from, R.PRIORITY_BALANCE, uuid4()))
        for code, counters in SETUPS[setup]["sections"]:
            s.add_section(merchant, pid, code, by, now=now)
            for _ in range(counters): s.add_counter(merchant, pid, [code], by, now=now)
        s._log(merchant, pid, by, "place_added", now=now); return pid
    def add_section(s, merchant, place, code, by, opens_min=8 * 60, closes_min=17 * 60, last_ticket_before_min=30, average_minutes=4, now=None):
        s._need_manager(merchant, by); ent = s._ent(merchant)
        if not R.valid_section(code): raise ValueError("a section code is 3 Lynk Alphabet characters")
        n = s.db.execute("select count(*) from qu_sections where place=?", (place,)).fetchone()[0]
        if ent["sections_per_place"] is not None and n >= ent["sections_per_place"]: raise PermissionError("plan_limit_sections")
        if s.db.execute("select 1 from qu_sections where place=? and code=?", (place, code)).fetchone(): raise ValueError("section code already used here")
        s.db.execute("insert into qu_sections values(?,?,?,?,?,?,null)", (place, code, opens_min, closes_min, last_ticket_before_min, average_minutes))
        for (dev,) in s.db.execute("select device_id from qu_devices where place=? and locked=0 and kind in (%s)" % ",".join("?" * len(KEEPER_KINDS)), (place, *KEEPER_KINDS)).fetchall(): s._reserve(merchant, place, dev, code, now)
        s._log(merchant, place, by, f"section_added:{code}", now=now)
    def set_hours(s, merchant, place, code, by, opens_min, closes_min, last_ticket_before_min=None, now=None):
        s._need_manager(merchant, by)
        s.db.execute("update qu_sections set opens_min=?, closes_min=?, last_before=coalesce(?, last_before) where place=? and code=?", (opens_min, closes_min, last_ticket_before_min, place, code))
        s._log(merchant, place, by, f"hours_changed:{code}", now=now)
    def remove_section(s, merchant, place, code, by, now=None):
        """A section is removed only when no one waits there; its codes are closed and never reused."""
        s._need_manager(merchant, by)
        if s.db.execute("select 1 from qu_tickets where place=? and section=? and state in ('waiting','called')", (place, code)).fetchone(): raise ValueError("people_still_waiting")
        s.db.execute("delete from qu_sections where place=? and code=?", (place, code)); s._log(merchant, place, by, f"section_removed:{code}", now=now)
    def add_counter(s, merchant, place, sections, by, now=None):
        """A desk, window, room or chair. It may serve several sections, in the order the manager sets."""
        s._need_manager(merchant, by); ent = s._ent(merchant)
        n = s.db.execute("select count(*) from qu_counters where place=?", (place,)).fetchone()[0]
        if ent["counters_per_place"] is not None and n >= ent["counters_per_place"]: raise PermissionError("plan_limit_counters")
        known = {x["code"] for x in s._sections(place)}
        if not sections or any(c not in known for c in sections): raise ValueError("unknown section")
        cid = uuid4(); s.db.execute("insert into qu_counters values(?,?,?,'closed',null,null)", (cid, place, json.dumps(list(sections))))
        s._log(merchant, place, by, "counter_added", now=now); return cid
    def set_counter_sections(s, merchant, counter, sections, by, now=None):
        s._need_manager(merchant, by); place = s.db.execute("select place from qu_counters where counter_id=?", (counter,)).fetchone()[0]
        if any(c not in {x["code"] for x in s._sections(place)} for c in sections): raise ValueError("unknown section")
        s.db.execute("update qu_counters set sections=? where counter_id=?", (json.dumps(list(sections)), counter)); s._log(merchant, place, by, "counter_sections_changed", now=now)
    def set_balance(s, merchant, place, balance, by, now=None):
        """1 priority person after every `balance` others."""
        s._need_manager(merchant, by)
        if not 1 <= int(balance) <= 10: raise ValueError("1 to 10")
        s.db.execute("update qu_places set balance=? where place_id=?", (int(balance), place)); s._log(merchant, place, by, f"priority_balance:{int(balance)}", now=now)
    def set_public_page(s, merchant, place, on, by, now=None):
        s._need_manager(merchant, by); s.db.execute("update qu_places set public_page=? where place_id=?", (1 if on else 0, place)); s._log(merchant, place, by, f"public_page:{'on' if on else 'off'}", now=now)

    # ---- devices: only an added device works; each gets its own block of codes; a lost one is locked
    def add_device(s, merchant, place, device_id, kind, by, now=None):
        s._need_manager(merchant, by); ent = s._ent(merchant)
        if kind not in DEVICE_KINDS: raise ValueError("unknown device kind")
        if kind in ("printer", "counter_keypad", "call_button", "pager_set", "scanner") and not ent["own_hardware"]: raise PermissionError("plan_no_hardware_without_display")
        s.db.execute("insert or replace into qu_devices values(?,?,?,?,0,?,'ok')", (device_id, merchant, place, kind, _now(now)))
        if kind in KEEPER_KINDS:
            for sec in s._sections(place): s._reserve(merchant, place, device_id, sec["code"], now)
            if not s._place(place)["keeper"]: s.db.execute("update qu_places set keeper=? where place_id=?", (device_id, place))
        s._log(merchant, place, by, f"device_added:{kind}", now=now)
        return s.pack(device_id, now=now)
    def _reserve(s, merchant, place, device, section, now):
        """The next block of codes for one device, after every code already set aside for that section at that place."""
        last = s.db.execute("select last_code from qu_sections where place=? and code=?", (place, section)).fetchone()[0]
        b = R.reserve_block(last)
        if b is None: raise ValueError("section_codes_used_up")               # the section then gets a new section code
        count = R.index(b["last"]) - R.index(b["first"]) + 1
        s.db.execute("update qu_sections set last_code=? where place=? and code=?", (b["last"], place, section))
        s.db.execute("insert into qu_blocks values(?,?,?,?,?,null,0)", (place, device, section, b["first"], b["last"]))
        s.cloud.event(merchant, "TicketCodesReserved", {"place_id": place, "device_id": device, "section": section, "first": b["first"], "count": count}, now=now)
        return {"first": b["first"], "count": count}
    def more_codes(s, merchant, device_id, section, now=None):
        """When online, a device that is running low gets its next block."""
        d = s._device(merchant, device_id); return s._reserve(merchant, d["place"], device_id, section, now)
    def _device(s, merchant, device_id):
        r = s.db.execute("select place, kind, locked from qu_devices where device_id=? and merchant=?", (device_id, merchant)).fetchone()
        if not r: raise KeyError("device_not_added")
        return {"place": r[0], "kind": r[1], "locked": bool(r[2])}
    def pack(s, device_id, now=None):
        """What an added device holds: the place's setup and its own blocks of codes. Never a contact, never a name."""
        place, merchant, locked = s.db.execute("select place, merchant, locked from qu_devices where device_id=?", (device_id,)).fetchone()
        if locked: raise PermissionError("device_locked")
        pl, blocks = s._place(place), {}
        for sec, first, last, used in s.db.execute("select section, first, last, used from qu_blocks where place=? and device=? and voided=0 order by rowid", (place, device_id)):
            start = R.next_code(used) if used else first
            if start and R.index(start) <= R.index(last) and sec not in blocks: blocks[sec] = {"first": start, "count": R.index(last) - R.index(start) + 1}
        return {"place_id": place, "sections": s._sections(place), "counters": s._counters(place), "priority_balance": pl["balance"], "join_from": pl["join_from"], "blocks": blocks,
                "keeper": pl["keeper"], "free_limit_reached": s._free_limit_reached(merchant, place, _now(now))}
    def lock_device(s, merchant, device_id, by, now=None):
        """Lost or stolen: it can no longer give out or call tickets, and its unused codes are closed for good."""
        s._need_manager(merchant, by); d = s._device(merchant, device_id)
        s.db.execute("update qu_devices set locked=1 where device_id=?", (device_id,))
        for rowid, sec, first, last, used in s.db.execute("select rowid, section, first, last, used from qu_blocks where device=? and voided=0", (device_id,)).fetchall():
            start = R.next_code(used) if used else first
            if start and R.index(start) <= R.index(last): s.cloud.event(merchant, "TicketCodesVoided", {"place_id": d["place"], "device_id": device_id, "section": sec, "first": start, "last": last, "reason": "device_locked"}, now=now)
            s.db.execute("update qu_blocks set voided=1 where rowid=?", (rowid,))
        if s._place(d["place"])["keeper"] == device_id: s.db.execute("update qu_places set keeper=null where place_id=?", (d["place"],))
        s._log(merchant, d["place"], by, "device_locked", now=now)
    def device_health(s, merchant, device_id, health, now=None):
        """Offline, paper low, battery low: shown on the dashboard ("Reception printer: paper low")."""
        if health not in ("ok", "offline", "paper_low", "battery_low"): raise ValueError("unknown health")
        s._device(merchant, device_id); s.db.execute("update qu_devices set health=?, seen=? where device_id=?", (health, _now(now), device_id))
    def devices(s, merchant, place): return [dict(zip(("device_id", "kind", "locked", "health"), (r[0], r[1], bool(r[2]), r[3]))) for r in s.db.execute("select device_id, kind, locked, health from qu_devices where merchant=? and place=? order by rowid", (merchant, place))]

    # ---- the plan: nobody is turned away
    def _month(s, n): t = time.gmtime(n); return (t.tm_year, t.tm_mon)
    def _month_start(s, n): t = time.gmtime(n); return time.mktime((t.tm_year, t.tm_mon, 1, 0, 0, 0, 0, 0, 0)) - time.timezone
    def _free_limit_reached(s, merchant, place, n):
        """LynkQueue Free: tickets keep working until closing on the day the limit is reached; the rest of the month needs a paid tier."""
        ent = s._ent(merchant)
        if ent["extra_place_cents"] is not None: return False                  # paid tiers: extra tickets just cost more
        before_today = s.db.execute("select count(*) from qu_tickets where place=? and issued>=? and issued<?", (place, s._month_start(n), _day(n) * DAY)).fetchone()[0]
        return before_today >= ent["tickets_per_place_month"]

    # ---- what the queue keeper recorded reaches the cloud (maybe hours later)
    def ingest(s, merchant, evt, now=None):
        t, p, n = evt["type"], evt["payload"], _now(now)
        dev = s.db.execute("select place, locked from qu_devices where device_id=? and merchant=?", (evt.get("device_id"), merchant)).fetchone()
        if not dev or dev[1]: return {"state": "refused", "reason": "device_not_added"}
        if s.db.execute("select 1 from qu_seen where event_id=?", (evt["event_id"],)).fetchone(): return {"state": "duplicate"}
        place, at = dev[0], _epoch(evt["occurred_at_device"])
        if t == "TicketIssued":
            blk = s.db.execute("select rowid from qu_blocks where place=? and device=? and section=? and voided=0", (place, evt["device_id"], p["section"])).fetchall()
            inside = [r[0] for r in blk if s._in_block(r[0], p["code"])]
            if not inside or s.db.execute("select 1 from qu_tickets where place=? and first_section=? and code=?", (place, p["section"], p["code"])).fetchone():
                return {"state": "refused", "reason": "code_not_set_aside_for_this_device"}                 # a code is never used twice
        s.db.execute("insert into qu_seen values(?)", (evt["event_id"],))
        eid = s.cloud.device_event(merchant, evt, now=n)
        tk = p.get("ticket_id"); by = p.get("by") or evt.get("actor_user_id")
        if t == "TicketIssued":
            s.db.execute("update qu_blocks set used=? where rowid=?", (p["code"], inside[0]))
            j = s.db.execute("select contact_ref, lang, join_id from qu_joins where place=? and ticket=?", (place, tk)).fetchone()
            s.db.execute("insert into qu_tickets values(?,?,?,?,?,?,?,?,'waiting',?,null,null,null,0,?,?,?,?,0,0)", (tk, merchant, place, p["section"], p["section"], p["code"], p["via"], 1 if p.get("priority") else 0, at, evt["device_id"],
                         j[0] if j else None, at + CONTACT_KEPT_DAYS * DAY if j else None, j[1] if j else "en"))
            s._log(merchant, place, by, "ticket_given", tk, at)
        elif t == "TicketPriorityMarked":
            s.db.execute("update qu_tickets set priority=1 where ticket_id=?", (tk,)); s._log(merchant, place, p["by"], "priority", tk, at); s._check(merchant, p["by"], "priority", at)
        elif t == "TicketCalled":
            s.db.execute("update qu_tickets set state='called', called=coalesce(called, ?), counter=?, calls=? where ticket_id=?", (at, p["counter_id"], p["call"], tk))
            s.db.execute("update qu_counters set serving=? where counter_id=?", (tk, p["counter_id"]))
            s._log(merchant, place, by, f"called:{p['call']}", tk, at)
            if p["call"] == 1: s._to_person("queue_your_turn", tk, eid, n)
        elif t == "TicketServed":
            s.db.execute("update qu_tickets set state='served', done=? where ticket_id=?", (at, tk)); s.db.execute("update qu_counters set serving=null where counter_id=?", (p["counter_id"],))
            s._learn(place, tk); s._log(merchant, place, by, "served", tk, at)
        elif t == "TicketSentTo":
            s.db.execute("update qu_tickets set state='waiting', section=?, sent_to=sent_to+1, calls=0, counter=null where ticket_id=?", (p["to_section"], tk))
            s.db.execute("update qu_counters set serving=null where serving=?", (tk,)); s._log(merchant, place, by, f"sent_to:{p['to_section']}", tk, at); s._to_person("queue_next_section", tk, eid, n)
        elif t == "TicketMissed":
            s.db.execute("update qu_tickets set state='missed', done=? where ticket_id=?", (at, tk)); s.db.execute("update qu_counters set serving=null where serving=?", (tk,))
            s._log(merchant, place, by, "missed", tk, at); s._to_person("queue_missed", tk, eid, n)
        elif t == "TicketPutBack":
            s.db.execute("update qu_tickets set state='waiting', done=null, calls=0 where ticket_id=?", (tk,)); s._log(merchant, place, p["by"], "put_back", tk, at); s._check(merchant, p["by"], "put_back", at)
        elif t == "TicketRunningLate": s._log(merchant, place, None, "running_late", tk, at)
        elif t == "TicketLeft":
            s.db.execute("update qu_tickets set state='left', done=? where ticket_id=?", (at, tk)); s._log(merchant, place, None, "left", tk, at)
        elif t == "CounterStateChanged":
            s.db.execute("update qu_counters set state=?, staff=? where counter_id=?", (p["state"], p.get("by") if p["state"] != "closed" else None, p["counter_id"])); s._log(merchant, place, p.get("by"), f"counter_{p['state']}", now=at)
        elif t == "QueueKeeperChanged":
            s.db.execute("update qu_places set keeper=? where place_id=?", (p["device_id"], place)); s._log(merchant, place, None, "queue_keeper_changed", now=at)
            for mg in s._managers(merchant): s._tell("queue_device_health", mg, eid, n, record=place, business=merchant, role="manager")
        elif t == "TicketCodesVoided":
            s.db.execute("update qu_blocks set voided=1 where place=? and device=? and section=?", (place, p["device_id"], p["section"]))
        return {"state": "accepted", "event_id": eid}
    def _in_block(s, rowid, code):
        first, last = s.db.execute("select first, last from qu_blocks where rowid=?", (rowid,)).fetchone()
        return R.valid_code(code) and R.index(first) <= R.index(code) <= R.index(last)
    def _learn(s, place, ticket):
        """Wait time learns by itself: the section's usual serving time moves a little towards each real one."""
        sec, called, done = s.db.execute("select section, called, done from qu_tickets where ticket_id=?", (ticket,)).fetchone()
        if called and done and done > called:
            avg = s.db.execute("select avg_minutes from qu_sections where place=? and code=?", (place, sec)).fetchone()
            if avg: s.db.execute("update qu_sections set avg_minutes=? where place=? and code=?", (max(1, round((avg[0] * 9 + (done - called) / 60) / 10)), place, sec))
    def _to_person(s, kind, ticket, eid, now):
        """Only people who joined by phone get a message, in their language, to their own contact (a vault reference)."""
        r = s.db.execute("select contact_ref, lang, merchant from qu_tickets where ticket_id=?", (ticket,)).fetchone()
        if r and r[0]: return s._tell(kind, r[0], eid, now, record=ticket, business=r[2], lang=r[1] or "en")
    def _check(s, merchant, staff, sign, at):
        """Priority or Put back used far more than the others do: "Please check". Only a flag, never an accusation."""
        s.db.execute("insert into qu_checks values(?,?,?,?)", (merchant, staff, sign, at))
    def please_check(s, merchant, now=None):
        n, out = _now(now), []
        for sign in ("priority", "put_back"):
            rows = dict(s.db.execute("select staff, count(*) from qu_checks where merchant=? and sign=? and at>=? group by staff", (merchant, sign, n - 30 * DAY)).fetchall())
            for staff, c in rows.items():
                others = [v for k, v in rows.items() if k != staff]
                if c >= PLEASE_CHECK_TIMES and others and c >= PLEASE_CHECK_TIMES * (sum(others) / len(others)): out.append({"staff": staff, "sign": sign, "times": c})
        return out

    # ---- the person on a phone: the link or QR, WhatsApp, LynkChat, basic phone
    def mark(s, place, contact): return hmac.new(s._place(place)["mark_key"].encode(), contact.encode(), hashlib.sha256).hexdigest()[:32]
    def see_wait(s, place):
        """Seen before taking a ticket: how many are waiting in each section and about how long."""
        return [{"section": x["code"], "waiting": w, "about_minutes": R.wait_minutes(w + 1, x["average_minutes"], max(1, s._open(place, x["code"])))} for x in s._sections(place)
                for w in [s.db.execute("select count(*) from qu_tickets where place=? and section=? and state='waiting'", (place, x["code"])).fetchone()[0]]]
    def _open(s, place, section): return sum(1 for cid, secs in s.db.execute("select counter_id, sections from qu_counters where place=? and state='open'", (place,)) if section in json.loads(secs))
    def join(s, merchant, place, section, way, contact, lang="en", at_the_place=False, now=None):
        """A request to join by phone. The cloud checks the plan and the place's choice; the queue keeper gives the number."""
        ent, pl, n = s._ent(merchant), s._place(place), _now(now)
        if way not in JOIN_WAYS: raise ValueError("unknown way")
        if way in ("whatsapp", "lynkchat") and not ent["whatsapp_and_chat"]: return {"state": "refused", "reason": "plan_no_whatsapp_or_chat"}
        if way == "basic_phone" and not ent["basic_phone"]: return {"state": "refused", "reason": "plan_no_basic_phone"}
        if way in PARTNER_WAYS:
            from providers import ready
            if not ready("people_messages", pl["country"])[0]: return {"state": "coming_soon"}        # "Coming to your country soon."
        if pl["join_from"] == "only_at_the_place" and not at_the_place: return {"state": "refused", "reason": "only_at_the_place"}
        if section not in {x["code"] for x in s._sections(place)}: return {"state": "refused", "reason": "section_closed"}
        mark = s.mark(place, contact)
        if s.db.execute("select 1 from qu_joins j join qu_tickets t on t.ticket_id=j.ticket where j.place=? and j.mark=? and t.section=? and t.state='waiting'", (place, mark, section)).fetchone(): return {"state": "refused", "reason": "one_waiting_ticket_per_phone"}
        jid = uuid4(); ref = s.vault.put(jid, "contact", contact)
        s.db.execute("insert into qu_joins values(?,?,?,?,?,?,?,?,?,null)", (jid, merchant, place, section, way, ref, mark, lang, n))
        return {"state": "sent", "join_id": jid, "section": section, "phone_mark": mark, "via": "smartphone" if way == "link" else way}
    def joined(s, join_id, ticket_id):
        """The queue keeper gave the number: the request is tied to its ticket (before the ticket's event arrives, or after)."""
        s.db.execute("update qu_joins set ticket=? where join_id=?", (ticket_id, join_id))
        ref, lang, at = s.db.execute("select contact_ref, lang, at from qu_joins where join_id=?", (join_id,)).fetchone()
        s.db.execute("update qu_tickets set contact_ref=?, lang=?, contact_until=? where ticket_id=?", (ref, lang, at + CONTACT_KEPT_DAYS * DAY, ticket_id))
    def running_late(s, merchant, ticket_id, now=None):
        """Asked from the phone while the building is online: written by the cloud and passed to the queue keeper."""
        s._waiting(ticket_id); eid = s.cloud.event(merchant, "TicketRunningLate", {"ticket_id": ticket_id}, now=now); s._log(merchant, s._tk(ticket_id)["place"], None, "running_late", ticket_id, now); return eid
    def leave(s, merchant, ticket_id, now=None):
        s._waiting(ticket_id); eid = s.cloud.event(merchant, "TicketLeft", {"ticket_id": ticket_id}, now=now)
        s.db.execute("update qu_tickets set state='left', done=? where ticket_id=?", (_now(now), ticket_id)); s._log(merchant, s._tk(ticket_id)["place"], None, "left", ticket_id, now); return eid
    def _tk(s, ticket):
        r = s.db.execute("select merchant, place, section, code, state, issued, priority, via, first_section from qu_tickets where ticket_id=?", (ticket,)).fetchone()
        if not r: raise KeyError("no such ticket")
        return dict(zip(("merchant", "place", "section", "code", "state", "issued", "priority", "via", "first_section"), r))
    def _waiting(s, ticket):
        if s._tk(ticket)["state"] != "waiting": raise ValueError("ticket_finished")
    def please_come(s, merchant, place, ticket_ids, now=None):
        """"Please come now" when 5 people are left (the queue keeper says who; told once each)."""
        out = []
        for tk in ticket_ids:
            if s.db.execute("select told from qu_tickets where ticket_id=? and place=?", (tk, place)).fetchone() == (0,):
                s.db.execute("update qu_tickets set told=1 where ticket_id=?", (tk,)); s._to_person("queue_your_turn", tk, f"please-come:{tk}", now); out.append(tk)
        return out
    def ticket(s, ticket_id):
        """What the person's phone shows: the number, where it stands and about how long. Never a name, never who is serving."""
        t = s._tk(ticket_id); ahead = s.db.execute("select count(*) from qu_tickets where place=? and section=? and state='waiting' and (issued<? or (issued=? and rowid<(select rowid from qu_tickets where ticket_id=?)))", (t["place"], t["section"], t["issued"], t["issued"], ticket_id)).fetchone()[0]
        avg = s.db.execute("select avg_minutes from qu_sections where place=? and code=?", (t["place"], t["section"])).fetchone()
        counter = s.db.execute("select counter from qu_tickets where ticket_id=?", (ticket_id,)).fetchone()[0]
        out = {"number": R.ticket_number(t["first_section"], t["code"]), "section": t["section"], "state": t["state"]}
        if t["state"] == "waiting": out.update(place=ahead + 1, about_minutes=R.wait_minutes(ahead + 1, avg[0] if avg else 4, max(1, s._open(t["place"], t["section"]))))
        if t["state"] == "called": out["counter_id"] = counter
        return out

    def pending(s, place):
        """Requests waiting for the queue keeper to give a number (phone joins and parcel collections), oldest first."""
        return [dict(zip(("join_id", "section", "way", "phone_mark"), r)) for r in s.db.execute("select join_id, section, way, mark from qu_joins where place=? and ticket is null order by rowid", (place,))]

    # ---- links, only when switched on: LynkAttend opens a counter, a pickup point gives collections a ticket
    def set_counter_staff(s, merchant, counter, member, by, now=None):
        """The person who serves at a counter (a LynkAttend member): the counter can then open when they check in."""
        s._need_manager(merchant, by); place = s.db.execute("select place from qu_counters where counter_id=?", (counter,)).fetchone()[0]
        s.db.execute("insert or replace into qu_staff values(?,?)", (counter, member)); s._log(merchant, place, by, "counter_staff_set", now=now)
    def counters_of(s, member): return [r[0] for r in s.db.execute("select counter from qu_staff where member=?", (member,))]
    def set_pickup_section(s, merchant, point, place, section, by, now=None):
        """Parcel collections at this pickup point wait in this section."""
        s._need_manager(merchant, by)
        if section not in {x["code"] for x in s._sections(place)}: raise ValueError("unknown section")
        s.db.execute("insert or replace into qu_pickup values(?,?,?,?)", (point, merchant, place, section)); s._log(merchant, place, by, f"pickup_section:{section}", now=now)
    def collection(s, merchant, point, shipment, now=None):
        """A parcel reached the pickup point: a request is made ready, and the keeper gives the ticket when the person comes."""
        r = s.db.execute("select place, section from qu_pickup where point=? and merchant=?", (point, merchant)).fetchone()
        if not r: return None
        jid = uuid4(); s.db.execute("insert into qu_joins values(?,?,?,?,'collection',null,?,'en',?,null)", (jid, merchant, r[0], r[1], f"shipment:{shipment}", _now(now)))
        return {"join_id": jid, "place": r[0], "section": r[1]}
    def places(s, merchant): return [r[0] for r in s.db.execute("select place_id from qu_places where merchant=? order by rowid", (merchant,))]
    def closing_due(s, merchant, now=None):
        """Places whose last section has closed for the day and that still have someone waiting."""
        n = _now(now); minute = int(n % DAY // 60)
        return [pl for pl in s.places(merchant) if all(minute >= x["closes_min"] for x in s._sections(pl))
                and s.db.execute("select 1 from qu_tickets where place=? and state in ('waiting','missed')", (pl,)).fetchone()]

    # ---- closing: a ticket is for today only
    def close_day(s, merchant, place, now=None):
        """Tickets still waiting at closing are closed by themselves and marked "Not served today"; they show in the reports."""
        n, out = _now(now), []
        for (tk,) in s.db.execute("select ticket_id from qu_tickets where merchant=? and place=? and state in ('waiting','missed') and issued<=?", (merchant, place, n)).fetchall():
            s.cloud.event(merchant, "TicketNotServedToday", {"ticket_id": tk}, now=n)
            s.db.execute("update qu_tickets set state='not_served_today', done=? where ticket_id=?", (n, tk)); s._log(merchant, place, None, "not_served_today", tk, n); out.append(tk)
        s.db.execute("update qu_counters set state='closed', staff=null, serving=null where place=?", (place,))
        return out
    def forget_contacts(s, now=None):
        """A phone number is used only for that ticket's messages and is removed after 30 days."""
        n = _now(now); old = [r[0] for r in s.db.execute("select join_id from qu_joins where contact_ref is not null and at<=?", (n - CONTACT_KEPT_DAYS * DAY,)).fetchall()]
        s.db.execute("update qu_tickets set contact_ref=null where contact_until<=?", (n,)); s.db.execute("update qu_joins set contact_ref=null, mark=null where at<=?", (n - CONTACT_KEPT_DAYS * DAY,))
        for jid in old: s.vault.delete_subject(jid)
        return len(old)

    # ---- the manager: live view, suggestions, forecast, history, reports
    def live(s, merchant, place, now=None):
        n, out = _now(now), []
        for x in s._sections(place):
            rows = s.db.execute("select issued from qu_tickets where place=? and section=? and state='waiting'", (place, x["code"])).fetchall()
            longest = int((n - min(r[0] for r in rows)) // 60) if rows else 0
            out.append({"section": x["code"], "waiting": len(rows), "longest_wait_minutes": longest, "open_counters": s._open(place, x["code"]),
                        "suggest_open_counter": longest > LONG_WAIT_MINUTES})          # LynkAssist only suggests; the manager decides
        counters = [dict(zip(("counter_id", "state", "staff", "serving"), r)) for r in s.db.execute("select counter_id, state, staff, serving from qu_counters where place=? order by rowid", (place,))]
        return {"sections": out, "counters": counters, "devices": s.devices(merchant, place), "keeper": s._place(place)["keeper"], "please_check": s.please_check(merchant, n)}
    def forecast(s, merchant, place, weekday, now=None):
        """Busy-hour forecast from the place's own past days: "Tomorrow 9:00 to 11:00 will be busy at LAB"."""
        if not s._ent(merchant)["busy_forecast"]: raise PermissionError("plan_no_busy_forecast")
        hours = {}
        for sec, issued in s.db.execute("select first_section, issued from qu_tickets where place=?", (place,)):
            t = time.gmtime(issued)
            if t.tm_wday == weekday: hours[(sec, t.tm_hour)] = hours.get((sec, t.tm_hour), 0) + 1
        if not hours: return []
        top = max(hours.values())
        return sorted(({"section": k[0], "hour": k[1], "tickets": v} for k, v in hours.items() if v * 2 >= top and v > 1), key=lambda r: (-r["tickets"], r["hour"]))
    def history(s, merchant, place=None, limit=200):
        q = "select at, by, what, ticket, place from qu_history where merchant=?" + (" and place=?" if place else "") + " order by rowid desc limit ?"
        return [dict(zip(("at", "by", "what", "ticket", "place"), r)) for r in s.db.execute(q, (merchant, place, limit) if place else (merchant, limit))]
    def report(s, merchant, place, from_at, to_at, by="section"):
        """By section, counter or hour: tickets, served, missed, left, not served today, the usual wait and the busiest hour."""
        ent, n = s._ent(merchant), to_at
        if by != "section" and ent["reports"] == "daily_summary": raise PermissionError("plan_daily_summary_only")
        if ent["history_months"] is not None and from_at < n - ent["history_months"] * 31 * DAY: from_at = n - ent["history_months"] * 31 * DAY
        key = {"section": "first_section", "counter": "counter", "hour": "cast(strftime('%H', issued, 'unixepoch') as int)"}[by]
        out = []
        for k, total, served, missed, left, nst, wait in s.db.execute(f"""select {key}, count(*), sum(state='served'), sum(state='missed'), sum(state='left'), sum(state='not_served_today'),
              avg(case when called is not null then (called - issued) / 60.0 end) from qu_tickets where merchant=? and place=? and issued>=? and issued<? group by 1 order by 1""", (merchant, place, from_at, to_at)):
            out.append({by: k, "tickets": total, "served": served or 0, "missed": missed or 0, "left": left or 0, "not_served_today": nst or 0, "average_wait_minutes": None if wait is None else round(wait)})
        busiest = s.db.execute("select cast(strftime('%H', issued, 'unixepoch') as int) h, count(*) c from qu_tickets where merchant=? and place=? and issued>=? and issued<? group by h order by c desc, h limit 1", (merchant, place, from_at, to_at)).fetchone()
        return {"rows": out, "busiest_hour": busiest[0] if busiest else None}
    def public_page(s, place):
        """The public queue page: "Now serving LAB-A2K9P2. 12 waiting. About 25 minutes." Ticket numbers only."""
        if not s._place(place)["public_page"]: return None
        out = []
        for w in s.see_wait(place):
            now_serving = [R.ticket_number(r[0], r[1]) for r in s.db.execute("select first_section, code from qu_tickets where place=? and section=? and state='called' order by called desc", (place, w["section"]))]
            out.append({**w, "now_serving": now_serving})
        return {"sections": out, "join_from": s._place(place)["join_from"]}
    def billable(s, merchant, month_start, month_end):
        """Only places that gave out at least one ticket that month are counted. A visit that uses Send to is one ticket."""
        ent = s._ent(merchant); rows = s.db.execute("select place, count(*) from qu_tickets where merchant=? and issued>=? and issued<? group by place", (merchant, month_start, month_end)).fetchall()
        extra_places = max(0, len(rows) - ent["places_included"]); paid = ent["extra_place_cents"] is not None
        over = sum(max(0, c - ent["tickets_per_place_month"]) for _, c in rows)
        return {"places": len(rows), "included": ent["places_included"], "extra_places": extra_places, "extra_place_cents": extra_places * (ent["extra_place_cents"] or 0),
                "tickets": sum(c for _, c in rows), "extra_tickets": over if paid else 0, "extra_ticket_cents": (-(-over // 1000)) * billing.SERVICE_FEES["queue_extra_1000_tickets_cents"] if paid else 0}


def _epoch(ts):
    from datetime import datetime
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
