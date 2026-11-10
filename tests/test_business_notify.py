"""Business app and device notifications and messages (MASTER UPDATE sections 56 and 62; build section 3)."""
import unittest
from services.business_notify import BusinessNotices, DeviceBell
from services.messages import Notifier

T0 = 1_800_000_000


class Notices(unittest.TestCase):
    def setUp(self):
        self.ev = []
        self.n = Notifier()
        self.b = BusinessNotices("biz-1", "owner-1", self.n, emit=lambda t, p: self.ev.append((t, p)))
        self.b.staff("mgr-1", "manager"); self.b.staff("stk-1", "stock_staff"); self.b.staff("stk-2", "stock_staff"); self.b.staff("c1", "cashier")

    def test_role_routing_and_done_by(self):
        out = self.b.stock_level("rice", 4000, "ev-1", now=T0)
        self.assertEqual(len(out), 2, "both stock staff, nobody else")
        self.assertEqual(self.n.bell("owner-1", now=T0)["new"], [])
        nid = out[0]["nid"]
        self.b.done_by(nid, "stk-2")
        for p in ("stk-1", "stk-2"):
            line = self.n.bell(p, now=T0)["earlier"] + self.n.bell(p, now=T0)["new"]
            self.assertEqual(line[0]["done_by"], "stk-2")
        self.assertEqual(self.b.stock_level("rice", 6000, "ev-2", now=T0), [], "above the owner's threshold: nothing")

    def test_only_the_owner_sets_thresholds(self):
        with self.assertRaises(PermissionError):
            self.b.set_threshold("mgr-1", "cash_difference_minor", 0)
        self.b.set_threshold("owner-1", "cash_difference_minor", 1000)
        self.assertEqual(self.b.cash_count(10_000, 10_900, "XAF", "ev-3", now=T0), [])
        r = self.b.cash_count(10_000, 8_900, "XAF", "ev-4", now=T0)
        self.assertEqual(r[0]["state"], "shown")
        self.assertEqual(self.n.lines[r[0]["nid"]]["facts"], {"difference_minor": -1100, "currency": "XAF"})
        with self.assertRaises(ValueError):
            self.b.set_threshold("owner-1", "cash_difference_minor", 1.5)
        self.assertEqual(self.ev[-1][0], "ThresholdChanged")

    def test_receipts_and_documents_only_when_asked_and_only_to_a_vault_reference(self):
        with self.assertRaises(PermissionError):
            self.b.send_document("receipt", "LORCP-7731-0042-9911", "text", "pii_7", False, "c1")
        with self.assertRaises(ValueError):
            self.b.send_document("receipt", "LORCP-7731-0042-9911", "text", "+237600000000", True, "c1")
        r = self.b.send_document("receipt", "LORCP-7731-0042-9911", "text", "pii_7", True, "c1", now=T0)
        self.assertEqual(r["channels"], ["text"])
        self.assertEqual(self.n.messages("pii_7")[0]["sender"], "receipts@mail.lynkomni.com")
        self.b.send_document("document", "LODOC-9001-0044-2814", "email", "pii_7", True, "c1", now=T0)
        self.assertEqual([t for t, _ in self.ev], ["DocumentSent", "DocumentSent"])

    def test_owner_summary_needs_consent_and_uses_integers(self):
        f = BusinessNotices.build_summary([1500, 2500, 1000], (5000, 4800), [("rice", 4000, 5000), ("bread", 9000, 5000)], ["x"], "XAF")
        self.assertEqual(f, {"sales_count": 3, "sales_minor": 5000, "currency": "XAF", "cash_expected_minor": 5000, "cash_counted_minor": 4800, "to_reorder": ["rice"], "needs_attention": 1})
        self.assertEqual(self.b.send_summary(f, "2026-11-10")["state"], "refused")
        with self.assertRaises(PermissionError):
            self.b.choose_summary("mgr-1", "day", "email", 19, True)
        self.b.choose_summary("owner-1", "day", "email", 19, True)
        self.assertEqual(self.b.send_summary(f, "2026-11-10", now=T0)["state"], "in_summary")
        self.assertEqual(self.ev[-1][1]["channel"], "email")


class Bell(unittest.TestCase):
    def test_the_device_bell_folds_offline_and_merges_without_doubles(self):
        d = DeviceBell("dev-1")
        d.raise_("sync_retried", "e1", "Waiting to send", now=1)
        d.raise_("sync_retried", "e2", "Waiting to send", now=2)
        d.raise_("stock_low", "e3", "Low stock: Rice", record="rice", now=3)
        d.raise_("device_hard_locked", "e4", "A staff PIN locked", now=4)
        self.assertEqual(len(d.lines), 3)
        self.assertEqual([l["kind"] for l in d.unread()], ["device_hard_locked", "stock_low", "sync_retried"], "what needs action first")
        merged = d.merge([{"nid": "c1", "kind": "stock_low", "events": ["e3"]}])
        self.assertEqual(sorted(l["kind"] for l in merged), ["device_hard_locked", "stock_low", "sync_retried"])
        with self.assertRaises(KeyError):
            d.raise_("made_up", "e5", "x")


if __name__ == "__main__":
    unittest.main()
