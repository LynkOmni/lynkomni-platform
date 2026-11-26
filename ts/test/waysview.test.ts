import { test } from "node:test";
import assert from "node:assert/strict";
import { signUpHtml, signInHtml, recoverHtml, securityHtml, lostPhoneHtml, phoneOwnerHtml, waysStart, waysAct, waysInput } from "../src/waysview.js";
import type { WaysLook } from "../src/waysview.js";

let seed = 1;
const rnd = (n: number): number => { seed = (seed * 1103515245 + 12345) % 2147483648; return Math.floor((seed / 2147483648) * n); };
const look: WaysLook = { t: (k) => k, icon: () => "", when: (s) => String(s), num: (n) => String(n), btn: { primary: "p", secondary: "s" },
  phoneField: (id) => `<phone id="${id}">`, emailField: (id) => `<email id="${id}">`, codeField: (id) => `<code id="${id}">` };

test("sign-up goes through the ten steps in order, online only, with both codes", () => {
  const st = waysStart(0, rnd);
  st.online = false;
  assert.ok(/wy_offline_signup/.test(signUpHtml(look, st)));
  st.online = true;
  assert.ok(/wy_step_country/.test(signUpHtml(look, st)));
  waysAct(st, "wy:su:next:country", rnd);
  waysAct(st, "wy:su:next:username", rnd);
  assert.deepEqual(st.su.done, ["country"], "a username in the right form first");
  waysInput(st, "wy:username", "@Grace.K", false); waysAct(st, "wy:su:next:username", rnd);
  waysAct(st, "wy:su:next:age", rnd);
  assert.deepEqual(st.su.done, ["country", "username"], "the age must be confirmed first");
  st.now = Date.UTC(2026, 10, 26, 12) / 1000;
  assert.ok(!/18/.test(signUpHtml(look, st)), "the neutral age gate never says the age needed");
  const type = (y: string, m: string, d: string): void => { waysInput(st, "wy:birth_y", y, false); waysInput(st, "wy:birth_m", m, false); waysInput(st, "wy:birth_d", d, false); };
  type("1990", "2", "30"); waysAct(st, "wy:su:next:age", rnd);
  assert.ok(st.su.ageWrong && /wy_birth_invalid/.test(signUpHtml(look, st)), "a date that does not exist is explained");
  const kid = waysStart(st.now, rnd); kid.su.done = ["country", "username"];
  waysInput(kid, "wy:birth_y", String(new Date(st.now * 1000).getFullYear() - 10), false); waysInput(kid, "wy:birth_m", "1", false); waysInput(kid, "wy:birth_d", "1", false);
  waysAct(kid, "wy:su:next:age", rnd);
  assert.ok(kid.su.ageConfirm && /wy_birth_confirm/.test(signUpHtml(look, kid)), "Is this right? once before the check");
  waysAct(kid, "wy:su:age:yes", rnd);
  assert.deepEqual([kid.su.done, kid.su.birth.y, kid.su.ageRefusedAt], [["country", "username"], "", kid.now], "under age: the date is forgotten and the device is blocked");
  assert.ok(/wy_age_blocked/.test(signUpHtml(look, kid)) && !/wy:birth_y/.test(signUpHtml(look, kid)), "no retyping");
  kid.now += 30 * 86400;
  assert.ok(/wy_age_blocked/.test(signUpHtml(look, kid)), "no wait that ends by itself");
  waysAct(kid, "wy:su:age:id", rnd);
  assert.ok(/wy_age_id_sent/.test(signUpHtml(look, kid)), "only the partner's ID check can clear it");
  type("١٩٩٠", "5", "14"); waysAct(st, "wy:su:next:age", rnd);
  waysAct(st, "wy:su:age:change", rnd);
  assert.ok(!st.su.ageConfirm && st.su.birth.y === "1990", "Change it goes back to the boxes before confirming");
  waysAct(st, "wy:su:next:age", rnd); waysAct(st, "wy:su:age:yes", rnd);
  assert.deepEqual([st.su.ageOk, st.su.birth], [true, { d: "", m: "", y: "" }], "adult: only adult yes is kept, digits in any script");
  waysInput(st, "wy:legal", "R2D2", false); waysAct(st, "wy:su:next:legal_name", rnd);
  assert.ok(/wy_legal_no_digits/.test(signUpHtml(look, st)));
  waysInput(st, "wy:legal", "Grace Uwase", false); waysAct(st, "wy:su:next:legal_name", rnd);
  assert.ok(/<email id="wyEmail">/.test(signUpHtml(look, st)));
  for (const s of ["email", "email_code", "phone", "phone_code", "passkey"]) waysAct(st, `wy:su:next:${s}`, rnd);
  const rec = signUpHtml(look, st);
  assert.equal((rec.match(/<li>/g) ?? []).length, 10, "ten backup codes, shown once");
  assert.equal(waysAct(st, "wy:su:next:recovery", rnd).event, "AccountCreated");
});

test("sign-in starts with three choices in the owner's order, each opening only its own field", () => {
  const st = waysStart(0, rnd);
  const first = signInHtml(look, st);
  const at = (v: string): number => first.indexOf(`wy:si:via:${v}`);
  assert.ok(at("email") > 0 && at("email") < at("username") && at("username") < at("phone"), "email, username, phone");
  assert.ok(!/wyWho|wy_who_is/.test(first), "no box and no guessing note before a choice");
  waysAct(st, "wy:si:via:email", rnd);
  assert.ok(/<email id="wyWhoEmail">/.test(signInHtml(look, st)) && !/<phone/.test(signInHtml(look, st)), "email opens only the email field");
  waysAct(st, "wy:si:via:none", rnd);
  waysAct(st, "wy:si:via:phone", rnd);
  assert.ok(/<phone id="wyWhoPhone">/.test(signInHtml(look, st)), "phone opens the phone field");
  waysAct(st, "wy:si:via:username", rnd);
  const u = signInHtml(look, st);
  assert.ok(/handle-at/.test(u) && /data-act="wy:si:who"[^>]*disabled/.test(u), "username opens the @ box, Next waits for typing");
});

test("sign-in offers the person's ways strongest first and an extra check when unusual", () => {
  const st = waysStart(0, rnd);
  waysAct(st, "wy:si:who", rnd);
  const html = signInHtml(look, st);
  assert.ok(html.indexOf("wy_way_passkey") < html.indexOf("wy_way_email_code"));
  st.si.unusual = ["new_country"];
  waysAct(st, "wy:si:way:passkey", rnd);
  assert.equal(st.si.step, "extra");
  assert.ok(/wy_unusual_new_country/.test(signInHtml(look, st)));
});

test("the hub shows never-allowed ways, locks first when someone else is in, and waits", () => {
  const st = waysStart(1000, rnd);
  assert.ok(/wy_never_password/.test(recoverHtml(look, st)));
  waysAct(st, "wy:rc:problem:someone_else", rnd);
  assert.ok(/wy_lock_first/.test(recoverHtml(look, st)));
  waysAct(st, "wy:rc:lock", rnd);
  assert.ok(/wy_way_backup_code/.test(recoverHtml(look, st)));
  assert.equal(waysAct(st, "wy:rc:start:email_and_phone", rnd).event, "RecoveryStarted");
  assert.ok(/wy_waiting/.test(recoverHtml(look, st)));
  assert.equal(waysAct(st, "wy:rc:cancel", rnd).event, "RecoveryCancelled");
  assert.ok(/wy_lost_done/.test(lostPhoneHtml(look, st)));
});

test("the security page lists what is missing and each part works", () => {
  const st = waysStart(0, rnd);
  assert.ok(/wy_check_recovery_contacts/.test(securityHtml(look, st)));
  waysAct(st, "wy:sec:fix:recovery_contacts", rnd);
  assert.equal(st.sec.contacts.length, 3);
  waysAct(st, "wy:sec:authsetup", rnd);
  assert.ok(/wyAuthCode/.test(securityHtml(look, st)));
  waysInput(st, "wy:word", "ab", false);
  assert.ok(/wy_word_too_short/.test(securityHtml(look, st)));
});

test("the phone owner card: consent first, every answer with its fix, the SIM change wait, the ID document path", () => {
  const st = waysStart(1_800_000_000, (n) => 0);
  const html = (): string => phoneOwnerHtml(look, st);
  assert.ok(/disabled data-why/.test(html()), "Check my number waits for the consent tick");
  assert.deepEqual(waysAct(st, "wy:po:check", () => 0), {}, "nothing is sent without consent");
  waysInput(st, "wy:poconsent", "", true);
  assert.deepEqual(waysAct(st, "wy:po:check", () => 0), { event: "PhoneOwnerCheckRequested" });
  assert.ok(html().includes("wy_po_sent") && html().includes("wy:po:answer:match"));
  waysAct(st, "wy:po:answer:partial", () => 0);
  assert.equal(st.po.state, "partial"); assert.ok(html().includes("wy:po:fix:check_spelling") && html().includes("wy:po:fix:id_document"));
  waysAct(st, "wy:po:fix:check_spelling", () => 0); assert.equal(st.po.state, "none"); assert.equal(st.po.consent, false, "a new check asks for consent again");
  waysInput(st, "wy:poconsent", "", true); waysAct(st, "wy:po:check", () => 0); waysAct(st, "wy:po:answer:sim", () => 0);
  assert.equal(st.po.state, "waiting"); assert.ok(html().includes("wy_po_wait"));
  st.po.state = "sent"; waysAct(st, "wy:po:answer:no_match", () => 0); assert.equal(st.po.state, "failed");
  assert.deepEqual(waysAct(st, "wy:po:fix:id_document", () => 0), { event: "IdentityCheckRequested" });
  assert.equal(st.po.method, "id_document"); assert.ok(html().includes("wy_po_id_doc") && !html().includes("wy:po:answer:"), "the ID document answer comes only from the partner");
  st.po.state = "sent"; st.po.method = "network"; waysAct(st, "wy:po:answer:match", () => 0); assert.equal(st.po.state, "confirmed");
  assert.ok(html().includes("wy_po_free") && html().includes("wy_po_who"), "the card says LynkOmni never pays and who does");
  assert.ok(!html().includes("wy_po_act_recovery"), "getting back in never uses a paid check");
});

test("the checkup asks for a working way to reach you and explains the hold", () => {
  const st = waysStart(1_800_000_000, () => 0);
  st.sec.reach = false;
  const html = securityHtml(look, st);
  assert.ok(html.includes("wy_check_reachable") && html.includes("wy:sec:fix:reachable"));
  assert.ok(html.includes("wy_hold_note"), "LynkOmni holds a change instead of texting");
  waysAct(st, "wy:sec:fix:reachable", () => 0);
  assert.ok(!securityHtml(look, st).includes("wy_check_reachable"));
});
