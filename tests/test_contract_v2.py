"""Contract version 2 (Step 0, blueprint 42 A): any currency as integer minor units, version 1 still readable through the
upcaster, and the event names of sections 42 I, 44 and 45 registered. The published version 1 files are never edited."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT
from core import money, regions

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V1, V2 = load("event-payloads.v1.json"), load("event-payloads.v2.json")
CUR = load("currencies.v1.json")["decimals"]


class Version2(unittest.TestCase):
    def test_generated_files_match_the_generator(self):
        out = subprocess.run([sys.executable, "contract/tools/build_v2.py", "--check"], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_version_1_is_untouched_and_fully_carried_over(self):
        self.assertEqual(V1["$id"], "lynkomni/event-payloads.v1")
        self.assertEqual(len(V1["events"]), 21)
        for name, e in V1["events"].items():
            self.assertEqual(e["schema_version"], 1, name)
            self.assertIn(name, V2["events"]); self.assertEqual(V2["events"][name]["since"], "v1")
            self.assertEqual(V2["events"][name]["origins"], e["origins"], name)
        self.assertTrue(all(e["schema_version"] == 2 for e in V2["events"].values()))

    def test_money_is_minor_units_in_a_listed_currency(self):
        self.assertNotIn("rwf", V2["$defs"]); self.assertIn("money", V2["$defs"])
        self.assertEqual(set(V2["$defs"]["currency"]["enum"]), set(CUR))
        self.assertEqual(money.CURRENCIES, CUR)                       # one currency list for the code and the contract
        for code, c in regions.COUNTRIES.items():
            self.assertIn(c["currency"], CUR, f"pack {code} names a currency missing from contract/currencies.v1.json")
        self.assertEqual(money.fmt(1500, "RWF"), "RWF 1,500"); self.assertEqual(money.fmt(1500, "USD"), "USD 15.00"); self.assertEqual(money.fmt(1500, "JPY"), "JPY 1,500")

    def test_blueprint_event_names_are_registered(self):
        new = {n for n, e in V2["events"].items() if e["since"] == "v2"}
        for name in ("AgentRequestCreated", "AgentRequestConfirmed", "CommissionRecorded", "CashDifferenceFlagged",   # 42 I
                     "MessageTranslated",                                                                              # 44 E
                     "PartnerRegistered", "ConnectionUnplugged", "ScorecardComputed",                                 # 44 G
                     "TableOpened", "PayrollRunApproved", "TaxReturnAccepted", "MandateCreated", "QuoteSigned",        # 44 I
                     "FinancingOffered", "LeaseConfirmed", "DeliveryDelivered", "WarrantyIssued", "ReviewSubmitted",
                     "GroupOrderReached", "SupplierShareGranted", "CertificateIssued", "RegistrationApproved",
                     "ReportBuilt", "ScoreComputed", "InsightActionDrafted",                                          # 44 J
                     "AutomationTriggered", "AutomationUndone"):                                                      # 45 A
            self.assertIn(name, new, name)
        self.assertGreaterEqual(len(new), 100)
        # the cloud alone writes a partner's answer and every Partner Hub, LynkStat and finance event
        for name in ("AgentRequestConfirmed", "AgentRequestFailed", "CommissionRecorded", "PartnerRegistered", "ReportBuilt",
                     "PayoutConfirmed", "FinancingOffered", "MandateConfirmed", "TaxReturnAccepted"):
            self.assertEqual(V2["events"][name]["origins"], ["server"], name)
        # agent, financing and delivery requests are device facts but never queued offline (class C commands)
        reg = {c["name"]: c for c in load("command-policy-register.v2.json")["commands"]}
        for cmd in ("RequestAgentService", "RequestFinancing", "RequestDelivery"):
            self.assertEqual(reg[cmd]["class"], "C"); self.assertFalse(reg[cmd]["offline"]["allowed"])
        for cmd in ("OpenShift", "CountCash", "OpenTable", "ClockIn", "RecordCustomerCredit"):
            self.assertEqual(reg[cmd]["class"], "A"); self.assertTrue(reg[cmd]["offline"]["allowed"])

    def test_upcaster_reads_version_1_without_rewriting_it(self):
        self.assertEqual(CURRENT, 6)                                                             # version 3 (2026-11-09) adds the side, version 4 (2026-11-10) the movement milestones, version 5 (MASTER UPDATE) the card request, version 6 (NEW UPDATE 4) LynkA, LynkQ and LynkS
        v1 = {"type": "PaymentRecorded", "schema_version": 1, "payload": {"payment_id": "x", "amount": 1500}}
        up = upcast(v1)
        self.assertEqual((up["schema_version"], up["payload"]["currency"], up["payload"]["amount"]), (CURRENT, "RWF", 1500))
        self.assertEqual(v1["schema_version"], 1); self.assertNotIn("currency", v1["payload"])     # the stored event is untouched
        sale = {"type": "SaleRecorded", "schema_version": 1, "payload": {"currency": "RWF", "total": 5}}
        self.assertEqual(upcast(sale)["payload"]["currency"], "RWF")
        self.assertIs(upcast(up), up)                                                            # already current
        self.assertEqual(upcast({"type": "X", "schema_version": 9, "payload": {}})["schema_version"], 9)   # unknown: left for quarantine


if __name__ == "__main__": unittest.main()
