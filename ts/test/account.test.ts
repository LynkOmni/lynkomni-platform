import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { CLOSE_GRACE_DAYS, CONSENT_SCOPES, DATA_REQUEST_DAYS, MAX_CONSENT_DAYS, PAGES, PAYOUT_WAIT_S, RECOVERY, REGISTRATION_STEPS, RESTRICTED_AFTER_RECOVERY, RESTRICTION_S, SESSION_S, SITES, STEPUP_S,
  applicationStatus, canSubmit, consentEnd, consentState, deviceCan, exportAllowed, nextSignUpStep, pagePath, payoutChange, recoveryPath, recoveryReady, recoveryReadyAt, sessionValid, signInAlertNeeded, standingChargeAllowed } from "../src/account.js";
import type { ConsentScope, RecoveryPath, RegistrationStep } from "../src/account.js";

const root = `${process.cwd()}/..`;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/account.v1.json`, "utf8"));

test("constants agree with the Python reference", () => {
  const c = V.constants;
  assert.equal(SESSION_S, c.session_s); assert.equal(STEPUP_S, c.stepup_s); assert.deepEqual([...SITES].sort(), c.sites);
  assert.deepEqual([...RESTRICTED_AFTER_RECOVERY].sort(), c.restricted_after_recovery); assert.equal(RESTRICTION_S, c.restriction_s);
  for (const p of Object.keys(c.recovery_wait_s) as RecoveryPath[]) { assert.equal(RECOVERY[p].waitS, c.recovery_wait_s[p]); assert.equal(RECOVERY[p].approvals, c.recovery_approvals[p]); }
  assert.equal(PAYOUT_WAIT_S, c.payout_wait_s); assert.equal(DATA_REQUEST_DAYS, c.data_request_days); assert.equal(CLOSE_GRACE_DAYS, c.close_grace_days);
  assert.deepEqual(MAX_CONSENT_DAYS, c.max_consent_days); assert.deepEqual([...CONSENT_SCOPES].sort(), Object.keys(c.max_consent_days).sort());
  assert.deepEqual([...REGISTRATION_STEPS], c.registration_steps); assert.deepEqual([...PAGES], c.pages);
});
test("recovery, restriction, consent, standing-payment and payout vectors", () => {
  for (const v of V.recovery) { const r = { path: v.path as RecoveryPath, startedAt: v.started_at, approvals: v.approvals }; assert.equal(recoveryReady(r, v.now), v.ready, JSON.stringify(v)); assert.equal(recoveryReadyAt(r), v.ready_at); }
  for (const v of V.restriction) assert.equal(deviceCan(v.action, v.restricted_until, v.now), v.allowed, JSON.stringify(v));
  for (const v of V.consent) assert.equal(consentEnd(v.scope as ConsentScope, v.days, v.now), v.expires, JSON.stringify(v));
  for (const v of V.standing) assert.equal(standingChargeAllowed(v.cap_minor, v.amount_minor, v.revoked, v.provider_ready), v.allowed, JSON.stringify(v));
  for (const v of V.payout) assert.deepEqual(payoutChange(v.second_device_ok, v.now), { status: v.status, readyAt: v.ready_at });
  assert.ok(V.recovery.length >= 50);
});
test("sign-up order, recovery path choice, sessions bound to a site, alerts on new device or place", () => {
  assert.equal(nextSignUpStep({}), "username"); assert.equal(nextSignUpStep({ username: "grace.k" }), "contact");
  assert.equal(nextSignUpStep({ username: "grace.k", contactVerified: true }), "passkey");
  assert.equal(nextSignUpStep({ username: "grace.k", contactVerified: true, passkey: true }), "recovery_code");
  assert.equal(nextSignUpStep({ username: "grace.k", contactVerified: true, passkey: true, recoveryCodeConfirmed: true }), null);
  assert.equal(recoveryPath({ otherDevice: true, recoveryCode: true, smsOk: true }), "device");
  assert.equal(recoveryPath({ otherDevice: false, recoveryCode: true, smsOk: true }), "code");
  assert.equal(recoveryPath({ otherDevice: false, recoveryCode: false, smsOk: true }), "assisted");   // SMS alone is never enough
  assert.equal(recoveryPath({ otherDevice: false, recoveryCode: true, smsOk: false }), "assisted");
  const s = { site: "account" as const, expires: 1000 };
  assert.ok(sessionValid(s, "account", 999)); assert.ok(!sessionValid(s, "merchant", 999)); assert.ok(!sessionValid(s, "account", 1000));
  assert.deepEqual(signInAlertNeeded([], "phone", "Kigali"), { alert: false, newDevice: false, newPlace: false });
  assert.deepEqual(signInAlertNeeded([{ device: "phone", place: "Kigali" }], "laptop", "Kigali"), { alert: true, newDevice: true, newPlace: false });
  assert.ok(!exportAllowed(true, 2000, 1000)); assert.ok(exportAllowed(true, 2000, 2000)); assert.ok(!exportAllowed(false, 0, 2000));
});
test("consent states, Start a business never claims approval first, page paths", () => {
  const now = 1_800_000_000; const c = { scope: "lender" as const, grantee: "bank", purpose: "credit", expires: now + 10 * 86400 };
  assert.equal(consentState(c, now), "active"); assert.equal(consentState(c, now + 4 * 86400), "ending_soon"); assert.equal(consentState(c, now + 10 * 86400), "ended");
  assert.equal(consentState({ ...c, withdrawn: now }, now), "withdrawn");
  const steps: Record<RegistrationStep, boolean> = { profile: true, registration: true, tax_number: false, bank_account: true };
  assert.ok(!canSubmit(steps)); assert.ok(canSubmit({ ...steps, tax_number: true }));
  assert.equal(applicationStatus("submitted", "pending"), "submitted"); assert.equal(applicationStatus("submitted", "approved"), "approved"); assert.equal(applicationStatus("started", "approved"), "started");
  assert.equal(pagePath("overview"), "/"); assert.equal(pagePath("security"), "/security");
});
