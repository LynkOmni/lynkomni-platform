/** LynkPOS customer-facing display, standalone (S3; 42 J added emulator): a small screen on a pole that shows only what the
 *  till sends: welcome, each line as it is added, the total with a labelled second-currency estimate, scan to pay with the
 *  honest state, and thank you. The buttons beside it play the cashier's part. "Powered by LynkOmni" follows billing FEATURES
 *  powered_by and never shows on the payment step. */
import { Cart, qtyText } from "../../../ts/src/pos.js";
import type { UserState } from "../../../ts/src/pos.js";
import { secondCurrency } from "../../../ts/src/business.js";
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, newId, panelChange, panelHtml, reducedMotion, stateButtons } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";
import { brandMark } from "../../../ts/src/brand.js";
import { DeviceMode, wireDevice } from "../../../ts/src/devicemode.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";
import { PeopleHub, afterPaymentRating } from "../../../ts/src/peoplehub.js";

declare const DATA: Build & { fx: Record<string, number> };
const TIERS = ["free", "plus", "pro", "max"] as const;
type Step = "welcome" | "basket" | "pay" | "thanks";
const S: PanelState & { step: Step; payState: UserState; ticks: number; rated: number | null } = { online: true, fail: false, type: "shop", tier: "free", country: "", realUser: false, practice: false, dark: false, lang: "en", step: "welcome", payState: "sent", ticks: 0, rated: null };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const icon = (id: string): string => `<span class="ic" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); });
const ITEMS = [["p_bread", 1000], ["p_milk", 600], ["p_eggs", 4500], ["p_soap", 500]] as const;
const products = ITEMS.map(([name, price]) => ({ id: newId(), name, price, category: "food" }));
const cart = new Cart();
/** LynkSurvey's rating after payment (NEW UPDATE 4, section 3): one tap on a touch screen, the QR on a screen that only shows.
 *  Never required, never before the payment is confirmed; the answer is saved here and sent when the link is back. Its words are
 *  this display's own copies of the shared "ppl_" words (same text and translation), so the display does not carry the whole shell. */
const PH = new PeopleHub((type, payload, origin) => LOG.emit(type, payload, origin));
const tt = (k: string, v?: Record<string, string | number>): string => t(k, v ?? {});

function display(): string {
  const cur = C.pack().currency, total = cart.total();
  const pb = S.tier === "free" && S.step !== "pay" ? `<small class="pb">${esc(t("powered_by"))} LynkOmni</small>` : "";
  if (S.step === "welcome") return `<div class="cwel">${brandMark(DATA.brand.places, "customer-welcome", S.dark, "cmark")}<h2>${esc(t("welcome"))}</h2><p>${esc(t("sample_shop"))}</p>${pb}</div>`;
  if (S.step === "thanks") return `<div class="cwel"><span class="bigcheck">${icon("ui-check")}</span><h2>${esc(t("thank_you_visit"))}</h2><p>${esc(C.money(total))}</p>${afterPaymentRating(PH, DM.touch(), S.rated, tt, (id) => icon(id))}${pb}</div>`;
  const second = total ? secondCurrency(total, cur, cur === "USD" ? "EUR" : "USD", (m, a, b) => Math.round(m * ((DATA.fx[b] ?? 1) / (DATA.fx[a] ?? 1)))) : null;
  return `<div class="cbas"><ul>${cart.lines().map((l) => `<li><span>${esc(t(l.product.name))}</span><span>${qtyText(l.qtyMilli)} × ${esc(C.money(l.product.price))}</span><strong>${esc(C.money(l.product.price * l.qtyMilli / 1000))}</strong></li>`).join("")}</ul>
    <div class="ctot"><span>${esc(t("your_total"))}</span><strong>${esc(C.money(total))}</strong></div>${second ? `<p class="sec">${esc(t("second_currency", { amount: C.money(second.amount, second.currency), currency: cur }))}</p>` : ""}
    ${S.step === "pay" ? `<div class="cpay"><span class="qr">${icon("ui-qr")}</span><div><strong>${esc(t("pay_by_qr"))}</strong>${chip(S.payState)}<p>${esc(t("not_proof"))}</p></div></div>` : ""}${pb}</div>`;
}
function till(): string {
  return `<h3>${esc(t("customer_display"))}</h3><div class="tbtns">${products.map((p) => `<button data-act="add:${p.id}">+ ${esc(t(p.name))}</button>`).join("")}</div>
    <div class="tbtns"><button data-act="pay" ${cart.lines().length ? "" : "disabled"}>${esc(t("charge"))}</button><button data-act="clear">${esc(t("new_sale"))}</button></div>
    <div class="tbtns"><button data-act="afterpay" aria-pressed="${PH.afterPayment}">${esc(t("ppl_after_payment"))}: ${esc(t(PH.afterPayment ? "ppl_on" : "ppl_off"))}</button></div>`;
}
/** Touch or display only (DEVICE 48.17.14): the customer display shows the same screens either way; without touch nothing on it
 *  needs pressing (the till drives it), so it has no pad. */
const DM = new DeviceMode(DEVICES, "customer-display");
const DEV = wireDevice(DM, { t, icon: (id) => `<span class="ic" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`, screen: () => document.getElementById("screen"), pad: () => null, back: () => undefined, redraw: () => draw(), rtl: () => document.getElementById("screen")?.dir === "rtl" });
function draw(): void {
  const el = $("#screen"); DEV.draw(el); el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W); el.innerHTML = display();
  const tl = $("#till"); applyRoot(tl, W); tl.innerHTML = till();
}
function act(a: string): void {
  const [k = "", v = ""] = a.split(":");
  if (k === "add") { const p = products.find((x) => x.id === v); if (p) { cart.add(p); S.step = "basket"; } }
  if (k === "pay" && cart.lines().length) {
    S.step = "pay"; S.payState = S.online ? "sent" : "queued"; LOG.emit("PaymentRecorded", { payment_id: newId(), method: "other", amount: cart.total(), status: "pending_confirmation", currency: C.pack().currency });
    window.setTimeout(() => { if (!S.online) return; S.payState = S.fail ? "failed" : "confirmed"; LOG.emit("PaymentStatusChanged", { to_status: S.fail ? "failed" : "confirmed", source: "provider_callback" }, "server"); if (!S.fail) window.setTimeout(() => { S.step = "thanks"; draw(); }, 900); draw(); }, reducedMotion() ? 300 : 1800);
  }
  if (k === "clear") { cart.clear(); S.step = "welcome"; S.rated = null; }
  if (k === "ppl" && a.startsWith("ppl:rate:") && S.step === "thanks" && S.rated === null) { const n = Number(a.slice(9)); if (PH.rate(n, "pos", S.lang)) S.rated = n; }
  if (k === "afterpay") PH.afterPayment = !PH.afterPayment;
  draw();
}
function panel(): void {
  $("#panel").innerHTML = panelHtml(["online", "fail", "plan", "country", "dark", "lang"], S, W, C, { tiers: TIERS }) + DEV.control();
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), ["welcome", "basket", "pay", "thanks"], (k) => { if (!cart.lines().length && products[0] && products[1]) { cart.add(products[0]); cart.add(products[1], 2000); } S.step = k as Step; S.payState = "sent"; draw(); });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? "";
  panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (b && !b.hasAttribute("disabled")) act(b.dataset["act"] ?? ""); });
  $("#panel").addEventListener("change", (e) => { if (DEV.change(e.target as HTMLElement)) return; if (panelChange(e.target as HTMLSelectElement, S, DATA, { tiers: TIERS })) panel(); draw(); });
  window.setInterval(() => { S.ticks += 1; LOG.tick(S.online, false, S.ticks, () => undefined); }, 400);
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 760);
}
main();
