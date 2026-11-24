import { test } from "node:test";
import assert from "node:assert/strict";
import { publicId, randomBelow } from "../src/emulator.js";
import { pairCode } from "../src/queuedesk.js";
import { CODE_LENGTH } from "../src/queue.js";

test("randomBelow is fair and in range (CodeQL: no bias from a remainder)", () => {
  const counts = new Array(10).fill(0);
  for (let i = 0; i < 20000; i++) { const v = randomBelow(10); assert.ok(Number.isInteger(v) && v >= 0 && v < 10); counts[v]++; }
  for (const c of counts) assert.ok(c > 1700 && c < 2300, String(counts));   // about 2,000 each
  assert.equal(randomBelow(1), 0);
  assert.ok(randomBelow(2 ** 32) < 2 ** 32);
  for (const bad of [0, -1, 1.5, 2 ** 32 + 1]) assert.throws(() => randomBelow(bad));
});

test("public ids and pairing codes still have their one format", () => {
  for (let i = 0; i < 50; i++) {
    assert.match(publicId("SAL"), /^LOSAL-\d{4}-\d{4}-\d{4}$/);
    assert.equal(pairCode().length, CODE_LENGTH);
  }
});
