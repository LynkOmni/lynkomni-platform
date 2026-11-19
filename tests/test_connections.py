"""The connections register (catalog/connections.v1.json, CONNECT UPDATE 71.3): every link joins two real services, names
real contract events or the events its build section adds, and every journey of 71.2 is made of links (section 4 step A)."""
import glob, json, os, re, unittest
from core import build_sections as b, connections as C
from services import billing

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDER = [str(n) for n in b.ORDER]
JOURNEYS = ["sale_to_books", "quote_to_cash", "hire_to_work", "enrol_to_class", "lease_to_rent", "booking_to_visit",
            "low_stock_to_supplier", "meeting_to_action", "document_to_record", "problem_to_fix"]     # blueprint 71.2


def contract_events():
    latest = max(glob.glob(os.path.join(ROOT, "contract", "event-payloads.v*.json")), key=lambda p: int(re.search(r"v(\d+)", p).group(1)))
    d = json.load(open(latest, encoding="utf-8"))
    ev = d.get("events", d)
    return set(ev) if isinstance(ev, dict) else {e["type"] for e in ev}


class Connections(unittest.TestCase):
    def test_every_link_joins_two_real_services(self):
        known = set(billing.FAMILIES) | set(C.PLATFORM)
        for l in C.LINKS.values():
            self.assertIn(l["from"], known, l["id"]); self.assertIn(l["to"], known, l["id"])
            self.assertNotEqual(l["from"], l["to"], l["id"])
            self.assertIn(l["consent"], ("none", "merchant", "person"), l["id"])
            self.assertIn(str(l["build_section"]), ORDER, l["id"])
            self.assertTrue(l["what"].strip(), l["id"])

    def test_events_are_in_the_contract_or_added_by_their_section(self):
        have = contract_events()
        building = next(str(s["n"]) for s in b.SECTIONS if s.get("status") != "locked")
        for l in C.LINKS.values():
            for e in l["events"]:
                self.assertIn(e, have, f"{l['id']}: {e} is not in the contract")
            for e in l["planned_events"]:
                self.assertNotIn(e, have, f"{l['id']}: {e} is already in the contract, list it under events")
                self.assertTrue(re.match(r"^[A-Z][A-Za-z]+$", e), e)
            if b.status(l["build_section"]) == "locked":
                self.assertEqual(l["planned_events"], [], f"{l['id']}: a locked section's link has all its events")
            if l["planned_events"]:
                self.assertGreaterEqual(ORDER.index(str(l["build_section"])), ORDER.index(building), l["id"])

    def test_the_ten_journeys_are_made_of_links_built_by_their_section(self):
        self.assertEqual(sorted(C.JOURNEYS), sorted(JOURNEYS))
        for j in C.JOURNEYS.values():
            self.assertGreaterEqual(len(j["links"]), 2, j["id"])
            for l in C.journey(j["id"]):
                self.assertLessEqual(ORDER.index(str(l["build_section"])), ORDER.index(str(j["build_section"])),
                                     f"{j['id']} is finished in section {j['build_section']} but needs {l['id']} from {l['build_section']}")

    def test_every_service_is_connected(self):
        """Everything connected (the quality bar): every billing family and platform service has at least one link."""
        for s in list(billing.FAMILIES) + list(C.PLATFORM):
            self.assertTrue(C.links_for(s), f"{s} has no link")

    def test_ids_are_unique_and_the_map_has_no_doubles(self):
        ids = [l["id"] for l in json.load(open(os.path.join(ROOT, "catalog", "connections.v1.json")))["links"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(C.edges()), len(set(C.edges())))


if __name__ == "__main__":
    unittest.main()
