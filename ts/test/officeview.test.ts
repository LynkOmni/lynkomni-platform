import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { OfficeView, OFFICE_PAGES, OFFICE_SERVICES } from "../src/officeview.js";
import { NAV } from "../src/navigation.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const EN: Record<string, string> = JSON.parse(readFileSync(`${root}/web/office/strings.en.json`, "utf8"));
const NV: Record<string, string> = JSON.parse(readFileSync(`${root}/web/navigation/strings.en.json`, "utf8"));
const t = (k: string, v: Record<string, string | number> = {}): string => (EN[k] ?? NV[k] ?? `MISSING:${k}`).replace(/\{(\w+)\}/g, (m, x: string) => (x in v ? String(v[x]) : m));
const view = (role = "owner", user = "u-owner") => new OfficeView({ t, money: (n) => `$${(n / 100).toFixed(2)}`, icon: () => "", chip: (s) => `[${s}]`, nav: NAV, role, user, today: "2026-11-20", taxBp: () => 1800 });

test("every office page draws with its words and no raw word name", () => {
  const v = view();
  for (const s of OFFICE_SERVICES) for (const p of OFFICE_PAGES[s]) {
    const html = v.draw(s, p.id);
    assert.ok(html.length > 100, p.id);
    assert.ok(!html.includes("MISSING:"), `${p.id}: ${html.match(/MISSING:\w+/)?.[0]}`);
    assert.ok(html.includes(EN["of_sample_note"]!), `${p.id} is labelled Sample`);
  }
});
test("the person who entered a bill never approves it", () => {
  const amina = view("manager", "u-amina");
  assert.ok(amina.draw("lynkacc", "acc_bills").includes(EN["of_not_own_bill"]!));
  amina.act("of:bill:b1:approve");
  assert.equal(amina.bills.find((b) => b.id === "b1")!.state, "awaiting_approval");
  const owner = view();
  owner.act("of:bill:b1:approve");
  assert.equal(owner.bills.find((b) => b.id === "b1")!.state, "approved");
  owner.act("of:bill:b2:pay_all");
  assert.equal(owner.bills.find((b) => b.id === "b2")!.state, "approved", "a payment counts only when the provider confirms");
});
test("a credit note never exceeds what is still owed and needs a reason", () => {
  const v = view();
  v.act("of:inv:LOINV-1002"); v.act("of:creditnote");
  v.input("of:credit:amount", "5000"); v.input("of:credit:reason", "Short delivery");
  assert.ok(v.draw("lynkinv", "inv_list").includes(EN["of_credit_too_much"]!));
  v.act("of:docredit");
  assert.equal(v.invoices.find((x) => x.id === "LOINV-1002")!.credited ?? 0, 0);
  v.input("of:credit:amount", "2200"); v.act("of:docredit");
  const inv = v.invoices.find((x) => x.id === "LOINV-1002")!;
  assert.equal(inv.credited, 220000);
  assert.equal(inv.state, "paid", "fully settled by payment and credit");
});
test("measures show nothing rather than a made-up number, and estimates are labelled", () => {
  const v = view();
  v.input("of:measure", "sales / (orders - orders)");
  assert.ok(v.draw("lynkstat", "stat_measures").includes(EN["of_measure_nothing"]!));
  v.input("of:measure", "open('x')");
  assert.ok(v.draw("lynkstat", "stat_measures").includes(EN["of_measure_invalid"]!));
  assert.ok(v.draw("lynkstat", "stat_whatif").includes(EN["of_estimate"]!));
  assert.ok(v.draw("lynkstat", "stat_public").includes(EN["of_hidden"]!), "a group below 5 is hidden");
});
test("closing waits for every step and a second person; merging keeps the oldest and can be undone", () => {
  const v = view();
  assert.ok(/disabled/.test(v.draw("lynkacc", "acc_close")));
  v.act("of:merge:LOCST-1001+LOCST-1004");
  assert.equal(v.merged?.kept, "LOCST-1001");
  v.act("of:unmerge");
  assert.equal(v.merged, null);
  v.act("of:deal:d1:won"); assert.equal(v.deals.find((d) => d.id === "d1")!.stage, "won");
  v.act("of:deal:d1:new"); assert.equal(v.deals.find((d) => d.id === "d1")!.stage, "won", "a won deal does not move back");
});
