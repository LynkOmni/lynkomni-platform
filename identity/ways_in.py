"""The ways to prove it's you and the protections around an account (section 4C point 3, master blueprint section 87), on top of
identity/account.py. Rules only from core/ways_in.py (catalog/ways-in.v1.json). No outside company is used for any of this:
security keys and passkeys are the open web standard, authenticator apps the open time-based code standard (RFC 6238) with no
brand named, and every code, key and word is kept only as a salted hash or encrypted (core/secrethash.py). Every step is an
account event (identity/events.v1.json) with references only: never a code, secret, word, name or contact in a payload."""
import base64, calendar, hashlib, hmac, json, secrets, struct, time, uuid


from core import ways_in as WI
from core.secrethash import code_hash, code_matches

DAY, HOUR = 86400, 3600
CODE_ALPHABET = WI.W["backup_codes"]["alphabet"]           # no 0, O, 1 or I: easy to read from paper


def _now(n):
    return time.time() if n is None else n


def totp(secret_b32, t, digits=None, period=None):
    """The open standard's 6-digit code for a moment (RFC 6238 over RFC 4226, SHA-1, 30 seconds), as authenticator apps make it."""
    a = WI.WAYS["authenticator"]
    digits, period = digits or a["digits"], period or a["period_s"]
    key = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8))
    mac = hmac.new(key, struct.pack(">Q", int(t // period)), hashlib.sha1).digest()
    o = mac[-1] & 15
    return f"{(struct.unpack('>I', mac[o:o + 4])[0] & 0x7FFFFFFF) % 10 ** digits:0{digits}d}"


class WaysIn:
    def __init__(self, account):
        self.a, self.db = account, account.db
        self._box_key = None                          # production: the key comes from the server key store (later item server_signing_key)
        self.db.executescript("""
        create table if not exists wi_backup(person text, n int, hash text, used real);
        create table if not exists wi_auth(person text primary key, secret text, confirmed real, last_step int);
        create table if not exists wi_keys(locrd text primary key, person text, name text, enrolled real, revoked real);
        create table if not exists wi_qr(token text primary key, device text, person text, made real, approved real, used real);
        create table if not exists wi_contacts(person text primary key, contacts text, set_at real);
        create table if not exists wi_word(person text primary key, word text, set_at real);
        create table if not exists wi_lock(person text primary key, countries text);
        create table if not exists wi_devices(person text, device text, last_used real, remembered int, primary key(person, device));
        create table if not exists wi_bounced(person text primary key, since real);
        create table if not exists wi_signins(person text, country text, at real);
        create table if not exists wi_tries(person text, at real);
        create table if not exists wi_extra_tries(person text, at real);
        create table if not exists wi_org(org text primary key, rules text);
        create table if not exists wi_basic(person text primary key);""")

    @property
    def _box(self):
        """The box that encrypts authenticator secrets and anti-phishing words, made only when one is first kept."""
        from cryptography.fernet import Fernet
        if self._box_key is None:
            self._box_key = Fernet(Fernet.generate_key())
        return self._box_key

    def _lid(self, person):
        return self.a._lynkid(person)

    def _emit(self, person, type_, payload, now):
        return self.a.emit(person, type_, dict({"lynkid": self._lid(person)}, **payload), now)

    # ---- backup codes: ten one-time codes, shown once, kept only scrambled ---------------------------------------------
    def make_backup_codes(self, person, now=None, quiet=False):
        b = WI.W["backup_codes"]
        codes = ["".join(secrets.choice(CODE_ALPHABET) for _ in range(b["length"])) for _ in range(b["count"])]
        self.db.execute("delete from wi_backup where person=?", (person,))
        self.db.executemany("insert into wi_backup values(?,?,?,null)", [(person, i, code_hash(c)) for i, c in enumerate(codes)])
        self.db.commit()
        if not quiet:
            self._emit(person, "BackupCodesMade", {"count": len(codes)}, now)
        return [f"{c[:5]}-{c[5:]}" for c in codes]

    def backup_codes_left(self, person):
        return self.db.execute("select count(*) from wi_backup where person=? and used is null", (person,)).fetchone()[0]

    def use_backup_code(self, person, typed, now=None):
        """Each code works once; an alert goes out every time one is used; at 2 left the person is asked to make new ones."""
        t = (typed or "").replace("-", "").replace(" ", "").upper()
        for n, h in self.db.execute("select n,hash from wi_backup where person=? and used is null", (person,)).fetchall():
            if code_matches(t, h):
                self.db.execute("update wi_backup set used=? where person=? and n=?", (_now(now), person, n)); self.db.commit()
                left = self.backup_codes_left(person)
                self._emit(person, "BackupCodeUsed", {"left": left}, now)
                self.a.contact_notices.append({"kind": "every", "person": person, "message": "backup_code_used"})
                return {"ok": True, "left": left, "note": WI.backup_codes_left_note(left)}
        self._extra_wrong(person, now)
        return {"ok": False}

    # ---- authenticator apps: the open time-based code standard, no brand named ------------------------------------------
    def add_authenticator(self, person, now=None):
        """Starts adding an authenticator app: the secret is shown once (as text and a QR code) and kept only encrypted."""
        secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
        self.db.execute("insert or replace into wi_auth values(?,?,null,null)", (person, self._box.encrypt(secret.encode()).decode())); self.db.commit()
        return {"secret": secret, "digits": WI.WAYS["authenticator"]["digits"], "period_s": WI.WAYS["authenticator"]["period_s"]}

    def _auth_ok(self, person, code, now):
        r = self.db.execute("select secret,last_step from wi_auth where person=?", (person,)).fetchone()
        if not r:
            return False
        a = WI.WAYS["authenticator"]
        secret, t = self._box.decrypt(r[0].encode()).decode(), _now(now)
        for d in range(-a["window"], a["window"] + 1):
            step = int(t // a["period_s"]) + d
            if (r[1] is None or step > r[1]) and hmac.compare_digest(totp(secret, step * a["period_s"]), str(code or "")):
                self.db.execute("update wi_auth set last_step=? where person=?", (step, person)); self.db.commit()
                return True                                   # each code once: an earlier or the same step never works again
        return False

    def confirm_authenticator(self, person, code, now=None):
        if not self._auth_ok(person, code, now):
            self._extra_wrong(person, now); raise PermissionError("that code doesn't match: type the code the app shows now")
        self.db.execute("update wi_auth set confirmed=? where person=?", (_now(now), person)); self.db.commit()
        self._emit(person, "ExtraCheckTurnedOn", {"way": "authenticator"}, now)

    def check_authenticator(self, person, code, now=None):
        if self._extra_locked(person, now):
            return {"ok": False, "wait_s": WI.W["extra_checks"]["wrong_tries"]["wait_s"]}
        confirmed = self.db.execute("select confirmed from wi_auth where person=?", (person,)).fetchone()
        ok = bool(confirmed and confirmed[0]) and self._auth_ok(person, code, now)
        if not ok:
            self._extra_wrong(person, now)
        return {"ok": ok}

    def _extra_wrong(self, person, now):
        self.db.execute("insert into wi_extra_tries values(?,?)", (person, _now(now))); self.db.commit()

    def _extra_locked(self, person, now):
        w = WI.W["extra_checks"]["wrong_tries"]
        n = self.db.execute("select count(*) from wi_extra_tries where person=? and at>?", (person, _now(now) - w["wait_s"])).fetchone()[0]
        return n >= w["wait_after"]

    def turn_off_extra(self, person, way, fresh_check, now=None):
        """Turning an extra check off needs a fresh check and waits out the cool-off (identity/protection.py)."""
        if not fresh_check:
            raise PermissionError("turning a check off needs a fresh check")
        m = self.a.protect.may(person, "remove_passkey", now)
        if not m["ok"]:
            raise PermissionError(f"held: {m['why']}")
        if way == "authenticator":
            self.db.execute("delete from wi_auth where person=?", (person,))
        self.db.commit()
        self._emit(person, "ExtraCheckTurnedOff", {"way": way}, now)

    def extras(self, person):
        has = set()
        r = self.db.execute("select confirmed from wi_auth where person=?", (person,)).fetchone()
        if r and r[0]:
            has.add("authenticator")
        if self.backup_codes_left(person):
            has.add("backup_code")
        return WI.extra_checks(has)

    # ---- security keys: a USB or tap key works as a passkey -------------------------------------------------------------
    def add_security_key(self, person, public_key, name, now=None):
        self.a.idp.enroll_passkey(person, public_key)
        locrd = self.db.execute("select locrd from creds where person=? and kind='passkey' order by rowid desc", (person,)).fetchone()[0]
        self.db.execute("insert into wi_keys values(?,?,?,?,null)", (locrd, person, name, _now(now))); self.db.commit()
        self._emit(person, "SecurityKeyAdded", {"locrd": locrd}, now)
        return locrd

    def security_keys(self, person):
        return [{"locrd": r[0], "name": r[1]} for r in self.db.execute("select locrd,name from wi_keys where person=? and revoked is null", (person,))]

    # ---- sign in with a QR code: the signed-in phone app scans and approves -------------------------------------------
    def qr_start(self, device, now=None):
        tok = secrets.token_urlsafe(24)
        self.db.execute("insert into wi_qr values(?,?,null,?,null,null)", (code_hash(tok), device, _now(now))); self.db.commit()
        return {"token": tok, "lifetime_s": WI.WAYS["qr_code"]["lifetime_s"]}

    def _qr_row(self, tok):
        for r in self.db.execute("select token,device,person,made,approved,used from wi_qr where used is null").fetchall():
            if code_matches(tok, r[0]):
                return r
        return None

    def qr_approve(self, person, tok, session_ok, now=None):
        """The phone app that is already signed in scans the code and approves; the code lasts two minutes and works once."""
        if not session_ok:
            raise PermissionError("approve from a phone that is already signed in")
        r = self._qr_row(tok)
        if not r or _now(now) - r[3] > WI.WAYS["qr_code"]["lifetime_s"]:
            raise PermissionError("this code has ended: show a new one")
        self.db.execute("update wi_qr set person=?, approved=? where token=?", (person, _now(now), r[0])); self.db.commit()
        return {"device": r[1]}

    def qr_finish(self, tok, device, now=None):
        r = self._qr_row(tok)
        if not r or not r[2] or r[1] != device:
            return None
        self.db.execute("update wi_qr set used=? where token=?", (_now(now), r[0])); self.db.commit()
        return r[2]

    # ---- recovery contacts: 3 to 5 trusted people confirm it's you ------------------------------------------------------
    def set_recovery_contacts(self, person, lynkids, fresh_check, now=None):
        if not fresh_check:
            raise PermissionError("changing recovery contacts needs a fresh check")
        why = WI.contacts_problem(lynkids)
        if why:
            raise ValueError(f"recovery contacts: {why}")
        if self._lid(person) in lynkids:
            raise ValueError("you can't be your own recovery contact")
        self.db.execute("insert or replace into wi_contacts values(?,?,?)", (person, json.dumps(sorted(set(lynkids))), _now(now))); self.db.commit()
        self._emit(person, "RecoveryContactsSet", {"count": len(set(lynkids))}, now)

    def recovery_contacts(self, person):
        r = self.db.execute("select contacts from wi_contacts where person=?", (person,)).fetchone()
        return json.loads(r[0]) if r else []

    # ---- the anti-phishing word: the person's secret word in every real LynkOmni message -------------------------------
    def set_word(self, person, word, fresh_check, now=None):
        if not fresh_check:
            raise PermissionError("changing the word needs a fresh check")
        why = WI.anti_phishing_problem(word)
        if why:
            raise ValueError(f"word: {why}")
        self.db.execute("insert or replace into wi_word values(?,?,?)", (person, self._box.encrypt(word.strip().encode()).decode(), _now(now))); self.db.commit()
        self._emit(person, "AntiPhishingWordSet", {}, now)

    def word_for_message(self, person):
        """The message engine puts this in every real LynkOmni email and message to the person; never in an event or a log."""
        r = self.db.execute("select word from wi_word where person=?", (person,)).fetchone()
        return self._box.decrypt(r[0].encode()).decode() if r else None

    # ---- sign-in checks: unusual sign-ins, the country lock, old devices, remember this device -------------------------
    def set_country_lock(self, person, countries, fresh_check, now=None):
        if not fresh_check:
            raise PermissionError("the country lock needs a fresh check")
        if len(countries) > WI.PROTECT["country_lock"]["max_countries"]:
            raise ValueError("too many countries")
        self.db.execute("insert or replace into wi_lock values(?,?)", (person, json.dumps(sorted(set(countries))))); self.db.commit()
        self._emit(person, "CountryLockSet", {"count": len(set(countries))}, now)

    def country_lock(self, person):
        r = self.db.execute("select countries from wi_lock where person=?", (person,)).fetchone()
        return json.loads(r[0]) if r else []

    def check_sign_in(self, person, device, country, now=None):
        """Before a sign-in finishes: refused outside a country lock; an extra check asked for an unusual sign-in or a new device."""
        t = _now(now)
        if not WI.country_allowed(self.country_lock(person), country):
            self._emit(person, "SignInRefused", {"reason": "country_lock"}, now)
            return {"ok": False, "why": "country_lock"}
        history = [{"country": c, "at": a} for c, a in self.db.execute("select country,at from wi_signins where person=?", (person,))]
        tries = self.db.execute("select count(*) from wi_tries where person=? and at>?", (person, t - HOUR)).fetchone()[0]
        reasons = WI.unusual(history, {"country": country, "at": t}, tries)
        known = self.db.execute("select 1 from wi_devices where person=? and device=?", (person, device)).fetchone() is not None
        ask = bool(reasons) or (bool(history) and not known)
        return {"ok": True, "unusual": reasons, "extra_check": ask and bool(self.extras(person) or self.a.passkeys(person)), "new_device": not known}

    def failed_sign_in(self, person, now=None):
        self.db.execute("insert into wi_tries values(?,?)", (person, _now(now))); self.db.commit()

    def signed_in(self, person, device, country, remember, now=None):
        """Records the sign-in (country only, never a position) and returns how long the session lasts."""
        t = _now(now)
        self.db.execute("insert into wi_signins values(?,?,?)", (person, country, t))
        self.db.execute("insert or replace into wi_devices values(?,?,?,?)", (person, device, t, 1 if remember else 0)); self.db.commit()
        return {"hours": WI.session_hours(remember)}

    def known_device(self, person, device):
        """A device this person has signed in on before (and not signed out for being old)."""
        return self.db.execute("select 1 from wi_devices where person=? and device=?", (person, device)).fetchone() is not None

    # ---- a working way to reach you (owner, 2026-11-26): LynkOmni never texts, so the checkup makes sure a free way works --
    def email_bounced(self, person, now=None):
        """Cloud only, from the email partner's report: messages to this person's email are coming back."""
        self.db.execute("insert or ignore into wi_bounced values(?,?)", (person, _now(now))); self.db.commit()

    def email_works(self, person):
        """The email was confirmed again (a code was read) or a message was opened."""
        self.db.execute("delete from wi_bounced where person=?", (person,)); self.db.commit()

    def reachable(self, person):
        """A free way reaches this person: an email that is not bouncing, or the app signed in on a device."""
        bounced = self.db.execute("select 1 from wi_bounced where person=?", (person,)).fetchone() is not None
        devices = self.db.execute("select 1 from wi_devices where person=?", (person,)).fetchone() is not None
        return not bounced or devices

    def sign_out_old_devices(self, now=None):
        """Devices unused for 90 days are signed out (the daily housekeeping)."""
        t, out = _now(now), []
        for person, device, last in self.db.execute("select person,device,last_used from wi_devices").fetchall():
            if WI.old_device(last, t):
                self.db.execute("delete from wi_devices where person=? and device=?", (person, device))
                self._emit(person, "OldDeviceSignedOut", {"device_name": device}, now)
                out.append((person, device))
        self.db.commit()
        return out

    def activity(self, person, now=None):
        """The security activity log: every sign-in and change for a year, newest first, each with This wasn't me."""
        keep = WI.PROTECT["activity_log"]["keep_days"] * DAY
        t = _now(now)
        def at(e):
            return calendar.timegm(time.strptime(e["ts"], "%Y-%m-%dT%H:%M:%SZ")) if isinstance(e["ts"], str) else e["ts"]
        rows = [e for e in self.a.c.store.since(person) if e["type"] in SECURITY_EVENTS and t - at(e) <= keep]
        return [{"type": e["type"], "at": e["ts"], "this_was_not_me": True} for e in reversed(rows)]

    def checkup(self, person, now=None):
        have = {"second_way": len(self.a.passkeys(person)) + len(self.security_keys(person)) >= 2 or "authenticator" in self.extras(person),
                "backup_codes": self.backup_codes_left(person) > WI.W["backup_codes"]["remind_at"],
                "recovery_contacts": bool(self.recovery_contacts(person)),
                "anti_phishing_word": self.word_for_message(person) is not None,
                "old_devices": not any(WI.old_device(l, _now(now)) for (l,) in self.db.execute("select last_used from wi_devices where person=?", (person,))),
                "number_confirmed": True,
                "reachable": self.reachable(person)}
        return WI.checkup(have)

    # ---- basic phone accounts: phone and PIN only, limited until an email is added ------------------------------------
    def mark_basic_phone(self, person):
        self.db.execute("insert or ignore into wi_basic values(?)", (person,)); self.db.commit()

    def email_added(self, person, now=None):
        if self.db.execute("delete from wi_basic where person=?", (person,)).rowcount:
            self.db.commit(); self._emit(person, "BasicPhoneLimitsLifted", {}, now)

    def allows(self, person, act):
        basic = self.db.execute("select 1 from wi_basic where person=?", (person,)).fetchone() is not None
        return WI.basic_phone_allows(act, not basic)

    # ---- organisation rules (Max and Enterprise) ----------------------------------------------------------------------
    def set_org_rules(self, org, plan, rules):
        o = WI.PROTECT["org_rules"]
        if plan not in o["plans"]:
            raise PermissionError("organisation sign-in rules come with Max and Enterprise")
        bad = set(rules) - set(o["rules"])
        if bad:
            raise ValueError(f"unknown rules {sorted(bad)}")
        h = rules.get("staff_session_hours")
        if h is not None and not (o["staff_session_hours"]["min"] <= h <= o["staff_session_hours"]["max"]):
            raise ValueError("staff session length is 1 to 24 hours")
        self.db.execute("insert or replace into wi_org values(?,?)", (org, json.dumps(rules, sort_keys=True))); self.db.commit()

    def org_rules(self, org):
        r = self.db.execute("select rules from wi_org where org=?", (org,)).fetchone()
        return json.loads(r[0]) if r else {}


SECURITY_EVENTS = ("SessionStarted", "SessionRevoked", "PasskeyEnrolled", "PasskeyRevoked", "SecurityKeyAdded", "BackupCodesMade", "BackupCodeUsed",
                   "ExtraCheckTurnedOn", "ExtraCheckTurnedOff", "RecoveryContactsSet", "AntiPhishingWordSet", "CountryLockSet", "SignInRefused",
                   "OldDeviceSignedOut", "RecoveryStarted", "RecoveryCompleted", "RecoveryCancelled", "PayoutChangeRequested", "ContactRemoved")
