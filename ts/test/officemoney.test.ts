import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { balances, depositLeft, match, costs, payouts } from "../src/officemoney.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/office-money.v1.json`, "utf8"));
const attempt = (f: () => unknown) => { try { return { value: f() }; } catch { return { error: true }; } };

test("gift card and store credit balances and deposits agree with the Python reference (67.2)", () => {
  for (const c of V.balances) assert.deepEqual(attempt(() => balances(c.a)), c.expect, JSON.stringify(c.a));
  for (const c of V.deposit) assert.deepEqual(attempt(() => depositLeft(c.a[0], c.a[1])), c.expect, JSON.stringify(c.a));
});
test("matching, payment costs and payouts agree with the Python reference (67.8)", () => {
  for (const c of V.match) assert.deepEqual(attempt(() => match(c.a[0], c.a[1], c.a[2])), c.expect, JSON.stringify(c.a[2]));
  for (const c of V.costs) assert.deepEqual(attempt(() => costs(c.a)), c.expect, JSON.stringify(c.a).slice(0, 80));
  for (const c of V.payouts) assert.deepEqual(attempt(() => payouts(c.a[0], c.a[1], c.a[2])), c.expect, c.a[2]);
});
