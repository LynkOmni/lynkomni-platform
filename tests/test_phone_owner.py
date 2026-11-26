"""The phone owner check (section 4C point 4, catalog/ways-in.v1.json phone_owner, identity/phone_owner.py)."""
import json, os, unittest

from core import ways_in as WI
from services.platform import Platform
from services.phone_owner_partners import SandboxNetworkOwnerMatch
from tests._signup import confirm_contacts

T0, H, DAY = 1_800_000_000, 3600, 86400


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
        with self.assertRaises(PermissionError):
            self.o.start(p, "payouts", False, "NETWORK", now=T0)
        self.assertTrue(self.o.may_go(p, "cash_sale", T0), "everyday use never needs the check")
        self.assertFalse(self.o.may_go(p, "payouts", T0))

    def test_the_network_gets_vault_references_and_answers_in_the_cloud(self):
        p = self.person()
        r = self.o.start(p, "payouts", True, "NETWORK", now=T0)
        self.assertEqual((r["state"], r["method"]), ("sent", "network"))
        self.assertTrue(r["lover"].startswith("LOVER-"))
        self.assertEqual([x[0] for x in self.spy.sent], ["kyc", "sim"], "the SIM change check runs at the same time")
        self.assertTrue(all(ref.startswith("vault:") for x in self.spy.sent for ref in x[1:3] if isinstance(ref, str) and x[0] == "kyc"))
        self.assertFalse(self.o.may_go(p, "payouts", T0), "the sandbox never says match by itself")
        out = self.o.network_answer(r["lover"], "match", None, T0 + 60)
        self.assertEqual((out["state"], out["result"]), ("confirmed", "go"))
        self.assertTrue(self.o.may_go(p, "payouts", T0 + 120))
        again = self.o.network_answer(r["lover"], "no_match", None, T0 + 90)
        self.assertEqual(again["state"], "confirmed", "a repeated answer changes nothing")
        self.assertEqual(self.o.start(p, "cards", True, "NETWORK", now=T0 + 200)["reused"], True)
        self.assertFalse(self.o.may_go(p, "payouts", T0 + 181 * DAY), "a match is kept for a time only")
        self.assertFalse(self.o.may_go(p, "payouts", T0 + 300, sim_changed_at=T0 + 200), "a SIM change since the match asks again")
        self.assertFalse(self.o.may_go(p, "payouts", T0 + 300, number_changed=True))

    def test_partial_no_match_and_a_recent_sim_change(self):
        p = self.person()
        a = self.o.start(p, "payouts", True, "NETWORK", now=T0)
        self.assertEqual(self.o.network_answer(a["lover"], "partial", None, T0)["fixes"], ["check_spelling", "id_document"])
        b = self.o.start(p, "exchange", True, "NETWORK", now=T0 + 1)
        stop = self.o.network_answer(b["lover"], "no_match", None, T0 + 2)
        self.assertEqual((stop["state"], stop["fixes"]), ("failed", ["check_number", "id_document"]))
        c = self.o.start(p, "agent_point", True, "NETWORK", now=T0 + 3)
        w = self.o.network_answer(c["lover"], "match", T0 - H, T0 + 4)
        self.assertEqual((w["state"], w["until"]), ("waiting", T0 - H + WI.OWNER["sim_swap_wait_hours"] * H))
        self.assertFalse(self.o.may_go(p, "agent_point", T0 + 5))
        self.assertFalse(self.o.wait_over(c["lover"], T0 + 5))
        self.assertTrue(self.o.wait_over(c["lover"], T0 + 80 * H))
        self.assertEqual(self.o.state(c["lover"])["state"], "sent", "after the wait the network is asked again")

    def test_without_a_network_the_id_document_check_is_used(self):
        p = self.person()
        r = self.o.start(p, "first_paid_offer", True, "ELSEWHERE", now=T0)
        self.assertEqual((r["state"], r["method"]), ("sent", "id_document"))
        self.assertEqual(self.spy.sent, [], "no network is asked where none is signed")
        self.a.partner_identity_answer(r["lover"], True, "sandbox-identity", T0 + 60)
        self.assertTrue(self.o.may_go(p, "first_paid_offer", T0 + 61))
        b = self.o.start(self.person("shop.owner"), "payouts", True, "NETWORK", business_ref="pii_registered", now=T0)
        self.assertEqual(b["method"], "owner_id_document", "a business without registered-name support uses the owner's ID check")
        c = self.o.start(self.person("shop.two"), "payouts", True, "NETWORK", business_ref="pii_registered2", registered_name_supported=True, now=T0)
        self.assertEqual(c["method"], "registered_name")
        self.assertEqual(self.spy.sent[0][2], "vault:pii_registered2")

    def test_no_event_carries_a_name_or_number_and_the_default_is_off(self):
        p = self.person()
        r = self.o.start(p, "payouts", True, "NETWORK", now=T0)
        self.o.network_answer(r["lover"], "match", None, T0 + 1)
        evs = self.events(p, "PhoneOwnerCheckRequested") + self.events(p, "PhoneOwnerCheckAnswered")
        self.assertEqual(len(evs), 2)
        blob = json.dumps([e["payload"] for e in evs])
        for secret in ("pii_p_grace.k", "pii_legal", "Grace", "vault:"):
            self.assertNotIn(secret, blob)
        from identity.phone_owner import PhoneOwner
        self.assertEqual(PhoneOwner(self.a).start(self.person("fresh.one"), "cards", True, "RW", now=T0 + 2)["method"], "id_document",
                         "the network stays off for real users until a mobile partner is signed")
        self.assertFalse(WI.OWNER["cost"]["charged_to_person"])
