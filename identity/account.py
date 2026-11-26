"""LynkOmni Account (account.lynkomni.com), build section 2: one identity for every LynkOmni surface, on top of the identity
platform (identity/platform.py) and the layered recovery design (identity/auth.py). Reference rules for sign-up, passkeys,
sessions, the Security Center, data-sharing consents, the account-takeover safeguards (blueprint 43 H), download-my-records,
closing an account, Start a business (N14) and the customer's standing payments (N4). Every change is an event on the person's
own stream, named in identity/events.v1.json, with references only: no phone numbers, emails, codes or secrets in a payload.
Sandbox notes: contact codes and recovery codes are returned to the caller so tests run offline; production sends them and never
returns them (provider ledger: sms_otp). The registration gateway is a SANDBOX adapter (provider ledger: registration_gateway)."""
import json, os, secrets, time, uuid

import providers
from core.usernames import UsernameRegistry, check as username_check
from identity.auth import Identity, SITES
from identity.platform import IdentityPlatform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "identity", "events.v1.json"), encoding="utf-8") as f:
    EVENTS = json.load(f)["events"]
DAY = 86400
PAYOUT_WAIT_S = DAY            # takeover safeguard: payout or bank details change waits a day unless a second enrolled device approves
DATA_REQUEST_DAYS = 30              # download my records: ready within 30 days, kept for 7
CLOSE_GRACE_DAYS = 30               # closing an account: a grace period, then the LynkID is retired for ever
CONSENT_SCOPES = {"health-pack": "business health pack (LynkStat Score and trends, never a credit score)", "accountant": "the accountant sees the books of this business",
                  "lender": "a licensed lender reads the health pack once", "developer-app": "a developer app reads the scopes it names", "support": "support sees this record for a short time",
                  "supplier-sell-through": "a supplier sees sell-through of its own products only",
                  "location-share": "people you choose see your trip or live location until the share ends (Arrive Safe)"}
MAX_CONSENT_DAYS = {"health-pack": 90, "accountant": 365, "lender": 30, "developer-app": 365, "support": 1, "supplier-sell-through": 365, "location-share": 30}
REGISTRATION_STEPS = ("profile", "registration", "tax_number", "bank_account")
PAGES = ("overview", "profile", "security", "businesses", "orders", "transactions", "wallet", "billing", "memberships", "privacy", "notifications", "messages", "support", "assist", "payslips", "payments", "start", "storefront", "trips", "collect",
         "attendance", "tickets", "answers", "panel")   # NEW UPDATE 4 (section 2): My details, My tickets, My answers, the LynkSurvey Panel
def _now(n): return time.time() if n is None else n


class CodeWait(Exception):
    """Another code cannot be sent yet: .seconds is the wait left (the screen counts it down)."""
    def __init__(self, seconds):
        super().__init__(f"wait {seconds} seconds before asking for another code"); self.seconds = seconds
from core.secrethash import code_hash as _h, code_matches  # salted scrypt for codes a person types (core/secrethash.py)


class RegistrationGateway:
    """Interface to a government registration gateway or a bank in the Partner Hub (N14). A real adapter submits the application
    and reports the authority's answer; LynkOmni never decides, never takes the fee and never claims approval before the answer."""
    def submit(self, application): raise NotImplementedError
    def result(self, application_id): raise NotImplementedError


class SandboxGateway(RegistrationGateway):
    """SANDBOX: approves any complete application after one poll. Fees go to the government body in the real adapter, never through LynkOmni."""
    def __init__(self): self.sent = {}
    def submit(self, application): self.sent[application["application_id"]] = application; return {"reference": "SBX-" + application["application_id"][:8]}
    def result(self, application_id):
        a = self.sent.get(application_id)
        return {"status": "approved", "registration_number": "SBX" + application_id[:6].upper()} if a and all(a["steps"].values()) else {"status": "pending"}


class Account:
    def __init__(s, platform, flow=None, gateway=None):
        s.p, s.c, s.db, s.ids, s.idp = platform, platform.c, platform.c.store.db, platform.ids, platform.idp
        s.auth = Identity(platform.c)
        s.flow, s.gateway, s.usernames = flow, gateway or SandboxGateway(), UsernameRegistry()
        s.contact_notices = []          # SANDBOX: what the messaging provider would send (provider ledger sms_otp); kept here for tests
        s.db.executescript("""
        create table if not exists acct_people(person text primary key, lynkid text, username text, lang text, status text, closes_at real, contact_ok int);
        create table if not exists acct_contacts(person text, kind text, code_hash text, expires real, primary key(person, kind));
        create table if not exists acct_code_sends(person text, kind text, at real);
        create table if not exists acct_signup(person text primary key, country text, legal_ref text, email_ok int, phone_ok int, basic int, device text, network text, at real, age_checked real);
        create table if not exists acct_age_blocks(key text, at real, cleared real);
        create table if not exists acct_age_idchecks(lover text primary key, keys text, country text, state text, at real, answered real);
        create table if not exists acct_signup_tries(device text, network text, at real);
        create table if not exists acct_number_checks(person text primary key, confirmed real, reminded real);
        create table if not exists acct_idchecks(lover text primary key, person text, purpose text, state text, partner text, requested real, answered real);
        create table if not exists acct_passkeys(locrd text primary key, person text, device_name text, enrolled_at real, revoked_at real);
        create table if not exists acct_sessions(token text primary key, person text, site text, device_name text, place text, started real, revoked real);
        create table if not exists acct_consents(locns text primary key, person text, scope text, grantee text, purpose text, granted real, expires real, withdrawn real, warned int);
        create table if not exists acct_payout(id text primary key, person text, org text, ready_at real, status text);
        create table if not exists acct_holds(ref text primary key, person text, kind text, since real, cleared real, how text);
        create table if not exists acct_requests(id text primary key, person text, opened real, due real, ready real, expires real);
        create table if not exists acct_apps(application_id text primary key, person text, lodoc text, country text, steps text, status text, gateway_ref text, lynkoid text);
        create table if not exists acct_standing(losub text primary key, person text, merchant text, cap_minor int, currency text, provider text, approved real, revoked real, uses int);""")
        from identity.arrive_safe import ArriveSafe
        s.safe = ArriveSafe(s)          # Arrive Safe and Collect Pass (NEW UPDATE 1, build section 2)
        from identity.protection import Protection
        s.protect = Protection(s)       # MASTER UPDATE section 2: two ways in, cool-off, slow contact change, Lock everything, successor, terms
        from identity.ways_in import WaysIn
        s.ways = WaysIn(s)              # section 4C point 3: backup codes, authenticator apps, security keys, QR sign-in, recovery contacts, protections
        from identity.recover import RecoveryHub
        s.recover = RecoveryHub(s)      # section 4C point 5: the Can't sign in? hub
        from identity.phone_owner import PhoneOwner
        s.owner = PhoneOwner(s)         # section 4C point 4: the phone owner check, only where deep identity is needed
    # ---- events
    def _lynkid(s, person):
        r = s.db.execute("select lynkid from acct_people where person=?", (person,)).fetchone(); return r[0] if r else None
    def emit(s, person, type_, payload, now=None):
        if type_ not in EVENTS: raise ValueError(f"{type_} is not an account event (identity/events.v1.json)")
        allowed = set(EVENTS[type_]["payload"])
        bad = set(payload) - allowed
        if bad: raise ValueError(f"{type_} must not carry {sorted(bad)}")
        eid = uuid.uuid4().hex
        s.c.store.append(person, "server", type_, payload, id_=eid)
        if s.flow: s.flow.on_event(person, {"id": eid, "type": type_, "payload": payload}, now=now)
        return eid
    # ---- sign-up: username, contact check, passkey, recovery code shown once
    def username_status(s, value): return s.usernames.status(value)
    @staticmethod
    def minimum_age(country=None):
        """18, or the country pack's age of majority when it is set and higher (unconfirmed packs keep 18)."""
        from core import workspaces, regions
        return workspaces.minimum_age(regions.country(country).get("storefront") if country else None)
    def begin_sign_up(s, username, lang="en", now=None, adult_confirmed=False, country=None, online=True, device=None, network=None):
        """Sign-up on the app and the web (section 4C point 3, catalog/ways-in.v1.json): online only, in the fixed order country,
        username, age, legal name, email and its code, phone and its code, passkey, recovery. BIZZ & DEVICE: an account is for a
        person of at least 18, or the local age of majority where that is higher (core.workspaces.minimum_age); the person
        confirms it and no birth date or age is asked for or stored. Fake sign-ups are slowed per device and network each hour,
        with no picture puzzles and no outside company."""
        from core import ways_in
        t = _now(now)
        hour = [r for r in s.db.execute("select device,network from acct_signup_tries where at>?", (t - 3600,))]
        ok, why = ways_in.may_start_sign_up(online, sum(1 for d, _ in hour if device and d == device), sum(1 for _, n in hour if network and n == network))
        if not ok:
            if why == "connect_to_create": raise ConnectionError("connect to the internet to create your account; what you typed is kept")
            raise PermissionError("too many new accounts from here this hour: try again later")
        if s.age_blocked(device=device, network=network):
            raise PermissionError("an account cannot be created from here: if this is a mistake, check your age with an ID")
        if adult_confirmed is not True:
            raise PermissionError("the age check on the device must say adult")
        c = username_check(username)
        if not c["ok"]: raise ValueError(c["reason"])
        if s.usernames.status(username) != "available": raise ValueError(s.usernames.status(username))
        s.db.execute("insert into acct_signup_tries values(?,?,?)", (device, network, t))
        p = s.idp.register_person(lang); u = s.usernames.take(username, p["lynkid"], "person")
        s.db.execute("insert into acct_people values(?,?,?,?,?,?,0)", (p["internal"], p["lynkid"], u, lang, "signing_up", None))
        s.db.execute("insert into acct_signup values(?,?,null,0,0,0,?,?,?,?)", (p["internal"], country, device, network, t, t)); s.db.commit()
        return {"person": p["internal"], "lynkid": p["lynkid"], "username": u, "next": "legal_name"}
    @staticmethod
    def _age_keys(device=None, network=None, number_digest=None):
        return [f"{k}:{v}" for k, v in (("device", device), ("network", network), ("phone_number", number_digest)) if v]
    def age_refused(s, device=None, network=None, number_digest=None, now=None):
        """The device's age check said under: final on that device, network or (basic phone) number until the licensed
        partner's ID check clears it. Nothing about the person is kept: no date, no age, no name, only the key and the time."""
        t = _now(now)
        for k in s._age_keys(device, network, number_digest):
            s.db.execute("insert into acct_age_blocks values(?,?,null)", (k, t))
        s.db.commit()
    def age_blocked(s, device=None, network=None, number_digest=None):
        from core import ways_in
        for k in s._age_keys(device, network, number_digest):
            for at, cleared in s.db.execute("select at, cleared from acct_age_blocks where key=?", (k,)):
                if ways_in.age_blocked(at, cleared):
                    return True
        return False
    def age_id_check_request(s, country, device=None, network=None, number_digest=None, now=None, partner=None):
        """The person asks the licensed identity partner to check their age with an ID (they pay its fee, shown first). Off until
        the partner is signed in the country (core.regions.enabled "age_id_check"). The state is sent until the partner answers."""
        from core import regions
        from services.age_partners import SandboxAgeIdCheck
        keys = s._age_keys(device, network, number_digest)
        if not keys: raise ValueError("a device, network or number is needed")
        if partner is None and not regions.enabled(country, "age_id_check"): return {"state": "coming_soon"}
        lover = s.ids.assign("VER", uuid.uuid4().hex)
        r = (partner or SandboxAgeIdCheck()).start(lover, country)
        if not r.get("ok"): raise ValueError(r.get("reason", "partner refused"))
        s.db.execute("insert into acct_age_idchecks values(?,?,?,?,?,null)", (lover, json.dumps(keys), country, "sent", _now(now))); s.db.commit()
        return {"lover": lover, "state": "sent"}
    def partner_age_answer(s, lover, adult, now=None):
        """Cloud only, from the partner's answer: adult yes or no, never the document, date or age. Adult clears the block on
        every key of the request; not adult leaves it."""
        r = s.db.execute("select keys, state from acct_age_idchecks where lover=?", (lover,)).fetchone()
        if not r or r[1] != "sent": raise ValueError("no open age check")
        t, state = _now(now), ("confirmed" if adult is True else "failed")
        s.db.execute("update acct_age_idchecks set state=?, answered=? where lover=?", (state, t, lover))
        if state == "confirmed":
            for k in json.loads(r[0]):
                s.db.execute("update acct_age_blocks set cleared=? where key=? and cleared is null", (t, k))
        s.db.commit()
        return state
    def set_legal_name(s, person, legal_name, legal_ref):
        """The legal name as on the person's ID document (a business gives its registered name), asked once and kept apart from
        the display name so the phone owner check can match it. The text is checked here and kept only in the PII vault;
        the account keeps the vault reference."""
        from core import ways_in
        why = ways_in.legal_name_problem(legal_name)
        if why: raise ValueError(f"legal name: {why}")
        s.db.execute("update acct_signup set legal_ref=? where person=?", (legal_ref, person)); s.db.commit()
        return {"next": "email"}
    def send_contact_code(s, person, now=None, kind="email"):
        """SANDBOX: the code is returned so tests run offline. Production sends it by SMS or email and never returns it.
        Email and phone each get their own code. A code lasts 5 minutes; asking again waits a little longer each time and at
        most 5 codes go out in an hour (core/phone.py CODES): the wait is raised as CodeWait with the seconds left."""
        from core.phone import CODES, resend_wait
        if kind not in ("email", "phone"): raise ValueError("a code goes to an email or a phone number")
        t = _now(now)
        sent = [r[0] for r in s.db.execute("select at from acct_code_sends where person=? and kind=?", (person, kind))]
        wait = resend_wait(sent, t)
        if wait: raise CodeWait(wait)
        code = f"{secrets.randbelow(10**6):06d}"
        s.db.execute("insert or replace into acct_contacts values(?,?,?,?)", (person, kind, _h(code), t + CODES["lifetime_s"]))
        s.db.execute("insert into acct_code_sends values(?,?,?)", (person, kind, t)); s.db.commit(); return code
    def confirm_contact(s, person, code, now=None, kind="email"):
        r = s.db.execute("select code_hash,expires from acct_contacts where person=? and kind=?", (person, kind)).fetchone()
        if not r or r[1] < _now(now) or not code_matches(code, r[0]): raise PermissionError("wrong or expired code")
        s.db.execute(f"update acct_signup set {kind}_ok=1 where person=?", (person,))
        s.db.execute("delete from acct_contacts where person=? and kind=?", (person, kind))
        both = s.db.execute("select email_ok and phone_ok from acct_signup where person=?", (person,)).fetchone()
        if both and both[0]: s.db.execute("update acct_people set contact_ok=1 where person=?", (person,))
        s.db.commit()
        return {"next": "phone" if kind == "email" else "passkey"}
    def finish_sign_up(s, person, passkey_public_key, device_name, phone_ref, email_ref, backup_contact=None, now=None):
        """Needs the legal name, a confirmed email and a confirmed phone number, and a passkey. Returns the recovery code and the
        ten backup codes ONCE: the recovery code goes on paper, never on the phone."""
        row = s.db.execute("select contact_ok,lynkid,username,lang from acct_people where person=?", (person,)).fetchone()
        su = s.db.execute("select legal_ref from acct_signup where person=?", (person,)).fetchone()
        if not row or not row[0]: raise PermissionError("confirm the email and the phone number first, each with its own code")
        if not su or not su[0]: raise PermissionError("give the legal name as on your ID document first")
        if not (phone_ref and email_ref): raise ValueError("an account needs both an email and a phone number")
        # one person, one contact (section 4C point 1): a personal email or phone number belongs to one personal account at a time
        for col, ref in (("phone", phone_ref), ("email", email_ref)):
            if ref and s.auth.db.execute(f"select 1 from identities where {col}=? and person<>?", (ref, person)).fetchone():
                raise PermissionError("this contact already belongs to another account: sign in to it or use Can't sign in?")
        locrd = s.enroll_passkey(person, passkey_public_key, device_name, now, quiet=True)
        s.auth.register(person, phone_ref, email_ref, row[3])                      # vault references only, never the numbers
        code = s.auth.add_merchant_role(person, f"personal:{person}", backup_contact)
        s.db.execute("update acct_people set status='active' where person=?", (person,)); s.db.commit()
        s.emit(person, "AccountCreated", {"lynkid": row[1], "username": row[2], "lang": row[3]}, now)
        s.emit(person, "PasskeyEnrolled", {"lynkid": row[1], "locrd": locrd, "device_name": device_name}, now)
        from identity.protection import TERMS
        s.protect.accept_terms(person, TERMS["terms"], TERMS["privacy"], now)      # the sign-up screen shows both; the versions are recorded
        backup = s.ways.make_backup_codes(person, now, quiet=True)
        return {"recovery_code": code, "backup_codes": backup, "locrd": locrd, "show_once": True, "next": "two_ways_in"}
    # ---- MASTER UPDATE 55: sign-up by email or by phone, side by side, and no clue for strangers
    # ---- section 4C point 1: numbers that change hands --------------------------------------------------------------------
    def number_reassigned(s, phone_ref, now=None):
        """The mobile network partner says a number now belongs to someone else (networks give old numbers out again). The number
        is taken off the account it was on, so its new owner can never reach that account, and the owner is told by email.
        A phone number alone never opens or recovers an account."""
        row = s.auth.db.execute("select person from identities where phone=?", (phone_ref,)).fetchone()
        if not row: return None
        person = row[0]
        s.auth.db.execute("update identities set phone=null where person=?", (person,)); s.auth.db.commit()
        lynkid = s._lynkid(person)
        s.emit(person, "ContactRemoved", {"lynkid": lynkid, "kind": "phone", "reason": "reassigned"}, now)
        s.contact_notices.append({"kind": "email", "person": person, "message": "number_removed_reassigned"})
        return {"removed": "phone", "told_by": "email"}

    def confirm_number(s, person, now=None):
        """The person confirms the number on the account is still theirs (asked once a year)."""
        t = _now(now)
        s.db.execute("insert into acct_number_checks values(?,?,null) on conflict(person) do update set confirmed=excluded.confirmed, reminded=null", (person, t)); s.db.commit()
        s.emit(person, "NumberConfirmed", {"lynkid": s._lynkid(person)}, now)

    def numbers_to_confirm(s, now=None):
        """People whose number was last confirmed (or set) more than a year ago and who were not reminded yet."""
        t = _now(now)
        out = []
        for (person,) in s.db.execute("select person from acct_people where status='active'"):
            r = s.db.execute("select confirmed,reminded from acct_number_checks where person=?", (person,)).fetchone()
            ph = s.auth.db.execute("select phone from identities where person=?", (person,)).fetchone()
            if not ph or not ph[0]: continue
            if r is None:
                s.db.execute("insert into acct_number_checks values(?,?,null)", (person, t)); continue
            if r[1] is None and t - r[0] >= 365 * DAY: out.append(person)
        s.db.commit(); return out

    def mark_number_reminded(s, person, now=None):
        s.db.execute("update acct_number_checks set reminded=? where person=?", (_now(now), person)); s.db.commit()

    def start_with_contact(s, kind, contact_ref, now=None):
        """The first step of sign-up or sign-in with an email or a phone number (a vault reference). The answer is the same
        whether or not the contact already has an account, so nobody can learn who is a LynkOmni customer. A contact that has an
        account gets a message saying someone tried to sign up with it, with a sign-in button, never a code that opens it."""
        if kind not in ("email", "phone"):
            raise ValueError("sign up with an email or a phone number")
        col = "email" if kind == "email" else "phone"
        known = s.auth.db.execute(f"select person from identities where {col}=?", (contact_ref,)).fetchone() is not None
        s.contact_notices.append({"kind": kind, "ref": contact_ref, "message": "someone_tried_your_contact" if known else "sign_up_code"})
        return {"next": "check_your_messages"}
    # ---- identity check before a first paid Storefront offer (BIZZ & DEVICE): the licensed partner checks, LynkOmni only asks and records
    def request_identity_check(s, person, purpose="first_paid_offer", now=None):
        """Sends the request to the licensed payment partner (sandbox until signed). The state is 'sent' until the partner answers."""
        open_ = s.db.execute("select lover,state from acct_idchecks where person=? and state in ('sent','confirmed')", (person,)).fetchone()
        if open_: return {"lover": open_[0], "state": open_[1]}
        lover = s.ids.assign("VER", uuid.uuid4().hex)
        s.db.execute("insert into acct_idchecks values(?,?,?,?,?,?,null)", (lover, person, purpose, "sent", None, _now(now))); s.db.commit()
        s.emit(person, "IdentityCheckRequested", {"lynkid": s._lynkid(person), "purpose": purpose, "lover": lover}, now)
        return {"lover": lover, "state": "sent"}
    def partner_identity_answer(s, lover, confirmed, partner, now=None):
        """Cloud only, from the partner's answer: confirmed or failed. Nothing on a device can confirm an identity."""
        r = s.db.execute("select person,state from acct_idchecks where lover=?", (lover,)).fetchone()
        if not r or r[1] != "sent": raise ValueError("no open identity check")
        state = "confirmed" if confirmed else "failed"
        s.db.execute("update acct_idchecks set state=?, partner=?, answered=? where lover=?", (state, partner, _now(now), lover)); s.db.commit()
        if confirmed: s.emit(r[0], "IdentityCheckConfirmed", {"lynkid": s._lynkid(r[0]), "lover": lover, "partner": partner}, now)
        return state
    def identity_confirmed(s, person):
        return s.db.execute("select 1 from acct_idchecks where person=? and state='confirmed'", (person,)).fetchone() is not None
    def change_username(s, person, new, now=None):
        lid, old = s._lynkid(person), s.db.execute("select username from acct_people where person=?", (person,)).fetchone()[0]
        u = s.usernames.change(lid, old, new, now); s.db.execute("update acct_people set username=? where person=?", (u, person)); s.db.commit()
        s.emit(person, "UsernameChanged", {"lynkid": lid, "old": old, "new": u}, now); return u
    # ---- passkeys
    def enroll_passkey(s, person, public_key, device_name, now=None, quiet=False):
        s.idp.enroll_passkey(person, public_key)
        locrd = s.db.execute("select locrd from creds where person=? and kind='passkey' order by rowid desc", (person,)).fetchone()[0]
        s.db.execute("insert into acct_passkeys values(?,?,?,?,null)", (locrd, person, device_name, _now(now))); s.db.commit()
        if not quiet: s.emit(person, "PasskeyEnrolled", {"lynkid": s._lynkid(person), "locrd": locrd, "device_name": device_name}, now)
        return locrd
    def passkeys(s, person): return [{"locrd": r[0], "device_name": r[1], "enrolled_at": r[2]} for r in s.db.execute("select locrd,device_name,enrolled_at from acct_passkeys where person=? and revoked_at is null", (person,))]
    def revoke_passkey(s, person, locrd, stepup_token, now=None):
        if not s.auth.stepup_valid(stepup_token, now=now): raise PermissionError("removing a sign-in method needs a fresh step-up")
        if len(s.passkeys(person)) <= 1: raise PermissionError("keep at least one passkey; add another before removing this one")
        if s.protect.advanced(person) and len(s.passkeys(person)) <= 2: raise PermissionError("advanced protection keeps two passkeys; add another first")
        m = s.protect.may(person, "remove_passkey", now)
        if not m["ok"]: raise PermissionError(f"held: {m['why']}")
        s.db.execute("update acct_passkeys set revoked_at=? where locrd=? and person=?", (_now(now), locrd, person)); s.db.execute("update creds set status='revoked' where locrd=?", (locrd,)); s.db.commit()
        s.emit(person, "PasskeyRevoked", {"lynkid": s._lynkid(person), "locrd": locrd}, now)
    # ---- sessions and sign-in alerts (takeover safeguard 1)
    def sign_in(s, person, site, device_name, place, now=None):
        if site not in SITES: raise ValueError("unknown site")
        seen = s.db.execute("select device_name,place from acct_sessions where person=?", (person,)).fetchall()
        new_device, new_place = device_name not in {d for d, _ in seen}, place not in {p for _, p in seen}
        tok = s.auth.sign_in(person, site, now)
        s.db.execute("insert into acct_sessions values(?,?,?,?,?,?,null)", (tok, person, site, device_name, place, _now(now))); s.db.commit()
        s.emit(person, "SessionStarted", {"lynkid": s._lynkid(person), "site": site, "device_name": device_name, "new_device": new_device and bool(seen), "new_place": new_place and bool(seen)}, now)
        s.protect.seen(person, now)                                  # the owner is active: the successor clock resets
        if new_device and seen: s.protect.start_cool_off(person, "new_device", now)
        return tok
    def sessions(s, person, now=None):
        return [{"token_tail": r[0][-4:], "site": r[1], "device_name": r[2], "place": r[3], "started": r[4]} for r in
                s.db.execute("select token,site,device_name,place,started from acct_sessions where person=? and revoked is null order by started desc", (person,))]
    def revoke_session(s, person, token_tail, by="security_center", now=None):
        for (tok, site) in s.db.execute("select token,site from acct_sessions where person=? and revoked is null", (person,)).fetchall():
            if tok.endswith(token_tail):
                s.db.execute("update acct_sessions set revoked=? where token=?", (_now(now), tok)); s.db.execute("delete from isessions where token=?", (tok,)); s.db.commit()
                s.emit(person, "SessionRevoked", {"lynkid": s._lynkid(person), "site": site, "by": by}, now); return True
        return False
    def sign_out_everywhere(s, person, now=None):
        for r in s.sessions(person): s.revoke_session(person, r["token_tail"], "self", now)
        s.idp.revoke_sessions(person, now)
    # ---- Security Center (blueprint 22)
    def security_center(s, person, now=None):
        lid = s._lynkid(person)
        events = [e for e in s.c.store.of(person, "SessionStarted", "SessionRevoked", "PasskeyEnrolled", "PasskeyRevoked", "RecoveryStarted", "RecoveryCompleted", "RecoveryCancelled", "PayoutChangeRequested", "PayoutChangeApplied", "ConsentGranted", "ConsentWithdrawn", "SecurityAlertSent")][-30:]
        rec = s.db.execute("select recovery_hash,backup_contact from identities where person=?", (person,)).fetchone()
        devices = s.db.execute("select device_id,role,restricted_until from idevices where person=? and revoked_at is null", (person,)).fetchall()
        return {"lynkid": lid, "passkeys": s.passkeys(person), "sessions": s.sessions(person, now),
                "events": [{"type": e["type"], "at": e["ts"], "payload": {k: v for k, v in e["payload"].items() if k != "lynkid"}} for e in reversed(events)],
                "recovery": {"code_set": bool(rec and rec[0]), "backup_contact_set": bool(rec and rec[1]), "second_device": len(devices) > 1,
                             "restricted_until": max([d[2] or 0 for d in devices] or [0])},
                "connected_apps": [c for c in s.consents(person, now) if c["scope"] in ("developer-app", "accountant", "lender", "health-pack", "supplier-sell-through")],
                "memberships": s.memberships(person)}
    # ---- data-sharing consents (every screen that shares data)
    def grant_consent(s, person, scope, grantee, purpose, days, now=None):
        if scope not in CONSENT_SCOPES: raise ValueError("unknown consent scope")
        if not purpose: raise ValueError("a consent names its purpose")
        days = min(int(days), MAX_CONSENT_DAYS[scope])
        i = uuid.uuid4().hex; locns = s.ids.assign("CNS", i); exp = _now(now) + days * DAY
        s.db.execute("insert into acct_consents values(?,?,?,?,?,?,?,null,0)", (locns, person, scope, grantee, purpose, _now(now), exp)); s.db.commit()
        s.emit(person, "ConsentGranted", {"lynkid": s._lynkid(person), "locns": locns, "scope": scope, "grantee": grantee, "expires_at": exp}, now); return locns
    def withdraw_consent(s, person, locns, by="self", now=None):
        s.db.execute("update acct_consents set withdrawn=? where locns=? and person=?", (_now(now), locns, person)); s.db.commit()
        s.emit(person, "ConsentWithdrawn", {"lynkid": s._lynkid(person), "locns": locns, "by": by}, now)
    def consents(s, person, now=None, include_ended=False):
        rows = s.db.execute("select locns,scope,grantee,purpose,granted,expires,withdrawn from acct_consents where person=? order by granted desc", (person,)).fetchall()
        out = [{"locns": r[0], "scope": r[1], "grantee": r[2], "purpose": r[3], "granted": r[4], "expires": r[5], "withdrawn": r[6], "active": r[6] is None and r[5] > _now(now)} for r in rows]
        return out if include_ended else [c for c in out if c["active"]]
    def consent_allows(s, person, scope, grantee, now=None):
        return any(c["scope"] == scope and c["grantee"] == grantee for c in s.consents(person, now))
    def consents_ending(s, within_days, now=None):
        """For the consent-expiry automation: active consents that end within the window and were not warned yet, and ones just ended."""
        n = _now(now); ending, ended = [], []
        for r in s.db.execute("select locns,person,expires,warned from acct_consents where withdrawn is null").fetchall():
            if r[2] <= n: ended.append({"locns": r[0], "person": r[1]})
            elif r[2] - n <= within_days * DAY and not r[3]: ending.append({"locns": r[0], "person": r[1], "expires": r[2]})
        return ending, ended
    def mark_warned(s, locns): s.db.execute("update acct_consents set warned=1 where locns=?", (locns,)); s.db.commit()
    # ---- takeover safeguards 2 and 3: payout change waits; export needs a step-up
    def request_payout_change(s, person, org, second_device_ok=False, now=None):
        lid = s._lynkid(person); oid = s.ids.public_for("OID", org)
        if s.idp.role_of(person, org) != "owner": raise PermissionError("only an owner changes payout details")
        m = s.protect.may(person, "payout_change", now)
        if not m["ok"]: return {"status": "held", **m}
        i = uuid.uuid4().hex
        if second_device_ok:
            s.db.execute("insert into acct_payout values(?,?,?,?,'applied')", (i, person, org, _now(now))); s.db.commit()
            s.emit(person, "PayoutChangeApplied", {"lynkid": lid, "lynkoid": oid, "approved_by": "second_device"}, now); return {"id": i, "status": "applied"}
        ready = _now(now) + PAYOUT_WAIT_S
        s.db.execute("insert into acct_payout values(?,?,?,?,'waiting')", (i, person, org, ready)); s.db.commit()
        s.emit(person, "PayoutChangeRequested", {"lynkid": lid, "lynkoid": oid, "ready_at": ready}, now)
        s.emit(person, "SecurityAlertSent", {"lynkid": lid, "kind": "payout_change", "channels": ["push", "email"]}, now)
        return {"id": i, "status": "waiting", "ready_at": ready}
    # ---- held until reached (owner, 2026-11-26): LynkOmni never texts; when no free channel delivered the alert about a change,
    #      the change waits until the person opens the alert or confirms on a device they used before (catalog/messages.v1.json)
    HOLD_KINDS = ("payout_change", "contact_change")
    HOLD_CLEARED_BY = ("read", "known_device")

    def hold_unreached(s, person, kind, ref, now=None):
        """Cloud only: the alert about this change reached the person on no free channel, so the change is held."""
        if kind not in s.HOLD_KINDS: raise ValueError("only payout and contact changes are held")
        if s.db.execute("select 1 from acct_holds where ref=?", (ref,)).fetchone(): return False
        s.db.execute("insert into acct_holds values(?,?,?,?,null,null)", (ref, person, kind, _now(now))); s.db.commit()
        s.emit(person, "ChangeHeldUntilReached", {"lynkid": s._lynkid(person), "kind": kind}, now)
        return True

    def reached(s, person, ref, how, now=None, device=None):
        """The person opened the alert, or confirmed on a device they used before: the held change may go on when its wait is over."""
        if how not in s.HOLD_CLEARED_BY: raise ValueError("a hold ends only when the alert is read or confirmed on a known device")
        r = s.db.execute("select person, cleared from acct_holds where ref=?", (ref,)).fetchone()
        if not r or r[0] != person: raise PermissionError("only the person the change belongs to")
        if r[1] is not None: return False
        if how == "known_device" and not (device and s.ways.known_device(person, device)):
            raise PermissionError("confirm on a device you have used before")
        s.db.execute("update acct_holds set cleared=?, how=? where ref=?", (_now(now), how, ref)); s.db.commit()
        s.emit(person, "ChangeHoldCleared", {"lynkid": s._lynkid(person), "how": how}, now)
        return True

    def on_hold(s, ref):
        return s.db.execute("select 1 from acct_holds where ref=? and cleared is null", (ref,)).fetchone() is not None

    def apply_payout_change(s, person, change_id, now=None):
        r = s.db.execute("select org,ready_at,status from acct_payout where id=? and person=?", (change_id, person)).fetchone()
        if not r or r[2] != "waiting": raise PermissionError("no waiting change")
        if s.on_hold(change_id): raise PermissionError("held: the alert about this change has not reached you yet")
        if _now(now) < r[1]: raise PermissionError("the waiting period is not over")
        s.db.execute("update acct_payout set status='applied' where id=?", (change_id,)); s.db.commit()
        s.emit(person, "PayoutChangeApplied", {"lynkid": s._lynkid(person), "lynkoid": s.ids.public_for("OID", r[0]), "approved_by": "waiting_period"}, now)
    def cancel_payout_change(s, person, change_id, by, now=None):
        r = s.db.execute("select org from acct_payout where id=? and person=? and status='waiting'", (change_id, person)).fetchone()
        if not r: raise PermissionError("no waiting change")
        s.db.execute("update acct_payout set status='cancelled' where id=?", (change_id,)); s.db.commit()
        s.emit(person, "PayoutChangeCancelled", {"lynkid": s._lynkid(person), "lynkoid": s.ids.public_for("OID", r[0]), "by": by}, now)
    def can_export(s, person, stepup_token, device_id=None, now=None):
        """Exports need a fresh step-up, and never from a device still restricted after a recovery."""
        if not s.auth.stepup_valid(stepup_token, now=now): return False
        if not s.protect.may(person, "data_export", now)["ok"]: return False
        return device_id is None or s.auth.device_can(device_id, "export_data", now)
    # ---- privacy and data: download my records, close the account
    def open_data_request(s, person, now=None):
        i = uuid.uuid4().hex; due = _now(now) + DATA_REQUEST_DAYS * DAY
        s.db.execute("insert into acct_requests values(?,?,?,?,null,null)", (i, person, _now(now), due)); s.db.commit()
        s.emit(person, "DataRequestOpened", {"lynkid": s._lynkid(person), "request_id": i, "due_at": due}, now); return {"request_id": i, "due_at": due}
    def mark_data_ready(s, request_id, now=None):
        person = s.db.execute("select person from acct_requests where id=?", (request_id,)).fetchone()[0]
        exp = _now(now) + 7 * DAY; s.db.execute("update acct_requests set ready=?, expires=? where id=?", (_now(now), exp, request_id)); s.db.commit()
        s.emit(person, "DataRequestReady", {"lynkid": s._lynkid(person), "request_id": request_id, "expires_at": exp}, now)
    def data_requests_due(s, within_days, now=None):
        n = _now(now)
        return [{"request_id": r[0], "person": r[1], "due_at": r[2]} for r in s.db.execute("select id,person,due from acct_requests where ready is null").fetchall() if r[2] - n <= within_days * DAY]
    def request_close(s, person, stepup_token, now=None):
        if not s.auth.stepup_valid(stepup_token, now=now): raise PermissionError("closing an account needs a fresh step-up")
        closes = _now(now) + CLOSE_GRACE_DAYS * DAY
        s.db.execute("update acct_people set status='closing', closes_at=? where person=?", (closes, person)); s.db.commit()
        s.emit(person, "AccountCloseRequested", {"lynkid": s._lynkid(person), "closes_at": closes}, now); return closes
    def cancel_close(s, person): s.db.execute("update acct_people set status='active', closes_at=null where person=?", (person,)); s.db.commit()
    def close_if_due(s, person, now=None):
        r = s.db.execute("select status,closes_at,lynkid from acct_people where person=?", (person,)).fetchone()
        if r[0] != "closing" or _now(now) < r[1]: return False
        s.sign_out_everywhere(person, now); s.idp.close_person(person); s.p.vault.delete_subject(person)
        s.db.execute("update acct_people set status='closed' where person=?", (person,)); s.db.commit()
        s.emit(person, "AccountClosed", {"lynkid": r[2]}, now); return True                      # the LynkID and the username stay reserved for ever
    # ---- businesses and the accountant's client switcher
    def memberships(s, person):
        rows = s.db.execute("select o.lynkoid,o.name,m.role,o.internal from members m join orgs o on o.internal=m.org where m.person=? and m.status='active'", (person,)).fetchall()
        return [{"lynkoid": r[0], "name": r[1], "role": r[2], "internal": r[3]} for r in rows]
    def clients(s, person, now=None):
        """The accountant's client switcher: the businesses that made this person their accountant, with the owner's consent state."""
        out = []
        for m in s.memberships(person):
            if m["role"] != "accountant": continue
            owner = s.idp._owners(m["internal"])
            ok = bool(owner) and s.consent_allows(owner[0], "accountant", s._lynkid(person), now)
            out.append({**m, "consent": "active" if ok else "missing"})
        return out
    def leave(s, person, org, now=None):
        if s.idp.role_of(person, org) == "owner" and len(s.idp._owners(org)) == 1: raise PermissionError("the last owner cannot leave: transfer ownership first")
        s.db.execute("update members set status='removed' where org=? and person=?", (org, person)); s.db.commit()
        s.emit(person, "MembershipLeft", {"lynkid": s._lynkid(person), "lynkoid": s.ids.public_for("OID", org)}, now)
    # ---- subscriptions and billing (read only; prices come from services/billing.py)
    def subscriptions(s, person):
        out = []
        for m in s.memberships(person):
            eff = s.p.billing.effective(m["internal"])
            out.append({"lynkoid": m["lynkoid"], "name": m["name"], "plans": {f: v for f, v in eff.items() if v["tier"] != "free"}, "bill": s.p.billing.bill(m["internal"]) if any(v["tier"] != "free" for v in eff.values()) else None})
        return out
    # ---- N14 Start a business
    def start_business(s, person, country, now=None):
        av = providers.availability("registration", country)
        if av["state"] != "available": return {"state": "coming_soon", "message": av["message"], "notify_me": True}
        i = uuid.uuid4().hex; lodoc = s.ids.assign("DOC", i)
        s.db.execute("insert into acct_apps values(?,?,?,?,?,?,null,null)", (i, person, lodoc, country, json.dumps({k: False for k in REGISTRATION_STEPS}), "started")); s.db.commit()
        s.emit(person, "RegistrationStarted", {"lynkid": s._lynkid(person), "application_id": i, "country": country}, now)
        return {"state": "available", "application_id": i, "lodoc": lodoc, "steps": list(REGISTRATION_STEPS)}
    def complete_step(s, application_id, step):
        if step not in REGISTRATION_STEPS: raise ValueError("unknown step")
        steps = json.loads(s.db.execute("select steps from acct_apps where application_id=?", (application_id,)).fetchone()[0]); steps[step] = True
        s.db.execute("update acct_apps set steps=? where application_id=?", (json.dumps(steps), application_id)); s.db.commit(); return steps
    def submit_application(s, application_id, now=None):
        r = s.db.execute("select person,country,steps,status from acct_apps where application_id=?", (application_id,)).fetchone()
        steps = json.loads(r[2])
        if not all(steps[k] for k in ("profile", "registration", "tax_number")): raise ValueError("finish profile, registration and tax number first")
        ref = s.gateway.submit({"application_id": application_id, "country": r[1], "steps": steps})["reference"]
        s.db.execute("update acct_apps set status='submitted', gateway_ref=? where application_id=?", (ref, application_id)); s.db.commit()
        s.emit(r[0], "RegistrationSubmitted", {"lynkid": s._lynkid(r[0]), "application_id": application_id, "country": r[1], "gateway": "registration_gateway"}, now)
        if steps.get("bank_account"): s.emit(r[0], "BankAccountReferred", {"lynkid": s._lynkid(r[0]), "application_id": application_id, "partner": "registration_gateway"}, now)
        return ref
    def poll_application(s, application_id, now=None):
        """Only the gateway's answer changes the status: LynkOmni never claims approval first."""
        r = s.db.execute("select person,country,status from acct_apps where application_id=?", (application_id,)).fetchone()
        if r[2] != "submitted": return r[2]
        res = s.gateway.result(application_id)
        if res["status"] == "approved":
            org = s.idp.register_org(r[0], f"Business {application_id[:6]}", country=r[1])
            s.db.execute("update acct_apps set status='approved', lynkoid=? where application_id=?", (org["lynkoid"], application_id)); s.db.commit()
            s.emit(r[0], "RegistrationApproved", {"lynkid": s._lynkid(r[0]), "application_id": application_id, "lynkoid": org["lynkoid"]}, now)
        elif res["status"] == "rejected":
            s.db.execute("update acct_apps set status='rejected' where application_id=?", (application_id,)); s.db.commit()
            s.emit(r[0], "RegistrationRejected", {"lynkid": s._lynkid(r[0]), "application_id": application_id, "reason_code": res.get("reason_code", "unknown")}, now)
        return s.db.execute("select status from acct_apps where application_id=?", (application_id,)).fetchone()[0]
    def applications(s, person):
        return [{"application_id": r[0], "lodoc": r[1], "country": r[2], "steps": json.loads(r[3]), "status": r[4], "lynkoid": r[5]} for r in
                s.db.execute("select application_id,lodoc,country,steps,status,lynkoid from acct_apps where person=?", (person,))]
    # ---- N4 standing payments (the customer's own capped instruction, held by the licensed provider)
    def approve_standing(s, person, merchant, cap_minor, currency, country, now=None):
        ok, reasons = providers.ready("paylinks", country)
        if not ok: raise PermissionError("standing payments wait for the licensed provider in this country: " + "; ".join(reasons))
        if int(cap_minor) <= 0: raise ValueError("a standing payment needs a cap above zero")
        i = uuid.uuid4().hex; losub = s.ids.assign("SUB", i); prov = providers.needs("paylinks", country)[0]["id"]
        s.db.execute("insert into acct_standing values(?,?,?,?,?,?,?,null,0)", (losub, person, merchant, int(cap_minor), currency, prov, _now(now))); s.db.commit()
        s.emit(person, "StandingPaymentApproved", {"lynkid": s._lynkid(person), "losub": losub, "merchant": merchant, "cap_minor": int(cap_minor), "currency": currency, "provider": prov}, now); return losub
    def standing_charge_allowed(s, losub, amount_minor, now=None):
        """Each use is within the cap and the customer is told every time (the provider confirms the charge, LynkOmni holds nothing)."""
        r = s.db.execute("select cap_minor,revoked from acct_standing where losub=?", (losub,)).fetchone()
        return bool(r and r[1] is None and int(amount_minor) <= r[0])
    def revoke_standing(s, person, losub, by="self", now=None):
        s.db.execute("update acct_standing set revoked=? where losub=? and person=?", (_now(now), losub, person)); s.db.commit()
        s.emit(person, "StandingPaymentRevoked", {"lynkid": s._lynkid(person), "losub": losub, "by": by}, now)
    def standing_payments(s, person):
        return [{"losub": r[0], "merchant": r[1], "cap_minor": r[2], "currency": r[3], "provider": r[4], "active": r[5] is None} for r in
                s.db.execute("select losub,merchant,cap_minor,currency,provider,revoked from acct_standing where person=?", (person,))]
    # ---- payslips (N2): read only; LynkAcc payroll writes them in build section 4
    def payslips(s, person): return [{"lodoc": e["payload"]["lodoc"], "period": e["payload"]["period"], "employer": e["payload"]["lynkoid"]} for e in s.c.store.of(person, "payslip.issued")]
    # ---- the whole account site, page by page
    def pages(s): return PAGES
