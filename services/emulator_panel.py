"""The Emulator Panel, the cloud side (EMULATOR UPDATE, master blueprint section 70; build section 3A).

The one place where a manager gives emulators to devices, sees every device, emulator and user live, and connects or disconnects
them, for every service that has a dedicated screen (catalog/emulators.v1.json), on the workspace side and the Storefront side.
The rules (slots, the check before assigning, tones, the delivery menu) are in core/emulators.py.

Who may use it: the owner and the roles the owner chooses; a branch manager sees and acts only in their branch. A staff member
never connects their own device without approval. The device only asks (it answers a connect request, asks to be connected again,
signs a user in or out, reports its health); this service alone offers, connects, disconnects, locks, swaps and asks for
re-approval, each as a contract event with who did it. A PIN, a position or a person's name never goes into an event; the place
shown is the branch. No partner is needed, so the panel is on in every country.

States shown to people are only queued, sent, accepted, confirmed and failed."""
import hashlib, json, secrets, time

from contract.tools.validate_contract import uuid4
from core import emulators as R
from services import billing

DAY = 86400
LONG_OFFLINE_HOURS = 24
LOW_BATTERY_PCT = 15
MANY_UNSENT = 50
MANAGE_ROLES = ("owner", "manager")
ACTIONS = ("connect", "disconnect", "message", "lock", "swap", "test_print")
BUSY = ("payment", "cash_count", "signature", "pin")            # never viewed by anyone while the device is in one of these


def _now(n): return time.time() if n is None else n
def _day(n): return int(n // DAY)
def _hash(code): return hashlib.sha256(code.encode()).hexdigest()


class EmulatorPanel:
    def __init__(s, cloud, platform, notifier=None):
        s.cloud, s.p, s.db, s.n = cloud, platform, platform.c.store.db, notifier
        s.seq = secrets.randbelow(R.Q.CAPACITY)                 # assignment codes walk the Lynk Alphabet from a random start
        s.db.executescript("""
        create table if not exists em_roles(merchant text, person text, role text, branch text, primary key(merchant, person));
        create table if not exists em_devices(device_id text primary key, merchant text, branch text, name text, lynk_name text, os text, caps text,
          last_seen real, lost int, removed int, reapprove int, tag text, station text, staff_own int, busy text);
        create table if not exists em_offers(assignment_id text primary key, merchant text, emulator text, code_hash text, issued real, used int,
          device_id text, way text, temporary_until_day int, practice int, by text, side text, state text);
        create table if not exists em_conn(device_id text, emulator text, merchant text, connected int, practice int, extra_slot int, since real,
          temporary_until_day int, pending text, to_kind text, user_id text, side text, primary key(device_id, emulator));
        create table if not exists em_usage(device_id text, emulator text, user_id text, since real, until real);
        create table if not exists em_health(device_id text primary key, online int, unsent int, battery int, printer text, morning text, at real);
        create table if not exists em_extra(merchant text, family text, n int, primary key(merchant, family));
        create table if not exists em_settings(device_id text primary key, tones int, vibration int, volume text, user_may_change int, pin_same_tone int);
        create table if not exists em_seen(event_id text primary key);
        create table if not exists em_pass(merchant text, family text, devices int, until_day int);
        create table if not exists em_grace(merchant text, family text, until_day int, primary key(merchant, family));
        create table if not exists em_history(merchant text, at real, by text, what text, device_id text, emulator text);""")

    # ---- who may use the panel -------------------------------------------------------------------------------------------
    def add_role(s, merchant, person, role="owner", branch=None, by=None):
        if role not in MANAGE_ROLES + ("staff",): raise ValueError("unknown role")
        if role != "owner" and by is not None: s._need(merchant, by)
        s.db.execute("insert or replace into em_roles values(?,?,?,?)", (merchant, person, role, branch)); s.db.commit()
    def _role(s, merchant, person):
        return s.db.execute("select role, branch from em_roles where merchant=? and person=?", (merchant, person)).fetchone()
    def _need(s, merchant, person, branch=None):
        r = s._role(merchant, person)
        if not r or r[0] not in MANAGE_ROLES: raise PermissionError("only_the_owner_and_chosen_roles")
        if r[1] and branch and r[1] != branch: raise PermissionError("other_branch")
        return r
    def _log(s, merchant, by, what, device=None, emulator=None, now=None):
        s.db.execute("insert into em_history values(?,?,?,?,?,?)", (merchant, _now(now), by, what, device, emulator))
    def _tell(s, kind, person, event_id, now, record=None, business=None, role=None):
        if s.n: return s.n.notify(kind, person, event_id, _now(now), record=record, business=business, role=role)
    def _managers(s, merchant, branch=None):
        return [r[0] for r in s.db.execute("select person, branch from em_roles where merchant=? and role in ('owner','manager')", (merchant,)) if not r[1] or not branch or r[1] == branch]

    # ---- devices -----------------------------------------------------------------------------------------------------------
    def add_device(s, merchant, branch, name, lynk_name, os_name="android", caps=None, staff_own=False, now=None):
        """A device known to the business (enrolled through the device rules, identity/device_session.py). caps: what it can do."""
        if lynk_name not in R.DEVICE_NAMES: raise ValueError("unknown device name")
        did = uuid4()
        s.db.execute("insert into em_devices values(?,?,?,?,?,?,?,?,0,0,0,null,null,?,null)",
                     (did, merchant, branch, name, lynk_name, os_name, json.dumps(caps or {}), _now(now), int(staff_own)))
        s.db.commit(); return did
    def _dev(s, device):
        r = s.db.execute("select merchant, branch, name, lynk_name, os, caps, last_seen, lost, removed, reapprove, tag, station, staff_own, busy from em_devices where device_id=?", (device,)).fetchone()
        if not r: raise KeyError("no such device")
        d = dict(zip(("merchant", "branch", "name", "lynk_name", "os", "caps", "last_seen", "lost", "removed", "reapprove", "tag", "station", "staff_own", "busy"), r))
        d["caps"] = json.loads(d["caps"]); return d

    # ---- giving an emulator to a device (70.4) ------------------------------------------------------------------------------
    def check(s, device, emulator):
        """The check before assigning: what the device can do against what the emulator needs (core/emulators.can_run)."""
        d = s._dev(device)
        return R.can_run(emulator, dict(d["caps"], os=d["os"]))
    def offer(s, merchant, emulator, by, branch=None, way="code", device=None, temporary_until_day=None, practice=False, side="internal", now=None):
        """Add a device: a QR code, a 6-character Lynk Code and a link that work once and expire after core.emulators.CODE_MINUTES.
        The code is shown once and never stored or sent in an event (only its hash is kept)."""
        s._need(merchant, by, branch)
        if emulator not in R.EMULATORS: raise KeyError("no such emulator")
        e = R.EMULATORS[emulator]
        if e["planned"]: raise PermissionError("built_in_a_later_section")
        if side not in e["checks"]["sides"]: raise PermissionError("not_on_this_side")
        if device:
            chk = s.check(device, emulator)
            if not chk["ok"]: return {"state": "failed", "reason": chk["refused"]}
        s.seq += 1
        code, aid, n = R.new_code(s.seq), uuid4(), _now(now)
        s.db.execute("insert into em_offers values(?,?,?,?,?,0,?,?,?,?,?,?,'sent')",
                     (aid, merchant, emulator, _hash(code), n, device, way, temporary_until_day, int(practice), by, side))
        p = {"assignment_id": aid, "emulator": emulator, "way": way, "expires_in_minutes": R.CODE_MINUTES}
        if temporary_until_day is not None: p["temporary_until_day"] = temporary_until_day
        if device: p["device_id"] = device
        if side == "external": p["side"] = "external"
        s.cloud.event(merchant, "EmulatorOffered", p, now=n)
        s._log(merchant, by, "offered", device, emulator, now); s.db.commit()
        return {"state": "sent", "assignment_id": aid, "code": code, "link": f"https://app.lynkomni.com/business/emulators?code={code}"}
    def lookup(s, code, now=None):
        """What the device shows before Accept or Deny: which business, which emulator, who sent it. Online only (class C)."""
        r = s.db.execute("select assignment_id, merchant, emulator, issued, used, by, side from em_offers where code_hash=?", (_hash(code.strip().upper()),)).fetchone()
        if not r or not R.code_valid(r[3], _now(now), bool(r[4])): return {"state": "failed", "reason": "code_expired_or_used"}
        return {"state": "sent", "assignment_id": r[0], "merchant": r[1], "emulator": r[2], "sent_by": r[5], "side": r[6]}
    def guided_setup(s, merchant, service, by, branch=None, now=None):
        """"Set up my queue" (and the like): one offer for each of the service's built emulators, walked through one by one."""
        out = []
        for e in R.REG["emulators"]:
            if e["service"] == service and not e["planned"] and not e["shared_with"]:
                o = s.offer(merchant, e["id"], by, branch=branch, way="guided_setup", now=now); out.append({"emulator": e["id"], **o})
        return out

    # ---- device answers and the cloud connects -----------------------------------------------------------------------------
    def ingest(s, merchant, evt, now=None):
        """A device fact that reached the cloud: a connect answer, Connect request, user change, settings change or health report."""
        t, p, n = evt["type"], evt["payload"], _now(now)
        if s.db.execute("select 1 from em_seen where event_id=?", (evt["event_id"],)).fetchone(): return {"state": "duplicate"}
        s.db.execute("insert into em_seen values(?)", (evt["event_id"],))
        s.cloud.device_event(merchant, evt, now=n)
        dev = p.get("device_id") or evt.get("device_id")
        out = {"state": "accepted"}
        if t == "EmulatorRequestAnswered": out = s._answered(merchant, p, n)
        elif t == "EmulatorConnectAsked": pass                                     # LynkFlow tells the managers (emulator-connect-asked)
        elif t == "EmulatorUserChanged": s._user_changed(dev, p, n)
        elif t == "EmulatorSettingsChanged": s._save_settings(dev, p)
        elif t == "DeviceHealthReported": s._health(merchant, dev, p, evt["event_id"], n)
        s.db.execute("update em_devices set last_seen=?, reapprove=0 where device_id=? and reapprove=0", (n, dev))
        s.db.commit(); return out
    def _answered(s, merchant, p, n):
        r = s.db.execute("select merchant, emulator, issued, used, device_id, temporary_until_day, practice, by, side from em_offers where assignment_id=?", (p["assignment_id"],)).fetchone()
        if not r or r[0] != merchant: return {"state": "failed", "reason": "no_such_request"}
        if not R.code_valid(r[2], n, bool(r[3])):
            s.db.execute("update em_offers set state='failed' where assignment_id=?", (p["assignment_id"],)); return {"state": "failed", "reason": "code_expired_or_used"}
        s.db.execute("update em_offers set used=1, device_id=? where assignment_id=?", (p["device_id"], p["assignment_id"]))
        if p["answer"] == "deny":
            s.db.execute("update em_offers set state='failed' where assignment_id=?", (p["assignment_id"],)); return {"state": "failed", "reason": "denied"}
        chk = s.check(p["device_id"], r[1])
        if not chk["ok"]: return {"state": "failed", "reason": chk["refused"]}
        return s._connect(merchant, p["device_id"], r[1], r[7], assignment=p["assignment_id"], practice=bool(r[6]), temporary=r[5], side=r[8], now=n)
    def _connect(s, merchant, device, emulator, by, assignment=None, practice=False, temporary=None, side="internal", now=None):
        d = s._dev(device)
        if d["lost"] or d["removed"]: return {"state": "failed", "reason": "device_lost_or_removed"}
        if d["reapprove"]: return {"state": "failed", "reason": "reapproval_needed"}
        fam = R.counts_for(emulator)
        extra = 0
        if fam:
            limit = R.slots(fam, s.p.billing.tier(merchant, fam))
            ok, why = R.may_connect(limit, fam, s._connections(merchant), {"device": device, "emulator": emulator, "practice": practice},
                                     s._extra(merchant, fam) + s._passes(merchant, fam, _day(_now(now))))
            if not ok: return {"state": "failed", "reason": why, "family": fam}
            extra = int(isinstance(limit, int) and R.in_use(fam, s._connections(merchant) + [{"device": device, "emulator": emulator, "connected": True}]) > limit)
        n = _now(now)
        s.db.execute("insert or replace into em_conn values(?,?,?,1,?,?,?,?,null,'nobody',null,?)", (device, emulator, merchant, int(practice), extra, n, temporary, side))
        if assignment: s.db.execute("update em_offers set state='confirmed' where assignment_id=?", (assignment,))
        p = {"assignment_id": assignment or uuid4(), "device_id": device, "emulator": emulator}
        if practice: p["practice"] = True
        if extra: p["extra_slot"] = True
        if side == "external": p["side"] = "external"
        s.cloud.event(merchant, "EmulatorConnected", p, now=n)
        s._log(merchant, by, "connected", device, emulator, now); s.db.commit()
        return {"state": "confirmed", "device_id": device, "emulator": emulator}
    def _connections(s, merchant):
        return [{"device": r[0], "emulator": r[1], "connected": bool(r[2]), "practice": bool(r[3])}
                for r in s.db.execute("select device_id, emulator, connected, practice from em_conn where merchant=?", (merchant,))]
    def _passes(s, merchant, family, today):
        r = s.db.execute("select coalesce(sum(devices),0) from em_pass where merchant=? and family=? and until_day>=?", (merchant, family, today)).fetchone()
        return r[0]
    def _extra(s, merchant, family):
        r = s.db.execute("select n from em_extra where merchant=? and family=?", (merchant, family)).fetchone(); return r[0] if r else 0

    # ---- connect and disconnect (70.7) -------------------------------------------------------------------------------------
    def connect(s, merchant, devices, emulator, by, practice=False, now=None):
        """Connect switches the service on for one device, several or a branch (one tap). Practice mode (the staff coach) never
        counts against the plan and nothing it does is real."""
        out = []
        for d in devices:
            s._need(merchant, by, s._dev(d)["branch"]); out.append(s._connect(merchant, d, emulator, by, practice=practice, now=now))
        return out
    def disconnect(s, merchant, devices, by, emulator=None, reason="manager", now=None):
        """Safe disconnect: the device finishes what it is doing and first sends its unsent records. Online, it is done at once;
        offline, it is "sent" until the device next reaches the cloud. The panel shows how many records are still to come."""
        out = []
        for d in devices:
            if reason == "manager": s._need(merchant, by, s._dev(d)["branch"])
            h = s._health_of(d)
            for (em,) in s.db.execute("select emulator from em_conn where device_id=? and connected=1" + (" and emulator=?" if emulator else ""), (d, emulator) if emulator else (d,)).fetchall():
                if h["online"]: out.append(s._disconnected(merchant, d, em, reason, h["unsent"], by, now))
                else:
                    s.db.execute("update em_conn set pending=? where device_id=? and emulator=?", (reason, d, em))
                    out.append({"state": "sent", "device_id": d, "emulator": em, "unsent": h["unsent"]})
        s.db.commit(); return out
    def _disconnected(s, merchant, device, emulator, reason, unsent, by, now):
        s.db.execute("update em_conn set connected=0, pending=null where device_id=? and emulator=?", (device, emulator))
        s.db.execute("update em_usage set until=? where device_id=? and emulator=? and until is null", (_now(now), device, emulator))
        s.cloud.event(merchant, "EmulatorDisconnected", {"device_id": device, "emulator": emulator, "reason": reason, "unsent": unsent}, now=now)
        s._log(merchant, by, f"disconnected_{reason}", device, emulator, now)
        return {"state": "confirmed", "device_id": device, "emulator": emulator, "unsent": unsent}
    def device_view(s, device, emulator):
        """What the emulator shows when opened from its icon: connected, or the plain disconnected message with Connect request."""
        r = s.db.execute("select connected, pending, practice from em_conn where device_id=? and emulator=?", (device, emulator)).fetchone()
        d = s._dev(device)
        if d["lost"]: return {"screen": "locked_lost"}
        if d["reapprove"]: return {"screen": "reapproval"}
        if not r: return {"screen": "not_assigned"}
        if not r[0]: return {"screen": "disconnected", "ask": True}
        return {"screen": "practice" if r[2] else "ready"}
    def mark_lost(s, merchant, device, by, found=False, now=None):
        """Mark as lost locks every emulator on the device (a wipe stays with the owner alone, after a fresh check)."""
        s._need(merchant, by, s._dev(device)["branch"])
        s.db.execute("update em_devices set lost=? where device_id=?", (int(not found), device))
        p = {"device_id": device}
        if found: p["found"] = True
        s.cloud.event(merchant, "DeviceMarkedLost", p, now=now); s._log(merchant, by, "found" if found else "lost", device, None, now); s.db.commit()
        return {"state": "confirmed"}
    def swap(s, merchant, from_device, to_device, emulator, by, now=None):
        """Moves an emulator with its name, settings and printers to another device; the old one is disconnected first."""
        s._need(merchant, by, s._dev(from_device)["branch"])
        chk = s.check(to_device, emulator)
        if not chk["ok"]: return {"state": "failed", "reason": chk["refused"]}
        r = s.db.execute("select practice, side from em_conn where device_id=? and emulator=?", (from_device, emulator)).fetchone()
        if not r: return {"state": "failed", "reason": "not_on_that_device"}
        s.cloud.event(merchant, "EmulatorSwapStarted", {"from_device_id": from_device, "to_device_id": to_device, "emulator": emulator}, now=now)
        s._disconnected(merchant, from_device, emulator, "swapped", s._health_of(from_device)["unsent"], by, now)
        st = s.db.execute("select tones, vibration, volume, user_may_change, pin_same_tone from em_settings where device_id=?", (from_device,)).fetchone()
        if st: s.db.execute("insert or replace into em_settings values(?,?,?,?,?,?)", (to_device, *st))
        name = s._dev(from_device)["name"]; s.db.execute("update em_devices set name=? where device_id=?", (name, to_device))
        res = s._connect(merchant, to_device, emulator, by, practice=bool(r[0]), side=r[1], now=now)
        if res["state"] == "confirmed":
            s.cloud.event(merchant, "EmulatorSwapped", {"from_device_id": from_device, "to_device_id": to_device, "emulator": emulator}, now=now)
        s.db.commit(); return res
    def remove(s, merchant, device, by, now=None):
        """Remove a device: every emulator is disconnected; its history is kept."""
        s.disconnect(merchant, [device], by, reason="removed", now=now)
        s.db.execute("update em_devices set removed=1 where device_id=?", (device,)); s.db.commit()
    def approve_again(s, merchant, device, by, now=None):
        s._need(merchant, by, s._dev(device)["branch"])
        s.db.execute("update em_devices set reapprove=0, last_seen=? where device_id=?", (_now(now), device))
        s.cloud.event(merchant, "DeviceApprovedAgain", {"device_id": device}, now=now); s._log(merchant, by, "approved_again", device, None, now); s.db.commit()
    def carry_on(s, user, from_device, to_device):
        """Carry on from another device: the open sale or ticket continues on the spare once the first device's records have
        reached the cloud ("confirmed"); until then it waits ("sent") and nothing is doubled."""
        return {"state": "confirmed" if s._health_of(from_device)["unsent"] == 0 else "sent"}

    # ---- the daily housekeeping (LynkFlow: emulator-daily) -------------------------------------------------------------------
    def daily(s, merchant=None, now=None):
        """Ends temporary emulators, asks for re-approval of devices not seen for core.emulators.REAPPROVE_DAYS, and raises the
        long-offline alert."""
        n, today, out = _now(now), _day(_now(now)), {"ended": 0, "reapproval": 0, "offline_alerts": 0, "over_plan": 0}
        only, arg = (" and merchant=?", (merchant,)) if merchant else ("", ())
        for dev, em, m in s.db.execute("select device_id, emulator, merchant from em_conn where connected=1 and temporary_until_day is not null and temporary_until_day < ?" + only, (today,) + arg).fetchall():
            s._disconnected(m, dev, em, "temporary_ended", s._health_of(dev)["unsent"], "lynkflow", now); out["ended"] += 1
        for m in ([merchant] if merchant else [r[0] for r in s.db.execute("select distinct merchant from em_grace")]):
            out["over_plan"] += s._grace_ended(m, today, now)
        for dev, merchant, last, branch in s.db.execute("select device_id, merchant, last_seen, branch from em_devices where removed=0 and reapprove=0" + only, arg).fetchall():
            if R.reapproval_due(_day(last), today):
                s.db.execute("update em_devices set reapprove=1 where device_id=?", (dev,))
                eid = s.cloud.event(merchant, "EmulatorReapprovalNeeded", {"device_id": dev, "days": today - _day(last)}, now=n)
                for mg in s._managers(merchant, branch): s._tell("emulator_reapproval", mg, eid, n, record=dev, business=merchant, role="manager")
                out["reapproval"] += 1
            elif n - last >= LONG_OFFLINE_HOURS * 3600 and s.db.execute("select 1 from em_conn where device_id=? and connected=1", (dev,)).fetchone():
                out["offline_alerts"] += 1
        s.db.commit(); return out

    # ---- users, history and the live view (70.8) -----------------------------------------------------------------------------
    def assign_to(s, merchant, device, emulator, by, to="person", user_id=None, now=None):
        s._need(merchant, by, s._dev(device)["branch"])
        if R.EMULATORS[emulator]["user"] == "none" and to != "nobody": raise PermissionError("customer_facing_needs_no_user")
        s.db.execute("update em_conn set to_kind=?, user_id=? where device_id=? and emulator=?", (to, user_id, device, emulator))
        p = {"device_id": device, "emulator": emulator, "to": to}
        if user_id: p["user_id"] = user_id
        s.cloud.event(merchant, "EmulatorAssignedTo", p, now=now); s.db.commit()
    def _user_changed(s, device, p, n):
        if p["change"] in ("signed_out", "idle_signed_out", "switched"):
            s.db.execute("update em_usage set until=? where device_id=? and emulator=? and until is null", (n, device, p["emulator"]))
        if p["change"] in ("signed_in", "switched") and p.get("user_id"):
            s.db.execute("insert into em_usage values(?,?,?,?,null)", (device, p["emulator"], p["user_id"], n))
    def history(s, merchant, by=None, user_id=None):
        """Who used which emulator on which device, from when to when; a staff member sees their own in their account."""
        if by: s._need(merchant, by)
        q = "select u.device_id, d.name, d.branch, u.emulator, u.user_id, u.since, u.until from em_usage u join em_devices d on d.device_id=u.device_id where d.merchant=?"
        args = [merchant] + ([user_id] if user_id else [])
        rows = s.db.execute(q + (" and u.user_id=?" if user_id else "") + " order by u.since desc", args).fetchall()
        return [dict(zip(("device_id", "device", "branch", "emulator", "user_id", "since", "until"), r)) for r in rows]
    def _health(s, merchant, device, p, eid, n):
        s.db.execute("insert or replace into em_health values(?,?,?,?,?,?,?)", (device, int(p["online"]), p["unsent"], p.get("battery_pct"), p.get("printer"), p.get("morning_check"), n))
        for (em, reason) in s.db.execute("select emulator, pending from em_conn where device_id=? and pending is not null", (device,)).fetchall():
            if p["online"]: s._disconnected(merchant, device, em, reason, p["unsent"], "cloud", n)       # a disconnect made while offline lands now

    # ---- what LynkFlow runs (catalog/automations.v1.json: emulator-connect-asked, emulator-device-alert, emulator-daily) --------
    def connect_asked(s, merchant, device, event_id, now=None):
        told = [mg for mg in s._managers(merchant, s._dev(device)["branch"])]
        for mg in told: s._tell("emulator_connect_asked", mg, event_id, _now(now), record=device, business=merchant, role="manager")
        return told
    @staticmethod
    def needs_alert(p):
        """A health report worth a manager's look: paper out or low, a low battery, many unsent records or a failed morning check."""
        return [w for w, hit in (("printer", p.get("printer") in ("out_of_paper", "paper_low")),
                                 ("battery", p.get("battery_pct") is not None and p["battery_pct"] <= LOW_BATTERY_PCT),
                                 ("unsent", p.get("unsent", 0) >= MANY_UNSENT), ("morning_check", p.get("morning_check") == "failed")) if hit]
    def device_alert(s, merchant, device, p, event_id, now=None):
        why = s.needs_alert(p)
        if not why: return []
        told = s._managers(merchant, s._dev(device)["branch"])
        for mg in told: s._tell("emulator_device_alert", mg, event_id, _now(now), record=device, business=merchant, role="manager")
        return why
    def _health_of(s, device):
        r = s.db.execute("select online, unsent, battery, printer, morning, at from em_health where device_id=?", (device,)).fetchone()
        return dict(zip(("online", "unsent", "battery", "printer", "morning", "at"), r)) if r else {"online": 1, "unsent": 0, "battery": None, "printer": None, "morning": None, "at": None}
    def live(s, merchant, by, query="", now=None):
        """The live list: device name and kind, its emulators and their state, the user now and since when, health, and the actions."""
        r = s._need(merchant, by)
        out = []
        for row in s.db.execute("select device_id, name, lynk_name, branch, lost, removed, reapprove, station, tag from em_devices where merchant=? and removed=0 order by name", (merchant,)).fetchall():
            dev, name, kind, branch, lost, _, reapp, station, tag = row
            if r[1] and branch != r[1]: continue                       # a branch manager sees only their branch
            if query and query.lower() not in (name or "").lower(): continue
            ems = []
            for em, conn, practice, pending, user, side in s.db.execute("select emulator, connected, practice, pending, user_id, side from em_conn where device_id=?", (dev,)).fetchall():
                since = s.db.execute("select since from em_usage where device_id=? and emulator=? and until is null", (dev, em)).fetchone()
                state = "lost" if lost else "reapproval" if reapp else ("disconnect_sent" if pending else "connected" if conn else "disconnected")
                ems.append({"emulator": em, "state": state, "practice": bool(practice), "user_id": user, "user_since": since[0] if since else None, "side": side})
            out.append({"device_id": dev, "name": name, "kind": kind, "branch": branch, "station": station, "tag": tag, "emulators": ems,
                        "health": s._health_of(dev), "actions": list(ACTIONS)})
        return out

    # ---- tones and vibration (70.6), the plan (70.12) ------------------------------------------------------------------------
    def set_tones(s, merchant, device, by, tones=True, vibration=True, volume="medium", user_may_change=True, pin_same_tone=False, now=None):
        s._need(merchant, by, s._dev(device)["branch"])
        s._save_settings(device, {"tones": tones, "vibration": vibration, "volume": volume, "pin_same_tone": pin_same_tone}, user_may_change)
        s.cloud.event(merchant, "EmulatorSettingsChanged", {"device_id": device, "tones": tones, "vibration": vibration, "volume": volume,
                                                            "pin_same_tone": pin_same_tone, "by": "manager"}, now=now); s.db.commit()
    def _save_settings(s, device, p, user_may_change=None):
        old = s.db.execute("select user_may_change from em_settings where device_id=?", (device,)).fetchone()
        may = int(user_may_change if user_may_change is not None else (old[0] if old else 1))
        s.db.execute("insert or replace into em_settings values(?,?,?,?,?,?)", (device, int(p["tones"]), int(p["vibration"]), p["volume"], may, int(p.get("pin_same_tone", False))))
    def tones_for(s, device, emulator, user=None, silent=False, quiet_hours=False):
        r = s.db.execute("select tones, vibration, volume, user_may_change, pin_same_tone from em_settings where device_id=?", (device,)).fetchone()
        mgr = dict(zip(("tones", "vibration", "volume", "user_may_change", "pin_same_tone"), r)) if r else {}
        caps = s._dev(device)["caps"]
        return R.tones(mgr, user, R.EMULATORS[emulator]["customer_facing"], silent, quiet_hours, caps.get("vibration", True))
    def usage(s, merchant, by, now=None):
        """What is counted: per family, the staff slots in use, the plan's number, extra slots and a hint when the plan is larger
        than needed. Customer-facing screens and practice mode are listed apart and never counted."""
        s._need(merchant, by)
        conns, out = s._connections(merchant), {}
        for fam in sorted({R.counts_for(e) for e in R.EMULATORS if R.counts_for(e)}):
            limit = R.slots(fam, s.p.billing.tier(merchant, fam))
            used = R.in_use(fam, conns)
            out[fam] = {"in_use": used, "limit": limit, "extra": s._extra(merchant, fam), "extra_slot_cents": R.extra_slot_cents(fam), "day_passes": s._passes(merchant, fam, _day(_now(now))),
                        "cheaper_tier": R.cheaper_tier(fam, s.p.billing.tier(merchant, fam), s._extra(merchant, fam)),
                        "larger_than_needed": isinstance(limit, int) and limit >= 5 and used <= 2}
        out["free_screens"] = sum(1 for c in conns if c["connected"] and R.counts_for(c["emulator"]) is None)
        out["practice"] = sum(1 for c in conns if c["connected"] and c["practice"])
        return out
    def buy_extra_slot(s, merchant, family, by, n=1):
        """One more staff device a month at the family's price (billing.EMULATOR_EXTRA_CENTS), on Plus and Pro. The answer says when
        the next tier would cost less (never upgrades by itself)."""
        s._need(merchant, by)
        tier = s.p.billing.tier(merchant, family)
        if tier == "free": raise PermissionError("extra_slots_on_paid_tiers")
        if not isinstance(R.slots(family, tier), int) or R.extra_slot_cents(family) is None: raise PermissionError("no_slot_limit_on_this_plan")
        s.db.execute("insert into em_extra values(?,?,?) on conflict(merchant, family) do update set n=n+?", (merchant, family, n, n)); s.db.commit()
        ex = s._extra(merchant, family)
        return {"extra": ex, "monthly_cents": ex * R.extra_slot_cents(family), "cheaper_tier": R.cheaper_tier(family, tier, ex)}
    def buy_day_pass(s, merchant, family, by, devices=1, days=1, now=None):
        """A day pass: one more staff device for an event or a market day, on any tier, for at most core.emulators.day_pass_max_days()
        days; it ends by itself (the daily housekeeping takes it back)."""
        s._need(merchant, by)
        if not 1 <= days <= R.day_pass_max_days() or devices < 1: raise ValueError("day_pass_days")
        if not isinstance(R.slots(family, s.p.billing.tier(merchant, family)), int): raise PermissionError("no_slot_limit_on_this_plan")
        until = _day(_now(now)) + days - 1
        s.db.execute("insert into em_pass values(?,?,?,?)", (merchant, family, devices, until)); s.db.commit()
        return {"devices": devices, "until_day": until, "cents": devices * days * R.day_pass_cents()}
    def after_downgrade(s, merchant, family, now=None):
        """After a downgrade the owner chooses which devices to disconnect; nothing is cut off for core.emulators.DOWNGRADE_GRACE_DAYS
        days, then the daily housekeeping disconnects the most recently connected ones still over the plan (reason "plan")."""
        out = R.downgrade(R.slots(family, s.p.billing.tier(merchant, family)), family, s._connections(merchant))
        if out["to_disconnect"]:
            s.db.execute("insert or replace into em_grace values(?,?,?)", (merchant, family, _day(_now(now)) + out["grace_days"])); s.db.commit()
        return out
    def _grace_ended(s, merchant, today, now):
        n = 0
        for (family,) in s.db.execute("select family from em_grace where merchant=? and until_day <= ?", (merchant, today)).fetchall():
            over = R.downgrade(R.slots(family, s.p.billing.tier(merchant, family)), family, s._connections(merchant))["to_disconnect"]
            rows = s.db.execute("select device_id, emulator from em_conn where merchant=? and connected=1 and practice=0 order by since desc", (merchant,)).fetchall()
            for dev, em in [r for r in rows if R.counts_for(r[1]) == family][:over]:
                s._disconnected(merchant, dev, em, "plan", s._health_of(dev)["unsent"], "lynkflow", now); n += 1
            s.db.execute("delete from em_grace where merchant=? and family=?", (merchant, family))
        return n

    # ---- see the screen to help (70.8) ---------------------------------------------------------------------------------------
    def set_busy(s, device, busy=None):
        """The device says when it is in a payment, cash count, signature or PIN entry (nobody may view its screen then)."""
        s.db.execute("update em_devices set busy=? where device_id=?", (busy, device)); s.db.commit()
    def view_screen(s, merchant, device, by, viewer="manager", consent_id=None, now=None):
        """Only with the user's consent (support through its time-limited consent record); never during a payment, cash count,
        signature or PIN; the user sees that viewing is on (message emulator_screen_view)."""
        if viewer == "manager": s._need(merchant, by, s._dev(device)["branch"])
        d, n = s._dev(device), _now(now)
        change = "refused" if (not consent_id or d["busy"] in BUSY) else "started"
        p = {"device_id": device, "change": change, "viewer": viewer}
        if consent_id: p["consent_id"] = consent_id
        eid = s.cloud.event(merchant, "ScreenViewChanged", p, now=n)
        user = s.db.execute("select user_id from em_usage where device_id=? and until is null", (device,)).fetchone()
        if change == "started" and user: s._tell("emulator_screen_view", user[0], eid, n, record=device, business=merchant, role="staff")
        s.db.commit(); return {"state": "confirmed" if change == "started" else "failed", "reason": None if change == "started" else ("no_consent" if not consent_id else "busy")}
    def end_view(s, merchant, device, viewer="manager", consent_id=None, now=None):
        p = {"device_id": device, "change": "ended", "viewer": viewer}
        if consent_id: p["consent_id"] = consent_id
        s.cloud.event(merchant, "ScreenViewChanged", p, now=now); s.db.commit()

    # ---- stations and groups -------------------------------------------------------------------------------------------------
    def link_station(s, merchant, devices, station, by):
        """Devices that work as one set (a till, its customer display and kitchen screen) are linked and shown together."""
        for d in devices:
            s._need(merchant, by, s._dev(d)["branch"]); s.db.execute("update em_devices set station=? where device_id=?", (station, d))
        s.db.commit()
    def tag(s, merchant, devices, tag, by):
        for d in devices:
            s._need(merchant, by, s._dev(d)["branch"]); s.db.execute("update em_devices set tag=? where device_id=?", (tag, d))
        s.db.commit()
    def group(s, merchant, tag):
        return [r[0] for r in s.db.execute("select device_id from em_devices where merchant=? and tag=? and removed=0", (merchant, tag))]
