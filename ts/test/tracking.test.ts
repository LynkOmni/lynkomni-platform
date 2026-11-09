import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { Tracking, percent } from "../src/tracking.js";
import { REGISTER } from "../src/tracking.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/tracking.v1.json`, "utf8"));

test("every tracking scenario looks the same in TypeScript as in the Python reference", () => {
  for (const s of V.scenarios) {
    const t = new Tracking(REGISTER), got: unknown[] = [];
    for (const st of s.steps) {
      if (st.op === "event") t.apply(st.event, st.owner);
      else if (st.op === "progress") got.push({ progress_ok: t.setProgress(st.kind, st.record, st.share, st.eta) });
      else if (st.op === "state") t.feedState(st.kind, st.record, st.state, st.at);
      else got.push({ view: t.view(st.kind, st.record, st.audience, st.now) });
    }
    assert.deepEqual(JSON.parse(JSON.stringify(got)), s.expect, s.name);
  }
});

test("a customer subscription is kept and progress reads as a percent", () => {
  const t = new Tracking(REGISTER);
  t.apply({ type: "TrackingSubscribed", payload: { kind: "delivery", record: "d1", channel: "sms", lang: "fr" } });
  assert.deepEqual(t.subs.get("delivery|d1"), { channel: "sms", lang: "fr" });
  assert.equal(percent(0.45), 45); assert.equal(percent(null), null);
});

test("a tracker never reads a summary child as live (no NaN percent)", async () => {
  const { trackEta } = await import("../src/trackview.js");
  const tr = new Tracking(REGISTER), at = 1_800_000_000;
  tr.apply({ type: "OrderSentToKitchen", payload: { order_id: "o", lines: [{ line_no: 0 }] }, at }, "shop");
  tr.apply({ type: "DeliveryRequested", payload: { delivery_id: "d", order_id: "o" }, at: at + 60 }, "shop");
  tr.apply({ type: "DeliveryAccepted", payload: { delivery_id: "d", eta: "2027-01-15T08:30:00Z" }, at: at + 70 }, "shop");
  tr.apply({ type: "DeliveryPickedUp", payload: { delivery_id: "d" }, at: at + 90 }, "shop");
  tr.setProgress("delivery", "d", 0.55);
  const look = { t: (k: string, v?: Record<string, string | number>) => `${k}:${JSON.stringify(v ?? {})}`, esc: (s: string) => s, icon: () => "", time: (s: string) => s, chip: (s: string) => s };
  const merchant = trackEta(tr.view("order", "o", "merchant", at + 100)!, look);
  assert.equal(merchant, "");
  const customer = trackEta(tr.view("order", "o", "customer", at + 100)!, look);
  assert.ok(customer.includes('"pct":55') && !customer.includes("NaN"));
});
