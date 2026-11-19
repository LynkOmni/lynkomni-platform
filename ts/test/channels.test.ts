import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { USSD_MAX, chPage as page, chQPage, chQStart, chQStep, chSPage, chSStart, chSStep, parseQueueSms, parseSms, chStart as start, chStep as step } from "../src/channels.js";
import type { ChQCtx, ChQState, ChSState } from "../src/channels.js";
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

test("joining a queue by basic phone gives the same pages and actions as the Python reference", () => {
  const Q = V.queue;
  for (const steps of Q.sessions) {
    const ctx: ChQCtx = { ...Q.ctx, ticket: null }; let s: ChQState = chQStart();
    assert.deepEqual(chQPage(s, ctx), steps[0].page);
    for (const want of steps.slice(1)) {
      const [n, ends, action] = chQStep(s, want.input, ctx);
      s = n; ctx.ticket = want.ctx_ticket;                       // the caller's part: the cloud gave the ticket or moved it
      assert.deepEqual(chQPage(s, ctx), want.page, want.input);
      assert.equal(ends, want.ends); assert.deepEqual(action, want.action);
    }
  }
  assert.deepEqual(chQPage(chQStart(true), { ...Q.ctx, ticket: { ...Q.ticket, state: "called", counter: "Counter 1" } }), Q.called_page);
  for (const c of Q.sms) assert.deepEqual(parseQueueSms(c.text, Q.ctx.sections.length), c.parsed, c.text);
});

test("answering a survey by basic phone gives the same pages, ends and answers as the Python reference", () => {
  const S = V.survey;
  for (const steps of S.sessions) {
    let s: ChSState = chSStart();
    assert.deepEqual(chSPage(s, S.ctx), steps[0].page);
    for (const want of steps.slice(1)) {
      const [n, ends, action] = chSStep(s, want.input, S.ctx);
      s = n; assert.deepEqual(chSPage(s, S.ctx), want.page, want.input);
      assert.equal(ends, want.ends); assert.deepEqual(action, want.action);
    }
  }
});
