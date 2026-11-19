"""Contract version 8 (owner decision 2026-11-19): version 7 without WhatsApp. LynkAttend PINs and agreement codes, joining a LynkQueue
queue and answering a LynkSurvey survey no longer name WhatsApp; nothing else changes. An older event that names WhatsApp reads as
LynkChat, and the stored event is never rewritten."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT
from contract.tools.validate_contract import validate_event

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V7, V8 = load("event-payloads.v7.json"), load("event-payloads.v8.json")
REG7, REG8 = load("command-policy-register.v7.json"), load("command-policy-register.v8.json")


class ContractV8(unittest.TestCase):
    def test_built_from_v7_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v8.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(CURRENT, 8)

    def test_no_whatsapp_anywhere_in_version_8(self):
        self.assertNotIn("whatsapp", json.dumps(V8["events"]).lower())
        self.assertNotIn("whatsapp", json.dumps(REG8["commands"]).lower())

    def test_only_the_whatsapp_values_changed(self):
        self.assertEqual(set(V7["events"]), set(V8["events"]))
        self.assertEqual(REG7["commands"], REG8["commands"])
        for name, e in V7["events"].items():
            old = json.loads(json.dumps(e["payload"]).replace('"code_whatsapp", ', "").replace('"whatsapp", ', ""))
            self.assertEqual((V8["events"][name]["payload"], V8["events"][name]["origins"]), (old, e["origins"]), name)
            self.assertEqual(V8["events"][name]["schema_version"], 8)

    def test_an_older_whatsapp_value_reads_as_lynkchat(self):
        old = {"type": "TicketIssued", "schema_version": 7, "payload": {"ticket_id": "t1", "via": "whatsapp"}}
        up = upcast(old)
        self.assertEqual((up["schema_version"], up["payload"]["via"]), (8, "lynkchat"))
        self.assertEqual(old["payload"]["via"], "whatsapp", "the stored event is never rewritten")
        consent = upcast({"type": "AttendanceConsentRecorded", "schema_version": 6, "payload": {"method": "code_whatsapp"}})
        self.assertEqual(consent["payload"]["method"], "code_lynkchat")
        other = upcast({"type": "TicketIssued", "schema_version": 7, "payload": {"ticket_id": "t1", "via": "kiosk"}})
        self.assertEqual(other["payload"]["via"], "kiosk")

    def test_a_new_event_naming_whatsapp_is_refused(self):
        from contract.tools.validate_contract import Device, uuid7, uuid4
        bad = Device().emit("TicketIssued", {"ticket_id": uuid7(), "place_id": uuid4(), "section": "LAB", "code": "A2K9P2", "via": "whatsapp"})
        self.assertTrue(validate_event(bad))
        ok = Device().emit("TicketIssued", {"ticket_id": uuid7(), "place_id": uuid4(), "section": "LAB", "code": "A2K9P2", "via": "lynkchat"})
        self.assertEqual(validate_event(ok), [])


if __name__ == "__main__": unittest.main()
