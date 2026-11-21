import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { levelBps, partBps, quote, aboveMidBps, costOut } from "../src/exchange.js";
import { LEVELS } from "../src/exchange.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/exchange.v1.json`, "utf8"));
const attempt = (f: () => unknown) => { try { return { value: f() }; } catch { return { error: true }; } };

test("levels, parts and the one full price agree with the Python reference (EXCHANGE UPDATE 65)", () => {
  for (const c of V.levels) assert.deepEqual(attempt(() => levelBps(LEVELS, c.v)), c.expect, String(c.v));
  for (const c of V.part) assert.deepEqual(attempt(() => partBps(c.t, LEVELS, c.v)), c.expect, JSON.stringify(c));
  for (const c of V.quote) assert.deepEqual(attempt(() => quote(...(c.a as [number, number, number, number]))), c.expect, JSON.stringify(c.a));
});
test("the distance from the mid-market rate and the cost of money spent agree with the Python reference", () => {
  for (const c of V.mid) assert.deepEqual(attempt(() => aboveMidBps(...(c.a as [number, number, number, number]))), c.expect, JSON.stringify(c.a));
  for (const c of V.cost) assert.deepEqual(attempt(() => costOut(...(c.a as [number, number, number]))), c.expect, JSON.stringify(c.a));
});
