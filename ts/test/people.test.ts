import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as A from "../src/attendance.js";
import * as Q from "../src/queue.js";
import * as S from "../src/survey.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/people.v1.json`, "utf8"));

test("LynkAttend: IDCN, easy PINs, sets, the door ladder and checkers agree with the Python reference", () => {
  const a = V.attendance;
  for (const c of a.idcn) assert.equal(A.idcn(c.id), c.idcn, c.id);
  for (const c of a.easy_pin) assert.equal(A.isEasyPin(c.pin), c.easy, c.pin);
  assert.equal(A.PIN_GROUP_SIZE, a.pin_group_size); assert.equal(A.EASY_PIN_COUNT, a.easy_pin_count);
  for (const [s, m] of Object.entries(a.means)) assert.deepEqual(A.meansOf(s), m);
  for (const c of a.sets_allowed) assert.deepEqual(A.setsAllowed(c.face, c.finger), c.sets);
  for (const c of a.door) assert.deepEqual(A.door(c.set, c.attempts, c.broken), c.out);
  assert.deepEqual(A.checkerChoices(a.checkers.list, a.checkers.me), a.checkers.choices);
  for (const c of a.warning) assert.equal(A.pinGroupWarning(c.used), c.warn);
  for (const c of a.no_check_out) assert.equal(A.noCheckOutDue(c.in, c.end), c.due);
});

test("LynkQueue: Lynk Codes, rude-word skipping, blocks, the fair order and put back agree", () => {
  const q = V.queue;
  assert.equal(Q.ALPHABET, q.alphabet); assert.equal(Q.CAPACITY, q.capacity);
  for (const c of q.codes) { assert.equal(Q.code(c.n), c.code); assert.equal(Q.index(c.code), c.n); }
  for (const c of q.next) assert.equal(Q.nextCode(c.after), c.next);
  for (const c of q.sections) assert.equal(Q.validSection(c.s), c.valid, c.s);
  assert.deepEqual(Q.reserveBlock("A2K9P2"), q.block);
  for (const c of q.pick) assert.equal(Q.pickNext(q.waiting, c.served_since_priority, c.now), c.next);
  for (const c of q.wait) assert.equal(Q.waitMinutes(c.place, c.avg, c.open), c.minutes);
  for (const c of q.put_back) assert.deepEqual(Q.putBack(c.order, c.ticket, c.missed, c.now), c.out);
  assert.deepEqual(Q.runningLate(q.running_late.order, q.running_late.ticket), q.running_late.out);
});

test("LynkSurvey: sample size, margins, the group of 5, one answer and the real-answers check agree", () => {
  const s = V.survey;
  for (const c of s.sample) assert.equal(S.sampleSize(c.margin, c.population), c.n);
  for (const c of s.margin) assert.equal(S.margin(c.share, c.answers), c.tenths);
  for (const c of s.show) assert.equal(S.canShow(c.size), c.show);
  for (const c of s.may_answer) assert.equal(S.mayAnswer(c.rule, c.already, c.invite, c.signed_in, c.phone), c.out);
  for (const c of s.flags) assert.deepEqual(S.realAnswerFlags(c.seconds, c.questions, c.same, c.today, c.shared), c.out);
  for (const c of s.groups) assert.equal(S.groupOpen(c.group, c.counts, c.targets), c.open);
});
