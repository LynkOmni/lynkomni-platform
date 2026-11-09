import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { FOOTER_KEYS, buildFooter, columns, copyright, currentYear, mainFooterHtml, paymentMarks, shortFooter, shortFooterHtml, footerText, SOCIAL, SOCIAL_LINKS, type Pack } from "../src/footer.js";

const pack = (c: string): Pack => JSON.parse(readFileSync(`${process.cwd()}/../contract/country-packs/${c}.json`, "utf8"));
const FIXED = "© 2026 CruxOmni Group. All rights reserved. LynkOmni is a product of CruxOmni Group.";

test("the copyright line is fixed text and only the year changes", () => {
  assert.equal(copyright(2026), FIXED);
  assert.equal(shortFooter(new Date("2026-07-01T12:00:00Z"), "Africa/Kigali"), FIXED);
  assert.equal(copyright(2027), FIXED.replace("2026", "2027"));
});
test("the year flips at the viewer's local midnight", () => {
  const instant = new Date("2026-12-31T22:30:00Z");                      // still 2026 in UTC, already 2027 in Kigali (UTC+2)
  assert.equal(currentYear(instant, "UTC"), 2026); assert.equal(currentYear(instant, "Africa/Kigali"), 2027);
  assert.equal(buildFooter({ now: instant, pack: pack("RW"), lang: "en" }).legal.copyright, copyright(2027));
  assert.equal(currentYear(instant, "Not/AZone"), 2026);                  // a bad zone falls back to UTC instead of failing
});
test("menus use the ecosystem names and the cleaned structure", () => {
  const cols = columns("en"), ids = (c: string) => cols.find((x) => x.id === c)!.items.map((i) => i.label);
  assert.deepEqual(ids("developers"), ["LynkHub", "LynkDoc", "LynkAPI", "LynkSDK"]);
  assert.ok(ids("products").includes("LynkVCard") && ids("products").includes("LynkSuite") && ids("products").includes("LynkAssist"));
  assert.ok(ids("support").includes("LynkStatus") && ids("support").includes("LynkFAQ"));
  assert.ok(!ids("company").includes("Founder") && !ids("company").includes("Press"));                     // folded into Leadership and Newsroom
  const all = cols.flatMap((c) => c.items.map((i) => i.href)).join(" ");
  for (const bad of ["support.lynkomni.com", "docs.lynkomni.com", "bookings.lynkomni.com", "essentials.lynkomni.com", "flow.lynkomni.com"]) assert.ok(!all.includes(bad), bad);
  assert.ok(all.includes("https://doc.lynkomni.com") && all.includes("https://booking.lynkomni.com") && all.includes("https://essential.lynkomni.com") && all.includes("/support"));
  assert.deepEqual([...SOCIAL], ["linkedin", "x", "facebook", "instagram", "youtube", "tiktok", "whatsapp"]);
  for (const id of SOCIAL) assert.ok(SOCIAL_LINKS[id].startsWith("https://"), id);
});
test("payment methods follow the country pack and are never a global list", () => {
  assert.deepEqual(paymentMarks(pack("RW")), ["visa", "mastercard", "momo_mtn", "airtel_money", "bank_transfer", "qr"]);
  assert.deepEqual(paymentMarks(pack("KE")), ["visa", "mastercard", "mpesa", "bank_transfer", "qr"]);
  assert.ok(paymentMarks(pack("IN")).includes("upi") && !paymentMarks(pack("IN")).includes("momo_mtn"));
  assert.deepEqual(paymentMarks(null), ["visa", "mastercard", "bank_transfer"]);
});
test("language follows the visitor with per-string fallback to English", () => {
  assert.equal(footerText("fr", "products"), "Produits"); assert.equal(footerText("sw", "products"), "Bidhaa"); assert.equal(footerText("sw", "appstore"), "App Store"); assert.equal(footerText("xx", "products"), "Products");
  const f = buildFooter({ now: new Date(), pack: pack("RW"), lang: "fr" });
  assert.equal(f.newsletter.button, "S'abonner"); assert.equal(f.legal.copyright.startsWith("© "), true); assert.ok(f.legal.copyright.includes("All rights reserved. LynkOmni is a product of CruxOmni Group."));
  assert.equal(buildFooter({ now: new Date(), pack: null, lang: "zz" }).lang, "en");
});
test("the newsletter is double opt-in, nothing pre-ticked, and honest about confirmation", () => {
  const n = buildFooter({ now: new Date(), pack: pack("RW"), lang: "en" }).newsletter;
  assert.equal(n.preticked, false); assert.equal(n.doubleOptIn, true); assert.ok(n.note.includes("not subscribed until you confirm")); assert.equal(n.topics.length, 4);
});

test("the footer's words live in one file for every language (web/footer/strings.en.json)", () => {
  const file = JSON.parse(readFileSync(`${process.cwd()}/../web/footer/strings.en.json`, "utf8")) as Record<string, string>;
  assert.deepEqual(Object.keys(file).sort(), FOOTER_KEYS.map((k) => `ft_${k}`).sort());
  for (const k of FOOTER_KEYS) assert.equal(file[`ft_${k}`], footerText("en", k), k);
});
test("the main footer is drawn from the model: fixed copyright, unticked newsletter, method icons with names as text", () => {
  const words = (k: string): string | undefined => (k === "ft_products" ? "Produits" : undefined);
  const f = buildFooter({ now: new Date("2026-11-09T12:00:00Z"), pack: pack("RW"), lang: "fr", words });
  const html = mainFooterHtml(f, (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;"), (id) => `<svg data-i="${id}"></svg>`);
  assert.ok(html.includes("© 2026 CruxOmni Group. All rights reserved. LynkOmni is a product of CruxOmni Group."));
  assert.ok(html.includes("<h3>Produits</h3>"));                                  // words come from the language pack
  assert.ok(!/checked/.test(html));                                                // nothing pre-ticked
  assert.ok(html.includes("MTN MoMo") && html.includes('data-i="ui-pay-mobile-money"'));
  assert.ok(!/Africa|Afrique|Afrika/.test(html));                                  // nothing built for one region (section 5 positioning line only)
  assert.equal(footerText("en", "tagline"), "Works with or without internet.");                  // section 5 positioning line
});
test("the short footer inside apps is one line: the fixed copyright", () => {
  const h = shortFooterHtml(new Date("2026-11-09T12:00:00Z"), "UTC");
  assert.equal(h, '<footer class="shortfoot" role="contentinfo"><p>© 2026 CruxOmni Group. All rights reserved. LynkOmni is a product of CruxOmni Group.</p></footer>');
});
