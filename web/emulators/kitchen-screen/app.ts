/** LynkPOS kitchen screen (N1 restaurant mode, blueprint 44 I; 42 J added emulator): a wall-mounted display that shows each
 *  table order as the till sends it (OrderSentToKitchen), with a bump bar to mark items ready (KitchenItemReady). Works offline
 *  over the shop's network or LynkMesh; the plan decides how many screens a shop may run (billing FEATURES kitchen_screens). */
import { qtyText } from "../../../ts/src/pos.js";
import type { UserState } from "../../../ts/src/pos.js";
import type { PosEntitlement } from "../../../ts/src/business.js";
import { kitchenOutput, restaurantLimits } from "../../../ts/src/restaurant.js";
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, newId, panelChange, panelHtml, stateButtons } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";

declare const DATA: Build & { entitlements: Record<string, PosEntitlement> };
const TIERS = ["free", "plus", "pro", "max"] as const;
interface Line { lineNo: number; name: string; qty: number; mods: string; ready: boolean }
interface Ticket { id: string; table: string; at: number; lines: Line[]; bumped: boolean }
const S: PanelState & { tickets: Ticket[]; sel: number; station: number; ticks: number } = { online: true, fail: false, type: "restaurant", tier: "plus", country: "", realUser: false, practice: false, dark: false, lang: "en", tickets: [], sel: 0, station: 1, ticks: 0 };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const icon = (id: string): string => `<span class="ic" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); });
const DISHES = [["p_soup", ""], ["p_chicken", "modifiers"], ["p_rice_plate", ""], ["p_juice", ""], ["p_bread", ""]] as const;
const lim = () => restaurantLimits(DATA.entitlements[S.tier] ?? {});
const open = (): Ticket[] => S.tickets.filter((x) => !x.bumped);

function incoming(table?: string): void {
  const n = 1 + Math.floor(Math.random() * 3), lines: Line[] = [];
  for (let i = 0; i < n; i++) { const d = DISHES[Math.floor(Math.random() * DISHES.length)] ?? DISHES[0]; lines.push({ lineNo: i + 1, name: d[0], qty: 1 + Math.floor(Math.random() * 2), mods: d[1], ready: false }); }
  const tk: Ticket = { id: newId(), table: table ?? String(1 + Math.floor(Math.random() * 12)), at: Date.now(), lines, bumped: false };
  S.tickets.push(tk);
  LOG.emit("OrderSentToKitchen", { order_id: tk.id, table_id: newId(), lines: lines.map((l) => ({ line_no: l.lineNo, product_id: newId(), quantity_milli: l.qty * 1000, ...(l.mods ? { modifiers: t(l.mods) } : {}) })) }, "device", "accepted");
  LOG.emit("KitchenTicketRouted", { order_id: tk.id, station: kitchenOutput(lim()), by_automation: "kitchen-routing" }, "server");
  draw();
}
function ready(tk: Ticket, line?: Line): void {
  for (const l of line ? [line] : tk.lines) if (!l.ready) { l.ready = true; LOG.emit("KitchenItemReady", { order_id: tk.id, line_no: l.lineNo }); }
  if (tk.lines.every((l) => l.ready)) tk.bumped = true;
  S.sel = Math.min(S.sel, Math.max(open().length - 1, 0)); draw();
}
const mins = (ms: number): string => String(Math.max(0, Math.floor((Date.now() - ms) / 60000)));

function screen(): string {
  const l = lim();
  if (kitchenOutput(l) !== "screen") return `<div class="kempty"><h2>${esc(t("kitchen"))}</h2><p>${esc(t("printed_tickets"))}</p><pre class="kticket">${esc(open().slice(0, 2).map((tk) => `${t("table", { label: tk.table })}\n${tk.lines.map((x) => `${x.qty} x ${t(x.name)}`).join("\n")}`).join("\n\n") || t("all_ready"))}</pre></div>`;
  const screens = l.kitchenScreens === null ? "∞" : String(l.kitchenScreens);
  const pending = LOG.pending();
  return `<header class="khead"><h1>${esc(t("kitchen_queue"))}</h1><span class="kst">${esc(t("kitchen"))} ${S.station}/${screens}</span><span class="knet${S.online ? "" : " off"}">${icon(S.online ? "ui-sync" : "ui-offline")}${esc(t(S.online ? "online" : "offline"))}${pending.count ? ` · ${pending.count}` : ""}</span></header>
    <div class="tickets">${open().map((tk, i) => `<article class="ticket${i === S.sel ? " sel" : ""}${Date.now() - tk.at > 10 * 60000 ? " late" : ""}" aria-label="${esc(t("table", { label: tk.table }))}"><header><strong>${esc(t("table", { label: tk.table }))}</strong><span>${esc(mins(tk.at))} min</span></header>
      <ul>${tk.lines.map((x) => `<li class="${x.ready ? "done" : ""}"><button data-act="line:${tk.id}:${x.lineNo}" ${x.ready ? "disabled" : ""}><span class="q">${x.qty}</span><span class="nm">${esc(t(x.name))}${x.mods ? `<small>${esc(t(x.mods))}</small>` : ""}</span>${x.ready ? chip("confirmed") : ""}</button></li>`).join("")}</ul>
      <button class="kready" data-act="all:${tk.id}">${esc(t("ready"))}</button></article>`).join("") || `<p class="kall">${esc(t("all_ready"))}</p>`}</div>`;
}
function draw(): void { const el = $("#screen"); el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W); el.innerHTML = screen(); }
function panel(): void {
  $("#panel").innerHTML = panelHtml(["online", "plan", "country", "dark", "lang"], S, W, C, { tiers: TIERS });
  $("#panel").insertAdjacentHTML("afterbegin", `<p><button type="button" class="pill" data-act="incoming">+ ${esc(t("new_order_test"))}</button></p>`);
  stateButtons($("#stateButtons"), ["queue", "empty", "printed", "late"], (k) => { if (k === "empty") S.tickets = []; if (k === "printed") S.tier = "free"; if (k === "queue" || k === "late") { S.tier = S.tier === "free" ? "plus" : S.tier; if (!open().length) { incoming("4"); incoming("7"); } if (k === "late" && open()[0]) open()[0]!.at = Date.now() - 12 * 60000; } panel(); draw(); });
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
}
function main(): void {
  S.country = DATA.packOrder[0] ?? "";
  panel(); incoming("4"); incoming("7");
  document.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (!b) return;
    const [k = "", a = "", c = ""] = (b.dataset["act"] ?? "").split(":");
    const tk = S.tickets.find((x) => x.id === a);
    if (k === "incoming") incoming();
    else if (k === "line" && tk) ready(tk, tk.lines.find((x) => x.lineNo === Number(c)));
    else if (k === "all" && tk) ready(tk);
    else if (k === "bump") { const o = open(); if (a === "prev") S.sel = Math.max(0, S.sel - 1); if (a === "next") S.sel = Math.min(o.length - 1, S.sel + 1); if (a === "ready" && o[S.sel]) { ready(o[S.sel]!); return; } if (a === "recall") { const last = [...S.tickets].reverse().find((x) => x.bumped); if (last) { last.bumped = false; for (const l of last.lines) l.ready = false; } } draw(); }
  });
  $("#panel").addEventListener("change", (e) => { if (panelChange(e.target as HTMLSelectElement, S, DATA, { tiers: TIERS })) panel(); draw(); });
  window.setInterval(() => { S.ticks += 1; if (LOG.tick(S.online, false, S.ticks, () => undefined)) draw(); if (S.ticks % 75 === 0) draw(); }, 400);
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 1000);
}
main();
