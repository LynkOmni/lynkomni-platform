/** Rider phone for own-staff deliveries (N8, blueprint 44 I; 42 J added emulator). The rider sees the deliveries assigned to
 *  them, records pickup at the shop and delivery at the door with the customer's code or a photo of the parcel (never of a
 *  person). Steps are device events (DeliveryPickedUp, DeliveryDelivered) that work offline and are sent when a link exists.
 *  LynkOmni never employs riders: the rider is the shop's own staff. */
import type { UserState } from "../../../ts/src/pos.js";
import { nextDeliveryStep } from "../../../ts/src/restaurant.js";
import type { DeliveryState } from "../../../ts/src/restaurant.js";
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, newId, panelChange, panelHtml, plain, stateButtons, appShortFooter } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";
import { designedState, panelShell, sampleAccount } from "../../../ts/src/deviceshell.js";
import type { Entry } from "../../../ts/src/shell.js";
import { Tracking } from "../../../ts/src/tracking.js";
import type { View as TrackView } from "../../../ts/src/tracking.js";
import { REGISTER } from "../../../ts/src/tracking.generated.js";
import { trackerHtml } from "../../../ts/src/trackview.js";
import { chooseInterface } from "../../../ts/src/interfaces.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";

declare const DATA: Build;
interface Job { id: string; order: number; area: string; amount: number; state: DeliveryState; code: string; proof?: "code" | "photo" }
/** NEW UPDATE 1 (build section 3): battery warnings and the last message, off-shift privacy, sealed hand-overs and SOS on the watch. */
const RX = { battery: 100, lastSent: false, onShift: true, sos: "" as "" | "confirm" | "sent", seals: {} as Record<string, string> };
async function seal(j: Job): Promise<void> {          // the hand-over as one sealed record (services/sealing.py in the cloud); the screen shows its hash
  const bytes = new TextEncoder().encode(JSON.stringify({ delivery_id: j.id, proof: j.proof, to_role: "receiver", at: Math.floor(Date.now() / 1000) }));
  const h = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), (b) => b.toString(16).padStart(2, "0")).join("");
  RX.seals[j.id] = h; draw();
}
function batteryNote(): string {
  if (RX.battery > 20) return "";
  if (RX.battery <= 3) {
    if (!RX.lastSent) { RX.lastSent = true; LOG.emit("DeviceLastReport", { device_id: "rider-phone-1", reason: "battery", battery_pct: RX.battery }); }
    return `<p class="warn" role="status">${icon("ui-warning")}${esc(t("last_report"))}</p>`;
  }
  return `<p class="warn" role="status">${icon("ui-warning")}${esc(t(RX.battery <= 10 ? "battery_10" : "battery_20"))}</p>`;
}
function shiftBar(): string {
  return `<div class="shift"><button class="${RX.onShift ? "primary" : "secondary"}" data-act="shift:${RX.onShift ? "off" : "on"}" aria-pressed="${RX.onShift}">${esc(t(RX.onShift ? "shift_on" : "shift_off"))}</button>${RX.onShift ? "" : `<p class="note">${esc(t("shift_off_note"))}</p>`}</div>`;
}
function sosView(): string {
  if (RX.sos === "confirm") return `<div class="sos" role="alertdialog" aria-labelledby="sosQ"><p id="sosQ"><strong>${esc(t("sos_confirm"))}</strong></p><button class="primary" data-act="sos:send">${esc(t("sos_send"))}</button><button class="secondary" data-act="sos:cancel">${esc(t("sos_cancel"))}</button></div>`;
  if (RX.sos === "sent") return `<p class="warn" role="status">${esc(t("sos_sent"))}</p>`;
  return `<button class="secondary sosbtn" data-act="sos:ask">${icon("ui-warning")}${esc(t("sos"))}</button>`;
}
const S: PanelState & { jobs: Job[]; open: string; typed: string; msg: string; ticks: number; share: boolean; trip: number } = { online: true, fail: false, type: "shop", tier: "plus", country: "", realUser: false, practice: false, dark: false, lang: "en", jobs: [], open: "", typed: "", msg: "", ticks: 0, share: false, trip: 0 };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const icon = (id: string): string => `<span class="ic" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); draw(); });
const code6 = (): string => String(Math.floor(100000 + Math.random() * 900000));
const job = (): Job | undefined => S.jobs.find((j) => j.id === S.open);
const stateWord = (st: DeliveryState): string => (st === "accepted" ? t("st_accepted") : st === "picked_up" ? t("picked_up") : st === "delivered" ? t("delivered") : st === "failed" ? t("st_failed") : t("st_sent"));
const lastSync = (id: string, type: string): UserState => LOG.events.find((e) => e.type === type && (e.payload as { delivery_id: string }).delivery_id === id)?.sync ?? "queued";

// ---- the shell parts on this device (41 B): search, help, account, connection chip, first-run card, the screen's address ----
const shellTitle = (): string => document.querySelector("#screen h1, #screen h2")?.textContent?.trim() || t("sample_shop");
const DSH = panelShell({
  st: S, t, icon: (id) => icon(id), clock: (ms) => C.clock(ms),
  native: () => (DATA.i18n[S.lang]?.native ?? S.lang), region: () => (C.pack().sample ? t("sample_country") : C.pack().name), currency: () => C.pack().currency,
  pending: () => LOG.pending().count, lastSync: () => LOG.events.find((e) => e.sync === "accepted")?.at ?? null,
  screen: () => ({ id: S.open ? "delivery" : "deliveries", title: shellTitle(), path: "/deliveries" }), entries: (): Entry[] => S.jobs.map((j): Entry => ({ id: j.id, kind: "order", title: t("order", { n: j.order }), subtitle: `${t(j.area)} · ${stateWord(j.state)}`, act: `open:${j.id}` })),
  account: () => sampleAccount(t, "cashier", ["cashier", "manager", "owner"], t("sample_shop"), S.dark ? "dark" : "light", DATA.i18n[S.lang]?.native ?? S.lang, C.pack().sample ? t("sample_country") : C.pack().name),
  run: (a) => { act(a); }, redraw: () => draw(),
});

function list(): string {
  // designed states (41 B): changes waiting for the connection, and nothing left to deliver
  const waiting = !S.online && LOG.pending().count ? designedState("sync_pending", t, DATA.statePictures, S.dark, null) : "";
  const done = S.jobs.every((j) => j.state === "delivered") ? designedState("success", t, DATA.statePictures, S.dark, null) : "";
  return `${batteryNote()}${shiftBar()}${waiting}${done}<h2>${esc(t("deliveries"))}</h2><ul class="jobs">${S.jobs.map((j) => `<li><button data-act="open:${j.id}"><strong>${esc(t("order", { n: j.order }))}</strong><span>${esc(t(j.area))}</span><span class="st st-${j.state}">${esc(stateWord(j.state))}</span>${icon("ui-chevron-right")}</button></li>`).join("")}</ul><p class="note">${esc(t("proof_photo"))}</p>${appShortFooter(C)}`;
}
/** The job as the shared tracking engine sees it (the same steps the shop and the customer see). Trip progress is shared only
 *  while the rider has switched it on for this trip: a share of the way and the arrival time, never a position. */
function tracker(j: Job): TrackView | null {
  const tr = new Tracking(REGISTER), at = Date.now() / 1000 - 900, eta = new Date((at + 2700) * 1000).toISOString().slice(0, 19) + "Z";
  tr.apply({ type: "DeliveryRequested", payload: { delivery_id: j.id, order_id: j.id, own_rider: true, price: 0, currency: C.pack().currency }, at }, "shop");
  tr.apply({ type: "DeliveryAccepted", payload: { delivery_id: j.id, partner_reference: "own-rider", eta }, at: at + 60 }, "shop");
  if (j.state === "picked_up" || j.state === "delivered") tr.apply({ type: "DeliveryPickedUp", payload: { delivery_id: j.id }, at: at + 300 }, "shop");
  if (j.state === "picked_up" && S.share) tr.setProgress("delivery", j.id, Math.min(0.9, 0.1 + S.trip * 0.05));
  if (j.state === "delivered") tr.apply({ type: "DeliveryDelivered", payload: { delivery_id: j.id, proof: j.proof ?? "code" }, at: at + 900 }, "shop");
  if (j.state === "failed") tr.apply({ type: "DeliveryFailed", payload: { delivery_id: j.id, reason_code: "other" }, at: at + 900 }, "shop");
  return tr.view("delivery", j.id, "staff", Date.now() / 1000);
}
const look = { t, esc, icon: (id: string) => icon(id), time: (iso: string) => C.clock(Date.parse(iso)), chip: (st: TrackView["state"]) => chip(st) };
function detail(j: Job): string {
  const next = nextDeliveryStep(j.state);
  const syncChip = j.state === "picked_up" ? chip(lastSync(j.id, "DeliveryPickedUp")) : j.state === "delivered" ? chip(lastSync(j.id, "DeliveryDelivered")) : "";
  return `<button class="link" data-act="back">${icon("ui-arrow-left")}${esc(t("back"))}</button><h2>${esc(t("order", { n: j.order }))}</h2><p>${esc(t(j.area))} · ${esc(C.money(j.amount))}</p>
    <p class="state">${esc(stateWord(j.state))} ${syncChip}</p>
    ${next === "picked_up" ? `<button class="primary" data-act="pickup">${esc(t("picked_up"))}</button>` : ""}
    ${next === "delivered" ? `<label class="codebox">${esc(t("delivery_code", { code: "" }))}<input inputmode="numeric" maxlength="6" data-field="code" value="${esc(S.typed)}" autocomplete="off"></label>
      <button class="primary" data-act="deliver:code" ${S.typed.length === 6 ? "" : "disabled"}>${esc(t("delivered"))}</button><p class="note">${esc(t("proof_code"))}</p>
      <button class="secondary" data-act="deliver:photo">${icon("ui-receipt")}${esc(t("proof_photo"))}</button>` : ""}
    ${batteryNote()}${S.msg ? `<p class="warn" role="alert">${esc(S.msg)}</p>` : ""}
    ${(() => { const v = tracker(j); return v ? trackerHtml(v, look, t("order", { n: j.order })) : ""; })()}
    ${j.state === "delivered" && RX.seals[j.id] ? `<p class="note" data-item="sealed">${icon("ui-lock")}${esc(t("sealed", { seal: RX.seals[j.id]!.slice(0, 12) }))}</p>` : ""}
    ${j.state === "picked_up" && RX.onShift ? `<label class="share"><input type="checkbox" data-field="share" ${S.share ? "checked" : ""}> <span>${esc(t("trk_share_progress"))}</span></label><p class="note">${esc(t("trk_share_help"))}</p>` : ""}
    <p class="note">${esc(t("track"))}: shop.lynkomni.com/track/LODLV-…</p><p class="hint">${esc(t("pickup_code"))}: ${esc(j.code)}</p>`;
}
/** The same rider app on a phone, a watch or a car screen (DEVICE 48.17): the registered device decides the interface. A watch shows
 *  the next job and its one action; a car screen is voice only while the vehicle moves and the full screen when it stops. */
const RK = { device: "rider-phone" as "rider-phone" | "smartwatch" | "car-screen", moving: false };
const rkChoice = () => chooseInterface(DEVICES, { registered: { device: RK.device, version: RK.device === "car-screen" ? "non_touch" : "touch" } });
function watchView(): string {
  const j = S.jobs.find((x) => x.state !== "delivered"); const next = j ? nextDeliveryStep(j.state) : null;
  return sosView() + (j ? `<div class="wjob"><strong>${esc(t("order", { n: j.order }))}</strong><span>${esc(stateWord(j.state))}</span>${next === "picked_up" ? `<button class="primary" data-act="open:${j.id}">${esc(t("picked_up"))}</button>` : `<button class="primary" data-act="open:${j.id}">${esc(t("delivered"))}</button>`}<p class="note">${esc(t("watch_more"))}</p></div>` : designedState("success", t, DATA.statePictures, S.dark, null));
}
function carVoice(): string {
  const j = S.jobs.find((x) => x.state !== "delivered"); const next = j ? nextDeliveryStep(j.state) : null;
  return `<div class="carvoice" role="status"><p class="big">${icon("ui-mic")}</p><p>${esc(t("car_voice_only"))}</p>${j && next ? `<p><strong>${esc(t("car_next", { step: t(next === "picked_up" ? "picked_up" : "delivered") }))}</strong> · ${esc(t("order", { n: j.order }))}</p>` : ""}<p class="note">${esc(t("car_stop"))}</p></div>`;
}
function draw(): void {
  const el = $("#screen"); if (!el) return;
  const c = rkChoice(); el.dataset["interface"] = c.interface; el.dataset["deviceClass"] = c.class; el.dataset["moving"] = RK.device === "car-screen" && RK.moving ? "yes" : "no";
  document.querySelector(".phone")?.setAttribute("data-kind", RK.device);
  if (RK.device === "smartwatch" && !job()) { el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W); el.innerHTML = `<div class="rbody">${watchView()}</div>${DSH.overlay()}`; return; }
  if (RK.device === "car-screen" && RK.moving) { el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W); el.innerHTML = carVoice(); return; } el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); el.classList.toggle("lowlit", DSH.pictures); applyRoot(el, W);
  el.innerHTML = `<header class="rtop"><span class="rmark">${icon("product-chat")}</span><strong>${esc(t("deliveries"))}</strong>${DSH.bar()}</header><div class="rbody">${job() ? detail(job()!) : list()}</div>${DSH.overlay()}`;
  const ad = document.getElementById("address"); if (ad) ad.textContent = DSH.address();
}
function act(a: string): void {
  const [k = "", v = ""] = a.split(":"); const j = job();
  if (k === "open") { S.open = S.jobs.some((x) => x.id === v) ? v : ""; S.typed = ""; S.msg = ""; }
  else if (k === "back") S.open = "";
  else if (k === "shift") { RX.onShift = v === "on"; if (!RX.onShift) S.share = false; }
  else if (k === "sos") { if (v === "ask") RX.sos = "confirm"; else if (v === "cancel") RX.sos = ""; else if (v === "send") { RX.sos = "sent"; LOG.emit("ProtectionAlertRaised", { alert_id: newId(), subject_id: "rider-1", alert: "sos", level: "urgent" }); } }
  else if (k === "pickup" && j && nextDeliveryStep(j.state) === "picked_up") { j.state = "picked_up"; S.trip = 0; LOG.emit("DeliveryPickedUp", { delivery_id: j.id }); }
  else if (k === "deliver" && j && nextDeliveryStep(j.state) === "delivered") {
    if (v === "code" && S.typed !== j.code) { S.msg = t("wrong_code"); draw(); return; }
    j.state = "delivered"; j.proof = v === "photo" ? "photo" : "code"; S.share = false; LOG.emit("DeliveryDelivered", { delivery_id: j.id, proof: j.proof }); S.msg = ""; void seal(j);
  }
  draw();
}
function seed(): void {
  S.jobs = [{ id: newId(), order: 1042, area: "area_1", amount: 8500, state: "accepted", code: code6() }, { id: newId(), order: 1043, area: "area_2", amount: 23000, state: "accepted", code: code6() }, { id: newId(), order: 1039, area: "area_3", amount: 4000, state: "delivered", code: code6(), proof: "code" }];
}
function panel(): void {
  $("#panel").innerHTML = panelHtml(["online", "country", "dark", "lang"], S, W, C)
    + `<label class="center"><span>${esc(t("rk_device"))}</span> <select data-ctl="rkdevice">${(["rider-phone", "smartwatch", "car-screen"] as const).map((k) => `<option value="${k}"${k === RK.device ? " selected" : ""}>${esc(t(k === "rider-phone" ? "rk_phone" : k === "smartwatch" ? "rk_watch" : "rk_car"))}</option>`).join("")}</select></label>`
    + `<label class="center"><span>${esc(t("rk_battery"))}</span> <select data-ctl="battery">${[100, 20, 10, 3].map((b) => `<option value="${b}"${b === RX.battery ? " selected" : ""}>${b}%</option>`).join("")}</select></label>`
    + (RK.device === "car-screen" ? `<label><input type="checkbox" data-ctl="moving"${RK.moving ? " checked" : ""}> <span>${esc(t("rk_moving"))}</span></label>` : "");
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), ["list", "pickup", "deliver", "delivered", "wrong"], (k) => { seed(); const j = S.jobs[0]!; S.open = k === "list" ? "" : j.id; S.msg = "";
    if (k === "deliver" || k === "delivered" || k === "wrong") j.state = "picked_up"; if (k === "delivered") { j.state = "delivered"; } if (k === "wrong") { S.typed = "000000"; S.msg = t("wrong_code"); } draw(); });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? ""; seed(); panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (!b || b.hasAttribute("disabled")) return; if (b.classList.contains("dsh-scrim") && (e.target as HTMLElement).closest("[data-stop]")) return; if (!DSH.act(b.dataset["act"] ?? "")) act(b.dataset["act"] ?? ""); });
  document.addEventListener("keydown", (e) => { DSH.key(e); });
  (window as unknown as { __settle: () => void }).__settle = () => { DSH.settle(); draw(); };
  document.addEventListener("change", (e) => { const el = e.target as HTMLInputElement; if (el.dataset["field"] === "share") { S.share = el.checked; S.trip = 0; draw(); } });
  document.addEventListener("input", (e) => { const el = e.target as HTMLInputElement; if (DSH.input(el)) return; if (el.dataset["field"] === "code") { S.typed = plain(el.value).replace(/\D/g, "").slice(0, 6); const pos = el.selectionStart; draw(); const n = document.querySelector<HTMLInputElement>('[data-field="code"]'); if (n) { n.focus(); n.setSelectionRange(pos, pos); } } });
  $("#panel").addEventListener("change", (e) => { const c = e.target as HTMLSelectElement & HTMLInputElement;
    if (c.dataset["ctl"] === "rkdevice") { RK.device = c.value === "smartwatch" ? "smartwatch" : c.value === "car-screen" ? "car-screen" : "rider-phone"; RK.moving = false; S.open = ""; panel(); draw(); (window as unknown as { __refit: () => void }).__refit(); return; }
    if (c.dataset["ctl"] === "moving") { RK.moving = c.checked; draw(); return; }
    if (c.dataset["ctl"] === "battery") { RX.battery = Number(c.value) || 100; if (RX.battery > 3) RX.lastSent = false; draw(); return; }
    if (panelChange(e.target as HTMLSelectElement, S, DATA)) panel(); draw(); });
  window.setInterval(() => { S.ticks += 1; LOG.tick(S.online, false, S.ticks, () => undefined); if (S.share && S.online && job()?.state === "picked_up" && S.ticks % 8 === 0 && S.trip < 16) { S.trip += 1; draw(); } }, 400);
  const base = Number($("#rig").dataset["width"]) || 400;
  (window as unknown as { __refit: () => void }).__refit = () => { const r = $("#rig"); document.documentElement.style.setProperty("--fit", String(Math.min(1, (r.clientWidth - 8) / (RK.device === "car-screen" ? 680 : base)))); };
  addEventListener("resize", () => (window as unknown as { __refit: () => void }).__refit());
  (window as unknown as { __refit: () => void }).__refit();
}
main();
