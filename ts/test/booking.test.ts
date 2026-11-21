import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { commission, busyForecast, emptyHours, noShowRate } from "../src/booking.js";
import { COMMISSION as R } from "../src/booking.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/booking.v1.json`, "utf8"));
const attempt = (f: () => unknown) => { try { return { value: f() }; } catch { return { error: true }; } };

test("commission agrees with the Python reference and the locked rule (BOOKING UPDATE 64)", () => {
  for (const c of V.commission) assert.deepEqual(attempt(() => commission(R, c.k, c.s, c.a, c.f, c.g, c.t, c.fixed ?? {})), c.expect, JSON.stringify(c));
  assert.equal(commission(R, "stay", "own_link", 100000), 0, "nothing on the business's own customers");
});
test("the busy-time forecast, empty hours and no-show rate agree with the Python reference", () => {
  for (const c of V.forecast) assert.deepEqual(attempt(() => busyForecast(c.b, c.w)), c.expect, JSON.stringify(c.w));
  for (const c of V.empty) assert.deepEqual(emptyHours(c.c, c.b), c.expect);
  for (const c of V.noshow) assert.deepEqual(attempt(() => noShowRate(c.c, c.n)), c.expect, JSON.stringify(c));
  assert.equal(busyForecast([], 1).estimate, true);
});
