import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { mayShow, counts, slotHtml } from "../src/ads.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/ads.v1.json`, "utf8"));
const attempt = (f: () => unknown) => { try { return { value: f() }; } catch { return { error: true }; } };

test("the device-side ad rules agree with the Python reference (ADS UPDATE 79)", () => {
  for (const c of V.may_show) { const { place, ...ctx } = c.a; assert.deepEqual(attempt(() => mayShow(place, ctx)), c.expect, JSON.stringify(c.a)); }
  for (const c of V.counts) assert.equal(counts(c.a[0], c.a[1]), c.expect, JSON.stringify(c.a));
});
test("no ad leaves no gap; an ad is always labelled with why and report", () => {
  const L = { t: (k: string) => k, esc: (s: string) => s, icon: () => "" };
  assert.equal(slotHtml("pos_idle", null, L), "");
  const h = slotHtml("pos_idle", { id: "a1", text: "Bread", sample: true }, L);
  for (const k of ["ad_sponsored", "ad_sample", "ad:why:a1", "ad:report:a1"]) assert.ok(h.includes(k), k);
});
