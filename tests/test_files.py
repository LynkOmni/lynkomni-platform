"""LynkFiles' document engine (SIX SERVICES UPDATE, master blueprint 69.7; section 4 step E3): catalog/files.v1.json read through
core/files.py and ts/src/files.ts with shared vectors, and the cloud engine services/files.py.

A file is kept under its record and opens only where that record's service allows; programs are refused by their bytes; every
version is kept; nothing under legal hold changes, is shared or deleted; a share link has an end date and a password kept only as a
hash; signers follow their order and sign the exact version they saw; partner signatures are written only on the partner's answer;
the verification code shows the fingerprint and never who signed; no event carries content, names, addresses or codes."""
import json, os, subprocess, sys, unittest

from core import files as F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V13 = json.load(open(os.path.join(ROOT, "contract", "event-payloads.v13.json"), encoding="utf-8"))["events"]
PDF = b"%PDF-1.7\n1 0 obj << >> endobj\n"
PDF2 = b"%PDF-1.7\n1 0 obj << /Changed true >> endobj\n"
RID = "01890a5d-ac96-774b-bcce-b302099a8057"


class Rules(unittest.TestCase):
    def test_vectors_and_the_typescript_register_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "files_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_programs_are_refused_by_their_bytes_not_their_name(self):
        self.assertEqual(F.sniff(b"MZ\x90\x00"), "blocked")
        self.assertEqual(F.sniff(b"#!/bin/sh\nrm -rf /"), "blocked")
        self.assertEqual(F.sniff(PDF), "pdf")
        self.assertIsNone(F.sniff(b"\x00\x01binary"))

    def test_every_record_kind_belongs_to_a_billing_family(self):
        from services import billing
        for fam in F.FILES["record_kinds"].values():
            self.assertIn(fam, billing.FAMILIES)
        contract = V13["DocumentFiled"]["payload"]["properties"]
        self.assertEqual(sorted(F.FILES["record_kinds"]), sorted(contract["record_kind"]["enum"]))
        self.assertEqual(F.FILES["kinds"], contract["kind"]["enum"])


class Engine(unittest.TestCase):
    def setUp(self):
        from services.platform import Platform
        self.p = Platform(); self.p.register("m1", "RW"); self.f = self.p.files
        self.doc = self.f.store("m1", "owner", "invoice", RID, "contract", PDF)

    def events(self):
        return [e for e in self.p.c.store.since("m1") if e["type"] in V13 and (V13[e["type"]].get("since") == "v13" or e["type"] == "DocumentFiled")]

    def test_keeping_versions_and_restoring(self):
        with self.assertRaises(ValueError):
            self.f.store("m1", "owner", "invoice", RID, "contract", b"MZ\x90\x00 a program called invoice.pdf")
        self.assertEqual(self.f.add_version("m1", self.doc, "owner", PDF2), 2)
        self.assertEqual(self.f.restore("m1", self.doc, "owner", 1), 3)
        self.assertEqual(self.f.open("m1", self.doc, "owner")["data"], PDF)
        with self.assertRaises(ValueError):
            self.f.add_version("m1", self.doc, "owner", b"\x89PNG\r\n\x1a\n....")                # a version keeps the file's type

    def test_a_file_opens_only_where_its_records_service_allows(self):
        self.assertTrue(self.f.may_open("m1", self.doc, {"inv": ["view"]}))
        with self.assertRaises(PermissionError):
            self.f.open("m1", self.doc, "staff-1", {"crm": ["view", "edit"]})
        self.assertEqual([a["what"] for a in self.f.audit("m1", self.doc)], ["version_added"])

    def test_legal_hold_blocks_changes_sharing_and_deleting_and_stops_links(self):
        lid, tok = self.f.share("m1", self.doc, "owner")
        self.f.hold("m1", self.doc, True, "owner")
        self.assertEqual(self.f.open_link(tok)["reason"], "stopped")
        for act in (lambda: self.f.add_version("m1", self.doc, "owner", PDF2), lambda: self.f.share("m1", self.doc, "owner"),
                    lambda: self.f.delete("m1", self.doc, "owner")):
            with self.assertRaises(PermissionError):
                act()
        self.f.hold("m1", self.doc, False, "owner")
        self.f.delete("m1", self.doc, "owner")
        with self.assertRaises(KeyError):
            self.f.open("m1", self.doc, "owner")

    def test_share_links_end_need_their_password_and_stop_at_once(self):
        with self.assertRaises(ValueError):
            self.f.share("m1", self.doc, "owner", days=400)
        lid, tok = self.f.share("m1", self.doc, "owner", days=2, password="long enough", download_blocked=True)
        self.assertEqual(self.f.open_link(tok)["reason"], "password")
        self.assertEqual(self.f.open_link(tok, "wrong one!")["reason"], "password")
        got = self.f.open_link(tok, "long enough")
        self.assertTrue(got["ok"]); self.assertFalse(got["download"])
        self.f.now = lambda: 10 ** 12
        self.assertEqual(self.f.open_link(tok, "long enough")["reason"], "expired")
        stored = json.dumps([l for _, l in self.f.links.items()])
        self.assertNotIn("long enough", stored); self.assertNotIn(tok, stored)

    def test_signers_follow_their_order_and_sign_what_they_saw(self):
        rid, (a, b) = self.f.request_signatures("m1", self.doc, "owner", ["Ana, ana@example.org", "Bo, +250788000000"])
        sha = self.f.open("m1", self.doc, "owner")["sha256"]
        with self.assertRaises(PermissionError):
            self.f.sign(b, sha)                                                            # in order: Bo waits for Ana
        with self.assertRaises(ValueError):
            self.f.sign(a, "0" * 64)                                                       # not the version she saw
        self.assertEqual(self.f.sign(a, sha), "partly_signed")
        self.assertEqual(self.f.sign(b, sha), "completed")
        code = self.f.code_for("m1", rid)
        self.assertTrue(F.code_ok(code))
        v = self.f.verify(code.lower())
        self.assertEqual((v["sha256"], v["signers"]), (sha, 2))
        self.assertNotIn("Ana", json.dumps(v))
        self.assertFalse(self.f.verify("2222-2222-2222")["ok"])

    def test_a_refusal_stops_the_request(self):
        rid, (a, b) = self.f.request_signatures("m1", self.doc, "owner", ["Ana", "Bo"], order="together")
        sha = self.f.open("m1", self.doc, "owner")["sha256"]
        self.f.decline(b, "wrong_document")
        with self.assertRaises(PermissionError):
            self.f.sign(a, sha)
        self.assertEqual(self.f.state(rid), "declined")

    def test_partner_signatures_wait_for_the_partner(self):
        with self.assertRaises(PermissionError):
            self.f.request_signatures("m1", self.doc, "owner", ["Ana"], level="qualified")   # Coming to your country soon
        rid, (a,) = self.f.request_signatures("m1", self.doc, "owner", ["Ana"], level="simple")
        r = self.f.requests.get(rid); r["level"] = "identity_checked"                       # as if the partner were signed
        sha = self.f.open("m1", self.doc, "owner")["sha256"]
        self.assertEqual(self.f.sign(a, sha), "waiting_for_partner")
        self.assertNotIn("DocumentSigned", [e["type"] for e in self.events()])
        self.assertEqual(self.f.partner_answer(rid, 1, True), "completed")

    def test_the_plan_limits_signature_requests_and_storage(self):
        for _ in range(5):
            self.f.request_signatures("m1", self.doc, "owner", ["Ana"])
        with self.assertRaises(PermissionError):
            self.f.request_signatures("m1", self.doc, "owner", ["Ana"])                     # Free: 5 a month
        self.assertFalse(F.fits(self.f.used("m1"), 5 * F.GB, 5))

    def test_events_fit_the_contract_and_carry_no_content_names_addresses_or_codes(self):
        rid, (a,) = self.f.request_signatures("m1", self.doc, "owner", ["Ana, ana@example.org"])
        self.f.sign(a, self.f.open("m1", self.doc, "owner")["sha256"])
        _, tok = self.f.share("m1", self.doc, "owner", password="long enough")
        code = self.f.code_for("m1", rid)
        for e in self.events():
            spec = V13[e["type"]]["payload"]
            self.assertTrue(set(spec["required"]) <= set(e["payload"]) <= set(spec["properties"]), e["type"])
            text = json.dumps(e["payload"])
            for secret in ("Ana", "example.org", "PDF", tok, code, "long enough"):
                self.assertNotIn(secret, text, e["type"])


if __name__ == "__main__":
    unittest.main()
