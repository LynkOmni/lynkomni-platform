/** The customer's tracking page (owner request 9 November 2026): what a customer sees when they open the tracking link a shop
 *  sends, with no account (shop.lynkomni.com/track/(LOORD-)). Every step comes from the shared tracking engine
 *  (ts/src/tracking.ts) replaying the cloud's events, and is drawn by the shared look (ts/src/trackview.ts), so it reads the same
 *  as the shop's phone and the rider's. Only customer steps show: never an address, a phone number, the rider's identity or a
 *  position; live progress is a share of the trip. "Tell me each step" records how the customer wants to hear (by text message or
 *  in chat), in their language; offline, the page keeps the last known step and says so. */
import type { UserState } from "../../../ts/src/pos.js";
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, newId, panelChange, panelHtml, publicId, stateButtons, appShortFooter } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";
import { brandMark } from "../../../ts/src/brand.js";
import { Tracking } from "../../../ts/src/tracking.js";
import type { View } from "../../../ts/src/tracking.js";
import { REGISTER } from "../../../ts/src/tracking.generated.js";
import { trackerHtml } from "../../../ts/src/trackview.js";

declare const DATA: Build;
type Stage = "placed" | "preparing" | "ready" | "on_the_way" | "late" | "delivered" | "failed";
const STAGES: readonly Stage[] = ["placed", "preparing", "ready", "on_the_way", "late", "delivered", "failed"];
const S: PanelState & { stage: Stage; channel: string; ticks: number; last: View | null } = { online: true, fail: false, type: "shop", tier: "free", country: "", realUser: false, practice: false, dark: false, lang: "en", stage: "on_the_way", channel: "", ticks: 0, last: null };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const icon = (id: string): string => `<span class="ic" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); });
const ORDER = newId(), DELIVERY = newId(), PUBLIC = publicId("ORD");
const clock = (iso: string): string => { try { return new Intl.DateTimeFormat(C.locale(), { timeZone: C.pack().tz, hour: "2-digit", minute: "2-digit" }).format(Date.parse(iso)); } catch { return iso.slice(11, 16); } };
const look = { t, esc, icon, time: clock, chip: (s: View["state"]) => chip(s) };

/** The cloud's events up to a stage, replayed by the shared engine: the page holds no step of its own. */
function replay(stage: Stage): View | null {
  const tr = new Tracking(REGISTER), at = Date.now() / 1000 - 1800;
  const late = stage === "late", promise = new Date((late ? at + 600 : at + 3600) * 1000).toISOString().slice(0, 19) + "Z";
  const ev = (type: string, payload: Record<string, unknown>, dt: number): void => { tr.apply({ type, payload, at: at + dt }, "shop"); };
  const order = STAGES.indexOf(stage === "late" ? "on_the_way" : stage);
  ev("OrderSentToKitchen", { order_id: ORDER, table_id: newId(), lines: [{ line_no: 0 }, { line_no: 1 }] }, 0);
  if (order >= 1) ev("KitchenItemReady", { order_id: ORDER, line_no: 0 }, 300);
  if (order >= 2) ev("KitchenItemReady", { order_id: ORDER, line_no: 1 }, 600);
  if (order >= 3 || stage === "failed") {
    ev("DeliveryRequested", { delivery_id: DELIVERY, order_id: ORDER, own_rider: false, price: 1500, currency: C.pack().currency }, 700);
    ev("DeliveryAccepted", { delivery_id: DELIVERY, partner_reference: "SBXD-SAMPLE", eta: promise }, 760);
  }
  if (stage === "failed") ev("DeliveryFailed", { delivery_id: DELIVERY, reason_code: "timeout" }, 900);
  if (order >= 3 && stage !== "failed") { ev("DeliveryPickedUp", { delivery_id: DELIVERY }, 900); tr.setProgress("delivery", DELIVERY, late ? 0.6 : 0.45); }
  if (stage === "delivered") ev("DeliveryDelivered", { delivery_id: DELIVERY, proof: "code" }, 1500);
  return tr.view("order", ORDER, "customer", Date.now() / 1000);
}
function page(): string {
  const v = S.online ? replay(S.stage) : S.last;
  if (S.online) S.last = v;
  const logo = brandMark(DATA.brand.places, "web-header", S.dark, "tlogo", 96);
  const notify = S.channel
    ? `<p class="note" role="status">${esc(t("trk_notify_done"))}</p>`
    : `<div class="btns">${["sms", "chat"].map((c) => `<button data-act="notify:${c}" aria-pressed="false">${esc(t(`trk_by_${c}`))}</button>`).join("")}</div>`;
  return `<div class="urlbar">${icon("ui-lock")}<span class="u">shop.lynkomni.com/track/${esc(PUBLIC)}</span></div><div class="tbody">
    <div class="thead">${logo}<span class="from">${esc(t("trk_from_shop", { shop: t("sample_shop") }))}</span></div><h1>${esc(t("track_heading"))}</h1>
    ${S.online ? "" : `<p class="banner" role="status">${icon("ui-offline")}<span>${esc(t("trk_last_known"))}</span></p>`}
    ${v ? trackerHtml(v, look, t("trk_k_order")) : ""}
    <section class="card"><h2>${esc(t("trk_notify"))}</h2>${notify}</section>
    <p class="note">${esc(t("trk_privacy"))}</p>${appShortFooter(C)}</div>`;
}
function draw(): void {
  const el = $("#screen"); el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W); el.innerHTML = page();
  const a = document.getElementById("address"); if (a) a.textContent = `shop.lynkomni.com/track/${PUBLIC}`;
}
function act(a: string): void {
  const [k = "", v = ""] = a.split(":");
  if (k === "notify" && (v === "sms" || v === "chat")) {
    S.channel = v;   // the contact itself stays in the PII vault; the cloud records only the way and the language (TrackingSubscribed)
    LOG.emit("TrackingSubscribed", { kind: "order", record: ORDER, channel: v, lang: W.htmlLang() }, "server");
  }
  draw();
}
function panel(): void {
  $("#panel").innerHTML = panelHtml(["online", "country", "dark", "lang"], S, W, C);
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), STAGES, (k) => { S.stage = (STAGES as readonly string[]).includes(k) ? (k as Stage) : "on_the_way"; S.channel = ""; draw(); });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? "";
  panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (b && !b.hasAttribute("disabled")) act(b.dataset["act"] ?? ""); });
  $("#panel").addEventListener("change", (e) => { if (panelChange(e.target as HTMLSelectElement, S, DATA)) panel(); draw(); });
  window.setInterval(() => { S.ticks += 1; LOG.tick(S.online, false, S.ticks, () => undefined); }, 400);
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 400);
}
main();
