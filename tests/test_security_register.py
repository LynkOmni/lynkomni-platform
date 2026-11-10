"""The security register (MASTER UPDATE, master blueprint section 59): every protection is listed with what it protects, the
threat, where it is enforced, the test that proves it and its build section. A locked build section may not hold a control
without a passing test, except while an update for it is still being built."""
import json, os, sqlite3, unittest
from core import build_sections
from core.events import EventStore
from tools.security import scan_secrets

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = json.load(open(os.path.join(ROOT, "catalog", "security.v1.json"), encoding="utf-8"))
SHOW = json.load(open(os.path.join(ROOT, "web", "showcase", "showcase.v1.json"), encoding="utf-8"))
LOCKED = {s["n"] for s in SHOW["sections"] if s.get("status") == "locked"}


class TestSecurityRegister(unittest.TestCase):
    def test_every_control_is_complete(self):
        ids = [c["id"] for c in REG["controls"]]
        self.assertEqual(len(ids), len(set(ids)), "duplicate control ids")
        self.assertEqual(len(REG["principles"]), 7)
        for c in REG["controls"]:
            self.assertIn(c["asset"], REG["assets"], c["id"])
            self.assertGreater(len(c["threat"]), 15, c["id"])
            self.assertIn(c["build_section"], build_sections.ORDER, c["id"])
            self.assertIn(c["status"], ("built", "planned"), c["id"])

    def test_built_controls_point_at_real_code_and_a_real_test(self):
        for c in REG["controls"]:
            if c["status"] != "built":
                continue
            self.assertTrue(c["enforced_in"], c["id"])
            for f in c["enforced_in"]:
                self.assertTrue(os.path.exists(os.path.join(ROOT, f)), f"{c['id']}: {f} does not exist")
            path, _, name = c["test"].partition("::")
            self.assertTrue(name, f"{c['id']}: a built control names its test function")
            src = open(os.path.join(ROOT, path), encoding="utf-8").read()
            self.assertIn(f"def {name}(", src, f"{c['id']}: {c['test']} not found")

    def test_a_locked_section_never_holds_an_untested_control(self):
        for c in REG["controls"]:
            if c["status"] == "built" or c["build_section"] not in LOCKED:
                continue
            self.assertIn(c.get("update"), REG["open_updates"],
                          f"{c['id']}: section {c['build_section']} is locked, so this control needs its test now")

    def test_planned_controls_in_later_sections_name_that_section(self):
        for c in REG["controls"]:
            if c["status"] == "planned" and c["build_section"] not in LOCKED:
                self.assertTrue(build_sections.after(c["build_section"], 3), c["id"])

    def test_every_asset_is_protected_by_at_least_one_control(self):
        self.assertEqual(set(REG["assets"]), {c["asset"] for c in REG["controls"]})

    def test_event_log_chain_detects_any_change(self):
        s = EventStore()
        for i in range(5):
            s.append("m1", "d1", "SaleRecorded", {"n": i}, id_=f"e{i}")
        self.assertEqual(s.verify(), {"ok": True, "events": 5})
        head = s.head()
        self.assertFalse(s.append("m1", "d1", "SaleRecorded", {"n": 0}, id_="e0"), "a retry is still refused")
        self.assertEqual(s.head(), head)
        s.db.execute("update events set payload=? where id=?", (json.dumps({"n": 99}), "e2")); s.db.commit()
        self.assertEqual(s.verify(), {"ok": False, "broken_at": 3})
        t = EventStore()
        for i in range(3):
            t.append("m1", "d1", "SaleRecorded", {"n": i}, id_=f"e{i}")
        t.db.execute("delete from events where id='e1'"); t.db.commit()
        self.assertFalse(t.verify()["ok"], "a removed event breaks the chain")

    def test_an_old_log_without_the_chain_is_sealed_when_opened(self):
        path = os.path.join(ROOT, "tests", "_old_events.sqlite")
        try:
            db = sqlite3.connect(path)
            db.execute("create table events(seq integer primary key autoincrement, id text unique, merchant text, device text, type text, ts text, payload text)")
            db.execute("insert into events(id,merchant,device,type,ts,payload) values('a','m','d','SaleRecorded','2026-01-01T00:00:00Z','{}')")
            db.commit(); db.close()
            s = EventStore(path)
            self.assertEqual(s.verify(), {"ok": True, "events": 1})
            s.append("m", "d", "SaleRecorded", {"n": 1}, id_="b")
            self.assertEqual(s.verify(), {"ok": True, "events": 2})
            s.db.close()
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_secret_scan_finds_planted_keys_and_the_repository_is_clean(self):
        planted = "-----BEGIN " + "PRIVATE KEY-----\n" + "AKIA" + "ABCDEFGHIJKLMNOP\n" + "sk_" + "live_" + "a" * 24
        kinds = {h["kind"] for h in scan_secrets.scan_text(planted)}
        self.assertEqual(kinds, {"private key", "cloud access key", "live payment key"})
        self.assertEqual(scan_secrets.scan_text("AKIA" + "ABCDEFGHIJKLMNOP  # " + scan_secrets.ALLOW_MARK), [])
        self.assertEqual(scan_secrets.scan(), [], "the repository holds no secrets")

    def test_the_scan_runs_in_ci(self):
        ci = open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8").read()
        self.assertIn("tools/security/scan_secrets.py", ci)


if __name__ == "__main__":
    unittest.main()
