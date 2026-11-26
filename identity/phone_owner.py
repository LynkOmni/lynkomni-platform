"""The phone owner check (section 4C point 4, master blueprint section 87): only for the activities that need the real owner of
a number (catalog/ways-in.v1.json phone_owner), never for everyday sign-up or sign-in. Rules only from core/ways_in.py.

- Always with the person's consent ("phone-owner-check").
- Where the mobile network offers it (core.regions.enabled(country, "phone_owner_match"): the flag and a signed network), the legal name and the number go to the
  network as vault references; a business uses its registered name where supported. Elsewhere the licensed identity partner's
  ID document check is used (Account.request_identity_check), for a business the owner's own.
- The network's answer is written by the cloud alone (network_answer). Match goes ahead; partial asks to check the spelling or
  use the ID document; no match stops with the reason and the fix; a recent SIM change makes the activity wait.
- Kept as a verification record (LOVER-). No event carries a name or a number; the network's own name is never kept.
- LynkOmni never pays for a check and the person never does (owner, 2026-11-26): for a licensed partner's service (payouts, cards,
  agent points, exchange, a first paid Storefront offer) the partner checks identity as part of its own legal duty; employer,
  landlord and election checks are paid by the one who asks (requester), who must be named before anything is sent.
"""
import time, uuid

from core import ways_in as WI
from core.regions import enabled
from services.phone_owner_partners import SandboxNetworkOwnerMatch

STATE_OF = {"go": "confirmed", "fix": "partial", "stop": "failed", "wait": "waiting"}


def _vault(ref):
    """The account keeps plain vault references; a partner gets them marked as vault references."""
    return ref if ref.startswith("vault:") else "vault:" + ref


def _now(n):
    return time.time() if n is None else n


class PhoneOwner:
    def __init__(self, account, partner=None, network_ready=None):
        self.a, self.db = account, account.db
        self.partner = partner or SandboxNetworkOwnerMatch()
        self.network_ready = network_ready or (lambda country: enabled(country, WI.OWNER["partner_service"]))
        self.db.executescript("""
        create table if not exists po_checks(lover text primary key, person text, activity text, method text, country text, state text,
                                             result text, until real, requested real, answered real, payer text);""")

    # ---- starting a check ---------------------------------------------------------------------------------------------
    def start(self, person, activity, consent, country, business_ref=None, registered_name_supported=False, now=None, requester=None):
        """Starts the check for one activity. Returns {"state", "method", "lover", "payer"}; "sent" until the answer comes.
        A requester activity needs the requester (the employer, landlord or organiser who pays) named first."""
        now = _now(now)
        if not WI.owner_check_needed(activity):
            raise ValueError("this activity does not need the phone owner check")
        if not consent:
            raise PermissionError("the phone owner check needs the person's consent")
        payer = WI.owner_payer(activity)
        if payer == "requester" and not requester:
            raise PermissionError("the one who asks for this check pays for it: name them before anything is sent; LynkOmni never pays")
        if self.may_go(person, activity, now):
            return {"state": "confirmed", "method": self.last(person)["method"], "lover": self.last(person)["lover"], "reused": True, "payer": payer}
        business = business_ref is not None
        method = WI.owner_check_method(self.network_ready(country), business, registered_name_supported, payer)
        if method in ("partner", "id_document", "owner_id_document"):
            r = self.a.request_identity_check(person, purpose=activity, now=now)
            self._save(r["lover"], person, activity, method, country, r["state"], now, payer if payer == "partner" else requester)
            return {"state": r["state"], "method": method, "lover": r["lover"], "payer": payer}
        number_ref = _vault(self._number_ref(person))
        name_ref = _vault(business_ref if business else self._legal_ref(person))
        lover = self.a.ids.assign("VER", uuid.uuid4().hex)
        sent = self.partner.kyc_match(lover, number_ref, name_ref, country)
        if not sent.get("ok"):
            raise ValueError(sent.get("reason", "the network refused the request"))
        self.partner.sim_swap(lover, number_ref, country)           # the SIM change check runs at the same time
        self._save(lover, person, activity, method, country, "sent", now, requester)
        self.a.emit(person, "PhoneOwnerCheckRequested", {"lynkid": self.a._lynkid(person), "activity": activity, "method": method, "lover": lover, "payer": payer}, now)
        return {"state": "sent", "method": method, "lover": lover, "payer": payer}

    # ---- the network's answer (cloud only) ---------------------------------------------------------------------------------
    def network_answer(self, lover, answer, sim_changed_at, now=None):
        """Cloud only, from the network partner's answer: match, partial or no_match, and the last SIM change. Nothing on a
        device can write it. A repeated answer changes nothing."""
        now = _now(now)
        r = self.db.execute("select person, activity, state from po_checks where lover=?", (lover,)).fetchone()
        if not r:
            raise ValueError("no phone owner check")
        if r[2] != "sent":
            return self.state(lover)
        out = WI.owner_check_outcome(answer, sim_changed_at, now)
        state = STATE_OF[out["result"]]
        self.db.execute("update po_checks set state=?, result=?, until=?, answered=? where lover=?", (state, out["result"], out["until"], now, lover)); self.db.commit()
        self.a.emit(r[0], "PhoneOwnerCheckAnswered", {"lynkid": self.a._lynkid(r[0]), "lover": lover, "activity": r[1], "result": out["result"]}, now)
        return {**self.state(lover), "fixes": out["fixes"]}

    def wait_over(self, lover, now=None):
        """A check waiting after a SIM change asks the network again once the wait is over."""
        now = _now(now)
        r = self.db.execute("select state, until from po_checks where lover=?", (lover,)).fetchone()
        if not r or r[0] != "waiting" or now < r[1]:
            return False
        self.db.execute("update po_checks set state='sent', until=null where lover=?", (lover,)); self.db.commit()
        return True

    # ---- reading --------------------------------------------------------------------------------------------------------
    def state(self, lover):
        r = self.db.execute("select lover, activity, method, state, result, until from po_checks where lover=?", (lover,)).fetchone()
        return None if not r else {"lover": r[0], "activity": r[1], "method": r[2], "state": r[3], "result": r[4], "until": r[5]}

    def last(self, person):
        r = self.db.execute("select lover from po_checks where person=? order by requested desc, rowid desc", (person,)).fetchone()
        return None if not r else self.state(r[0])

    def may_go(self, person, activity, now=None, number_changed=False, sim_changed_at=None):
        """True when the person's number has a valid network match, or their ID document check is confirmed."""
        now = _now(now)
        if not WI.owner_check_needed(activity):
            return True
        m = self.db.execute("select max(answered) from po_checks where person=? and state='confirmed' and method in ('network','registered_name')", (person,)).fetchone()[0]
        if WI.owner_match_valid(m, now, number_changed, sim_changed_at):
            return True
        return self.a.identity_confirmed(person)

    # ---- helpers --------------------------------------------------------------------------------------------------------
    def _save(self, lover, person, activity, method, country, state, now, payer):
        self.db.execute("insert or replace into po_checks values(?,?,?,?,?,?,null,null,?,null,?)", (lover, person, activity, method, country, state, now, payer)); self.db.commit()

    def payer_of(self, lover):
        """Who pays this check: "partner" or the requester who asked; never LynkOmni and never the person."""
        r = self.db.execute("select payer from po_checks where lover=?", (lover,)).fetchone()
        return None if not r else r[0]

    def _number_ref(self, person):
        r = self.a.auth.db.execute("select phone from identities where person=?", (person,)).fetchone()
        if not r or not r[0]:
            raise ValueError("the account has no confirmed phone number")
        return r[0]

    def _legal_ref(self, person):
        r = self.db.execute("select legal_ref from acct_signup where person=?", (person,)).fetchone()
        if not r or not r[0]:
            raise ValueError("the account has no legal name")
        return r[0]
