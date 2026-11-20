import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { mayMake, invMove, labelWord, dueDate, totals, creditCheck, needsApproval, reminderDue, lateFee, ageing, applyPayment, instalments, prorate,
  usage, stages, retainerDraw, toBase, cashRound, eInvoiceRequired, keepYears, languagesOk } from "../src/invoices.js";
import { INVOICES as I } from "../src/invoices.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/invoices.v1.json`, "utf8"));
const P = V.packs;

test("documents, states, labels and due dates agree with the Python reference (OFFICE UPDATE 66.3)", () => {
  for (const c of V.make) assert.equal(mayMake(I, c.from, c.to, P[c.pack]), c.expect, JSON.stringify(c));
  for (const c of V.moves) assert.equal(invMove(I, c.state, c.action), c.expect, JSON.stringify(c));
  for (const [p, want] of Object.entries(V.labels)) assert.equal(labelWord(P[p]), want, p);
  for (const c of V.due) assert.equal(dueDate(I, c.issued, c.term ?? undefined), c.expect, JSON.stringify(c));
});
test("totals, the credit warning and approval before sending", () => {
  for (const c of V.totals) assert.deepEqual(totals(c.lines, c.taxes, c.included, c.bp), c.expect, JSON.stringify(c));
  for (const c of V.credit) assert.deepEqual(creditCheck(c.limit, c.open, c.new), c.expect);
  for (const c of V.approval) assert.equal(needsApproval(I, c.total, c.over, c.prep, c.named), c.expect, JSON.stringify(c));
});
test("reminders, late fees only by law, ageing, paying several and instalments", () => {
  for (const c of V.reminders) assert.equal(reminderDue(I, c.due, c.today, c.sent, c.promise, c.disputed), c.expect, JSON.stringify(c));
  for (const c of V.fees) assert.deepEqual(lateFee(c.amount, c.days, P[c.pack], c.owner), c.expect, JSON.stringify(c));
  assert.deepEqual(ageing(I, V.ageing.items, V.ageing.today), V.ageing.expect);
  for (const c of V.pay) assert.deepEqual(applyPayment(c.amount, V.ageing.items, c.order), c.expect, JSON.stringify(c));
  for (const c of V.instalments) assert.deepEqual(instalments(I, c.t, c.n, c.start, c.every), c.expect, JSON.stringify(c));
});
test("ways to bill, currency, rounding, e-invoices, keeping and languages", () => {
  for (const c of V.prorate) assert.equal(prorate(c.o, c.n, c.p, c.l), c.expect);
  for (const c of V.usage) assert.equal(usage(c.qty, c.bands, c.mode), c.expect, JSON.stringify(c));
  for (const c of V.stages) assert.deepEqual(stages(c.t, c.s), c.expect);
  for (const c of V.retainer) assert.deepEqual(retainerDraw(c.b, c.a), c.expect);
  for (const c of V.base) assert.equal(toBase(c.a, c.n, c.d), c.expect);
  for (const c of V.cash) assert.deepEqual(cashRound(c.a, c.s), c.expect);
  for (const [p, want] of Object.entries(V.einvoice)) assert.equal(eInvoiceRequired(P[p]), want, p);
  for (const [p, want] of Object.entries(V.keep)) assert.equal(keepYears(I, P[p]), want, p);
  for (const c of V.languages) assert.equal(languagesOk(I, c.l), c.expect);
});
