import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { betAdultAge, betCancelCheck, betCheckAnswer, betCommission, betExpectedCash, betFlags, betMayHandOverCash, betMayStart, betOddsText, betOfflineSlip,
  betOnlineOnly, betPossibleWin, betReferNext, betSettlement, betSlipResult, betSplitting, betStakeCheck, betStakeMethodOk, betTotalOdds, betTwoPersonNeeded } from "../src/betting.js";
import type { BetOddsFormat } from "../src/betting.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/betting.v1.json`, "utf8"));

test("who may start a bet agrees with the Python reference", () => {
  for (const c of V.starts) assert.equal(betMayStart(c.online, c.signed, c.age, c.excluded), c.answer, JSON.stringify(c));
});
test("odds, how they look, possible wins and stakes agree", () => {
  for (const c of V.odds) assert.equal(betTotalOdds(c.odds), c.total);
  for (const c of V.texts) assert.equal(betOddsText(c.odds, c.format as BetOddsFormat), c.text, JSON.stringify(c));
  for (const c of V.wins) assert.equal(betPossibleWin(c.stake, c.odds, c.max), c.win, JSON.stringify(c));
  for (const c of V.stakes) assert.equal(betStakeCheck(c.stake, c.min, c.max, c.left), c.answer, JSON.stringify(c));
  assert.throws(() => betPossibleWin(1.5, [2000])); assert.throws(() => betTotalOdds([999]));
});
test("every ticket check answers the same in both languages", () => {
  for (const c of V.checks) assert.equal(betCheckAnswer(c.ticket, c.today, c.shop_max, c.cash), c.answer, JSON.stringify(c));
});
test("offline slips, online-only actions, cancelling and two-person approval agree", () => {
  for (const c of V.slips) assert.equal(betOfflineSlip(c.allows, c.kind, c.starts_in, c.lead, c.stake, c.slip_cap, c.queued, c.shop_cap), c.answer, JSON.stringify(c));
  for (const c of V.results) assert.deepEqual(betSlipResult(c.accepted, c.stake), c.out);
  for (const c of V.online) assert.equal(betOnlineOnly(c.action, c.online), c.ok);
  for (const c of V.cancels) assert.equal(betCancelCheck(c.online, c.allows, c.started, c.manager, c.since, c.window), c.answer, JSON.stringify(c));
  for (const c of V.two_person) assert.equal(betTwoPersonNeeded(c.amount, c.owner), c.needed, JSON.stringify(c));
});
test("commission, cash, flags, warnings, settlement, stake methods, ages and referral steps agree", () => {
  for (const c of V.commission) assert.equal(betCommission(c.amount, c.bps), c.commission);
  for (const c of V.cash) assert.equal(betExpectedCash(c.opening, c.stakes, c.payouts), c.expected);
  for (const c of V.flags) assert.deepEqual(betFlags(c.scans, c.payouts, c.shop_max), c.flags);
  for (const c of V.splitting) assert.equal(betSplitting(c.stakes, c.threshold), c.flag, JSON.stringify(c));
  for (const c of V.settlement) assert.equal(betSettlement(c.stakes, c.payouts, c.commission), c.net);
  for (const c of V.methods) assert.equal(betStakeMethodOk(c.method), c.ok, c.method);
  for (const c of V.ages) assert.equal(betAdultAge(c.pack), c.age);
  for (const c of V.refer) assert.equal(betReferNext(c.step), c.next);
});
test("cash leaves the drawer only after the operator confirms the payout lock", () => {
  assert.equal(betMayHandOverCash("confirmed"), true);
  for (const s of ["sent", "failed", "queued", ""]) assert.equal(betMayHandOverCash(s), false);
});
