/** LynkPOS handheld terminal emulator. Draws an original LynkOmni handheld (printer, screen, keypad, tap area, card slot,
 *  scan key) and runs the real sale rules from ts/src/pos.ts against sandbox providers. Draft until a designer reviews it.
 *  Built into one offline HTML file by web/build.mjs. Colours come only from the design tokens (CSS variables). */
import { Cart, PosError, change, formatMoney, paymentPayload, paymentState, quickCash, receiptLines, salePayload, uuid7 } from "../../../ts/src/pos.js";
import type { PaymentMethod, PaymentPayload, PaymentStatus, Product, SalePayload, UserState } from "../../../ts/src/pos.js";

interface BuildData {
  icons: Record<string, string>;
  brand: { body: string; topLight: string; topDark: string; receipt: string };
  pictures: { offLight: string; offDark: string; offAlt: string };
  states: Record<string, { label: string; meaning: string }>;
  /** Every country pack, the neutral sample pack first (Step 0): the chooser never opens on a real country. */
  packs: Record<string, CountryPack>;
  packOrder: string[];
  i18n: Record<string, { native: string; dir: "ltr" | "rtl"; texts: Record<string, string> }>;
}
interface CountryPack {
  code: string; name: string; currency: string; tz: string; locale: string; sample: boolean;
  ready: Record<string, { ok: boolean; message: string }>;
  services: { service: string; name: string; icon: string; state: "available" | "coming_soon" }[];
}
declare const DATA: BuildData;
/** The country the emulator shows. Read from the country pack and the provider ledger; nothing about a country lives in this code. */
const pack = (): CountryPack => DATA.packs[S.country] ?? DATA.packs[DATA.packOrder[0] ?? ""] as CountryPack;

type Screen = "lock" | "sell" | "cart" | "pay" | "cash" | "momo" | "card" | "waiting" | "done" | "off" | "menu" | "sales" | "sale" | "count";
type Lang = string;   // a language code from design/fonts/scripts.v1.json, or one of TEST_LANGS
interface Ev { n: number; type: string; origin: "device" | "server"; payload: unknown; sync: UserState; at: number }
interface Sale { sale: SalePayload; payments: PaymentPayload[]; tendered?: number; at: number; voided: boolean }

/** Screen words: English source in strings.en.json, every other language from the machine-translated language packs in
 *  i18n/<lang>.json (tools/translation/build_packs.py), all embedded by web/build.mjs so every language works offline. */
const PACKS = DATA.i18n;
const EN: Record<string, string> = PACKS.en?.texts ?? {};
const TEST_LANGS = ["xx", "xx-rtl"];   // xx = long-text test, xx-rtl = right-to-left test (pseudo-translations, never shown to real users)

const rnd = (n: number): Uint8Array => crypto.getRandomValues(new Uint8Array(n));
/** An unbiased index below n (rejection sampling: bytes that would favour the low indexes are thrown away). */
const pick = (n: number): number => { const limit = 256 - (256 % n); let b = rnd(1)[0]!; while (b >= limit) b = rnd(1)[0]!; return b % n; };
const newId = (): string => uuid7(Date.now(), rnd);
const CATALOG: Product[] = [
  ["Rice 1 kg", 1500, "food", "6000000000011"], ["Sugar 1 kg", 1400, "food", "6000000000028"], ["Beans 1 kg", 1200, "food", "6000000000035"],
  ["Cooking oil 1 L", 3200, "food", "6000000000042"], ["Bread", 1000, "food", "6000000000059"], ["Eggs, tray of 30", 4500, "food", "6000000000066"],
  ["Milk 500 ml", 600, "drinks", "6000000000073"], ["Water 1.5 L", 700, "drinks", "6000000000080"], ["Soda 300 ml", 500, "drinks", "6000000000097"],
  ["Tea leaves 100 g", 900, "drinks", "6000000000103"], ["Soap bar", 500, "home", "6000000000110"], ["Matches, pack", 300, "home", "6000000000127"],
].map(([name, price, category, barcode]) => ({ id: newId(), name: String(name), price: Number(price), category: String(category), barcode: String(barcode) }));
const NOTES = [500, 1000, 2000, 5000, 10000];
const SHOP = "Sample shop";
const DEVICE = "PT";
const PIN = "1234";

const S = {
  screen: "lock" as Screen, lang: "en" as Lang, theme: "light" as "light" | "dark", online: true, realUser: false, country: "", outcome: "confirm" as "confirm" | "fail",
  input: "", note: "", category: "all", cart: new Cart(), current: null as Sale | null, method: "cash" as PaymentMethod, sales: [] as Sale[],
  events: [] as Ev[], receiptNo: 0, selected: -1, timer: 0, leds: 0, flash: "",
};

const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const PSEUDO: Record<string, string> = { a: "\u00e0", c: "\u00e7", e: "\u00e9", i: "\u00ee", n: "\u00f1", o: "\u00f6", s: "\u0161", u: "\u00fc", y: "\u00fd" };
/** Same pseudo-translation as services/translation.py: accented letters and about 40% more length, to prove screens never break. */
const pseudo = (s: string): string => `[${s.replace(/[aceinosuy]/g, (c) => PSEUDO[c] ?? c)} ${"~".repeat(Math.max(1, Math.round(s.length * 0.4)))}]`;
const isTest = (): boolean => TEST_LANGS.includes(S.lang);
const t = (k: string): string => { const en = EN[k] ?? k; return isTest() ? pseudo(en) : PACKS[S.lang]?.texts[k] ?? en; };
const esc = (s: string): string => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const locale = (): string => `${isTest() ? "en" : S.lang}-${pack().code}`;
const money = (n: number): string => formatMoney(n, pack().currency, locale());
const icon = (id: string, cls = "ic"): string => `<span class="${cls}" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const stateWord = (s: string): string => t(`st_${s}`);
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(stateWord(s))}</span></span>`;
const clock = (ms: number, withDate = false): string => new Intl.DateTimeFormat(locale(), { timeZone: pack().tz, hour: "2-digit", minute: "2-digit", ...(withDate ? { day: "2-digit", month: "short", year: "numeric" } : {}) }).format(ms);
const reduced = (): boolean => matchMedia("(prefers-reduced-motion: reduce)").matches;
const methodOk = (m: PaymentMethod): boolean => m === "cash" || !S.realUser || (pack().ready[m]?.ok ?? false);

// ---- event log and the simulated cloud --------------------------------------------------------------------------
function emit(type: string, payload: unknown, origin: "device" | "server" = "device"): void {
  S.events.unshift({ n: S.events.length + 1, type, origin, payload, sync: origin === "server" ? "accepted" : "queued", at: Date.now() });
  drawLog();
}
function tick(): void {
  let changed = false;
  if (S.online) {
    const now = Date.now();
    for (const e of S.events) {
      if (e.sync === "queued") { e.sync = "sent"; e.at = now; changed = true; }
      else if (e.sync === "sent" && now - e.at > 700) { e.sync = "accepted"; changed = true; }
    }
    for (const s of S.sales) for (const p of s.payments) if (p.status === "pending_confirmation" && !pendingTimers.has(p.payment_id)) askProvider(s, p);
  }
  if (changed) { drawLog(); if (S.screen === "sales" || S.screen === "sale") draw(); drawStatus(); }
}
const pendingTimers = new Set<string>();
function askProvider(s: Sale, p: PaymentPayload): void {   // the sandbox provider answers after a short wait
  pendingTimers.add(p.payment_id);
  window.setTimeout(() => {
    if (!S.online) { pendingTimers.delete(p.payment_id); return; }
    const to: PaymentStatus = S.outcome === "confirm" ? "confirmed" : "failed";
    emit("PaymentStatusChanged", { payment_id: p.payment_id, from_status: p.status, to_status: to, source: "provider_callback", provider_reference: `SBX-${p.payment_id.slice(-8).toUpperCase()}` }, "server");
    p.status = to; pendingTimers.delete(p.payment_id);
    if (S.current === s && S.screen === "waiting") {
      if (to === "confirmed") finish(); else { S.screen = "waiting"; draw(); }
    } else draw();
  }, p.method === "card" ? 1800 : 3200);
}

// ---- sale flow ----------------------------------------------------------------------------------------------------
function recordSale(): Sale {
  if (S.current) return S.current;
  S.receiptNo += 1;
  const sale = salePayload(S.cart, newId(), `${DEVICE}-${S.receiptNo}`, pack().currency);
  emit("SaleRecorded", sale);
  emit("ReceiptIssued", { receipt_id: newId(), sale_id: sale.sale_id, receipt_number_local: sale.receipt_number_local, copy_number: 1, validity: "provisional" });
  const s: Sale = { sale, payments: [], at: Date.now(), voided: false };
  S.sales.unshift(s); S.current = s;
  return s;
}
function pay(method: PaymentMethod, tendered?: number): void {
  const s = recordSale();
  const p = paymentPayload(newId(), s.sale.sale_id, method, s.sale.total);
  s.payments.push(p); emit("PaymentRecorded", p);
  if (method === "cash") { s.tendered = tendered; finish(); return; }
  S.screen = "waiting"; draw();
}
function finish(): void {
  const s = S.current; if (!s) return;
  S.screen = "done"; draw(); printReceipt(s);
}
function newSale(): void { S.cart.clear(); S.current = null; S.input = ""; S.note = ""; S.screen = "sell"; draw(); }
function activePayment(): PaymentPayload | undefined { return S.current?.payments[S.current.payments.length - 1]; }

// ---- the printer --------------------------------------------------------------------------------------------------
function printReceipt(s: Sale): void {
  const paper = $("#paper"), wrap = $("#paperWrap");
  const lines = receiptLines({ shop: SHOP, sale: s.sale, payments: s.payments, tendered: s.tendered, when: clock(s.at, true), money, words: Object.fromEntries(Object.keys(EN).map((k) => [k, t(k)])) });
  paper.innerHTML = `<div class="rhead" role="img" aria-label="LynkOmni">${DATA.brand.receipt}</div><pre class="rtext"></pre><div class="rcut" aria-hidden="true"></div>`;
  wrap.classList.remove("torn"); wrap.hidden = false;
  const pre = paper.querySelector("pre") as HTMLElement;
  $("#printerStatus").textContent = t("printing");
  window.clearInterval(S.timer);
  if (reduced()) { pre.textContent = lines.join("\n"); $("#printerStatus").textContent = ""; return; }
  let i = 0;
  S.timer = window.setInterval(() => {
    pre.textContent += (i ? "\n" : "") + (lines[i] ?? "");
    i += 1;
    if (i >= lines.length) { window.clearInterval(S.timer); $("#printerStatus").textContent = ""; }
  }, 45);
}
function tear(): void { const w = $("#paperWrap"); w.classList.add("torn"); window.setTimeout(() => { w.hidden = true; }, reduced() ? 0 : 450); }

// ---- input: touch screen, physical keypad and keyboard -------------------------------------------------------------
function digit(d: string): void {
  const max = S.screen === "lock" ? 4 : S.screen === "momo" ? 12 : 9;
  if (!["lock", "cash", "momo", "count"].includes(S.screen)) return;
  if (S.input.length + d.length > max) return;
  S.input += d; S.note = "";
  if (S.screen === "lock" && S.input.length === 4) { enter(); return; }
  draw();
}
function clearKey(): void { S.input = S.input.slice(0, -1); draw(); }
function cancelKey(): void {
  const back: Partial<Record<Screen, Screen>> = { cart: "sell", pay: "cart", cash: "pay", momo: "pay", card: "pay", off: "pay", menu: "sell", sales: "menu", sale: "sales", count: "menu" };
  if (S.screen === "lock") { S.input = ""; draw(); return; }
  if (S.screen === "waiting" && activePayment()?.status === "failed") { S.screen = "pay"; draw(); return; }
  const to = back[S.screen]; if (to) { S.screen = to; S.input = ""; S.note = ""; draw(); }
}
function enter(): void {
  switch (S.screen) {
    case "lock": if (S.input === PIN) { S.screen = "sell"; S.input = ""; } else { S.note = t("wrong_pin"); S.input = ""; } break;
    case "sell": if (S.cart.lines().length) S.screen = "cart"; break;
    case "cart": if (S.cart.lines().length) S.screen = "pay"; break;
    case "cash": { const v = Number(S.input || "0"); if (v >= S.cart.total()) { pay("cash", v); return; } S.note = t("not_enough"); break; }
    case "momo": if (S.input.length >= 9) { pay("mobile_money"); return; } break;
    case "done": newSale(); return;
    case "count": S.screen = "menu"; S.input = ""; break;
    default: return;
  }
  draw();
}
function tapCard(): void {
  if (S.screen !== "card") return;
  if (!S.online) { S.note = t("card_online"); draw(); return; }
  S.leds = 0;
  const step = (): void => { S.leds += 1; drawLeds(); if (S.leds < 4) window.setTimeout(step, reduced() ? 0 : 160); else window.setTimeout(() => { S.leds = 0; drawLeds(); pay("card"); }, reduced() ? 0 : 250); };
  step();
}
function scan(): void {
  const p = CATALOG[pick(CATALOG.length)]!;
  const beam = $("#beam"); beam.classList.remove("on"); void beam.offsetWidth; beam.classList.add("on");
  if (S.screen === "lock") return;
  if (!["sell", "cart"].includes(S.screen)) return;
  S.cart.add(p); S.flash = `${t("scan_added")}: ${p.name}`; draw();
  window.setTimeout(() => { S.flash = ""; draw(); }, 1600);
}

// ---- screens ------------------------------------------------------------------------------------------------------
function top(title: string, backable = true): string {
  return `<div class="bar">${backable ? `<button class="iconbtn" data-act="cancel" aria-label="${esc(t("back"))}">${icon("ui-arrow-left")}</button>` : `<span class="logo" role="img" aria-label="LynkOmni">${S.theme === "dark" ? DATA.brand.topDark : DATA.brand.topLight}</span>`}
    <h1>${esc(title)}</h1><button class="iconbtn" data-act="menu" aria-label="${esc(t("menu"))}">${icon("ui-menu")}</button></div>`;
}
function totalBar(label: string, act: string, enabled: boolean): string {
  return `<div class="foot"><div class="sum"><span>${S.cart.count()} ${esc(t("items"))}</span><strong>${esc(money(S.cart.total()))}</strong></div>
    <button class="primary" data-act="${act}" ${enabled ? "" : "disabled"}>${esc(label)}</button></div>`;
}
function amountPad(label: string, value: string): string {
  return `<div class="field"><span>${esc(label)}</span><output aria-live="polite">${esc(value)}</output></div>`;
}
function view(): string {
  const c = S.current;
  switch (S.screen) {
    case "lock":
      return `<div class="lock"><span class="lockmark" role="img" aria-label="LynkOmni">${S.theme === "dark" ? DATA.brand.topDark : DATA.brand.topLight}</span><p class="pname">LynkPOS</p>
        <h1>${esc(t("pin"))}</h1><div class="dots" aria-label="${S.input.length} of 4">${[0, 1, 2, 3].map((i) => `<i class="${i < S.input.length ? "on" : ""}"></i>`).join("")}</div>
        <p class="note" role="alert">${esc(S.note)}</p><p class="keyhint">${icon("ui-info")}${esc(t("use_keys"))}</p>
        <p class="hint">${esc(t("pin_hint"))}</p></div>`;
    case "sell": {
      const cats = ["all", "food", "drinks", "home"];
      const items = CATALOG.filter((p) => S.category === "all" || p.category === S.category);
      return `${top("LynkPOS", false)}<div class="tabs" role="tablist">${cats.map((k) => `<button role="tab" aria-selected="${S.category === k}" data-act="cat:${k}">${esc(t(k))}</button>`).join("")}</div>
        <div class="grid">${items.map((p) => { const q = S.cart.lines().find((l) => l.product.id === p.id); return `<button class="tile" data-act="add:${p.id}"><span class="nm">${esc(p.name)}</span><span class="pr">${esc(money(p.price))}</span>${q ? `<span class="qty" aria-label="in basket">${q.qtyMilli / 1000}</span>` : ""}</button>`; }).join("")}</div>
        ${S.flash ? `<div class="toast" role="status">${icon("ui-check")}${esc(S.flash)}</div>` : ""}${totalBar(t("cart"), "go:cart", S.cart.lines().length > 0)}`;
    }
    case "cart":
      return `${top(t("cart"))}<ul class="lines">${S.cart.lines().map((l) => `<li><div><span class="nm">${esc(l.product.name)}</span><span class="sub">${esc(money(l.product.price))}</span></div>
          <div class="step"><button class="iconbtn" data-act="dec:${l.product.id}" aria-label="Less ${esc(l.product.name)}">${icon(l.qtyMilli > 1000 ? "ui-minus" : "ui-trash")}</button><span>${l.qtyMilli / 1000}</span>
          <button class="iconbtn" data-act="inc:${l.product.id}" aria-label="More ${esc(l.product.name)}">${icon("ui-plus")}</button></div></li>`).join("") || `<li class="empty">${esc(t("empty"))}</li>`}</ul>
        ${S.flash ? `<div class="toast" role="status">${icon("ui-check")}${esc(S.flash)}</div>` : ""}${totalBar(t("charge"), "go:pay", S.cart.lines().length > 0)}`;
    case "pay":
      return `${top(t("payment"))}<div class="due"><span>${esc(t("total"))}</span><strong>${esc(money(S.cart.total()))}</strong></div><p class="ask">${esc(t("how_pay"))}</p>
        <div class="methods">${(["cash", "mobile_money", "card"] as PaymentMethod[]).map((m) => { const ok = methodOk(m); return `<button class="method${ok ? "" : " off"}" data-act="method:${m}">
          ${icon(m === "cash" ? "ui-receipt" : m === "card" ? "ui-pay-card" : "ui-pay-mobile-money")}<span>${esc(t("method_" + m))}</span>${ok ? (m !== "cash" ? `<em>${esc(t("sandbox"))}</em>` : "") : `<em>${esc(t("unavailable"))}</em>`}${icon("ui-chevron-right")}</button>`; }).join("")}</div>`;
    case "cash": {
      const total = S.cart.total(), given = Number(S.input || "0");
      return `${top(t("method_cash"))}<div class="due"><span>${esc(t("total"))}</span><strong>${esc(money(total))}</strong></div>
        ${amountPad(t("cash_given"), S.input ? money(given) : "–")}
        <div class="quick">${quickCash(total, NOTES).map((v) => `<button data-act="cash:${v}">${esc(money(v))}</button>`).join("")}</div>
        <div class="change ${given >= total ? "ok" : ""}"><span>${esc(t("change"))}</span><strong>${given >= total ? esc(money(change(total, given))) : "–"}</strong></div>
        <p class="note" role="alert">${esc(S.note)}</p><div class="foot"><button class="primary" data-act="enter" ${given >= total ? "" : "disabled"}>${esc(t("complete"))}</button></div>`;
    }
    case "momo":
      return `${top(t("method_mobile_money"))}<div class="due"><span>${esc(t("total"))}</span><strong>${esc(money(S.cart.total()))}</strong></div>
        ${amountPad(t("phone"), S.input.replace(/(\d{3})(?=\d)/g, "$1 ") || "–")}<p class="sbx">${icon("ui-info")}${esc(t("sandbox"))}: ${esc(t("test_money"))}</p>
        <div class="foot"><button class="primary" data-act="enter" ${S.input.length >= 9 ? "" : "disabled"}>${esc(t("send_request"))}</button></div>`;
    case "card":
      return `${top(t("method_card"))}<div class="due"><span>${esc(t("total"))}</span><strong>${esc(money(S.cart.total()))}</strong></div>
        <div class="tapgfx" aria-hidden="true"><i></i><i></i><i></i></div><p class="ask">${esc(t("tap_card"))}</p><p class="note" role="alert">${esc(S.note)}</p><p class="sbx">${icon("ui-info")}${esc(t("sandbox"))}: ${esc(t("test_money"))}</p>
        <div class="foot"><button class="ghost" data-act="tapcard">${esc(t("method_card"))}: ${esc(t("sandbox"))}</button></div>`;
    case "waiting": {
      const p = activePayment(); if (!p || !c) return "";
      const st = paymentState(p.status, S.online);
      const failed = st === "failed";
      return `${top(t(p.method === "card" ? "method_card" : "method_mobile_money"), failed)}<div class="due"><span>${esc(t("total"))}</span><strong>${esc(money(c.sale.total))}</strong></div>
        <div class="waitbox">${failed ? "" : `<div class="spinner" aria-hidden="true"></div>`}${st !== "cash" && st !== "credit" ? chip(st) : ""}
        <p>${esc(failed ? t("failed_note") : st === "queued" ? t("queued_note") : p.method === "card" ? t("wait_card") : t("wait_momo"))}</p></div>
        ${st === "queued" ? `<div class="foot"><button class="primary" data-act="newsale">${esc(t("new_sale"))}</button></div>` : ""}
        ${failed ? `<div class="foot two"><button class="ghost" data-act="go:pay">${esc(t("other_method"))}</button><button class="primary" data-act="retry">${esc(t("try_again"))}</button></div>` : ""}`;
    }
    case "done":
      return `<div class="donebox">${icon("ui-check", "bigcheck")}<h1>${esc(t("done"))}</h1>${c ? `<p class="big">${esc(money(c.sale.total))}</p>${c.tendered !== undefined ? `<p>${esc(t("change"))}: <strong>${esc(money(change(c.sale.total, c.tendered)))}</strong></p>` : ""}<p class="sub">${esc(t("receipt"))} ${esc(c.sale.receipt_number_local)}</p>` : ""}</div>
        <div class="foot"><button class="primary" data-act="enter">${esc(t("new_sale"))}</button></div>`;
    case "off":
      return `${top(t("unavailable"))}<div class="offbox"><span class="pic" role="img" aria-label="${esc(DATA.pictures.offAlt)}">${S.theme === "dark" ? DATA.pictures.offDark : DATA.pictures.offLight}</span>
        <p>${esc(pack().ready[S.method]?.message ?? "")}</p></div><div class="foot"><button class="primary" data-act="go:pay">${esc(t("other_method"))}</button></div>`;
    case "menu":
      return `${top(t("menu"))}<ul class="menu"><li><button data-act="go:sales">${icon("ui-receipt")}${esc(t("sales"))}${icon("ui-chevron-right")}</button></li>
        <li><button data-act="go:count">${icon("product-ledger")}${esc(t("count"))}${icon("ui-chevron-right")}</button></li>
        <li><button data-act="lock">${icon("ui-lock")}${esc(t("lock"))}${icon("ui-chevron-right")}</button></li></ul>`;
    case "sales":
      return `${top(t("sales"))}<ul class="lines">${S.sales.map((s, i) => { const p = s.payments[s.payments.length - 1]; const ps = p ? paymentState(p.status, S.online) : null;
          const ev = S.events.find((e) => e.type === "SaleRecorded" && (e.payload as SalePayload).sale_id === s.sale.sale_id);
          return `<li><button class="row" data-act="sale:${i}"><div><span class="nm">${esc(s.sale.receipt_number_local)} · ${esc(clock(s.at))}${s.voided ? ` · ${esc(t("voided"))}` : ""}</span>
          <span class="sub">${p ? esc(t("method_" + p.method)) : ""} ${ps && ps !== "cash" && ps !== "credit" ? chip(ps) : ""}</span></div><div class="rt"><strong>${esc(money(s.sale.total))}</strong>${ev ? chip(ev.sync) : ""}</div></button></li>`; }).join("") || `<li class="empty">${esc(t("no_sales"))}</li>`}</ul>`;
    case "sale": {
      const s = S.sales[S.selected]; if (!s) return "";
      return `${top(`${t("receipt")} ${s.sale.receipt_number_local}`)}<ul class="lines">${s.sale.lines.map((l) => `<li><div><span class="nm">${esc(l.product_name)}</span><span class="sub">${l.quantity_milli / 1000} × ${esc(money(l.unit_price))}</span></div><strong>${esc(money(l.line_total))}</strong></li>`).join("")}</ul>
        ${s.voided ? `<p class="note">${esc(t("voided"))}</p><div class="foot"><button class="ghost" data-act="reprint">${esc(t("reprint"))}</button></div>` : S.note === "void" ? `<p class="ask">${esc(t("void_reason"))}</p><div class="reasons">${["entered_in_error", "customer_cancelled", "price_error", "duplicate"].map((r) => `<button data-act="void:${r}">${esc(t("r_" + r))}</button>`).join("")}</div>`
        : `<div class="foot two"><button class="ghost" data-act="askvoid">${esc(t("void"))}</button><button class="primary" data-act="reprint">${esc(t("reprint"))}</button></div>`}`;
    }
    case "count": {
      const expected = S.sales.filter((s) => !s.voided).flatMap((s) => s.payments).filter((p) => p.status === "cash_received").reduce((a, p) => a + p.amount, 0);
      const got = Number(S.input || "0"), d = got - expected;
      return `${top(t("count"))}<div class="due"><span>${esc(t("expected"))}</span><strong>${esc(money(expected))}</strong></div>${amountPad(t("counted"), S.input ? money(got) : "–")}
        ${S.input ? `<div class="change ${d === 0 ? "ok" : "warn"}"><span>${esc(d === 0 ? t("matches") : d < 0 ? t("short") : t("over"))}</span><strong>${d === 0 ? icon("ui-check") : esc(money(Math.abs(d)))}</strong></div>` : ""}
        <div class="foot"><button class="primary" data-act="enter">${esc(t("ok"))}</button></div>`;
    }
  }
}

function draw(): void {
  const d = $("#display");
  d.className = `display ${S.theme}`;
  d.lang = S.lang === "xx-rtl" ? "ar" : S.lang === "xx" ? "en" : S.lang;
  d.dir = S.lang === "xx-rtl" ? "rtl" : S.lang === "xx" ? "ltr" : PACKS[S.lang]?.dir ?? "ltr";
  d.querySelector(".app")!.innerHTML = view();
  drawStatus();
}
function drawStatus(): void {
  const queued = S.events.filter((e) => e.sync !== "accepted").length;
  const pending = S.events.find((e) => e.sync === "queued") ? "queued" : S.events.find((e) => e.sync === "sent") ? "sent" : "accepted";
  $("#statusbar").innerHTML = `<span>${esc(clock(Date.now()))}</span>${S.realUser ? "" : `<span class="sbxtag">${esc(t("sandbox"))}</span>`}
    <span class="sync" title="${esc(DATA.states[pending]?.meaning ?? "")}">${icon(`status-${pending}`)}${queued ? `<span>${queued}</span>` : ""}</span>
    <span class="net">${icon(S.online ? "ui-sync" : "ui-offline")}<span class="sr">${esc(t(S.online ? "online" : "offline"))}</span></span>`;
}
function drawLeds(): void { document.querySelectorAll<HTMLElement>(".leds i").forEach((el, i) => el.classList.toggle("on", i < S.leds)); }
function drawLog(): void {
  const box = $("#log");
  box.innerHTML = S.events.slice(0, 40).map((e) => `<li><span class="n">#${e.n}</span><code>${esc(e.type)}</code><span class="org">${e.origin}</span>${chip(e.sync)}
    <details><summary>payload</summary><pre>${esc(JSON.stringify(e.payload, null, 1))}</pre></details></li>`).join("") || `<li class="empty">No events yet. Make a sale.</li>`;
}

function act(a: string): void {
  const [k, v = ""] = a.split(/:(.*)/s);
  try {
    if (k && /^d\d+$/.test(k)) { digit(k.slice(1)); return; }
    switch (k) {
      case "clear": clearKey(); return;
      case "cancel": cancelKey(); return;
      case "enter": enter(); return;
      case "menu": if (S.screen !== "lock") { S.screen = "menu"; draw(); } return;
      case "lock": S.screen = "lock"; S.input = ""; draw(); return;
      case "cat": S.category = v; draw(); return;
      case "add": { const p = CATALOG.find((x) => x.id === v); if (p) S.cart.add(p); draw(); return; }
      case "inc": { const l = S.cart.lines().find((x) => x.product.id === v); if (l) S.cart.setQty(v, l.qtyMilli + 1000); draw(); return; }
      case "dec": { const l = S.cart.lines().find((x) => x.product.id === v); if (l) S.cart.setQty(v, l.qtyMilli - 1000); if (!S.cart.lines().length) S.screen = "sell"; draw(); return; }
      case "go": S.screen = v as Screen; S.input = ""; S.note = ""; draw(); return;
      case "method": {
        const m = v as PaymentMethod; S.method = m; S.input = "";
        S.screen = !methodOk(m) ? "off" : m === "cash" ? "cash" : m === "card" ? "card" : "momo"; draw(); return;
      }
      case "cash": S.input = v; draw(); return;
      case "tapcard": tapCard(); return;
      case "newsale": newSale(); return;
      case "retry": { const s = S.current; const p = activePayment(); if (s && p) { const q = paymentPayload(newId(), s.sale.sale_id, p.method, s.sale.total); s.payments.push(q); emit("PaymentRecorded", q); draw(); } return; }
      case "sale": S.selected = Number(v); S.note = ""; S.screen = "sale"; draw(); return;
      case "reprint": { const s = S.sales[S.selected]; if (s) printReceipt(s); return; }
      case "askvoid": S.note = "void"; draw(); return;
      case "void": { const s = S.sales[S.selected]; if (s && !s.voided) { emit("SaleVoided", { sale_id: s.sale.sale_id, reason_code: v }); s.voided = true; } S.note = ""; draw(); return; }
    }
  } catch (e) { S.note = e instanceof PosError ? e.reason : String(e); draw(); }
}

// ---- controls beside the device ------------------------------------------------------------------------------------
function wire(): void {
  document.addEventListener("click", (ev) => {
    const el = (ev.target as HTMLElement).closest<HTMLElement>("[data-act]");
    if (el && !(el as HTMLButtonElement).disabled) act(el.dataset["act"] ?? "");
  });
  $("#tapzone").addEventListener("click", tapCard);
  $("#slot").addEventListener("click", tapCard);
  $("#scanKey").addEventListener("click", scan);
  $("#tearBtn").addEventListener("click", tear);
  const bind = (id: string, f: (el: HTMLInputElement) => void): void => { const el = $<HTMLInputElement>(id); el.addEventListener("change", () => f(el)); };
  bind("#cOnline", (el) => { S.online = el.checked; drawStatus(); draw(); });
  bind("#cDark", (el) => { S.theme = el.checked ? "dark" : "light"; draw(); });
  bind("#cReal", (el) => { S.realUser = el.checked; draw(); });
  const country = $<HTMLSelectElement>("#cCountry");
  country.innerHTML = DATA.packOrder.map((c) => { const p = DATA.packs[c] as CountryPack; return `<option value="${esc(c)}">${esc(p.sample ? t("sample_country") : p.name)}</option>`; }).join("");
  country.addEventListener("change", (e) => { S.country = (e.target as HTMLSelectElement).value; draw(); });
  bind("#cFail", (el) => { S.outcome = el.checked ? "fail" : "confirm"; });
  const sel = $<HTMLSelectElement>("#cLang");
  sel.insertAdjacentHTML("afterbegin", Object.entries(PACKS).map(([code, p]) => `<option value="${esc(code)}" lang="${esc(code)}" dir="${p.dir}">${esc(p.native)}</option>`).join(""));
  sel.value = "en";
  $<HTMLSelectElement>("#cLang").addEventListener("change", (e) => { S.lang = (e.target as HTMLSelectElement).value as Lang; draw(); });
  document.addEventListener("keydown", (e) => {
    if ((e.target as HTMLElement).closest("input,select,textarea,summary")) return;
    if (/^\d$/.test(e.key)) { digit(e.key); e.preventDefault(); }
    else if (e.key === "Backspace") { clearKey(); e.preventDefault(); }
    else if (e.key === "Enter" && !(e.target as HTMLElement).closest("button")) { enter(); e.preventDefault(); }
    else if (e.key === "Escape") { cancelKey(); e.preventDefault(); }
  });
  const fit = (): void => {   // scale the whole device down on small screens, never up
    const rig = $("#rig"), dev = $("#device");
    const s = Math.min(1, (rig.clientWidth - 8) / dev.offsetWidth);
    document.documentElement.style.setProperty("--fit", String(s));
  };
  addEventListener("resize", fit); fit();
  window.setInterval(tick, 350);
  window.setInterval(drawStatus, 30000);
}

wire(); draw(); drawLog();
