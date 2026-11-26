/** LynkPOS handheld terminal emulator. Draws an original LynkOmni handheld (printer, screen, keypad, tap area, card slot,
 *  scan key) and runs the real sale rules from ts/src/pos.ts against sandbox providers. Draft until a designer reviews it.
 *  Built into one offline HTML file by web/build.mjs. Colours come only from the design tokens (CSS variables). */
import { hintFor } from "../../../ts/src/hints.js";
import { phoneFieldHtml, wireFields, countryNamer, type FieldCtx } from "../../../ts/src/fields.js";
import { emailFieldHtml } from "../../../ts/src/emailfield.js";
import { noticeHtml, wireNotices } from "../../../ts/src/errorbox.js";
import { Cart, PosError, change, formatMoney, paymentPayload, paymentState, quickCash, receiptLines, salePayload, uuid7 } from "../../../ts/src/pos.js";
import type { PaymentMethod, PaymentPayload, PaymentStatus, Product, SalePayload, UserState } from "../../../ts/src/pos.js";
import { HANDHELD_TILES } from "../../../ts/src/business.js";
import { AGENT_SERVICES, COLLECTION_KINDS, FINANCE_PRODUCTS, combinedLimits, commission, limitCheck, mayHandOverCash } from "../../../ts/src/agent.js";
import type { AgentState, Limits } from "../../../ts/src/agent.js";
import { TEST_LANGS, esc, newId, pseudo, publicId, randomBelow } from "../../../ts/src/emulator.js";
import { brandMark } from "../../../ts/src/brand.js";
import { shortFooterHtml } from "../../../ts/src/footer.js";
import type { BrandPlaces } from "../../../ts/src/brand.js";
import { DeviceShell, designedState, screenArticles } from "../../../ts/src/deviceshell.js";
import type { DsScreen, StatePictures } from "../../../ts/src/deviceshell.js";
import type { Entry } from "../../../ts/src/shell.js";
import { DeviceMode, wireDevice } from "../../../ts/src/devicemode.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";
import { StaffLock, deviceBanners, needsManager, raiseLocal, staffPicker, staffWhoRow, lockWhoButton } from "../../../ts/src/devicekit.js";
import type { Line } from "../../../ts/src/notify.js";
import { buildPack } from "../../../ts/src/assist.js";
import { PeopleHub } from "../../../ts/src/peoplehub.js";
import { pairCode, quCounterView, quPaper, quReceptionView } from "../../../ts/src/queuedesk.js";
import type { QuLook, QuPlan } from "../../../ts/src/queuedesk.js";
import type { SvPlan } from "../../../ts/src/surveydesk.js";
import { atDoor, wasThisYou } from "../../../ts/src/attenddesk.js";
import type { AtLook, AtPlan, AtTier } from "../../../ts/src/attenddesk.js";
import { ticketNumber } from "../../../ts/src/queue.js";
import { EmKit, kitFor, wireKit } from "../../../ts/src/emkit.js";
import { EMULATOR_REGISTER } from "../../../ts/src/emulators.generated.js";
import { watchNames } from "../../../ts/src/names.js";
import { mayShow, slotHtml, whyHtml } from "../../../ts/src/ads.js";
import type { Ad, AdLook } from "../../../ts/src/ads.js";

interface BuildData {
  icons: Record<string, string>;
  brand: { body: string; receipt: string; places: BrandPlaces };
  pictures: { offLight: string; offDark: string; offAlt: string };
  states: Record<string, { label: string; meaning: string }>;
  statePictures: StatePictures;
  /** Every country pack, the neutral sample pack first (Step 0): the chooser never opens on a real country. */
  packs: Record<string, CountryPack>;
  packOrder: string[];
  i18n: Record<string, { native: string; dir: "ltr" | "rtl"; texts: Record<string, string> }>;
  people: { attend: Record<AtTier, AtPlan>; queue: Record<AtTier, QuPlan>; survey: Record<AtTier, SvPlan> };
}
interface CountryPack {
  code: string; name: string; currency: string; tz: string; locale: string; sample: boolean;
  ready: Record<string, { ok: boolean; message: string }>;
  services: { service: string; name: string; icon: string; state: "available" | "coming_soon" }[];
}
declare const DATA: BuildData;
/** The country the emulator shows. Read from the country pack and the provider ledger; nothing about a country lives in this code. */
const pack = (): CountryPack => DATA.packs[S.country] ?? DATA.packs[DATA.packOrder[0] ?? ""] as CountryPack;

type Screen = "lock" | "home" | "sell" | "cart" | "pay" | "cash" | "momo" | "card" | "waiting" | "done" | "off" | "menu" | "sales" | "sale" | "count" | "shopqr"
  | "pick" | "agent" | "agentdone" | "code" | "credit" | "staff" | "door" | "reception" | "counter";
type Step = "number" | "amount" | "confirm";
interface Req { id: string; service: string; amount: number; fee: number; commission: number; state: AgentState; ref: string }
type Lang = string;   // a language code from design/fonts/scripts.v1.json, or one of TEST_LANGS
interface Ev { n: number; type: string; origin: "device" | "server"; payload: unknown; sync: UserState; at: number }
interface Sale { sale: SalePayload; payments: PaymentPayload[]; tendered?: number; at: number; voided: boolean; receiptId: string }

/** Screen words: English source in strings.en.json, every other language from the machine-translated language packs in
 *  i18n/<lang>.json (tools/translation/build_packs.py), all embedded by web/build.mjs so every language works offline. */
const PACKS = DATA.i18n;
const EN: Record<string, string> = PACKS.en?.texts ?? {};

/** An unbiased index below n (rejection sampling: bytes that would favour the low indexes are thrown away). */
const pickIndex = (n: number): number => randomBelow(n);
const CATALOG: Product[] = [
  ["Rice 1 kg", 1500, "food", "6000000000011"], ["Sugar 1 kg", 1400, "food", "6000000000028"], ["Beans 1 kg", 1200, "food", "6000000000035"],
  ["Cooking oil 1 L", 3200, "food", "6000000000042"], ["Bread", 1000, "food", "6000000000059"], ["Eggs, tray of 30", 4500, "food", "6000000000066"],
  ["Milk 500 ml", 600, "drinks", "6000000000073"], ["Water 1.5 L", 700, "drinks", "6000000000080"], ["Soda 300 ml", 500, "drinks", "6000000000097"],
  ["Tea leaves 100 g", 900, "drinks", "6000000000103"], ["Soap bar", 500, "home", "6000000000110"], ["Matches, pack", 300, "home", "6000000000127"],
].map(([name, price, category, barcode]) => ({ id: newId(), name: String(name), price: Number(price), category: String(category), barcode: String(barcode) }));
const NOTES = [500, 1000, 2000, 5000, 10000];
const SHOP = "Sample shop";
const DEVICE = "PT";
/** MASTER UPDATE section 3: each person their own PIN on the device (samples; a real device keeps only a slow salted hash).
 *  8642 is the cashier's sample duress PIN: it opens the quiet limited view and the alert leaves by the first path out. */
const STAFF = new StaffLock([
  { person: "c1", name: "Aline", role: "cashier", pin: "1234", duress: "8642" },
  { person: "m1", name: "Eric", role: "manager", pin: "2580" },
  { person: "o1", name: "Grace", role: "owner", pin: "4719" },
]);

// ADS UPDATE 79 (section 4 row 79.10): the idle screen and after a sale on LynkPOS Free; the receipt line only once the shop hosts it
const AD = { on: false, host: false, why: false, reported: false };
const SAMPLE_AD = (): Ad => ({ id: "sample-ad", text: t("ad_sample_text"), sample: true });
const adLook = (): AdLook => ({ t, esc, icon: (id) => icon(id) });
function adBlock(place: string, screen: string): string {
  if (!mayShow(place, { screen, country_on: AD.on, hosting: AD.host })) return "";
  return slotHtml(place, SAMPLE_AD(), adLook()) + (AD.why ? whyHtml(adLook()) : "") + (AD.reported ? `<p class="ad-why" role="status">${esc(t("ad_reported"))}</p>` : "");
}
const receiptAd = (): { label: string; text: string } | null =>
  mayShow("receipt_footer", { screen: "receipt", country_on: AD.on, hosting: AD.host }) ? { label: `${t("ad_sponsored")} · ${t("ad_sample")}`, text: SAMPLE_AD().text } : null;
const S = {
  screen: "lock" as Screen, lang: "en" as Lang, theme: "light" as "light" | "dark", online: true, realUser: false, country: "", outcome: "confirm" as "confirm" | "fail",
  input: "", note: "", category: "all", cart: new Cart(), current: null as Sale | null, method: "cash" as PaymentMethod, sales: [] as Sale[],
  events: [] as Ev[], receiptNo: 0, selected: -1, timer: 0, leds: 0, flash: "",
  tileGroup: "" as string, service: "bills", step: "number" as Step, number: "", amount: 0, req: null as Req | null, lowLiteracy: false, partnerFloat: 300_000, usedToday: 0,
  credit: [{ name: "Aline", owes: 4500 }, { name: "Eric", owes: 12000 }, { name: "Grace", owes: 0 }],
  // MASTER UPDATE section 3: who is signed in, the quiet limited view, the manager's approval, the device's bell and messages
  who: "c1", role: "cashier", view: "full" as "full" | "limited", picking: false, pinNote: "", approve: null as null | { act: "void"; reason: string; amount: number; pin: string; asked: boolean },
  lines: [] as Line[], wiped: false, staffSheet: null as null | { person: string; byPin: string; newPin: string; note: string }, sendTo: "" as "" | "text" | "email", rcptTo: "", rcptCc: "", sent: "",
};
/** Agent point on the handheld (blueprint 42 I): one sandbox partner; its float sits in the agent's own account there and is only read. */
const PARTNER_LIMITS: Limits = { per_transaction: 200_000, per_day: 2_000_000 };
const PARTNER_BPS = 100;
/** The low-literacy picture set for the 12 tiles (43 G, 44 L row 1; lynkomni-icons lit-*): the word always sits beside it. */
const TILE_ICON: Record<string, string> = { sell: "lit-sell", agent: "lit-agent", collect: "lit-collect", bills: "lit-bills", airtime_data: "lit-airtime-data", tickets: "lit-tickets", government: "lit-government",
  remittances: "lit-remittance", partner_finance: "lit-partner-finance", customers_credit: "lit-customers-credit", reports: "lit-reports", settings: "lit-settings" };
const TILE_SERVICES: Record<string, readonly string[]> = { agent: ["cash_withdrawal", "cash_deposit", "money_transfer"], collect: COLLECTION_KINDS, partner_finance: FINANCE_PRODUCTS };
const DIRECT: Record<string, string> = { bills: "bills", airtime_data: "airtime_data", tickets: "tickets", government: "government_payment", remittances: "remittance" };

const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const isTest = (): boolean => (TEST_LANGS as readonly string[]).includes(S.lang);
const t = (k: string, vars: Record<string, string | number> = {}): string => { const en = EN[k] ?? k; const raw = isTest() ? pseudo(en) : PACKS[S.lang]?.texts[k] ?? en; return raw.replace(/\{(\w+)\}/g, (m, v: string) => (v in vars ? String(vars[v]) : m)); };
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
  if (!S.online && type === "SaleRecorded") bellAdd("sync_retried", t("ln_sync"));     // the device's own bell while offline
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
  const s: Sale = { sale, payments: [], at: Date.now(), voided: false, receiptId: publicId("RCP") };   // the public receipt id (LORCP-) the verify QR opens
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
// ---- messages (section 4C point 2): every note through the shared part, with what to do next; a sale error never shows its code
let NOTE_HOW = "", PIN_HARD = false;
function setNote(text: string, how: string): void { S.note = text; NOTE_HOW = how; }
const POS_HOW: Record<string, string> = { invalid_amount: "fd_check_retry", empty_cart: "fd_add_item", bad_receipt_number: "fd_check_retry", not_enough_cash: "fd_enter_cash" };
const noteBox = (): string => S.note && S.note !== "void" ? noticeHtml(t, { level: "error", text: S.note, how: NOTE_HOW || t("fd_check_retry") }) : `<p class="note" aria-live="polite"></p>`;
const pinBox = (): string => S.pinNote ? noticeHtml(t, PIN_HARD ? { level: "error", text: S.pinNote, how: t("fd_ask_manager") } : { level: "warning", text: S.pinNote, how: t("fd_type_again") }) : "";
function newSale(): void { S.cart.clear(); S.current = null; S.input = ""; S.note = ""; S.sent = ""; S.sendTo = ""; S.screen = "sell"; draw(); }
function activePayment(): PaymentPayload | undefined { return S.current?.payments[S.current.payments.length - 1]; }

// ---- the printer --------------------------------------------------------------------------------------------------
/** LynkAttend and LynkQueue on this terminal (ts/src/peoplehub.ts): the same engine as the Business app, writing to this log. */
const PH = new PeopleHub((type, payload, origin) => emit(type, payload, origin), Date.now, DATA.people.attend, DATA.people.queue, DATA.people.survey);
PH.q.ownPrinter = true;                                                 // the terminal prints tickets on its own receipt printer
/** How the LynkAttend screens look on this terminal, and the door speaking the person's own language after the PIN. */
const atLook = (): AtLook => ({ t, icon, clock: (ms) => clock(ms), money: (c) => formatMoney(c, "USD", locale()), online: S.online, partner: !S.realUser, mayManage: S.role === "owner" || S.role === "manager" });
const SPEAK = { t: (lang: string) => (k: string, vars: Record<string, string | number> = {}): string => (isTest() ? t(k, vars) : (PACKS[lang]?.texts[k] ?? EN[k] ?? k).replace(/\{(\w+)\}/g, (m, v: string) => (v in vars ? String(vars[v]) : m))),
  dir: (lang: string): "ltr" | "rtl" => (S.lang === "xx-rtl" ? "rtl" : isTest() ? "ltr" : PACKS[lang]?.dir ?? "ltr"), code: (lang: string): string => (isTest() ? "en" : lang) };
const phCtx = (): { online: boolean; redraw: () => void; language: string } => ({ online: S.online, redraw: draw, language: S.lang });
/** How the LynkQueue screens look on this terminal: the ticket prints on the receipt printer, so it is not drawn on the screen too. */
const quLook = (): QuLook => ({ ...atLook(), place: SHOP, powered: `<small class="pb">${esc(t("ppl_qu_powered", { brand: "LynkOmni" }))}</small>`, paper: false });
const quCtx = (): { online: boolean; partner: boolean; pairCode: () => string; redraw: () => void } => ({ online: S.online, partner: !S.realUser, pairCode, redraw: draw });
/** The ticket on the receipt printer: the place, the section, the big number, its QR, the time and the place in the queue (no name, no phone number). */
function printTicket(): void {
  const tk = PH.q.tk(PH.q.printed); if (!tk) return;
  const paper = $("#paper"), wrap = $("#paperWrap");
  paper.innerHTML = `${quPaper(PH.q, tk, { ...quLook(), paper: true })}<div class="rcut" aria-hidden="true"></div>`;
  wrap.classList.remove("torn"); wrap.hidden = false;
}
function printReceipt(s: Sale): void {
  const paper = $("#paper"), wrap = $("#paperWrap");
  const lines = receiptLines({ shop: SHOP, sale: s.sale, payments: s.payments, tendered: s.tendered, when: clock(s.at, true), money, words: Object.fromEntries(Object.keys(EN).map((k) => [k, t(k)])), ad: receiptAd() });
  paper.innerHTML = `<div class="rhead" role="img" aria-label="LynkOmni">${DATA.brand.receipt}</div><pre class="rtext"></pre><div class="rqr" hidden><span class="qr" aria-hidden="true">${DATA.icons["ui-qr"] ?? ""}</span><span>${esc(t("verify_receipt"))}</span><span>${esc(s.receiptId)}</span></div><div class="rcut" aria-hidden="true"></div>`;
  const qr = paper.querySelector(".rqr") as HTMLElement;   // 38 C, 7: every receipt carries a QR the customer can scan to check it
  wrap.classList.remove("torn"); wrap.hidden = false;
  const pre = paper.querySelector("pre") as HTMLElement;
  $("#printerStatus").textContent = t("printing");
  window.clearInterval(S.timer);
  if (reduced()) { pre.textContent = lines.join("\n"); qr.hidden = false; $("#printerStatus").textContent = ""; return; }
  let i = 0;
  S.timer = window.setInterval(() => {
    pre.textContent += (i ? "\n" : "") + (lines[i] ?? "");
    i += 1;
    if (i >= lines.length) { window.clearInterval(S.timer); qr.hidden = false; $("#printerStatus").textContent = ""; }
  }, 45);
}
function tear(): void { const w = $("#paperWrap"); w.classList.add("torn"); window.setTimeout(() => { w.hidden = true; }, reduced() ? 0 : 450); }

// ---- input: touch screen, physical keypad and keyboard -------------------------------------------------------------
function digit(d: string): void {
  if (S.screen === "door") { PH.doorDigit(d); draw(); return; }      // the door's PIN and IDCN: dots only, never the digits
  const max = S.screen === "lock" ? STAFF.lengthOf(S.who) : S.screen === "momo" || (S.screen === "agent" && S.step === "number") ? 12 : S.screen === "code" ? 8 : 9;
  if (!["lock", "cash", "momo", "count", "agent", "code", "credit"].includes(S.screen) || (S.screen === "agent" && S.step === "confirm")) return;
  if (S.input.length + d.length > max) return;
  S.input += d; S.note = "";
  if (S.screen === "lock" && S.input.length === STAFF.lengthOf(S.who)) { enter(); return; }   // full: checked at once, never a digit more
  draw();
}
function clearKey(): void { if (S.screen === "door") { PH.doorBack(); draw(); return; } S.input = S.input.slice(0, -1); draw(); }
function cancelKey(): void {
  const back: Partial<Record<Screen, Screen>> = { sell: "home", cart: "sell", pay: "cart", cash: "pay", momo: "pay", card: "pay", off: "pay", menu: "home", sales: "home", sale: "sales", count: "menu", shopqr: "menu",
    pick: "home", agent: S.tileGroup ? "pick" : "home", agentdone: "home", code: "pick", credit: "home", door: "menu", reception: "menu", counter: "menu" };
  if (S.screen === "agent" && S.step !== "number") { S.step = S.step === "confirm" ? "amount" : "number"; S.input = S.step === "number" ? S.number : String(S.amount || ""); draw(); return; }
  if (S.screen === "lock") { S.input = ""; draw(); return; }
  if (S.screen === "door" && PH.door.step !== "pin") { PH.doorReset(); draw(); return; }   // Back at the door starts again for the next person
  if (S.screen === "waiting" && activePayment()?.status === "failed") { S.screen = "pay"; draw(); return; }
  const to = back[S.screen]; if (to) { S.screen = to; S.input = ""; S.note = ""; draw(); }
}
function enter(): void {
  switch (S.screen) {
    case "lock": { signIn(); return; }
    case "door": if (PH.door.step === "done") PH.doorReset(); else PH.doorIdcn(); break;                    // OK: check in with the IDCN typed, or the next person
    case "reception": PH.q.act("qu:issue", quCtx()); printTicket(); break;
    case "counter": { const c = PH.q.counter(PH.q.counterPick); if (c && !c.serving) PH.q.callNext(c.id); else if (c) PH.q.finish(c.id, "served"); break; }
    case "agent":
      if (S.step === "number") { if (S.input.length < 4) return; S.number = S.input; S.input = ""; S.step = (FINANCE_PRODUCTS as readonly string[]).includes(S.service) ? "confirm" : "amount"; break; }
      if (S.step === "amount") { const a = Number(S.input || "0"); if (!a) return; if (limitCheck(a, S.usedToday, combinedLimits(PARTNER_LIMITS)) !== "ok") { setNote(t("limit_exceeded"), t("fd_smaller_amount")); break; } S.amount = a; S.input = ""; S.step = "confirm"; break; }
      agentSend(); return;
    case "agentdone": S.screen = "home"; break;
    case "code": redeem(); return;
    case "credit": { const c = S.credit[S.selected]; const a = Number(S.input || "0"); if (c && a > 0 && a <= c.owes) { c.owes -= a; emit("CustomerCreditPaid", { payment_id: newId(), credit_id: newId(), amount: a, currency: pack().currency, method: "cash" }); S.flash = t("saved"); S.input = ""; } break; }
    case "sell": if (S.cart.lines().length) S.screen = "cart"; break;
    case "cart": if (S.cart.lines().length) S.screen = "pay"; break;
    case "cash": { const v = Number(S.input || "0"); if (v >= S.cart.total()) { pay("cash", v); return; } setNote(t("not_enough"), t("fd_enter_cash")); break; }
    case "momo": if (S.input.length >= 9) { pay("mobile_money"); return; } break;
    case "done": newSale(); return;
    case "count": {
      const expected = S.sales.filter((x) => !x.voided).flatMap((x) => x.payments).filter((p) => p.status === "cash_received").reduce((a, p) => a + p.amount, 0);
      if (S.input && Number(S.input) !== expected) bellAdd("cash_difference", t("ln_cash", { amount: money(Math.abs(Number(S.input) - expected)) }));
      S.screen = "menu"; S.input = ""; break;
    }
    case "home": S.screen = "sell"; break;
    default: return;
  }
  draw();
}
function signIn(): void {
  const r = STAFF.signIn(S.who, S.input, Date.now());
  S.input = "";
  if (r.ok) { S.role = r.role; S.view = r.view; S.screen = "home"; S.note = ""; S.pinNote = ""; sendAlerts(); draw(); return; }
  S.pinNote = r.reason === "wrong" ? t("dk_tries_left", { n: r.left ?? 0 }) : r.reason === "wait" ? t("dk_wait", { s: r.seconds ?? 0 }) : t(r.reason === "hard_locked" ? "dk_hard_locked" : "locked_by_owner"); PIN_HARD = r.reason !== "wrong" && r.reason !== "wait";
  if (r.reason === "hard_locked") { emit("DeviceHardLocked", { device: DEVICE }); bellAdd("device_hard_locked", t("dk_hard_locked")); }
  draw();
}
/** The duress alert leaves silently by the first path that appears; the device's screen never shows it. */
function sendAlerts(): void { const n = STAFF.pathsOut(S.online ? ["internet"] : []); for (let i = 0; i < n; i++) emit("DuressSignalled", { device_id: DEVICE, person: S.who, path: "internet", at: Date.now() }, "server"); }
function bellAdd(kind: string, title: string, record?: string): void { S.lines = raiseLocal(S.lines, kind, title, Date.now(), record); }
const KP = (): ReturnType<typeof buildPack> => buildPack({ ...EN, ...(PACKS[S.lang]?.texts ?? {}) });
function tapCard(): void {
  if (S.screen !== "card") return;
  if (!S.online) { setNote(t("card_online"), t("fd_go_online")); draw(); return; }
  S.leds = 0;
  const step = (): void => { S.leds += 1; drawLeds(); if (S.leds < 4) window.setTimeout(step, reduced() ? 0 : 160); else window.setTimeout(() => { S.leds = 0; drawLeds(); pay("card"); }, reduced() ? 0 : 250); };
  step();
}
function scan(): void {
  const p = CATALOG[pickIndex(CATALOG.length)]!;
  const beam = $("#beam"); beam.classList.remove("on"); void beam.offsetWidth; beam.classList.add("on");
  if (S.screen === "lock") return;
  if (!["sell", "cart"].includes(S.screen)) return;
  S.cart.add(p); S.flash = `${t("scan_added")}: ${p.name}`; draw();
  window.setTimeout(() => { S.flash = ""; draw(); }, 1600);
}

// ---- agent point, collection point, partner finance, credit book --------------------------------------------------
function openTile(tile: string): void {
  S.input = ""; S.note = ""; S.tileGroup = "";
  if (tile === "sell") { S.screen = "sell"; return; }
  if (tile === "reports") { S.screen = "sales"; return; }
  if (tile === "settings") { S.screen = "menu"; return; }
  if (tile === "customers_credit") { S.screen = "credit"; S.selected = 0; return; }
  if (DIRECT[tile]) { startService(DIRECT[tile]!); return; }
  S.tileGroup = tile; S.screen = "pick";
}
function startService(service: string): void {
  S.service = service; S.number = ""; S.amount = 0; S.input = ""; S.note = ""; S.req = null;
  if (service === "voucher" || service === "pickup") { S.screen = "code"; return; }    // own vouchers and pickup codes work offline
  S.step = "number"; S.screen = "agent";
}
function agentSend(): void {
  if (!S.online) { setNote(t("online_only"), t("fd_go_online")); draw(); return; }     // never queued, never shown as done offline
  const finance = (FINANCE_PRODUCTS as readonly string[]).includes(S.service);
  const r: Req = { id: newId(), service: S.service, amount: S.amount, fee: finance ? 0 : Math.max(100, Math.floor(S.amount / 100)), commission: 0, state: "sent", ref: "" };
  S.req = r; S.screen = "agentdone";
  if (finance) emit("PartnerReferralRecorded", { referral_id: r.id, partner_id: "sandbox-partner", product: S.service, fee: 0, currency: pack().currency }, "server");
  else emit("AgentRequestCreated", { request_id: r.id, partner_id: "sandbox-partner", service: (AGENT_SERVICES as readonly string[]).includes(S.service) || S.service === "loan_repayment" || S.service === "insurance_premium" ? S.service : "bills", amount: r.amount, fee: r.fee, currency: pack().currency });
  draw();
  window.setTimeout(() => {
    if (finance) { r.state = "confirmed"; draw(); return; }
    const out = S.service === "cash_deposit" ? 0 : r.amount;
    if (!S.online || S.outcome === "fail" || out > S.partnerFloat) { r.state = "failed"; emit("AgentRequestFailed", { request_id: r.id, reason_code: !S.online ? "timeout" : out > S.partnerFloat ? "insufficient_float" : "partner_declined" }, "server"); draw(); return; }
    r.state = "confirmed"; r.ref = `SBX-${r.id.slice(-8).toUpperCase()}`; r.commission = commission(r.amount, PARTNER_BPS); S.usedToday += r.amount;
    S.partnerFloat += S.service === "cash_deposit" ? r.amount : -r.amount;
    emit("AgentRequestConfirmed", { request_id: r.id, partner_reference: r.ref, amount: r.amount, fee: r.fee, commission: r.commission, currency: pack().currency }, "server");
    emit("CommissionRecorded", { commission_id: newId(), request_id: r.id, partner_id: "sandbox-partner", amount: r.commission, currency: pack().currency, period: new Date().toISOString().slice(0, 10) }, "server");
    draw();
  }, reduced() ? 300 : 2200);
}
const usedCodes = new Set<string>();
function redeem(): void {
  if (S.input.length < 4) return;
  if (usedCodes.has(S.input)) { setNote(t("already_used"), t("fd_check_retry")); S.input = ""; draw(); return; }
  usedCodes.add(S.input);
  if (S.service === "voucher") emit("VoucherRedeemed", { redemption_id: newId(), voucher_id: newId(), amount: 1000, currency: pack().currency });
  else emit("PickupHandedOver", { pickup_id: newId(), order_id: newId(), code_hash: "0".repeat(64) });
  S.flash = t(S.service === "voucher" ? "redeemed" : "handed_over"); S.input = ""; draw();
  window.setTimeout(() => { S.flash = ""; draw(); }, 1600);
}


// ---- the shell parts on the terminal (41 B): search, help, account menu, first-run language card, every screen's address ---------
const SCREEN_PATH: Record<Screen, string> = { lock: "/", home: "/", sell: "/sell", cart: "/sell/basket", pay: "/sell/payment", cash: "/sell/payment", momo: "/sell/payment",
  card: "/sell/payment", waiting: "/sell/payment", off: "/sell/payment", done: "/sell/receipt", menu: "/business", sales: "/sell/sales", sale: "/sell/sales", count: "/sell/shifts",
  shopqr: "/business/online-shop", pick: "/services", agent: "/services", agentdone: "/services", code: "/services", credit: "/crm", staff: "/business/team", door: "/attendance/door", reception: "/queue/reception", counter: "/queue/counter" };
const screenNow = (): DsScreen => ({ id: S.screen, title: document.querySelector("#display .app h1")?.textContent?.trim() || t("sample_shop"), path: SCREEN_PATH[S.screen] });
function entries(): Entry[] {
  const go = (id: string, key: string, kind: Entry["kind"] = "action"): Entry => ({ id, kind, title: t(key), act: `go:${id}` });
  return [
    { id: "new-sale", kind: "action", title: t("new_sale"), act: "newsale", keywords: [t("sell")] },
    go("sales", "sales", "report"), go("count", "count"), go("shopqr", "shop_qr"), go("menu", "menu", "setting"),
    go("door", "ppl_door_title"), go("reception", "ppl_reception_title"), go("counter", "ppl_counter_title"),
    { id: "lowlit", kind: "setting", title: t("low_literacy"), act: "lowlit" },
    ...HANDHELD_TILES.map((k): Entry => ({ id: `tile-${k}`, kind: "action", title: t(`tile_${k}`), act: `tile:${k}` })),
    ...CATALOG.map((p): Entry => ({ id: p.id, kind: "product", title: p.name, subtitle: money(p.price), act: `add:${p.id}`, keywords: [p.barcode ?? ""] })),
    ...S.credit.map((c, i): Entry => ({ id: `cust-${i}`, kind: "customer", title: c.name, subtitle: c.owes ? money(c.owes) : "", act: `custopen:${i}` })),
    ...S.sales.map((x, i): Entry => ({ id: x.sale.sale_id, kind: "order", title: x.sale.receipt_number_local, subtitle: money(x.sale.total), act: `sale:${i}` })),
  ];
}
const DSH = new DeviceShell({
  t, icon: (id) => icon(id), clock,
  screen: screenNow,
  entries,
  articles: (id) => screenArticles(t, id, screenNow().title),
  sync: () => ({ link: S.online ? "good" : "offline", pending: S.events.filter((e) => e.sync !== "accepted").length, lastSync: S.events.find((e) => e.sync === "accepted")?.at ?? null, dataSaver: false, forcedOffline: false }),
  account: () => ({ name: t("role_cashier"), lynkId: "LOID-4821-9035-7715", businesses: [{ id: "b1", name: SHOP, current: true }], role: "cashier", roles: ["cashier", "manager", "owner"],
    theme: S.theme, language: PACKS[S.lang]?.native ?? S.lang, region: pack().sample ? t("sample_country") : pack().name }),
  locale: () => ({ language: PACKS[S.lang]?.native ?? S.lang, region: pack().sample ? t("sample_country") : pack().name, currency: pack().currency, english: S.lang === "en" }),
  run: (a) => {
    if (a === "pictures") { S.lowLiteracy = DSH.pictures; return; }
    if (a === "lang:en") { S.lang = "en"; ($("#cLang") as HTMLSelectElement).value = "en"; return; }
    if (a === "locale:change") { $("#cLang").focus(); return; }
    if (a === "shell:theme") { S.theme = S.theme === "dark" ? "light" : "dark"; ($("#cDark") as HTMLInputElement).checked = S.theme === "dark"; return; }
    if (a === "shell:signout") { S.screen = "lock"; S.input = ""; S.view = "full"; return; }
    if (a.startsWith("ntf:")) { act(a); return; }
    if (a === "toggle:forced" || a === "sync:now") return;
    if (a.startsWith("add:")) { act(a); S.screen = "cart"; return; }
    if (a.startsWith("custopen:")) { S.screen = "credit"; S.selected = Number(a.slice(9)) || 0; return; }
    if (S.screen === "lock") S.screen = "home";
    act(a);
  },
  redraw: () => draw(),
  lines: () => S.lines.map((l) => ({ ...l })),
  knowledge: () => KP(),
  crumbLabel: (p) => t(CRUMB[p] ?? "sample_shop"),
});
const CRUMB: Record<string, string> = { "/": "sample_shop", "/sell": "sell", "/sell/basket": "basket", "/sell/payment": "pay", "/sell/receipt": "receipt", "/sell/sales": "sales", "/sell/shifts": "count", "/business": "menu", "/business/team": "staff_title", "/business/online-shop": "shop_qr", "/services": "menu", "/crm": "menu", "/attendance/door": "ppl_door_title", "/queue/reception": "ppl_reception_title", "/queue/counter": "ppl_counter_title" };

// ---- screens ------------------------------------------------------------------------------------------------------
function top(title: string, backable = true): string {
  return `<div class="bar">${backable ? `<button class="iconbtn" data-act="cancel" aria-label="${esc(t("back"))}">${icon("ui-arrow-left")}</button>` : `${brandMark(DATA.brand.places, "app-top-bar", S.theme === "dark", "logo")}`}
    <h1>${esc(title)}</h1>${DSH.bar({ chip: false, account: false })}<button class="iconbtn" data-act="menu" aria-label="${esc(t("menu"))}">${icon("ui-menu")}</button></div>${DSH.crumbs(true)}`;
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
      if (S.wiped) return `<div class="lock"><p class="pname">LynkPOS</p><h1>${esc(t("wiped"))}</h1></div>`;
      if (STAFF.remoteLocked) return `<div class="lock">${brandMark(DATA.brand.places, "auth-onboarding", S.theme === "dark", "lockmark")}<p class="pname">LynkPOS</p><h1>${esc(t("locked_by_owner"))}</h1></div>`;
      if (S.picking) return `<div class="lock">${staffPicker(STAFF.staff, t, icon)}</div>`;
      return `<div class="lock">${brandMark(DATA.brand.places, "auth-onboarding", S.theme === "dark", "lockmark")}<p class="pname">LynkPOS</p>
        <p class="who">${lockWhoButton(STAFF.find(S.who)?.name ?? "", STAFF.find(S.who)?.role ?? "cashier", t, (id) => icon(id))}</p>
        <h1>${esc(t("pin"))}</h1>${pinBox()}<div class="dots" aria-label="${esc(t("pin_entered", { n: S.input.length }))}">${Array.from({ length: STAFF.lengthOf(S.who) }, (_, i) => i).map((i) => `<i class="${i < S.input.length ? "on" : ""}"></i>`).join("")}</div>
        ${noteBox()}<p class="keyhint">${icon("ui-info")}${esc(t("use_keys"))}</p>
        <p class="hint">${esc(t("dk_pin_sample", { list: STAFF.staff.map((x) => `${t(`role_${x.role}`)} ${x.pin}`).join(", ") }))}</p>${STAFF.find(S.who)?.duress ? `<p class="hint">${esc(t("dk_duress_sample", { pin: STAFF.find(S.who)!.duress! }))}</p>` : ""}</div>`;
    case "home":
      return `${top(t("sample_shop"), false)}${banners()}${staffWhoRow(STAFF.find(S.who)?.name ?? "", STAFF.find(S.who)?.role ?? "cashier", t, (id) => icon(id))}<div class="tiles12${S.lowLiteracy ? " big" : ""}">${HANDHELD_TILES.map((k) => `<button class="t12" data-act="tile:${k}">${icon(TILE_ICON[k] ?? "ui-grid")}<span>${esc(t(`tile_${k}`))}</span></button>`).join("")}</div>${adBlock("pos_idle", "home")}
        ${S.flash ? `<div class="toast" role="status">${icon("ui-check")}${esc(S.flash)}</div>` : ""}`;
    case "pick":
      return `${top(t(`tile_${S.tileGroup}`))}<ul class="menu">${(TILE_SERVICES[S.tileGroup] ?? []).map((k) => `<li><button data-act="svc:${k}">${icon(TILE_ICON[S.tileGroup] ?? "ui-grid")}${esc(t(`svc_${k}`))}${icon("ui-chevron-right")}</button></li>`).join("")}</ul>
        ${S.tileGroup === "partner_finance" ? `<p class="note">${esc(t("referred"))}</p>` : ""}`;
    case "agent": {
      const lim = combinedLimits(PARTNER_LIMITS), finance = (FINANCE_PRODUCTS as readonly string[]).includes(S.service);
      const field = S.step === "number" ? amountPad(t("customer_number"), S.input || "–") : S.step === "amount" ? amountPad(t("amount"), S.input ? money(Number(S.input)) : "–") : "";
      const confirm = S.step === "confirm" ? `<div class="due"><span>${esc(t("customer_number"))}</span><strong>${esc(S.number)}</strong></div>${finance ? `<p class="note">${esc(t("referred"))}</p>` : `<div class="due"><span>${esc(t("amount"))}</span><strong>${esc(money(S.amount))}</strong></div>
        <div class="change ok"><span>${esc(t("fee"))}</span><strong>${esc(money(Math.max(100, Math.floor(S.amount / 100))))}</strong></div><div class="change ok"><span>${esc(t("commission"))}</span><strong>${esc(money(commission(S.amount, PARTNER_BPS)))}</strong></div>`}` : "";
      return `${top(t(`svc_${S.service}`))}${S.online ? "" : `<p class="note">${esc(t("online_only"))}</p>`}${field}${confirm}
        ${S.step !== "number" || finance ? "" : `<p class="hint">${esc(t("limit_line", { per: money(lim.per_transaction), day: money(lim.per_day) }))}</p>`}<p class="hint">${esc(t("identity_check"))}</p>${noteBox()}
        <div class="foot"><button class="primary" data-act="enter" ${S.step === "confirm" && !S.online ? "disabled" : ""}>${esc(t(S.step === "confirm" ? "send_to_partner" : "next"))}</button></div>`;
    }
    case "agentdone": {
      const r = S.req; if (!r) return "";
      const done = r.state === "confirmed", cash = r.service === "cash_withdrawal";
      return `${top(t(`svc_${r.service}`), false)}<div class="donebox">${r.amount ? `<p class="big">${esc(money(r.amount))}</p>` : ""}${chip(r.state)}<p>${esc(t(r.state === "sent" ? "request_sent" : done ? "request_confirmed" : "request_failed"))}</p>
        ${r.ref ? `<p class="sub">${esc(t("partner_ref"))}: ${esc(r.ref)}</p>` : ""}${done && r.commission ? `<p class="sub">${esc(t("commission"))}: ${esc(money(r.commission))}</p>` : ""}${cash ? `<p class="sub">${esc(t("never_before_confirmed"))}</p>` : ""}</div>
        <div class="foot${cash ? " two" : ""}">${cash ? `<button class="ghost" data-act="handcash" ${mayHandOverCash(r.state) ? "" : "disabled"}>${esc(t("hand_over_cash"))}</button>` : ""}<button class="primary" data-act="enter" ${r.state === "sent" ? "disabled" : ""}>${esc(t("ok"))}</button></div>`;
    }
    case "code":
      return `${top(t(`svc_${S.service}`))}${amountPad(t(S.service === "voucher" ? "voucher_code" : "pickup_code"), S.input || "–")}${noteBox()}${S.flash ? `<div class="toast" role="status">${icon("ui-check")}${esc(S.flash)}</div>` : ""}
        <div class="foot"><button class="primary" data-act="enter">${esc(t(S.service === "voucher" ? "redeem" : "hand_over"))}</button></div>`;
    case "credit": {
      const c = S.credit[S.selected];
      return `${top(t("credit_book"))}<ul class="lines">${S.credit.map((x, i) => `<li><button class="row" data-act="cust:${i}"><div><span class="nm">${esc(x.name)}</span></div><div class="rt"><strong>${esc(money(x.owes))}</strong>${i === S.selected ? icon("ui-check") : ""}</div></button></li>`).join("")}</ul>
        ${c ? amountPad(t("record_payment"), S.input ? money(Number(S.input)) : "–") : ""}${S.flash ? `<div class="toast" role="status">${icon("ui-check")}${esc(S.flash)}</div>` : ""}<div class="foot"><button class="primary" data-act="enter">${esc(t("record_payment"))}</button></div>`;
    }
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
        <div class="methods">${((S.view === "limited" ? ["cash"] : ["cash", "mobile_money", "card"]) as PaymentMethod[]).map((m) => { const ok = methodOk(m); return `<button class="method${ok ? "" : " off"}" data-act="method:${m}">
          ${icon(m === "cash" ? "ui-receipt" : m === "card" ? "ui-pay-card" : "ui-pay-mobile-money")}<span>${esc(t("method_" + m))}</span>${ok ? (m !== "cash" ? `<em>${esc(t("sandbox"))}</em>` : "") : `<em>${esc(t("unavailable"))}</em>`}${icon("ui-chevron-right")}</button>`; }).join("")}</div>`;
    case "cash": {
      const total = S.cart.total(), given = Number(S.input || "0");
      return `${top(t("method_cash"))}<div class="due"><span>${esc(t("total"))}</span><strong>${esc(money(total))}</strong></div>
        ${amountPad(t("cash_given"), S.input ? money(given) : "–")}
        <div class="quick">${quickCash(total, NOTES).map((v) => `<button data-act="cash:${v}">${esc(money(v))}</button>`).join("")}</div>
        <div class="change ${given >= total ? "ok" : ""}"><span>${esc(t("change"))}</span><strong>${given >= total ? esc(money(change(total, given))) : "–"}</strong></div>
        ${noteBox()}<div class="foot"><button class="primary" data-act="enter" ${given >= total ? "" : "disabled"}>${esc(t("complete"))}</button></div>`;
    }
    case "momo":
      return `${top(t("method_mobile_money"))}<div class="due"><span>${esc(t("total"))}</span><strong>${esc(money(S.cart.total()))}</strong></div>
        ${amountPad(t("phone"), S.input.replace(/(\d{3})(?=\d)/g, "$1 ") || "–")}<p class="sbx">${icon("ui-info")}${esc(t("sandbox"))}: ${esc(t("test_money"))}</p>
        <div class="foot"><button class="primary" data-act="enter" ${S.input.length >= 9 ? "" : "disabled"}>${esc(t("send_request"))}</button></div>`;
    case "card":
      return `${top(t("method_card"))}<div class="due"><span>${esc(t("total"))}</span><strong>${esc(money(S.cart.total()))}</strong></div>
        <div class="tapgfx" aria-hidden="true"><i></i><i></i><i></i></div><p class="ask">${esc(t("tap_card"))}</p>${noteBox()}<p class="sbx">${icon("ui-info")}${esc(t("sandbox"))}: ${esc(t("test_money"))}</p>
        <div class="foot"><button class="ghost" data-act="tapcard" data-wait>${esc(t("method_card"))}: ${esc(t("sandbox"))}</button></div>`;
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
      return `<div class="donebox">${icon("ui-check", "bigcheck")}<h1>${esc(t("done"))}</h1>${c ? `<p class="big">${esc(money(c.sale.total))}</p>${c.tendered !== undefined ? `<p>${esc(t("change"))}: <strong>${esc(money(change(c.sale.total, c.tendered)))}</strong></p>` : ""}<p class="sub">${esc(t("receipt"))} ${esc(c.sale.receipt_number_local)}</p>` : ""}</div>${adBlock("pos_after_sale", "after_sale")}
        ${c ? receiptByMessage() : ""}<div class="foot"><button class="primary" data-act="enter">${esc(t("new_sale"))}</button></div>`;
    case "off":
      return `${top(t("unavailable"))}<div class="offbox"><span class="pic" role="img" aria-label="${esc(DATA.pictures.offAlt)}">${S.theme === "dark" ? DATA.pictures.offDark : DATA.pictures.offLight}</span>
        <p>${esc(pack().ready[S.method]?.message ?? "")}</p></div><div class="foot"><button class="primary" data-act="go:pay">${esc(t("other_method"))}</button></div>`;
    case "shopqr":   // 38 C: the shop QR customers scan to open the shop page and pay (LynkCheckout)
      return `${top(t("shop_qr"))}<div class="offbox"><span class="qrbig" role="img" aria-label="${esc(t("shop_qr"))}">${icon("ui-qr")}</span><p>${esc(t("shop_qr_help"))}</p></div>`;
    case "staff": return staffScreen();
    // NEW UPDATE 4 (section 3): the door (LynkAttend), reception and counter (LynkQueue) on LynkPOS, offline like the till
    case "door": return `${top(t("ppl_door_title"))}${atDoor(PH.att, atLook(), SPEAK)}${wasThisYou(PH.att, atLook())}<p class="keyhint">${icon("ui-info")}${esc(t("ppl_door_sample", { pin: PH.members[1]?.pin ?? "", idcn: PH.members[1]?.idcn ?? "" }))}</p>`;
    case "reception": return `${top(t("ppl_reception_title"))}<div class="ph-wrap">${quReceptionView(PH.q, quLook())}</div>`;
    case "counter": return `${top(t("ppl_counter_title"))}<div class="ph-wrap">${quCounterView(PH.q, quLook())}</div>`;
    case "menu":
      if (S.view === "limited") return `${top(t("menu"))}<ul class="menu"><li><button data-act="lock">${icon("ui-lock")}${esc(t("lock"))}${icon("ui-chevron-right")}</button></li></ul>`;
      return `${top(t("menu"))}<ul class="menu"><li><button data-act="go:sales">${icon("ui-receipt")}${esc(t("sales"))}${icon("ui-chevron-right")}</button></li>
        <li><button data-act="go:count">${icon("product-ledger")}${esc(t("count"))}${icon("ui-chevron-right")}</button></li>
        <li><button data-act="go:shopqr">${icon("ui-qr")}${esc(t("shop_qr"))}${icon("ui-chevron-right")}</button></li>
        <li><button data-act="go:staff">${icon("ui-user")}${esc(t("staff_title"))}${icon("ui-chevron-right")}</button></li>
        <li><button data-act="go:door">${icon("product-attend")}<span>${esc(t("ppl_door_title"))} <span class="pn">LynkAttend</span></span>${icon("ui-chevron-right")}</button></li>
        <li><button data-act="go:reception">${icon("product-queue")}<span>${esc(t("ppl_reception_title"))} <span class="pn">LynkQueue</span></span>${icon("ui-chevron-right")}</button></li>
        <li><button data-act="go:counter">${icon("product-queue")}<span>${esc(t("ppl_counter_title"))} <span class="pn">LynkQueue</span></span>${icon("ui-chevron-right")}</button></li>
        <li><button data-act="dsh:account">${icon("ui-user")}${esc(t("account_menu"))}${icon("ui-chevron-right")}</button></li>
        <li><button data-act="dsh:sync" data-wait>${icon(S.online ? "ui-sync" : "ui-offline")}${esc(t("sync"))}${icon("ui-chevron-right")}</button></li>
        <li><button data-act="lowlit" aria-pressed="${S.lowLiteracy}">${icon("ui-grid")}${esc(t("low_literacy"))}${S.lowLiteracy ? icon("ui-check") : icon("ui-chevron-right")}</button></li>
        <li><button data-act="lock">${icon("ui-lock")}${esc(t("lock"))}${icon("ui-chevron-right")}</button></li></ul>${shortFooterHtml(new Date(), pack().tz)}`;
    case "sales":
      return `${top(t("sales"))}<ul class="lines">${S.sales.map((s, i) => { const p = s.payments[s.payments.length - 1]; const ps = p ? paymentState(p.status, S.online) : null;
          const ev = S.events.find((e) => e.type === "SaleRecorded" && (e.payload as SalePayload).sale_id === s.sale.sale_id);
          return `<li><button class="row" data-act="sale:${i}"><div><span class="nm">${esc(s.sale.receipt_number_local)} · ${esc(clock(s.at))}${s.voided ? ` · ${esc(t("voided"))}` : ""}</span>
          <span class="sub">${p ? esc(t("method_" + p.method)) : ""} ${ps && ps !== "cash" && ps !== "credit" ? chip(ps) : ""}</span></div><div class="rt"><strong>${esc(money(s.sale.total))}</strong>${ev ? chip(ev.sync) : ""}</div></button></li>`; }).join("")}</ul>${S.sales.length ? "" : designedState("empty", t, DATA.statePictures, S.theme === "dark", { label: t("new_sale"), act: "newsale" })}`;
    case "sale": {
      const s = S.sales[S.selected]; if (!s) return "";
      return `${top(`${t("receipt")} ${s.sale.receipt_number_local}`)}<ul class="lines">${s.sale.lines.map((l) => `<li><div><span class="nm">${esc(l.product_name)}</span><span class="sub">${l.quantity_milli / 1000} × ${esc(money(l.unit_price))}</span></div><strong>${esc(money(l.line_total))}</strong></li>`).join("")}</ul>
        ${S.approve ? approveSheet() : s.voided ? `<p class="note">${esc(t("voided"))}</p><div class="foot"><button class="ghost" data-act="reprint">${esc(t("reprint"))}</button></div>` : S.note === "void" ? `<p class="ask">${esc(t("void_reason"))}</p><div class="reasons">${["entered_in_error", "customer_cancelled", "price_error", "duplicate"].map((r) => `<button data-act="void:${r}">${esc(t("r_" + r))}</button>`).join("")}</div>`
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

/** Banners on the device screen (high and critical lines), never on the payment, cash count or void screens. */
const banners = (): string => deviceBanners(S.lines, t, (id) => icon(id));
function approveSheet(): string {
  const ap = S.approve!;
  if (ap.asked) return `<div class="dk-sheet" role="status"><p class="dk-queued">${icon("status-sent")}<span>${esc(t("asked_owner"))}</span></p><button class="secondary" data-act="approve:cancel">${esc(t("back"))}</button></div>`;
  return `<div class="dk-sheet" role="group" aria-labelledby="apT"><h3 id="apT">${esc(t("mgr_needed"))}</h3><p>${esc(money(ap.amount))}</p>
    <label for="mgrPin">${esc(t("mgr_pin"))}</label><input id="mgrPin" type="password" inputmode="numeric" autocomplete="off" maxlength="8">
    <div class="dk-row"><button class="primary" data-act="approve:pin">${esc(t("ntf_act_approve"))}</button>${S.online ? `<button class="secondary" data-act="approve:ask">${esc(t("as_ask_owner"))}</button>` : ""}<button class="secondary" data-act="approve:cancel">${esc(t("back"))}</button></div></div>`;
}
function staffScreen(): string {
  const sh = S.staffSheet;
  const sheet = sh ? `<div class="dk-sheet" role="group" aria-labelledby="rsT"><h3 id="rsT">${esc(t("reset_pin"))}: ${esc(STAFF.find(sh.person)?.name ?? "")}</h3>
    <label for="byPin">${esc(t("your_pin"))}</label><input id="byPin" type="password" inputmode="numeric" autocomplete="off" maxlength="8">
    <label for="newPin">${esc(t("new_pin"))}</label><input id="newPin" type="password" inputmode="numeric" autocomplete="off" maxlength="8">
    ${sh.note ? noticeHtml(t, sh.note === t("bad_pin") ? { level: "error", text: sh.note, field: "newPin", fix: { label: t("fd_go_to", { field: t("new_pin") }), focus: "newPin" } }
      : sh.note === t("wrong_pin") ? { level: "error", text: sh.note, field: "byPin", fix: { label: t("fd_go_to", { field: t("your_pin") }), focus: "byPin" } } : { level: "error", text: sh.note, how: t("fd_ask_manager") }) : ""}<div class="dk-row"><button class="primary" data-act="staff:save">${esc(t("ok"))}</button><button class="secondary" data-act="staff:cancel">${esc(t("back"))}</button></div></div>` : "";
  return `${top(t("staff_title"))}${S.flash ? `<div class="toast" role="status">${icon("ui-check")}${esc(S.flash)}</div>` : ""}<ul class="menu">${STAFF.staff.map((x) => `<li><button data-act="staff:reset:${x.person}" ${x.role === "owner" ? "disabled" : ""}>${icon("ui-user")}<span>${esc(x.name)} · ${esc(t(`role_${x.role}`))}</span>${icon("ui-chevron-right")}</button></li>`).join("")}</ul>
    <p class="note">${esc(t("staff_note"))}</p>${sheet}`;
}
function receiptByMessage(): string {
  if (S.sent) return `<p class="note" role="status">${esc(S.sent)}</p>`;
  if (!S.sendTo) return `<div class="dk-row"><button class="ghost" data-act="rcpt:text">${icon("product-chat")}${esc(t("by_text"))}</button><button class="ghost" data-act="rcpt:email">${icon("ui-doc")}${esc(t("by_email"))}</button></div>`;
  // Section 4C point 1: the customer's number or email is the shared field part; Send stays off until it is complete.
  const field = S.sendTo === "text" ? phoneFieldHtml(fieldCtx(), { id: "rcptTo", label: t("customer_contact"), country: S.rcptCc || pack().code, digits: S.rcptTo })
    : emailFieldHtml(fieldCtx(), { id: "rcptTo", label: t("customer_contact"), text: S.rcptTo });
  return `<div class="dk-sheet">${field}<button class="primary" data-act="rcpt:send" data-wait ${S.sendTo === "text" ? "data-needs-phone" : "data-needs-email"}="rcptTo" disabled>${esc(t("send_receipt"))}</button></div>`;
}
function fieldCtx(): FieldCtx {
  const packs = DATA.packs as unknown as FieldCtx["packs"];
  return { t, lang: locale(), packs, packOrder: DATA.packOrder, countryName: countryNamer(locale(), packs, t("sample_country")),
    onPhone: (_id, v) => { S.rcptCc = v.country; S.rcptTo = v.digits; }, onEmail: (_id, v) => { S.rcptTo = v.text; } };
}

/** Touch or buttons (DEVICE 48.17.14): the registered hardware version decides; a button terminal works by its keys alone. */
const DM = new DeviceMode(DEVICES, "pos-terminal");
const DEV = wireDevice(DM, { t, icon, screen: () => document.getElementById("display"), pad: () => document.getElementById("pad"), back: () => cancelKey(), redraw: () => draw(), rtl: () => document.getElementById("display")?.dir === "rtl" });
/** The duress PIN's limited view looks like an ordinary quiet till: selling for cash and the receipt, nothing else. */
const LIMITED_OK: Screen[] = ["lock", "sell", "cart", "pay", "cash", "done", "menu"];
/** The device side of the Emulator Panel (ts/src/emkit.ts, build section 3A): the connect request, the disconnected and locked screens,
 *  practice mode, key tones and vibration, the hardware helper and the delivery menu. */
const KIT = new EmKit(EMULATOR_REGISTER, kitFor(EMULATOR_REGISTER, "pos.terminal", "Counter 1", { short_side: 480, touch: true, keys: true, camera: true, speaker: true, device_print: true, hardware: ["receipt_printer", "cash_drawer"] }, "android"), (type, payload, origin) => { emit(type, payload, origin); });
const KW = wireKit(KIT, { t, icon: (id, cls) => icon(id, cls), online: () => S.online, redraw: () => draw() });
function draw(): void { drawScreen(); KW.after(document.querySelector("#display .app") as HTMLElement); wireFields($("#display"), fieldCtx()); wireNotices($("#display")); }
function drawScreen(): void {
  if (S.view === "limited" && !LIMITED_OK.includes(S.screen)) S.screen = "sell";
  const d = $("#display");
  d.className = `display ${S.theme}`;
  const wantLang = S.lang === "xx-rtl" ? "ar" : S.lang === "xx" ? "en" : S.lang;
  if (d.lang !== wantLang) d.lang = wantLang;   // only on a change: setting the same value still restyles the whole screen
  const wantDir = S.lang === "xx-rtl" ? "rtl" : S.lang === "xx" ? "ltr" : PACKS[S.lang]?.dir ?? "ltr";
  if (d.dir !== wantDir) d.dir = wantDir;
  for (const p of document.querySelectorAll<HTMLElement>("#panel, #log, #emkCtl")) { if (p.lang !== d.lang) p.lang = d.lang; if (p.dir !== d.dir) p.dir = d.dir; }   // the "Try it" controls speak the same language
  d.querySelector(".app")!.innerHTML = view() + DSH.overlay();
  DEV.draw(d);
  const a = document.getElementById("address"); if (a) a.textContent = DSH.address();
  drawStatus();
}
function drawStatus(): void {
  const queued = S.events.filter((e) => e.sync !== "accepted").length;
  const pending = S.events.find((e) => e.sync === "queued") ? "queued" : S.events.find((e) => e.sync === "sent") ? "sent" : "accepted";
  $("#statusbar").innerHTML = `<span>${esc(clock(Date.now()))}</span>${S.realUser ? "" : `<span class="sbxtag">${esc(t("sandbox"))}</span>`}
    <span class="sync" title="${esc(DATA.states[pending]?.meaning ?? "")}">${icon(`status-${pending}`)}${queued ? `<span>${queued}</span>` : ""}</span>
    <button type="button" class="net" data-act="dsh:sync" data-wait aria-label="${esc(t(S.online ? "online" : "offline"))}. ${esc(t("sync"))}">${icon(S.online ? "ui-sync" : "ui-offline")}</button>`;   // the connection chip (41 B): opens the sync sheet
}
function drawLeds(): void { document.querySelectorAll<HTMLElement>(".leds i").forEach((el, i) => el.classList.toggle("on", i < S.leds)); }
function drawLog(): void {
  const box = $("#log");
  box.innerHTML = S.events.slice(0, 40).map((e) => `<li><span class="n">#${e.n}</span><code>${esc(e.type)}</code><span class="org">${e.origin}</span>${chip(e.sync)}
    <details><summary>payload</summary><pre>${esc(JSON.stringify(e.payload, null, 1))}</pre></details></li>`).join("") || `<li class="empty">No events yet. Make a sale.</li>`;
}

function act(a: string): void {
  if (DSH.act(a)) return;
  if (a.startsWith("ad:why:")) { AD.why = !AD.why; draw(); return; }
  if (a.startsWith("ad:report:")) { AD.reported = true; draw(); return; }   // the report goes to services/ads.py report_ad; three reports pause the ad
  if (a.startsWith("at:")) { PH.att.act(a, { online: S.online, partner: !S.realUser }); draw(); return; }
  if (a.startsWith("qu:")) { const prints = a === "qu:issue" || a.startsWith("qu:reprint:"); PH.q.act(a, quCtx()); if (prints) printTicket(); draw(); return; }
  if (a.startsWith("ph:")) { PH.act(a, phCtx()); draw(); return; }
  const [k, v = ""] = a.split(/:(.*)/s);
  try {
    if (k && /^d\d+$/.test(k)) { digit(k.slice(1)); return; }
    switch (k) {
      case "clear": clearKey(); return;
      case "cancel": cancelKey(); return;
      case "enter": enter(); return;
      case "menu": if (S.screen !== "lock") { S.screen = "home"; S.input = ""; S.note = ""; draw(); } return;
      case "tile": if ((HANDHELD_TILES as readonly string[]).includes(v)) openTile(v); draw(); return;
      case "svc": if ([...AGENT_SERVICES, ...COLLECTION_KINDS, ...FINANCE_PRODUCTS].includes(v as never)) startService(v); draw(); return;
      case "handcash": if (S.req && mayHandOverCash(S.req.state)) { S.flash = t("done"); S.screen = "home"; } draw(); return;
      case "cust": S.selected = Math.max(0, Math.min(S.credit.length - 1, Number(v) || 0)); S.input = ""; draw(); return;
      case "lowlit": S.lowLiteracy = !S.lowLiteracy; DSH.pictures = S.lowLiteracy; draw(); return;
      case "lock": S.screen = "lock"; S.input = ""; S.view = "full"; S.approve = null; draw(); return;
      case "gate": if (v === "lock") { emit("DeviceLocked", { device_id: DEVICE, after_s: 0, by_automation: false }, "device"); S.screen = "lock"; S.input = ""; S.view = "full"; S.approve = null; draw(); } return;   // Lock beside the name on Home (owner, 2026-11-25)
      case "cat": S.category = v; draw(); return;
      case "add": { const p = CATALOG.find((x) => x.id === v); if (p) S.cart.add(p); draw(); return; }
      case "inc": { const l = S.cart.lines().find((x) => x.product.id === v); if (l) S.cart.setQty(v, l.qtyMilli + 1000); draw(); return; }
      case "dec": { const l = S.cart.lines().find((x) => x.product.id === v); if (l) S.cart.setQty(v, l.qtyMilli - 1000); if (!S.cart.lines().length) S.screen = "sell"; draw(); return; }
      case "go": S.screen = (["sell", "cart", "pay", "sales", "count", "menu", "home", "shopqr", "staff", "door", "reception", "counter"] as Screen[]).find((x) => x === v && (S.view === "full" || ["sell", "cart", "pay", "home"].includes(x))) ?? "home"; S.input = ""; S.note = ""; draw(); return;
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
      case "void": {
        const s = S.sales[S.selected];
        if (s && !s.voided && needsManager(S.role, "void", s.sale.total)) { S.approve = { act: "void", reason: v, amount: s.sale.total, pin: "", asked: false }; S.note = ""; draw(); return; }
        if (s && !s.voided) { emit("SaleVoided", { sale_id: s.sale.sale_id, reason_code: v }); s.voided = true; } S.note = ""; draw(); return;
      }
      case "approve": {                    // a manager's PIN on this device (offline) or Ask the owner (online)
        const s = S.sales[S.selected], ap = S.approve;
        if (!s || !ap) return;
        if (v === "cancel") { S.approve = null; draw(); return; }
        if (v === "ask") { ap.asked = true; emit("OwnerAsked", { request_id: newId(), action: "void_sale_within_rules", person: S.who, role: S.role, facts: { amount: ap.amount } }, "server"); draw(); return; }
        if (v === "pin") { ap.pin = (document.getElementById("mgrPin") as HTMLInputElement | null)?.value ?? ""; }
        const mgr = STAFF.staff.find((x) => (x.role === "manager" || x.role === "owner") && x.pin === ap.pin && x.person !== S.who);
        if (mgr && STAFF.approve(S.who, mgr.person, ap.pin)) {
          emit("OverLimitApproved", { device_id: DEVICE, act: "void", amount: ap.amount, by: mgr.person });
          emit("SaleVoided", { sale_id: s.sale.sale_id, reason_code: ap.reason }); s.voided = true; S.approve = null;
        } else ap.pin = "";
        draw(); return;
      }
      case "staff": {
        if (v === "change") { S.picking = true; draw(); return; }
        if (v.startsWith("pick:")) { S.who = v.slice(5); S.picking = false; S.pinNote = ""; S.input = ""; draw(); return; }
        if (v.startsWith("reset:")) { S.staffSheet = { person: v.slice(6), byPin: "", newPin: "", note: "" }; draw(); return; }
        if (v === "cancel") { S.staffSheet = null; draw(); return; }
        if (v === "save" && S.staffSheet) {
          const by = (document.getElementById("byPin") as HTMLInputElement | null)?.value ?? "", np = (document.getElementById("newPin") as HTMLInputElement | null)?.value ?? "";
          const r = STAFF.reset(S.who, by, S.staffSheet.person, np);
          if (r === "ok") { emit("StaffPinReset", { device_id: DEVICE, person: S.staffSheet.person, by: S.who }, "server"); S.staffSheet = null; S.flash = t("reset_done"); }
          else S.staffSheet.note = t(r === "not_allowed" ? "not_allowed" : r === "wrong_pin" ? "wrong_pin" : "bad_pin");
          draw(); return;
        }
        return;
      }
      case "rcpt": {                        // receipts by message: only when the customer asks; offline it waits, never lost
        if (v === "text" || v === "email") { S.sendTo = v; S.rcptTo = ""; draw(); return; }
        if (v === "send" && S.current && S.sendTo) {
          if (S.online) { emit("DocumentSent", { document_id: S.current.receiptId, kind: "receipt", channel: S.sendTo, by: S.who }, "server"); S.sent = t("receipt_sent"); }
          else S.sent = t("receipt_waits");                // waits on the device; nothing is claimed as sent
          S.sendTo = ""; draw();
        }
        return;
      }
      case "ntf": {                         // a line acted on in the bell
        const [what = "", nid = ""] = v.split(":");
        const l = S.lines.find((x) => x.nid === nid);
        if (l && (what === "read" || what === "open" || what === "ack" || what === "dismiss" || what === "act")) { l.read = true; l.acknowledged = true; }
        if (what === "allread") S.lines.forEach((x) => { x.read = true; });
        draw(); return;
      }
    }
  } catch (e) { const why = e instanceof PosError && POS_HOW[e.reason] ? e.reason : "invalid_amount"; setNote(t(`pos_why_${why}`), t(POS_HOW[why]!)); draw(); }
}

// ---- controls beside the device ------------------------------------------------------------------------------------
function wire(): void {
  document.addEventListener("click", (ev) => {
    const el = (ev.target as HTMLElement).closest<HTMLElement>("[data-act]");
    if (el?.classList.contains("dsh-scrim") && (ev.target as HTMLElement).closest("[data-stop]")) return;   // a tap inside a panel
    if (el && DEV.act(el.dataset["act"] ?? "")) return;
    if (el && !(el as HTMLButtonElement).disabled) act(el.dataset["act"] ?? "");
  });
  $("#display").addEventListener("input", (ev) => { DSH.input(ev.target as HTMLInputElement); });
  $("#display").addEventListener("change", (ev) => { const el = ev.target as HTMLSelectElement; if (el.dataset["act"] === "ppl:checker") { PH.pickChecker(el.value); draw(); } });
  (window as unknown as { __settle: () => void }).__settle = () => { DSH.settle(); draw(); };
  $("#tapzone").addEventListener("click", tapCard);
  $("#slot").addEventListener("click", tapCard);
  $("#scanKey").addEventListener("click", scan);
  $("#tearBtn").addEventListener("click", tear);
  const bind = (id: string, f: (el: HTMLInputElement) => void): void => { const el = $<HTMLInputElement>(id); el.addEventListener("change", () => f(el)); };
  bind("#cOnline", (el) => { S.online = el.checked; if (S.online) sendAlerts(); drawStatus(); draw(); });
  // MASTER UPDATE section 3: the owner's remote lock and wipe, and an altered app (what the cloud does about it)
  bind("#cRemoteLock", (el) => { STAFF.remoteLocked = el.checked; if (el.checked) { emit("DeviceLocked", { device_id: DEVICE, after_s: 0, by_automation: false }, "server"); S.screen = "lock"; S.input = ""; } draw(); });
  $("#cWipe").addEventListener("click", () => { S.wiped = true; S.screen = "lock"; S.sales = []; S.lines = []; emit("DeviceWiped", { device_id: DEVICE, unsent_lost: S.events.filter((e) => e.sync === "queued").length }, "server"); draw(); });
  bind("#cAltered", (el) => { if (el.checked) emit("DeviceIntegrityFailed", { device_id: DEVICE, failed: ["app_signature"] }, "server"); });
  bind("#cDark", (el) => { S.theme = el.checked ? "dark" : "light"; draw(); });
  bind("#cAds", (el) => { AD.on = el.checked; AD.why = false; AD.reported = false; draw(); });
  bind("#cAdHost", (el) => { AD.host = el.checked; draw(); });
  bind("#cReal", (el) => { S.realUser = el.checked; draw(); });
  const country = $<HTMLSelectElement>("#cCountry");
  country.innerHTML = DATA.packOrder.map((c) => { const p = DATA.packs[c] as CountryPack; return `<option value="${esc(c)}">${esc(p.sample ? t("sample_country") : p.name)}</option>`; }).join("");
  country.addEventListener("change", (e) => { S.country = (e.target as HTMLSelectElement).value; draw(); });
  bind("#cFail", (el) => { S.outcome = el.checked ? "fail" : "confirm"; });
  const sel = $<HTMLSelectElement>("#cLang");
  sel.insertAdjacentHTML("afterbegin", Object.entries(PACKS).map(([code, p]) => `<option value="${esc(code)}" lang="${esc(code)}" dir="${p.dir}">${esc(p.native)}</option>`).join(""));
  sel.value = "en";
  $<HTMLSelectElement>("#cLang").addEventListener("change", (e) => { S.lang = (e.target as HTMLSelectElement).value as Lang; draw(); });
  const vc = document.getElementById("versionCtl");
  if (vc) { vc.innerHTML = DEV.control(); vc.addEventListener("change", (e) => { DEV.change(e.target as HTMLElement); }); }
  document.addEventListener("keydown", (e) => {
    if (DSH.key(e)) return;
    if (DEV.key(e)) return;
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
/** Every Lynk name on this page carries its plain word (catalog/names.v1.json, ts/src/names.ts). */
watchNames(document.body, () => t);
