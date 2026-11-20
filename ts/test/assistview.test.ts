import { test } from "node:test";
import assert from "node:assert/strict";
import { guard, work } from "../src/assisttrust.js";
import { TRUST } from "../src/assisttrust.generated.js";
import { answerHtml, previewHtml, controlsHtml, stoppedHtml, askButtonHtml, warningLineHtml, type LaLook } from "../src/assistview.js";

const look: LaLook = { t: (k, v) => (v ? `${k}${JSON.stringify(v)}` : k), icon: (id) => `<i data-ic="${id}"></i>`, money: (m) => String(m) };
const has = (s: string, part: string): void => assert.ok(s.includes(part), `missing ${part}`);
const hasNot = (s: string, part: string): void => assert.ok(!s.includes(part), `should not have ${part}`);

test("an answer names LynkAssist, says how sure in words and opens its working (ASSIST UPDATE 75)", () => {
  const w = work([{ minor: 1500, currency: "USD" }, { minor: 250, currency: "USD" }]);
  const h = answerHtml(TRUST, look, { title: "Sales", value: "17.50", sure: "certain", working: { w, parts: [{ label: "R1", minor: 1500 }, { label: "R2", minor: 250 }] }, notAdviser: true });
  has(h, "at_assist_name"); has(h, "at_sure_certain"); has(h, "at-working"); has(h, "at_checked_twice"); has(h, "at_not_adviser");
  const bad = answerHtml(TRUST, look, { title: "Sales", sure: "not_sure", working: { w: work([{ minor: 1, currency: "USD" }, { minor: 1, currency: "EUR" }]), parts: [] } });
  has(bad, "at_not_shown"); hasNot(bad, "at-working");
  assert.ok(answerHtml(TRUST, look, { title: "<b>", sure: "dont_know" }).includes("&lt;b&gt;"), "text is escaped");
});

test("a preview shows a sample for many changes and the second approver for a big one", () => {
  const rows = Array.from({ length: 240 }, (_, i) => ({ label: `P${i}`, before: "1", after: "2" }));
  const g = guard(TRUST, { register_needs: "confirm", register_run: false, cls: "B", confirmed: true, items: 240, asker: "owner" });
  const h = previewHtml(look, { action: "Round", rows, items: 240, cost: "none", told: "team", guard: g, approverRole: "manager" });
  assert.equal((h.match(/<tr><th scope="row">/g) ?? []).length, 5, "a sample of 5");
  has(h, "at_sample"); has(h, 'data-act="la:askapprover"'); hasNot(h, 'data-act="la:confirm"'); has(h, "at_role_manager");
  const one = guard(TRUST, { register_needs: "confirm", register_run: false, cls: "B", confirmed: true, items: 1, practice: true });
  const p = previewHtml(look, { action: "Fix", rows: rows.slice(0, 1), items: 1, cost: "none", told: "nobody", guard: one, practice: true });
  has(p, "at_confirm_practice"); has(p, "at_practice_note"); hasNot(p, "at_sample");
});

test("stops, warnings, Ask about this and the owner's controls", () => {
  has(stoppedHtml(look, "paused"), "at_stopped_paused");
  const w = warningLineHtml(look, "at_w_price_below_cost", { cost: "5" }, "price_below_cost");
  has(w, 'data-act="la:fix:price_below_cost"'); has(w, 'data-act="la:fine:price_below_cost"');
  const a = askButtonHtml(look, "number", "today_sales");
  has(a, 'data-act="la:ask:number:today_sales"'); has(a, "aria-label=");
  const base = { paused: false, roles: ["manager"], areas: ["stock"], off: new Set(["manager:stock"]), approverAmount: "500", pace: "normal", memoryOn: false,
    memory: [{ id: "m1", text: "Tuesdays" }], draft: "", areaLabel: (x: string) => x };
  const staff = controlsHtml(TRUST, look, { ...base, owner: false });
  has(staff, 'data-in="la:pause" disabled'); has(staff, 'data-in="la:role:manager:stock" disabled');
  const own = controlsHtml(TRUST, look, { ...base, owner: true });
  hasNot(own, 'data-in="la:pause" disabled'); has(own, 'data-act="la:forget:m1"'); has(own, 'aria-pressed="true"');
  has(own, 'data-act="la:remember" disabled');
  hasNot(own, 'data-in="la:role:manager:stock" checked');
});
