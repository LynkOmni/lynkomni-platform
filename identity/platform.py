"""LynkOmni Identity Platform (reference). One LynkID per person, one LynkOID per organization, scoped memberships, default-deny
authorization, PIN and passkey credentials, verification cases, merchant-scoped customer references and time-limited support access.
Stage gating: the pilot runs the core and authentication stages only. Verification (KYC/KYB) activates with the first regulated service.
Argon2id is the production password hash; this reference uses scrypt because the Python standard library has no Argon2id."""
import hashlib, hmac, json, os, secrets, time, uuid
from contract.tools.validate_contract import PERMS
from services.suite import ServiceOff

OFFLINE_DAYS = {"owner": 7, "manager": 7, "cashier": 14}        # how long a role may stay offline before re-authenticating
STAFF_PERMS = {"support_agent": {"case.view", "conversation.reply", "transfer.request"}, "support_lead": {"case.view", "conversation.reply", "transfer.request", "transfer.accept", "case.reassign"},
               "safety": {"report.view", "report.handle"}, "security": {"vuln.view", "vuln.handle", "report.view"}, "verifier": {"verification.review"}}
MERCHANT_ROLES = ("cashier", "manager", "owner")
HIGH_RISK = {"transfer_ownership", "remove_last_admin", "close_organization", "change_payout", "export_data", "revoke_device"}
STAGES = {"core": True, "authentication": True, "verification": False, "fraud": False, "global": False, "ecosystem": False}   # pilot scope
VERIFY_NEXT = {"not_started": {"pending"}, "pending": {"in_review", "rejected"}, "in_review": {"verified", "additional_evidence_required", "rejected"},
               "additional_evidence_required": {"pending", "rejected"}, "verified": {"expired", "suspended", "revoked"}, "suspended": {"verified", "revoked"},
               "expired": {"pending"}, "rejected": set(), "revoked": set()}
def _now(n): return time.time() if n is None else n

class IdentityPlatform:
    LOCK_AFTER, LOCK_S = 5, 900
    def __init__(s, c, ids, secret=None):
        s.c, s.ids, s.db, s.secret = c, ids, c.store.db, (secret or os.environ.get("LYNK_ID_SECRET", "dev-only-change-me"))
        s.db.executescript("""
        create table if not exists persons(internal text primary key, lynkid text unique, status text, lang text);
        create table if not exists orgs(internal text primary key, lynkoid text unique, name text, kind text, country text, parent text, status text);
        create table if not exists branches(internal text primary key, lobrn text unique, org text, name text);
        create table if not exists members(internal text primary key, lomem text unique, org text, person text, role text, status text);
        create table if not exists creds(internal text primary key, locrd text unique, person text, kind text, hash text, salt text, status text);
        create table if not exists fails(person text, ts real);
        create table if not exists vcases(internal text primary key, lover text unique, kind text, subject text, claim text, jurisdiction text, status text,
                                          method text, source text, source_ok int, evidence text, policy text, opener text, reviewer text, expires real, partner text);
        create table if not exists crefs(org text, person text, cst text, primary key(org, person));
        create table if not exists grants(internal text primary key, locns text unique, subject text, scope text, expires real, revoked int);
        create table if not exists revoked_sessions(person text, before real);""")
    def stage(s, name):
        if os.environ.get("LYNK_MODE") != "sandbox" and not STAGES.get(name): raise ServiceOff(f"identity stage '{name}' is not active yet")
    def audit(s, actor, action, target=None, outcome="ok"): s.c.store.append("_identity", actor or "system", "audit.logged", {"action": action, "target": target, "outcome": outcome})
    # people and organizations
    def register_person(s, lang="en"):
        i = uuid.uuid4().hex; pid = s.ids.assign("ID", i)
        s.db.execute("insert into persons values(?,?,?,?)", (i, pid, "active", lang)); s.db.commit(); s.audit(i, "person_registered", pid); return {"internal": i, "lynkid": pid}
    def close_person(s, person):
        s.db.execute("update persons set status='closed' where internal=?", (person,)); s.db.commit(); s.revoke_sessions(person); s.audit(person, "person_closed")   # the LynkID stays reserved
    def register_org(s, owner, name, kind="merchant", country=None, parent=None):
        i = uuid.uuid4().hex; oid = s.ids.assign("OID", i)
        s.db.execute("insert into orgs values(?,?,?,?,?,?,?)", (i, oid, name, kind, country, parent, "active")); s.db.commit()
        s._member(i, owner, "owner"); s.audit(owner, "org_registered", oid); return {"internal": i, "lynkoid": oid}
    def add_branch(s, org, name):
        i = uuid.uuid4().hex; b = s.ids.assign("BRN", i); s.db.execute("insert into branches values(?,?,?,?)", (i, b, org, name)); s.db.commit(); return b
    def _member(s, org, person, role):
        i = uuid.uuid4().hex; s.db.execute("insert into members values(?,?,?,?,?,?)", (i, s.ids.assign("MEM", i), org, person, role, "active")); s.db.commit(); return i
    # authorization: default deny
    def role_of(s, person, org):
        r = s.db.execute("select role from members where org=? and person=? and status='active'", (org, person)).fetchone(); return r[0] if r else None
    def can(s, person, org, permission):
        role = s.role_of(person, org)
        if role is None: return False
        if role in MERCHANT_ROLES: return any(p["id"] == permission and role in p["roles"] for p in PERMS["permissions"])
        return permission in STAFF_PERMS.get(role, set())
    def _owners(s, org): return [r[0] for r in s.db.execute("select person from members where org=? and role='owner' and status='active'", (org,))]
    def add_member(s, actor, org, person, role):
        if s.role_of(actor, org) != "owner": raise PermissionError("only an owner can add members")
        if role not in MERCHANT_ROLES + tuple(STAFF_PERMS): raise ValueError("unknown role")
        s.audit(actor, "member_added", person); return s._member(org, person, role)
    def change_role(s, actor, org, person, role):
        if s.role_of(actor, org) != "owner": raise PermissionError("only an owner can change roles")
        if s.role_of(person, org) == "owner" and role != "owner" and len(s._owners(org)) == 1: raise PermissionError("the last owner cannot be demoted")
        s.db.execute("update members set role=? where org=? and person=? and status='active'", (role, org, person)); s.db.commit(); s.audit(actor, "role_changed", person)
    def remove_member(s, actor, org, person):
        if s.role_of(actor, org) != "owner": raise PermissionError("only an owner can remove members")
        if s.role_of(person, org) == "owner" and len(s._owners(org)) == 1: raise PermissionError("the last owner cannot be removed")
        s.db.execute("update members set status='removed' where org=? and person=?", (org, person)); s.db.commit(); s.audit(actor, "member_removed", person)
    def transfer_ownership(s, org, from_owner, to_person, stepup_ok=False, accepted_by_target=False):
        """High-risk: needs a fresh step-up AND the receiving person's acceptance. Membership never proves authority by itself."""
        if s.role_of(from_owner, org) != "owner": raise PermissionError("only an owner can transfer ownership")
        if not (stepup_ok and accepted_by_target): raise PermissionError("ownership transfer needs a step-up and the receiver's acceptance")
        if s.role_of(to_person, org) is None: s._member(org, to_person, "owner")
        else: s.db.execute("update members set role='owner' where org=? and person=?", (org, to_person))
        s.db.execute("update members set role='manager' where org=? and person=?", (org, from_owner)); s.db.commit(); s.audit(from_owner, "ownership_transferred", to_person)
    # credentials and sessions
    def _hash(s, secret, salt): return hashlib.scrypt(secret.encode(), salt=salt, n=2 ** 14, r=8, p=1).hex()
    def enroll_pin(s, person, pin):
        if len(pin) < 6 or len(set(pin)) < 3: raise ValueError("choose a PIN of at least 6 digits that is not trivial")
        salt = secrets.token_bytes(16); i = uuid.uuid4().hex
        s.db.execute("update creds set status='replaced' where person=? and kind='pin'", (person,))
        s.db.execute("insert into creds values(?,?,?,?,?,?,?)", (i, s.ids.assign("CRD", i), person, "pin", s._hash(pin, salt), salt.hex(), "active")); s.db.commit()
    def enroll_passkey(s, person, public_key):
        """Registry only. Verifying a WebAuthn assertion needs a reviewed library and the authenticator, so it is not done here."""
        i = uuid.uuid4().hex; s.db.execute("insert into creds values(?,?,?,?,?,?,?)", (i, s.ids.assign("CRD", i), person, "passkey", public_key, "", "active")); s.db.commit()
    def _locked(s, person, now):
        return s.db.execute("select count(*) from fails where person=? and ts>?", (person, now - s.LOCK_S)).fetchone()[0] >= s.LOCK_AFTER
    def sign_in_pin(s, person, pin, channel="device", now=None):
        """channel 'device' (an enrolled phone) gives a full session. 'ussd' (feature phone) gives a limited one that cannot do high-risk actions."""
        now = _now(now)
        if s._locked(person, now): raise PermissionError("too many wrong PINs: try again later")
        r = s.db.execute("select hash,salt from creds where person=? and kind='pin' and status='active'", (person,)).fetchone()
        if not r or not hmac.compare_digest(r[0], s._hash(pin, bytes.fromhex(r[1]))):
            s.db.execute("insert into fails values(?,?)", (person, now)); s.db.commit(); raise PermissionError("wrong PIN")
        s.db.execute("delete from fails where person=?", (person,)); s.db.commit()
        assurance = "full" if channel == "device" else "limited"; exp = int(now + 12 * 3600)
        body = f"{person}|{assurance}|{exp}"; return body + "|" + hmac.new(s.secret.encode(), body.encode(), hashlib.sha256).hexdigest()[:24]
    def session(s, token, now=None):
        try: person, assurance, exp, sig = token.split("|")
        except Exception: return None
        ok = hmac.compare_digest(sig, hmac.new(s.secret.encode(), f"{person}|{assurance}|{exp}".encode(), hashlib.sha256).hexdigest()[:24])
        rv = s.db.execute("select max(before) from revoked_sessions where person=?", (person,)).fetchone()[0] or 0
        return {"person": person, "assurance": assurance} if ok and int(exp) > _now(now) and int(exp) - 12 * 3600 >= rv else None
    def revoke_sessions(s, person, now=None): s.db.execute("insert into revoked_sessions values(?,?)", (person, _now(now) + 1)); s.db.commit()
    def require(s, token, action, now=None):
        sess = s.session(token, now)
        if not sess: raise PermissionError("not signed in")
        if action in HIGH_RISK and sess["assurance"] != "full": raise PermissionError("this action needs a full session, not a feature-phone session")
        return sess
    @staticmethod
    def offline_unlock_allowed(role, days_offline): return days_offline <= OFFLINE_DAYS.get(role, 7)
    # verification (activates with the first regulated service)
    def open_case(s, kind, subject, claim, jurisdiction, policy="v1", opener="system"):
        s.stage("verification"); i = uuid.uuid4().hex
        s.db.execute("insert into vcases values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (i, s.ids.assign("VER", i), kind, subject, claim, jurisdiction, "not_started", None, None, 1, "[]", policy, opener, None, None, None)); s.db.commit(); return i
    def _case(s, i): return s.db.execute("select status,source_ok,opener,jurisdiction,subject,claim from vcases where internal=?", (i,)).fetchone()
    def _move(s, i, to):
        if to not in VERIFY_NEXT[s._case(i)[0]]: raise ValueError(f"cannot go from {s._case(i)[0]} to {to}")
        s.db.execute("update vcases set status=? where internal=?", (to, i)); s.db.commit()
    def submit_evidence(s, i, method, source, source_available, evidence_hashes):
        """Evidence is stored as hashes and category names only. An unavailable source can never produce 'verified'."""
        if s._case(i)[0] == "not_started": s._move(i, "pending")
        s.db.execute("update vcases set method=?, source=?, source_ok=?, evidence=? where internal=?", (method, source, int(source_available), json.dumps(evidence_hashes), i)); s.db.commit(); s._move(i, "in_review")
    def decide(s, i, reviewer, outcome, expires=None):
        st, ok, opener, *_ = s._case(i)
        if reviewer == opener: raise PermissionError("a reviewer cannot decide a case they opened")
        if outcome == "verified" and not ok: outcome = "additional_evidence_required"
        s._move(i, outcome); s.db.execute("update vcases set reviewer=?, expires=? where internal=?", (reviewer, expires, i)); s.db.commit(); s.audit(reviewer, "verification_decided", i, outcome); return outcome
    def attest_partner(s, kind, subject, claim, jurisdiction, partner, outcome, expires=None):
        """A licensed partner did the check. LynkOmni stores the outcome and a reference, never the documents."""
        i = s.open_case(kind, subject, claim, jurisdiction, opener=f"partner:{partner}")
        s.db.execute("update vcases set method='partner_attestation', source=?, partner=?, evidence='[]' where internal=?", (partner, partner, i)); s.db.commit()
        s._move(i, "pending"); s._move(i, "in_review"); s._move(i, "verified" if outcome == "verified" else "rejected")
        s.db.execute("update vcases set expires=? where internal=?", (expires, i)); s.db.commit(); return i
    def is_verified(s, subject, claim, jurisdiction, now=None):
        r = s.db.execute("select expires from vcases where subject=? and claim=? and jurisdiction=? and status='verified' order by rowid desc", (subject, claim, jurisdiction)).fetchall()
        return any(e[0] is None or e[0] > _now(now) for e in r)         # a check in one country is never universal
    def status_view(s, subject):
        """What general support may see: claim, status and expiry. Never evidence, methods or sources."""
        return [{"claim": r[0], "status": r[1], "expires": r[2]} for r in s.db.execute("select claim,status,expires from vcases where subject=?", (subject,))]
    # merchant-scoped customer references and support access grants
    def customer_ref(s, merchant_org, person):
        r = s.db.execute("select cst from crefs where org=? and person=?", (merchant_org, person)).fetchone()
        if r: return r[0]
        ref = s.ids.assign("CST", f"{merchant_org}|{person}"); s.db.execute("insert into crefs values(?,?,?)", (merchant_org, person, ref)); s.db.commit(); return ref
    def grant_support_access(s, subject, scope, hours=24, now=None):
        i = uuid.uuid4().hex; g = s.ids.assign("CNS", i); s.db.execute("insert into grants values(?,?,?,?,?,0)", (i, g, subject, scope, _now(now) + hours * 3600)); s.db.commit(); s.audit(subject, "support_access_granted", g); return g
    def revoke_grant(s, locns): s.db.execute("update grants set revoked=1 where locns=?", (locns,)); s.db.commit()
    def support_access_ok(s, subject, scope, now=None):
        return bool(s.db.execute("select 1 from grants where subject=? and scope=? and revoked=0 and expires>?", (subject, scope, _now(now))).fetchone())
