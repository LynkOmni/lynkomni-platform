"""LynkAssist in LynkAttend, LynkQueue and LynkSurvey (CONNECT UPDATE 71.6, build section 3B): every action is in the register,
runs only after its class allows it, can be undone where the register says so, and never chooses who is served or decides about
a person."""
import os, unittest
from datetime import datetime, timezone

from contract.tools.validate_contract import uuid4
from dv.box import LynkDVBox
from people.keeper import QueueKeeper
from people.queue import DAY
from services import assist_register as AR
from services.assist_people import PEOPLE_ACTIONS, PeopleAssist
from services.platform import Platform

T0 = 1_800_000_000.0 - 1_800_000_000.0 % DAY + 9 * 3600
AT = lambda t: datetime.fromtimestamp(t, tz=timezone.utc)


class PeopleAssistTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None)
        self.p = Platform(); self.m = uuid4(); self.boss = uuid4()
        self.p.billing.set_plan(self.m, "lynkqueue", "plus"); self.p.billing.set_plan(self.m, "lynksurvey", "plus")
        q = self.p.queue; q.add_manager(self.m, self.boss); place = q.add_place(self.m, self.boss, country="CM", now=T0)
        dev = uuid4(); box = LynkDVBox(self.m, place, dev, self.boss, "manager", now=AT(T0))
        self.k = QueueKeeper(box, q.add_device(self.m, place, dev, "reception", self.boss, now=T0))
        self.s = self.p.survey; self.s.add_role(self.m, self.boss, "owner")
        self.a = PeopleAssist(self.p, self.m, self.boss, self.boss, keeper=self.k)

    def test_every_action_is_in_the_register_and_built(self):
        for a in PEOPLE_ACTIONS:
            self.assertIn(a, AR.ACTIONS); self.assertEqual(AR.ACTIONS[a]["status"], "built", a); self.assertEqual(AR.ACTIONS[a]["build_section"], "3B", a)

    def test_open_a_counter_after_confirm_and_undo_closes_it(self):
        c = next(iter(self.k.counters))
        self.assertEqual(self.a.do("dev", self.boss, "manager", "queue_open_counter", counter=c, now=T0)["state"], "not_done")   # class B waits for Confirm
        r = self.a.do("dev", self.boss, "manager", "queue_open_counter", confirmed=True, counter=c, now=T0)
        self.assertEqual(r["state"], "done"); self.assertEqual(self.k.counters[c]["state"], "open")
        self.assertTrue(self.a.undo(r["entry"], now=T0 + 10)); self.assertEqual(self.k.counters[c]["state"], "closed")
        self.assertEqual(self.a.do("dev", self.boss, "cashier", "queue_open_counter", confirmed=True, counter=c, now=T0)["needs"], "refused")

    def test_survey_draft_pause_with_undo_and_reminders(self):
        r = self.a.do("dev", self.boss, "owner", "survey_write_it_for_me", confirmed=True, sentence="why customers don't come back", now=T0)
        self.assertEqual(r["result"]["draft"], "recommend"); self.assertTrue(r["result"]["suggestion"])
        sid = self.s.create(self.m, self.boss, "satisfaction", [{"id": "v", "type": "rating", "text": "How was it?"}], now=T0); self.s.set_state(self.m, sid, self.boss, "open", now=T0)
        r = self.a.do("dev", self.boss, "owner", "survey_pause", confirmed=True, survey=sid, now=T0)
        self.assertEqual(self.s._sv(sid)["state"], "paused")
        self.assertTrue(self.a.undo(r["entry"], now=T0 + 5)); self.assertEqual(self.s._sv(sid)["state"], "open")
        self.assertEqual(self.a.do("dev", self.boss, "owner", "survey_send_reminders", now=T0)["state"], "done")   # class A: harmless, runs alone

    def test_a_flag_is_only_explained_for_a_person_to_decide_and_offline_waits(self):
        d = self.a.decide("attend_explain_flag", "owner")
        self.assertFalse(d["run"]); self.assertEqual(d["needs"], "hand_over")
        off = self.a.do("dev", self.boss, "owner", "survey_pause", confirmed=True, online=False, survey=uuid4(), now=T0)
        self.assertEqual(off["state"], "queued")                                              # never shown done before the cloud carries it out
        self.assertEqual(self.a.decide("survey_write_it_for_me", "owner", confirmed=True, online=False)["needs"], "prepare_for_later")


if __name__ == "__main__":
    unittest.main()
