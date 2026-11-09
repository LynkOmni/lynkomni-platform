"""Office services for everyone (owner request 9 November 2026): a person, a company or an organisation runs its internal affairs
with LynkOmni's accounting, invoicing, contacts, analytics and the rest (catalog/workspaces.v1.json, core/workspaces.py)."""
import json, os, unittest, uuid

from core import accounts, workspaces as W
from services import billing

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Register(unittest.TestCase):
    def test_the_register_is_sound(self):
        self.assertEqual(W.validate(), [])
        self.assertEqual(set(W.ENTITIES), {"person", "company", "organisation"})
        for f in W.OFFICE_FAMILIES: self.assertIn(f, billing.FAMILIES)
        self.assertEqual(set(W.REGISTER["entities"]["organisation"]["kinds"]), {"nonprofit", "school", "faith", "association", "cooperative", "public_body"})

    def test_the_entity_never_changes_a_price_or_a_family(self):
        """One product for every size: no family, tier or price is tied to an entity."""
        blob = json.dumps(billing.FAMILIES) + json.dumps(billing.FEATURES)
        for e in W.ENTITIES: self.assertNotIn(f'"{e}"', blob)

    def test_categories_post_to_the_global_chart(self):
        self.assertEqual(W.account_for("organisation", "donations"), "4200")
        self.assertEqual(accounts.ACCOUNTS[W.account_for("person", "rent")]["type"], "expense")
        with self.assertRaises(ValueError): W.account_for("person", "nothing")
        self.assertEqual(W.funds("organisation"), ("unrestricted", "restricted"))

    def test_words_and_tabs_follow_the_entity(self):
        self.assertEqual(W.word("person", "tab_customers"), "tab_contacts")
        self.assertEqual(W.word("organisation", "tab_customers"), "tab_members")
        self.assertEqual(W.word("company", "tab_customers"), "tab_customers")
        self.assertEqual(W.tabs("person", "no_till", ("x",)), ("home", "books", "invoices", "customers", "business"))
        self.assertEqual(W.tabs("organisation", "shop", ("home", "sell")), ("home", "sell"))      # an organisation that also sells keeps its till
        with self.assertRaises(ValueError): W.check("planet")
        with self.assertRaises(ValueError): W.check("person", "school")

    def test_every_workspace_word_is_translated(self):
        en = json.load(open(os.path.join(ROOT, "web", "emulators", "merchant-phone", "strings.en.json"), encoding="utf-8"))
        for e, v in W.REGISTER["entities"].items():
            for k in v["words"].values(): self.assertIn(k, en, k)
            for k in v["kinds"]: self.assertIn(f"kind_{k}", en, k)
            for side in ("income", "expense"):
                for c in v["categories"][side]: self.assertIn(f"cat_{c['id']}", en, c["id"])
            self.assertIn(f"entity_{e}", en)


class OnThePlatform(unittest.TestCase):
    def test_a_person_and_an_organisation_get_office_workspaces(self):
        os.environ.pop("LYNK_MODE", None)
        from services.platform import Platform
        p = Platform(); a, b = str(uuid.uuid4()), str(uuid.uuid4())
        p.business.create(a, "Grace's household", "no_till", "XX", "USD", entity="person", kind="household")
        p.business.create(b, "Hope Foundation", "no_till", "XX", "USD", entity="organisation", kind="nonprofit")
        self.assertEqual(p.business.tabs(a), ("home", "books", "invoices", "customers", "business"))
        self.assertEqual(p.business.word(b, "tab_customers"), "tab_members")
        self.assertEqual(p.business.entity(b), ("organisation", "nonprofit"))
        created = [e["payload"] for e in p.c.store.of(b, "BusinessCreated")]
        self.assertEqual((created[0]["entity"], created[0]["kind"]), ("organisation", "nonprofit"))
        c = str(uuid.uuid4()); p.business.create(c, "Shop", "shop", "XX", "USD")
        self.assertEqual(p.business.entity(c), ("company", "business"))
        with self.assertRaises(ValueError): p.business.create(str(uuid.uuid4()), "X", "no_till", "XX", "USD", entity="person", kind="school")


if __name__ == "__main__":
    unittest.main()
