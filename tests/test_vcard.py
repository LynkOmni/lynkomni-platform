import json, os, re, unittest
from core import ids
from services import vcard as V
from services.platform import Platform

def luhn_pan(s):
    d = [int(c) for c in s]; t = 0
    for i, x in enumerate(reversed(d)):
        if i % 2 == 1: x = x * 2 - 9 if x * 2 > 9 else x * 2
        t += x
    return t % 10 == 0

class T(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"; self.p = Platform(); self.v = self.p.vcard; self.p.register("m1", "RW"); self.v.attest_kyb("m1", "IssuerX")
        self.p.billing.set_plan("m1", "lynkvcard", "pro"); self.t = 1_000_000.0; self.k = 0
    def tearDown(self): os.environ.pop("LYNK_MODE", None)
    def key(self): self.k += 1; return f"k{self.k}"
    def tok(self): return self.p.identity.issue("m1", verified=True)
    def card(self, **kw):
        self.t += 700; kw.setdefault("type", "supplier"); return self.v.request_card("m1", self.key(), "owner", now=self.t, **kw)["card"]
    def fund(self, card, amt=500000): return self.v.request_funding("m1", self.key(), card, amt, funding_source="momo_mtn")

    def test_registry_is_consistent(self):
        R = V.REG
        for c in R["commands"]:
            self.assertIn(c["permission"], R["permissions"]); self.assertEqual(c["class"], "C")
            if c["name"].startswith("Request"): self.assertTrue(c["idempotent"]); self.assertIn("idempotency_key", c["fields"])
        self.assertEqual([c["name"] for c in R["commands"] if c["offline"] != "refused_offline"], ["RequestFreeze"])   # only a freeze intent may queue offline
        self.assertTrue(all(e["origin"] == "server" for e in R["events"]))
        for t in R["id_types"].values(): self.assertIn(t, ids.TYPES)
        for a, nxt in R["card_transitions"].items():
            self.assertIn(a, R["card_states"]); [self.assertIn(b, R["card_states"]) for b in nxt]
        self.assertEqual(len(R["permissions"]), 13)

    def test_pack_alone_never_enables_cards_and_the_issuer_must_verify_the_business(self):
        os.environ.pop("LYNK_MODE"); self.p.c.profile  # outside the sandbox the pack's vcard.enabled is false
        with self.assertRaises(Exception): self.v.request_card("m1", "x", "owner")
        os.environ["LYNK_MODE"] = "sandbox"; self.p.register("m2", "RW"); self.p.billing.set_plan("m2", "lynkvcard", "plus")
        with self.assertRaises(PermissionError): self.v.request_card("m2", "y", "owner")            # no issuer attestation yet
        self.assertEqual(ids.parse(self.card())[0], "VC")

    def test_plan_limits(self):
        self.p.register("f", "RW"); self.v.attest_kyb("f", "IssuerX"); self.p.billing.set_plan("f", "lynkvcard", "free")
        with self.assertRaises(PermissionError): self.v.request_card("f", "a1", "owner", type="team")                          # Free is single-use supplier cards
        self.v.request_card("f", "a2", "owner")
        with self.assertRaises(PermissionError): self.v.request_card("f", "a3", "owner")                                      # one active card at a time
        with self.assertRaises(PermissionError): self.v.request_card("f", "a4", "cashier")                                    # cashiers cannot create cards
        self.p.register("p1", "RW"); self.v.attest_kyb("p1", "IssuerX"); self.p.billing.set_plan("p1", "lynkvcard", "plus")
        with self.assertRaises(PermissionError): self.v.set_lock("p1", "l1", self.v.request_card("p1", "b1", "owner")["card"], "owner", shift=("08:00", "17:00"))   # shift locks are Pro

    def test_idempotency_never_debits_twice(self):
        c = self.card(); k = "fund-1"
        a = self.v.request_funding("m1", k, c, 100000, funding_source="momo_mtn"); b = self.v.request_funding("m1", k, c, 100000, funding_source="momo_mtn")
        self.assertTrue(b["replayed"]); self.assertEqual(self.v.issuer.debits, 1); self.assertEqual(a["txn"], b["txn"])
        with self.assertRaises(ValueError): self.v.request_funding("m1", k, c, 999, funding_source="momo_mtn")                 # same key, different request
        with self.assertRaises(ValueError): self.v.request_funding("m1", "k-x", c, 1000, funding_source="paypal")             # not a payment method of the country pack
        with self.assertRaises(ValueError): self.v.request_funding("m1", "", c, 1000)

    def test_offline_freeze_is_only_an_intent(self):
        c = self.card(); r = self.v.queue_freeze("m1", c, "lost phone", "n1", now=self.t)
        self.assertEqual((r["state"], r["card_state"]), ("freeze_requested_waiting_for_connection", "active"))                  # never shown as frozen
        with self.assertRaises(PermissionError): self.v.queue_freeze("m1", c, "again", "n1", now=self.t)                       # replayed nonce
        self.assertEqual(self.v.process_intents(self.t + 60), {"done": 1, "expired": 0}); self.assertEqual(self.v._row(c)["state"], "frozen")
        d = self.card(); self.v.queue_freeze("m1", d, "x", "n2", now=self.t)
        self.assertEqual(self.v.process_intents(self.t + 25 * 3600), {"done": 0, "expired": 1}); self.assertEqual(self.v._row(d)["state"], "active")   # expired intents are reported, not silent
        self.assertTrue([e for e in self.p.c.store.of("m1", "VirtualCardFreezeIntentExpired")])

    def test_wallet_tokens_revoked_on_freeze_close_and_rotate(self):
        c = self.card(); self.v.provision_wallet("m1", self.key(), c, "apple_pay"); self.v.request_freeze("m1", self.key(), c, "test")
        self.assertEqual(self.p.c.store.of("m1", "WalletTokenRevoked")[0]["payload"]["reason"], "freeze")
        self.v.request_unfreeze("m1", self.key(), c); self.v.provision_wallet("m1", self.key(), c, "google_pay"); old = self.v._row(c)["token"]
        self.v.request_rotate("m1", self.key(), c, "90d"); self.assertNotEqual(old, self.v._row(c)["token"]); self.assertEqual(self.p.c.store.of("m1", "WalletTokenRevoked")[-1]["payload"]["reason"], "rotate")
        self.assertEqual(self.v.request_close("m1", self.key(), c)["state"], "closed")

    def test_authorization_locks_fx_buffer_settlement_receipt_and_revenue(self):
        c = self.card(); self.fund(c, 500000)
        self.assertFalse(self.v.authorize(c, "Casino", "7995", 1000, "RWF", now=self.t)["approved"])                           # blocked category in the pack
        a = self.v.authorize(c, "Alibaba", "5311", 100000, "USD", now=self.t); self.assertEqual(a["buffer_hold"], 2000)         # 2% buffer on foreign spend
        self.assertEqual(self.v._row(c)["balance"], 500000 - 100000 - 2000)
        self.assertEqual(self.p.c.store.of("m1", "VirtualCardChallengeIssued")[0]["payload"]["channel"], "app_approval")      # never a chat thread
        with self.assertRaises(PermissionError): self.v.respond_to_challenge("m1", c, a["txn"], "approve", None)
        self.assertEqual(self.v.respond_to_challenge("m1", c, a["txn"], "approve", self.tok())["decision"], "approve")
        s = self.v.settle(a["txn"], 99000, 1.0, supplier_fiscal_ref="EBM-123")
        self.assertEqual(self.v._row(c)["balance"], 500000 - 99000)                                                            # buffer released
        rcp = self.p.c.store.of("m1", "VirtualCardReceiptCreated")[0]["payload"]; self.assertFalse(rcp["fiscal"]); self.assertEqual(ids.parse(rcp["receipt"])[0], "RCP")
        self.assertEqual(self.p.accountant.summary("m1")["expenses_minor"], 99000)                                             # the accountant picks it up
        streams = {e["payload"]["stream"] for e in self.p.c.store.of("_company", "revenue.earned")}; self.assertTrue({"vcard_interchange", "vcard_fx"} <= streams)
        self.assertEqual(s["cashback_points"], 99000 * 5 // 10000)                                                             # Pro cashback as LynkPoints
        self.v.set_lock("m1", self.key(), c, "owner", supplier="till-9"); self.assertFalse(self.v.authorize(c, "Other", "5311", 1000, "RWF", supplier="till-1", now=self.t)["approved"])

    def test_card_numbers_are_never_stored_and_display_is_issuer_hosted(self):
        c = self.card(); self.fund(c)
        with self.assertRaises(PermissionError): self.v.display_session("m1", c, "owner", None)
        s = self.v.display_session("m1", c, "owner", self.tok()); self.assertTrue(s["url"].startswith("https://issuer.example/")); self.assertEqual(s["expires_in"], 60)
        with self.assertRaises(PermissionError): self.v.display_session("m1", c, "cashier", self.tok())
        dump = " ".join(str(r) for t in ("vcards", "vtxns", "vcommands", "events") for r in self.v.db.execute(f"select * from {t}").fetchall())
        self.assertFalse([m for m in re.findall(r"\b\d{13,19}\b", dump) if luhn_pan(m)])

    def test_risk_box_velocity_flags_blocks_unfreeze_and_chargeback_halts(self):
        for i in range(5): self.t += 5; self.v.request_card("m1", self.key(), "owner", now=self.t) if i < 1 else None
        self.p.billing.set_plan("m1", "lynkvcard", "max")
        made = 0
        for i in range(6):
            try: self.v.request_card("m1", self.key(), "owner", now=self.t + i); made += 1
            except PermissionError as e: err = str(e)
        self.assertIn("flagged", err); flag = self.p.c.store.of("m1", "LynkVCRBoxFlagged")[0]["payload"]; self.assertEqual(ids.parse(flag["case"])[0], "CASE")
        c = self.card(); self.v.request_freeze("m1", self.key(), c, "x"); case = self.v.risk.flag("m1", c, "category"); 
        with self.assertRaises(PermissionError): self.v.request_unfreeze("m1", self.key(), c)                                    # open case blocks unfreeze
        self.v.risk.clear("m1", case); self.assertEqual(self.v.request_unfreeze("m1", self.key(), c)["state"], "active")

    def test_disputes_and_chargeback_tiers(self):
        c = self.card(); self.fund(c); a = self.v.authorize(c, "Shop", "5311", 1000, "RWF", now=self.t); self.v.settle(a["txn"], 1000)
        d = self.v.request_dispute("m1", self.key(), c, a["txn"], "not received"); self.assertEqual(ids.parse(d["case"])[0], "CASE")
        self.assertGreaterEqual(self.v.risk.chargeback_ratio(), 0.9)
        self.assertEqual({r[0] for r in self.v.db.execute("select rule from vflags")} & {"chargeback_halt"}, {"chargeback_halt"})
        with self.assertRaises(PermissionError): self.card()                                                                      # issuance paused until the case clears
        self.assertIsNotNone(self.v.resolve_dispute("m1", d["case"], "refund")["refund_txn"])

    def test_physical_companion_is_max_only_with_its_own_id(self):
        c = self.card()
        with self.assertRaises(PermissionError): self.v.request_physical("m1", self.key(), c, "addr-ref")
        self.p.billing.set_plan("m1", "lynkvcard", "max"); r = self.v.request_physical("m1", self.key(), c, "addr-ref")
        self.assertEqual(ids.parse(r["physical"])[0], "PC"); self.assertNotIn(c[:6], r["physical"][:6] + "x") ; self.assertEqual(self.v._row(c)["physical"], r["physical"])
        with self.assertRaises(PermissionError): self.v.activate_physical("m1", self.key(), r["physical"], None)
        self.assertEqual(self.v.activate_physical("m1", self.key(), r["physical"], self.tok())["state"], "activated")

    def test_supplier_scores_need_three_merchants(self):
        for i, m in enumerate(("a", "b", "c")):
            self.p.register(m, "RW"); self.v.attest_kyb(m, "IssuerX"); self.p.billing.set_plan(m, "lynkvcard", "pro")
            card = self.v.request_card(m, f"s{i}", "owner", now=self.t + i * 1000)["card"]; self.v.request_funding(m, f"f{i}", card, 50000, funding_source="momo_mtn")
            self.v.authorize(card, "Acme", "5311", 1000, "RWF", supplier="acme", now=self.t)
            if i < 2: self.assertEqual(self.v.update_supplier_scores(), {})                                                       # fewer than 3 merchants: no score
        self.assertEqual(ids.parse(self.v.update_supplier_scores()["acme"])[0], "SC")

    def test_webhooks_are_signed_and_retries_stay_inside_24_hours(self):
        body = b'{"event":"VirtualCardSettled"}'; sig = V.developer_webhook_headers("s3cret", body)["X-Lynk-Signature"]
        self.assertTrue(V.verify_issuer_webhook("s3cret", body, sig)); self.assertFalse(V.verify_issuer_webhook("s3cret", body + b" ", sig)); self.assertFalse(V.verify_issuer_webhook("s3cret", body, None))
        d = V.retry_delays(); self.assertEqual(d[:4], [2, 4, 8, 16]); self.assertLessEqual(sum(d), 86400)

    def test_extra_cards_beyond_the_allowance_carry_a_small_fee(self):
        self.p.register("e", "RW"); self.v.attest_kyb("e", "IssuerX"); self.p.billing.set_plan("e", "lynkvcard", "free"); fee = None
        for i in range(7):
            r = self.v.request_card("e", f"e{i}", "owner", now=self.t + i * 700); fee = r["extra_card_fee_minor"]; self.v.request_close("e", f"c{i}", r["card"])
        self.assertGreater(fee, 0); self.assertIn("vcard_issuance", {e["payload"]["stream"] for e in self.p.c.store.of("_company", "revenue.earned")})

if __name__ == "__main__":
    unittest.main()
