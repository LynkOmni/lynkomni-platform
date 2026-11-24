/** LynkPOS on a button phone (42 J build section 3): for phones without a touch screen. A numbered menu records a sale by
 *  product number and quantity, shows today's total and stock, and queues facts by SMS when there is no data (blueprint
 *  section 2: one sync protocol over any link). Agent services are online only, so the menu says so instead of queuing them. */
import { Cart, qtyText, salePayload } from "../../../ts/src/pos.js";
import type { UserState } from "../../../ts/src/pos.js";
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, newId, panelChange, panelHtml, stateButtons } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";
import { APP_HOST } from "../../../ts/src/deviceshell.js";
import { chooseInterface } from "../../../ts/src/interfaces.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";
import { chPage, chQPage, chQStart, chQStep, chRender, chSPage, chSStart, chSStep, chStart, chStep, parseSms } from "../../../ts/src/channels.js";
import type { ChQCtx, ChQState, ChSCtx, ChSState, ChState } from "../../../ts/src/channels.js";
import { nextCode, runningLate, ticketNumber, waitMinutes } from "../../../ts/src/queue.js";
import { bpPage, bpStart, bpStep, textNotification } from "../../../ts/src/basicphone.js";
import type { BpCtx, BpState, PinCheck } from "../../../ts/src/basicphone.js";
import { check } from "../../../ts/src/usernames.js";
import { loadPrefs, savePrefs } from "../../../ts/src/soundprefs.js";
import type { Volume } from "../../../ts/src/soundprefs.js";
import { playSound, soundForAct } from "../../../ts/src/keytones.js";
import type { Sound } from "../../../ts/src/keytones.js";
import { SOUNDS } from "../../../ts/src/sounds.generated.js";
import { watchNames } from "../../../ts/src/names.js";

declare const DATA: Build;
/** Shell parts on a button phone (41 B, decided 9 November 2026): there is no touch screen, so "find or do" is the numbered menu
 *  itself (every action is one number away), and help, language and region, sync and the account are menu items. */
type Screen = "menu" | "sell" | "qty" | "basket" | "done" | "today" | "stock" | "agent" | "help" | "locale" | "sync" | "account";
const S: PanelState & { scr: Screen; sel: number; buf: string; prod: number; total: number; count: number; link: "data" | "sms" | "none"; ticks: number; last: string; pics: boolean } =
  { online: true, fail: false, type: "shop", tier: "free", country: "", realUser: false, practice: false, dark: false, lang: "en", scr: "locale", sel: 0, pics: false, buf: "", prod: 0, total: 0, count: 0, link: "data", ticks: 0, last: "" };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
/** Which phone this is (DEVICE 48.17): the registered device decides the interface. A button phone runs the app, a simple phone
 *  the lighter app, and a basic phone with no apps reaches LynkPOS by USSD, text message or a voice menu (core/channels.py). */
type Kind = "button-phone" | "feature-phone" | "basic-phone";
const KINDS: Kind[] = ["button-phone", "feature-phone", "basic-phone"];
const PH = { kind: "button-phone" as Kind, mode: "idle" as "idle" | "ussd" | "sms" | "voice" | "acct" | "queue" | "survey", st: chStart() as ChState, input: "", sms: "", reply: "", ended: false,
  // MASTER UPDATE section 3: the LynkOmni account on a basic phone (identity/basic_phone.py): sign up, sign in, help, the bell
  acct: bpStart() as BpState, wrong: 0, read: new Set<string>(), created: false };
/** LynkQueue by basic phone (build section 3B; core/channels.py queue menu): a sample place whose queue keeper gives the number. The
 *  menu only asks; ticket codes and the order come from the queue rules (ts/src/queue.ts). "#" plays the counter serving the next person. */
const QQ = { st: chQStart() as ChQState, place: newId(), last: null as string | null, order: ["a", "b", "c", "d"] as string[], me: null as null | { id: string; code: string; late: boolean; state: "waiting" | "called" | "served" } };
const Q_SECTIONS: [string, boolean][] = [["ch_q_sec_1", true], ["ch_q_sec_2", false]];
const qCtx = (): ChQCtx => {
  const me = QQ.me, at = me ? QQ.order.indexOf(me.id) + 1 : 0;
  return { place: t("sample_shop"), sections: Q_SECTIONS.map(([k, open], i): [string, number, number, boolean] => [t(k), i ? 0 : QQ.order.length - (me && me.state === "waiting" ? 1 : 0), waitMinutes(QQ.order.length + 1, 4, 1) ?? 0, open]),
    ticket: me ? { number: ticketNumber("SRV", me.code), place: at, minutes: waitMinutes(Math.max(1, at), 4, 1) ?? 0, state: me.state, late_used: me.late, counter: t("ch_q_counter") } : null };
};
function queueAsk(action: { join: number } | { running_late: true } | { leave: true }): void {
  if ("join" in action) {
    const code = nextCode(QQ.last) ?? "222222"; QQ.last = code; QQ.me = { id: newId(), code, late: false, state: "waiting" }; QQ.order.push(QQ.me.id);
    LOG.emit("TicketIssued", { ticket_id: QQ.me.id, place_id: QQ.place, section: "SRV", code, via: "basic_phone", priority: false });
  } else if (QQ.me && "running_late" in action) { QQ.order = runningLate(QQ.order, QQ.me.id); QQ.me.late = true; LOG.emit("TicketRunningLate", { ticket_id: QQ.me.id }, "server"); }
  else if (QQ.me) { QQ.order = QQ.order.filter((x) => x !== QQ.me?.id); LOG.emit("TicketLeft", { ticket_id: QQ.me.id }, "server"); QQ.me = null; }
}
/** The counter serves the next person: when it is this phone's turn the ticket is called (a text would tell the person). */
function queueMove(): void {
  const next = QQ.order.shift(); if (!next) return;
  if (QQ.me && next === QQ.me.id) { QQ.me.state = "called"; LOG.emit("TicketCalled", { ticket_id: QQ.me.id, counter_id: QQ.place, call: 1, by_number: true }); }
  if (QQ.order.length < 2) QQ.order.push(newId());
}
/** LynkSurvey by basic phone (build section 3B; core/channels.py survey menu): a sample survey asked one question a page; the
 *  answers go to the cloud when the last one is given (anonymous here: no name and no number in the answer). */
const SQ = { st: chSStart() as ChSState, survey: newId() };
const sCtx = (): ChSCtx => ({ org: t("sample_shop"), minutes: 1, anonymous: true, questions: [{ id: "visit", type: "rating", text: t("ch_s_sample_q1") }, { id: "again", type: "yes_no", text: t("ch_s_sample_q2") }] });
const ACCT_PIN = "4719";                 // the sample account's PIN
const SAMPLE_USER = "ama.shop";          // "*" types it: a basic phone types letters by tapping a key several times
const acctCtx = (): BpCtx => ({ age: 18, lines: [["n1", t("bp_new_sign_in")], ["n2", t("bp_low_rice")], ["n3", t("bp_day_closed")]].filter(([nid]) => !PH.read.has(nid!)) as [string, string][], recovery: "7F3K-9Q2M-X81B-4TZC", case: "LOCASE-2101-7710-0042" });
const acctRules = {
  pinCheck: (p: string): PinCheck => { if (p === ACCT_PIN) { PH.wrong = 0; return "ok"; } PH.wrong += 1; return PH.wrong >= 10 ? "locked" : ["wrong", 10 - PH.wrong]; },
  usernameCheck: (u: string): string | null => { const r = check(u); return r.ok ? null : r.reason; },
  taken: (u: string): boolean => u === "mamas.kitchen",
};
const iface = (): string => chooseInterface(DEVICES, { registered: { device: PH.kind, version: "non_touch" } }).interface;
const PIN = "1234";
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const icon = (id: string): string => `<span class="ic" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); draw(); });
const PRODUCTS = ([["p_rice", 1500], ["p_sugar", 1400], ["p_bread", 1000], ["p_soap", 500], ["p_water", 700]] as const).map(([name, price]) => ({ id: newId(), name, price, category: "food", level: 20_000 }));
const cart = new Cart();
const MENU: [Screen, string][] = [["sell", "sell"], ["today", "today_sales"], ["stock", "stock"], ["agent", "agent"], ["help", "help"], ["locale", "language_region"], ["sync", "sync"], ["account", "account_menu"]];
const PATH: Record<Screen, string> = { menu: "/", sell: "/sell", qty: "/sell", basket: "/sell/basket", done: "/sell/receipt", today: "/sell/sales", stock: "/stock", agent: "/services", help: "/", locale: "/", sync: "/", account: "account.lynkomni.com" };
/** Picture mode (S4): the picture for each menu line, the word always beside it. */
const PIC: Partial<Record<Screen, string>> = { sell: "lit-sell", today: "lit-reports", stock: "product-stock", agent: "lit-agent", help: "ui-info", locale: "ui-globe", sync: "ui-sync", account: "ui-user" };
const HELP = ["ask_assist_short", "chat_with_person", "open_case"];
const HELP_DONE = ["assist_opening", "support_connecting", "case_opened"];

function chCtx() {
  return { products: PRODUCTS.map((p): [string, string, string] => [t(p.name), C.money(p.price), qtyText(p.level)]), today: [S.count, C.money(S.total)] as [number, string], receipt: S.last, pinOk: (x: string) => x === PIN };
}
function channelBody(): string {
  const head = `<div class="bhead"><span>${esc(t("ch_idle"))}</span><span>${esc(S.link === "none" ? t("offline") : "")}</span></div>`;
  const soft = (l: string, r: string): string => `<div class="bsoft"><span>${esc(l)}</span><span>${esc(r)}</span></div>`;
  if (PH.mode === "acct") {
    const text = chRender(bpPage(PH.acct, acctCtx()), (k) => t(k));
    return `${head}<pre class="bussd" role="status">${esc(text)}</pre>${PH.ended ? `<p class="bnote">${esc(t("ch_session_ended"))}</p>` : `<p class="breply">${esc(t("ch_reply"))}: <strong>${esc(PH.acct.screen === "pin" || PH.acct.screen === "new_pin" || PH.acct.screen === "pin_again" ? "•".repeat(PH.input.length) : PH.input)}</strong>_</p>${PH.acct.screen === "username" ? `<p class="bnote">${esc(t("bp_star_hint", { name: SAMPLE_USER }))}</p>` : ""}`}${soft(t("ch_send"), t("back"))}`;
  }
  if (PH.mode === "idle") return `${head}<ol class="bmenu">${[t("ch_dial"), t("ch_text"), t("ch_voice"), t("bp_dial_account"), t("ch_q_dial"), t("ch_s_dial")].map((w, i) => `<li class="${i === S.sel ? "sel" : ""}">${i + 1}. ${esc(w)}</li>`).join("")}</ol><p class="bnote">${esc(t("ch_sandbox"))}</p>${soft(t("confirm"), "")}`;
  if (PH.mode === "queue") {
    const text = chRender(chQPage(QQ.st, qCtx()), (k) => t(k));
    return `${head}<pre class="bussd" role="status">${esc(text)}</pre>${PH.ended ? `<p class="bnote">${esc(t("ch_session_ended"))}</p>` : `<p class="breply">${esc(t("ch_reply"))}: <strong>${esc(PH.input)}</strong>_</p>`}<p class="bnote">${esc(t("ch_q_text_help"))} ${esc(t("ch_q_sandbox"))}</p>${soft(t("ch_send"), t("back"))}`;
  }
  if (PH.mode === "survey") {
    const text = chRender(chSPage(SQ.st, sCtx()), (k) => t(k));
    return `${head}<pre class="bussd" role="status">${esc(text)}</pre>${PH.ended ? `<p class="bnote">${esc(t("ch_session_ended"))}</p>` : `<p class="breply">${esc(t("ch_reply"))}: <strong>${esc(PH.input)}</strong>_</p>`}${soft(t("ch_send"), t("back"))}`;
  }
  if (PH.mode === "sms") return `${head}<p class="bt">${esc(t("ch_message_to"))}</p><p class="bsms">${esc(PH.sms)}_</p>${PH.reply ? `<p class="bsms in" role="status">${esc(PH.reply)}</p>` : ""}${soft(t("ch_send"), t("back"))}`;
  const text = chRender(chPage(PH.st, chCtx()), (k) => t(k));
  const spoken = PH.mode === "voice" ? `<p class="bnote">${icon("ui-mic")} ${esc(t("ch_spoken"))}</p>` : "";
  return `${head}<pre class="bussd" role="status">${esc(text)}</pre>${spoken}${PH.ended ? `<p class="bnote">${esc(t("ch_session_ended"))}</p>` : `<p class="breply">${esc(t("ch_reply"))}: <strong>${esc(PH.input)}</strong>_</p>`}${soft(t("ch_send"), t("back"))}`;
}
function sellFromChannel(prod: number, qtyMilli: number): void {
  const p = PRODUCTS[prod]; if (!p) return;
  cart.clear(); cart.add(p, qtyMilli);
  const sale = salePayload(cart, newId(), `BP-${S.count + 1}`, C.pack().currency); S.last = sale.receipt_number_local;
  LOG.emit("SaleRecorded", sale, "server"); LOG.emit("PaymentRecorded", { payment_id: newId(), sale_id: sale.sale_id, method: "cash", amount: sale.total, status: "cash_received", currency: C.pack().currency }, "server");
  p.level -= qtyMilli; S.total += sale.total; S.count += 1; cart.clear();
}
function channelAct(a: string): void {
  const n = /^d(\d)$/.exec(a);
  if (PH.mode === "idle") {
    const pickMode = (i: number): void => { PH.mode = (["ussd", "sms", "voice", "acct", "queue", "survey"] as const)[i] ?? "ussd"; PH.st = chStart(); PH.acct = bpStart(); QQ.st = chQStart(QQ.me !== null); SQ.st = chSStart(); PH.input = ""; PH.sms = ""; PH.reply = ""; PH.ended = false; };
    if (n && Number(n[1]) >= 1 && Number(n[1]) <= 6) pickMode(Number(n[1]) - 1);
    else if (a === "call" || a === "soft:left") pickMode(S.sel);
    else if (a === "nav:up") S.sel = Math.max(0, S.sel - 1); else if (a === "nav:down") S.sel = Math.min(5, S.sel + 1);
    draw(); return;
  }
  if (a === "end" || a === "soft:right") { if (PH.mode === "sms" && PH.sms) PH.sms = PH.sms.slice(0, -1); else { PH.mode = "idle"; S.sel = 0; } draw(); return; }
  if (PH.mode === "sms") {
    if (n) PH.sms = (PH.sms + n[1]).slice(0, 40); else if (a === "star" || a === "hash") PH.sms = (PH.sms + " ").replace(/\s+$/, " ");
    else if (a === "call" || a === "soft:left") {
      const c = parseSms(PH.sms);
      if (!c) PH.reply = t("ch_no_command");
      else if (c.command === "sell") { if (c.pin === PIN && PRODUCTS[c.product]) { sellFromChannel(c.product, c.qty_milli); PH.reply = chRender([["ch_sale_saved", { receipt: S.last }]], (k) => t(k)); } else PH.reply = t("ch_no_command"); }
      else PH.reply = chRender(chPage({ screen: c.command, prod: null, qty: null }, chCtx()), (k) => t(k));
      PH.sms = "";
    }
    draw(); return;
  }
  if (PH.ended) { PH.mode = "idle"; S.sel = 0; draw(); return; }
  if (PH.mode === "queue") {
    if (n) PH.input = (PH.input + n[1]).slice(0, 2);
    else if (a === "hash") queueMove();
    else if (a === "call" || a === "soft:left") {
      const [st, ends, action] = chQStep(QQ.st, PH.input, qCtx()); PH.input = "";
      if (action) queueAsk(action);
      QQ.st = st; PH.ended = ends;
    }
    draw(); return;
  }
  if (PH.mode === "survey") {
    if (n) PH.input = (PH.input + n[1]).slice(0, 2);
    else if (a === "call" || a === "soft:left") {
      const [st, ends, action] = chSStep(SQ.st, PH.input, sCtx()); PH.input = "";
      if (action) LOG.emit("SurveyAnswerReceived", { answer_id: newId(), survey_id: SQ.survey, version: 1, way: "basic_phone", test: false }, "server");
      SQ.st = st; PH.ended = ends;
    }
    draw(); return;
  }
  if (PH.mode === "acct") {
    if (n) PH.input = (PH.input + n[1]).slice(0, 30);
    else if (a === "star" && PH.acct.screen === "username") PH.input = SAMPLE_USER;
    else if (a === "call" || a === "soft:left") {
      const [st, ends, action] = bpStep(PH.acct, PH.input, acctCtx(), acctRules); PH.input = "";
      if (action && "create" in action) { PH.created = true; LOG.emit("AccountCreated", { username: action.create.username, channel: "ussd" }, "server"); }
      if (action && "sign_in" in action) LOG.emit("SessionStarted", { site: "basic_phone", channel: "ussd" }, "server");
      if (action && "read" in action) { PH.read.add(action.read); LOG.emit("NotificationRead", { nid: action.read, channel: "ussd" }, "server"); }
      if (action && "hand_over" in action) LOG.emit("SupportCaseOpened", { case: "LOCASE-2101-7710-0042", channel: "ussd" }, "server");
      if (action && "send_link" in action) PH.reply = textNotification(t("bp_link_sent"), null, (k) => t(k));
      PH.acct = st; PH.ended = ends;
    }
    draw(); return;
  }
  if (n) PH.input = (PH.input + n[1]).slice(0, 4);
  else if (a === "call" || a === "soft:left") {
    const [st, ends, action] = chStep(PH.st, PH.input, chCtx()); PH.input = "";
    if (action) sellFromChannel(action.sale, action.qty_milli);
    PH.st = st; PH.ended = ends;
  }
  draw();
}
function body(): string {
  if (PH.kind === "basic-phone") return channelBody();
  const net = S.link === "data" ? t("online") : S.link === "sms" ? "SMS" : t("offline");
  const head = `<div class="bhead"><span>${esc(t("sample_shop"))}</span><span>${esc(net)}${LOG.pending().count ? ` ${LOG.pending().count}` : ""}</span></div>`;
  const soft = (l: string, r: string): string => `<div class="bsoft"><span>${esc(l)}</span><span>${esc(r)}</span></div>`;
  switch (S.scr) {
    case "menu": return `${head}<ol class="bmenu${S.pics ? " pics" : ""}">${MENU.map(([k, w], i) => `<li class="${i === S.sel ? "sel" : ""}">${i + 1}. ${S.pics ? icon(PIC[k] ?? "ui-grid") : ""}${esc(t(w))}</li>`).join("")}</ol>${soft(t("confirm"), "")}`;
    case "sell": return `${head}<p class="bt">${esc(t("products"))}</p><ol class="bmenu">${PRODUCTS.map((p, i) => `<li class="${i === S.sel ? "sel" : ""}">${i + 1}. ${esc(t(p.name))} ${esc(C.money(p.price))}</li>`).join("")}</ol>${soft(t("basket"), t("back"))}`;
    case "qty": return `${head}<p class="bt">${esc(t(PRODUCTS[S.prod]?.name ?? ""))}</p><p>${esc(t("qty"))}: <strong>${esc(S.buf || "1")}</strong>_</p>${soft(t("confirm"), t("back"))}`;
    case "basket": return `${head}<p class="bt">${esc(t("basket"))}</p><ul class="bmenu">${cart.lines().map((l) => `<li>${qtyText(l.qtyMilli)} ${esc(t(l.product.name))}</li>`).join("") || `<li>—</li>`}</ul><p>${esc(t("total"))}: <strong>${esc(C.money(cart.total()))}</strong></p><p>OK = ${esc(t("cash"))}</p>${soft(t("pay"), t("back"))}`;
    case "done": return `${head}<p class="bt">${esc(t("done"))}</p><p>${esc(t("receipt"))} ${esc(S.last)}</p><p>${esc(S.link === "data" ? t("st_sent") : S.link === "sms" ? t("st_queued") + " (SMS)" : t("st_queued"))}</p>${soft(t("new_sale"), "")}`;
    case "today": return `${head}<p class="bt">${esc(t("today_sales"))}</p><p>${S.count} · <strong>${esc(C.money(S.total))}</strong></p>${soft("", t("back"))}`;
    case "stock": return `${head}<p class="bt">${esc(t("stock"))}</p><ul class="bmenu">${PRODUCTS.map((p) => `<li>${esc(t(p.name))}: ${qtyText(p.level)}</li>`).join("")}</ul>${soft("", t("back"))}`;
    case "agent": return `${head}<p class="bt">${esc(t("agent"))}</p><p>${esc(t("online_only"))}</p>${soft("", t("back"))}`;
    case "help": return `${head}<p class="bt">${esc(t("help"))}</p>${S.last.startsWith("help:") ? `<p role="status">${esc(t(HELP_DONE[Number(S.last.slice(5))] ?? ""))}</p>` : ""}<ol class="bmenu">${HELP.map((k, i) => `<li class="${i === S.sel ? "sel" : ""}">${i + 1}. ${esc(t(k))}</li>`).join("")}</ol>${soft(t("confirm"), t("back"))}`;
    case "locale": { const p = C.pack(); return `${head}<p class="bt">${esc(t("locale_title"))}</p><p>${esc(DATA.i18n[S.lang]?.native ?? S.lang)} · ${esc(p.sample ? t("sample_country") : p.name)} · ${esc(p.currency)}</p><ol class="bmenu">${["looks_right", "english", "change"].map((k, i) => `<li class="${i === S.sel ? "sel" : ""}"${k === "english" ? ' lang="en" dir="ltr"' : ""}>${i + 1}. ${k === "english" ? "English" : esc(t(k))}</li>`).join("")}</ol>${soft(t("confirm"), "")}`; }
    case "sync": { const p = LOG.pending(); const last = LOG.events.find((e) => e.sync === "accepted")?.at; return `${head}<p class="bt">${esc(t("sync"))}</p><p>${esc(p.count ? t("waiting_send", { n: p.count }) : t("all_sent"))}</p><p>${esc(t("last_sync"))}: ${esc(last ? C.clock(last) : t("not_yet"))}</p>${soft("", t("back"))}`; }
    case "account": return `${head}<p class="bt">${esc(t("account_menu"))}</p><p>${esc(t("role_cashier"))} · <code>LOID-…-7715</code></p><ol class="bmenu"><li class="${S.sel === 0 ? "sel" : ""}">1. ${esc(t("sign_out"))}</li><li class="${S.sel === 1 ? "sel" : ""}" role="switch" aria-checked="${S.pics}">2. ${esc(t("low_literacy"))}: ${esc(t(S.pics ? "on" : "off"))}</li></ol>${soft(t("confirm"), t("back"))}`;
  }
}
function draw(): void { const el = $("#screen"); if (!el) return; el.dataset["interface"] = iface(); el.dataset["deviceClass"] = DEVICES.interfaces[iface()]?.class ?? "phone"; el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W); el.innerHTML = body(); el.querySelector(".bmenu .sel")?.scrollIntoView({ block: "nearest" });
  const ad = document.getElementById("address"); if (ad) { const p = PATH[S.scr]; ad.textContent = !p.startsWith("/") ? p : `${APP_HOST}${p}`; } }
function ok(): void {
  if (S.scr === "menu") { S.scr = MENU[S.sel]?.[0] ?? "menu"; S.sel = 0; S.last = ""; }
  else if (S.scr === "locale") { if (S.sel === 1) { S.lang = "en"; panel(); } if (S.sel === 2) document.querySelector<HTMLSelectElement>('[data-ctl="lang"]')?.focus(); S.scr = "menu"; S.sel = 0; }
  else if (S.scr === "help") { S.last = `help:${S.sel}`; }
  else if (S.scr === "account") { if (S.sel === 1) S.pics = !S.pics; else { S.scr = "menu"; S.sel = 0; } }
  else if (S.scr === "sell") { S.prod = S.sel; S.buf = ""; S.scr = "qty"; }
  else if (S.scr === "qty") { const p = PRODUCTS[S.prod]; if (p) cart.add(p, Math.max(1, Number(S.buf || "1")) * 1000); S.scr = "basket"; }
  else if (S.scr === "basket" && cart.lines().length) {
    const sale = salePayload(cart, newId(), `BP-${S.count + 1}`, C.pack().currency); S.last = sale.receipt_number_local;
    LOG.emit("SaleRecorded", sale); LOG.emit("PaymentRecorded", { payment_id: newId(), sale_id: sale.sale_id, method: "cash", amount: sale.total, status: "cash_received", currency: C.pack().currency });
    for (const l of cart.lines()) { const p = PRODUCTS.find((x) => x.id === l.product.id); if (p) p.level -= l.qtyMilli; }
    S.total += sale.total; S.count += 1; cart.clear(); S.scr = "done";
  } else if (S.scr === "done") S.scr = "sell";
  draw();
}
/** Key tones and press vibration like a real button phone (owner, 19 November 2026): each number key its own keypad pair, the
 *  green key, the red key, the arrows and the soft keys each their own sound; both can be turned off in the panel. */
const P0 = loadPrefs();   // the person's Sounds and vibration, remembered and followed here (catalog/sounds.v1.json)
const TONES = { tones: P0.tones, vibration: P0.vibration, volume: P0.volume as string, pin_tones: "per_key" as "per_key" | "same" };
function keySound(a: string): void { const k: Sound = soundForAct(a); playSound(SOUNDS, k, TONES); }
function act(a: string): void {
  keySound(a);
  if (PH.kind === "basic-phone") { channelAct(a); return; }
  const n = /^d(\d)$/.exec(a);
  const list = S.scr === "menu" ? MENU.length : S.scr === "sell" ? PRODUCTS.length : S.scr === "help" || S.scr === "locale" ? 3 : S.scr === "account" ? 2 : 0;
  if (n) { const d = Number(n[1]); if (S.scr === "qty") S.buf = (S.buf + d).slice(0, 3); else if (d >= 1 && d <= list) { S.sel = d - 1; ok(); return; } }
  else if (a === "call" || a === "soft:left") { if (a === "soft:left" && S.scr === "sell") S.scr = "basket"; else ok(); return; }
  else if (a === "end" || a === "soft:right") { S.scr = S.scr === "qty" ? "sell" : S.scr === "basket" ? "sell" : "menu"; S.sel = 0; }
  else if (a === "nav:up") S.sel = Math.max(0, S.sel - 1);
  else if (a === "nav:down") S.sel = Math.min(Math.max(list - 1, 0), S.sel + 1);
  draw();
}
function panel(): void {
  $("#panel").innerHTML = panelHtml(["country", "dark", "lang"], S, W, C) ;
  $("#panel").insertAdjacentHTML("beforeend", `<label class="center"><input type="checkbox" id="cTones"${TONES.tones ? " checked" : ""}> <span>${esc(t("bp_key_tones"))}</span></label><label class="center"><input type="checkbox" id="cVibe"${TONES.vibration ? " checked" : ""}> <span>${esc(t("bp_vibration"))}</span></label><label class="center"><span>${esc(t("bp_volume"))}</span> <select id="cVol">${(["low", "medium", "high"] as const).map((v) => `<option value="${v}"${TONES.volume === v ? " selected" : ""}>${esc(t(`bp_vol_${v}`))}</option>`).join("")}</select></label>`);
  $("#panel").insertAdjacentHTML("afterbegin", `<label class="center"><span>${esc(t("internet"))}</span> <select id="cLink"><option value="data">${esc(t("online"))}</option><option value="sms">SMS</option><option value="none">${esc(t("offline"))}</option></select></label>`);
  ($("#cLink") as HTMLSelectElement).value = S.link;
  $("#panel").insertAdjacentHTML("afterbegin", `<label class="center"><span>${esc(t("bp_kind"))}</span> <select id="cKind">${KINDS.map((k) => `<option value="${k}"${k === PH.kind ? " selected" : ""}>${esc(t(k === "button-phone" ? "bp_kind_button" : k === "feature-phone" ? "bp_kind_feature" : "bp_kind_basic"))}</option>`).join("")}</select></label>`);
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), ["menu", "sell", "qty", "basket", "done", "today", "stock", "agent", "help", "locale", "sync", "account"], (k) => { if (k === "basket" || k === "done") { if (!cart.lines().length && PRODUCTS[0]) cart.add(PRODUCTS[0], 2000); } S.scr = k as Screen; S.sel = 0; draw(); });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? ""; panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (b) act(b.dataset["act"] ?? ""); });
  $("#panel").addEventListener("change", (e) => { const el = e.target as HTMLSelectElement & HTMLInputElement; if (el.id === "cTones") { TONES.tones = el.checked; savePrefs({ tones: el.checked }); return; } if (el.id === "cVibe") { TONES.vibration = el.checked; savePrefs({ vibration: el.checked }); return; } if (el.id === "cVol") { TONES.volume = savePrefs({ volume: el.value as Volume }).volume; keySound("ok"); return; } if (el.id === "cKind") { PH.kind = KINDS.find((k) => k === el.value) ?? "button-phone"; PH.mode = "idle"; S.sel = 0; S.scr = "menu"; draw(); return; } if (el.id === "cLink") { S.link = el.value === "sms" ? "sms" : el.value === "none" ? "none" : "data"; draw(); return; } if (panelChange(el, S, DATA)) panel(); draw(); });
  document.addEventListener("keydown", (e) => { if (/^\d$/.test(e.key)) act(`d${e.key}`); else if (e.key === "Enter") act("call"); else if (e.key === "Escape" || e.key === "Backspace") act("end"); else if (e.key === "ArrowUp") act("nav:up"); else if (e.key === "ArrowDown") act("nav:down"); });
  window.setInterval(() => { S.ticks += 1; LOG.tick(S.link !== "none", S.link === "sms", S.ticks, () => undefined); }, 400);
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 300);
  (window as unknown as { __settle: () => void }).__settle = () => { if (S.scr === "locale") { S.scr = "menu"; S.sel = 0; } draw(); };
}
main();
/** Every Lynk name on this page carries its plain word (catalog/names.v1.json, ts/src/names.ts). */
watchNames(document.body, () => t);
