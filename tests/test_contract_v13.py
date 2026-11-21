"""Contract version 13 (build section 4, step E3): version 12 plus LynkFiles' document engine (SIX SERVICES UPDATE 69.7). Nothing older
changes; a version 12 event reads as version 13 with only its version raised. A file's content or name, a signer's name or contact, a
link's address or password and a verification code are never in an event. Only a new version of a kept file may come from a device."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT
from contract.tools.validate_contract import validate_event, uuid7, ts, fake_sig, MERCHANT

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V12, V13 = load("event-payloads.v12.json"), load("event-payloads.v13.json")
REG12, REG13 = load("command-policy-register.v12.json"), load("command-policy-register.v13.json")
NEW = {"SignatureRequested", "DocumentSigned", "SignatureDeclined", "SignatureCompleted", "ShareLinkCreated", "ShareLinkStopped",
       "FileVersionAdded", "LegalHoldChanged", "FileDeleted"}
DEVICE = {"FileVersionAdded"}


class ContractV13(unittest.TestCase):
    def test_built_from_v12_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v13.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreaterEqual(CURRENT, 13)                                  # version 14 (section 4, step E4a) reads version 13 unchanged

    def test_only_the_new_events_are_added(self):
        self.assertEqual(set(V13["events"]) - set(V12["events"]), NEW)
        for name, e in V12["events"].items():
            self.assertEqual((V13["events"][name]["payload"], V13["events"][name]["origins"]), (e["payload"], e["origins"]), name)
        self.assertTrue(all(e["schema_version"] == 13 for e in V13["events"].values()))
        self.assertEqual(REG13["commands"][:len(REG12["commands"])], REG12["commands"])

    def test_the_cloud_alone_signs_shares_holds_and_deletes(self):
        emitted = {e for c in REG13["commands"] for e in c["emits"]}
        for name in NEW - DEVICE:
            self.assertEqual(V13["events"][name]["origins"], ["server"], name)
            self.assertNotIn(name, emitted, name)
        for name in DEVICE:
            self.assertIn("device", V13["events"][name]["origins"])
            self.assertIn(name, emitted)

    def test_no_content_name_contact_address_password_or_code(self):
        fields = {f.lower() for n in NEW for f in V13["events"][n]["payload"]["properties"]}
        for word in ("name", "email", "phone", "address", "url", "content", "text", "body", "code", "token", "position"):
            self.assertFalse([f for f in fields if word in f.split("_") and f != "code_sha256"], word)
        self.assertEqual(V13["events"]["ShareLinkCreated"]["payload"]["properties"]["password"], {"type": "boolean"}, "only whether a password is set")

    def test_a_version_12_event_reads_as_version_13_unchanged(self):
        old = {"type": "VoteClosed", "schema_version": 12, "payload": {"vote_id": uuid7(), "ballots": 3, "list_head": "a" * 64}}
        up = upcast(old)
        self.assertEqual((up["schema_version"], up["payload"]), (CURRENT, old["payload"]))

    def test_a_share_link_validates_and_its_address_is_refused(self):
        ok = {"event_id": uuid7(), "origin": "server", "merchant_id": MERCHANT, "type": "ShareLinkCreated", "schema_version": CURRENT,
              "created_at_server": ts(), "server_cursor": 1, "server_signature": fake_sig(),
              "payload": {"link_id": uuid7(), "document_id": uuid7(), "rights": "view", "days": 7, "password": True, "download_blocked": False}}
        self.assertEqual(validate_event(ok), [])
        for k, v in (("url", "https://files.example/x"), ("days", 400), ("rights", "own")):
            bad = json.loads(json.dumps(ok)); bad["payload"][k] = v
            self.assertTrue(validate_event(bad), k)


if __name__ == "__main__":
    unittest.main()
