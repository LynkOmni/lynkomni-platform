import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { check, display, normalize, suggestions } from "../src/usernames.js";

const root = `${process.cwd()}/..`;
const vectors = JSON.parse(readFileSync(`${root}/contract/vectors/usernames.v1.json`, "utf8"));

test("username vectors from the Python reference (Instagram format, reserved words, look-alikes)", () => {
  for (const v of vectors.cases) {
    const c = check(v.input);
    assert.equal(c.ok, v.ok, v.input); assert.equal(c.reason, v.reason, v.input); assert.equal(c.username, v.username, v.input);
  }
  assert.ok(vectors.cases.length >= 40);
});
test("case-insensitive, shown with @, suggestions are free and valid", () => {
  assert.equal(normalize("  @Mamas.Kitchen "), "mamas.kitchen"); assert.equal(display("Mamas.Kitchen"), "@mamas.kitchen");
  const s = suggestions("Mama's Kitchen", (u) => u === "mamas.kitchen");
  assert.ok(s.length >= 2 && !s.includes("mamas.kitchen") && s.every((u) => check(u).ok));
});
