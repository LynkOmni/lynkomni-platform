"""The phone owner check (section 4C point 4, catalog/ways-in.v1.json phone_owner, identity/phone_owner.py).
LynkOmni never pays for a check and the person never does (owner, 2026-11-26)."""
import json, os, unittest

from core import ways_in as WI
from services.platform import Platform
from services.phone_owner_partners import SandboxNetworkOwnerMatch
from tests._signup import confirm_contacts

T0, H, DAY = 1_800_000_000, 3600, 86400
EMP = "employer_verification"


class Spy(SandboxNetworkOwnerMatch):
    def __init__(self):
        self.sent = []
    def kyc_match(self, request_id, number_ref, name_ref, country):
        self.sent.append(("kyc", number_ref, name_ref, country)); return super().kyc_match(request_id, number_ref, name_ref, country)
    def sim_swap(self, request_id, number_ref, country):
        self.sent.append(("sim", number_ref, country)); return super().sim_swap(request_id, number_ref, country)


class PhoneOwnerCheck(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.a = self.p.account
        from identity.phone_owner import PhoneOwner
        self.spy = Spy()
        self.o = PhoneOwner(self.a, partner=self.spy, network_ready=lambda c: c == "NETWORK")

    def person(self, username="grace.k"):
        s = self.a.begin_sign_up(username, "en", T0, adult_confirmed=True)
        confirm_contacts(self.a, s["person"], T0)
        self.a.finish_sign_up(s["person"], f"pk-{username}", "phone", f"pii_p_{username}", f"pii_e_{username}", now=T0)
        return s["person"]

    def events(self, person, type_):
        return [e for e in self.p.c.store.since(person) if e["type"] == type_]

    def test_only_the_registered_activities_and_only_with_consent(self):
        p = self.person()
        with self.assertRaises(ValueError):
            self.o.start(p, "sign_in", True, "NETWORK", now=T0)
        with self.assertRaises(ValueError, msg="getting back into an account uses the free ways of the hub, never a paid check"):
            self.o.start(p, "recovery", True, "NETWORK", now=T0)
        with self.assertRaises(PermissionError):
            self.o.start(p, EMP, False, "NETWORK", now=T0, requester="employer-ws")
        self.assertTrue(self.o.may_go(p, "cash_sale", T0), "everyday use never needs the check")
        self.assertFalse(self.o.may_go(p, "payouts", T0))

    def test_lynkomni_never_pays_a_partner_or_the_one_who_asks_pays(self):
        self.assertFalse(WI.OWNER["cost"]["lynkomni_pays"]); self.assertFalse(WI.OWNER["cost"]["person_pays"])
        self.assertEqual(set(WI.OWNER["payers"]), set(WI.OWNER["activities"]))
        self.assertLessEqual(set(WI.OWNER["payers"].values()), {"partner", "requester"})
        p = self.person()
        with self.assertRaises(PermissionError, msg="nothing is sent until the one who pays is named"):
            self.o.start(p, EMP, True, "NETWORK", now=T0)
        self.assertEqual(self.spy.sent, [])
        r = self.o.start(p, "payouts", True, "NETWORK", now=T0)
        self.assertEqual((r["method"], r["payer"]), ("partner", "partner"), "a partner's service uses the partner's own identity check")
        self.assertEqual(self.spy.sent, [], "no paid network check for a partner's service")
        self.assertEqual(self.o.payer_of(r["lover"]), "partner")
        self.a.partner_identity_answer(r["lover"], True, "sandbox-identity", T0 + 60)
        self.assertTrue(self.o.may_go(p, "payouts", T0 + 61))
        e = self.o.start(self.person("emp.check"), EMP, True, "NETWORK", now=T0, requester="employer-ws")
        self.assertEqual(self.o.payer_of(e["lover"]), "employer-ws")

    def test_the_network_gets_vault_references_and_answers_in_the_cloud(self):
        p = self.person()
        r = self.o.start(p, EMP, True, "NETWORK", now=T0, requester="employer-ws")
        self.assertEqual((r["state"], r["method"], r["payer"]), ("sent", "network", "requester"))
        self.assertTrue(r["lover"].startswith("LOVER-"))
        self.assertEqual([x[0] for x in self.spy.sent], ["kyc", "sim"], "the SIM change check runs at the same time")
        self.assertTrue(all(x[1].startswith("vault:") and x[2].startswith("vault:") for x in self.spy.sent if x[0] == "kyc"))
        self.assertFalse(self.o.may_go(p, EMP, T0), "the sandbox never says match by itself")
        out = self.o.network_answer(r["lover"], "match", None, T0 + 60)
        self.assertEqual((out["state"], out["result"]), ("confirmed", "go"))
        self.assertTrue(self.o.may_go(p, EMP, T0 + 120))
        again = self.o.network_answer(r["lover"], "no_match", None, T0 + 90)
        self.assertEqual(again["state"], "confirmed", "a repeated answer changes nothing")
        self.assertEqual(self.o.start(p, "landlord_verification", True, "NETWORK", now=T0 + 200, requester="landlord-ws")["reused"], True)
        self.assertFalse(self.o.may_go(p, EMP, T0 + 181 * DAY), "a match is kept for a time only")
        self.assertFalse(self.o.may_go(p, EMP, T0 + 300, sim_changed_at=T0 + 200), "a SIM change since the match asks again")
        self.assertFalse(self.o.may_go(p, EMP, T0 + 300, number_changed=True))

    def test_partial_no_match_and_a_recent_sim_change(self):
        p = self.person()
        a = self.o.start(p, EMP, True, "NETWORK", now=T0, requester="employer-ws")
        self.assertEqual(self.o.network_answer(a["lover"], "partial", None, T0)["fixes"], ["check_spelling", "id_document"])
        b = self.o.start(p, "landlord_verification", True, "NETWORK", now=T0 + 1, requester="landlord-ws")
        stop = self.o.network_answer(b["lover"], "no_match", None, T0 + 2)
        self.assertEqual((stop["state"], stop["fixes"]), ("failed", ["check_number", "id_document"]))
        c = self.o.start(p, "public_election", True, "NETWORK", now=T0 + 3, requester="organiser-ws")
        w = self.o.network_answer(c["lover"], "match", T0 - H, T0 + 4)
        self.assertEqual((w["state"], w["until"]), ("waiting", T0 - H + WI.OWNER["sim_swap_wait_hours"] * H))
        self.assertFalse(self.o.may_go(p, "public_election", T0 + 5))
        self.assertFalse(self.o.wait_over(c["lover"], T0 + 5))
        self.assertTrue(self.o.wait_over(c["lover"], T0 + 80 * H))
        self.assertEqual(self.o.state(c["lover"])["state"], "sent", "after the wait the network is asked again")

    def test_without_a_network_the_id_document_check_is_used(self):
        p = self.person()
        r = self.o.start(p, EMP, True, "ELSEWHERE", now=T0, requester="employer-ws")
        self.assertEqual((r["state"], r["method"]), ("sent", "id_document"))
        self.assertEqual(self.spy.sent, [], "no network is asked where none is signed")
        self.a.partner_identity_answer(r["lover"], True, "sandbox-identity", T0 + 60)
        self.assertTrue(self.o.may_go(p, EMP, T0 + 61))
        b = self.o.start(self.person("shop.owner"), EMP, True, "NETWORK", business_ref="pii_registered", now=T0, requester="employer-ws")
        self.assertEqual(b["method"], "owner_id_document", "a business without registered-name support uses the owner's ID check")
        c = self.o.start(self.person("shop.two"), EMP, True, "NETWORK", business_ref="pii_registered2", registered_name_supported=True, now=T0, requester="employer-ws")
        self.assertEqual(c["method"], "registered_name")
        self.assertEqual(self.spy.sent[0][2], "vault:pii_registered2")

    def test_no_event_carries_a_name_or_number_and_the_default_is_off(self):
        p = self.person()
        r = self.o.start(p, EMP, True, "NETWORK", now=T0, requester="employer-ws")
        self.o.network_answer(r["lover"], "match", None, T0 + 1)
        evs = self.events(p, "PhoneOwnerCheckRequested") + self.events(p, "PhoneOwnerCheckAnswered")
        self.assertEqual(len(evs), 2)
        self.assertEqual(evs[0]["payload"]["payer"], "requester")
        blob = json.dumps([e["payload"] for e in evs])
        for secret in ("pii_p_grace.k", "pii_legal", "Grace", "vault:", "employer-ws"):
            self.assertNotIn(secret, blob)
        from identity.phone_owner import PhoneOwner
        self.assertEqual(PhoneOwner(self.a).start(self.person("fresh.one"), EMP, True, "RW", now=T0 + 2, requester="employer-ws")["method"], "id_document",
                         "the network stays off for real users until a mobile partner is signed")
