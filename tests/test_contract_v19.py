"""Contract version 19 (SIX SERVICES UPDATE, master blueprint section 69, built in section 4B): version 18 plus the events of LynkHR,
LynkProject and LynkFiles' approval routes and document requests. Nothing older changes; only the offline steps of blueprint 69.9 may
come from a device; pay, payroll, billing and decisions are cloud only; no event carries a person's details or anyone's words."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import CURRENT, upcast


def load(name): return json.loads((ROOT / "contract" / name).read_text())
V18, V19 = load("event-payloads.v18.json"), load("event-payloads.v19.json")
REG18, REG19 = load("command-policy-register.v18.json"), load("command-policy-register.v19.json")
NEW = set(V19["events"]) - set(V18["events"])
DEVICE = {"StaffChecklistStepDone", "LeaveRequested", "LeaveAnswered", "LeaveCancelled", "ReviewAnswered", "HrCaseOpened", "ProjectCreated", "TaskCreated",
          "TaskStateChanged", "TaskWaitAdded", "MilestoneReached", "TimeLogged", "TimeSheetAnswered", "ChangeRequestRaised"}
NEVER = ("name", "email", "phone", "contact", "address", "bank", "health", "family", "union", "words", "text", "title", "notes", "content", "position", "salary")


class ContractV19(unittest.TestCase):
    def test_built_from_v18_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v19.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreaterEqual(CURRENT, 19)

    def test_nothing_older_changes(self):
        grows = {"ConversationCardSent": "card", "TrackingStepMarked": "kind"}     # their lists only grow, with 4B's cards and tracking kinds
        for name, e in V18["events"].items():
            a, b = json.loads(json.dumps(V19["events"][name]["payload"])), json.loads(json.dumps(e["payload"]))
            if name in grows:
                new, old = a["properties"][grows[name]]["enum"], b["properties"][grows[name]]["enum"]
                self.assertEqual(new[: len(old)], old, name)
                a["properties"][grows[name]]["enum"] = old
            self.assertEqual((a, V19["events"][name]["origins"]), (b, e["origins"]), name)
        self.assertEqual(len(NEW), 29)

    def test_only_the_offline_steps_come_from_a_device(self):
        self.assertEqual({n for n in NEW if "device" in V19["events"][n]["origins"]}, DEVICE)
        for n in ("PayChangeProposed", "PayChangeApproved", "PayrollFiguresSent", "ProjectTimeBilled", "ProjectCostRecorded", "ChangeRequestDecided", "HrCaseStepMoved"):
            self.assertEqual(V19["events"][n]["origins"], ["server"], n)
        added = [c for c in REG19["commands"] if c not in REG18["commands"]]
        self.assertEqual({e for c in added for e in c["emits"]}, DEVICE)
        self.assertTrue(all(c["offline"]["allowed"] and c["class"] == "A" for c in added))

    def test_no_event_carries_a_persons_details_or_words(self):
        for n in NEW:
            for field in V19["events"][n]["payload"]["properties"]:
                self.assertFalse(any(w in field for w in NEVER), f"{n}.{field}")

    def test_the_newest_version_has_every_card_and_tracking_kind(self):
        cards = set(json.loads((ROOT / "catalog" / "chat.v1.json").read_text())["cards"]["kinds"])
        kinds = {k["id"] for k in json.loads((ROOT / "catalog" / "tracking.v1.json").read_text())["kinds"]}
        self.assertEqual(set(V19["events"]["ConversationCardSent"]["payload"]["properties"]["card"]["enum"]), cards)
        self.assertEqual(set(V19["events"]["TrackingStepMarked"]["payload"]["properties"]["kind"]["enum"]), kinds)

    def test_money_is_whole_numbers(self):
        for n in NEW:
            for field, sch in V19["events"][n]["payload"]["properties"].items():
                if field in ("amount", "gross_total", "cost_change"):
                    self.assertEqual(sch.get("type", "integer"), "integer", f"{n}.{field}")

    def test_a_version_18_event_reads_as_version_19_unchanged(self):
        ev = {"schema_version": 18, "type": "TrackingStepMarked", "payload": {"kind": "order", "record": "x", "extra_step": "qc"}}
        up = upcast(dict(ev))
        self.assertEqual((up["schema_version"], up["payload"]), (CURRENT, ev["payload"]))


if __name__ == "__main__":
    unittest.main()
