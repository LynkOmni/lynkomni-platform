import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resendWait } from "../src/codefield.js";
import { phoneRules, phoneClean, phoneCheck, phoneAccept, phoneGroups, phoneSample, phoneInternational, phoneLengths, phoneReadPasted, type PhoneRules } from "../src/phone.js";
import { emailCheck } from "../src/emailfield.js";
import { EMAIL_DOMAINS } from "../src/phone.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/phone.v1.json`, "utf8"));
const R = (c: string): PhoneRules => phoneRules(V.packs[c] as PhoneRules | null);

test("phone checks agree with the Python reference (section 4C point 1)", () => {
  for (const c of V.cases) {
    const r = R(c.country);
    if ("typed" in c) {
      const d = phoneClean(r, c.typed);
      assert.equal(d, c.clean, JSON.stringify(c));
      assert.equal(phoneCheck(r, d, c.mobile).state, c.state, JSON.stringify(c));
      assert.equal(phoneCheck(r, d, c.mobile, true).state, c.submit, JSON.stringify(c));
      assert.equal(phoneAccept(r, d, c.mobile), c.accept, JSON.stringify(c));
      assert.equal(phoneGroups(r, phoneAccept(r, d, c.mobile), c.mobile), c.groups, JSON.stringify(c));
    } else {
      assert.deepEqual({ mobile: phoneSample(r, true), any: phoneSample(r, false) }, c.sample, c.country);
      assert.deepEqual(phoneLengths(r.mobile.lengths), c.lengths, c.country);
      assert.equal(phoneInternational(r, r.mobile.sample || "123456"), c.international, c.country);
    }
  }
});

test("pasted numbers with a dialling code switch the country", () => {
  for (const c of V.pasted) assert.deepEqual(phoneReadPasted(c.text, c.current, R, V.codes), c.result, JSON.stringify(c));
});

test("email checks agree with the Python reference", () => {
  for (const c of V.emails) assert.deepEqual(emailCheck(EMAIL_DOMAINS, c.text, c.deep), c.result, JSON.stringify(c));
});

test("the wait before another code agrees with the Python reference", () => {
  for (const c of V.waits) assert.equal(resendWait(c.sent, c.now), c.wait, JSON.stringify(c));
});

test("the phone chooser lists only countries with a dialling code and starts on the device's country (owner, 2026-11-25)", async () => {
  const { dialCountries, deviceCountry } = await import("../src/fields.js");
  const ph = (code: string) => ({ code, prefix: "", main: true, mobile: { lengths: [9], groups: [3, 3, 3], sample: "612345678" } }) as unknown as PhoneRules;
  const ctx = { t: (k: string) => k, lang: "en", countryName: (c: string) => c, packOrder: ["XX", "AQ", "CM", "FR", "GA"],
    packs: { XX: { name: "Sample", sample: true, tz: "UTC", ph: ph("999") }, AQ: { name: "Antarctica", tz: "Antarctica/McMurdo", ph: null },
      CM: { name: "Cameroon", tz: "Africa/Douala", ph: ph("237") }, FR: { name: "France", tz: "Europe/Paris", ph: ph("33") }, GA: { name: "Gabon", tz: "Africa/Libreville", ph: ph("241") } } };
  assert.deepEqual(dialCountries(ctx), ["CM", "FR", "GA"]);                    // no flag without a code, never the sample
  assert.equal(deviceCountry(ctx, "Africa/Douala", ["fr-FR"]), "CM");          // the time zone decides
  assert.equal(deviceCountry(ctx, "America/Chicago", ["fr-GA", "en"]), "GA");  // else a language's region
  assert.equal(deviceCountry(ctx, "", []), "CM");                              // else the first country with numbers
});
