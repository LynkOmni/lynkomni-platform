import { test } from "node:test";
import assert from "node:assert/strict";
import { SHAPES, TIMING, loadingPhase, holdFor, skeletonHtml, hintFor, hintAttr, FORMAT_HINTS } from "../src/placeholder.js";

test("cached content stays; no flash before the delay; a note when slow", () => {
  assert.equal(loadingPhase(5000, true), "nothing");
  assert.equal(loadingPhase(TIMING.SHOW_AFTER - 1, false), "nothing");
  assert.equal(loadingPhase(TIMING.SHOW_AFTER, false), "skeleton");
  assert.equal(loadingPhase(TIMING.SLOW_AFTER, false), "slow");
  assert.equal(holdFor(1000, 1100), TIMING.MIN_SHOW - 100);
  assert.equal(holdFor(1000, 5000), 0);
});

test("every shape is one polite status with hidden bars and a bounded count", () => {
  for (const s of SHAPES) {
    const h = skeletonHtml(s, "Loading", 50);
    assert.equal((h.match(/role="status"/g) ?? []).length, 1, s);
    assert.ok(/aria-busy="true"/.test(h));
    assert.ok(/aria-label="Loading"/.test(h));
    assert.ok(!/<span class="skel [^"]*"(?! aria-hidden)/.test(h), `${s}: every bar is hidden from screen readers`);
    assert.ok((h.match(/class="skel /g) ?? []).length <= 12 * 4 + 4, `${s}: at most 12 repeats`);
  }
});

test("format hints need no words; word hints come from the page's words; sensitive fields get none", () => {
  const t = (k: string) => `T:${k}`;
  assert.equal(hintFor("amount", t), "0");
  assert.equal(hintFor("email", t), FORMAT_HINTS.email);
  assert.equal(hintFor("search", t), "T:hint_search");
  assert.equal(hintAttr(null, t), "");
  assert.ok(/placeholder="T:hint_note"/.test(hintAttr("note", t)));
});

test("number hints use the reader's digits", () => {
  const t = (k: string) => k;
  assert.equal(hintFor("amount", t, "en"), "0");
  assert.equal(hintFor("amount", t, "ar-EG"), new Intl.NumberFormat("ar-EG").format(0));
  assert.equal(hintFor("count", t, "bn"), new Intl.NumberFormat("bn").format(0));
  assert.equal(hintFor("amount", t), "0");
});
