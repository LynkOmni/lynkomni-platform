/** The LynkFiles signing tablet (SIX SERVICES UPDATE 69.7; build section 4B): a customer-facing tablet at a counter. The person reads
 *  every page of the document, then signs exactly the version they saw, with a finger, a stylus or their typed name (every gesture has
 *  a button or a key). Reading works without internet; a signature is written only by the cloud (DocumentSigned is cloud only), and an
 *  identity-checked signature only when the licensed partner confirms (catalog/files.v1.json signing.levels; services/files_partners.py).
 *  The verification code comes from ts/src/files.ts and never shows who signed. No staff PIN: a customer screen with no user. */
import { Country, EventLog, Words, applyRoot, esc, fitRig, panelChange, panelHtml, stateButtons, randomBelow } from "../../../ts/src/emulator.js";
import { turnDevice } from "../../../ts/src/turn.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";
import type { UserState } from "../../../ts/src/pos.js";
import { DeviceMode, wireDevice } from "../../../ts/src/devicemode.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";
import { FILES } from "../../../ts/src/files.generated.js";
import { formatCode, levelPartner, nextSigners, signRequestState } from "../../../ts/src/files.js";
import type { FilesRegister } from "../../../ts/src/files.js";
import { EmKit, kitFor, wireKit } from "../../../ts/src/emkit.js";
import { EMULATOR_REGISTER } from "../../../ts/src/emulators.generated.js";
import { watchNames } from "../../../ts/src/names.js";
import { hintFor } from "../../../ts/src/hints.js";
import { PageWait } from "../../../ts/src/placeholder.js";
void PageWait;   // the waiting part (catalog/placeholders.v1.json) travels with the kit; its words come with it

declare const DATA: Build;
const F = FILES as unknown as FilesRegister;
type View = "ready" | "read" | "sign" | "done" | "declined";
const S: PanelState & { view: View; read: boolean; name: string; strokes: string[]; level: string; state: UserState | ""; code: string; reason: string; ticks: number } =
  { online: true, fail: false, type: "shop", tier: "plus", country: "", realUser: false, practice: false, dark: false, lang: "en", view: "ready", read: false, name: "", strokes: [], level: "simple", state: "", code: "", reason: "declined", ticks: 0 };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <E extends HTMLElement>(sel: string): E => document.querySelector(sel) as E;
const icon = (id: string, cls = "ic"): string => `<span class="${cls}" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); });
const SIGNERS = ["a", "b"];                 // two signers in order; this tablet serves the first
let signed: string[] = [];
const VERSION = 2, FP = "9f3c51e8";          // the sample document's version and the start of its fingerprint
const DM = new DeviceMode(DEVICES, "tablet");
const DEV = wireDevice(DM, { t, icon: (id) => icon(id), screen: () => document.getElementById("screen"), pad: () => document.getElementById("pad"), back: () => { back(); draw(); }, redraw: () => draw(), rtl: () => document.getElementById("screen")?.dir === "rtl" });
const KIT = new EmKit(EMULATOR_REGISTER, kitFor(EMULATOR_REGISTER, "files.signing_tablet", "Counter tablet", { short_side: 768, keys: false, speaker: true }, "android"), (type, payload, origin) => { LOG.emit(type, payload, origin); });
const KW = wireKit(KIT, { t, icon: (id, cls) => icon(id, cls), online: () => S.online, redraw: () => draw() });
const uuid = (): string => "0192f0c0-0000-7000-8000-" + String(randomBelow(1e6)).padStart(6, "0") + String(randomBelow(1e6)).padStart(6, "0");
const REQ = uuid();

function back(): void { S.view = S.view === "sign" ? "read" : "ready"; }
function hasMark(): boolean { return S.strokes.length > 0 || S.name.trim().length >= 2; }
function onlineNote(): string { return S.online ? "" : `<p class="notice" role="status">${esc(t("fs_online_only"))}</p>`; }
function head(): string {
  const turn = nextSigners(F, "in_order", SIGNERS, signed)[0], n = turn ? SIGNERS.indexOf(turn) + 1 : SIGNERS.length;
  return `<p class="sub">${esc(t("fs_turn", { n, total: SIGNERS.length }))} · <span class="tag">${esc(t("fs_sample"))}</span></p>`;
}
function screen(): string {
  switch (S.view) {
    case "ready": return `<h2>${esc(t("fs_hand"))}</h2>${head()}<p>${esc(t("fs_doc"))}: <strong>${esc(t("fs_doc_name"))}</strong></p>
      <p class="sub">${esc(t(S.level === "simple" ? "fs_level_simple" : "fs_level_identity"))}</p><div class="acts"><button class="primary" data-act="fs:start">${esc(t("fs_start"))}</button></div>`;
    case "read": return `<h2>${esc(t("fs_doc_name"))}</h2>${head()}<p class="sub">${esc(t("fs_version", { n: VERSION, fp: FP }))}</p>
      <div class="doc" tabindex="0" role="document" aria-label="${esc(t("fs_doc_name"))}">${[1, 2, 3].map((n) => `<h3>${esc(t("fs_page", { n, total: 3 }))}</h3><p>${esc(t(`fs_p${n}`))}</p>`).join("")}</div>
      <label class="tick"><input type="checkbox" data-in="fs:read"${S.read ? " checked" : ""}><span>${esc(t("fs_read_all"))}</span></label>
      <div class="acts"><button class="primary" data-act="fs:tosign"${S.read ? "" : ' disabled data-why="fs_read_all"'}>${esc(t("fs_sign"))}</button><button class="ghost" data-act="fs:decline">${esc(t("fs_decline"))}</button></div>`;
    case "sign": return `<h2>${esc(t("fs_draw"))}</h2><p class="sub">${esc(t("fs_exact"))} ${esc(t("fs_version", { n: VERSION, fp: FP }))}</p>
      <div class="padbox" id="sigpad" role="img" aria-label="${esc(t("fs_pad_label"))}"><svg viewBox="0 0 600 160" preserveAspectRatio="none" aria-hidden="true">${S.strokes.map((d) => `<path d="${esc(d)}"/>`).join("")}</svg><span class="line"></span></div>
      <label class="field" for="fsName"><span>${esc(t("fs_type"))}</span><input id="fsName" data-in="fs:name" value="${esc(S.name)}" autocomplete="name" placeholder="${esc(hintFor("name", t))}"></label>
      ${onlineNote()}${S.level !== "simple" && S.online ? `<p class="note">${icon("ui-info")}<span>${esc(t("fs_identity"))}</span></p>` : ""}
      <div class="acts"><button class="primary" data-act="fs:sign"${hasMark() && S.online ? "" : ` disabled data-why="${S.online ? "fs_draw" : "fs_online_only"}"`}>${esc(t("fs_sign_now"))}</button><button class="ghost" data-act="fs:clear">${esc(t("fs_clear"))}</button><button class="ghost" data-act="fs:back">${esc(t("fs_back"))}</button></div>`;
    case "done": {
      const st = signRequestState(SIGNERS, signed);
      return `<h2>${esc(t(S.state === "confirmed" ? "fs_done" : "fs_waiting"))}</h2>${S.state ? chip(S.state) : ""}
      ${S.state === "confirmed" && S.code ? `<p class="sub">${esc(t("fs_code"))}</p><p class="code">${esc(S.code)}</p><p class="note">${icon("ui-info")}<span>${esc(t("fs_code_note"))}</span></p>` : ""}
      ${S.state === "confirmed" ? `<p>${esc(t(st === "completed" ? "fs_hand_back" : "fs_next_signer"))}</p><div class="acts"><button class="ghost" data-act="fs:again">${esc(t("fs_hand_back"))}</button></div>` : ""}`;
    }
    case "declined": return `<h2>${esc(t("fs_declined"))}</h2><label class="field" for="fsReason"><span>${esc(t("fs_reason"))}</span><select id="fsReason" data-in="fs:reason">${["declined", "wrong_document", "not_me"].map((r) => `<option value="${r}"${r === S.reason ? " selected" : ""}>${esc(t(`fs_reason_${r}`))}</option>`).join("")}</select></label>
      <div class="acts"><button class="ghost" data-act="fs:again">${esc(t("fs_hand_back"))}</button></div>`;
  }
}
let REFIT: (() => void) | undefined;
/** Turning (owner, 2026-11-26): Upright or Sideways from the panel; the body takes its turned shape and the screen its layout. */
const turnNow = (): void => turnDevice(DEVICES, { rig: $("#rig"), body: document.querySelector(".tab"), screens: [$("#screen")], turn: S.turn, width: 760, sidewaysWidth: 540, shape: { width: 1280, height: 800, device: "tablet" } }, REFIT);
function draw(): void { turnNow();
  const el = $("#screen"); el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); DEV.draw(el); applyRoot(el, W);
  el.innerHTML = `<div class="tbody" data-wait-area data-shape="text">${screen()}</div>`; $("#mark").innerHTML = DATA.brand.body;
  wirePad(); KW.after(el);
}
/** The signature box: a finger, a stylus or a mouse draws; the typed name and the buttons do the same without a gesture. */
function wirePad(): void {
  const pad = document.getElementById("sigpad"); if (!pad) return;
  let cur = "";
  const pt = (e: PointerEvent): string => { const r = pad.getBoundingClientRect(); return `${Math.round(((e.clientX - r.left) / r.width) * 600)} ${Math.round(((e.clientY - r.top) / r.height) * 160)}`; };
  pad.addEventListener("pointerdown", (e) => { pad.setPointerCapture(e.pointerId); cur = `M${pt(e)}`; });
  pad.addEventListener("pointermove", (e) => { if (!cur) return; cur += ` L${pt(e)}`; const svg = pad.querySelector("svg"); if (svg) svg.innerHTML = [...S.strokes, cur].map((d) => `<path d="${esc(d)}"/>`).join(""); });
  pad.addEventListener("pointerup", () => { if (cur.includes("L")) S.strokes.push(cur); cur = ""; draw(); });
}
function sign(): void {
  if (!S.online || !hasMark()) return;
  S.state = "sent"; S.view = "done"; draw();
  const turn = signed.length + 1;
  window.setTimeout(() => {   // the cloud alone writes the signature; an identity-checked one only when the partner confirms
    if (S.level !== "simple" && !levelPartner(F, S.level)) return;
    signed = [...signed, SIGNERS[turn - 1]!];
    LOG.emit("DocumentSigned", { request_id: REQ, turn, level: S.level }, "server");
    S.code = formatCode(F, BigInt(randomBelow(2 ** 31)) * 2654435761n);
    S.state = "confirmed"; draw();
  }, S.level === "simple" ? 600 : 1400);
}
function act(a: string): void {
  if (!a.startsWith("fs:")) return;
  const k = a.slice(3);
  if (k === "start") { S.view = "read"; S.read = false; }
  else if (k === "tosign" && S.read) S.view = "sign";
  else if (k === "back") back();
  else if (k === "clear") { S.strokes = []; S.name = ""; }
  else if (k === "sign") { sign(); return; }
  else if (k === "decline") { S.view = "declined"; LOG.emit("SignatureDeclined", { request_id: REQ, turn: signed.length + 1, reason: S.reason }, "server"); }
  else if (k === "again") { S.view = "ready"; S.read = false; S.name = ""; S.strokes = []; S.state = ""; S.code = ""; if (signRequestState(SIGNERS, signed) === "completed") signed = []; }
  draw();
}
function panel(): void {
  $("#panel").innerHTML = panelHtml(["online", "country", "dark", "lang", "turn"], S, W, C) + DEV.control()
    + `<label class="field"><span>${esc(t("fs_level"))}</span><select data-ctl="level">${["simple", "identity_checked"].map((l) => `<option value="${l}"${l === S.level ? " selected" : ""}>${esc(t(l === "simple" ? "fs_level_simple" : "fs_level_identity"))}</option>`).join("")}</select></label>`;
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), ["ready", "read", "sign", "offline", "signed", "declined"], (k) => {
    S.online = k !== "offline"; S.read = k !== "ready"; S.strokes = k === "sign" || k === "offline" ? ["M40 110 L120 60 L200 120 L300 50 L420 110"] : []; S.name = "";
    S.view = k === "ready" ? "ready" : k === "read" ? "read" : k === "declined" ? "declined" : k === "signed" ? "done" : "sign";
    if (k === "signed") { S.state = "confirmed"; S.code = formatCode(F, 987654321987n); } else { S.state = ""; S.code = ""; }
    panel(); draw();
  });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? "";
  panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (b && DEV.act(b.dataset["act"] ?? "")) return; if (b && !b.hasAttribute("disabled")) act(b.dataset["act"] ?? ""); });
  document.addEventListener("input", (e) => { const el = e.target as HTMLInputElement; if (el.dataset["in"] === "fs:name") { S.name = el.value.slice(0, 80); const pos = el.selectionStart; draw(); const again = document.getElementById("fsName") as HTMLInputElement | null; if (again) { again.focus(); if (pos !== null) again.setSelectionRange(pos, pos); } } });
  document.addEventListener("change", (e) => { const el = e.target as HTMLInputElement & HTMLSelectElement;
    if (el.dataset["in"] === "fs:read") { S.read = el.checked; draw(); return; }
    if (el.dataset["in"] === "fs:reason") { S.reason = el.value; return; } });
  $("#panel").addEventListener("change", (e) => { const el = e.target as HTMLSelectElement; if (el.dataset["ctl"] === "level") { S.level = el.value; draw(); return; } if (DEV.change(el)) return; if (panelChange(el, S, DATA)) panel(); draw(); });
  document.addEventListener("keydown", (e) => { if (DEV.key(e)) return; });
  window.setInterval(() => { S.ticks += 1; LOG.tick(S.online, false, S.ticks, () => undefined); }, 400);
  REFIT = fitRig($("#rig"), 760); turnNow();
}
main();
/** Every Lynk name on this page carries its plain word (catalog/names.v1.json, ts/src/names.ts). */
watchNames(document.body, () => t);
