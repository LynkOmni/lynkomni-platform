import { test } from "node:test";
import assert from "node:assert/strict";
import { tabsHtml, firstColumnHtml, serviceMenuHtml, quickCreateHtml, quickCreateButton, launcherGroupsHtml, orderedMenuHtml } from "../src/appshell.js";
import { NAV } from "../src/navigation.generated.js";
import { DEVICES } from "../src/interfaces.generated.js";
import { layoutFor } from "../src/interfaces.js";

const look = { t: (k: string) => `[${k}]`, icon: (id: string) => `<i data-ic="${id}"></i>` };
const tabsOf = (html: string): string[] => [...html.matchAll(/data-tab="([^"]+)"/g)].map((m) => m[1]!);
const upright = layoutFor(DEVICES, { interface: "phone.touch", width: 390, height: 844 });
const small = layoutFor(DEVICES, { interface: "phone.touch", width: 320, height: 568 });
const sideways = layoutFor(DEVICES, { interface: "phone.touch", width: 844, height: 390 });

test("the bottom bar comes from the register: five with words, four on a small phone, a rail when sideways, none on a focus screen", () => {
  const html = tabsHtml(NAV, look, { kind: "shop", layout: upright, screen: "home", current: "home" });
  assert.deepEqual(tabsOf(html), ["home", "sell", "stock", "chats", "business"]);
  assert.ok(/class="tabbar ash-bottom"/.test(html));
  assert.ok(/\[nv_home\]/.test(html), "every tab carries its word");
  assert.equal(tabsOf(tabsHtml(NAV, look, { kind: "shop", layout: small, screen: "home", current: "home" })).length, 4);
  assert.ok(/class="rail ash-rail"/.test(tabsHtml(NAV, look, { kind: "shop", layout: sideways, screen: "home", current: "home" })));
  assert.equal(tabsHtml(NAV, look, { kind: "shop", layout: upright, screen: "pay", current: "sell" }), "", "no bar during a payment");
  assert.equal(tabsHtml(NAV, look, { kind: "shop", layout: upright, screen: "shift", current: "sell" }), "", "no bar during a cash count");
  assert.deepEqual(tabsOf(tabsHtml(NAV, look, { kind: "person", layout: upright, screen: "home", current: "home" })), ["home", "track", "scan", "chats", "me"]);
});

test("the two-level side bar keeps Settings and Help however a person hides items", () => {
  const html = firstColumnHtml(NAV, look, { current: "home", hidden: ["settings", "help", "track"] });
  assert.ok(tabsOf(html).includes("settings") && tabsOf(html).includes("help"));
  assert.ok(!tabsOf(html).includes("track"));
  const menu = serviceMenuHtml(NAV, look, { service: "queue", current: "queue_tickets", title: (s) => s });
  assert.deepEqual([...menu.matchAll(/data-slot="([^"]+)"/g)].map((m) => m[1]).slice(0, 2), ["overview", "list"]);
});

test("quick create follows the role and hides on a focus screen", () => {
  assert.ok(/data-item="new_sale"/.test(quickCreateHtml(NAV, look, { role: "cashier", close: "x" })));
  assert.ok(!/new_invoice/.test(quickCreateHtml(NAV, look, { role: "cashier", close: "x" })));
  assert.equal(quickCreateHtml(NAV, look, { role: "nobody", close: "x" }), "");
  assert.notEqual(quickCreateButton(NAV, look, { role: "owner", screen: "home", act: "qc" }), "");
  assert.equal(quickCreateButton(NAV, look, { role: "owner", screen: "pay", act: "qc" }), "");
});

test("the launcher shows My services first, then the eight groups, each family once", () => {
  const html = launcherGroupsHtml(NAV, look, { mine: ["lynkpos", "lynkacc"], name: (f) => f, productIcon: () => "ui-grid" });
  const groups = [...html.matchAll(/data-group="([^"]+)"/g)].map((m) => m[1]);
  assert.deepEqual(groups, ["mine", "sell", "get_paid", "run_the_office", "people", "move_and_protect", "learn_and_work", "ask_and_decide", "build"]);
  assert.equal((html.match(/data-act="place:lynkpos"/g) ?? []).length, 1);
});

test("a surface's own menu is put in the register's fixed order", () => {
  const html = orderedMenuHtml(NAV, look, { items: [{ id: "share", slot: "settings", label: "S" }, { id: "auto", slot: "automations", label: "A" }, { id: "sales", slot: "list", label: "L" }, { id: "home", slot: "overview", label: "O" }], current: "sales", act: "go" });
  assert.deepEqual([...html.matchAll(/data-act="go:([a-z]+)"/g)].map((m) => m[1]), ["home", "sales", "auto", "share"]);
  assert.ok(/data-act="go:sales" data-slot="list" aria-current="page"/.test(html));
});
