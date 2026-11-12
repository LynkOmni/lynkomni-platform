"""Arrive Safe and Collect Pass on the account (NEW UPDATE 1, build section 2): sharing only by consent and for a set time,
trip plans watched by the cloud, and one changing pass for every parcel at a pickup point. No position is ever stored here."""
import json, os, re, unittest
from identity.account import EVENTS, MAX_CONSENT_DAYS, PAGES
from identity.arrive_safe import PASS_WINDOW_S, SHARE_MAX_HOURS, uuid7
from services.platform import Platform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T0 = 1_800_000_000.0
CONTRACT = json.load(open(os.path.join(ROOT, "contract", "event-payloads.v4.json"), encoding="utf-8"))["events"]
UUID7 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
POSITION = ("lat", "lng", "latitude", "longitude", "position", "location", "coordinates")


class ArriveSafeTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None); self.p = Platform(); self.a = self.p.account; self.s = self.a.safe
        self.me = self.person("grace.k"); self.sis = self.a._lynkid(self.person("amina.k"))

    def person(self, username):
        st = self.a.begin_sign_up(username, "en", T0, adult_confirmed=True); p = st["person"]
        code = self.a.send_contact_code(p, T0); self.a.confirm_contact(p, code, T0)
        self.a.finish_sign_up(p, f"pk-{username}", "phone", "pii_1", "pii_2", backup_contact="bk", now=T0); return p

    def events(self, *types): return [e for e in self.p.c.store.of(self.me, *types)]

    def test_sharing_needs_a_consent_an_end_and_someone_chosen(self):
        self.assertEqual(MAX_CONSENT_DAYS["location-share"], 30)
        with self.assertRaises(ValueError): self.s.share(self.me, self.sis, "everything", 2, T0)
        with self.assertRaises(ValueError): self.s.share(self.me, self.sis, "live", SHARE_MAX_HOURS + 1, T0)
        with self.assertRaises(ValueError): self.s.share(self.me, self.a._lynkid(self.me), "live", 2, T0)
        sh = self.s.share(self.me, self.sis, "trips", 3, T0)
        self.assertTrue(UUID7.match(sh["share_id"])); self.assertTrue(sh["locns"].startswith("LOCNS-"))
        self.assertTrue(self.a.consent_allows(self.me, "location-share", self.sis, T0 + 60))
        self.assertTrue(self.s.can_see(self.sis, self.me, T0 + 60))
        self.assertEqual([x["with"] for x in self.s.shares(self.me, T0 + 60)], [self.sis])            # always shown to the person sharing
        self.assertEqual(self.s.expire(T0 + 3 * 3600), [sh["share_id"]])
        self.assertFalse(self.s.can_see(self.sis, self.me, T0 + 3 * 3600 + 1))
        self.assertEqual([e["payload"]["reason"] for e in self.events("LocationShareEnded")], ["expired"])

    def test_stopping_a_share_withdraws_the_consent_at_once(self):
        sh = self.s.share(self.me, self.sis, "live", 2, T0)
        with self.assertRaises(PermissionError): self.s.stop(self.p.account.db.execute("select person from acct_people where person!=?", (self.me,)).fetchone()[0], sh["share_id"], T0)
        self.assertTrue(self.s.stop(self.me, sh["share_id"], T0 + 10))
        self.assertFalse(self.a.consent_allows(self.me, "location-share", self.sis, T0 + 11)); self.assertFalse(self.s.can_see(self.sis, self.me, T0 + 11))

    def test_a_trip_plan_is_watched_by_the_cloud(self):
        with self.assertRaises(ValueError): self.s.plan(self.me, T0 + 3600, [], T0)
        with self.assertRaises(ValueError): self.s.plan(self.me, T0 - 1, [self.sis], T0)
        on_time = self.s.plan(self.me, T0 + 3600, [self.sis], T0)
        self.assertTrue(self.s.check_in(self.me, on_time, T0 + 1800))
        late = self.s.plan(self.me, T0 + 7200, [self.sis], T0)
        self.assertEqual(self.s.tick(T0 + 7199), [])
        told = self.s.tick(T0 + 7200)
        self.assertEqual([(x["plan_id"], [c["contact"] for c in x["tell"]], x["tell"][0]["with_location"]) for x in told], [(late, [self.sis], False)])
        self.assertEqual(self.s.tick(T0 + 9000), [])                                                   # told once
        self.assertEqual([e["type"] for e in self.events("TripPlanSet", "TripPlanCheckedIn", "TripPlanOverdue")], ["TripPlanSet", "TripPlanCheckedIn", "TripPlanSet", "TripPlanOverdue"])
        self.assertEqual(CONTRACT["TripPlanOverdue"]["origins"], ["server"])

    def test_collect_pass_changes_every_minute_and_collects_each_parcel_once(self):
        a = self.s.collect_pass(self.me, T0); b = self.s.collect_pass(self.me, T0 + PASS_WINDOW_S)
        self.assertRegex(a["code"], r"^\d{6}$"); self.assertNotEqual(a["code"], b["code"])
        self.assertEqual(self.s.collect(self.me, a["code"], "shp-1", T0 + PASS_WINDOW_S + 5)["ok"], True)    # last minute's code still works
        self.assertEqual(self.s.collect(self.me, b["code"], "shp-1", T0 + PASS_WINDOW_S + 6)["reason"], "already_collected")
        self.assertEqual(self.s.collect(self.me, a["code"], "shp-2", T0 + 5 * PASS_WINDOW_S)["reason"], "code_not_valid")
        other = self.a.db.execute("select person from acct_people where person!=?", (self.me,)).fetchone()[0]
        self.assertEqual(self.s.collect(other, b["code"], "shp-3", T0 + PASS_WINDOW_S)["reason"], "code_not_valid")    # only the person's own pass

    def test_events_match_the_contract_and_carry_no_position(self):
        sh = self.s.share(self.me, self.sis, "zones", 5, T0); self.s.plan(self.me, T0 + 3600, [self.sis], T0); self.s.stop(self.me, sh["share_id"], T0)
        for e in self.events("LocationShareStarted", "LocationShareEnded", "TripPlanSet"):
            self.assertIn(e["type"], EVENTS)
            self.assertEqual(set(e["payload"]) - set(CONTRACT[e["type"]]["payload"]["properties"]), set(), e["type"])
            self.assertFalse(any(k in e["payload"] for k in POSITION))

    def test_pages_and_addresses(self):
        self.assertEqual(PAGES[PAGES.index("trips"):PAGES.index("trips") + 2], ("trips", "collect"))   # NEW UPDATE 4 pages follow them
        addr = json.load(open(os.path.join(ROOT, "catalog", "addresses.v1.json"), encoding="utf-8"))["account_paths"]
        for p in ("/trips", "/collect"): self.assertIn(p, addr)
        self.assertTrue(UUID7.match(uuid7(T0)))


if __name__ == "__main__": unittest.main()
