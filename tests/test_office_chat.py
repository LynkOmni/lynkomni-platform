"""The office services in a customer conversation (CHAT UPDATE 74.5) and LynkAssist's office skills (ASSIST UPDATE 75.6), section 4
step D4c. A card comes only from its own service and its actions open that service's step; Pay is never offered offline or on
a paid invoice; every conversation goes on the customer's timeline; the chats behind a figure open by role. LynkAssist only
suggests, drafts and explains here; posting, filing and payroll stay with a person."""
import os, unittest
os.environ["LYNK_MODE"] = "sandbox"

from services import assist_register as AR

LINES = [{"name": "Work", "qty_milli": 2000, "unit_minor": 5000}]


class Chat(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"
        from services.platform import Platform
        self.p = Platform(); self.p.register("m1", "RW"); self.c = self.p.office_chat
        self.p.billing.set_plan("m1", "lynkinv", "pro"); self.p.billing.set_plan("m1", "lynkcrm", "pro")
        self.cust = self.p.crm.create("m1", "u1", "customer", name="Amina")

    def test_an_invoice_card_comes_from_lynkinv_and_pay_opens_checkout(self):
        conv = self.c.open("m1", self.cust)
        card = self.c.make_invoice("m1", conv, LINES, None)
        self.assertEqual((card["service"], card["body"]["to_pay_minor"] > 0), ("lynkinv", True))
        self.assertEqual(card["actions"], ["pay", "chat_about"])
        self.assertNotIn("pay", self.c.card("m1", conv, "invoice", card["record"], online=False)["actions"], "never Pay offline")
        self.assertEqual(self.c.act("m1", conv, "invoice", card["record"], "pay")["opens"], "lynkcheckout")
        self.p.invoicing.record_payment("m1", card["record"], "cash", card["body"]["to_pay_minor"])
        self.assertNotIn("pay", self.c.card("m1", conv, "invoice", card["record"])["actions"], "nothing to pay, no Pay")
        events = [e["type"] for e in self.p.c.store.since("m1")]
        self.assertIn("chat.card_sent", events)
        self.assertIn(conv, self.p.crm.timeline("m1", self.cust, ["chats", "invoices"]))

    def test_promise_quote_credit_note_new_customer_note_and_follow_up(self):
        conv = self.c.open("m1")
        with self.assertRaises(ValueError):
            self.c.make_invoice("m1", conv, LINES, None)
        rid = self.c.new_customer("m1", conv, "u1", name="Jean", email="jean@shop.rw")
        self.assertNotIn("jean@shop.rw", str(list(self.p.c.store.since("m1"))))
        q = self.c.make_quote("m1", conv, 10000)
        self.assertEqual((q["kind"], q["actions"]), ("quote", ["accept", "chat_about"]))
        inv = self.c.make_invoice("m1", conv, LINES, None)["record"]
        self.assertEqual(self.c.act("m1", conv, "reminder", inv, "promise_to_pay", date="2026-12-01")["promise"], "2026-12-01")
        self.assertEqual(self.c.card("m1", conv, "reminder", inv)["body"]["promise"], "2026-12-01")
        self.p.billing.set_plan("m1", "lynkinv", "max")
        cn = self.p.invoicing.credit_note("m1", inv, 1000, "short delivery")["credit"]
        self.assertEqual(self.c.card("m1", conv, "credit_note", cn)["body"]["amount_minor"], 1000)
        n, f = self.c.note("m1", conv, "u1", "Prefers mornings"), self.c.follow_up("m1", conv, "u1", "2026-12-02")
        self.assertTrue({n, f, conv} <= set(self.p.crm.timeline("m1", rid, ["chats", "notes", "invoices"])))
        with self.assertRaises(ValueError):
            self.c.card("m1", conv, "receipt", inv)

    def test_chat_figures_are_real_and_the_chats_behind_them_open_by_role(self):
        convs = [self.c.open("m1", self.cust) for _ in range(3)]
        for i, cv in enumerate(convs):
            self.c.record(cv, first_reply_min=4 + i, solved_min=30, reopened=(i == 0), solved_by_assist=(i == 2))
        f = self.c.chat_figures("m1")
        self.assertEqual((f["conversations"], f["reopened"], f["solved_by_assist"]), (3, 1, 1))
        self.assertIsNone(f["usually_replies_within"], "fewer than 20 replies: never invented")
        self.assertEqual(self.c.act("m1", convs[0], "report", "r", "open_chats", figure="reopened", role="owner")["conversations"], [convs[0]])
        with self.assertRaises(PermissionError):
            self.c.chats_behind("m1", "reopened", "cashier")


class Skills(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"
        from services.platform import Platform
        from services.assist_office import OfficeAssist
        self.p = Platform(); self.p.register("m1", "RW")
        self.p.billing.set_plan("m1", "lynkinv", "pro"); self.p.billing.set_plan("m1", "lynkcrm", "pro")
        self.a = OfficeAssist(self.p, "m1", "u0", "u0")

    def test_every_office_skill_is_registered_and_built(self):
        from services.assist_office import OFFICE_ACTIONS
        for a in OFFICE_ACTIONS:
            self.assertIn(a, AR.ACTIONS, a)
            self.assertEqual(AR.ACTIONS[a]["status"], "built", a)

    def test_suggestions_never_post_and_drafts_never_issue(self):
        self.p.books.record_bill("m1", "u1", 5000, account="6200", supplier="S1")
        r = self.a.do("d1", "u0", "owner", "acc_suggest_category", supplier="S1")
        self.assertEqual((r["state"], r["result"]["suggestion"], r["result"]["posted"]), ("done", "6200", False))
        self.assertIsNone(self.a.do("d1", "u0", "owner", "acc_suggest_category", supplier="S9")["result"]["suggestion"])
        d = self.a.do("d1", "u0", "owner", "inv_draft_from_chat", confirmed=True, customer="c", lines=LINES)
        self.assertEqual((d["result"]["issued"], len(self.p.invoicing.inv.items())), (False, 0))
        self.assertEqual(self.a.do("d1", "u0", "owner", "inv_draft_from_chat")["state"], "not_done", "a draft needs Confirm")
        self.assertEqual(self.a.do("d1", "u0", "owner", "acc_month_end_checklist", done=[])["result"]["closed"], False)
        self.assertEqual(self.a.do("d1", "u0", "owner", "inv_draft_from_photo", confirmed=True, online=False, lines=LINES)["needs"], "prepare_for_later")

    def test_tax_filing_and_payroll_are_only_handed_over(self):
        for a in ("file_tax_return", "run_payroll"):
            r = self.a.do("d1", "u0", "owner", a, confirmed=True)
            self.assertEqual((r["needs"], r["state"]), ("hand_over", "not_done"), a)

    def test_next_contact_respects_consent_and_why_changed_labels_estimates(self):
        cust = self.p.crm.create("m1", "u1", "customer", name="Amina")
        self.p.invoicing.issue("m1", cust, LINES)
        nxt = self.a.do("d1", "u0", "owner", "crm_next_contact")["result"]["next"]
        self.assertEqual((nxt[0]["may_message"], nxt[0]["suggest"]), (False, "call_or_visit"))
        self.p.crm.consent("m1", cust, "email", True)
        self.assertEqual(self.a.do("d1", "u0", "owner", "crm_next_contact")["result"]["next"][0]["suggest"], "message")
        w = self.a.do("d1", "u0", "owner", "stat_why_changed", start="2026-01-01", end="2026-01-31", before=10, after=7, estimate=True)["result"]
        self.assertEqual((w["change"], w["label"]), (-3, "estimate"))
        s = self.a.do("d1", "u0", "owner", "crm_customer_summary", record=cust, team="t")["result"]
        self.assertEqual(s["invoices"], 1); self.assertGreater(s["owed_minor"], 0)


if __name__ == "__main__":
    unittest.main()
