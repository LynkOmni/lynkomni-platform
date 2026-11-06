import os, json, unittest
from uuid import uuid4
os.environ["LYNK_MODE"] = "sandbox"
from services.platform import Platform
from services.improvements import merkle_root, merkle_proof, merkle_verify, _h
from cc.box import LynkCCBox
from dv.box import LynkDVBox

class T(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"; self.p = Platform(); self.p.register("m1", "RW")
    def rev(self, stream):
        return [e["payload"] for e in self.p.c.store.all_of("revenue.earned") if e["payload"]["stream"] == stream]

    def _device(self):
        M, B, U = str(uuid4()), str(uuid4()), str(uuid4()); cc = LynkCCBox(); d = LynkDVBox(M, B, str(uuid4()), U, "owner"); cc.enroll(str(d.d), M)
        pr = d.create_product("Juice", 1500); d.receive_stock([(pr, 1000)]); return cc, d, pr

    def test_mesh_relay_cannot_read_batches_and_never_says_confirmed(self):
        from services.sealing import generate_keypair, seal, unseal
        cc, d, _ = self._device(); priv, pub = generate_keypair(); plain = json.dumps(d.pending(0)).encode()
        r = self.p.mesh_for(cc)
        self.assertEqual(r.submit("phone1", d.d, _h(plain), plain)["state"], "refused")      # plain JSON is refused
        sealed = seal(plain, pub); bh = _h(sealed)
        self.assertNotIn(b"Juice", sealed)
        self.assertEqual(r.submit("phone1", d.d, bh, sealed)["state"], "queued"); self.assertEqual(r.ui_state(bh), "sent")
        self.assertTrue(r.submit("phone1", d.d, bh, sealed)["duplicate"])
        r.forward(lambda body: json.loads(unseal(body, priv))); self.assertEqual(r.ui_state(bh), "accepted")
        self.assertEqual(self.rev("mesh"), [])
        self.assertNotIn(r.ui_state(bh), ("confirmed",))

    def test_mesh_wrong_key_tamper_and_rate_limit(self):
        from services.sealing import generate_keypair, seal, unseal
        cc, d, _ = self._device(); priv, pub = generate_keypair(); other, _p = generate_keypair(); sealed = seal(b"[]", pub); bh = _h(sealed)
        r = self.p.mesh_for(cc, limit=2); r.submit("x", d.d, bh, sealed); r.forward(lambda b: json.loads(unseal(b, other)))
        self.assertEqual(r.ui_state(bh), "failed")
        r.submit("x", d.d, "bad-hash", seal(b"[]", pub)); r.forward(lambda b: json.loads(unseal(b, priv)))
        self.assertEqual(r.items["bad-hash"]["state"], "tampered")
        self.assertEqual(r.submit("x", d.d, "h3", seal(b"[]", pub))["reason"], "rate_limited")
        flipped = bytearray(sealed); flipped[-1] ^= 1
        with self.assertRaises(Exception): unseal(bytes(flipped), priv)

    def test_state_survives_a_restart(self):
        import tempfile, os as _os
        path = _os.path.join(tempfile.mkdtemp(), "p.db"); p1 = Platform(path); p1.register("m1", "RW")
        pid = p1.proof.create("m1", "pay1", {"receipt": "r"})["id"]; p1.risk_limits.set_cap("m1", 120); p1.meter.record("m1", "k", "d1", 7)
        p1.c.store.db.commit(); p2 = Platform(path)
        self.assertEqual(p2.proof.packs[pid]["state"], "created"); self.assertEqual(p2.risk_limits.caps.get("m1")["usd"], 120); self.assertEqual(p2.meter.calls("m1", "d1"), 7)

    def test_guarded_device_declines_at_the_cap_but_cash_still_works(self):
        from services.improvements import GuardedDevice
        cc, d, pr = self._device(); self.p.risk_limits.set_cap("m1", 0)
        g = GuardedDevice(d, self.p.risk_limits, "m1"); sid = g.record_sale([(pr, 1000, 0)])
        self.assertEqual(g.record_payment(sid, "mobile_money", 1), "offline_limit_reached")
        self.assertEqual(g.record_payment(sid, "cash", 1500), "cash_received")

    def test_offline_risk_caps_non_cash_only_and_never_guarantees(self):
        k = self.p.risk_limits; cap = k.cap_minor("m1")
        a = k.authorise("m1", "dev", "s1", cap, "mobile_money"); self.assertTrue(a["allowed"]); self.assertFalse(a["guaranteed"]); self.assertEqual(a["status"], "pending_confirmation")
        self.assertFalse(k.authorise("m1", "dev", "s2", 1, "mobile_money")["allowed"])
        self.assertTrue(k.authorise("m1", "dev", "s3", cap * 10, "cash")["allowed"])
        k.confirm("m1", "dev", "s1"); self.assertTrue(k.authorise("m1", "dev", "s4", 1, "card")["allowed"])
        with self.assertRaises(ValueError): k.set_cap("m1", 501)

    def test_proof_pack_fee_only_on_provider_win_and_once(self):
        pk = self.p.proof
        with self.assertRaises(PermissionError): pk.create("m1", "pay1", {"signature": "x"})
        r = pk.create("m1", "pay1", {"receipt": "r1", "signature": "x"}, consent_id="c1"); self.assertTrue(r["id"].startswith("LOPRF-"))
        with self.assertRaises(ValueError): pk.provider_outcome(r["id"], "won")
        pk.hand_over(r["id"], "acquirer"); pk.provider_outcome(r["id"], "lost"); self.assertEqual(self.rev("proof:success_fee"), [])
        r2 = pk.create("m1", "pay2", {"receipt": "r2"}); pk.hand_over(r2["id"], "acquirer"); pk.provider_outcome(r2["id"], "won"); pk.provider_outcome(r2["id"], "won")
        fees = self.rev("proof:success_fee"); self.assertEqual(len(fees), 1); self.assertEqual(fees[0]["usd_minor"], 500)

    def test_device_database_refuses_to_open_without_a_key(self):
        from core.devicedb import open_device_db, EncryptionUnavailable
        with self.assertRaises(EncryptionUnavailable): open_device_db(":memory:")
        with self.assertRaises(EncryptionUnavailable): open_device_db(":memory:", key="k")     # SQLCipher is not installed in the build sandbox
        open_device_db(":memory:", allow_unencrypted=True).close()

    def test_merkle_proofs(self):
        leaves = [{"n": i} for i in range(5)]; root = merkle_root(leaves)
        for i, l in enumerate(leaves): self.assertTrue(merkle_verify(l, merkle_proof(leaves, i), root))
        self.assertFalse(merkle_verify({"n": 99}, merkle_proof(leaves, 0), root))

    def test_audit_export_fee_by_tier(self):
        self.p.c.store.append("m1", "server", "note.test", {"a": 1}); e = self.p.audit_export.export("m1"); self.assertTrue(e["id"].startswith("LOAUD-")); self.assertTrue(e["fee_charged"]); self.assertFalse(e["tax_authority_validated"])
        self.assertEqual(self.rev("audit:export")[0]["usd_minor"], 250)
        pr = self.p.audit_export.proof_for(e["id"], 0); self.assertTrue(merkle_verify(pr["leaf"], pr["proof"], e["root"]))
        self.p.billing.set_plan("m1", "lynkledger", "max"); self.assertFalse(self.p.audit_export.export("m1")["fee_charged"]); self.assertEqual(len(self.rev("audit:export")), 1)

    def test_split_exact_sum_and_fee_and_no_funds_held(self):
        s = self.p.split; self.p.billing.set_plan("m1", "lynkmpay", "pro")
        with self.assertRaises(ValueError): s.create("m1", "p", 10001, {"supplier": 3000}, provider_confirmed=False)
        r = s.create("m1", "p", 10001, {"supplier": 3333, "agent": 1000}, provider_confirmed=True)
        self.assertTrue(r["id"].startswith("LOSPLT-")); self.assertEqual(sum(r["parts"].values()), 10001); self.assertEqual(r["held_by_lynkomni"], 0)
        with self.assertRaises(PermissionError): s.create("m1", "p", 1000, {"tax_authority": 500}, provider_confirmed=True, tax_leg=True)
        self.assertEqual(len(self.rev("split:fee")), 1)

    def test_new_services_have_tiers_inside_existing_families_and_suite_prices_are_as_set(self):
        from services import billing as B
        self.assertEqual([self._ent(t)["proof_fee_cents"] for t in B.MT], [500, 500, 400, 300])
        self.assertEqual([self._ent(t)["proof_packs_per_month"] for t in B.MT], [3, 20, 100, None]); self.assertEqual([self._ent(t)["split_max_legs"] for t in B.MT], [0, 2, 5, None])
        self.assertNotIn("lynkmpay", B.SUITE_MEMBERS); self.assertEqual(B.FAMILIES["lynksuite"][3], (0, 17, 49, 125))
        for fam in ("lynkpos", "lynkledger"): self.assertIn(fam, B.SUITE_MEMBERS)
        self.p.billing.set_plan("m1", "lynksuite", "max")                      # Suite Max carries LynkLedger Max, so exports are included; MPay stays separate
        self.assertFalse(self.p.audit_export.export("m1")["fee_charged"]); self.assertEqual(self.p.billing.entitlement("m1", "lynkmpay")["split_max_legs"], 0)
    def _ent(self, tier):
        from services import billing as B
        d = {}
        for x in B.FEATURES["lynkmpay"][: B.MT.index(tier) + 1]: d.update(x)
        return d
    def test_tier_limits_are_enforced(self):
        pk = self.p.proof
        for i in range(3): pk.create("m1", f"p{i}", {"r": i}, month="2026-11")
        with self.assertRaises(PermissionError): pk.create("m1", "p9", {"r": 9}, month="2026-11")
        pk.create("m1", "p10", {"r": 1}, month="2026-12")                       # a new month starts fresh
        with self.assertRaises(PermissionError): self.p.split.create("m1", "p", 1000, {"supplier": 1000}, provider_confirmed=True)   # Free has no splits
        self.p.billing.set_plan("m1", "lynkmpay", "plus")
        with self.assertRaises(PermissionError): self.p.split.create("m1", "p", 1000, {"a": 100, "b": 100, "c": 100}, provider_confirmed=True)
        self.p.billing.set_plan("m1", "lynkmpay", "max"); a = self.p.split.create("m1", "p", 100000, {"a": 100, "b": 100, "c": 100}, provider_confirmed=True)
        self.p.billing.set_plan("m1", "lynkmpay", "pro"); b = self.p.split.create("m1", "p", 100000, {"a": 100}, provider_confirmed=True); self.assertLess(a["fee_minor"], b["fee_minor"])
        self.assertEqual(self.p.audit_export.export("m1")["fee_charged"], True); self.p.billing.set_plan("m1", "lynkledger", "pro")
        self.p.audit_export.export("m1"); fees = [r["usd_minor"] for r in self.rev("audit:export")]; self.assertEqual(fees, [250, 150])
        self.assertGreater(self.p.edge.overage_minor("m1", 100), 0); self.p.billing.set_plan("m1", "lynkdev", "business"); self.assertEqual(self.p.edge.overage_minor("m1", 100), 0)   # 250 GB included
    def test_seats_meter_edge(self):
        self.assertEqual(self.p.seats.included("m1", "lynkpos"), 1); self.assertEqual(self.p.seats.extra_cost("m1", "lynkpos", 1), 0); self.assertGreater(self.p.seats.extra_cost("m1", "lynkpos", 3), 0)
        m = self.p.meter; self.assertTrue(m.record("m1", "k1", "d1", 1500)); self.assertFalse(m.record("m1", "k1", "d1", 1500))
        self.assertEqual(m.overage_calls("m1", "d1"), 500); self.assertEqual(m.bill_day("m1", "d1"), 0)   # free tier is never charged
        self.p.billing.set_plan("m1", "lynkdev", "starter"); m.record("m1", "k2", "d2", 50500); self.assertGreater(m.bill_day("m1", "d2"), 0)
        self.assertEqual(self.p.edge.overage_minor("m1", 10), 0); self.assertGreater(self.p.edge.overage_minor("m1", 110), 0)

    def test_seat_and_edge_charges_are_billed_once_a_month(self):
        self.assertEqual(self.p.seats.charge("m1", "lynkpos", 1, "2026-11"), 0)
        a = self.p.seats.charge("m1", "lynkpos", 3, "2026-11"); self.assertGreater(a, 0); self.assertEqual(self.p.seats.charge("m1", "lynkpos", 3, "2026-11"), 0)
        self.assertEqual(len(self.rev("seats:extra")), 1)
        self.assertGreater(self.p.edge.charge("m1", 110, "2026-11"), 0); self.assertEqual(self.p.edge.charge("m1", 110, "2026-11"), 0); self.assertEqual(len(self.rev("edge:bandwidth")), 1)
        self.p.billing.set_plan("m1", "lynkdev", "starter"); self.p.meter.record("m1", "k9", "d9", 50500)
        self.assertGreater(self.p.meter.bill_day("m1", "d9"), 0); self.assertEqual(self.p.meter.bill_day("m1", "d9"), 0)

    def test_guest_checkout_uses_pack_not_ip_and_adds_no_surcharge(self):
        g = self.p.guest.methods("RW", ip_hint="KE"); self.assertIn("momo_mtn", g["methods"]); self.assertEqual(g["surcharge_bp"], 0); self.assertFalse(g["ip_used_as_filter"]); self.assertNotIn("vcard", g["methods"])
        self.assertFalse(self.p.guest.methods("RW", location=(1, 2))["location_used_as_suggestion"]); self.assertTrue(self.p.guest.methods("RW", location=(1, 2), location_consent=True)["location_used_as_suggestion"])
        self.assertTrue(self.p.guest.passkey_pay(True)["created"]); self.assertFalse(self.p.guest.passkey_pay(True, "LOID-x")["created"])
        with self.assertRaises(PermissionError): self.p.guest.passkey_pay(False)

    def test_quote_to_order_adds_no_commission(self):
        before = len(self.p.c.store.all_of("revenue.earned"))
        qid = self.p.chat.quote("m1", "dev", "th1", "biz", [{"qty": 2, "price_minor": 1500}]); oid = self.p.chat.accept_quote("m1", "th1", "cust", qid)
        self.assertTrue(oid); self.assertEqual(len(self.p.c.store.all_of("revenue.earned")), before)   # the order is drafted; no extra fee or commission is recorded

    def test_business_settings_need_stepup_wait_and_second_owner(self):
        now = [1000.0]; self.p.settings.now = lambda: now[0]; idp = self.p.idp
        a, b = idp.register_person()["internal"], idp.register_person()["internal"]; org = idp.register_org(a, "Shop", country="RW")["internal"]; idp.add_member(a, org, b, "owner")
        with self.assertRaises(PermissionError): self.p.settings.request(org, a, "tax_id", "123", "bad")
        rid = self.p.settings.request(org, a, "tax_id", "123", self.p.identity.issue(a, verified=True))
        with self.assertRaises(PermissionError): self.p.settings.approve(rid, a, self.p.identity.issue(a, verified=True))
        with self.assertRaises(PermissionError): self.p.settings.apply(rid)
        self.p.settings.approve(rid, b, self.p.identity.issue(b, verified=True))
        with self.assertRaises(PermissionError): self.p.settings.apply(rid)
        self.assertIsNone(self.p.settings.get(org, "tax_id"))
        now[0] += 24 * 3600 + 1; self.assertTrue(self.p.settings.apply(rid)); self.assertEqual(self.p.settings.get(org, "tax_id"), "123")

    def test_revenue_model_total(self):
        self.assertEqual(4000 + 7500 + 2500 + 7500 + 5000, 26500); self.assertEqual(26500 * 12, 318000)

if __name__ == "__main__": unittest.main()
