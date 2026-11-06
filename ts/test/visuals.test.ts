import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { decorative, visual, visualAlt, visualIds } from "../src/visuals.js";

const GEN = `${process.cwd()}/../visuals/generated`;
const INDEX = JSON.parse(readFileSync(`${GEN}/index.json`, "utf8")) as { needs: Record<string, { alt: string; files: { file: string; theme: string }[] }> };

test("the TypeScript table lists the same visuals as the Python index", () => {
  assert.deepEqual(visualIds(), Object.keys(INDEX.needs).sort());
});

test("every visual resolves to a real file with its text alternative", () => {
  for (const id of visualIds()) {
    let v;
    try { v = visual(id, "light"); } catch { v = visual(id, "light", undefined, "png"); }
    assert.ok(readFileSync(`${GEN}/${v.file}`, "latin1").length > 0, v.file);
    assert.equal(v.alt, INDEX.needs[id]?.alt);
    assert.ok(v.alt.length > 19);
  }
});

test("unknown ids and themes throw instead of returning a placeholder", () => {
  assert.throws(() => visual("product-nothing"), /needs\.v1\.json/);
  assert.throws(() => visual("product-pos", "light", undefined, "png"), /no light version|no \.png/);
  assert.throws(() => visual("diagram-sync-states", "dark", "lite", "png"));
});

test("lite mode hides decorative images but keeps figures; sunlight uses the contrast set", () => {
  assert.equal(decorative("state-offline", "light", "lite"), undefined);
  assert.ok(decorative("diagram-sync-states", "light", "lite"));
  assert.equal(visual("product-pos", "light", "sunlight").theme, "contrast-light");
  assert.equal(visual("product-pos", "dark", "sunlight").theme, "contrast-dark");
});

test("fixed-appearance images fall back to light and png is available for icons", () => {
  assert.equal(visual("share-card", "dark").theme, "light");
  assert.ok(visual("app-icon", "dark", undefined, "png").file.endsWith("app-icon-1024-dark.png"));
  assert.equal(visualAlt("product-pos"), INDEX.needs["product-pos"]?.alt);
});
