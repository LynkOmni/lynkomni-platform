/** LynkMesh relay between devices (42 J build section 3; CLAUDE.md LynkMesh rules). Till A has no connection; it seals its
 *  queued batch (services/sealing.py in the reference) and hands it to device B nearby, which has one. B can neither read nor
 *  change the batch: it only carries it. The sale on A shows "sent, awaiting cloud" until the cloud accepts it, and a relay can
 *  never produce "confirmed". LynkMesh carries data, never money, and takes no fee. A tampered batch is refused by the cloud. */
import { Cart, salePayload } from "../../../ts/src/pos.js";
import type { UserState } from "../../../ts/src/pos.js";
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, newId, panelChange, panelHtml, reducedMotion, stateButtons } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";

declare const DATA: Build;
interface Batch { id: string; items: number; state: UserState; tampered: boolean }
const S: PanelState & { aQueued: number; batches: Batch[]; bOnline: boolean; tamper: boolean; moving: boolean; ticks: number } =
  { online: false, fail: false, type: "shop", tier: "free", country: "", realUser: false, practice: false, dark: false, lang: "en", aQueued: 0, batches: [], bOnline: true, tamper: false, moving: false, ticks: 0 };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const icon = (id: string): string => `<span class="ic" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); });
const product = { id: newId(), name: "p_bread", price: 1000, category: "food" };
const short = (id: string): string => id.slice(-6);

function sell(): void {
  const c = new Cart(); c.add({ ...product, name: t(product.name) });
  const sale = salePayload(c, newId(), `MA-${S.aQueued + 1 + S.batches.reduce((n, b) => n + b.items, 0)}`, C.pack().currency);
  LOG.emit("SaleRecorded", sale, "device", "queued"); S.aQueued += 1; draw();
}
function relay(): void {
  if (!S.aQueued || S.moving) return;
  const b: Batch = { id: newId(), items: S.aQueued, state: "sent", tampered: S.tamper }; S.aQueued = 0; S.batches.unshift(b); S.moving = true;
  for (const e of LOG.events) if (e.sync === "queued") e.sync = "sent";
  draw();
  window.setTimeout(() => { S.moving = false; draw(); if (S.bOnline) window.setTimeout(() => cloud(b), reducedMotion() ? 200 : 1200); }, reducedMotion() ? 200 : 1400);
}
function cloud(b: Batch): void {
  b.state = b.tampered ? "failed" : "accepted";
  for (const e of LOG.events) if (e.sync === "sent") e.sync = b.state;
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));     // the relayed sales now show what the cloud answered
  draw();
}
function draw(): void {
  for (const [id, scr] of [["A", $("#screenA")], ["B", $("#screenB")]] as const) { scr.classList.toggle("dark", S.dark); scr.classList.toggle("light", !S.dark); applyRoot(scr, W); }
  const latest = S.batches[0];
  $("#screenA").innerHTML = `<header>${icon("ui-offline")}<strong>${esc(t("offline"))}</strong></header><div class="mb"><p>${esc(t("pending_items", { n: S.aQueued }))} ${S.aQueued ? chip("queued") : ""}</p>
    <button class="primary" data-act="sell">${esc(t("new_sale"))} · ${esc(C.money(product.price))}</button><button class="secondary" data-act="relay" ${S.aQueued && !S.moving ? "" : "disabled"}>${esc(t("relay_now"))}</button>
    ${latest ? `<p class="state">${latest.state === "sent" ? esc(t("mesh_relay")) : ""} ${chip(latest.state)}</p>` : ""}<p class="note">${esc(t("relay_body"))}</p></div>`;
  $("#screenB").innerHTML = `<header>${icon(S.bOnline ? "ui-sync" : "ui-offline")}<strong>${esc(t(S.bOnline ? "online" : "offline"))}</strong></header><div class="mb"><p>${esc(t("relayed", { n: S.batches.reduce((n, b) => n + b.items, 0) }))}</p>
    <ul>${S.batches.slice(0, 4).map((b) => `<li><code>#${esc(short(b.id))}</code> ${chip(b.state)}</li>`).join("")}</ul><p class="note">${esc(t("mesh_no_money"))}</p></div>`;
  $("#labelA").textContent = "A"; $("#labelB").textContent = "B";
  $("#link").classList.toggle("moving", S.moving);
  $("#cloud").innerHTML = `${icon("ui-globe")}<span>${latest ? esc(t(latest.state === "accepted" ? "st_accepted" : latest.state === "failed" ? "st_failed" : "st_sent")) : ""}</span>`;
}
function panel(): void {
  $("#panel").innerHTML = panelHtml(["country", "dark", "lang"], S, W, C);
  $("#panel").insertAdjacentHTML("afterbegin", `<label><input type="checkbox" id="bOnline" ${S.bOnline ? "checked" : ""}> <span>B: ${esc(t("internet"))}</span></label><label><input type="checkbox" id="tamper" ${S.tamper ? "checked" : ""}> <span>${esc(t("tamper_test"))}</span></label>`);
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), ["queued", "relaying", "accepted", "refused"], (k) => { S.batches = []; S.aQueued = 0; sell(); sell(); if (k !== "queued") { S.tamper = k === "refused"; relay(); if (k !== "relaying") { S.moving = false; const b = S.batches[0]; if (b) cloud(b); } } panel(); draw(); });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? ""; panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (!b || b.hasAttribute("disabled")) return; if (b.dataset["act"] === "sell") sell(); if (b.dataset["act"] === "relay") relay(); });
  $("#panel").addEventListener("change", (e) => { const el = e.target as HTMLInputElement; if (el.id === "bOnline") S.bOnline = el.checked; else if (el.id === "tamper") S.tamper = el.checked; else if (panelChange(el, S, DATA)) panel(); draw(); });
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 900);
}
main();
