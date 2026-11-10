import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { driverFallback, driverState, needsInstall } from "../src/drivers.js";
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
