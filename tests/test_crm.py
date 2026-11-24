"""LynkCRM's rules (OFFICE UPDATE, master blueprint 66.4; section 4 step D3): catalog/crm.v1.json read through core/crm.py and
ts/src/crm.ts with shared vectors, and the 66.7 tier table. Deal stages are the contract's five; lead scores are labelled
suggestions; a hidden field never reaches a role's screens; sensitive records only where the law allows; consent per channel."""
import json, os, re, subprocess, sys, unittest

from core import crm as C

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Crm(unittest.TestCase):
    def test_vectors_and_the_typescript_register_are_current(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "crm_vectors.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_every_kind_of_entity_has_its_record_kinds(self):
        for kind in json.load(open(os.path.join(ROOT, "catalog", "workspaces.v1.json"), encoding="utf-8"))["entities"].values():
            for k in kind["kinds"]:
                self.assertTrue(C.kinds_for(k), k)

    def test_the_stages_are_the_contracts_five(self):
        v11 = json.load(open(os.path.join(ROOT, "contract", "event-payloads.v11.json"), encoding="utf-8"))
        self.assertEqual(C.CRM["pipelines"]["stages"], v11["events"]["DealStageChanged"]["payload"]["properties"]["stage"]["enum"])
        self.assertFalse(C.stage_move("won", "lost"), "a won deal is final")
        self.assertFalse(C.close_ok("lost", None), "a lost deal names its reason")

    def test_lead_scores_are_suggestions_only(self):
        self.assertEqual(C.lead_score(["booked_meeting", "bought_before", "replied", "opened_quote"]), {"score": 100, "suggestion": True})
        self.assertEqual(C.lead_score(["no_answer_30_days"])["score"], 0)

    def test_access_and_hidden_fields(self):
        self.assertFalse(C.may_see({"id": "u4", "role": "staff", "team": "t2"}, {"owner": "u3", "team": "t1"}))
        self.assertTrue(C.may_see({"id": "u1", "role": "owner"}, {"owner": "u3", "team": "t1"}, "own"))
        self.assertNotIn("salary", C.visible_fields([{"id": "salary", "hidden_from": ["staff"]}], "staff"))

    def test_sensitive_records_and_consent(self):
        unknown = {"office": {"crm": {"sensitive_allowed": {"health": None}}}}
        self.assertFalse(C.sensitive_allowed("health", "business", unknown))
        self.assertTrue(C.sensitive_allowed("children", "school", unknown))
        self.assertFalse(C.consent_ok([{"channel": "sms", "basis": "contract"}], "sms", marketing=True), "marketing needs 'asked'")
        self.assertFalse(C.consent_ok([{"channel": "email", "basis": "asked"}, {"channel": "email", "basis": "asked", "withdrawn": True}], "email"))
        for n in sorted(os.listdir(os.path.join(ROOT, "contract", "country-packs")))[:5]:
            p = json.load(open(os.path.join(ROOT, "contract", "country-packs", n), encoding="utf-8"))
            self.assertIn("crm", p["office"], n)

    def test_duplicates_merge_without_losing_anything(self):
        v = json.load(open(os.path.join(ROOT, "contract", "vectors", "crm.v1.json"), encoding="utf-8"))
        m = v["merge"][0]
        self.assertEqual(m["id"], "p3", "the oldest record is kept")
        self.assertEqual(m["activities"], ["s0", "s1", "s2"], "every activity is kept")
        self.assertEqual(C.CRM["duplicates"]["undo_days"], 30)

    def test_the_tier_table_of_66_7_is_in_billing(self):
        from services import billing
        F = billing.FEATURES["lynkcrm"]
        for k in ("consent_records", "data_requests", "offline", "import_records", "duplicate_merge", "change_history"):
            self.assertTrue(F[0][k], f"{k} is on every tier, Free included")
        self.assertTrue(F[1]["saved_segments"] and F[2]["cases"] and F[3]["lead_scores"])
        self.assertEqual([C.field_limit(t) for t in ("free", "plus", "pro", "max")], [F[0]["own_fields"], F[1]["own_fields"], F[2]["own_fields"], F[3]["own_fields"]])



class CrmService(unittest.TestCase):
    """services/crm.py: names and contact details only in the vault, never in an event; duplicates merge and undo; access and
    hidden fields; deals on the five stages; cases late when past their promise."""
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"
        from services.platform import Platform
        self.p = Platform(); self.p.register("m1", "RW"); self.c = self.p.crm

    def test_contact_details_never_reach_an_event(self):
        rid = self.c.create("m1", "u1", "customer", name="Amina Uwase", email="amina@shop.rw", phone="+250 788 000 111")
        self.assertTrue(rid.startswith("LOCST-"))
        events = list(self.p.c.store.of("m1", "crm.record_created"))
        text = re.sub(r"LO[A-Z]+-\d{4}-\d{4}-\d{4}", "", str(events))   # a random public id may hold any digits by chance
        for v in ("Amina", "amina@shop.rw", "788 000 111", "788000111"):
            self.assertNotIn(v, text)
        self.assertEqual(self.p.vault.get(self.c.recs[rid]["email_ref"]), "amina@shop.rw")

    def test_duplicates_merge_keep_the_oldest_and_can_be_undone(self):
        a = self.c.create("m1", "u1", "customer", name="Amina Uwase", email="Amina@Shop.rw ")
        b = self.c.create("m1", "u1", "customer", name="AMÍNA  uwase", email="amina@shop.rw")
        self.c.create("m1", "u1", "customer", name="Jean")
        self.assertEqual(self.c.duplicates("m1"), [[a, b]])
        self.assertEqual(self.c.merge("m1", [a, b], "u1")["id"], a)
        self.assertEqual(self.c.duplicates("m1"), [])
        self.assertTrue(self.c.undo_merge("m1", a))
        self.assertEqual(self.c.duplicates("m1"), [[a, b]])

    def test_fields_limits_access_and_hidden_fields(self):
        with self.assertRaises(PermissionError):
            self.c.define_field("m1", "size", "choice")                                 # Free: no own fields
        self.p.billing.set_plan("m1", "lynkcrm", "max")
        self.c.define_field("m1", "salary", "money", hidden_from=["staff"])
        self.c.define_field("m1", "city", "text", required=True)
        with self.assertRaises(ValueError):
            self.c.create("m1", "u1", "customer")                                        # a required field
        rid = self.c.create("m1", "u1", "customer", fields={"city": "Kigali", "salary": 500000}, team="t1")
        self.assertNotIn("salary", self.c.view("m1", {"id": "u3", "role": "staff", "team": "t1"}, rid)["fields"])
        with self.assertRaises(PermissionError):
            self.c.view("m1", {"id": "u4", "role": "staff", "team": "t2"}, rid)
        with self.assertRaises(PermissionError):
            self.c.create("m1", "u1", "student")                                          # a school's record kind, not a business's

    def test_deals_cases_consent_and_requests(self):
        self.p.billing.set_plan("m1", "lynkcrm", "pro")
        rid = self.c.create("m1", "u1", "customer")
        d = self.c.create_deal("m1", rid, 100000)
        self.c.move_deal("m1", d, "proposal")
        self.assertEqual(self.c.forecast("m1")["total"], 60000)
        with self.assertRaises(ValueError):
            self.c.move_deal("m1", d, "won")                                              # names its reason
        self.c.move_deal("m1", d, "won", "price")
        with self.assertRaises(ValueError):
            self.c.move_deal("m1", d, "lost", "price")                                    # a won deal is final
        case = self.c.open_case("m1", rid, "high", hour=100)
        self.assertEqual(case["due_hour"], 108)
        self.assertEqual(self.c.late_cases("m1", 109), [case["case"]])
        self.c.consent("m1", rid, "sms", True, "contract")
        self.assertFalse(self.c.may_message("m1", rid, "sms", marketing=True))
        self.assertEqual(self.c.data_request("m1", rid, "delete", "2026-01-20")["due"], "2026-02-19")

if __name__ == "__main__":
    unittest.main()
