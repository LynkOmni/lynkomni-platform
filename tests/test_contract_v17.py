"""Contract version 17 (BETTING UPDATE, owner 2026-11-24, master blueprint section 86): version 16 plus LynkBet's events. Nothing older
changes; the counter only asks and the licensed operator's answers are cloud only; placing a bet may be queued offline (class B) only as a
slip, while payout locks, referrals and cancellations are online only (class C); no customer name, contact, ID number or photo is ever
in an event; the Emulator Panel's events name every emulator of the register."""
import json, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract.upcast import upcast, CURRENT
from contract.tools.validate_contract import validate_event, uuid7, ts, fake_sig, MERCHANT, Device
from core import emulators as E

def load(name): return json.loads((ROOT / "contract" / name).read_text())
V16, V17 = load("event-payloads.v16.json"), load("event-payloads.v17.json")
REG16, REG17 = load("command-policy-register.v16.json"), load("command-policy-register.v17.json")
DEVICE = {"BetRequested", "BetTicketChecked", "BetPayoutLockAsked", "BetPaidOut", "BetReferred", "BetCancelAsked", "BetDisputeOpened"}
NEW = DEVICE | {"BetConfirmed", "BetFailed", "BetPayoutLocked", "BetPayoutLockFailed", "BetReferralAnswered", "BetCancelled", "BetDisputeAnswered",
                "BetSettlementRecorded", "BetFlagRaised", "BetShopStatusChanged"}


class ContractV17(unittest.TestCase):
    def test_built_from_v16_and_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "contract" / "tools" / "build_v17.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreaterEqual(CURRENT, 17)

    def test_only_new_events_and_who_may_write_them(self):
        self.assertEqual(set(V17["events"]) - set(V16["events"]), NEW)
        for name, e in V16["events"].items():
            if "emulator" not in e["payload"]["properties"]:
                self.assertEqual((V17["events"][name]["payload"], V17["events"][name]["origins"]), (e["payload"], e["origins"]), name)
        for name in NEW - DEVICE:
            self.assertEqual(V17["events"][name]["origins"], ["server"], name)
        for name in DEVICE:
            self.assertEqual(V17["events"][name]["origins"], ["device"], name)

    def test_payouts_referrals_and_cancelling_are_online_only_and_bets_are_never_on_credit(self):
        added = {c["name"]: c for c in REG17["commands"] if c not in REG16["commands"]}
        self.assertEqual(sorted(e for c in added.values() for e in c["emits"]), sorted(DEVICE))
        for n in ("AskPayoutLock", "ReferBigWin", "AskCancelBet"):
            self.assertEqual((added[n]["class"], added[n]["offline"]["allowed"]), ("C", False), n)
        self.assertEqual(added["PlaceBet"]["class"], "B")
        self.assertNotIn("credit", V17["events"]["BetRequested"]["payload"]["properties"]["method"]["enum"])

    def test_the_emulator_list_is_the_register(self):
        self.assertEqual(V17["events"]["EmulatorConnected"]["payload"]["properties"]["emulator"]["enum"], list(E.EMULATORS))

    def test_no_name_contact_id_number_photo_or_position(self):
        fields = {f.lower() for n in NEW for f in V17["events"][n]["payload"]["properties"]}
        for word in ("name", "phone", "email", "photo", "image", "address", "position", "birth", "passport"):
            self.assertFalse([f for f in fields if word in f.split("_")], word)

    def test_a_version_16_event_reads_as_version_17_unchanged(self):
        old = {"type": "GiftCardSold", "schema_version": 16, "payload": {"card_id": uuid7(), "amount": 5000, "currency": "RWF", "method": "cash", "top_up": False}}
        self.assertEqual(upcast(old)["schema_version"], CURRENT)

    def test_a_counter_asks_and_only_the_cloud_answers(self):
        asked = Device().emit("BetRequested", {"request_id": uuid7(), "operator_id": uuid7(), "kind": "sports", "selections": 2, "stake": 1000,
                                               "currency": "RWF", "method": "cash", "queued_offline": False})
        self.assertEqual(validate_event(asked), [], validate_event(asked))
        ok = {"event_id": uuid7(), "origin": "server", "merchant_id": MERCHANT, "type": "BetConfirmed", "schema_version": 17,
              "created_at_server": ts(), "server_cursor": 1, "server_signature": fake_sig(),
              "payload": {"request_id": uuid7(), "ticket_ref": "SAMPLE48210001", "possible_win": 3977, "currency": "RWF"}}
        self.assertEqual(validate_event(ok), [], validate_event(ok))
        for k, v in (("possible_win", 39.77), ("customer_name", "x")):
            bad = json.loads(json.dumps(ok)); bad["payload"][k] = v
            self.assertTrue(validate_event(bad), k)
        forged = Device().emit("BetConfirmed", ok["payload"])
        self.assertTrue(validate_event(forged), "a device can never write the operator's answer")


if __name__ == "__main__":
    unittest.main()
