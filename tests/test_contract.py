import copy, subprocess, sys, unittest
from datetime import datetime, timedelta, timezone
from cc.box import LynkCCBox
from contract.tools.validate_contract import ReferenceIngest, uuid4, ts
from dv.box import LocalRejection, LynkDVBox

M, B, U = uuid4(), uuid4(), uuid4()

def device(role="owner", **kw):
    return LynkDVBox(M, B, uuid4(), U, role, **kw)

class T(unittest.TestCase):
    def setUp(self):
        self.cc = LynkCCBox()
    def attach(self, dv): self.cc.enroll(dv.d, M)

    def test_the_contract_validator_itself_passes(self):
        out = subprocess.run([sys.executable, "contract/tools/validate_contract.py"], capture_output=True, text=True)
        self.assertIn("failed: 0", out.stdout, out.stdout[-400:])

    def test_device_events_are_valid_chained_and_accepted(self):
        d = device(); self.attach(d)
        p = d.create_product("Juice", 1500); d.receive_stock([(p, 10000)])
        sid = d.record_sale([(p, 2500, 0)]); self.assertEqual(d.record_payment(sid, "cash", 3750), "cash_received")
        self.assertEqual(d.record_payment(sid, "mobile_money", 1), "pending_confirmation")   # never settled by a device
        res = self.cc.push(d.pending(0))
        self.assertTrue(all(r["result"] == "accepted" for r in res["results"])); self.assertEqual(res["ack_seq"], d.seq)
        self.assertEqual(self.cc.stock(M)[p], 10000 - 2500)

    def test_replay_gap_and_tamper(self):
        d = device(); self.attach(d); p = d.create_product("Rice", 1000); d.receive_stock([(p, 5000)]); d.record_sale([(p, 1000, 0)])
        evs = d.pending(0)
        self.assertEqual(self.cc.push(evs[:2])["ack_seq"], 2)
        again = self.cc.push(evs[:2]); self.assertTrue(all(r["result"] == "duplicate" for r in again["results"]))      # idempotent
        gap = self.cc.push(evs[3:]); self.assertEqual(gap["results"][0]["result"], "gap")                               # event 3 is missing
        bad = copy.deepcopy(evs[2]); bad["prev_hash"] = "0" * 64
        self.assertEqual(self.cc.push([bad])["results"][0]["reason"], "broken_hash_chain")
        self.assertEqual(self.cc.push([evs[2]])["results"][0]["result"], "duplicate")                                   # the tampered copy used event 3's id
        self.assertEqual(self.cc.push(evs[3:])["results"][0]["reason"], "broken_hash_chain")                            # the quarantined slot broke the chain
        self.assertTrue(self.cc.quarantined(M))                                                                         # visible, never silent

    def test_two_phones_sell_the_last_item(self):
        a, b = device(), device(); self.attach(a); self.attach(b)
        p = a.create_product("Soap", 800); a.receive_stock([(p, 1000)]); self.cc.push(a.pending(0))
        for dv in (b,):
            dv.products[p] = {"name": "Soap", "price": 800}; dv.stock[p] = 1000
        a.record_sale([(p, 1000, 0)]); b.record_sale([(p, 1000, 0)])
        self.cc.push(a.pending(2)); res = self.cc.push(b.pending(0))
        self.assertTrue(all(r["result"] == "accepted" for r in res["results"]))                                        # facts are never rejected
        self.assertEqual(self.cc.negative_stock(M), {p: -1000})
        self.assertTrue(any("negative_stock" in e["flags"] for e in self.cc.events(M)))

    def test_revocation_flags_and_quarantines(self):
        d = device(); self.attach(d); p = d.create_product("Tea", 500); self.cc.push(d.pending(0))
        self.cc.revoke(d.d, ts(d.clock)); d.advance(seconds=-5); d.receive_stock([(p, 1000)])        # claimed time before revocation
        self.assertIn("after_revocation", self.cc.push(d.pending(1))["results"][0]["flags"])
        d.advance(hours=1); d.receive_stock([(p, 1000)])
        self.assertEqual(self.cc.push(d.pending(2))["results"][0]["reason"], "after_revocation")

    def test_local_rules_permissions_and_session(self):
        c = device("cashier")
        o = device("owner"); pid = o.create_product("Milk", 700); o.receive_stock([(pid, 3000)]); sid = o.record_sale([(pid, 1000, 0)])
        c.products, c.stock = dict(o.products), dict(o.stock); csid = c.record_sale([(pid, 1000, 0)])          # cashiers may sell
        with self.assertRaises(LocalRejection) as e: c.void_sale(csid, "other")                                  # but not void
        self.assertEqual(e.exception.reason, "permission_denied")
        with self.assertRaises(LocalRejection) as e: c.create_product("X", 1)
        self.assertEqual(e.exception.reason, "permission_denied")
        o.void_sale(sid, "entered_in_error")
        with self.assertRaises(LocalRejection) as e: o.void_sale(sid, "duplicate")
        self.assertEqual(e.exception.reason, "already_voided")
        with self.assertRaises(LocalRejection) as e: o.record_sale([])
        self.assertEqual(e.exception.reason, "empty_cart")
        o.advance(days=15)                                                                                       # offline past the 14-day default
        with self.assertRaises(LocalRejection) as e: o.record_sale([(pid, 1000, 0)])
        self.assertEqual(e.exception.reason, "session_expired")
        o.session_max_days = 60; o.record_sale([(pid, 1000, 0)])                                                 # the limit is configurable
        o.session_max_days = 14; o.reauth(); o.record_sale([(pid, 1000, 0)])                                    # or re-authenticate

    def test_cloud_matches_the_reference_model(self):
        """Differential test: the persistent cloud and the contract's reference model agree on every outcome."""
        d = device(); ref = ReferenceIngest(); ref.enroll(d.d); self.attach(d)
        p = d.create_product("Beans", 900); d.receive_stock([(p, 9000)]); s1 = d.record_sale([(p, 1500, 100)]); d.void_sale(s1, "price_error")
        evs = d.pending(0); tampered = copy.deepcopy(evs[2]); tampered["payload"]["adjustment"] = 1
        for batch in (evs[:2], evs[:2], evs[3:], [tampered], evs[2:], evs):
            r1, r2 = self.cc.push(copy.deepcopy(batch)), ref.push(copy.deepcopy(batch))
            self.assertEqual([x["result"] for x in r1["results"]], [x["result"] for x in r2["results"]])
            self.assertEqual(r1["ack_seq"], r2["ack_seq"])
        self.assertEqual([e["event_id"] for e in self.cc.events(M)], [e["event_id"] for e in ref.store])
        self.assertEqual(len(self.cc.quarantined(M)), len(ref.quarantine))

    def test_incremental_negative_flag_agrees_with_full_projection(self):
        d = device(); self.attach(d); p = d.create_product("Oil", 2000); d.adjust_stock(p, -500, "loss"); self.cc.push(d.pending(0))
        self.assertEqual(self.cc.stock(M)[p], -500); self.assertEqual(self.cc.negative_stock(M), {p: -500})

if __name__ == "__main__":
    unittest.main()

class TestPublicIds(unittest.TestCase):
    def test_cloud_assigns_and_offline_devices_use_leased_blocks(self):
        import sqlite3
        from core.ids import IdAllocator, parse
        cc = LynkCCBox(); cc.ids = IdAllocator(cc.db); d = device(); cc.enroll(d.d, M)
        d.accept_lease("RCP", cc.ids.lease("RCP", d.d, 3)); d.accept_lease("ORD", cc.ids.lease("ORD", d.d, 3))
        p = d.create_product("Soap", 700); d.receive_stock([(p, 5000)]); sid = d.record_sale([(p, 1000, 0)]); sale = [e for e in d.log if e["type"] == "SaleRecorded"][0]
        receipt = [e for e in d.log if e["type"] == "ReceiptIssued"][0]["payload"]["receipt_id"]
        self.assertEqual(parse(d.public_map[receipt])[0], "RCP"); self.assertEqual(parse(d.public_map[sid])[0], "ORD")   # printed offline, valid, checksummed
        cc.claim_leased(d.d, d.public_map); res = cc.push(d.pending(0))
        self.assertTrue(all(r["result"] == "accepted" for r in res["results"]))
        self.assertEqual(cc.ids.public_for("RCP", receipt), d.public_map[receipt])                                      # the cloud keeps the device's choice, no second ID
        d2 = device(); cc.enroll(d2.d, M); q = d2.create_product("Tea", 400); d2.record_sale([(q, 1000, 0)]); cc.push(d2.pending(0))
        self.assertEqual(parse(cc.ids.public_for("ORD", [e for e in d2.log if e["type"] == "SaleRecorded"][0]["payload"]["sale_id"]))[0], "ORD")   # no lease: assigned on sync
        with self.assertRaises(PermissionError): cc.claim_leased(d2.d, {"x": d.public_map[receipt]})                  # not leased to this device
        self.assertEqual(cc.ids.release(d.d), 4)                                                                       # unused leased IDs are retired, never reused

class TestUserRevocation(unittest.TestCase):
    def test_revoked_staff_events_are_flagged_for_the_owner(self):
        cc = LynkCCBox(); d = device("cashier"); cc.enroll(d.d, M); p = d.create_product if False else None
        o = device("owner"); cc.enroll(o.d, M); pid = o.create_product("Milk", 700); o.receive_stock([(pid, 3000)]); cc.push(o.pending(0))
        d.products, d.stock = dict(o.products), dict(o.stock)
        cc.revoke_user(d.u, ts(d.clock - timedelta(hours=1))); d.record_sale([(pid, 1000, 0)])                          # sells offline after being removed
        r = cc.push(d.pending(0)); self.assertIn("after_user_revocation", r["results"][0]["flags"]); self.assertTrue(cc.owner_alerts(M))
        self.assertEqual(device("cashier").session_max_days, 14); self.assertEqual(device("owner").session_max_days, 7)   # privileged roles re-authenticate sooner
