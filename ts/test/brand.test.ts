import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { BRAND_THEMES, brandFile, brandSrc, invoiceBrand, minWidth, themeVariant, type BrandManifest } from "../src/brand.js";

const M: BrandManifest = { assets: { logo: { minWidthPx: 96, accessibleName: "LynkOmni", variants: { light: { svg: "svg/a-light.svg" }, mono: { svg: "svg/a-mono.svg" } } } } };

test("themes map to the same-named variants", () => {
  for (const t of BRAND_THEMES) assert.equal(themeVariant(t), t);
  assert.throws(() => themeVariant("mono"));
});

test("asset lookup and minimum width", () => {
  assert.equal(brandFile(M, "logo", "light"), "svg/a-light.svg");
  assert.equal(minWidth(M, "logo"), 96);
  assert.throws(() => brandFile(M, "nope", "light"));
  assert.throws(() => brandFile(M, "logo", "dark"));
});

test("brand files are served from this site only", () => {
  assert.equal(brandSrc("/brand/", M, "logo", "light"), "/brand/svg/a-light.svg");
  for (const bad of ["https://cdn.example.com/x", "//cdn.example.com/x", "javascript:alert(1)", "http://evil"]) assert.throws(() => brandSrc(bad, M, "logo", "light"), bad);
});

test("invoice branding matches the Python table and the billing tiers", () => {
  assert.equal(invoiceBrand("lynkomni").show_lynkomni, true);
  assert.equal(invoiceBrand("logo").merchant_logo, true);
  assert.equal(invoiceBrand("full").show_lynkomni, false);
  assert.throws(() => invoiceBrand("platinum"));
  const py = readFileSync(`${process.cwd()}/../brand/__init__.py`, "utf8");
  for (const tier of ["lynkomni", "logo", "full"]) assert.ok(py.includes(`"${tier}":`), tier);
});
