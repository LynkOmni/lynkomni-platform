"""Contract version 10 (build section 4, step C1): version 9 plus the conversation events of CHAT UPDATE (74.24). Nothing older
changes; a version 9 event reads as version 10 with only its version raised. No message text, live sign, card number, PIN, code,
position, vote or name is ever in an event."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT
from contract.tools.validate_contract import validate_event
from core import chat

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V9, V10 = load("event-payloads.v9.json"), load("event-payloads.v10.json")
REG9, REG10 = load("command-policy-register.v9.json"), load("command-policy-register.v10.json")
NEW = {"ConversationOpened", "MessagePosted", "MessageEdited", "MessageStateChanged", "ConversationRouted", "ConversationHandedOver",
       "ConversationClosed", "ConversationReported"}
CLOUD_ONLY = {"MessageStateChanged", "ConversationRouted", "ConversationHandedOver"}


class ContractV10(unittest.TestCase):
    def test_built_from_v9_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v10.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreaterEqual(CURRENT, 10)                                  # version 11 (section 4, step D2b) reads version 10 unchanged

    def test_only_the_new_events_are_added_and_the_card_list_only_grows(self):
        self.assertEqual(set(V10["events"]) - set(V9["events"]), NEW)
        for name, e in V9["events"].items():
            if name == "ConversationCardSent":
                continue
            self.assertEqual((V10["events"][name]["payload"], V10["events"][name]["origins"]), (e["payload"], e["origins"]), name)
        old = V9["events"]["ConversationCardSent"]["payload"]["properties"]["card"]["enum"]
        new = V10["events"]["ConversationCardSent"]["payload"]["properties"]["card"]["enum"]
        self.assertEqual(new[:len(old)], old, "an older card keeps its value")
        self.assertTrue(set(old) <= set(new) <= set(old) | set(chat.CARDS), "the cards grow from catalog/chat.v1.json; later cards join a later version")
        self.assertTrue(all(e["schema_version"] == 10 for e in V10["events"].values()))
        self.assertEqual(REG10["commands"][:len(REG9["commands"])], REG9["commands"])

    def test_the_cloud_alone_writes_states_routing_and_hand_overs(self):
        for name in CLOUD_ONLY:
            self.assertEqual(V10["events"][name]["origins"], ["server"], name)
        emitted = {e for c in REG10["commands"] for e in c["emits"]}
        for name in NEW - CLOUD_ONLY:
            self.assertIn("device", V10["events"][name]["origins"], name)
            self.assertIn(name, emitted, f"{name} has its offline device command")
        for name in CLOUD_ONLY:
            self.assertNotIn(name, emitted, f"{name} is written by the cloud alone")
        states = V10["events"]["MessageStateChanged"]["payload"]["properties"]["state"]["enum"]
        self.assertEqual(sorted(states), sorted(chat.CHAT["states"]["cloud_writes"]))

    def test_no_text_secret_sign_or_personal_field(self):
        fields = {f.lower() for n in NEW for f in V10["events"][n]["payload"]["properties"]}
        for word in ("pin", "card", "phone", "position", "latitude", "password", "name", "text", "body_text", "typing", "sign", "vote", "draft", "code"):
            self.assertFalse([f for f in fields if word in f.split("_")], f"no field about {word}: {sorted(fields)}")
        self.assertIn("content_sha256", V10["events"]["MessagePosted"]["payload"]["required"], "the text stays in the message store")
        for k in ("personal_chat", "group_chat", "staff_to_staff"):
            self.assertIn(k, chat.CHAT["never"])
            self.assertNotIn(k, V10["events"]["ConversationOpened"]["payload"]["properties"]["kind"]["enum"])

    def test_a_version_9_event_reads_as_version_10_unchanged(self):
        old = {"type": "InvoiceIssued", "schema_version": 9, "payload": {"invoice_id": "i1", "total": 5, "currency": "USD", "issued_on": "2026-11-19"}}
        up = upcast(old)
        self.assertEqual((up["schema_version"], up["payload"]), (CURRENT, old["payload"]))
        self.assertEqual(old["schema_version"], 9, "the stored event is never rewritten")

    def test_a_new_event_validates(self):
        from contract.tools.validate_contract import uuid7, ts, fake_sig, MERCHANT
        ok = {"event_id": uuid7(), "origin": "server", "merchant_id": MERCHANT, "type": "MessageStateChanged", "schema_version": CURRENT,
              "created_at_server": ts(), "server_cursor": 1, "server_signature": fake_sig(),
              "payload": {"message_id": uuid7(), "state": "confirmed"}}
        self.assertEqual(validate_event(ok), [])
        bad = json.loads(json.dumps(ok)); bad["payload"]["state"] = "seen"
        self.assertTrue(validate_event(bad), "only the five agreed states")
        bad = json.loads(json.dumps(ok)); bad["payload"]["text"] = "hello"
        self.assertTrue(validate_event(bad), "a message's text never travels in an event")


if __name__ == "__main__":
    unittest.main()
