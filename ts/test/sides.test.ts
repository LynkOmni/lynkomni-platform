import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { sideOf, storefrontPath, pathKind } from "../src/sides.js";
import { SIDE_RULE } from "../src/sides.generated.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/sides.v1.json`, "utf8"));

test("every address is on the same side in TypeScript as in the Python reference", () => {
  for (const c of V.sides) assert.equal(sideOf(SIDE_RULE, c.address), c.side, c.address);
});
test("every app path has the same kind and every mirror the same Storefront twin", () => {
  for (const c of V.kinds) assert.equal(pathKind(SIDE_RULE, c.path), c.kind, c.path);
  for (const c of V.twins) assert.equal(storefrontPath(SIDE_RULE, c.workspace), c.storefront);
  assert.throws(() => storefrontPath(SIDE_RULE, "/sell/basket"));
});
