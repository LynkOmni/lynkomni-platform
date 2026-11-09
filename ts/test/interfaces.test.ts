import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { chooseInterface, safeToSwitch, browserFacts } from "../src/interfaces.js";
import type { Facts } from "../src/interfaces.js";
import { DEVICES } from "../src/interfaces.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/interfaces.v1.json`, "utf8"));

test("every combination of device facts gets the same interface in TypeScript as in the Python reference", () => {
  for (const r of V.grid) {
    const f: Facts = { os_class: r[0], touch: !!r[1], fine: !!r[2], hover: !!r[3], keyboard: !!r[4], remote: !!r[5], width: r[6], last_input: r[7] };
    const c = chooseInterface(DEVICES, f);
    assert.deepEqual([c.interface, c.rule], [r[8], r[9]], JSON.stringify(f));
  }
  for (const n of V.named) assert.deepEqual(chooseInterface(DEVICES, n.facts), n.expect, JSON.stringify(n.facts));
});
test("never switch during a payment, count or signature; browser facts are capabilities only", () => {
  assert.equal(safeToSwitch("payment"), false); assert.equal(safeToSwitch(null), true);
  const fake = { matchMedia: (q: string) => ({ matches: q.includes("coarse") }), innerWidth: 390, innerHeight: 800, navigator: { maxTouchPoints: 5 } };
  assert.deepEqual(chooseInterface(DEVICES, browserFacts(fake)).interface, "phone.touch");
});
