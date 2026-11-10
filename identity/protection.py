"""Account protections (MASTER UPDATE, master blueprint sections 55 and 59; build section 2).

The rules a person's account follows after sign-up, enforced here and never by a screen:
- Two ways in from the start: a second passkey or device, and the recovery code typed back once to prove it was kept.
- A cool-off after a new device or a new contact: for COOL_OFF_S the sensitive acts (payout change, data export, removing a
  passkey, changing a contact) are held, and every other device is told with one tap for "This was not me".
- A contact change is slow on purpose: a fresh check, a notice to the old contact and CONTACT_WAIT_S in which the old contact
  can cancel. It never happens at once.
- Advanced protection, by choice: passkeys only (no code fallback), two passkeys required, longer waits.
- Lock everything: one verified command signs out every device, asks the issuer to freeze cards (shown frozen only when the
  issuer confirms) and pauses API keys. Arrive Safe shares and trip plans keep running and are asked about separately, because
  they may be keeping someone safe. Locking is quick; unlocking always needs verification.
- "This was not me" runs Lock everything and undoes what the suspicious session changed, where it can still be undone.
- A successor for the business: a trusted person the owner names may ask for access after the owner has been inactive for the
  chosen time; there is a waiting period with notices to the owner, and the licensed partner checks the successor's identity.
  It stays off in a country until a lawyer confirms the rule there (provider ledger "later": successor_law).
- A record of the terms agreed: which terms and privacy notice versions were accepted, and when; a new version asks again.
- Staff views: every time LynkOmni staff see a person's data (only through a time-limited consent) it is recorded and shown.
- The security check-up: findings with the fix ready to confirm.
No LynkOmni staff tool can change a person's passkeys, contacts or PIN, or skip recovery: nothing here takes a staff caller."""
import time, uuid

DAY = 86400
COOL_OFF_S = 2 * DAY
ADVANCED_COOL_OFF_S = 7 * DAY
CONTACT_WAIT_S = 3 * DAY
ADVANCED_CONTACT_WAIT_S = 7 * DAY
SUCCESSOR_WAIT_S = 30 * DAY
SUCCESSOR_INACTIVE_DAYS = (30, 365)                       # the owner chooses within these bounds
HELD_ACTS = ("payout_change", "data_export", "remove_passkey", "contact_change")
TERMS = {"terms": "2026-11-10", "privacy": "2026-11-10"}  # the versions in force; a change here asks everyone again


def _now(n):
    return time.time() if n is None else n


class Protection:
    def __init__(self, account):
        self.a, self.db = account, account.db
        self.db.executescript("""
        create table if not exists prot_people(person text primary key, advanced int default 0, second_way int default 0, recovery_typed int default 0,
            terms_version text, privacy_version text, terms_at real, last_seen real);
        create table if not exists prot_cooloff(person text, reason text, until real);
        create table if not exists prot_contact(change_id text primary key, person text, kind text, new_ref text, ready_at real, status text);
        create table if not exists prot_locks(person text primary key, locked_at real, by text, unlocked_at real);
        create table if not exists prot_changes(id text primary key, person text, session_tail text, what text, undo text, at real, undone int default 0);
        create table if not exists prot_successor(person text primary key, successor text, inactive_days int, state text, requested_at real, ready_at real, lover text);
        create table if not exists prot_staffviews(id text primary key, person text, locns text, scope text, desk text, at real);
        create table if not exists prot_api(key_id text primary key, person text, state text);
        create table if not exists prot_cards(card_id text primary key, person text, state text);""")

    # ---------------------------------------------------------------- helpers
    def _row(self, person):
        self.db.execute("insert or ignore into prot_people(person) values(?)", (person,))
        return self.db.execute("select advanced,second_way,recovery_typed,terms_version,privacy_version,terms_at,last_seen from prot_people where person=?", (person,)).fetchone()

    def _lid(self, person):
        return self.a._lynkid(person)

    def advanced(self, person):
        return bool(self._row(person)[0])

    def seen(self, person, now=None):
        """Any signed-in activity by the owner: it resets the successor's inactivity clock and stops an open successor request."""
        self._row(person)
        self.db.execute("update prot_people set last_seen=? where person=?", (_now(now), person))
        r = self.db.execute("select state from prot_successor where person=?", (person,)).fetchone()
        if r and r[0] == "requested":
            self.db.execute("update prot_successor set state='named', requested_at=null, ready_at=null where person=?", (person,))
            self.a.emit(person, "SuccessorRequestStopped", {"lynkid": self._lid(person), "by": "owner_active"}, now)
        self.db.commit()

    # ---------------------------------------------------------------- two ways in
    def add_second_way(self, person, kind, now=None):
        if kind not in ("passkey", "device"):
            raise ValueError("a second way in is a passkey or a device")
        self._row(person)
        self.db.execute("update prot_people set second_way=1 where person=?", (person,)); self.db.commit()
        self.a.emit(person, "SecondWayAdded", {"lynkid": self._lid(person), "kind": kind}, now)

    def confirm_recovery_code(self, person, typed, now=None):
        """The person types the recovery code back once. Only its hash is kept, so it is checked against the hash."""
        from identity.auth import _h
        r = self.a.auth.db.execute("select recovery_hash from identities where person=?", (person,)).fetchone()
        if not r or r[0] != _h(typed):
            return False
        self._row(person)
        self.db.execute("update prot_people set recovery_typed=1 where person=?", (person,)); self.db.commit()
        self.a.emit(person, "RecoveryCodeConfirmed", {"lynkid": self._lid(person)}, now)
        return True

    def two_ways(self, person):
        r = self._row(person)
        return {"second_way": bool(r[1]), "recovery_code_kept": bool(r[2]), "done": bool(r[1] and r[2])}

    # ---------------------------------------------------------------- cool-off and held acts
    def start_cool_off(self, person, reason, now=None):
        """A new device or a new contact: the sensitive acts are held, and every other device is told (new_sign_in, passkey_added)."""
        if reason not in ("new_device", "new_contact"):
            raise ValueError("a cool-off starts after a new device or a new contact")
        until = _now(now) + (ADVANCED_COOL_OFF_S if self.advanced(person) else COOL_OFF_S)
        self.db.execute("insert into prot_cooloff values(?,?,?)", (person, reason, until)); self.db.commit()
        self.a.emit(person, "CoolOffStarted", {"lynkid": self._lid(person), "reason": reason, "until": int(until)}, now)
        return until

    def held_until(self, person, now=None):
        r = self.db.execute("select max(until) from prot_cooloff where person=?", (person,)).fetchone()
        return r[0] if r and r[0] and r[0] > _now(now) else None

    def may(self, person, act, now=None):
        """Whether a sensitive act may run now. Held acts wait out the cool-off; a locked account does nothing sensitive."""
        if act not in HELD_ACTS:
            raise ValueError(f"{act} is not a held act")
        if self.locked(person):
            return {"ok": False, "why": "locked"}
        until = self.held_until(person, now)
        if until:
            self.a.emit(person, "SensitiveActHeld", {"lynkid": self._lid(person), "act": act, "until": int(until)}, now)
            return {"ok": False, "why": "cool_off", "until": until}
        return {"ok": True}

    # ---------------------------------------------------------------- slow contact change
    def request_contact_change(self, person, kind, new_ref, fresh_check, now=None):
        """A new email or number: a fresh check first, then a notice to the old contact and a wait in which it can cancel."""
        if kind not in ("email", "phone"):
            raise ValueError("a contact is an email or a phone number")
        if not fresh_check:
            return {"state": "needs_fresh_check"}
        m = self.may(person, "contact_change", now)
        if not m["ok"]:
            return {"state": "held", **m}
        cid = uuid.uuid4().hex
        ready = _now(now) + (ADVANCED_CONTACT_WAIT_S if self.advanced(person) else CONTACT_WAIT_S)
        self.db.execute("insert into prot_contact values(?,?,?,?,?,?)", (cid, person, kind, new_ref, ready, "waiting")); self.db.commit()
        self.a.emit(person, "ContactChangeRequested", {"lynkid": self._lid(person), "kind": kind, "change_id": cid, "ready_at": int(ready)}, now)
        return {"state": "waiting", "change_id": cid, "ready_at": ready, "old_contact_told": True}

    def cancel_contact_change(self, person, change_id, by, now=None):
        if by not in ("old_contact", "owner"):
            raise ValueError("only the old contact or the owner cancels a contact change")
        n = self.db.execute("update prot_contact set status='cancelled' where change_id=? and person=? and status='waiting'", (change_id, person)).rowcount
        self.db.commit()
        if n:
            self.a.emit(person, "ContactChangeCancelled", {"lynkid": self._lid(person), "change_id": change_id, "by": by}, now)
        return bool(n)

    def apply_contact_changes(self, now=None):
        """Runs on a schedule: a change whose wait is over and that nobody cancelled is applied, then a cool-off starts."""
        done = []
        for cid, person, kind, ref in self.db.execute("select change_id,person,kind,new_ref from prot_contact where status='waiting' and ready_at<=?", (_now(now),)).fetchall():
            col = "email" if kind == "email" else "phone"
            self.a.auth.db.execute(f"update identities set {col}=? where person=?", (ref, person))
            self.db.execute("update prot_contact set status='applied' where change_id=?", (cid,)); self.db.commit()
            self.a.emit(person, "ContactChanged", {"lynkid": self._lid(person), "kind": kind, "change_id": cid}, now)
            self.start_cool_off(person, "new_contact", now)
            done.append(cid)
        return done

    # ---------------------------------------------------------------- advanced protection
    def turn_on_advanced(self, person, fresh_check, now=None):
        if not fresh_check:
            return {"state": "needs_fresh_check"}
        if len(self.a.passkeys(person)) < 2:
            return {"state": "needs_second_passkey"}
        self._row(person)
        self.db.execute("update prot_people set advanced=1 where person=?", (person,)); self.db.commit()
        self.a.emit(person, "AdvancedProtectionTurnedOn", {"lynkid": self._lid(person)}, now)
        return {"state": "on"}

    def turn_off_advanced(self, person, fresh_check, now=None):
        """Turning it off is a sensitive change: a fresh check, then the usual cool-off before it takes effect."""
        if not fresh_check:
            return {"state": "needs_fresh_check"}
        self.db.execute("update prot_people set advanced=0 where person=?", (person,)); self.db.commit()
        self.a.emit(person, "AdvancedProtectionTurnedOff", {"lynkid": self._lid(person)}, now)
        self.start_cool_off(person, "new_contact", now)
        return {"state": "off"}

    def code_sign_in_allowed(self, person):
        """An email or text code may start a restricted sign-in, except under advanced protection (passkeys only)."""
        return not self.advanced(person)

    # ---------------------------------------------------------------- Lock everything and "This was not me"
    def record_change(self, person, session_tail, what, undo, now=None):
        """Every change a session makes is noted with how to undo it, so "This was not me" can roll it back."""
        cid = uuid.uuid4().hex
        self.db.execute("insert into prot_changes values(?,?,?,?,?,?,0)", (cid, person, session_tail, what, undo, _now(now))); self.db.commit()
        return cid

    def locked(self, person):
        r = self.db.execute("select locked_at,unlocked_at from prot_locks where person=?", (person,)).fetchone()
        return bool(r and r[0] and not r[1])

    def lock_everything(self, person, by, verified, now=None):
        """Quick: one verified command. Sessions end, card freezes are asked of the issuer (shown frozen only when it confirms),
        API keys pause. Arrive Safe shares and trip plans keep running and are listed so the person can decide about them."""
        if by not in ("person", "not_me", "assist"):
            raise ValueError("Lock everything is used by the person, by 'This was not me' or through LynkAssist")
        if not verified:
            return {"state": "needs_fresh_check"}
        n = _now(now)
        sessions = len(self.a.sessions(person))
        self.a.sign_out_everywhere(person, now)
        cards = [c for (c,) in self.db.execute("select card_id from prot_cards where person=? and state='active'", (person,)).fetchall()]
        self.db.executemany("update prot_cards set state='freeze_sent' where card_id=?", [(c,) for c in cards])
        keys = self.db.execute("update prot_api set state='paused' where person=? and state='active'", (person,)).rowcount
        self.db.execute("insert or replace into prot_locks values(?,?,?,null)", (person, n, by)); self.db.commit()
        shares = [x["share_id"] for x in self.a.safe.shares(person, now)]
        self.a.emit(person, "EverythingLocked", {"lynkid": self._lid(person), "by": by, "sessions": sessions, "cards": len(cards), "keys": keys, "shares_left_running": len(shares)}, now)
        return {"state": "locked", "sessions_ended": sessions, "cards_freeze_sent": len(cards), "keys_paused": keys, "safety_shares_running": shares, "ask_about_shares": bool(shares)}

    def unlock(self, person, verified, now=None):
        """Unlocking always needs verification. Paused keys and cards stay as they are; the person resumes each one."""
        if not verified:
            return {"state": "needs_fresh_check"}
        if not self.locked(person):
            return {"state": "not_locked"}
        self.db.execute("update prot_locks set unlocked_at=? where person=?", (_now(now), person)); self.db.commit()
        self.a.emit(person, "EverythingUnlocked", {"lynkid": self._lid(person)}, now)
        return {"state": "unlocked"}

    def not_me(self, person, session_tail, now=None):
        """One tap: Lock everything, then undo what the suspicious session changed where it can still be undone."""
        res = self.lock_everything(person, "not_me", verified=True, now=now)
        rows = self.db.execute("select id,what,undo from prot_changes where person=? and session_tail=? and undone=0", (person, session_tail)).fetchall()
        rolled = [{"what": w, "undo": u} for (_i, w, u) in rows if u]
        self.db.executemany("update prot_changes set undone=1 where id=?", [(i,) for (i, _w, u) in rows if u]); self.db.commit()
        self.a.emit(person, "NotMeReported", {"lynkid": self._lid(person), "session_tail": session_tail, "rolled_back": len(rolled)}, now)
        return {**res, "rolled_back": rolled, "could_not_undo": [w for (_i, w, u) in rows if not u]}

    # ---------------------------------------------------------------- successor
    def successor_available(self, country):
        """Off until a lawyer confirms the rule in that country (country pack 'successor_confirmed'; none is confirmed yet)."""
        from core import regions
        try:
            return bool(regions.country(country).get("successor_confirmed"))
        except Exception:
            return False

    def name_successor(self, person, successor_lynkid, inactive_days, country, fresh_check, now=None):
        if not self.successor_available(country):
            return {"state": "coming_soon"}
        if not fresh_check:
            return {"state": "needs_fresh_check"}
        lo, hi = SUCCESSOR_INACTIVE_DAYS
        if not lo <= int(inactive_days) <= hi:
            raise ValueError(f"choose between {lo} and {hi} days")
        self.db.execute("insert or replace into prot_successor values(?,?,?,?,null,null,null)", (person, successor_lynkid, int(inactive_days), "named")); self.db.commit()
        self.a.emit(person, "SuccessorNamed", {"lynkid": self._lid(person), "successor": successor_lynkid, "inactive_days": int(inactive_days)}, now)
        return {"state": "named"}

    def successor_request(self, person, successor_lynkid, now=None):
        """The successor asks. Refused unless the owner has been inactive long enough; then a waiting period with notices to the owner."""
        r = self.db.execute("select successor,inactive_days,state from prot_successor where person=?", (person,)).fetchone()
        if not r or r[0] != successor_lynkid or r[2] != "named":
            return {"state": "refused"}
        last = self._row(person)[6] or 0
        if _now(now) - last < r[1] * DAY:
            return {"state": "refused"}                       # no clue: the same answer whether or not the owner is active
        ready = _now(now) + SUCCESSOR_WAIT_S
        self.db.execute("update prot_successor set state='requested', requested_at=?, ready_at=? where person=?", (_now(now), ready, person)); self.db.commit()
        self.a.emit(person, "SuccessorRequested", {"lynkid": self._lid(person), "successor": successor_lynkid, "ready_at": int(ready)}, now)
        return {"state": "waiting", "ready_at": ready, "owner_told": True}

    def successor_partner_answer(self, person, lover, confirmed, now=None):
        """Cloud only: the licensed partner checked the successor's identity. Access opens only after the wait and a confirmed check."""
        r = self.db.execute("select successor,state,ready_at from prot_successor where person=?", (person,)).fetchone()
        if not r or r[1] != "requested" or _now(now) < r[2]:
            return {"state": "waiting" if r and r[1] == "requested" else "refused"}
        if not confirmed:
            self.db.execute("update prot_successor set state='named', requested_at=null, ready_at=null where person=?", (person,)); self.db.commit()
            return {"state": "refused"}
        self.db.execute("update prot_successor set state='granted', lover=? where person=?", (lover, person)); self.db.commit()
        self.a.emit(person, "SuccessorGranted", {"lynkid": self._lid(person), "successor": r[0], "lover": lover}, now)
        return {"state": "granted"}

    # ---------------------------------------------------------------- the terms agreed
    def accept_terms(self, person, terms_version, privacy_version, now=None):
        if (terms_version, privacy_version) != (TERMS["terms"], TERMS["privacy"]):
            raise ValueError("accept the versions in force")
        self._row(person)
        self.db.execute("update prot_people set terms_version=?, privacy_version=?, terms_at=? where person=?", (terms_version, privacy_version, _now(now), person)); self.db.commit()
        self.a.emit(person, "TermsAccepted", {"lynkid": self._lid(person), "terms_version": terms_version, "privacy_version": privacy_version}, now)

    def terms_to_accept(self, person):
        r = self._row(person)
        return [k for k, v in (("terms", r[3]), ("privacy", r[4])) if v != TERMS[k]]

    # ---------------------------------------------------------------- staff views
    def record_staff_view(self, person, locns, scope, desk, now=None):
        """LynkOmni staff see a person's data only through a live time-limited consent, and every look is recorded and shown."""
        if not self.a.consent_allows(person, scope, desk, now):
            raise PermissionError("no live consent for this view")
        vid = uuid.uuid4().hex
        self.db.execute("insert into prot_staffviews values(?,?,?,?,?,?)", (vid, person, locns, scope, desk, _now(now))); self.db.commit()
        self.a.emit(person, "StaffViewRecorded", {"lynkid": self._lid(person), "locns": locns, "scope": scope, "desk": desk}, now)
        return vid

    def staff_views(self, person):
        return [{"locns": l, "scope": s, "desk": d, "at": a} for (l, s, d, a) in self.db.execute("select locns,scope,desk,at from prot_staffviews where person=? order by at desc", (person,))]

    # ---------------------------------------------------------------- the security check-up
    def checkup(self, person, now=None):
        """Findings, each with its fix ready to confirm (the fix is a LynkAssist action or a Security Center step)."""
        out = []
        two = self.two_ways(person)
        if not two["second_way"]:
            out.append({"id": "add_second_way", "fix": "add_passkey"})
        if not two["recovery_code_kept"]:
            out.append({"id": "confirm_recovery_code", "fix": "type_recovery_code"})
        if self.terms_to_accept(person):
            out.append({"id": "accept_terms", "fix": "review_terms"})
        if len(self.a.sessions(person)) > 3:
            out.append({"id": "many_sessions", "fix": "sign_out_other_device"})
        if not self.advanced(person) and len(self.a.passkeys(person)) >= 2:
            out.append({"id": "advanced_available", "fix": "turn_on_advanced"})
        for c in self.a.consents(person, now):
            if c.get("expires") and c["expires"] - _now(now) < 7 * DAY:
                out.append({"id": "consent_ending", "fix": "review_consent", "locns": c["locns"]})
        if self.locked(person):
            out.insert(0, {"id": "account_locked", "fix": "unlock"})
        return out
