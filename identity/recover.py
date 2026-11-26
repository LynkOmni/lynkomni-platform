"""The Can't sign in? hub (account.lynkomni.com/recover; section 4C point 5, master blueprint section 87). LynkOmni has no
passwords: wherever people expect "Forgot password?", the link says Can't sign in? and opens this hub. Rules only from
core/ways_in.py (catalog/ways-in.v1.json): the person picks what's wrong, the hub offers only the ways back in that person
actually has, strongest first, with their waits; every old contact and device is told at once with one Cancel button; after a
recovery come 24 hours of restricted time and then the security checkup. Never a password, security questions, a text alone,
an email alone, a call alone, or a support agent finishing it in chat. Events carry references only (identity/events.v1.json)."""
import json, secrets, time

from core import ways_in as WI
from core.secrethash import code_matches

HOUR, DAY = 3600, 86400
FINISHERS = ("self", "cloud")             # who may finish a recovery: the person on the new device, or the cloud's own timer


def _now(n):
    return time.time() if n is None else n


class RecoveryHub:
    def __init__(self, account):
        self.a, self.db = account, account.db
        self.db.executescript("""
        create table if not exists rh_recoveries(rid text primary key, person text, way text, new_device text, state text, started real, ready_at real,
                                                 approvals text, confirms text, cancelled_by text, done_at real);
        create table if not exists rh_failed(person text, at real);
        create table if not exists rh_strongest(person text primary key, until real);
        create table if not exists rh_watch(person text primary key, since real);""")

    def _lid(self, person):
        return self.a._lynkid(person)

    # ---- what the hub offers -------------------------------------------------------------------------------------------
    @staticmethod
    def problems():
        return list(WI.RECOVERY["problems"])

    def has(self, person, new_device=None):
        """The ways back in this person actually has."""
        out = {"id_check"}
        others = [s for s in self.a.sessions(person) if s["device_name"] != new_device]
        if others:
            out.add("other_device")
        if self.a.ways.backup_codes_left(person):
            out.add("backup_code")
        r = self.a.auth.db.execute("select recovery_hash,phone,email from identities where person=?", (person,)).fetchone()
        if r and r[0]:
            out.add("recovery_code")
        if r and r[1] and r[2]:
            out.add("email_and_phone")
        if len(self.a.ways.recovery_contacts(person)) >= WI.W["recovery_contacts"]["min"]:
            out.add("recovery_contacts")
        return out

    def ways(self, person, problem=None, new_device=None):
        """The ways offered, strongest first, each with its wait. "Someone else is in my account" locks everything first."""
        if problem is not None and problem not in WI.RECOVERY["problems"]:
            raise ValueError("pick what's wrong from the list")
        ways = WI.recovery_ways(self.has(person, new_device))
        first = ["lock_everything"] if problem == "someone_else" else []
        return {"first": first, "ways": ways, "never": list(WI.RECOVERY["never"])}

    # ---- starting a recovery --------------------------------------------------------------------------------------------
    def _proof_ok(self, person, way, proof, now):
        if way == "other_device":
            return bool(proof.get("approved_on_signed_in_device"))
        if way == "backup_code":
            return self.a.ways.use_backup_code(person, proof.get("code", ""), now)["ok"]
        if way == "recovery_code":
            r = self.a.auth.db.execute("select recovery_hash from identities where person=?", (person,)).fetchone()
            return bool(r and r[0] and code_matches(proof.get("code") or "", r[0]))
        if way == "email_and_phone":
            return bool(proof.get("email_code_ok") and proof.get("phone_code_ok"))        # both together, never one alone
        if way == "recovery_contacts":
            return True                                                                  # the contacts confirm during the wait
        if way == "id_check":
            return bool(proof.get("lover")) and self.a.identity_confirmed(person)         # the licensed partner's answer, cloud only
        return False

    def start(self, person, way, proof, new_device, now=None):
        if WI.never_allowed(way):
            raise PermissionError(f"LynkOmni never recovers an account by {way}")
        if way not in self.has(person, new_device):
            raise PermissionError("that way back in is not set up on this account")
        t = _now(now)
        if not self._proof_ok(person, way, proof or {}, now):
            self.db.execute("insert into rh_failed values(?,?)", (person, t)); self.db.commit()
            failed = self.db.execute("select count(*) from rh_failed where person=? and at>?", (person, t - DAY)).fetchone()[0]
            if WI.to_strongest(failed):
                until = t + WI.RECOVERY["strongest_days"] * DAY
                self.db.execute("insert or replace into rh_strongest values(?,?)", (person, until)); self.db.commit()
                self.a.emit(person, "RecoveryAttemptsBlocked", {"lynkid": self._lid(person), "until": until}, now)
                self.a.contact_notices.append({"kind": "every", "person": person, "message": "recovery_attempts_blocked"})
            raise PermissionError("that didn't match: check it and try again, or pick another way")
        wait = next(w for w in WI.RECOVERY["ways"] if w["id"] == way)["wait_h"] * HOUR
        rid = secrets.token_hex(8)
        self.db.execute("insert into rh_recoveries values(?,?,?,?,?,?,?,'[]','[]',null,null)", (rid, person, way, new_device, "waiting", t, t + wait)); self.db.commit()
        self.a.emit(person, "RecoveryStarted", {"lynkid": self._lid(person), "path": way, "recovery_id": rid, "ready_at": t + wait}, now)
        # every old contact and device is told at once, with one Cancel button and the anti-phishing word, never a code
        self.a.contact_notices.append({"kind": "every", "person": person, "message": "recovery_started", "actions": ["cancel_recovery"], "recovery_id": rid})
        if wait == 0:
            return self.complete(rid, "self", now)
        return {"recovery_id": rid, "state": "waiting", "ready_at": t + wait}

    def contact_confirms(self, rid, contact_lynkid, now=None):
        """A recovery contact confirms it's really the person (during the 24-hour wait)."""
        r = self._row(rid)
        if not r or r["way"] != "recovery_contacts" or r["state"] != "waiting":
            raise ValueError("no recovery is waiting for contacts")
        if contact_lynkid not in self.a.ways.recovery_contacts(r["person"]):
            raise PermissionError("only the person's own recovery contacts can confirm")
        c = sorted(set(json.loads(r["confirms"])) | {contact_lynkid})
        self.db.execute("update rh_recoveries set confirms=? where rid=?", (json.dumps(c), rid)); self.db.commit()
        return len(c)

    def staff_approves(self, rid, staff_id):
        """The ID check way needs two different LynkOmni staff; it is never finished in chat."""
        r = self._row(rid)
        if not r or r["way"] != "id_check":
            raise ValueError("only the ID check way needs staff")
        a = sorted(set(json.loads(r["approvals"])) | {staff_id})
        self.db.execute("update rh_recoveries set approvals=? where rid=?", (json.dumps(a), rid)); self.db.commit()
        self.a.c.store.append("_identity", staff_id, "audit.logged", {"action": "recovery_approved", "recovery_id": rid})
        return len(a)

    def _row(self, rid):
        r = self.db.execute("select rid,person,way,new_device,state,started,ready_at,approvals,confirms,cancelled_by,done_at from rh_recoveries where rid=?", (rid,)).fetchone()
        return dict(zip(("rid", "person", "way", "new_device", "state", "started", "ready_at", "approvals", "confirms", "cancelled_by", "done_at"), r)) if r else None

    # ---- cancelling and finishing ---------------------------------------------------------------------------------------
    def cancel(self, rid, by, now=None):
        """One Cancel button on every old contact and device stops it at once and switches on the unusual sign-in check."""
        if by not in ("old_device", "old_contact"):
            raise PermissionError("only an old device or an old contact can cancel")
        r = self._row(rid)
        if not r or r["state"] != "waiting":
            raise ValueError("nothing is waiting")
        self.db.execute("update rh_recoveries set state='cancelled', cancelled_by=? where rid=?", (by, rid))
        self.db.execute("insert or replace into rh_watch values(?,?)", (r["person"], _now(now))); self.db.commit()
        self.a.emit(r["person"], "RecoveryCancelled", {"lynkid": self._lid(r["person"]), "recovery_id": rid, "by": by}, now)
        return {"state": "cancelled", "unusual_check": True}

    def complete(self, rid, by, now=None):
        if by not in FINISHERS:
            raise PermissionError("a recovery is finished only by the person or the cloud, never by support or LynkAssist")
        r = self._row(rid)
        if not r or r["state"] != "waiting":
            raise ValueError("nothing is waiting")
        t = _now(now)
        if t < r["ready_at"]:
            raise PermissionError("the wait is not over yet")
        if r["way"] == "account_pin":
            self.db.execute("update rh_recoveries set state='done', done_at=? where rid=?", (t, rid)); self.db.commit()
            return {"recovery_id": rid, "state": "done", "next": "new_pin"}
        if r["way"] == "id_check" and len(json.loads(r["approvals"])) < next(w for w in WI.RECOVERY["ways"] if w["id"] == "id_check")["staff_approvals"]:
            raise PermissionError("two different LynkOmni staff must approve")
        if r["way"] == "recovery_contacts" and not WI.contacts_confirmed(json.loads(r["confirms"]), self.a.ways.recovery_contacts(r["person"])):
            raise PermissionError("not enough recovery contacts have confirmed yet")
        self.db.execute("update rh_recoveries set state='done', done_at=? where rid=?", (t, rid)); self.db.commit()
        until = t + WI.RECOVERY["restricted_h"] * HOUR
        self.a.emit(r["person"], "RecoveryCompleted", {"lynkid": self._lid(r["person"]), "recovery_id": rid, "restricted_until": until}, now)
        return {"recovery_id": rid, "state": "done", "restricted_until": until, "next": WI.RECOVERY["after"]}

    # ---- after and during ---------------------------------------------------------------------------------------------
    def _recovered_at(self, person):
        r = self.db.execute("select max(done_at) from rh_recoveries where person=? and state='done'", (person,)).fetchone()
        return r[0] if r else None

    def restricted(self, person, act, now=None):
        return WI.restricted(act, self._recovered_at(person), _now(now))

    def paused(self, person, what, now=None):
        """Payouts, cards and keys pause while a recovery waits and during its restricted time."""
        if what not in WI.RECOVERY["paused_during"]:
            return False
        waiting = self.db.execute("select 1 from rh_recoveries where person=? and state='waiting'", (person,)).fetchone() is not None
        done = self._recovered_at(person)
        return waiting or (done is not None and _now(now) - done < WI.RECOVERY["restricted_h"] * HOUR)

    def strongest(self, person, now=None):
        r = self.db.execute("select until from rh_strongest where person=?", (person,)).fetchone()
        return bool(r and r[0] > _now(now))

    def watched(self, person):
        return self.db.execute("select 1 from rh_watch where person=?", (person,)).fetchone() is not None

    def someone_else(self, person, verified, now=None):
        """"Someone else is in my account": Lock everything first, then recovery, then the activity log, with the security desk."""
        lock = self.a.protect.lock_everything(person, "not_me", verified, now)
        return {"lock": lock, "then": WI.RECOVERY["someone_else"][1:]}

    def lost_phone(self, username, proof_ok, now=None):
        """The I lost my phone page: lock everything without signing in, after a backup code, the recovery code or both
        contact codes. The answer is the same whether or not the username exists."""
        person = self.a.db.execute("select person from acct_people where username=?", (username,)).fetchone()
        if person and proof_ok:
            self.a.protect.lock_everything(person[0], "person", True, now)
        return {"state": "done_if_it_matched"}

    # ---- the account PIN of a basic phone ---------------------------------------------------------------------------
    def basic_pin_reset(self, person, by, proof_ok, now=None):
        """By menu number with a code to the phone and a 24-hour wait, or at once at a shop or agent point after the ID check.
        Returns when the new PIN may be set; the old PIN keeps working for the person until then, and they are told."""
        ok, why = WI.may_reset("account_pin", by)
        if not ok:
            raise PermissionError(why)
        if not proof_ok:
            raise PermissionError("the code or the ID check didn't match")
        wait = WI.RESETS["account_pin"]["wait_h"] * HOUR if by == "self" else 0
        rid = secrets.token_hex(8)
        t = _now(now)
        self.db.execute("insert into rh_recoveries values(?,?,?,?,?,?,?,'[]','[]',null,null)", (rid, person, "account_pin", None, "waiting", t, t + wait)); self.db.commit()
        self.a.contact_notices.append({"kind": "every", "person": person, "message": "recovery_started", "actions": ["cancel_recovery"], "recovery_id": rid})
        return {"recovery_id": rid, "new_pin_from": t + wait}

    def recoveries(self, person):
        return [{k: v for k, v in self._row(r[0]).items() if k not in ("approvals", "confirms")} for r in
                self.db.execute("select rid from rh_recoveries where person=? order by started desc", (person,))]
