import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { PAYMENT_METHODS, paymentOptions } from "../src/payments.js";

const pack = (c: string) => JSON.parse(readFileSync(`../contract/country-packs/${c}.json`, "utf8"));
const vendored = JSON.parse(readFileSync("../brand/vendor/brand.json", "utf8"));
const iconIds = new Set<string>(Object.keys(vendored.icons ?? {}));

test("Rwanda shows Visa, Mastercard, MTN MoMo, Airtel Money, bank transfer and QR, and no crypto", () => {
  assert.deepEqual(paymentOptions(pack("RW")).map((o) => o.label), ["Visa", "Mastercard", "MTN MoMo", "Airtel Money", "Bank transfer", "QR payment"]);
});

test("each country shows only its own methods", () => {
  assert.ok(paymentOptions(pack("KE")).some((o) => o.id === "mpesa"));
  assert.ok(!paymentOptions(pack("KE")).some((o) => o.id === "momo_mtn"));
  assert.ok(paymentOptions(pack("IN")).some((o) => o.id === "upi" && o.kind === "instant"));
  for (const c of ["AE", "GH", "IN", "KE", "NG", "RW", "TZ", "UG", "US", "XX"]) {
    const ids = paymentOptions(pack(c)).map((o) => o.id);
    assert.deepEqual(ids.slice(0, 2), ["visa", "mastercard"], c);
    assert.ok(!ids.includes("card") && !ids.includes("crypto"), c);
  }
});

test("crypto appears only when a country pack lists it", () => {
  assert.ok(paymentOptions({ card_networks: ["visa"], providers: ["bank_transfer", "crypto"] }).some((o) => o.id === "crypto"));
});

test("every method uses a LynkOmni icon that exists, and nothing claims to be official artwork", () => {
  for (const [id, m] of Object.entries(PAYMENT_METHODS)) assert.ok(iconIds.has(m.icon), `${id}: icon ${m.icon} missing`);
  assert.ok(paymentOptions(pack("RW")).every((o) => o.official === false));
});
