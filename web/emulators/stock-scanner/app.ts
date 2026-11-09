/** LynkStock handheld scanner (42 J build section 3): a rugged scanner with a trigger. Count (StockCounted), receive a supplier
 *  delivery (StockReceived) and adjust (StockAdjusted) by scanning, fully offline and queued; low and negative stock are shown
 *  with words, never by colour alone, and a negative level is a fact for the owner (the cloud flags it), never a block. */
import { qtyText } from "../../../ts/src/pos.js";
import type { UserState } from "../../../ts/src/pos.js";
import { stockState } from "../../../ts/src/merchant.js";
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, newId, panelChange, panelHtml, stateButtons } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";

declare const DATA: Build;
type Mode = "count" | "receive" | "adjust";
interface Item { id: string; name: string; barcode: string; level: number; reorder: number }
const S: PanelState & { mode: Mode; cur: string; qty: number; flash: string; ticks: number } = { online: true, fail: false, type: "shop", tier: "plus", country: "", realUser: false, practice: false, dark: false, lang: "en", mode: "count", cur: "", qty: 1, flash: "", ticks: 0 };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const icon = (id: string): string => `<span class="ic" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); draw(); });
const ITEMS: Item[] = ([["p_rice", "6001", 24, 10], ["p_sugar", "6002", 6, 8], ["p_oil", "6004", 2, 5], ["p_eggs", "6006", -1, 3], ["p_water", "6008", 36, 12], ["p_soap", "6011", 18, 6]] as const)
  .map(([name, barcode, lv, re]) => ({ id: newId(), name, barcode, level: lv * 1000, reorder: re * 1000 }));
const item = (): Item | undefined => ITEMS.find((i) => i.id === S.cur);
const word = (i: Item): string => { const st = stockState(i.level, i.reorder); return st === "negative" ? t("negative_stock") : st === "low" ? t("low_stock") : ""; };

function scan(): void {
  const i = ITEMS[Math.floor(Math.random() * ITEMS.length)]; if (!i) return;
  S.cur = i.id; S.qty = S.mode === "count" ? Math.max(Math.round(i.level / 1000), 0) : 1; S.flash = t("scanned", { name: t(i.name) });
  const beam = document.querySelector(".window"); beam?.classList.add("on"); window.setTimeout(() => beam?.classList.remove("on"), 250); draw();
}
function save(): void {
  const i = item(); if (!i) return; const q = S.qty * 1000;
  if (S.mode === "count") { LOG.emit("StockCounted", { count_id: newId(), product_id: i.id, counted_milli: q, device_view_milli: i.level }); i.level = q; }
  else if (S.mode === "receive") { LOG.emit("StockReceived", { stock_receipt_id: newId(), lines: [{ product_id: i.id, quantity_milli: q }] }); i.level += q; }
  else { LOG.emit("StockAdjusted", { adjustment_id: newId(), product_id: i.id, delta_milli: -q, reason_code: "damaged" }); i.level -= q; }
  S.flash = t("saved"); S.cur = ""; draw();
}
function screen(): string {
  const p = LOG.pending(), i = item();
  const head = `<header class="shead"><span>${esc(t(S.mode === "count" ? "count" : S.mode === "receive" ? "receive" : "adjust"))}</span><span class="${S.online ? "" : "off"}">${icon(S.online ? "ui-sync" : "ui-offline")}${p.count ? p.count : ""}</span></header>`;
  const tabs = `<nav class="smodes">${(["count", "receive", "adjust"] as Mode[]).map((m, n) => `<button data-act="mode:${m}" ${S.mode === m ? 'aria-current="true"' : ""}>F${n + 1} ${esc(t(m))}</button>`).join("")}</nav>`;
  if (!i) return `${head}${tabs}<div class="sbody"><p class="big">${icon("ui-qr")}</p><p>${esc(t("scan"))}</p>${S.flash ? `<p class="ok">${esc(S.flash)}</p>` : ""}<ul class="slist">${ITEMS.map((x) => `<li><span>${esc(t(x.name))}</span><span>${qtyText(Math.abs(x.level))}${x.level < 0 ? " −" : ""}</span>${word(x) ? `<em>${esc(word(x))}</em>` : ""}</li>`).join("")}</ul></div>`;
  return `${head}${tabs}<div class="sbody"><h2>${esc(t(i.name))}</h2><p class="code">${esc(i.barcode)}</p><p>${esc(t("in_stock", { n: qtyText(i.level) }))}${word(i) ? ` · <em>${esc(word(i))}</em>` : ""}</p>
    <div class="qty"><button data-act="minus" aria-label="−">${icon("ui-minus")}</button><output>${S.qty}</output><button data-act="plus" aria-label="+">${icon("ui-plus")}</button></div><button class="save" data-act="save">${esc(t("save"))}</button></div>`;
}
function draw(): void { const el = $("#screen"); if (!el) return; el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W); el.innerHTML = screen(); }
function act(a: string): void {
  const [k = "", v = ""] = a.split(":");
  if (k === "mode") S.mode = (["count", "receive", "adjust"] as Mode[]).find((m) => m === v) ?? "count";
  if (k === "key") { if (v === "enter") { save(); return; } S.mode = v === "f2" ? "receive" : v === "f3" ? "adjust" : "count"; }
  if (k === "minus") S.qty = Math.max(0, S.qty - 1); if (k === "plus") S.qty += 1; if (k === "save") { save(); return; }
  draw();
}
function panel(): void {
  $("#panel").innerHTML = panelHtml(["online", "country", "dark", "lang"], S, W, C);
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), ["list", "count", "receive", "adjust"], (k) => { if (k === "list") S.cur = ""; else { S.mode = k as Mode; S.cur = ITEMS[3]!.id; S.qty = 1; } draw(); });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? ""; panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (b) act(b.dataset["act"] ?? ""); });
  $("#trigger").addEventListener("click", scan);
  $("#panel").addEventListener("change", (e) => { if (panelChange(e.target as HTMLSelectElement, S, DATA)) panel(); draw(); });
  window.setInterval(() => { S.ticks += 1; LOG.tick(S.online, false, S.ticks, () => undefined); }, 400);
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 420);
}
main();
