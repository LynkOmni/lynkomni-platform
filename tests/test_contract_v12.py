"""Contract version 12 (build section 4, step E2): version 11 plus the voting events of VOTE UPDATE (68). Nothing older changes; a
version 11 event reads as version 12 with only its version raised. A choice, a voter's identity beside a ballot, a key part, a
credential, a contact detail or a time of casting is never in an event; a ballot appears only as its tracking code. Only casting
and challenging a ballot may come from a (polling-place) device, in sealed batches; everything else is written by the cloud alone."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT
from contract.tools.validate_contract import validate_event, uuid7, ts, fake_sig, MERCHANT

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V11, V12 = load("event-payloads.v11.json"), load("event-payloads.v12.json")
REG11, REG12 = load("command-policy-register.v11.json"), load("command-policy-register.v12.json")
NEW = {"VoteCreated", "VoteRulesLocked", "VoteRulesChanged", "TrusteeKeyPublished", "VoteRollLocked", "VoteOpened", "BallotCast",
       "BallotChallenged", "BallotReplaced", "VoteReminderSent", "VoteClosed", "BallotsShuffled", "TallyPublished", "VoteResultCertified",
       "VoteAnomalyFlagged", "VoteCredentialReissued", "DecisionRecorded", "MinutesSigned"}
DEVICE = {"BallotCast", "BallotChallenged"}


class ContractV12(unittest.TestCase):
    def test_built_from_v11_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v12.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreaterEqual(CURRENT, 12)                                  # version 13 (section 4, step E3) reads version 12 unchanged

    def test_only_the_new_events_are_added(self):
        self.assertEqual(set(V12["events"]) - set(V11["events"]), NEW)
        for name, e in V11["events"].items():
            self.assertEqual((V12["events"][name]["payload"], V12["events"][name]["origins"]), (e["payload"], e["origins"]), name)
        self.assertTrue(all(e["schema_version"] == 12 for e in V12["events"].values()))
        self.assertEqual(REG12["commands"][:len(REG11["commands"])], REG11["commands"])

    def test_the_cloud_alone_writes_everything_but_casting_and_challenging(self):
        emitted = {e for c in REG12["commands"] for e in c["emits"]}
        for name in NEW - DEVICE:
            self.assertEqual(V12["events"][name]["origins"], ["server"], name)
            self.assertNotIn(name, emitted, f"{name} is written by the cloud alone")
        for name in DEVICE:
            self.assertIn("device", V12["events"][name]["origins"], name)
            self.assertIn(name, emitted, f"{name} has its device command")
        for c in REG12["commands"][len(REG11["commands"]):]:
            self.assertTrue(c["offline"]["sealed"], "an offline ballot travels only in a sealed batch")
            self.assertTrue(c["cloud_may_reject"], "the cloud checks every proof")

    def test_no_choice_voter_key_credential_contact_or_time(self):
        fields = {f.lower() for n in NEW for f in V12["events"][n]["payload"]["properties"]}
        for word in ("choice", "choices", "vote", "voter", "candidate", "option", "secret", "share", "key", "credential", "code",
                     "name", "email", "phone", "address", "ip", "device", "time", "at", "cast", "position", "pin", "password"):
            hits = [f for f in fields if word in f.split("_") and f not in ("vote_id", "tracking_code", "key_sha256")]
            self.assertFalse(hits, f"no field about {word}: {hits}")
        self.assertEqual(V12["events"]["BallotCast"]["payload"]["properties"]["tracking_code"], {"$ref": "#/$defs/sha256"})

    def test_a_rule_change_needs_two_people(self):
        self.assertEqual(V12["events"]["VoteRulesChanged"]["payload"]["properties"]["approvers"]["minimum"], 2)

    def test_a_version_11_event_reads_as_version_12_unchanged(self):
        old = {"type": "LockDateSet", "schema_version": 11, "payload": {"date": "2026-10-31"}}
        up = upcast(old)
        self.assertEqual((up["schema_version"], up["payload"]), (CURRENT, old["payload"]))
        self.assertEqual(old["schema_version"], 11, "the stored event is never rewritten")

    def test_a_cloud_tally_validates_and_a_choice_is_refused(self):
        ok = {"event_id": uuid7(), "origin": "server", "merchant_id": MERCHANT, "type": "TallyPublished", "schema_version": CURRENT,
              "created_at_server": ts(), "server_cursor": 1, "server_signature": fake_sig(),
              "payload": {"vote_id": uuid7(), "results_sha256": "a" * 64, "proofs_sha256": "b" * 64, "trustees": 2}}
        self.assertEqual(validate_event(ok), [])
        bad = json.loads(json.dumps(ok)); bad["payload"]["choice"] = "A"
        self.assertTrue(validate_event(bad), "a choice never travels in an event")
        bad = json.loads(json.dumps(ok)); bad["payload"]["vote_id"] = "LOVOT-1234-5678-9012"
        self.assertTrue(validate_event(bad), "events carry the internal id; the public LOVOT- id is looked up through core/ids.py")
        self.assertEqual(V12["events"]["VoteCreated"]["payload"]["properties"]["vote_id"], V12["events"]["VoteRollImported"]["payload"]["properties"]["vote_id"])


if __name__ == "__main__":
    unittest.main()
