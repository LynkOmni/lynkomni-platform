import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as S from "../src/shell.js";

const root = `${process.cwd()}/..`;
const addr = JSON.parse(readFileSync(`${root}/catalog/addresses.v1.json`, "utf8")) as S.AddressMap;
const t: S.T = (k, v) => `${k}${v ? JSON.stringify(v) : ""}`;
const icon: S.Icon = (id) => `<i data-icon="${id}"></i>`;

test("sizes: phone under 600, tablet to 1023, computer from 1024", () => {
  assert.equal(S.viewport(390), "phone"); assert.equal(S.viewport(600), "tablet"); assert.equal(S.viewport(1023), "tablet"); assert.equal(S.viewport(1024), "computer");
});
test("header grammar: logo, navigation, then search, globe, help, bell, launcher, account; phone shows logo, search, menu", () => {
  const parts = { logo: "<svg/>", nav: [{ id: "home", label: "Home", current: true }], notifications: 3, signedIn: true };
  const h = S.header(parts, "computer", t, icon);
  for (const a of ["shell:search", "shell:globe", "shell:help", "shell:bell", "shell:launcher", "shell:account"]) assert.ok(h.includes(`data-act="${a}"`), a);
  assert.ok(h.indexOf("shell:search") < h.indexOf("shell:globe") && h.indexOf("shell:globe") < h.indexOf("shell:help") && h.indexOf("shell:bell") < h.indexOf("shell:launcher"));
  assert.ok(h.includes('aria-current="page"') && h.includes(">3<"));
  assert.ok(!S.header({ ...parts, surface: "app" }, "computer", t, icon).includes('class="hnav"'));   // apps carry it in the sidebar
  const ph = S.header(parts, "phone", t, icon);
  assert.ok(ph.includes("shell:menu") && !ph.includes("shell:globe") && !ph.includes('class="hnav"'));
  const out = S.header({ ...parts, signedIn: false, primary: { label: "Start free", act: "start" } }, "computer", t, icon);
  assert.ok(out.includes("sign_in") && out.includes("Start free") && !out.includes("shell:bell"));
});
test("navigation: tabs (max 5) on a phone, rail on a tablet, sidebar on a computer", () => {
  const items = Array.from({ length: 7 }, (_, i) => ({ id: `n${i}`, label: `N${i}`, icon: "ui-home" }));
  assert.equal((S.navigation(items, "phone", t, icon).match(/navitem/g) ?? []).length, 5);
  assert.ok(S.navigation(items, "tablet", t, icon).includes('class="shell-nav rail"'));
  assert.equal((S.navigation(items, "computer", t, icon).match(/navitem/g) ?? []).length, 7);
});
test("launcher never hides a place: coming soon stays with its tag", () => {
  const l = S.launcher([{ id: "exchange", name: "Exchange", icon: "product-dev", href: "/x", state: "coming_soon" }], t, icon);
  assert.ok(l.includes("soon-tag") && l.includes("coming_soon") && l.includes("Exchange"));
});
test("account menu masks the LynkID and offers switch, language, theme, security, help, sign out", () => {
  assert.equal(S.maskId("LOID-1234-5678-9012"), "LOID-1…9012");
  const m = S.accountMenu({ name: "Grace", lynkId: "LOID-1234-5678-9012", businesses: [{ id: "b1", name: "A", current: true }, { id: "b2", name: "B", current: false }], role: "owner", roles: ["owner", "cashier"], theme: "dark", language: "fr", region: "XX" }, t, icon);
  assert.ok(!m.includes("LOID-1234-5678-9012") && m.includes("copy:lynkid") && m.includes("business:b2") && m.includes("role:cashier") && m.includes("shell:signout") && m.includes("go:security"));
});
test("find or do anything: actions first on an empty query, prefix wins, diacritics ignored, keywords match", () => {
  const idx: S.Entry[] = [
    { id: "a1", kind: "action", title: "New sale", act: "newsale" }, { id: "p1", kind: "product", title: "Café au lait", subtitle: "Drinks" },
    { id: "c1", kind: "customer", title: "Grace Uwimana" }, { id: "s1", kind: "setting", title: "Receipts", keywords: ["logo", "footer"] },
    { id: "h1", kind: "help", title: "How to void a sale" },
  ];
  assert.deepEqual(S.search(idx, "").map((e) => e.id), ["a1"]);
  assert.equal(S.search(idx, "cafe")[0]?.id, "p1");
  assert.equal(S.search(idx, "logo")[0]?.id, "s1");
  assert.equal(S.search(idx, "new")[0]?.id, "a1");
  assert.deepEqual(S.search(idx, "zzz"), []);
  const bar = S.commandBar("new", S.search(idx, "new"), t, icon);
  assert.ok(bar.includes('role="combobox"') && bar.includes("assist:ask") && bar.includes("suggested_by_assist"));
});
test("help panel always offers a person", () => {
  const h = S.helpPanel("Sell", [], t, icon);
  assert.ok(h.includes("support:chat") && h.includes("support:case") && h.includes("assist:ask") && h.includes("no_articles"));
});
test("notifications: security always now, transactional held in quiet hours, low urgency to the digest, nothing twice", () => {
  const seen = new Set<string>();
  const list: S.Notice[] = [
    { id: "s", at: 0, urgency: "security", title: "New sign-in" }, { id: "t", at: 0, urgency: "transactional", title: "Payment confirmed" },
    { id: "l", at: 0, urgency: "low", title: "Weekly insight" },
  ];
  const night = S.deliverNow(list, 23, { startHour: 22, endHour: 7 }, seen);
  assert.deepEqual([night.now.map((n) => n.id), night.held.map((n) => n.id), night.digest.map((n) => n.id)], [["s"], ["t"], ["l"]]);
  const again = S.deliverNow(list, 9, null, seen);
  assert.deepEqual([again.now, again.held, again.digest], [[], [], []]);
  assert.ok(S.inQuietHours(2, { startHour: 22, endHour: 7 }) && !S.inQuietHours(12, { startHour: 22, endHour: 7 }) && S.inQuietHours(13, { startHour: 12, endHour: 14 }));
});
test("every state has a picture, title, line and next step; loading is a skeleton; coming soon offers Notify me", () => {
  for (const k of Object.keys(S.STATE_PICTURE) as S.StateKind[]) {
    const html = S.state(k, t, k === "loading" ? null : { svg: "<svg/>", alt: "alt" }, { label: "Next", act: "go" });
    if (k === "loading") assert.ok(html.includes("skel"));
    else assert.ok(html.includes(`state_${k}_title`) && html.includes("Next") && html.includes('role="img"'), k);
  }
  assert.ok(S.state("error", t, null, null).includes('role="alert"'));
  assert.ok(S.comingSoon("LynkMPay", t, null, false).includes("notify:LynkMPay"));
  assert.ok(S.comingSoon("LynkMPay", t, null, true).includes("notify_done"));
});
test("connection chip and sync sheet; data saver on a weak link", () => {
  const s: S.SyncInfo = { link: "weak", pending: 2, lastSync: null, dataSaver: false, forcedOffline: false };
  assert.ok(S.connectionChip(s, t, icon).includes("weak_link") && S.connectionChip(s, t, icon).includes(">2<"));
  assert.ok(S.syncSheet(s, t, icon, () => "x").includes("toggle:datasaver"));
  assert.deepEqual(S.dataSaverPlan("weak", false), { pictures: false, syncPriorityOnly: true, chatMedia: false });
  assert.deepEqual(S.dataSaverPlan("good", false), { pictures: true, syncPriorityOnly: false, chatMedia: true });
  assert.ok(S.syncSheet({ ...s, link: "offline" }, t, icon, () => "x").includes("disabled"));
});
test("deep links come from the address map: language prefix, redirects, records, views, unknown is null", () => {
  assert.deepEqual(S.route(addr, "https://lynkomni.com/fr/pricing")?.path, "/pricing");
  const r = S.route(addr, "https://lynkomni.com/terms");
  assert.equal(r?.path, "/legal/terms"); assert.equal(r?.redirectedFrom, "/terms");
  assert.deepEqual(S.route(addr, "https://app.lynkomni.com/invoicing/invoices/LOINV-1234-5678-9012")?.params, { under: "/invoicing", record: "LOINV-1234-5678-9012" });
  assert.deepEqual(S.route(addr, "https://app.lynkomni.com/invoicing/invoices/new")?.params, { under: "/invoicing", record: "new" });
  assert.deepEqual(S.route(addr, "https://app.lynkomni.com/crm/customers?view=owing")?.params, { under: "/crm" });
  assert.equal(S.route(addr, "https://pay.lynkomni.com/r/LORCP-1111-2222-3333")?.params["LORCP"], "LORCP-1111-2222-3333");
  assert.equal(S.route(addr, "https://shop.lynkomni.com/mamas.kitchen")?.params["username"], "mamas.kitchen");
  assert.equal(S.route(addr, "https://evil.example/x"), null);
  assert.equal(S.route(addr, "https://app.lynkomni.com/nowhere-at-all"), null);
  assert.equal(S.route(addr, "https://staff.lynkomni.com/partner-hub")?.surface, "staff");
});
test("protected zones never carry ads or Powered by", () => {
  assert.ok(S.protectedZone("payment") && S.protectedZone("cash-count") && !S.protectedZone("home"));
});
test("undo anything within 30 seconds, from history later; money actions are audited voids", () => {
  const u = new S.Undo();
  let n = 1;
  u.push("a", "Product archived", 0, () => { n = 0; });
  u.push("m", "Sale voided", 0, () => { n = 9; }, true);
  assert.equal(u.openToasts(10_000).length, 2); assert.equal(u.openToasts(31_000).length, 0);
  assert.equal(u.undo("a", 31_000), "expired"); assert.equal(u.undo("a", 31_000, true), "undone"); assert.equal(n, 0);
  assert.equal(u.undo("m", 5_000), "voided"); assert.equal(u.undo("zz", 0), "unknown");
  assert.ok(S.undoToast(u.push("b", "x", 0, () => {}), 4_000, t, icon).includes("26s"));
});
test("continue on any device carries the screen and a draft, never a secret or a protected screen, and expires after a day", () => {
  const h: S.Handoff = { surface: "app", screen: "invoicing", record: "LOINV-1", draft: { note: "hi", pin: "1234", card_number: "x" }, at: 0, business: "b1" };
  assert.deepEqual(S.handoff(h, 1000)?.draft, { note: "hi" });
  assert.equal(S.handoff(h, 90_000_000), null);
  assert.equal(S.handoff({ ...h, screen: "payment" }, 10)?.screen, "home");
});
test("chat in two languages: banner, per-message note, switch back, same language shows nothing", () => {
  const name = (c: string) => ({ ar: "Arabic", fr: "French" })[c] ?? c;
  const c: S.ChatLang = { reader: "fr", writer: "ar", writerName: "Amina", showOriginal: false };
  assert.ok(S.translationBanner(c, name, t).includes("chat:lang:original"));
  assert.ok(S.translationBanner({ ...c, showOriginal: true }, name, t).includes("back_to"));
  assert.equal(S.translationBanner({ ...c, writer: "fr" }, name, t), "");
  const m: S.ChatMessage = { id: "1", text: "مرحبا", translated: "Bonjour", language: "ar" };
  assert.ok(S.messageNote(m, c, name, t).includes("translated_from") && S.messageText(m, c) === "Bonjour");
  assert.equal(S.messageText(m, { ...c, showOriginal: true }), "مرحبا");
  assert.ok(S.messageNote({ ...m, failed: true }, c, name, t).includes("could_not_translate"));
  assert.ok(S.messageNote({ ...m, translated: undefined, pendingTranslation: true }, c, name, t).includes("will_translate_online"));
  assert.equal(S.messageNote({ ...m, language: "fr" }, c, name, t), "");
});
test("username field: live rule, taken in the cloud, suggestions", () => {
  assert.ok(S.usernameField("adm1n", null, () => false, t, icon).includes("username_held_for_review"));
  assert.ok(S.usernameField("mamas.kitchen", "available", () => false, t, icon).includes("username_available"));
  const taken = S.usernameField("mamas.kitchen", "taken", (u) => u === "mamas.kitchen", t, icon);
  assert.ok(taken.includes("username_taken") && taken.includes("username:mamas.kitchen.shop"));
  assert.ok(S.usernameField("", null, () => false, t, icon).includes("username_hint"));
});
test("charts: table view, computed summary, assumption label, never invented numbers", () => {
  const spec: S.ChartSpec = { title: "Sales", labels: ["Mon", "Tue", "Wed"], series: [{ name: "Sales", values: [100, 300, 200] }], kind: "bar", format: (n) => `$${n}` };
  const sum = S.chartSummary(spec, t);
  assert.ok(sum.includes('chart_peak{"label":"Tue","value":"$300"}') && sum.includes('chart_up{"pct":100}'));
  const c = S.chart(spec, "chart", t);
  assert.ok(c.includes("<rect") && c.includes("chart-table") && c.includes('aria-pressed="true"') && !c.includes("assumption"));
  const tbl = S.chart({ ...spec, kind: "line", assumption: true }, "table", t);
  assert.ok(tbl.includes("<td>$300</td>") && tbl.includes("assumption") && !tbl.includes("<svg"));
  assert.equal(S.chartSummary({ ...spec, series: [] }, t), "chart_no_data");
});
test("smart defaults come from the country pack and the device language", () => {
  const pack = { code: "XX", currency: "USD", tz: "UTC", locale: "en", languages: ["en", "fr"] };
  assert.deepEqual(S.smartDefaults(pack, "fr-FR"), { language: "fr", region: "XX", currency: "USD", timeZone: "UTC", businessType: "shop" });
  assert.equal(S.smartDefaults(pack, "ja").language, "en");
});
