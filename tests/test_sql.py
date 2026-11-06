import os, sqlite3, unittest
import pathlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class T(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:"); self.db.executescript(pathlib.Path(os.path.join(ROOT, "sql", "schema.sqlite.sql")).read_text())
    def bad(self, sql, *a):
        with self.assertRaises(sqlite3.DatabaseError): self.db.execute(sql, a)
    def test_public_ids_are_unique_permanent_and_well_formed(self):
        self.db.execute("insert into public_ids values('LOID-4827-1936-5048','ID','p1','assigned',null,1)")
        self.bad("insert into public_ids values('LOID-4827-1936-5048','ID','p2','assigned',null,1)")          # duplicate
        self.bad("insert into public_ids values('LOID-4827-1936-5049','ID','p1','assigned',null,1)")          # one internal record, one ID per type
        self.bad("insert into public_ids values('ID-4827-1936-5050','ID','p3','assigned',null,1)")            # missing LO namespace
        self.bad("insert into public_ids values('LOID-4827-1936-5051','ID','p4','banana',null,1)")            # unknown status
        self.bad("delete from public_ids where public_id='LOID-4827-1936-5048'")                              # never deleted
        self.bad("update public_ids set public_id='LOID-0000-0000-0000' where public_id='LOID-4827-1936-5048'")
        self.db.execute("update public_ids set status='retired' where public_id='LOID-4827-1936-5048'")      # retirement is the only way out
    def _org(self):
        for pid, kind in (("LOID-1111-1111-1118", "p"), ("LOID-2222-2222-2226", "p"), ("LOOID-3333-3333-3330", "o")): 
            self.db.execute("insert into public_ids values(?,?,?, 'assigned', null, 1)", (pid, "OID" if "LOOID" in pid else "ID", pid))
        self.db.execute("insert into persons values('a','LOID-1111-1111-1118','active',1)"); self.db.execute("insert into persons values('b','LOID-2222-2222-2226','active',1)")
        self.db.execute("insert into organizations values('o','LOOID-3333-3333-3330','shop','active',1)")
    def test_last_owner_cannot_be_removed_and_roles_are_checked(self):
        self._org(); self.db.execute("insert into memberships values('m1','a','o','owner','active')"); self.db.execute("insert into memberships values('m2','b','o','cashier','active')")
        self.bad("update memberships set status='removed' where member_id='m1'"); self.bad("update memberships set role='manager' where member_id='m1'"); self.bad("delete from memberships where member_id='m1'")
        self.bad("insert into memberships values('m3','b','o','superuser','active')")                          # only the contract roles
        self.bad("insert into memberships values('m4','b','o','manager','active')")                           # one active membership per person per organization
        self.db.execute("update memberships set role='owner' where member_id='m2'"); self.db.execute("update memberships set status='removed' where member_id='m1'")   # a second owner makes it legal
    def test_audit_is_append_only(self):
        self.db.execute("insert into audit_events values('e1',1,'agent-1','view_case','LOCASE-1','ok')")
        self.bad("update audit_events set outcome='denied' where event_id='e1'"); self.bad("delete from audit_events")
    def test_verification_cannot_succeed_without_method_and_source(self):
        self.db.execute("insert into verification_cases values('v1','s','legal_name','pending',null,'p1',1,null)")
        self.bad("insert into verification_cases values('v2','s','legal_name','verified',null,'p1',1,null)")    # no method
        self.bad("insert into verification_cases values('v3','s','legal_name','verified','registry','p1',0,null)")   # source unavailable: never verified
        self.db.execute("insert into verification_cases values('v4','s','legal_name','verified','registry','p1',1,null)")
    def test_chat_has_only_business_and_support_routes(self):
        self.db.execute("insert into conversations values('c1','business',null,'merchant','m','in_progress')"); self.db.execute("insert into support_cases values('k1','r','billing','open')")
        self.db.execute("insert into conversations values('c2','support','k1','agent','a1','assigned')")
        self.bad("insert into conversations values('c3','personal',null,'agent','a','assigned')"); self.bad("insert into conversations values('c4','group',null,'agent','a','assigned')")
        self.bad("insert into conversations values('c5','support',null,'agent','a','teleported')")
    def test_postgres_schema_mirrors_the_checked_one(self):
        pg = pathlib.Path(os.path.join(ROOT, "sql", "schema.postgres.sql")).read_text()
        for needle in ("keep_one_owner", "audit_no_delete", "public_ids_never_deleted", "route IN ('business','support')", "NOT executed"): self.assertIn(needle, pg)
if __name__ == "__main__":
    unittest.main()
