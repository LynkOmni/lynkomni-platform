/** LynkPOS on a button phone (42 J build section 3): for phones without a touch screen. A numbered menu records a sale by
 *  product number and quantity, shows today's total and stock, and queues facts by SMS when there is no data (blueprint
 *  section 2: one sync protocol over any link). Agent services are online only, so the menu says so instead of queuing them. */
import { Cart, qtyText, salePayload } from "../../../ts/src/pos.js";
import type { UserState } from "../../../ts/src/pos.js";
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, newId, panelChange, panelHtml, stateButtons } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";

declare const DATA: Build;
type Screen = "menu" | "sell" | "qty" | "basket" | "done" | "today" | "stock" | "agent";
const S: PanelState & { scr: Screen; sel: number; buf: string; prod: number; total: number; count: number; link: "data" | "sms" | "none"; ticks: number; last: string } =
  { online: true, fail: false, type: "shop", tier: "free", country: "", realUser: false, practice: false, dark: false, lang: "en", scr: "menu", sel: 0, buf: "", prod: 0, total: 0, count: 0, link: "data", ticks: 0, last: "" };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const icon = (id: string): string => `<span class="ic" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); draw(); });
const PRODUCTS = ([["p_rice", 1500], ["p_sugar", 1400], ["p_bread", 1000], ["p_soap", 500], ["p_water", 700]] as const).map(([name, price]) => ({ id: newId(), name, price, category: "food", level: 20_000 }));
const cart = new Cart();
const MENU: [Screen, string][] = [["sell", "sell"], ["today", "today_sales"], ["stock", "stock"], ["agent", "agent"]];

function body(): string {
  const net = S.link === "data" ? t("online") : S.link === "sms" ? "SMS" : t("offline");
  const head = `<div class="bhead"><span>${esc(t("sample_shop"))}</span><span>${esc(net)}${LOG.pending().count ? ` ${LOG.pending().count}` : ""}</span></div>`;
  const soft = (l: string, r: string): string => `<div class="bsoft"><span>${esc(l)}</span><span>${esc(r)}</span></div>`;
  switch (S.scr) {
    case "menu": return `${head}<ol class="bmenu">${MENU.map(([, w], i) => `<li class="${i === S.sel ? "sel" : ""}">${i + 1}. ${esc(t(w))}</li>`).join("")}</ol>${soft(t("confirm"), "")}`;
    case "sell": return `${head}<p class="bt">${esc(t("products"))}</p><ol class="bmenu">${PRODUCTS.map((p, i) => `<li class="${i === S.sel ? "sel" : ""}">${i + 1}. ${esc(t(p.name))} ${esc(C.money(p.price))}</li>`).join("")}</ol>${soft(t("basket"), t("back"))}`;
    case "qty": return `${head}<p class="bt">${esc(t(PRODUCTS[S.prod]?.name ?? ""))}</p><p>${esc(t("qty"))}: <strong>${esc(S.buf || "1")}</strong>_</p>${soft(t("confirm"), t("back"))}`;
    case "basket": return `${head}<p class="bt">${esc(t("basket"))}</p><ul class="bmenu">${cart.lines().map((l) => `<li>${qtyText(l.qtyMilli)} ${esc(t(l.product.name))}</li>`).join("") || `<li>—</li>`}</ul><p>${esc(t("total"))}: <strong>${esc(C.money(cart.total()))}</strong></p><p>OK = ${esc(t("cash"))}</p>${soft(t("pay"), t("back"))}`;
    case "done": return `${head}<p class="bt">${esc(t("done"))}</p><p>${esc(t("receipt"))} ${esc(S.last)}</p><p>${esc(S.link === "data" ? t("st_sent") : S.link === "sms" ? t("st_queued") + " (SMS)" : t("st_queued"))}</p>${soft(t("new_sale"), "")}`;
    case "today": return `${head}<p class="bt">${esc(t("today_sales"))}</p><p>${S.count} · <strong>${esc(C.money(S.total))}</strong></p>${soft("", t("back"))}`;
    case "stock": return `${head}<p class="bt">${esc(t("stock"))}</p><ul class="bmenu">${PRODUCTS.map((p) => `<li>${esc(t(p.name))}: ${qtyText(p.level)}</li>`).join("")}</ul>${soft("", t("back"))}`;
    case "agent": return `${head}<p class="bt">${esc(t("agent"))}</p><p>${esc(t("online_only"))}</p>${soft("", t("back"))}`;
  }
}
function draw(): void { const el = $("#screen"); if (!el) return; el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W); el.innerHTML = body(); }
function ok(): void {
  if (S.scr === "menu") { S.scr = MENU[S.sel]?.[0] ?? "menu"; S.sel = 0; }
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
function act(a: string): void {
  const n = /^d(\d)$/.exec(a);
  const list = S.scr === "menu" ? MENU.length : S.scr === "sell" ? PRODUCTS.length : 0;
  if (n) { const d = Number(n[1]); if (S.scr === "qty") S.buf = (S.buf + d).slice(0, 3); else if (d >= 1 && d <= list) { S.sel = d - 1; ok(); return; } }
  else if (a === "call" || a === "soft:left") { if (a === "soft:left" && S.scr === "sell") S.scr = "basket"; else ok(); return; }
  else if (a === "end" || a === "soft:right") { S.scr = S.scr === "qty" ? "sell" : S.scr === "basket" ? "sell" : "menu"; S.sel = 0; }
  else if (a === "nav:up") S.sel = Math.max(0, S.sel - 1);
  else if (a === "nav:down") S.sel = Math.min(Math.max(list - 1, 0), S.sel + 1);
  draw();
}
function panel(): void {
  $("#panel").innerHTML = panelHtml(["country", "dark", "lang"], S, W, C) ;
  $("#panel").insertAdjacentHTML("afterbegin", `<label class="center"><span>${esc(t("internet"))}</span> <select id="cLink"><option value="data">${esc(t("online"))}</option><option value="sms">SMS</option><option value="none">${esc(t("offline"))}</option></select></label>`);
  ($("#cLink") as HTMLSelectElement).value = S.link;
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), ["menu", "sell", "qty", "basket", "done", "today", "stock", "agent"], (k) => { if (k === "basket" || k === "done") { if (!cart.lines().length && PRODUCTS[0]) cart.add(PRODUCTS[0], 2000); } S.scr = k as Screen; S.sel = 0; draw(); });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? ""; panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (b) act(b.dataset["act"] ?? ""); });
  $("#panel").addEventListener("change", (e) => { const el = e.target as HTMLSelectElement; if (el.id === "cLink") { S.link = el.value === "sms" ? "sms" : el.value === "none" ? "none" : "data"; draw(); return; } if (panelChange(el, S, DATA)) panel(); draw(); });
  document.addEventListener("keydown", (e) => { if (/^\d$/.test(e.key)) act(`d${e.key}`); else if (e.key === "Enter") act("call"); else if (e.key === "Escape" || e.key === "Backspace") act("end"); else if (e.key === "ArrowUp") act("nav:up"); else if (e.key === "ArrowDown") act("nav:down"); });
  window.setInterval(() => { S.ticks += 1; LOG.tick(S.link !== "none", S.link === "sms", S.ticks, () => undefined); }, 400);
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 300);
}
main();
