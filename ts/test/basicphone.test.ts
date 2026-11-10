import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { bpPage, bpStart, bpStep, textNotification } from "../src/basicphone.js";
import type { BpCtx, BpRules, PinCheck } from "../src/basicphone.js";
import { check } from "../src/usernames.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/basicphone.v1.json`, "utf8"));

test("every basic-phone session gives the pages, ends and actions of identity/basic_phone.py", () => {
  const ctx = V.ctx as BpCtx;
  const rules: BpRules = {
    pinCheck: (t): PinCheck => (t === "LOCKED" ? "locked" : t === V.pin ? "ok" : ["wrong", 9]),
    usernameCheck: (u) => { const r = check(u); return r.ok ? null : r.reason; },
    taken: (u) => (V.taken as string[]).includes(u),
  };
  for (const steps of V.sessions) {
    let s = bpStart();
    assert.deepEqual(bpPage(s, ctx), steps[0].page);
    for (const st of steps.slice(1)) {
      const [next, ends, action] = bpStep(s, st.input, ctx, rules);
      s = next;
      assert.equal(s.screen, st.screen, `after ${st.input}`);
      assert.deepEqual(bpPage(s, ctx), st.page, `page after ${st.input}`);
      assert.equal(ends, st.ends); assert.deepEqual(action, st.action);
    }
  }
  for (const [u, why] of Object.entries(V.username_checks as Record<string, string | null>)) { const r = check(u); assert.equal(r.ok ? null : r.reason, why, u); }
});

test("a notification as a text message is the same in both languages of the code", () => {
  const words = (k: string) => ({ msg_record: "Record number:", bp_read_more: "Dial the LynkOmni menu and choose Messages to read more." }[k] ?? k);
  for (const c of V.texts) assert.equal(textNotification(c.title, c.record, words), c.text);
});
