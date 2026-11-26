import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  signUpNext, mayStartSignUp, legalNameProblem, basicPhoneAllows, identifierKind, signInWays, extraChecks, sentCodeValid, offlineSignIn,
  unusual, countryAllowed, oldDevice, sessionHours, antiPhishingProblem, backupCodesLeftNote, checkup, recoveryWays, neverAllowed,
  restrictedAfterRecovery, contactsConfirmed, contactsProblem, toStrongest, mayReset, ownerCheckNeeded, ownerCheckMethod, ownerPayer, ownerCheckOutcome, ownerMatchValid,
} from "../src/waysin.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/ways-in.v1.json`, "utf8"));

test("sign-up, sign-in, protections, recovery and resets agree with the Python reference (section 4C points 3 and 5)", () => {
  for (const c of V.sign_up_next) assert.equal(signUpNext(c.done), c.expect, JSON.stringify(c.done));
  for (const c of V.may_start) assert.deepEqual(mayStartSignUp(c.a[0], c.a[1], c.a[2]), c.expect, JSON.stringify(c.a));
  for (const c of V.legal_name) assert.equal(legalNameProblem(c.a), c.expect, c.a);
  for (const c of V.basic) assert.equal(basicPhoneAllows(c.a[0], c.a[1]), c.expect, JSON.stringify(c.a));
  for (const c of V.identifier) assert.equal(identifierKind(c.a), c.expect, c.a);
  for (const c of V.sign_in_ways) assert.deepEqual(signInWays(c.a[0], c.a[1]), c.expect, JSON.stringify(c.a));
  for (const c of V.extra) assert.deepEqual(extraChecks(c.a), c.expect, JSON.stringify(c.a));
  for (const c of V.code_valid) assert.equal(sentCodeValid(c.a[0], c.a[1], c.a[2], c.a[3]), c.expect, JSON.stringify(c.a));
  for (const c of V.offline) assert.deepEqual(offlineSignIn(c.a[0], c.a[1], c.a[2]), c.expect, JSON.stringify(c.a));
  for (const c of V.owner_needed) assert.equal(ownerCheckNeeded(c.a), c.expect, c.a);
  for (const c of V.owner_method) assert.equal(ownerCheckMethod(c.a[0], c.a[1], c.a[2], c.a[3]), c.expect, JSON.stringify(c.a));
  for (const c of V.owner_payer) assert.equal(ownerPayer(c.a), c.expect, c.a);
  for (const c of V.owner_outcome) assert.deepEqual(ownerCheckOutcome(c.a[0], c.a[1], c.a[2]), c.expect, JSON.stringify(c.a));
  for (const c of V.owner_valid) assert.equal(ownerMatchValid(c.a[0], c.a[1], c.a[2], c.a[3]), c.expect, JSON.stringify(c.a));
  for (const c of V.unusual) assert.deepEqual(unusual(c.a[0], c.a[1], c.a[2]), c.expect, JSON.stringify(c.a));
  for (const c of V.country) assert.equal(countryAllowed(c.a[0], c.a[1]), c.expect, JSON.stringify(c.a));
  for (const c of V.old_device) assert.equal(oldDevice(c.a[0], c.a[1]), c.expect, JSON.stringify(c.a));
  for (const c of V.session_hours) assert.equal(sessionHours(c.a), c.expect);
  for (const c of V.word) assert.equal(antiPhishingProblem(c.a), c.expect, c.a);
  for (const c of V.codes_left) assert.equal(backupCodesLeftNote(c.a), c.expect, String(c.a));
  for (const c of V.checkup) assert.deepEqual(checkup(c.a), c.expect, JSON.stringify(c.a));
  for (const c of V.recovery_ways) assert.deepEqual(recoveryWays(c.a), c.expect, JSON.stringify(c.a));
  for (const c of V.never) assert.equal(neverAllowed(c.a), c.expect, c.a);
  for (const c of V.restricted) assert.equal(restrictedAfterRecovery(c.a[0], c.a[1], c.a[2]), c.expect, JSON.stringify(c.a));
  for (const c of V.contacts_confirmed) assert.equal(contactsConfirmed(c.a[0], c.a[1]), c.expect, JSON.stringify(c.a));
  for (const c of V.contacts_problem) assert.equal(contactsProblem(c.a), c.expect, JSON.stringify(c.a));
  for (const c of V.to_strongest) assert.equal(toStrongest(c.a), c.expect, String(c.a));
  for (const c of V.may_reset) assert.deepEqual(mayReset(c.a[0], c.a[1], c.a[2], c.a[3]), c.expect, JSON.stringify(c.a));
});
