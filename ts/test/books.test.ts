import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { rateBp, roundDiv, split, allocate, taxLine, billMove, approvers, mayApprove, match3, earlyDiscount, mileage, cardMatch, depreciation, loanSchedule, loanLines,
  disposal, repeatDates, reversalDate, mayPost, twoPerson, closeMissing, bankMatch, trialBalance, statements, yearEndLines, cashFlow, equityChanges, revalue,
  stockCost, consolidate, mirror, budgetVsActual, fundSpendOk, dimsOk, entityTools, type Line } from "../src/books.js";
import { BOOKS, CHART } from "../src/books.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/books.v1.json`, "utf8"));
const lines = (ls: unknown[]): Line[] => ls as Line[];

test("integer arithmetic and taxes agree with the Python reference (OFFICE UPDATE 66.2)", () => {
  for (const c of V.round_div) assert.equal(roundDiv(c.n, c.d), c.expect, JSON.stringify(c));
  for (const c of V.split) assert.deepEqual(split(c.t, c.p), c.expect, JSON.stringify(c));
  for (const [r, want] of Object.entries(V.rate_bp)) assert.equal(rateBp(r), want, r);
  for (const c of V.allocate) assert.deepEqual(allocate(c.t, c.w), c.expect, JSON.stringify(c));
  for (const c of V.tax) assert.deepEqual(taxLine(c.amount, c.taxes, c.included), c.expect, JSON.stringify(c));
});
test("bills: moves, approvers, three-way matching, early discount", () => {
  for (const c of V.moves) assert.equal(billMove(BOOKS, c.state, c.action), c.expect, JSON.stringify(c));
  for (const c of V.approvers) assert.deepEqual(approvers(BOOKS, c.amount), c.expect);
  for (const c of V.may_approve) assert.equal(mayApprove(c.p, c.a), c.expect);
  for (const c of V.match) assert.deepEqual(match3(V.po, V.received, c.bill, c.tol), c.expect, JSON.stringify(c.bill));
  for (const c of V.early) assert.equal(earlyDiscount(c.a, c.bp, c.w, c.after), c.expect);
});
test("staff spending, assets and loans", () => {
  for (const c of V.mileage) assert.equal(mileage(c.km, c.rate), c.expect);
  assert.deepEqual(cardMatch(BOOKS, V.card.spends, V.card.receipts), V.card.expect);
  for (const c of V.depreciation) assert.deepEqual(depreciation(c.c, c.r, c.y, c.m, c.bp), c.expect, JSON.stringify(c));
  for (const c of V.loans) assert.deepEqual(loanSchedule(c.p, c.bp, c.n), c.expect, JSON.stringify([c.p, c.bp, c.n]));
  for (const c of V.loan_lines) assert.deepEqual(loanLines(c.row, c.m), c.expect);
  for (const c of V.disposal) assert.deepEqual(disposal(c.c, c.s, c.p, c.m), c.expect);
});
test("dates, closing, two people and the bank", () => {
  for (const c of V.dates) assert.deepEqual(repeatDates(c.start, c.every, c.count), c.expect, JSON.stringify(c));
  for (const [d, want] of Object.entries(V.reversal)) assert.equal(reversalDate(d), want);
  for (const c of V.may_post) assert.equal(mayPost(c.d, c.lock), c.expect);
  for (const c of V.two_person) assert.deepEqual(twoPerson(BOOKS, c.k, c.p, c.a), c.expect);
  for (const c of V.close) assert.deepEqual(closeMissing(BOOKS, c.done), c.expect);
  assert.deepEqual(bankMatch(BOOKS, V.bank.lines, V.bank.items), V.bank.expect);
});
test("statements, revaluation, stock value and group books", () => {
  const ents = V.entries.map((e: { lines: unknown[] }) => ({ lines: lines(e.lines) }));
  assert.deepEqual(trialBalance(CHART, ents), V.tb);
  assert.deepEqual(statements(CHART, V.tb), V.statements);
  assert.deepEqual(yearEndLines(BOOKS, CHART, V.tb), V.year_end);
  assert.deepEqual(cashFlow(BOOKS, CHART, ents), V.cash_flow);
  assert.deepEqual(equityChanges(CHART, 0, ents), V.equity);
  for (const c of V.revalue) assert.deepEqual(revalue(c.items, c.num, c.den), c.expect);
  for (const c of V.stock) assert.deepEqual(stockCost(c.moves, c.method), c.expect, c.method);
  for (const c of V.group) assert.deepEqual(consolidate(BOOKS, CHART, c.entities, c.ic), c.expect);
  const m = mirror(V.mirror.invoice);
  assert.equal(m.supplier, "hold"); assert.equal(m.entity, "sub"); assert.equal(m.state, "awaiting_approval");
});
test("splitting the books and the tools for each kind of entity", () => {
  for (const c of V.budget) assert.deepEqual(budgetVsActual(c.b, c.a), c.expect);
  for (const c of V.funds) assert.equal(fundSpendOk(c.f, c.p), c.expect);
  for (const c of V.dims) assert.equal(dimsOk(BOOKS, c.d), c.expect);
  for (const [k, want] of Object.entries(V.tools)) assert.deepEqual(entityTools(BOOKS, k), want);
});
