"""The automation system of CONNECT UPDATE 71.2 (section 4 row 71.9): try on past data, owners, versioned settings, daily limits
(only lower), pausing on unusual activity, the monthly spending cap, approval chains with escalation and bulk approval, clash
warnings and the digest. Rules in catalog/automations.v1.json "system", run by services/flow.py for every registered automation."""
import json, os, unittest, uuid
os.environ["LYNK_MODE"] = "sandbox"
from services.flow import REGISTER, SYSTEM, DAY
from services.platform import Platform

T0 = 1_794_268_800          # a midnight (UTC)


def pick(level, trigger_kind="event", customer=None):
    for a in REGISTER.values():
        if a["level"] == level and a["trigger"].startswith(trigger_kind + ":") and (customer is None or a["customer_message"] == customer):
            return a
    raise LookupError(level)


class System(unittest.TestCase):
    def setUp(self):
        os.environ["LYNK_MODE"] = "sandbox"
        self.p = Platform(); self.f = self.p.flow; self.m = "m-" + uuid.uuid4().hex[:6]
        self.inform = pick("inform"); self.draft = pick("draft")
        for a in (self.inform, self.draft): self.f.handle(a["id"], lambda f, m, p, now: {"n": p.get("n", 0)})

    def fire(self, a, n, at):
        for i in range(n):
            self.f._run(REGISTER[a["id"]], self.m, {"n": i}, trigger_event=f"t{at}-{i}-{uuid.uuid4().hex[:4]}", now=at + i)

    def alerts(self, kind):
        return [e["payload"] for e in self.p.c.store.of(self.m, "AlertSent") if e["payload"]["kind"] == kind]

    def test_try_on_past_counts_without_acting(self):
        trig = self.inform["trigger"].split(":", 1)[1]
        for _ in range(4): self.p.c.store.append(self.m, "server", trig, {"x": 1})
        before = len(self.p.c.store.since(self.m))
        r = self.f.try_on_past(self.m, self.inform["id"])
        self.assertEqual((r["would_start"], r["replayable"]), (4, True))
        self.assertEqual(len(self.p.c.store.since(self.m)), before, "trying never writes anything")
        user = next(a for a in REGISTER.values() if a["trigger"].startswith("user:"))
        self.assertFalse(self.f.try_on_past(self.m, user["id"])["replayable"], "a person's ask cannot be replayed")

    def test_settings_are_versioned_limits_only_lower_and_owners_answer(self):
        a = self.inform["id"]
        self.assertEqual(self.f.configure(self.m, a, "u1", owner="u7"), 1)
        self.assertEqual(self.f.configure(self.m, a, "u1", daily_limit=2), 2)
        with self.assertRaises(ValueError): self.f.configure(self.m, a, "u1", daily_limit=SYSTEM["limits"]["max_per_day"] + 1)
        self.assertEqual(self.f.restore(self.m, a, 1, "u2"), 3)
        self.assertEqual(self.f.daily_limit(self.m, a), SYSTEM["limits"]["max_per_day"], "version 1 had no lower limit")
        self.assertEqual(self.f.owner(self.m, a), "u7")
        self.assertEqual([v["version"] for v in self.f.versions(self.m, a)], [1, 2, 3])

    def test_a_daily_limit_skips_runs_and_tells_the_owner_once(self):
        self.f.configure(self.m, self.inform["id"], "u1", daily_limit=2)
        self.fire(self.inform, 5, T0)
        self.assertEqual(self.f.runs_on_day(self.m, self.inform["id"], T0), 2)
        self.assertEqual(len(self.alerts("automation_limited")), 1)

    def test_unusual_activity_pauses_until_a_person_resumes(self):
        for d in range(1, 8): self.fire(self.inform, 2, T0 - d * DAY)
        self.fire(self.inform, SYSTEM["unusual"]["floor"] + 2, T0)
        self.assertEqual([x["automation"] for x in self.f.paused(self.m)], [self.inform["id"]])
        self.assertFalse(self.f.is_on(self.m, self.inform["id"]))
        self.assertEqual(len(self.alerts("automation_unusual")), 1)
        with self.assertRaises(PermissionError): self.f.resume(self.m, self.inform["id"], "")
        self.f.resume(self.m, self.inform["id"], "u1"); self.assertTrue(self.f.is_on(self.m, self.inform["id"]))

    def test_the_spending_cap_holds_paid_customer_messages(self):
        cm = next(a for a in REGISTER.values() if a["customer_message"])
        self.f.handle(cm["id"], lambda f, m, p, now: {"sent": 1, "cost_minor": 40})
        self.f.set_on(self.m, cm["id"])
        self.f.set_cap(self.m, 100)
        self.fire(cm, 5, T0)
        self.assertEqual(self.f.spent(self.m, T0), 120, "three runs of 40 reach the cap of 100, then they wait")
        self.assertEqual(len(self.alerts("automation_over_cap")), 1)
        with self.assertRaises(ValueError): self.f.set_cap(self.m, 10.5)

    def test_drafts_follow_their_chain_escalate_and_are_approved_in_bulk(self):
        self.f.configure(self.m, self.draft["id"], "u1", chain=["manager", "owner"])
        self.fire(self.draft, 3, T0)
        ids = [d["id"] for d in self.f.drafts(self.m)]
        self.assertEqual(len(ids), 3)
        with self.assertRaises(PermissionError): self.f.approve_draft(self.m, ids[0], "u2", "owner")          # the manager's step first
        self.assertEqual(self.f.approve_draft(self.m, ids[0], "u2", "manager"), "waiting")
        with self.assertRaises(PermissionError): self.f.approve_draft(self.m, ids[0], "u2", "owner")          # never the same person twice
        self.assertEqual(self.f.approve_draft(self.m, ids[0], "u3", "owner"), "approved")
        self.assertEqual(self.f.escalate(self.m, now=T0 + 3600), [], "nothing goes up before its time")
        up = self.f.escalate(self.m, now=T0 + SYSTEM["escalation"]["after_hours"] * 3600 + 10)
        self.assertEqual({u["to"] for u in up}, {"owner"}, "the manager did not act, so the owner is asked")
        self.assertEqual(len(self.alerts("automation_escalated")), 2)
        out = self.f.approve_many(self.m, ids[1:] + ["nope"], "u3", "owner")
        self.assertEqual([out[i] for i in ids[1:]], ["approved", "approved"])
        self.assertTrue(out["nope"].startswith("refused"), "one refusal never stops the others")
        self.assertEqual(self.f.drafts(self.m), [], "approved by people, never by waiting")

    def test_clashes_are_warned_and_the_digest_gathers_inform_notices(self):
        trig = "event:ClashTestEvent"
        for i in (1, 2):
            REGISTER[f"x-msg-{i}"] = {**self.inform, "id": f"x-msg-{i}", "trigger": trig, "customer_message": True}
            self.f.handle(f"x-msg-{i}", lambda f, m, p, now: {"x": 1})
        try:
            self.assertEqual([(c["a"], c["b"], c["why"]) for c in self.f.clashes(self.m)], [("x-msg-1", "x-msg-2", "two_customer_messages")])
        finally:
            for i in (1, 2): REGISTER.pop(f"x-msg-{i}"); self.f.handlers.pop(f"x-msg-{i}")
        self.assertEqual(self.f.clashes(self.m), [], "automations that work together are not a clash")
        with self.assertRaises(ValueError): self.f.configure(self.m, self.draft["id"], "u1", digest=True)
        self.f.configure(self.m, self.inform["id"], "u1", digest=True)
        self.fire(self.inform, 3, T0)
        d = self.f.digest(self.m, T0, now=T0 + 100)
        self.assertEqual([(x["automation"], x["runs"]) for x in d], [(self.inform["id"], 3)])


class Register(unittest.TestCase):
    def test_every_system_rule_is_stated(self):
        for k in ("try_on_past", "owners", "versions", "limits", "unusual", "spending_cap", "approval_chain", "escalation", "bulk", "clashes", "digest"):
            self.assertTrue(SYSTEM[k]["rule"].strip(), k)


if __name__ == "__main__":
    unittest.main()
