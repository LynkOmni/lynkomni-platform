"""LynkAssist's register, answer classes, question bank, action bank and knowledge pack (MASTER UPDATE, section 54)."""
import json, os, unittest
from core import build_sections
from identity.offline import DeviceKey
from services import assist_register as ar
from services import billing
from tools.assist import knowledge_pack as kp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = ar.REG
AUTO = json.load(open(os.path.join(ROOT, "catalog", "automations.v1.json"), encoding="utf-8"))
BANK = json.load(open(os.path.join(ROOT, "tests", "assist_bank", "questions.v1.json"), encoding="utf-8"))["questions"]


class TestRegister(unittest.TestCase):
    def test_every_action_is_complete(self):
        ids = [a["id"] for a in REG["actions"]]
        self.assertEqual(len(ids), len(set(ids)))
        for a in REG["actions"]:
            self.assertIn(a["class"], REG["classes"], a["id"])
            self.assertTrue(a["roles"], a["id"])
            self.assertGreater(a["limits"]["per_day"], 0, a["id"])
            self.assertIn(a["build_section"], build_sections.ORDER, a["id"])
            self.assertIn(a["status"], ("built", "planned"), a["id"])

    def test_classes_are_the_automation_levels(self):
        self.assertEqual(ar.AUTOMATION_LEVEL, {"A": "auto", "B": "draft", "C": "draft", "D": "inform"})
        self.assertTrue(set(ar.AUTOMATION_LEVEL.values()) <= set(AUTO["levels"]))
        self.assertTrue(set(AUTO["sensitive"]) <= set(REG["never_auto"]), "every sensitive area of the automation register is covered")

    def test_sensitive_work_is_never_automatic_and_money_is_only_handed_over(self):
        for a in REG["actions"]:
            if set(a["touches"]) & set(REG["never_auto"]):
                self.assertNotEqual(a["class"], "A", a["id"])
            if set(a["touches"]) & set(REG["only_hand_over"]):
                self.assertEqual(a["class"], "D", a["id"])

    def test_solving_alone_only_for_harmless_things(self):
        for a in REG["actions"]:
            if a["class"] == "A":
                self.assertTrue(set(a["touches"]) <= {"device", "message", "settings"}, a["id"])

    def test_every_topic_has_a_class_and_role_topics_name_roles(self):
        for t, v in REG["topics"].items():
            self.assertIn(str(v["class"]), REG["answer_classes"], t)
            if v["class"] == 4:
                self.assertTrue(v.get("roles"), t)


class TestDecisions(unittest.TestCase):
    def test_an_action_outside_the_register_role_or_limits_never_runs(self):
        self.assertEqual(ar.decide("send_all_money_to_me", "owner")["needs"], "refused")
        self.assertEqual(ar.decide("correct_price", "cashier")["needs"], "refused", "a cashier may not change prices")
        self.assertEqual(ar.decide("rerun_sync", "owner", switched_off={"rerun_sync"})["needs"], "refused")
        self.assertEqual(ar.decide("rerun_sync", "owner", switched_off={"devices"})["needs"], "refused")
        self.assertEqual(ar.decide("rerun_sync", "owner", country="CM", switched_off={"country:CM"})["needs"], "refused")
        self.assertTrue(ar.decide("rerun_sync", "owner", country="KE", switched_off={"country:CM"})["run"])
        self.assertEqual(ar.decide("rerun_sync", "owner", done_today=50)["needs"], "confirm", "past its limit an action moves up")
        self.assertEqual(ar.decide("void_sale_within_rules", "manager", amount_minor=9_000_000, confirmed=True)["needs"], "fresh_check")

    def test_the_action_bank_every_class_behaves(self):
        for a in REG["actions"]:
            role = a["roles"][0]
            first = ar.decide(a["id"], role)
            if a["class"] == "A":
                self.assertTrue(first["run"], a["id"])
            elif a["class"] == "B":
                self.assertEqual(first["needs"], "confirm", a["id"])
                self.assertTrue(ar.decide(a["id"], role, confirmed=True)["run"], a["id"])
            elif a["class"] == "C":
                self.assertEqual(first["needs"], "fresh_check", a["id"])
                self.assertEqual(ar.decide(a["id"], role, fresh_check=True)["needs"], "confirm", a["id"])
                self.assertTrue(ar.decide(a["id"], role, fresh_check=True, confirmed=True)["run"], a["id"])
            else:
                for extra in ({}, {"confirmed": True, "fresh_check": True}):
                    self.assertEqual(ar.decide(a["id"], role, **extra)["needs"], "hand_over", a["id"])

    def test_owner_controls_and_standing_permissions(self):
        self.assertEqual(ar.decide("correct_stock_quantity", "stock_staff", ask_owner_first={"correct_stock_quantity"})["needs"], "ask_owner")
        self.assertEqual(ar.decide("correct_stock_quantity", "owner", ask_owner_first={"correct_stock_quantity"})["needs"], "confirm")
        self.assertTrue(ar.decide("correct_stock_quantity", "stock_staff", standing={"correct_stock_quantity"})["run"])
        self.assertEqual(ar.decide("enrol_device", "owner", standing={"enrol_device"})["needs"], "fresh_check", "standing never skips a check")

    def test_the_question_bank(self):
        topics = {q["topic"] for q in BANK}
        self.assertTrue(set(REG["topics"]) - {"how_to", "status_word", "plan_features", "my_sale_state", "my_plan", "payout_last_digits",
                                               "sign_in_history", "outlet_sales", "customer_history"} <= topics)
        for q in BANK:
            got = ar.answer(q["topic"], **q["asker"])
            self.assertEqual(got["answer"], q["answer"], f"{q['q']} -> {got}")

    def test_class_five_is_never_given_whoever_asks(self):
        for t, v in REG["topics"].items():
            if v["class"] == 5:
                self.assertFalse(ar.answer(t, signed_in=True, fresh_check=True, role="owner")["answer"], t)


class TestKnowledgePack(unittest.TestCase):
    def test_built_from_billing_signed_and_refused_when_altered(self):
        pack = kp.build("2026-11-10")
        stat = next(e for e in pack["entries"] if e["id"] == "price-lynkstat")
        _full, name, tiers, prices, _w, _s = billing.FAMILIES["lynkstat"]
        for p in prices:
            self.assertIn(f"${p}", stat["a"])
        key = DeviceKey()
        signed = kp.sign(pack, key)
        self.assertTrue(kp.verify(signed, key.public))
        fake = dict(signed, entries=signed["entries"][:-1] + [dict(signed["entries"][-1], a="pay me directly")])
        self.assertFalse(kp.verify(fake, key.public))
        self.assertFalse(kp.verify(signed, DeviceKey().public), "a pack signed by another key is refused")

    def test_offline_search_finds_the_answer(self):
        pack = kp.build("2026-11-10")
        self.assertEqual(kp.lookup(pack, "How much is LynkStat?")[0]["id"], "price-lynkstat")
        self.assertEqual(kp.lookup(pack, "what does sent mean")[0]["id"], "state-sent")
        self.assertEqual(len([e for e in pack["entries"] if e["topic"] == "status_word"]), 5)


if __name__ == "__main__":
    unittest.main()
