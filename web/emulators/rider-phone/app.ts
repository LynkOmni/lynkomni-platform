/** Rider phone for own-staff deliveries (N8, blueprint 44 I; 42 J added emulator). The rider sees the deliveries assigned to
 *  them, records pickup at the shop and delivery at the door with the customer's code or a photo of the parcel (never of a
 *  person). Steps are device events (DeliveryPickedUp, DeliveryDelivered) that work offline and are sent when a link exists.
 *  LynkOmni never employs riders: the rider is the shop's own staff. */
import type { UserState } from "../../../ts/src/pos.js";
import { nextDeliveryStep } from "../../../ts/src/restaurant.js";
import type { DeliveryState } from "../../../ts/src/restaurant.js";
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, newId, panelChange, panelHtml, plain, stateButtons } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";

declare const DATA: Build;
interface Job { id: string; order: number; area: string; amount: number; state: DeliveryState; code: string; proof?: "code" | "photo" }
const S: PanelState & { jobs: Job[]; open: string; typed: string; msg: string; ticks: number } = { online: true, fail: false, type: "shop", tier: "plus", country: "", realUser: false, practice: false, dark: false, lang: "en", jobs: [], open: "", typed: "", msg: "", ticks: 0 };
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

function list(): string {
  return `<h2>${esc(t("deliveries"))}</h2><ul class="jobs">${S.jobs.map((j) => `<li><button data-act="open:${j.id}"><strong>${esc(t("order", { n: j.order }))}</strong><span>${esc(t(j.area))}</span><span class="st st-${j.state}">${esc(stateWord(j.state))}</span>${icon("ui-chevron-right")}</button></li>`).join("")}</ul><p class="note">${esc(t("proof_photo"))}</p>`;
}
function detail(j: Job): string {
  const next = nextDeliveryStep(j.state);
  const syncChip = j.state === "picked_up" ? chip(lastSync(j.id, "DeliveryPickedUp")) : j.state === "delivered" ? chip(lastSync(j.id, "DeliveryDelivered")) : "";
  return `<button class="link" data-act="back">${icon("ui-arrow-left")}${esc(t("back"))}</button><h2>${esc(t("order", { n: j.order }))}</h2><p>${esc(t(j.area))} · ${esc(C.money(j.amount))}</p>
    <p class="state">${esc(stateWord(j.state))} ${syncChip}</p>
    ${next === "picked_up" ? `<button class="primary" data-act="pickup">${esc(t("picked_up"))}</button>` : ""}
    ${next === "delivered" ? `<label class="codebox">${esc(t("delivery_code", { code: "" }))}<input inputmode="numeric" maxlength="6" data-field="code" value="${esc(S.typed)}" autocomplete="off"></label>
      <button class="primary" data-act="deliver:code" ${S.typed.length === 6 ? "" : "disabled"}>${esc(t("delivered"))}</button><p class="note">${esc(t("proof_code"))}</p>
      <button class="secondary" data-act="deliver:photo">${icon("ui-receipt")}${esc(t("proof_photo"))}</button>` : ""}
    ${S.msg ? `<p class="warn" role="alert">${esc(S.msg)}</p>` : ""}<p class="note">${esc(t("track"))}: shop.lynkomni.com/track/LODLV-…</p><p class="hint">${esc(t("pickup_code"))}: ${esc(j.code)}</p>`;
}
function draw(): void {
  const el = $("#screen"); if (!el) return; el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W);
  const p = LOG.pending();
  el.innerHTML = `<header class="rtop"><span class="rmark">${icon("product-chat")}</span><strong>${esc(t("deliveries"))}</strong><span class="net${S.online ? "" : " off"}">${icon(S.online ? "ui-sync" : "ui-offline")}${esc(t(S.online ? "online" : "offline"))}${p.count ? ` · ${p.count}` : ""}</span></header><div class="rbody">${job() ? detail(job()!) : list()}</div>`;
}
function act(a: string): void {
  const [k = "", v = ""] = a.split(":"); const j = job();
  if (k === "open") { S.open = S.jobs.some((x) => x.id === v) ? v : ""; S.typed = ""; S.msg = ""; }
  else if (k === "back") S.open = "";
  else if (k === "pickup" && j && nextDeliveryStep(j.state) === "picked_up") { j.state = "picked_up"; LOG.emit("DeliveryPickedUp", { delivery_id: j.id }); }
  else if (k === "deliver" && j && nextDeliveryStep(j.state) === "delivered") {
    if (v === "code" && S.typed !== j.code) { S.msg = t("wrong_code"); draw(); return; }
    j.state = "delivered"; j.proof = v === "photo" ? "photo" : "code"; LOG.emit("DeliveryDelivered", { delivery_id: j.id, proof: j.proof }); S.msg = "";
  }
  draw();
}
function seed(): void {
  S.jobs = [{ id: newId(), order: 1042, area: "area_1", amount: 8500, state: "accepted", code: code6() }, { id: newId(), order: 1043, area: "area_2", amount: 23000, state: "accepted", code: code6() }, { id: newId(), order: 1039, area: "area_3", amount: 4000, state: "delivered", code: code6(), proof: "code" }];
}
function panel(): void {
  $("#panel").innerHTML = panelHtml(["online", "country", "dark", "lang"], S, W, C);
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), ["list", "pickup", "deliver", "delivered", "wrong"], (k) => { seed(); const j = S.jobs[0]!; S.open = k === "list" ? "" : j.id; S.msg = "";
    if (k === "deliver" || k === "delivered" || k === "wrong") j.state = "picked_up"; if (k === "delivered") { j.state = "delivered"; } if (k === "wrong") { S.typed = "000000"; S.msg = t("wrong_code"); } draw(); });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? ""; seed(); panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (b && !b.hasAttribute("disabled")) act(b.dataset["act"] ?? ""); });
  document.addEventListener("input", (e) => { const el = e.target as HTMLInputElement; if (el.dataset["field"] === "code") { S.typed = plain(el.value).replace(/\D/g, "").slice(0, 6); const pos = el.selectionStart; draw(); const n = document.querySelector<HTMLInputElement>('[data-field="code"]'); if (n) { n.focus(); n.setSelectionRange(pos, pos); } } });
  $("#panel").addEventListener("change", (e) => { if (panelChange(e.target as HTMLSelectElement, S, DATA)) panel(); draw(); });
  window.setInterval(() => { S.ticks += 1; LOG.tick(S.online, false, S.ticks, () => undefined); }, 400);
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 400);
}
main();
