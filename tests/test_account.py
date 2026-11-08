"""LynkOmni Account and sign-in (build section 2): sign-up, passkeys, sessions and alerts, the Security Center, data-sharing
consents, the takeover safeguards, download-my-records, closing, Start a business, standing payments, the accountant's client
switcher, and the LynkFlow runner with the seven section-2 automations."""
import json, os, time, unittest
from identity.account import Account, CONSENT_SCOPES, EVENTS, PAGES, PAYOUT_WAIT_S, DAY
from identity.automations import RECOVERY_STEPS
from services.flow import REGISTER, Flow, MAX_DEPTH
from services.platform import Platform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T0 = 1_800_000_000.0
BUILT_SECTIONS = 3     # raise this as sections are built; every event trigger up to here must exist


class SignUpAndSecurity(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.a = self.p.account
    def tearDown(self): os.environ.pop("LYNK_MODE", None)
    def signed_up(self, username="grace.k", **kw):
        s = self.a.begin_sign_up(username, "en", T0); p = s["person"]
        code = self.a.send_contact_code(p, T0); self.a.confirm_contact(p, code, T0)
        done = self.a.finish_sign_up(p, "pk-1", "Grace's phone", "pii_1", "pii_2", backup_contact="bk-1", now=T0, **kw)
        return p, s, done

    def test_sign_up_takes_a_username_checks_a_contact_and_shows_the_recovery_code_once(self):
        with self.assertRaises(ValueError): self.a.begin_sign_up("admin", "en", T0)                    # reserved word
        with self.assertRaises(ValueError): self.a.begin_sign_up("Grace..K", "en", T0)                 # two dots
        p, s, done = self.signed_up()
        self.assertTrue(s["lynkid"].startswith("LOID-")); self.assertEqual(s["username"], "grace.k")
        self.assertTrue(done["show_once"] and done["recovery_code"] and done["locrd"].startswith("LOCRD-"))
        self.assertEqual(self.a.username_status("grace.k"), "taken")
        with self.assertRaises(ValueError): self.a.begin_sign_up("grace.k", "en", T0)
        types = [e["type"] for e in self.p.c.store.of(p, *EVENTS)]
        self.assertEqual(types, ["AccountCreated", "PasskeyEnrolled"])
        for e in self.p.c.store.of(p, *EVENTS):                                                           # payloads carry references only
            self.assertFalse(any(k in e["payload"] for k in ("phone", "email", "code", "recovery_code")))
        with self.assertRaises(PermissionError):                                                          # a contact must be verified first
            q = self.a.begin_sign_up("other.one", "en", T0)["person"]; self.a.finish_sign_up(q, "pk", "x", "pii_3", "pii_4", now=T0)

    def test_old_usernames_redirect_and_are_never_reissued(self):
        p, s, _ = self.signed_up()
        self.a.change_username(p, "grace.kamau", T0)
        self.assertEqual(self.a.usernames.resolve("grace.k"), self.a.usernames.resolve("grace.kamau"))
        with self.assertRaises(ValueError): self.a.begin_sign_up("grace.k", "en", T0)                   # reserved for its owner for ever

    def test_sign_in_alerts_on_a_new_device_or_place_and_sessions_are_bound_to_one_site(self):
        p, s, _ = self.signed_up()
        tok = self.a.sign_in(p, "account", "Grace's phone", "Kigali", T0)
        self.assertEqual(self.a.auth.validate_session(tok, "account", T0), p); self.assertIsNone(self.a.auth.validate_session(tok, "merchant", T0))
        self.assertEqual([e["type"] for e in self.p.c.store.of(p, "SecurityAlertSent")], [])                # the first sign-in is not an alert
        self.a.sign_in(p, "account", "Unknown laptop", "Kigali", T0 + 60)
        alerts = self.p.c.store.of(p, "SecurityAlertSent")
        self.assertEqual([a["payload"]["kind"] for a in alerts], ["new_sign_in"]); self.assertEqual(alerts[0]["payload"]["by_automation"], "sign-in-alert")
        runs = self.p.flow.history(p); self.assertEqual(runs[0]["automation"], "sign-in-alert"); self.assertIn("no link", runs[0]["why"])
        self.assertEqual(len(self.a.sessions(p)), 2)
        self.assertTrue(self.a.revoke_session(p, tok[-4:], now=T0 + 120)); self.assertIsNone(self.a.auth.validate_session(tok, "account", T0 + 121))
        self.a.sign_out_everywhere(p, T0 + 130); self.assertEqual(self.a.sessions(p), [])

    def test_security_center_lists_what_the_blueprint_asks_and_nothing_private_of_others(self):
        p, s, done = self.signed_up()
        self.a.sign_in(p, "account", "Grace's phone", "Kigali", T0)
        sc = self.a.security_center(p, T0)
        self.assertEqual(set(sc), {"lynkid", "passkeys", "sessions", "events", "recovery", "connected_apps", "memberships"})
        self.assertEqual(len(sc["passkeys"]), 1); self.assertTrue(sc["recovery"]["code_set"] and sc["recovery"]["backup_contact_set"]); self.assertFalse(sc["recovery"]["second_device"])
        self.assertEqual(sc["events"][0]["type"], "SessionStarted"); self.assertNotIn("lynkid", sc["events"][0]["payload"])
        # removing the only passkey is refused; a second one can be removed with a fresh step-up
        tok = self.a.sign_in(p, "account", "Grace's phone", "Kigali", T0)
        code = self.a.auth.begin_stepup(p, T0); su = self.a.auth.complete_stepup(p, tok, code, T0)
        with self.assertRaises(PermissionError): self.a.revoke_passkey(p, done["locrd"], su, T0)
        two = self.a.enroll_passkey(p, "pk-2", "Grace's laptop", T0)
        with self.assertRaises(PermissionError): self.a.revoke_passkey(p, two, "stale", T0)
        self.a.revoke_passkey(p, two, su, T0); self.assertEqual(len(self.a.passkeys(p)), 1)

    def test_consents_name_a_scope_a_purpose_and_an_end_and_the_automation_warns_and_ends_them(self):
        p, s, _ = self.signed_up()
        with self.assertRaises(ValueError): self.a.grant_consent(p, "everything", "acc-1", "books", 30, T0)
        with self.assertRaises(ValueError): self.a.grant_consent(p, "lender", "bank-1", "", 30, T0)
        c = self.a.grant_consent(p, "lender", "bank-1", "one-off credit decision", 400, T0)                 # capped at the scope's maximum
        self.assertTrue(c.startswith("LOCNS-")); self.assertEqual(self.a.consents(p, T0)[0]["expires"], T0 + 30 * DAY)
        self.assertTrue(self.a.consent_allows(p, "lender", "bank-1", T0)); self.assertFalse(self.a.consent_allows(p, "health-pack", "bank-1", T0))
        ran = self.p.flow.tick("daily", [p], T0 + 24 * DAY)                                                 # 6 days left: warned once
        self.assertEqual([r["automation"] for r in ran], ["consent-expiry"]); self.assertEqual(len(self.p.c.store.of(p, "ConsentExpiring")), 1)
        self.assertEqual(self.p.flow.tick("daily", [p], T0 + 24 * DAY + 3600), [])                        # once a day
        self.assertEqual(self.p.flow.tick("daily", [p], T0 + 25 * DAY), [])                               # not warned twice
        self.p.flow.tick("daily", [p], T0 + 31 * DAY)
        self.assertEqual(len(self.p.c.store.of(p, "ConsentExpired")), 1); self.assertFalse(self.a.consent_allows(p, "lender", "bank-1", T0 + 31 * DAY))
        self.assertEqual(self.p.c.store.of(p, "ConsentWithdrawn")[0]["payload"]["by"], "expiry")
        self.assertEqual(set(CONSENT_SCOPES), {"health-pack", "accountant", "lender", "developer-app", "support", "supplier-sell-through"})

    def test_takeover_safeguards_payout_change_waits_and_exports_need_a_step_up(self):
        p, s, _ = self.signed_up(); org = self.p.idp.register_org(p, "Mama Shop", country="XX")["internal"]
        r = self.a.request_payout_change(p, org, now=T0)
        self.assertEqual(r["status"], "waiting"); self.assertEqual(r["ready_at"], T0 + PAYOUT_WAIT_S)
        self.assertEqual([a["payload"]["kind"] for a in self.p.c.store.of(p, "SecurityAlertSent")], ["payout_change"])
        with self.assertRaises(PermissionError): self.a.apply_payout_change(p, r["id"], T0 + 3600)
        self.a.apply_payout_change(p, r["id"], T0 + PAYOUT_WAIT_S + 1)
        self.assertEqual(self.p.c.store.of(p, "PayoutChangeApplied")[0]["payload"]["approved_by"], "waiting_period")
        self.assertEqual(self.a.request_payout_change(p, org, second_device_ok=True, now=T0)["status"], "applied")
        r2 = self.a.request_payout_change(p, org, now=T0); self.a.cancel_payout_change(p, r2["id"], "other_device", T0)
        with self.assertRaises(PermissionError): self.a.apply_payout_change(p, r2["id"], T0 + 2 * PAYOUT_WAIT_S)
        other = self.a.begin_sign_up("not.owner", "en", T0)["person"]
        with self.assertRaises(PermissionError): self.a.request_payout_change(other, org, now=T0)
        self.assertFalse(self.a.can_export(p, "no-stepup", now=T0))
        tok = self.a.sign_in(p, "account", "Grace's phone", "Kigali", T0); code = self.a.auth.begin_stepup(p, T0); su = self.a.auth.complete_stepup(p, tok, code, T0)
        self.assertTrue(self.a.can_export(p, su, now=T0))
        self.a.auth.enroll_device(p, f"personal:{p}", "new-phone", "owner", T0, restricted_until=T0 + DAY)   # a device fresh from recovery
        self.assertFalse(self.a.can_export(p, su, "new-phone", T0))
        tok2 = self.a.sign_in(p, "account", "Grace's phone", "Kigali", T0 + DAY + 1)
        code = self.a.auth.begin_stepup(p, T0 + DAY + 1); su2 = self.a.auth.complete_stepup(p, tok2, code, T0 + DAY + 1)
        self.assertTrue(self.a.can_export(p, su2, "new-phone", T0 + DAY + 1))

    def test_download_my_records_has_a_due_date_and_a_reminder_and_closing_keeps_the_lynkid(self):
        p, s, _ = self.signed_up()
        r = self.a.open_data_request(p, T0)
        self.assertEqual(r["due_at"], T0 + 30 * DAY)
        self.assertEqual(self.p.flow.tick("daily", [p], T0 + 10 * DAY), [])
        ran = self.p.flow.tick("daily", [p], T0 + 28 * DAY); self.assertEqual(ran[0]["automation"], "data-request-timer")
        self.a.mark_data_ready(r["request_id"], T0 + 29 * DAY); self.assertEqual(self.p.c.store.of(p, "DataRequestReady")[0]["payload"]["expires_at"], T0 + 36 * DAY)
        tok = self.a.sign_in(p, "account", "Grace's phone", "Kigali", T0); code = self.a.auth.begin_stepup(p, T0); su = self.a.auth.complete_stepup(p, tok, code, T0)
        with self.assertRaises(PermissionError): self.a.request_close(p, "stale", T0)
        closes = self.a.request_close(p, su, T0); self.assertEqual(closes, T0 + 30 * DAY)
        self.assertFalse(self.a.close_if_due(p, T0 + DAY)); self.assertTrue(self.a.close_if_due(p, T0 + 31 * DAY))
        self.assertEqual(self.p.ids.lookup(s["lynkid"])["status"], "assigned")                          # retired in effect: never reused
        self.assertEqual(self.a.username_status("grace.k"), "taken"); self.assertEqual(self.a.sessions(p), [])
        self.assertEqual(self.p.c.store.of(p, "AccountClosed")[0]["payload"], {"lynkid": s["lynkid"]})


class BusinessesAndMoney(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.a = self.p.account
        s = self.a.begin_sign_up("owner.one", "en", T0); self.owner = s["person"]; self.lid = s["lynkid"]
        c = self.a.send_contact_code(self.owner, T0); self.a.confirm_contact(self.owner, c, T0); self.a.finish_sign_up(self.owner, "pk", "phone", "pii_1", "pii_2", now=T0)
        self.org = self.p.idp.register_org(self.owner, "Mama Shop", country="XX")["internal"]
    def tearDown(self): os.environ.pop("LYNK_MODE", None)

    def test_memberships_leaving_and_the_accountant_client_switcher(self):
        acc = self.a.begin_sign_up("numbers.lady", "en", T0); accountant = acc["person"]
        self.p.idp.add_member(self.owner, self.org, accountant, "accountant")
        self.assertTrue(self.p.idp.can(accountant, self.org, "ledger.view")); self.assertFalse(self.p.idp.can(accountant, self.org, "sale.record"))
        self.assertEqual(self.a.clients(accountant, T0)[0]["consent"], "missing")                         # a membership never proves consent
        self.a.grant_consent(self.owner, "accountant", acc["lynkid"], "monthly books", 365, T0)
        self.assertEqual(self.a.clients(accountant, T0)[0]["consent"], "active")
        self.assertEqual(self.a.memberships(accountant)[0]["lynkoid"], self.p.ids.public_for("OID", self.org))
        with self.assertRaises(PermissionError): self.a.leave(self.owner, self.org, T0)                 # the last owner cannot leave
        self.a.leave(accountant, self.org, T0); self.assertEqual(self.a.clients(accountant, T0), [])
        self.assertEqual(self.p.c.store.of(accountant, "MembershipLeft")[0]["payload"]["lynkoid"], self.p.ids.public_for("OID", self.org))

    def test_subscriptions_read_billing_and_the_renewal_reminder_tells_seven_days_before(self):
        self.p.c.profile(self.org)
        self.assertEqual(self.a.subscriptions(self.owner)[0]["plans"], {})
        self.p.billing.set_plan(self.org, "lynkpos", "plus")
        subs = self.a.subscriptions(self.owner)[0]
        self.assertEqual(subs["plans"]["lynkpos"]["tier"], "plus"); self.assertGreater(subs["bill"]["total_minor"], 0)
        now = time.time()
        self.assertEqual(self.p.flow.tick("daily", [self.owner], now + 2 * DAY), [])                        # 28 days left
        ran = self.p.flow.tick("daily", [self.owner], now + 24 * DAY)
        self.assertEqual(ran[0]["automation"], "renewal-reminder"); self.assertEqual(self.p.c.store.of(self.owner, "RenewalReminderSent")[0]["payload"]["family"], "lynkpos")

    def test_start_a_business_is_coming_soon_without_a_gateway_and_never_claims_approval_first(self):
        r = self.a.start_business(self.owner, "XX", T0)
        self.assertEqual(r["state"], "coming_soon"); self.assertEqual(r["message"], "Coming to your country soon."); self.assertTrue(r["notify_me"])
        os.environ["LYNK_MODE"] = "sandbox"
        r = self.a.start_business(self.owner, "XX", T0)
        self.assertEqual(r["state"], "available"); self.assertTrue(r["lodoc"].startswith("LODOC-")); self.assertEqual(r["steps"], ["profile", "registration", "tax_number", "bank_account"])
        with self.assertRaises(ValueError): self.a.submit_application(r["application_id"], T0)
        for st in ("profile", "registration", "tax_number", "bank_account"): self.a.complete_step(r["application_id"], st)
        self.a.submit_application(r["application_id"], T0)
        types = [e["type"] for e in self.p.c.store.of(self.owner, "RegistrationStarted", "RegistrationSubmitted", "BankAccountReferred", "GuideOffered")]
        self.assertEqual(types, ["RegistrationStarted", "RegistrationSubmitted", "GuideOffered", "BankAccountReferred"])   # the tracker answers the submission at once
        self.assertEqual(self.a.applications(self.owner)[0]["status"], "submitted")                       # not approved until the gateway says so
        self.assertEqual(self.a.poll_application(r["application_id"], T0), "approved")
        app = self.a.applications(self.owner)[0]; self.assertTrue(app["lynkoid"].startswith("LOOID-"))
        self.assertEqual(self.p.c.store.of(self.owner, "RegistrationApproved")[0]["payload"]["lynkoid"], app["lynkoid"])

    def test_standing_payments_need_the_licensed_provider_a_cap_and_can_be_revoked(self):
        with self.assertRaises(PermissionError): self.a.approve_standing(self.owner, "shop.one", 5000, "USD", "XX", T0)
        os.environ["LYNK_MODE"] = "sandbox"
        with self.assertRaises(PermissionError): self.a.approve_standing(self.owner, "shop.one", 5000, "USD", "XX", T0)   # sandbox mode does not sign a provider
        import providers
        country = next(c for c in ("RW", "KE", "UG", "GH") if providers.needs("paylinks", c))
        items = providers.needs("paylinks", country); olds = [i["status"] for i in items]
        for i in items: i["status"] = "contract_signed"; i["real_adapter"] = i["interface"]
        item = items[0]
        try:
            with self.assertRaises(ValueError): self.a.approve_standing(self.owner, "shop.one", 0, "USD", country, T0)
            sub = self.a.approve_standing(self.owner, "shop.one", 5000, "USD", country, T0)
            self.assertTrue(sub.startswith("LOSUB-")); self.assertTrue(self.a.standing_charge_allowed(sub, 4999)); self.assertFalse(self.a.standing_charge_allowed(sub, 5001))
            ev = self.p.c.store.of(self.owner, "StandingPaymentApproved")[0]["payload"]; self.assertEqual(ev["provider"], item["id"]); self.assertEqual(ev["cap_minor"], 5000)
            self.a.revoke_standing(self.owner, sub, "self", T0); self.assertFalse(self.a.standing_charge_allowed(sub, 10)); self.assertFalse(self.a.standing_payments(self.owner)[0]["active"])
        finally:
            for i, o in zip(items, olds): i["status"] = o; i.pop("real_adapter", None)

    def test_quiet_business_watch_drafts_a_check_in_and_payslips_are_read_only(self):
        self.p.c.store.append(self.org, "d1", "SaleRecorded", {"total": 1}, ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 20 * DAY)))
        ran = self.p.flow.tick("weekly", [self.org], time.time())
        self.assertEqual(ran[0]["automation"], "churn-watch"); self.assertEqual(ran[0]["level"], "draft")
        self.assertEqual(self.p.c.store.of(self.org, "CheckInDrafted")[0]["payload"]["days_quiet"], 20)
        self.p.c.store.append(self.owner, "server", "payslip.issued", {"lodoc": "LODOC-0000-0000-0001", "period": "2026-10", "lynkoid": "LOOID-1"})
        self.assertEqual(self.a.payslips(self.owner)[0]["period"], "2026-10")
        self.assertEqual(PAGES[:3], ("overview", "profile", "security")); self.assertIn("start", PAGES)


class FlowRunner(unittest.TestCase):
    def setUp(self): self.p = Platform(); self.f = self.p.flow
    def test_only_registered_automations_run_once_each_with_a_why_and_an_off_switch(self):
        with self.assertRaises(ValueError): self.f.handle("made-up", lambda *a: {})
        self.f.handle("sign-in-alert", lambda f, s, pl, now: {"why": "test"})
        ev = {"id": "e1", "type": "SessionStarted", "payload": {"lynkid": "x", "new_device": True}}
        self.assertEqual(len(self.f.on_event("p1", ev)), 1); self.assertEqual(self.f.on_event("p1", ev), [])          # idempotent
        self.f.set_off("p1", "sign-in-alert"); self.assertEqual(self.f.on_event("p1", {**ev, "id": "e2"}), [])          # off switch
        self.f.set_off("p1", "sign-in-alert", False); self.assertEqual(len(self.f.on_event("p1", {**ev, "id": "e3"})), 1)
        h = self.f.history("p1"); self.assertEqual(h[0]["why"], "test"); self.assertEqual(h[0]["level"], "inform")
        self.assertEqual([e["type"] for e in self.p.c.store.of("p1", "AutomationRan")], ["AutomationRan"] * 2)
    def test_loops_are_guarded(self):
        self.f.handle("sign-in-alert", lambda f, s, pl, now: {"n": f.emit(s, "SessionStarted", {"lynkid": "x", "new_device": True}, "sign-in-alert", now)} and {"why": "loop"})
        ran = self.f.on_event("p2", {"id": "e1", "type": "SessionStarted", "payload": {"lynkid": "x", "new_device": True}})
        self.assertEqual(len(ran), 1); self.assertLessEqual(len(self.p.c.store.of("p2", "AutomationRan")), MAX_DEPTH)
    def test_every_event_trigger_in_the_register_is_a_known_event(self):
        with open(os.path.join(ROOT, "contract", "event-payloads.v2.json"), encoding="utf-8") as f: core = set(json.load(f)["events"])
        from merchant.cloud import SIGNALS
        core |= set(SIGNALS)                              # Business app signals (merchant/events.v1.json)
        for a in REGISTER.values():                       # events of later sections are registered when those sections are built
            if a["trigger"].startswith("event:") and a["build_section"] <= BUILT_SECTIONS:
                name = a["trigger"][6:]
                self.assertTrue(name in core or name in EVENTS, f"{a['id']} triggers on unknown event {name}")
    def test_shared_vectors_are_current(self):
        import subprocess, sys
        self.assertEqual(subprocess.run([sys.executable, os.path.join(ROOT, "tools", "account_vectors.py"), "--check"], capture_output=True, text=True).returncode, 0, "run python3 tools/account_vectors.py")
    def test_section_2_automations_match_the_register_levels(self):
        for aid, level in (("sign-in-alert", "inform"), ("recovery-guide", "inform"), ("consent-expiry", "inform"), ("data-request-timer", "inform"), ("start-business-tracker", "inform"), ("churn-watch", "draft"), ("renewal-reminder", "inform")):
            self.assertEqual(REGISTER[aid]["level"], level); self.assertEqual(REGISTER[aid]["build_section"], 2); self.assertIn(aid, self.f.handlers)
        self.assertEqual(set(RECOVERY_STEPS), {"device", "code", "assisted"})


if __name__ == "__main__":
    unittest.main()
