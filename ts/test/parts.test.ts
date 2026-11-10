import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { afterWrong, numberChoices, numberMatch, pinPad, pinProblem } from "../src/signin.js";
import { badge, banner, bell, count, feelFor, lockScreen, mailPart, ranked, textParts } from "../src/notify.js";
import type { Line } from "../src/notify.js";
import { answer, buildPack, confirmCard, decide, lookup } from "../src/assist.js";
import { breadcrumbBar, trail } from "../src/breadcrumbs.js";
import { langUrl, pageHead } from "../src/pagehead.js";
import { translator } from "../src/shell.js";

const root = new URL("../../..", import.meta.url).pathname;
const V = JSON.parse(readFileSync(`${root}/contract/vectors/parts.v1.json`, "utf8"));
const words = (lang: string) => JSON.parse(readFileSync(`${root}/web/shell/i18n/${lang}.json`, "utf8")).texts as Record<string, string>;
const t = translator(words("en"));
const icon = (id: string) => `<i data-i="${id}"></i>`;

test("the PIN rule and the waits are the same as identity/offline.py", () => {
  for (const c of V.pins) assert.equal(pinProblem(c.pin), c.problem, c.pin);
  assert.equal(afterWrong(0), 0); assert.equal(afterWrong(3), 30); assert.equal(afterWrong(10), "locked");
  const pad = pinPad({ entered: 2, length: 4, wrong: 10, waitLeft: 0, pictures: true, sound: true, title: "PIN" }, t, icon);
  assert.ok(/role="alert"/.test(pad)); assert.ok(!/\b[0-9]{4}\b/.test(pad.replace(/<[^>]+>/g, " ").replace(/\d{3,}/g, "")), "typed digits are never shown");
  assert.ok(/disabled/.test(pad), "a locked pad takes no presses");
});

test("number matching offers three different numbers, the right one among them, and nothing on a wrong tap", () => {
  let x = 7; const rnd = () => (x = (x * 9301 + 49297) % 233280) / 233280;
  for (let i = 0; i < 50; i++) { const c = numberChoices("42", rnd); assert.equal(new Set(c).size, 3); assert.ok(c.includes("42")); }
  assert.ok(/role="alert"/.test(numberMatch(["11", "42", "73"], t, "wrong")));
  assert.equal(new Set(numberChoices("42", () => 0.5)).size, 3, "even a random source that always says the same thing");
});

test("every breadcrumb trail is the same as core/breadcrumbs.py", () => {
  for (const c of V.trails) assert.deepEqual(trail(c.host, c.path), c.trail, `${c.host}${c.path}`);
  const bar = breadcrumbBar([{ path: "/", label: "Home" }, { path: "/pricing", label: "Pricing" }], false, t);
  assert.ok(/aria-current="page">Pricing/.test(bar)); assert.ok(!bar.includes('href="/pricing"'), "the page never links to itself");
});

test("LynkAssist decides and answers exactly as services/assist_register.py", () => {
  for (const c of V.decide) { const d = decide(c.action, c.ask); assert.deepEqual([d.run, d.needs, d.class], [c.run, c.needs, c.class], `${c.action} ${JSON.stringify(c.ask)}`); }
  for (const c of V.answers) { const a = answer(c.topic, c.asker); assert.deepEqual([a.answer, a.class], [c.answer, c.class], `${c.topic} ${JSON.stringify(c.asker)}`); }
  const card = confirmCard({ what: "x", d: decide("send_all_money_to_me", { role: "owner" }) }, t, icon);
  assert.ok(!card.includes("assist:confirm"), "nothing outside the register can be confirmed");
});

test("the offline knowledge pack is the Python pack, entry for entry, in every language checked", () => {
  for (const [lang, entries] of Object.entries(V.packs as Record<string, unknown[]>)) assert.deepEqual(buildPack(words(lang)), entries, lang);
  for (const c of V.lookups) assert.deepEqual(lookup(buildPack(words(c.lang)), c.query).map((e) => e.id), c.ids, `${c.lang}: ${c.query}`);
});

test("the bell: count, badge, ranking by what needs action, folded lines and an empty state", () => {
  for (const c of V.badges) assert.equal(badge(c.n), c.text);
  const L: Line[] = [{ nid: "a", kind: "sync_retried", title: "low", at: 5 }, { nid: "b", kind: "stock_low", title: "normal", at: 9, count: 12 },
    { nid: "c", kind: "recovery_started", title: "critical", at: 1 }, { nid: "d", kind: "staff_request", title: "act", at: 2, actions: [{ id: "approve", label: "Approve" }] }];
  assert.equal(count(L), 3, "low priority never raises the count");
  assert.deepEqual(ranked(L).map((l) => l.nid), ["c", "d", "b", "a"]);
  const html = bell(L, { filter: "all", lastOpened: 3, areas: [] }, t, icon, String);
  assert.ok(/12/.test(html)); assert.ok(/ntf:ack:c/.test(html));
  assert.ok(/class="nempty"/.test(bell([], { filter: "all", lastOpened: 0, areas: [] }, t, icon, String)));
  assert.equal(banner(L[0]!, t, icon), "", "low and normal never become banners");
  assert.ok(/role="alert"/.test(banner(L[2]!, t, icon)));
});

test("sound, vibration and the lock screen follow the priority and the person's quiet time", () => {
  assert.equal(feelFor("normal", { quiet: true, silent: false, lowData: false }).tones.length, 0);
  assert.ok(feelFor("critical", { quiet: true, silent: true, lowData: false }).tones.length > 0, "critical breaks through");
  assert.equal(feelFor("low", { quiet: false, silent: false, lowData: false }).vibrate.length, 0);
  assert.ok(!lockScreen("LynkPOS", "neutral", "Sale 25,000", t).includes("25,000"), "private by default");
});

test("message parts: text length by encoding, and email buttons only to lynkomni.com", () => {
  assert.deepEqual(textParts("Your code is ready"), { encoding: "gsm7", units: 18, parts: 1 });
  assert.equal(textParts("a".repeat(161)).parts, 2);
  assert.equal(textParts("مرحبا".repeat(15)).encoding, "unicode");
  assert.equal(textParts("€".repeat(80)).parts, 1, "€ takes two places in GSM-7: 80 of them fill one part");
  assert.equal(textParts("€".repeat(81)).parts, 2);
  const good = mailPart({ title: "x", lines: [], button: { label: "Open", href: "https://app.lynkomni.com/sell" }, reason: "r", optIn: false, lang: "en", dir: "ltr" }, "", t);
  const bad = mailPart({ title: "x", lines: [], button: { label: "Open", href: "https://lynkomni.com.evil.example/x" }, reason: "r", optIn: true, lang: "en", dir: "ltr" }, "", t);
  assert.ok(/mbtn/.test(good)); assert.ok(!bad.includes("mbtn")); assert.ok(/msg:stop/.test(bad));
});

test("the page head: canonical, one alternate per language and x-default, noindex for app pages", () => {
  assert.equal(langUrl("https://lynkomni.com/pricing", "fr"), "https://lynkomni.com/fr/pricing");
  assert.equal(langUrl("https://lynkomni.com/", "en"), "https://lynkomni.com/");
  const h = pageHead({ url: "https://lynkomni.com/pricing", kind: "page", title_key: "help", description_key: "help", breadcrumb: ["/", "/pricing"], langs: "all" }, "fr", t, (p) => p);
  assert.equal((h.match(/hreflang=/g) ?? []).length, 39);
  assert.ok(/index, follow/.test(h));
  assert.ok(/noindex/.test(pageHead({ url: "https://app.lynkomni.com/sell", kind: "app", title_key: "help", description_key: "help", breadcrumb: ["/"], langs: ["en"] }, "en", t, (p) => p)));
});

import { cardPlanName, contactWaitSeconds, coolOffSeconds, mayNow } from "../src/protection.js";
test("the protection waits and card names on screen are identity/protection.py's and services/card_groups.py's", () => {
  for (const c of V.protection) { assert.equal(coolOffSeconds(c.advanced), c.cool_off_s); assert.equal(contactWaitSeconds(c.advanced), c.contact_wait_s); }
  for (const c of V.card_names) assert.equal(cardPlanName(c.group, c.tier), c.name);
  assert.deepEqual(mayNow("data_export", { locked: true, heldUntil: 0, now: 5 }), { ok: false, why: "locked" });
  assert.deepEqual(mayNow("data_export", { locked: false, heldUntil: 10, now: 5 }), { ok: false, why: "cool_off" });
  assert.deepEqual(mayNow("data_export", { locked: false, heldUntil: 1, now: 5 }), { ok: true });
  assert.throws(() => mayNow("buy_coffee", { locked: false, heldUntil: 0, now: 0 }));
});
