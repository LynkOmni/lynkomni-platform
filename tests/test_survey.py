"""LynkSurvey in full (LynkS; master blueprint section 63; build section 3B): building with the clear question check and versions,
approval, the plan's limits, the four "one person, one answer" rules, "Real answers only", anonymity and small groups, answers from
added devices (also offline), live results with margins, the research tools, call back and "You said, we did", rewards and the
LynkSurvey Panel through the partner, verified results, downloads, the person's own controls and what is billed.
No event ever carries a name or a phone number."""
import json, os, unittest
from datetime import datetime, timezone

from contract.tools.validate_contract import uuid4
from dv.box import LocalRejection, LynkDVBox
from people.survey import DAY, Survey
from people.survey_device import SurveyDevice
from services.platform import Platform

T0 = 1_800_000_000.0 - 1_800_000_000.0 % DAY + 9 * 3600
AT = lambda t: datetime.fromtimestamp(t, tz=timezone.utc)
Q = [{"id": "visit", "type": "rating", "text": "How was your visit today?"}, {"id": "why", "type": "long", "text": "What should we do better?"}]


class SurveyTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LYNK_MODE", None)
        self.p = Platform(); self.s = self.p.survey; self.m = uuid4(); self.boss = uuid4(); self.maker = uuid4()
        self.p.billing.set_plan(self.m, "lynksurvey", "plus")
        self.s.add_role(self.m, self.boss, "owner"); self.s.add_role(self.m, self.maker, "creator", by=self.boss)
        self.place = self.s.add_place(self.m, self.boss, now=T0)

    def events(self, *types): return self.p.c.store.of(self.m, *types)
    def make(self, **kw):
        kw.setdefault("place", self.place)
        sid = self.s.create(self.m, kw.pop("by", self.maker), kw.pop("kind", "satisfaction"), kw.pop("questions", Q), now=T0, **kw)
        self.s.set_state(self.m, sid, self.maker, "open", now=T0); return sid
    def give(self, sid, ratings, way="smartphone", **kw):
        return [self.s.answer(sid, way, [{"q": "visit", "number": r}], seconds=30, now=T0 + 60 * i, **kw) for i, r in enumerate(ratings)]

    # ---- building
    def test_the_clear_question_check_and_write_it_for_me(self):
        found = Survey.check_questions([{"id": "a", "type": "rating", "text": "Don't you agree our service is great?"}, {"id": "b", "type": "yes_no", "text": "Is it fast and is it cheap?"},
                                        {"id": "c", "type": "choice", "text": "Which political party do you support?"}])
        self.assertEqual([(f["q"], f["problem"]) for f in found], [("a", "pushes_towards_an_answer"), ("b", "two_questions_in_one"), ("c", "sensitive_topic")])
        self.assertTrue(found[0]["suggestion"].startswith("How would you rate"))
        d = self.s.write_it_for_me(self.m, self.maker, "I want to know why customers don't come back")
        self.assertEqual(d["kind"], "recommend"); self.assertTrue(d["suggestion"]); self.assertEqual(d["questions"][0]["type"], "score")
        free = uuid4(); self.p.billing.set_plan(free, "lynksurvey", "free"); self.s.add_role(free, self.boss, "owner")
        with self.assertRaisesRegex(PermissionError, "plan_no_write_it_for_me"): self.s.write_it_for_me(free, self.boss, "anything")
        with self.assertRaisesRegex(PermissionError, "plan_basic_question_types"): self.s.create(free, self.boss, "satisfaction", [{"id": "r", "type": "ranking", "text": "Order these"}])
        self.assertEqual(self.s.how_many(5), 385)

    def test_a_change_after_answers_makes_a_new_version(self):
        sid = self.make(); self.give(sid, [5])
        v = self.s.edit(self.m, sid, self.maker, Q + [{"id": "again", "type": "yes_no", "text": "Will you come back?"}], now=T0)
        self.assertEqual(v, 2)
        self.assertEqual([e["payload"]["version"] for e in self.events("SurveySaved")], [1, 2])
        self.give(sid, [1, 1, 1, 1, 1])
        self.assertFalse(self.s.results(self.m, sid, self.boss, version=1)["shown"])            # 1 answer to version 1: never shown
        self.assertEqual(self.s.results(self.m, sid, self.boss)["questions"]["visit"]["good_percent"], 0)   # version 2 only

    def test_approval_before_anything_reaches_the_public(self):
        self.p.billing.set_plan(self.m, "lynksurvey", "pro"); self.s.settings(self.m, self.boss, approval=True)
        ok = uuid4(); self.s.add_role(self.m, ok, "approver", by=self.boss)
        sid = self.s.create(self.m, self.maker, "satisfaction", Q, now=T0)
        with self.assertRaisesRegex(PermissionError, "needs_approval_first"): self.s.set_state(self.m, sid, self.maker, "open")
        self.s.submit(self.m, sid, self.maker); self.s.decide(self.m, sid, ok, "send_back", note="Shorter please")
        self.s.submit(self.m, sid, self.maker); self.s.decide(self.m, sid, ok, "approve")
        self.s.set_state(self.m, sid, self.maker, "open")
        self.assertEqual([e["payload"]["decision"] for e in self.events("SurveyApproval")], ["send_back", "approve"])
        free = uuid4(); self.p.billing.set_plan(free, "lynksurvey", "free"); self.s.add_role(free, self.boss, "owner")
        with self.assertRaisesRegex(PermissionError, "plan_no_approval"): self.s.settings(free, self.boss, approval=True)

    def test_the_plan_sets_the_limits(self):
        free = uuid4(); self.p.billing.set_plan(free, "lynksurvey", "free"); self.s.add_role(free, self.boss, "owner")
        ids = [self.s.create(free, self.boss, "quick_rating", [{"id": "r", "type": "rating", "text": "How was it?"}]) for _ in range(4)]
        for i in ids[:3]: self.s.set_state(free, i, self.boss, "open")
        with self.assertRaisesRegex(PermissionError, "plan_limit_live_surveys"): self.s.set_state(free, ids[3], self.boss, "open")
        self.assertEqual(self.s.answer(ids[0], "whatsapp", [{"q": "r", "number": 4}])["reason"], "plan_no_whatsapp_and_chat")
        with self.assertRaisesRegex(PermissionError, "plan_no_what_matters_most"): self.s.create(self.m, self.maker, "what_matters_most", Q)
        with self.assertRaisesRegex(PermissionError, "plan_no_organisation_tree"): self.s.add_place(self.m, self.boss, level="department")
        with self.assertRaises(PermissionError): self.s.create(self.m, uuid4(), "satisfaction", Q)             # only owners, managers and creators build

    # ---- one person, one answer
    def test_the_four_rules(self):
        sid = self.make(rule="invited"); codes = self.s.invite(self.m, sid, self.maker, [(uuid4(), "ama@example.org"), (None, None)], now=T0)
        self.assertEqual(self.s.answer(sid, "email", [{"q": "visit", "number": 4}], invite_code="wrong", seconds=20)["reason"], "invitation_needed")
        self.assertEqual(self.s.answer(sid, "email", [{"q": "visit", "number": 4}], invite_code=codes[0], seconds=20)["state"], "accepted")
        self.assertEqual(self.s.answer(sid, "email", [{"q": "visit", "number": 4}], invite_code=codes[0], seconds=20)["reason"], "already_answered")
        ph = self.make(rule="one_per_phone")
        self.assertEqual(self.s.answer(ph, "smartphone", [{"q": "visit", "number": 4}], seconds=20)["reason"], "confirm_phone_first")
        code = self.s.phone_code(ph, "+237650000111", now=T0)["sandbox_code"]
        self.assertIsNone(self.s.confirm_phone(ph, "+237650000111", "000000" if code != "000000" else "111111"))
        mark = self.s.confirm_phone(ph, "+237650000111", code)
        self.assertEqual(self.s.answer(ph, "smartphone", [{"q": "visit", "number": 4}], phone_mark=mark, seconds=20)["state"], "accepted")
        self.assertEqual(self.s.phone_code(ph, "+237650000111")["reason"], "already_answered")
        ver = self.make(rule="verified")
        self.assertEqual(self.s.answer(ver, "smartphone", [{"q": "visit", "number": 4}], seconds=20)["reason"], "sign_in_needed")
        me = uuid4(); self.s.answer(ver, "smartphone", [{"q": "visit", "number": 4}], person=me, seconds=20)
        self.assertEqual(self.s.answer(ver, "smartphone", [{"q": "visit", "number": 4}], person=me, seconds=20)["reason"], "already_answered")
        for e in self.p.c.store.of(self.m):
            self.assertNotIn("+237650000111", json.dumps(e["payload"])); self.assertNotIn("ama@example.org", json.dumps(e["payload"]))

    def test_real_answers_only_flags_and_never_deletes(self):
        sid = self.make()
        r = self.s.answer(sid, "smartphone", [{"q": "visit", "number": 5}], seconds=1)
        self.assertEqual(r["state"], "please_check")
        chk = [e["payload"] for e in self.events("SurveyAnswerChecked")]; self.assertEqual(chk[-1], {"answer_id": r["answer_id"], "result": "please_check", "reason": "too_fast"})
        self.assertEqual(self.s.live(self.m, self.boss)["please_check"], 1)
        self.s.decide_flag(self.m, r["answer_id"], self.boss, accept=True)
        self.assertEqual(self.s.live(self.m, self.boss)["please_check"], 0)
        self.assertEqual(self.s.answer(sid, "smartphone", [{"q": "visit", "number": 3}], seconds=20, device_today=9)["state"], "please_check")   # many from one personal phone

    def test_anonymous_means_anonymous_and_small_groups_are_never_shown(self):
        me = uuid4(); sid = self.make(rule="verified", anonymous=True)
        self.s.answer(sid, "smartphone", [{"q": "visit", "number": 2}], person=me, seconds=20)
        self.assertEqual(self.s.my_answers(me), [])                                               # nobody is linked to an anonymous answer
        self.assertEqual(self.s.db.execute("select person from sv_answers where survey_id=?", (sid,)).fetchone()[0], None)
        self.assertFalse(self.s.results(self.m, sid, self.boss)["shown"])
        for _ in range(4): self.s.answer(sid, "smartphone", [{"q": "visit", "number": 4}], person=uuid4(), seconds=20)
        r = self.s.results(self.m, sid, self.boss)
        self.assertTrue(r["shown"]); self.assertEqual(r["answers"], 5); self.assertEqual(r["questions"]["visit"]["good_percent"], 80)
        self.assertEqual(self.s.you_said(self.m, sid, self.boss, "We opened a second counter.")["public_page"], True)
        self.assertEqual([x["text"] for x in self.s.you_said_for(sid)], ["We opened a second counter."])   # what the public page shows
        named = self.make(rule="verified"); them = uuid4()
        self.s.answer(named, "smartphone", [{"q": "visit", "number": 2}], person=them, seconds=20)
        self.assertEqual(self.s.you_said(self.m, named, self.boss, "We cut the wait.")["told"], 1)
        self.assertEqual(self.s.my_answers(them)[0]["you_said"][0]["text"], "We cut the wait.")       # it reaches the person in My answers
        self.assertEqual([l["kind"] for l in self.p.notifier.lines.values() if l["person"] == them], ["survey_you_said"])   # and as a message
        self.assertEqual([e["payload"]["told"] for e in self.p.c.store.of(self.m, "SurveyYouSaidSent")], [0, 1])     # the cloud's own event

    def test_sensitive_questions_need_the_persons_agreement(self):
        sid = self.make(questions=[{"id": "visit", "type": "rating", "text": "How is your health care at this clinic?"}])
        self.assertEqual(self.s.answer(sid, "smartphone", [{"q": "visit", "number": 4}], seconds=20)["reason"], "agreement_needed")
        self.assertEqual(self.s.answer(sid, "smartphone", [{"q": "visit", "number": 4}], seconds=20, consent=True)["state"], "accepted")

    def test_partner_ways_wait_for_the_partner_and_test_answers_never_count(self):
        sid = self.make()
        self.assertEqual(self.s.answer(sid, "basic_phone", [{"q": "visit", "number": 4}], seconds=20)["state"], "coming_soon")
        t = self.s.create(self.m, self.maker, "satisfaction", Q, place=self.place); self.s.set_state(self.m, t, self.maker, "test")
        for _ in range(6): self.assertTrue(self.s.answer(t, "smartphone", [{"q": "visit", "number": 5}], seconds=20)["test"])
        self.assertFalse(self.s.results(self.m, t, self.boss)["shown"])

    # ---- answers from added devices, also offline
    def test_kiosk_and_field_answers_from_added_devices_offline(self):
        sid = self.make(); dev = uuid4(); staff = uuid4()
        self.s.add_device(self.m, self.place, dev, "tablet", self.boss)
        box = LynkDVBox(self.m, self.place, dev, staff, "manager", now=AT(T0)); box.online = False
        d = SurveyDevice(box, self.s.device_pack(dev))
        for r in (5, 4, 4, 2, 5, 5): d.answer(sid, "kiosk", [{"q": "visit", "number": r}])
        d.answer(sid, "field", [{"q": "visit", "number": 3}, {"q": "why", "text": "The wait was long"}], entered_by=staff)
        with self.assertRaisesRegex(LocalRejection, "way_not_on_this_device"): d.answer(sid, "pos", [{"q": "visit", "number": 3}])
        with self.assertRaisesRegex(LocalRejection, "device_not_added"): SurveyDevice(box).answer(sid, "kiosk", [])
        out = [self.s.ingest(self.m, e, now=T0 + 3600) for e in box.log]
        self.assertEqual([o["state"] for o in out], ["accepted"] * 7)                         # many people on one kiosk is never "many from one device"
        self.assertEqual(self.s.ingest(self.m, box.log[0], now=T0 + 3600)["state"], "duplicate")
        self.assertEqual(self.s.results(self.m, sid, self.boss)["answers"], 7)
        stranger = LynkDVBox(self.m, self.place, uuid4(), staff, "manager", now=AT(T0))
        stranger.log.append(dict(box.log[0], device_id=stranger.d, event_id=uuid4()))
        self.assertEqual(self.s.ingest(self.m, stranger.log[0])["reason"], "device_not_added")

    # ---- results and research tools
    def test_results_margins_the_tree_and_viewers(self):
        self.p.billing.set_plan(self.m, "lynksurvey", "max")
        hq = self.s.add_place(self.m, self.boss, level="head_office"); cm = self.s.add_place(self.m, self.boss, level="country", parent=hq, country="CM")
        dla = self.s.add_place(self.m, self.boss, level="branch", parent=cm); bua = self.s.add_place(self.m, self.boss, level="branch", parent=cm)
        v = uuid4(); self.s.add_role(self.m, v, "viewer", by=self.boss, place=dla)
        sid = self.make(place=None)
        for place, ratings in ((dla, [5, 5, 4, 4, 2, 1]), (bua, [5, 4, 4, 4, 4])):
            dev = uuid4(); self.s.add_device(self.m, place, dev, "kiosk", self.boss)
            box = LynkDVBox(self.m, place, dev, self.boss, "manager", now=AT(T0)); d = SurveyDevice(box, self.s.device_pack(dev))
            for r in ratings: d.answer(sid, "kiosk", [{"q": "visit", "number": r}])
            for e in box.log: self.s.ingest(self.m, e, now=T0)
        everything = self.s.results(self.m, sid, self.boss)["questions"]["visit"]
        self.assertEqual((everything["n"], everything["good_percent"], everything["margin_tenths"]), (11, 82, 227))
        self.assertEqual(self.s.results(self.m, sid, v)["answers"], 6)                     # a branch head sees only their branch
        self.assertEqual(self.s.results(self.m, sid, self.boss, places=self.s._below(cm))["answers"], 11)   # the country adds up its branches

    def test_research_tools(self):
        self.p.billing.set_plan(self.m, "lynksurvey", "pro")
        sid = self.make(questions=Q + [{"id": "most", "type": "best_worst", "text": "Most and least important"}, {"id": "offer", "type": "offer_pick", "text": "Which would you pick?"}])
        rows = [("men", 5, "The wait was too long"), ("men", 4, "Staff were kind"), ("men", 5, "long queue"), ("men", 4, "friendly staff"), ("men", 5, "slow"),
                ("women", 2, "waiting time"), ("women", 1, "too slow"), ("women", 2, "rude staff"), ("women", 4, "price too high"), ("women", 2, "long wait")]
        for i, (g, r, txt) in enumerate(rows):
            self.s.answer(sid, "smartphone", [{"q": "visit", "number": r}, {"q": "why", "text": txt}, {"q": "most", "choice": "speed|price"}, {"q": "offer", "choice": "A" if i % 3 else "B"}],
                          group=g, seconds=40, now=T0 + i)
        cmp = self.s.compare(self.m, sid, self.boss, "visit", "group", ["men", "women"])
        self.assertEqual((cmp["men"]["good_percent"], cmp["women"]["good_percent"]), (100, 20))
        self.assertEqual(self.s.real_difference_for(self.m, sid, self.boss, "visit", "group", "men", "women")["verdict"], "real")
        self.assertEqual(Survey.real_difference(62, 40, 55, 40), "could_be_chance")
        b = self.s.balanced(self.m, sid, self.boss, "visit", {"men": 30, "women": 70})
        self.assertEqual((b["raw_percent"], b["balanced_percent"]), (60, 44))
        th = self.s.themes(self.m, sid, self.boss, "why")["themes"]; self.assertEqual(next(iter(th)), "waiting_time")
        self.assertEqual(self.s.best_worst(self.m, sid, self.boss, "most")["order"][0], "speed")
        self.assertIn("A", self.s.trade_off(self.m, sid, self.boss, "offer")["picked"])
        with self.assertRaisesRegex(ValueError, "add up to 100"): self.s.balanced(self.m, sid, self.boss, "visit", {"men": 30})

    def test_groups_to_fill_close_a_full_group(self):
        self.p.billing.set_plan(self.m, "lynksurvey", "pro")
        sid = self.make(targets={"north": 2})
        for _ in range(2): self.s.answer(sid, "smartphone", [{"q": "visit", "number": 4}], group="north", seconds=20)
        self.assertEqual(self.s.answer(sid, "smartphone", [{"q": "visit", "number": 4}], group="north", seconds=20)["state"], "group_full")
        self.assertEqual(self.s.answer(sid, "smartphone", [{"q": "visit", "number": 4}], group="south", seconds=20)["state"], "accepted")

    # ---- closing the loop, rewards, panel
    def test_unhappy_answers_alert_the_manager_and_create_a_call_back(self):
        sid = self.make(); self.p.flow.set_on(self.m, "survey-call-back")
        for i in range(3): self.s.answer(sid, "smartphone", [{"q": "visit", "number": 1}], seconds=20, call_back_contact="+237650000222", now=T0 + i)
        tasks = self.s.tasks(self.m); self.assertEqual(len(tasks), 3)
        self.s.call_back_done(self.m, tasks[0]["task_id"], self.boss)
        self.assertEqual([e["payload"]["state"] for e in self.events("SurveyCallBack")], ["created"] * 3 + ["done"])
        kinds = [l["kind"] for l in self.p.notifier.lines.values()]
        self.assertEqual(kinds.count("survey_alert"), 1)                                    # 3 unhappy answers in an hour: one alert
        self.assertEqual(kinds.count("survey_call_back"), 3)

    def test_rewards_wait_for_the_partner_and_the_panel_never_shows_who(self):
        sid = self.make(); a = self.give(sid, [5])[0]["answer_id"]
        r = self.s.reward(self.m, a, "airtime", 500, "XAF")
        self.assertEqual(r["state"], "coming_soon")                                         # no rewards partner signed in that country yet
        self.assertEqual(self.s.reward(self.m, a, "airtime", 500, "XAF")["reason"], "one_reward_per_person")
        with self.assertRaises(ValueError): self.s.reward(self.m, a, "airtime", 5.0, "XAF")
        self.p.billing.set_plan(self.m, "lynksurvey", "pro")
        for i in range(4): self.s.panel_join(uuid4(), "GH", "18-35", "en", owns_business=i % 2 == 0)
        out = self.s.ask_panel(self.m, sid, self.maker, 500, country="GH", owns_business=True)
        self.assertEqual(out, {"reached": 2, "wanted": 500})
        me = uuid4(); self.s.panel_join(me, "CM", "36-50", "fr"); self.assertEqual(self.s.panel_leave(me), 1)
        self.assertEqual(self.s.db.execute("select count(*) from sv_panel where person=?", (me,)).fetchone()[0], 0)

    def test_a_reward_is_tracked_and_paid_only_on_the_partners_answer(self):
        import providers
        sid = self.make(); a = self.give(sid, [5])[0]["answer_id"]
        real = providers.ready
        providers.ready = lambda service, country: (True, "sandbox")
        try: r = self.s.reward(self.m, a, "airtime", 500, "XAF")
        finally: providers.ready = real
        self.assertEqual(r["state"], "sent")
        self.assertEqual(self.p.tracking.t.state("survey_reward", r["reward_id"]), "sent")             # never "paid" before the partner says so
        self.s.reward_answer(self.m, r["reward_id"], "paid")
        self.assertEqual(self.p.tracking.t.state("survey_reward", r["reward_id"]), "confirmed")
        with self.assertRaises(ValueError): self.s.reward_answer(self.m, r["reward_id"], "paid")        # answered once

    # ---- verified results, downloads, the person's control, billing
    def test_verified_results_and_downloads(self):
        self.p.billing.set_plan(self.m, "lynksurvey", "pro")
        sid = self.make(); self.give(sid, [5, 4, 3, 5, 4])
        digest = self.s.verify(self.m, sid, self.boss)
        self.assertEqual(self.s.check_link(digest)["state"], "real_and_untouched")
        self.s.db.execute("update sv_answers set answers='[]' where survey_id=? and rowid=(select min(rowid) from sv_answers where survey_id=?)", (sid, sid))
        self.assertEqual(self.s.check_link(digest)["state"], "changed_since")
        d = self.s.download(self.m, sid, self.boss, "spss")
        self.assertTrue(d["data"].startswith("answer,visit,why,way")); self.assertIn("VARIABLE LABELS visit", d["labels"])
        self.p.billing.set_plan(self.m, "lynksurvey", "plus")
        with self.assertRaisesRegex(PermissionError, "plan_no_download_stata"): self.s.download(self.m, sid, self.boss, "stata")

    def test_my_answers_dont_ask_again_and_contacts_kept_30_days(self):
        me = uuid4(); sid = self.make(rule="verified")
        a = self.s.answer(sid, "smartphone", [{"q": "visit", "number": 4}], person=me, seconds=20)["answer_id"]
        self.assertEqual([x["answer_id"] for x in self.s.my_answers(me)], [a])
        self.s.delete_my_answer(me, a); self.assertEqual(self.s.my_answers(me), [])
        self.assertEqual([e["payload"] for e in self.events("SurveyAnswerDeleted")], [{"answer_id": a}])
        self.s.dont_ask_again(me, self.m); self.assertFalse(self.s.may_ask(me, self.m))
        self.assertEqual(self.s.invite(self.m, sid, self.maker, [(me, "me@example.org")]), [])
        ph = self.make(rule="one_per_phone"); self.s.phone_code(ph, "+237650000333", now=T0)
        self.assertEqual(self.s.forget_contacts(now=T0 + 29 * DAY), 0); self.assertEqual(self.s.forget_contacts(now=T0 + 30 * DAY), 1)

    def test_reminders_stop_after_two_and_automatic_surveys_follow_the_plan(self):
        sid = self.make(rule="invited"); person = uuid4(); self.s.invite(self.m, sid, self.maker, [(person, "p@example.org")], now=T0)
        self.assertEqual(len(self.s.reminders(self.m, now=T0 + DAY)), 0)
        self.assertEqual(len(self.s.reminders(self.m, now=T0 + 3 * DAY)), 1)
        self.assertEqual(len(self.s.reminders(self.m, now=T0 + 6 * DAY)), 1)
        self.assertEqual(len(self.s.reminders(self.m, now=T0 + 9 * DAY)), 0)
        q = self.make(after="lynkqueue"); self.assertIsNotNone(self.s.ask_after(self.m, "lynkqueue"))
        with self.assertRaisesRegex(PermissionError, "plan_no_automatic_survey"): self.s.create(self.m, self.maker, "satisfaction", Q, after="lynkinv")
        self.assertIsNotNone(q)

    def test_billing_counts_active_creators_and_extra_answers(self):
        other = uuid4(); self.s.add_role(self.m, other, "creator", by=self.boss)
        sid = self.make()
        for i in range(12): self.s.answer(sid, "smartphone", [{"q": "visit", "number": 4}], seconds=20, now=T0 + i)
        b = self.s.billable(self.m, T0 - DAY, T0 + DAY)
        self.assertEqual((b["creators"], b["extra_creators"], b["answers"], b["over"]), (1, 0, 12, 0))
        for e in self.p.c.store.of(self.m):
            for k in ("name", "phone", "contact"): self.assertNotIn(k, e["payload"])


if __name__ == "__main__":
    unittest.main()
