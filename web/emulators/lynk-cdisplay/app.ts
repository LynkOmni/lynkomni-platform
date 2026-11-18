/** LynkCDisplay: the small LynkQueue screen above each counter (NEW UPDATE 4; build section 3B). It shows the ticket being served
 *  at its counter and flashes when a new ticket is called; "back soon" when the counter is paused, "closed" when it is closed.
 *  It only follows the queue keeper: the buttons beside it play reception and the counters. Its own buttons (arrows and OK) only
 *  choose which counter this display hangs above. Ticket numbers only, never a name. */
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, panelChange, panelHtml, reducedMotion, stateButtons } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";
import type { UserState } from "../../../ts/src/pos.js";
import { DeviceMode, wireDevice } from "../../../ts/src/devicemode.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";
import { QueueDesk, pairCode, quCDisplayView, quDriver } from "../../../ts/src/queuedesk.js";
import type { QuLook, QuPlan } from "../../../ts/src/queuedesk.js";
import type { AtTier } from "../../../ts/src/attenddesk.js";

declare const DATA: Build & { people: { queue: Record<AtTier, QuPlan> } };
const S: PanelState & { ticks: number; setting: boolean } = { online: true, fail: false, type: "shop", tier: "plus", country: "", realUser: false, practice: false, dark: true, lang: "en", ticks: 0, setting: false };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <E extends HTMLElement>(sel: string): E => document.querySelector(sel) as E;
const icon = (id: string, cls = "ic"): string => `<span class="${cls}" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); });
const Q = new QueueDesk((type, payload, origin) => { LOG.emit(type, payload, origin); }, DATA.people.queue);
const look = (): QuLook => ({ t, icon, clock: () => "", money: (c) => C.money(c, "USD"), online: S.online, partner: !S.realUser, mayManage: false, place: "", powered: "" });
const DM = new DeviceMode(DEVICES, "counter-display");
const DEV = wireDevice(DM, { t, icon: (id) => icon(id), screen: () => document.getElementById("screen"), pad: () => document.getElementById("pad"), back: () => { S.setting = false; draw(); }, redraw: () => draw(), rtl: () => document.getElementById("screen")?.dir === "rtl" });
let mine = Q.counters[0]?.id ?? "";

/** One desk of the hall: the display on its arm above the counter. The first is this device; the others show the same queue. */
function desk(id: string, own: boolean): string {
  const c = Q.counter(id); if (!c) return "";
  const body = own && S.setting ? `<div class="cd-set"><p>${esc(t("cd_which_counter"))}</p>${Q.counters.map((x) => `<button type="button" class="ghost" data-act="cd:pick:${x.id}" aria-pressed="${x.id === mine}">${esc(t("ppl_counter_n", { n: x.n }))}</button>`).join("")}</div>`
    : quCDisplayView(Q, id, look()) + (own ? `<button type="button" class="cd-gear" data-act="cd:set" aria-label="${esc(t("cd_which_counter"))}">${icon("ui-settings")}</button>` : "");
  return `<div class="deskcol"><div class="cdframe"><div class="cdscreen ${S.dark ? "dark" : "light"}"${own ? ' id="screen"' : ""}>${body}</div>${own ? `<div class="mark" aria-hidden="true">${DATA.brand.body}</div>` : ""}</div><div class="cdarm" aria-hidden="true"></div>
    <div class="cdesk" aria-hidden="true"></div>${own ? '<div class="cdpad" id="pad"></div>' : ""}</div>`;
}
function draw(): void {
  Q.tier = S.tier as AtTier;
  const others = Q.counters.filter((c) => c.id !== mine).slice(0, 1);
  $("#desks").innerHTML = desk(mine, true) + others.map((c) => desk(c.id, false)).join("");
  const el = $("#screen"); DEV.draw(el); applyRoot(el, W);
  for (const o of document.querySelectorAll<HTMLElement>("#desks .cdscreen:not(#screen)")) applyRoot(o, W);
  const tl = $("#till"); applyRoot(tl, W); tl.innerHTML = quDriver(Q, look());
}
function act(a: string): void {
  if (a.startsWith("qu:")) Q.act(a, { online: S.online, partner: !S.realUser, pairCode, redraw: draw });
  else if (a === "cd:set") S.setting = true;
  else if (a.startsWith("cd:pick:")) { if (Q.counter(a.slice(8))) mine = a.slice(8); S.setting = false; }
  draw();
}
function panel(): void {
  $("#panel").innerHTML = panelHtml(["online", "country", "dark", "lang"], S, W, C) + DEV.control();
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), ["next-please", "serving", "back-soon", "closed", "which-counter"], (k) => {
    S.setting = k === "which-counter";
    for (const c of Q.counters) { if (c.serving) Q.finish(c.id, "served"); Q.counterState(c.id, "open"); }
    while (Q.waiting().length < 3) Q.issue("SRV", false, "reception");
    if (k === "serving") Q.callNext(mine); else if (k === "back-soon") Q.counterState(mine, "paused"); else if (k === "closed") Q.counterState(mine, "closed");
    draw();
  });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? "";
  panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (b && DEV.act(b.dataset["act"] ?? "")) return; if (b && !b.hasAttribute("disabled")) act(b.dataset["act"] ?? ""); });
  $("#panel").addEventListener("change", (e) => { const el = e.target as HTMLSelectElement; if (DEV.change(el)) return; if (panelChange(el, S, DATA)) panel(); draw(); });
  document.addEventListener("keydown", (e) => { if (DEV.key(e)) return; });
  window.setInterval(() => { S.ticks += 1; LOG.tick(S.online, false, S.ticks, () => undefined); if (!reducedMotion() && S.ticks % 15 === 0 && document.querySelector("#desks .flash")) draw(); }, 400);
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 600);
}
main();
