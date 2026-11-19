import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { groupOf, headerFor, bottomBar, centreOf, quickCreate, serviceMenu, pageTabs, tapsFromHome } from "../src/navigation.js";
import { NAV } from "../src/navigation.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/navigation.v1.json`, "utf8"));

test("groups, headers and bottom bars agree with the Python reference (INTERFACE UPDATE)", () => {
  for (const c of V.groups) assert.equal(groupOf(NAV, c.family), c.group, c.family);
  for (const c of V.headers) assert.deepEqual(headerFor(NAV, c.screen), c.expect, c.screen);
  for (const c of V.bars) assert.deepEqual(bottomBar(NAV, c.kind, c.tabs, c.screen, c.chosen), c.expect, JSON.stringify(c));
  for (const c of V.centres) assert.equal(centreOf(NAV, c.kind), c.expect, c.kind);
});
test("quick create, service menus, page tabs and taps from Home agree", () => {
  for (const c of V.quick) assert.deepEqual(quickCreate(NAV, c.role, c.built), c.expect, JSON.stringify(c));
  for (const c of V.menus) assert.deepEqual(serviceMenu(NAV, c.service, c.side), c.expect, c.service + c.side);
  for (const c of V.page_tabs) assert.deepEqual(pageTabs(NAV, c.tabs), c.expect);
  for (const [kind, want] of Object.entries(V.taps)) assert.deepEqual(tapsFromHome(NAV, kind), want, kind);
});
