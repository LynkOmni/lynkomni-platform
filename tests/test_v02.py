import json, os, unittest
from unittest.mock import patch
from core.locale import ModeManager, choose_language, format_money, in_quiet_hours, local_dt, receipt_text, t
from services.extras import Deferred
from services.platform import Platform

def item(sku, qty, price): return {"sku": sku, "qty": qty, "price_minor": price}

class Base(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None)
        self.p = Platform(); self.m = "m1"
        self.p.register(self.m, "RW", channel="agent")
    def sandbox(self): os.environ["LYNK_MODE"] = "sandbox"
    def tearDown(self): os.environ.pop("LYNK_MODE", None)

class TestLocale(Base):
    def test_language_priority_and_fallback(self):
        self.assertEqual(choose_language(explicit="fr", country_code="RW"), "fr")       # explicit always wins
        self.assertEqual(choose_language(saved="sw", device="fr", country_code="RW"), "sw")
        self.assertEqual(choose_language(device="fr-CA", country_code="KE"), "fr")
        self.assertEqual(choose_language(country_code="KE"), "en")                       # location suggests the first supported
        self.assertEqual(choose_language(explicit="xx", country_code=None), "en")
        self.assertEqual(t("rw", "new_sale"), "New sale")                                # missing pack: English per string
        self.assertEqual(t("fr", "new_sale"), "Nouvelle vente")
        self.assertEqual(t("sw", "no_such_key"), "no_such_key")

    def test_formats_and_time(self):
        self.assertEqual(format_money(1234567, "RWF"), "RWF 1,234,567")
        self.assertEqual(format_money(1234567, "USD", "fr"), "12\u202f345,67 USD")
        self.assertEqual(local_dt("2026-10-25T22:30:00Z", "RW").hour, 0)                 # Kigali is UTC+2
        self.assertTrue(in_quiet_hours("2026-10-25T22:30:00Z", "RW"))
        self.assertFalse(in_quiet_hours("2026-10-25T10:00:00Z", "RW"))

    def test_receipt_text_and_mode(self):
        txt = receipt_text({"items": [item("rice", 2, 1500)], "total_minor": 3000, "currency": "RWF"}, "2026-10-25T10:00:00Z", "RW", "fr")
        self.assertIn("Ceci n'est pas une facture fiscale", " ".join(txt.split()))  # long lines wrap
        self.assertTrue(all(len(line) <= 32 for line in txt.split("\n")))
        mm = ModeManager()
        self.assertEqual(mm.mode(True, 100), "online"); self.assertEqual(mm.mode(False), "offline"); self.assertEqual(mm.mode(True, 5000), "offline")
        mm.forced_offline = True; self.assertEqual(mm.mode(True, 50), "offline")
        self.assertEqual(mm.chip("offline", 3), "Offline: working normally \u00b7 3 waiting to send")

class TestChat(Base):
    def test_states_inbox_and_safety(self):
        c = self.p.chat; tid = c.open_thread(self.m, "cust:1")
        mid = c.send(self.m, "d", tid, "cust:1", "text", "price of rice?")
        self.assertEqual(c.state(self.m, mid), "sent"); self.assertEqual(c.state(self.m, "unknown"), "queued")
        self.assertEqual(c.inbox(self.m)[0]["unread"], 1)
        c.mark_delivered(self.m, mid, "push"); self.assertEqual(c.state(self.m, mid), "delivered")
        with self.assertRaises(PermissionError): c.mark_read(self.m, "d", mid, "cust:1")
        c.mark_read(self.m, "d", mid, "shop"); self.assertEqual(c.state(self.m, mid), "read"); self.assertEqual(c.inbox(self.m)[0]["unread"], 0)
        c.assign(self.m, tid, "amina"); self.assertEqual(len(c.inbox(self.m, "amina")), 1); self.assertEqual(c.inbox(self.m, "bob"), [])
        c.save_reply(self.m, "hours", "Open 8 to 6"); self.assertEqual(c.saved_reply(self.m, "hours"), "Open 8 to 6")
        c.block(self.m, "cust:9")
        with self.assertRaises(PermissionError): c.send(self.m, "d", tid, "cust:9", "text", "spam")
        c.MAX_PER_MIN = 2
        c.send(self.m, "d", tid, "cust:2", "text", "a"); c.send(self.m, "d", tid, "cust:2", "text", "b")
        with self.assertRaises(PermissionError): c.send(self.m, "d", tid, "cust:2", "text", "c")

    def test_quote_to_paid_order(self):
        self.sandbox(); c = self.p.chat; tid = c.open_thread(self.m, "cust:1")
        qid = c.quote(self.m, "d", tid, "shop", [item("x", 2, 500)]); oid = c.accept_quote(self.m, tid, "cust:1", qid)
        self.assertIn("pay.lynkomni.example", c.pay_link(self.m, "d", tid, "shop", oid)["url"])
        with self.assertRaises(PermissionError): c.confirm_order(self.m, oid)           # a message cannot confirm an order
        self.assertTrue(self.p.payments.charge(self.m, 1000, "mobile_money", oid)["ok"])
        self.assertTrue(c.confirm_order(self.m, oid))

    def test_marketing_needs_consent_and_respects_quiet_hours(self):
        c = self.p.chat; tid = c.open_thread(self.m, "cust:1")
        with self.assertRaises(PermissionError): c.send(self.m, "d", tid, "shop", "marketing", "sale!", customer="cust:1")
        self.p.rights.grant(self.m, "marketing:cust:1")
        with patch("services.extras.in_quiet_hours", return_value=True):
            with self.assertRaises(Deferred): c.send(self.m, "d", tid, "shop", "marketing", "sale!", quiet_country="RW", customer="cust:1")

class TestAdditions(Base):
    def test_credit_collections_and_assistant(self):
        cr, now = self.p.credit, "2026-10-25T10:00:00Z"
        self.assertFalse(cr.sell(self.m, "d", "cust:1", 5000, "2026-10-01T00:00:00Z", limit_minor=4000)["ok"])
        cr.sell(self.m, "d", "cust:1", 1000, "2026-10-01T00:00:00Z"); cr.pay(self.m, "d", "cust:1", 400)
        self.assertEqual(cr.overdue(self.m, now), {"cust:1": 600})
        self.assertIsNotNone(cr.remind(self.m, "d", self.p.chat, "cust:1", now))
        with patch("services.extras.in_quiet_hours", return_value=True):
            self.assertIsNone(cr.remind(self.m, "d", self.p.chat, "cust:1", now, quiet_country="RW"))
        self.assertEqual(self.p.assistant.ask(self.m, "Who owes me?")["figures"], {"cust:1": 600})

    def test_shop_qr_and_verified_receipts(self):
        qr = self.p.shopqr.payload(self.m)["qr_payload"]
        self.assertEqual(self.p.shopqr.verify(qr), self.m); self.assertIsNone(self.p.shopqr.verify(qr.replace("m1", "m2")))
        sid = self.p.pos.record_sale(self.m, "d", [item("x", 1, 700)])["sale_id"]; r = self.p.receipts.issue(self.m, sid)
        self.assertTrue(self.p.receipts.verify(self.m, sid, r["sig"])); self.assertFalse(self.p.receipts.verify(self.m, sid, "bad"))
        self.assertFalse(self.p.receipts.verify(self.m, "nope", r["sig"])); self.assertFalse(r["fiscal"])

    def test_staff_voids_and_cash_shift(self):
        st = self.p.staff; self.p.inventory.receive(self.m, "d", "x", 10, 100)
        shift = st.open_shift(self.m, "d", "amina", 1000)
        sid = self.p.pos.record_sale(self.m, "d", [item("x", 2, 500)])["sale_id"]
        with self.assertRaises(PermissionError): st.void_sale(self.m, "d", "amina", "cashier", sid, "mistake")
        self.assertEqual(self.p.inventory.levels(self.m)["x"], 8)
        close = st.close_shift(self.m, "d", shift, 1900)
        self.assertEqual((close["expected_minor"], close["difference_minor"], close["alert"]), (2000, -100, True))
        st.void_sale(self.m, "d", "bob", "manager", sid, "wrong item")
        self.assertEqual(self.p.inventory.levels(self.m)["x"], 10); self.assertEqual(self.p.accountant.summary(self.m)["revenue_minor"], 0)
        with self.assertRaises(ValueError): st.void_sale(self.m, "d", "bob", "manager", sid, "again")
        self.assertTrue(self.p.c.store.of(self.m, "audit.logged"))

    def test_assistant_confirmation_and_ai_consent(self):
        a = self.p.assistant; self.p.pos.record_sale(self.m, "d", [item("x", 1, 800)])
        self.assertEqual(a.ask(self.m, "How much did I earn?")["source"], "accountant")
        prop = a.propose(self.m, "send_reminder", {"customer": "cust:1"}); self.assertEqual(prop["status"], "needs_confirmation")
        self.assertEqual(a.confirm(self.m, prop["proposal_id"])["action"], "send_reminder")
        with self.assertRaises(ValueError): a.confirm(self.m, prop["proposal_id"])
        class AI:
            def answer(self, q, figures): return "AI says hi"
        b = Platform(ai=AI()); b.register("n1", "RW")
        self.assertEqual(b.assistant.ask("n1", "tell me a joke")["source"], "rules")        # no consent
        b.rights.grant("n1", "ai_assistant")
        self.assertEqual(b.assistant.ask("n1", "tell me a joke")["source"], "ai")
        self.assertEqual(b.assistant.ask("n1", "tell me a joke", online=False)["source"], "rules")

    def test_data_rights(self):
        self.sandbox(); self.p.pos.record_sale(self.m, "d", [item("x", 1, 100)])
        self.p.growth.grant_consent(self.m, "bankA"); self.assertIn("revenue_minor", self.p.growth.share_with_lender(self.m, "bankA"))
        self.p.rights.revoke(self.m, "bankA")
        with self.assertRaises(PermissionError): self.p.growth.share_with_lender(self.m, "bankA")
        self.assertEqual([x[0] for x in self.p.rights.log(self.m)], ["consent.granted", "consent.revoked"])
        self.assertTrue(any(e["type"] == "sale.recorded" for e in self.p.rights.export(self.m)))

    def test_priority_sync_with_data_saver(self):
        sale = {"id": "s1", "type": "sale.recorded", "payload": {"items": [item("x", 1, 100)], "total_minor": 100, "currency": "RWF", "method": "cash"}}
        chat = {"id": "c1", "type": "chat.message", "payload": {"thread_id": "t", "msg_id": "c1", "from": "shop", "kind": "text", "body": "hi"}}
        r = self.p.sync(self.m, "d1", [chat, sale], budget_bytes=len(json.dumps(sale)) + 1)
        self.assertEqual((r["accepted"], r["deferred"]), (1, ["c1"]))                       # money first, chat waits
        self.assertEqual(self.p.sync(self.m, "d1", [chat])["accepted"], 1)

class TestControl(Base):
    def test_revenue_costs_funnel_cac_alerts_access(self):
        self.sandbox(); p, cc, ts = self.p, self.p.control, "2026-10-05T10:00:00Z"
        for m in ("m2", "m3"): p.register(m, "RW", channel="agent")
        p.register("k1", "KE", channel="coop")
        for m in ("m1", "m2", "m3"): cc.record_revenue(m, "subscription", 14500, "RWF", "RW", ts)   # 10 USD each
        cc.record_revenue("k1", "subscription", 129000, "KES", "KE", ts)                               # 10 USD
        cc.record_cost("cloud", 1000, "USD", ts=ts); cc.record_cost("marketing", 600, "USD", "RW", "agent", ts)
        cc.record_cost("agent_commissions", 5000, "USD", "KE", "coop", ts)
        rows = {r["group"]: r for r in cc.revenue("country", "month")}
        self.assertEqual(rows["RW"]["usd_minor"], 3000); self.assertTrue(rows["KE"]["suppressed"] and rows["KE"]["usd_minor"] is None)
        self.assertEqual(cc.pnl("month")[0]["profit_usd_minor"], 4000 - 1000 - 600 - 5000)
        self.assertEqual(cc.pnl("month", "RW")[0]["profit_usd_minor"], 3000 - 600)
        for m, when in (("m1", "2026-10-20T08:00:00Z"), ("m2", "2026-10-22T08:00:00Z"), ("m3", "2026-09-01T08:00:00Z")):
            p.c.store.append(m, "d", "sale.recorded", {"items": [], "total_minor": 1, "currency": "RWF", "method": "cash"}, ts=when)
        self.assertEqual(cc.funnel("2026-10-25T12:00:00Z"), {"registered": 4, "activated": 3, "weekly_active": 2, "paid": 4})
        self.assertEqual(cc.cac()["agent"]["cac_usd_minor"], 200)
        p.payments.charge("m1", 145000, "mobile_money", "k1"); cc.record_revenue("m1", "payment_fee", 1450, "RWF", "RW", ts)
        self.assertEqual(cc.volume_vs_revenue(), {"payment_volume_usd_minor": 10000, "payment_fee_revenue_usd_minor": 100})
        self.assertEqual(cc.reliability()["payment_success_rate"], 1.0)
        self.assertIn({"alert": "negative_margin", "country": "KE", "period": "2026-10"}, cc.alerts())
        with self.assertRaises(PermissionError): cc.view("support", "revenue")
        with self.assertRaises(PermissionError): cc.view("finance", "acquisition", now=ts)
        self.assertEqual({r["group"] for r in cc.view("country_lead:RW", "revenue")}, {"RW"})
        self.assertTrue(cc.view("founder", "alerts")); self.assertTrue(p.c.store.of("_company", "audit.logged"))

if __name__ == "__main__":
    unittest.main()
