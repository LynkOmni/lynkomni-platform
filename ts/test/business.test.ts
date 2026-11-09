import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { BUSINESS_SECTIONS, BUSINESS_TYPES, FAST_CHECKOUT, HANDHELD_TILES, IDLE_LOCK_S, PROOF_WARNING_KEY, RECEIPT_CHANNELS, SETUP_STEPS, SYNC_ORDER, TABS, TILL_ACTIONS,
  homeCards, mayShowConfirmed, nextSetupStep, parseVoice, practiceLabel, receiptChannels, secondCurrency, syncOrder, webRule, within } from "../src/business.js";
import type { BusinessType } from "../src/business.js";
import { AGENT_SERVICES, AGENT_STATES, COLLECTION_KINDS, FINANCE_PRODUCTS, LOW_FLOAT_RATIO, cashDifference, combinedLimits, commission, floatForecastDays, limitCheck, lowFloat, matchStatement, mayHandOverCash, mayStart } from "../src/agent.js";
import { DELIVERY_SHARE_CENTS, KITCHEN_WITHOUT_SCREEN, chargedWhen, deliveryEntitlement, groupOutcome, kitchenOutput, kitchenQueue, lynkomniShareCents, mayAddRider, mayCloseTable, mayOpenGroup, mayOpenTable,
  mayRequestPartnerDelivery, nextDeliveryStep, pickQuotes, restaurantLimits, splitNeedsAtLeast, tipShareForLynkOmni } from "../src/restaurant.js";

const root = `${process.cwd()}/..`;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/pos.v1.json`, "utf8"));

test("constants agree with the Python reference", () => {
  const c = V.constants;
  assert.deepEqual([...BUSINESS_TYPES], c.business_types);
  for (const t of c.business_types as BusinessType[]) assert.deepEqual([...TABS[t]], c.tabs[t]);
  assert.deepEqual([...SETUP_STEPS], c.setup_steps); assert.deepEqual([...HANDHELD_TILES], c.handheld_tiles); assert.deepEqual([...FAST_CHECKOUT], c.fast_checkout);
  assert.deepEqual([...RECEIPT_CHANNELS], c.receipt_channels); assert.deepEqual([...BUSINESS_SECTIONS], c.business_sections); assert.deepEqual([...TILL_ACTIONS], c.till_actions);
  assert.deepEqual([...AGENT_SERVICES], c.agent_services); assert.deepEqual([...COLLECTION_KINDS], c.collection_kinds); assert.deepEqual([...FINANCE_PRODUCTS], c.finance_products); assert.deepEqual([...AGENT_STATES], c.agent_states);
  assert.equal(LOW_FLOAT_RATIO, c.low_float_ratio); assert.equal(IDLE_LOCK_S, c.idle_lock_s); assert.deepEqual([...SYNC_ORDER], c.sync_order);
  assert.equal(KITCHEN_WITHOUT_SCREEN, c.kitchen_without_screen); assert.equal(tipShareForLynkOmni(1000), c.tip_share); assert.equal(DELIVERY_SHARE_CENTS, c.delivery_share_cents); assert.equal(PROOF_WARNING_KEY, c.proof_warning_key);
});
test("web rule, limits, low float, cash hand-over and statement vectors", () => {
  for (const v of V.web_rule) assert.equal(webRule(v.action, v.registered), v.rule, JSON.stringify(v));
  for (const v of V.limit_check) assert.equal(limitCheck(v.amount, v.used_today, combinedLimits(v.partner, v.pack ?? undefined)), v.result, JSON.stringify(v));
  for (const v of V.low_float) assert.equal(lowFloat(v.balance, v.usual), v.low, JSON.stringify(v));
  for (const v of V.cash) assert.equal(mayHandOverCash(v.state), v.may_hand_over_cash);
  const s = V.statement; const r = matchStatement(s.ours, s.rows);
  assert.equal(r.matched, s.matched); assert.equal(r.total, s.total); assert.deepEqual(r.mismatches, s.mismatches);
  assert.equal(commission(10_000, 100), 100); assert.equal(cashDifference(900, 1000), -100); assert.equal(floatForecastDays(500, 0), null); assert.equal(floatForecastDays(500, 100), 5);
  assert.equal(mayStart(false), false);
});
test("tier limits agree: receipts, tables, kitchen, tips, delivery, groups", () => {
  for (const [tier, t] of Object.entries(V.tiers) as [string, any][]) {
    assert.deepEqual([...receiptChannels(t.entitlement)], t.receipts);
    const l = restaurantLimits(t.entitlement);
    assert.equal(l.tables, t.tables); assert.equal(kitchenOutput(l), t.kitchen_output); assert.equal(l.tips, t.tips); assert.equal(l.tableQrOrdering, t.table_qr_ordering);
    assert.equal(mayOpenTable(l, t.tables === null ? 999 : t.tables - 1), true); if (t.tables !== null) assert.equal(mayOpenTable(l, t.tables), false);
    const d = deliveryEntitlement(t.entitlement, t.checkout_entitlement);
    assert.equal(d.partnerDeliveriesPerMonth, t.delivery.partner_deliveries_per_month); assert.equal(d.ownRiders, t.delivery.own_riders); assert.equal(d.routing, t.delivery.routing);
    assert.equal(mayOpenGroup(tier), t.may_open_group);
    assert.equal(within(t.devices, 0), true);
  }
  const d = deliveryEntitlement(V.tiers.free.entitlement, V.tiers.free.checkout_entitlement);
  assert.equal(mayRequestPartnerDelivery(19, d), true); assert.equal(mayRequestPartnerDelivery(20, d), false); assert.equal(mayAddRider(0, d), false);
  const q = [{ partnerId: "a", price: 2000, etaS: 1800 }, { partnerId: "b", price: 1500, etaS: 3600 }];
  assert.equal(pickQuotes(q, false).length, 1); assert.equal(pickQuotes(q, true)[0]?.partnerId, "b"); assert.equal(pickQuotes(q, true, "fastest")[0]?.partnerId, "a");
  assert.equal(nextDeliveryStep("accepted"), "picked_up"); assert.equal(nextDeliveryStep("delivered"), null); assert.equal(lynkomniShareCents(3), 30);
  assert.equal(groupOutcome(7000, 10000), "failed"); assert.equal(chargedWhen("failed"), false); assert.equal(chargedWhen("reached"), true);
  assert.equal(splitNeedsAtLeast, 2);
  const lines = [{ table: "T1", orderId: "o1", lineNo: 1, ready: false }, { table: "T1", orderId: "o1", lineNo: 2, ready: true }];
  assert.equal(kitchenQueue(lines).length, 1); assert.equal(mayCloseTable(lines, new Set(["o1"])), false); assert.equal(mayCloseTable(lines, new Set(["o2"])), true);
});
test("voice, home cards, sync order, setup, second currency, practice and confirmed", () => {
  for (const v of V.voice) assert.deepEqual(parseVoice(v.text, v.products), v.lines, v.text);
  for (const v of V.home_cards) assert.deepEqual(homeCards(v.role, v.staff_see_profit, v.pending, v.low, v.negative, v.unread), v.cards, JSON.stringify(v));
  for (const v of V.sync) assert.deepEqual(syncOrder(v.pending), v.order);
  assert.equal(nextSetupStep(new Set()), "locale_card"); assert.equal(nextSetupStep(new Set(SETUP_STEPS)), null);
  assert.equal(secondCurrency(1000, "USD", "USD", () => 0), null);
  assert.deepEqual(secondCurrency(1000, "USD", "EUR", () => 920), { amount: 920, currency: "EUR", estimate: true, saleCurrency: "USD" });
  assert.equal(practiceLabel(true), "PRACTICE"); assert.equal(practiceLabel(false), null);
  assert.equal(mayShowConfirmed("pending_confirmation"), false); assert.equal(mayShowConfirmed("confirmed"), true);
});
