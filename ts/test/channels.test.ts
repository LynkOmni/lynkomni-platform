import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { USSD_MAX, chPage as page, parseSms, chStart as start, chStep as step } from "../src/channels.js";
import type { ChState } from "../src/channels.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/channels.v1.json`, "utf8"));

test("every USSD, text and voice session gives the same pages and the same sale as the Python reference", () => {
  assert.equal(USSD_MAX, V.ussd_max);
  const ctx = { ...V.ctx, pinOk: (t: string) => t === V.pin };
  for (const steps of V.sessions) {
    let s: ChState = start();
    assert.deepEqual(page(s, V.ctx), steps[0].page);
    for (const want of steps.slice(1)) {
      const [n, ends, action] = step(s, want.input, ctx);
      s = n;
      assert.deepEqual(page(s, V.ctx), want.page, want.input);
      assert.equal(ends, want.ends); assert.deepEqual(action, want.action);
    }
  }
});

test("text-message commands parse the same way", () => {
  for (const c of V.sms) assert.deepEqual(parseSms(c.text), c.parsed, c.text);
});
