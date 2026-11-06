import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { STATUS_STATES, iconFile, statusIconFile, BRAND_THEMES, NO_BADGE_SCREENS, brandFile, brandSrc, chooseAsset, invoiceBrand, minWidth, poweredBy, surfaceVariant, themeVariant, type BrandManifest, type SurfacePolicy } from "../src/brand.js";

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

const POLICY = JSON.parse(readFileSync(`${process.cwd()}/../brand/surfaces.v1.json`, "utf8")) as SurfacePolicy;

test("placement matches the agreed table", () => {
  const want: Record<string, string> = { "web-header": "logo", "app-icon": "emblem", "pwa-manifest": "emblem", "receipt-header": "wordmark", "email-header": "logo", "email-footer": "wordmark", "powered-by-badge": "wordmark", "invoice-header": "logo" };
  for (const [id, asset] of Object.entries(want)) assert.equal(chooseAsset(POLICY, id), asset, id);
});

test("narrow space falls back to the emblem, same as Python", () => {
  assert.equal(chooseAsset(POLICY, "web-header", 96), "logo");
  assert.equal(chooseAsset(POLICY, "web-header", 95), "emblem");
  assert.equal(chooseAsset(POLICY, "side-menu", 220), "logo");
  assert.equal(chooseAsset(POLICY, "side-menu", 64), "emblem");
  assert.throws(() => chooseAsset(POLICY, "billboard"));
});

test("one-colour places and print use mono", () => {
  assert.equal(surfaceVariant(POLICY, "receipt-header", "dark"), "mono");
  assert.equal(surfaceVariant(POLICY, "notification-icon", "light"), "mono");
  assert.equal(surfaceVariant(POLICY, "invoice-header", "light"), "light");
  assert.equal(surfaceVariant(POLICY, "invoice-header", "light", true), "mono");
  assert.throws(() => surfaceVariant(POLICY, "web-header", "neon"));
});

test("powered-by badge never shows on money-critical screens and follows the tier", () => {
  assert.equal(poweredBy("required", "pay-link", true), true);
  assert.equal(poweredBy("removable", "pay-link", true), false);
  assert.equal(poweredBy("removable", "pay-link"), true);
  for (const s of NO_BADGE_SCREENS) assert.equal(poweredBy("required", s), false, s);
  assert.throws(() => poweredBy("sometimes", "pay-link"));
});

const ICONS: BrandManifest = { assets: {}, icons: { "status-queued": { group: "states", accessibleName: "Queued", svg: "icons/q.svg" }, "ui-home": { group: "ui", accessibleName: "Home", svg: "icons/h.svg" } } };

test("icon lookup and the five states", () => {
  assert.deepEqual(iconFile(ICONS, "ui-home"), { file: "icons/h.svg", accessibleName: "Home" });
  assert.equal(statusIconFile(ICONS, "queued").accessibleName, "Queued");
  assert.throws(() => statusIconFile(ICONS, "pending"));
  assert.throws(() => iconFile(ICONS, "nope"));
  assert.deepEqual([...STATUS_STATES], ["queued", "sent", "accepted", "confirmed", "failed"]);
});
