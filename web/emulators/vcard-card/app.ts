/** LynkVCard as a real card (42 J build section 3; CLAUDE.md LynkVCard rules). The four tier faces from visuals/cards.py flip
 *  to their backs. Freeze is the only action that may queue offline, and the card is shown frozen only when the issuer confirms.
 *  Card details are never sent to this screen: after a fresh check they appear only inside the licensed issuer's secure display,
 *  for a short time, and never offline. Cards stay "Coming to your country soon" until an issuer is signed there. */
import type { UserState } from "../../../ts/src/pos.js";
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, newId, panelChange, panelHtml, reducedMotion, stateButtons } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";
import { cardFormFields, cardName, cardWord } from "../../../ts/src/devicekit.js";

interface Card { face: string; front: string; front_alt: string; back: string; back_alt: string; price_usd: number; limits: Record<string, unknown> }
interface Sample { front: string; front_alt: string; back: string; back_alt: string }
declare const DATA: Build & { cards: Record<string, Card>; nearLimit: { svg: string; alt: string }; samples: Record<string, Sample> };
/** MASTER UPDATE section 3: the card group on the card screens, the twelve sample cards and "Get a card" on the sandbox partners. */
const GROUPS = ["prepaid", "debit", "credit"] as const;
const FACES = ["edge", "hub", "core", "omni"] as const;
const G = { group: "prepaid" as (typeof GROUPS)[number], sample: "" as string, ask: "prepaid" as (typeof GROUPS)[number], sent: "" as "" | "sent" | "confirmed" | "failed" };
const TIERS = ["free", "plus", "pro", "max"] as const;
const DETAILS_S = 30;            // the issuer's secure display hides the details again after a short time
const S: PanelState & { flipped: boolean; freeze: "none" | UserState; frozen: boolean; stepup: boolean; details: number; near: boolean; ticks: number } =
  { online: true, fail: false, type: "shop", tier: "pro", country: "", realUser: false, practice: false, dark: false, lang: "en", flipped: false, freeze: "none", frozen: false, stepup: false, details: 0, near: false, ticks: 0 };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const icon = (id: string): string => `<span class="ic" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); });
const card = (): Card => DATA.cards[S.tier] ?? (DATA.cards["free"] as Card);
const issuerReady = (): boolean => !S.realUser;       // no issuer is signed in any country yet (provider ledger: vcard_issuer)

function drawCard(): void {
  if (G.sample) {                                  // a sample card (Get a card, the store): labelled SAMPLE on the picture itself
    const sm = DATA.samples[G.sample]; if (!sm) return;
    $("#front").innerHTML = `<div role="img" aria-label="${esc(sm.front_alt)}">${sm.front}</div>`;
    $("#back").innerHTML = `<div role="img" aria-label="${esc(sm.back_alt)}">${sm.back}</div>`;
    $("#card").classList.toggle("flipped", S.flipped); $("#card").classList.remove("is-frozen"); return;
  }
  const c = card(); const front = S.tier === "pro" && S.near ? DATA.nearLimit : { svg: c.front, alt: c.front_alt };
  $("#front").innerHTML = `<div role="img" aria-label="${esc(front.alt)}">${front.svg}</div>${S.frozen ? `<span class="frozen">${esc(t("frozen"))}</span>` : ""}`;
  $("#back").innerHTML = `<div role="img" aria-label="${esc(c.back_alt)}">${c.back}</div>`;
  $("#card").classList.toggle("flipped", S.flipped); $("#card").classList.toggle("is-frozen", S.frozen);
}
function app(): string {
  if (!issuerReady()) return `<div class="soon"><h2>LynkVCard</h2><p>${esc(t("coming_soon"))}</p><button class="secondary" data-act="notify" ${notified ? "disabled" : ""}>${esc(notified ? t("saved") : t("notify_me"))}</button></div>`;
  const c = card(); const cap = c.limits["monthly_cap_usd"];
  const freezeLine = S.freeze === "none" ? "" : S.freeze === "confirmed" ? "" : `<p class="note">${esc(t("freeze_requested"))} ${chip(S.freeze)}</p>`;
  const details = S.details > 0 ? `<div class="issuer" role="region" aria-label="${esc(t("show_details"))}"><p class="note">${esc(t("details_secure"))}</p><div class="masked" aria-hidden="true">•••• •••• •••• ••••</div><p class="note">${S.details}s</p></div>` : "";
  const face = FACES[(TIERS as readonly string[]).indexOf(S.tier)] ?? "edge";
  const gallery = `<h3>${esc(t("vc_twelve"))}</h3><div class="gallery" role="group" aria-label="${esc(t("vc_twelve"))}">${FACES.map((f) => GROUPS.map((g) => { const sm = DATA.samples[`${f}-${g}`]; return sm ? `<button class="thumb${G.sample === `${f}-${g}` ? " on" : ""}" data-act="sample:${f}-${g}" aria-label="${esc(cardName(g, f))}, ${esc(cardWord(g))}"><span aria-hidden="true">${sm.front}</span><span class="tl">${esc(cardName(g, f))}</span></button>` : ""; }).join("")).join("")}</div>`;
  const form = G.sent === "sent" ? `<p class="note">${esc(t("card_sent"))} ${chip("sent")}</p>` : G.sent === "confirmed" ? `<p class="note">${esc(t("card_confirmed"))} ${chip("confirmed")}</p>` : G.sent === "failed" ? `<p class="note">${esc(t("vc_failed"))} ${chip("failed")}</p>`
    : `<label class="fieldrow"><span>${esc(t("card_which"))}</span><select data-act-change="ask">${GROUPS.map((g) => `<option value="${g}" ${G.ask === g ? "selected" : ""}>${esc(cardName(g, face))} · ${esc(cardWord(g))}</option>`).join("")}</select></label>
      <ul class="fields">${cardFormFields(G.ask).filter((f) => f !== "holder" && f !== "form").map((f) => `<li>${esc(t(`card_f_${f}`))}</li>`).join("")}</ul>${G.ask === "credit" ? `<p class="note">${esc(t("card_lender"))}</p>` : ""}
      <button class="primary" data-act="getcard" ${S.online ? "" : "disabled"}>${esc(t("card_send"))}</button>${S.online ? "" : `<p class="note">${esc(t("online_only"))}</p>`}`;
  const getCard = `<h3>${esc(t("card_get"))}</h3>${form}`;
  if (G.sample) return `<h2>${esc(cardName(G.sample.split("-")[1] ?? "prepaid", G.sample.split("-")[0] ?? "edge"))}</h2><p class="note">${esc(t("vc_sample_note"))}</p><div class="row"><button class="secondary" data-act="flip">↻ ${esc(t("flip_card"))}</button><button class="secondary" data-act="sample:">${esc(t("vc_my_card"))}</button></div>${gallery}${getCard}`;
  return `<h2>${esc(cardName(G.group, face))}</h2><p class="note">${esc(cardWord(G.group))}${G.group === "credit" ? ` · ${esc(t("card_lender"))}` : ""}</p><p class="note">${esc(t("placeholder_limits"))} ${typeof cap === "number" ? `${esc(C.money(cap * 100, "USD"))} / ${esc(t("money"))}` : ""}</p>
    <div class="row"><button class="primary" data-act="freeze">${icon("ui-lock")}${esc(t(S.frozen ? "unfreeze_card" : "freeze_card"))}</button><button class="secondary" data-act="flip" aria-label="${esc(t("flip_card"))}">↻ ${esc(t("flip_card"))}</button></div>${freezeLine}
    <button class="secondary" data-act="details" ${S.online ? "" : "disabled"}>${esc(t("show_details"))}</button>${S.online ? "" : `<p class="note">${esc(t("online_only"))}</p>`}${details}
    ${S.stepup ? `<div class="stepup" role="dialog" aria-label="${esc(t("step_up"))}"><h3>${esc(t("step_up"))}</h3><div class="row"><button class="primary" data-act="stepok">${esc(t("confirm"))}</button><button class="secondary" data-act="stepcancel">${esc(t("cancel"))}</button></div></div>` : ""}${gallery}${getCard}`;
}
function draw(): void { drawCard(); const el = $("#screen"); el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W); el.innerHTML = app(); }
function act(a: string): void {
  if (a === "flip") S.flipped = !S.flipped;
  if (a.startsWith("sample:")) { G.sample = a.slice(7); S.flipped = false; }
  if (a === "getcard" && S.online && !G.sent) {         // online only; the card appears only when the licensed partner confirms
    G.sent = "sent"; LOG.emit("CardRequested", { request_id: newId(), group: G.ask, tier: S.tier }, "device", "sent");
    window.setTimeout(() => { G.sent = S.fail ? "failed" : "confirmed"; if (!S.fail) G.group = G.ask; LOG.emit(S.fail ? "CardRequestFailed" : "CardRequestConfirmed", { group: G.ask, by: "partner" }, "server"); draw(); }, reducedMotion() ? 300 : 1400);
  }
  if (a === "freeze") {
    const want = !S.frozen;
    if (!want && !S.online) { S.freeze = "none"; draw(); return; }       // only a freeze may queue offline; unfreezing needs the issuer now
    S.freeze = S.online ? "sent" : "queued";
    if (!S.online && want) LOG.emit("VirtualCardFreezeIntentQueued", { card: CARD, nonce: newId() }, "device", "queued");   // offline: an intent, not a freeze
    const answer = (): void => { if (!S.online) return; S.freeze = S.fail ? "failed" : "confirmed"; if (!S.fail) { S.frozen = want; LOG.emit(want ? "VirtualCardFrozen" : "VirtualCardUnfrozen", { card: CARD }, "server"); } draw(); };
    if (S.online) window.setTimeout(answer, reducedMotion() ? 300 : 1600); else pendingFreeze = answer;
  }
  if (a === "details" && S.online) S.stepup = true;
  if (a === "stepok") { S.stepup = false; S.details = DETAILS_S; LOG.emit("StepUpPassed", { purpose: "card_details" }, "server"); }
  if (a === "stepcancel") S.stepup = false;
  if (a === "notify") notified = true;
  draw();
}
let pendingFreeze: (() => void) | null = null;
let notified = false;
const CARD = "LOVC-····";      // the card's public id from core/ids.py, masked; the card number never reaches this screen
function panel(): void {
  $("#panel").innerHTML = panelHtml(["online", "fail", "plan", "country", "real", "dark", "lang"], S, W, C, { tiers: TIERS });
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), ["free", "plus", "pro", "max", "back", "near-limit", "freezing", "frozen", "details", "coming-soon"], (k) => {
    S.flipped = false; S.near = false; S.details = 0; S.stepup = false; S.realUser = false;
    if ((TIERS as readonly string[]).includes(k)) S.tier = k as (typeof TIERS)[number];
    if (k === "back") S.flipped = true; if (k === "near-limit") { S.tier = "pro"; S.near = true; }
    if (k === "freezing") { S.freeze = "sent"; S.frozen = false; } if (k === "frozen") { S.freeze = "confirmed"; S.frozen = true; }
    if (k === "details") S.details = DETAILS_S; if (k === "coming-soon") S.realUser = true; panel(); draw(); });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? ""; panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (b && !b.hasAttribute("disabled")) act(b.dataset["act"] ?? ""); });
  $("#card").addEventListener("click", () => act("flip"));
  $("#screen").addEventListener("change", (e) => { const el = e.target as HTMLSelectElement; if (el.dataset["actChange"] === "ask") { G.ask = GROUPS.find((g) => g === el.value) ?? "prepaid"; draw(); } });
  $("#panel").addEventListener("change", (e) => { if (panelChange(e.target as HTMLSelectElement, S, DATA, { tiers: TIERS })) panel(); if (S.online && pendingFreeze) { const f = pendingFreeze; pendingFreeze = null; S.freeze = "sent"; window.setTimeout(f, 800); } if (!S.online) S.details = 0; draw(); });
  window.setInterval(() => { S.ticks += 1; if (S.details > 0 && S.ticks % 3 === 0) { S.details = Math.max(0, S.details - 1); draw(); } LOG.tick(S.online, false, S.ticks, () => undefined); }, 333);
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 700);
}
main();
