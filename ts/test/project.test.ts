import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { taskMoveOk, taskBlockers, taskDoneOk, waitOk, projectSchedule, lateTasks, atRiskTasks, myWork, workloadFor, timeEntryOk, timeApproveOk, billableTime,
  projectMoney, milestoneVariance, sprintStats, guestSees, fieldPlaceOk, pjAssistMay, pjTierHas } from "../src/project.js";
import { PROJECT as P } from "../src/project.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/project.v1.json`, "utf8"));

test("task moves, waiting and the critical path agree with the Python reference (SIX SERVICES UPDATE 69.4)", () => {
  for (const c of V.moves) assert.equal(taskMoveOk(P, c.f, c.t), c.expect, JSON.stringify(c));
  for (const t of V.tasks) { assert.deepEqual(taskBlockers(t, V.tasks), V.blockers[t.id], t.id); assert.equal(taskDoneOk(P, t, V.tasks), V.done[t.id], t.id); }
  for (const c of V.wait) assert.equal(waitOk(V.deps, c.a, c.b), c.expect, JSON.stringify(c));
  assert.deepEqual(projectSchedule(V.tasks.filter((t: { id: string }) => "abcdeh".includes(t.id))), V.schedule);
  assert.deepEqual(projectSchedule([]), V.schedule_empty);
});
test("late, at risk, My work and workload", () => {
  for (const c of V.late) assert.deepEqual(lateTasks(P, V.tasks, V.today + c.d), c.expect, JSON.stringify(c));
  for (const c of V.risk) assert.deepEqual(atRiskTasks(P, V.tasks, V.today + c.d), c.expect, JSON.stringify(c));
  for (const c of V.mywork) assert.deepEqual(myWork(P, V.tasks, c.p, V.today + c.d), c.expect, JSON.stringify(c));
  for (const c of V.workload) assert.deepEqual(workloadFor(P, c.pl, c.lv ?? undefined, c.wk ?? undefined), c.expect, JSON.stringify(c));
});
test("time, money, baselines, sprints, guests and LynkAssist", () => {
  for (const [m, want] of Object.entries(V.entries_ok)) assert.equal(timeEntryOk(P, Number(m)), want, m);
  for (const c of V.approve) assert.equal(timeApproveOk(c.l, c.a), c.expect);
  assert.deepEqual(billableTime(V.entries), V.billable);
  for (const c of V.money) assert.deepEqual(projectMoney(c.b, c.c, c.i), c.expect);
  assert.deepEqual(milestoneVariance({ m1: V.today, m2: V.today + 10, m3: V.today + 20 }, { m1: V.today + 2, m2: V.today + 7, m4: V.today }), V.variance);
  for (const c of V.sprint) assert.deepEqual(sprintStats(V.items, c.d), c.expect);
  for (const c of V.guest) assert.equal(guestSees(P, c.part, c.inv, "p1"), c.expect, JSON.stringify(c));
  for (const c of V.field) assert.equal(fieldPlaceOk(c.s, c.a), c.expect);
  for (const [a, want] of Object.entries(V.assist)) assert.equal(pjAssistMay(P, a), want, a);
  for (const c of V.tiers) assert.equal(pjTierHas(P, c.t, c.f), c.expect, JSON.stringify(c));
});
