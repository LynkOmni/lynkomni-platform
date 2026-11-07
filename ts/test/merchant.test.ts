import { test } from "node:test";
import assert from "node:assert/strict";
import { Cart, paymentPayload, salePayload, uuid7 } from "../src/pos.js";
import { adjust, afterSale, canChangeSettings, canSeeProfit, counted, daySummary, homeBlocks, insight, maySync, mode, pending, stockAlerts, stockState } from "../src/merchant.js";
import type { DaySale } from "../src/merchant.js";

let n = 0;
const id = (): string => uuid7(1_760_000_000_000 + n++, (k) => Uint8Array.from({ length: k }, (_, i) => (i * 31 + n) % 256));
const rice = { id: id(), name: "Rice 1 kg", price: 1500, category: "food" };
const soap = { id: id(), name: "Soap bar", price: 500, category: "home" };
const costs = { [rice.id]: 1100, [soap.id]: 350 };
function sold(lines: [typeof rice, number][], method: "cash" | "mobile_money" = "cash"): DaySale {
  const c = new Cart(); for (const [p, q] of lines) c.add(p, q);
  const sale = salePayload(c, id(), `MP-${n}`, "RWF");
  return { sale, payments: [paymentPayload(id(), sale.sale_id, method, sale.total)], voided: false };
}

test("the owner always sees profit; staff only when the owner allows it", () => {
  assert.equal(canSeeProfit("owner", { staffSeeProfit: false }), true);
  assert.equal(canSeeProfit("cashier", { staffSeeProfit: false }), false);
  assert.equal(canSeeProfit("manager", { staffSeeProfit: true }), true);
  assert.equal(canChangeSettings("owner"), true);
  assert.equal(canChangeSettings("manager"), false);
});

test("the home screen follows the role (blueprint section 5)", () => {
  const owner = homeBlocks("owner", { staffSeeProfit: false });
  assert.deepEqual(owner.slice(0, 3), ["sales", "profit", "new_sale"]);
  for (const b of ["alerts", "chats", "insight", "pending"] as const) assert.ok(owner.includes(b), b);
  const cashier = homeBlocks("cashier", { staffSeeProfit: false });
  assert.ok(!cashier.includes("profit") && !cashier.includes("sales"));
  assert.ok(cashier.includes("new_sale") && cashier.includes("stock_check") && cashier.includes("chats"));
  assert.ok(homeBlocks("cashier", { staffSeeProfit: true }).includes("profit"));
  assert.ok(!homeBlocks("manager", { staffSeeProfit: false }).includes("profit"));
});

test("a sale is never blocked by stock: it goes negative and is flagged", () => {
  const s = sold([[rice, 3000]]);
  const levels = afterSale({ [rice.id]: 2000 }, s.sale);
  assert.equal(levels[rice.id], -1000);
  const items = [{ productId: rice.id, cost: 1100, reorderAtMilli: 5000 }, { productId: soap.id, cost: 350, reorderAtMilli: 2000 }];
  assert.deepEqual(stockAlerts(items, { ...levels, [soap.id]: 2000 }), { negative: [rice.id], low: [soap.id] });
  assert.equal(stockState(2001, 2000), "ok");
  assert.equal(stockState(0, 0), "low");
});

test("adjustments and counts use integer thousandths", () => {
  assert.equal(adjust({ [rice.id]: 1000 }, rice.id, -500)[rice.id], 500);
  assert.throws(() => adjust({}, rice.id, 0.5));
  const c = counted({ [rice.id]: -1000 }, rice.id, 4000);
  assert.equal(c.levels[rice.id], 4000);
  assert.equal(c.differenceMilli, 5000);
  assert.throws(() => counted({}, rice.id, -1));
});

test("the day summary never counts unconfirmed money as received", () => {
  const a = sold([[rice, 2000], [soap, 1000]]);              // 3500 cash, cost 2550
  const b = sold([[soap, 3000]], "mobile_money");            // 1500 waiting for the provider
  const v = { ...sold([[rice, 1000]]), voided: true };        // voided: ignored
  const s = daySummary([a, b, v], costs);
  assert.deepEqual(s, { count: 2, total: 5000, profit: 5000 - 2200 - 350 - 1050, cash: 3500, confirmed: 0, waiting: 1500, failed: 0 });
  b.payments.push({ ...b.payments[0]!, payment_id: id(), status: "confirmed" });
  assert.equal(daySummary([a, b], costs).confirmed, 1500);
  for (const k of Object.values(s)) assert.ok(Number.isSafeInteger(k));
});

test("the insight of the day is the best seller, and nothing before the first sale", () => {
  assert.equal(insight([]), null);
  const best = insight([sold([[rice, 1000]]), sold([[soap, 3000]]), sold([[rice, 1000]])]);
  assert.equal(best?.name, "Soap bar");
  assert.equal(best?.qtyMilli, 3000);
});

test("mode manager: weak counts as offline, forced offline never syncs", () => {
  assert.equal(mode("good", false), "online");
  assert.equal(mode("weak", false), "offline");
  assert.equal(mode("good", true), "offline");
  assert.equal(maySync("weak", false), true);
  assert.equal(maySync("good", true), false);
  assert.equal(maySync("none", false), false);
});

test("the sync chip uses only the five user states", () => {
  assert.deepEqual(pending(["accepted", "sent", "queued"]), { count: 2, state: "queued" });
  assert.deepEqual(pending(["accepted", "sent"]), { count: 1, state: "sent" });
  assert.deepEqual(pending(["accepted"]), { count: 0, state: "accepted" });
});
