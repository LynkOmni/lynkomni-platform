import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { driverFallback, driverState, ladderNext, needsInstall, conditionsFor, roleKind, roleStatus } from "../src/drivers.js";
import { DRIVERS } from "../src/drivers.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/drivers.v1.json`, "utf8"));

test("LynkDriver update states agree with the Python reference", () => {
  for (const c of V.cases) assert.deepEqual(driverState(DRIVERS, c.installed, c.now), c.state, `${c.installed} at ${c.now}`);
});
test("install prompt and virtual stand-ins agree", () => {
  for (const c of V.install) assert.deepEqual(needsInstall(DRIVERS, c.kinds, c.installed), c.needs);
  for (const [k, v] of Object.entries(V.fallback)) assert.equal(driverFallback(DRIVERS, k), v, k);
});
test("roles and the ladder agree with the Python reference (DRIVER UPDATE D18, D43)", () => {
  for (const [r, k] of Object.entries(V.roles)) assert.equal(roleKind(DRIVERS, r), k, r);
  for (const [st, n] of Object.entries(V.ladder)) assert.equal(ladderNext(DRIVERS, st), n, st);
});
test("each piece of hardware in each condition shows the same state and stand-in as the Python reference (D12, D13)", () => {
  for (const c of V.status) assert.deepEqual(roleStatus(DRIVERS, c.role, Object.keys(DRIVERS.conditions).find((k) => DRIVERS.conditions[k]!.state === c.state && DRIVERS.conditions[k]!.warning === c.warning)!), c, `${c.role} ${c.state}`);
});
test("each piece offers only the conditions it can have (D13)", () => {
  for (const [r, c] of Object.entries(V.conditions_for)) assert.deepEqual(conditionsFor(DRIVERS, r), c, r);
});
