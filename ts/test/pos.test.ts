import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { Cart, PosError, change, deviceStatus, formatMoney, lineTotal, paymentPayload, paymentState, quickCash, receiptLines, salePayload, uuid7 } from "../src/pos.js";

const CONTRACT = JSON.parse(readFileSync("../contract/event-payloads.v1.json", "utf8"));
const UUID7 = new RegExp(CONTRACT.$defs.uuid7.pattern);
let n = 0;
const id = (): string => uuid7(1_760_000_000_000 + n++, (k) => Uint8Array.from({ length: k }, (_, i) => (i * 37 + n) % 256));
const rice = { id: id(), name: "Rice 1 kg", price: 1500, category: "food" };
const soap = { id: id(), name: "Soap bar", price: 500, category: "home" };

test("line totals round half up like the Python reference", () => {
  assert.equal(lineTotal(1000, 1500, 0), 1500);
  assert.equal(lineTotal(1500, 333, 0), 500);      // 499.5 rounds up
  assert.equal(lineTotal(2000, 500, 100), 900);
  assert.throws(() => lineTotal(0, 500, 0));
  assert.throws(() => lineTotal(1000, 100, 200));   // discount larger than the line
  assert.throws(() => lineTotal(1000, 1.5, 0));     // never a float price
});

test("the sale payload has the contract shape", () => {
  const c = new Cart(); c.add(rice); c.add(rice); c.add(soap);
  const s = salePayload(c, id(), "PT-1", "RWF");
  assert.ok(UUID7.test(s.sale_id));
  assert.equal(s.lines.length, 2);
  assert.equal(s.lines[0]?.quantity_milli, 2000);
  assert.equal(s.total, 3500);
  assert.equal(s.tax_mode, "none");
  const required: string[] = CONTRACT.events.SaleRecorded.payload.required;
  for (const k of required) assert.ok(k in s, k);
  for (const k of Object.keys(s)) assert.ok(k in CONTRACT.events.SaleRecorded.payload.properties, `extra field ${k}`);
  assert.throws(() => salePayload(new Cart(), id(), "PT-2", "RWF"), PosError);
  assert.throws(() => salePayload(c, id(), "pt 2", "RWF"), PosError);
});

test("a device never settles non-cash money", () => {
  assert.equal(deviceStatus("cash"), "cash_received");
  assert.equal(deviceStatus("mobile_money"), "pending_confirmation");
  assert.equal(deviceStatus("card"), "pending_confirmation");
  assert.equal(paymentPayload(id(), id(), "mobile_money", 3500).status, "pending_confirmation");
  assert.equal(paymentState("pending_confirmation", false), "queued");
  assert.equal(paymentState("pending_confirmation", true), "sent");
});

test("cash change and quick cash buttons", () => {
  assert.equal(change(3500, 5000), 1500);
  assert.throws(() => change(3500, 3000), PosError);
  assert.deepEqual(quickCash(3500, [500, 1000, 5000, 10000]), [3500, 4000, 5000, 10000]);
});

test("ids are UUIDv7", () => { for (let i = 0; i < 50; i++) assert.ok(UUID7.test(id())); });

test("money shows in the currency's own way without floats", () => {
  assert.ok(formatMoney(3500, "RWF", "en").includes("3,500"));
  assert.ok(formatMoney(123456, "USD", "en").includes("1,234.56"));
});

test("the receipt fits 58 mm paper and says it is not a tax receipt", () => {
  const c = new Cart(); c.add({ ...rice, name: "A very long product name that will not fit" }); c.add(soap);
  const s = salePayload(c, id(), "PT-9", "RWF");
  const lines = receiptLines({ shop: "Sample shop", sale: s, payments: [paymentPayload(id(), s.sale_id, "cash", s.total)], tendered: 5000, when: "06 Nov 2026 16:00",
    money: (m) => formatMoney(m, "RWF", "en"), words: {} });
  for (const l of lines) assert.ok(l.length <= 32, l);
  assert.ok(lines.includes(lines.find((l) => l.includes("Not a tax receipt")) ?? ""));
  assert.ok(lines.some((l) => l.startsWith("Change")));
});
