/** LynkKiosk: the self-service kiosk (NEW UPDATE 4; build section 3B). One kiosk does three jobs, each from its own engine:
 *  check in or out (LynkAttend, ts/src/attenddesk.ts), take a ticket (LynkQueue) and give an answer (LynkSurvey). It works by
 *  touch or by buttons only (arrows, OK and Back move across the on-screen keys), with or without internet. The camera and the
 *  fingerprint reader on the body answer for Face and Finger; a PIN or an IDCN is only ever shown as dots. */
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, panelChange, panelHtml, stateButtons } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";
import type { UserState } from "../../../ts/src/pos.js";
import type { T } from "../../../ts/src/shell.js";
import { brandMark } from "../../../ts/src/brand.js";
import { DeviceMode, wireDevice } from "../../../ts/src/devicemode.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";
import { PeopleHub } from "../../../ts/src/peoplehub.js";
import { atDoor } from "../../../ts/src/attenddesk.js";
import type { AtLook, AtPlan, AtTier } from "../../../ts/src/attenddesk.js";
import { pairCode, quKioskView, quPaper } from "../../../ts/src/queuedesk.js";
import type { QuLook, QuPlan } from "../../../ts/src/queuedesk.js";
import { svKioskView } from "../../../ts/src/surveydesk.js";
import type { SvLook, SvPlan } from "../../../ts/src/surveydesk.js";
import { EmKit, kitFor, wireKit } from "../../../ts/src/emkit.js";
import { EMULATOR_REGISTER } from "../../../ts/src/emulators.generated.js";

declare const DATA: Build & { people: { attend: Record<AtTier, AtPlan>; queue: Record<AtTier, QuPlan>; survey: Record<AtTier, SvPlan> } };
type Mode = "home" | "door" | "tickets" | "answer";
const S: PanelState & { mode: Mode; ticks: number } = { online: true, fail: false, type: "shop", tier: "plus", country: "", realUser: false, practice: false, dark: false, lang: "en", mode: "home", ticks: 0 };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <E extends HTMLElement>(sel: string): E => document.querySelector(sel) as E;
const icon = (id: string, cls = "ic"): string => `<span class="${cls}" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); });
const PH = new PeopleHub((type, payload, origin) => { LOG.emit(type, payload, origin); }, Date.now, DATA.people.attend, DATA.people.queue, DATA.people.survey);
PH.q.ownPrinter = true;                                                 // the kiosk prints tickets from its own slot
const clock = (ms: number): string => new Intl.DateTimeFormat(`${W.htmlLang()}-${C.pack().code}`, { timeZone: C.pack().tz, hour: "2-digit", minute: "2-digit" }).format(ms);
const look = (): AtLook => ({ t, icon, clock, money: (c) => C.money(c, "USD"), online: S.online, partner: !S.realUser, mayManage: false });
/** LynkQueue on the kiosk: the ticket comes out of the slot under the screen, so it is not drawn on the screen too. */
const quLook = (): QuLook => ({ ...look(), place: t("k_place"), powered: `<small class="pb">${esc(t("ppl_qu_powered", { brand: "LynkOmni" }))}</small>`, paper: false });
/** LynkSurvey on the kiosk: one person at a time, one question a page; saved on the kiosk at once and sent when the link is back. */
const svLook = (): SvLook => ({ ...look(), place: t("k_place"), powered: `<small class="pb">${esc(t("ppl_qu_powered", { brand: "LynkOmni" }))}</small>` });
/** After the PIN the kiosk speaks the person's own language (only the words change, never the steps or the record). */
const SPEAK = { t: (lang: string): T => (k, vars = {}) => (W.isTest() ? t(k, vars) : (DATA.i18n[lang]?.texts[k] ?? DATA.i18n["en"]?.texts[k] ?? k).replace(/\{(\w+)\}/g, (m, v: string) => (v in vars ? String(vars[v]) : m))),
  dir: (lang: string): "ltr" | "rtl" => (W.isTest() ? W.dir() : DATA.i18n[lang]?.dir ?? "ltr"), code: (lang: string): string => (W.isTest() ? "en" : lang) };

function home(): string {
  return `<div class="khome">${brandMark(DATA.brand.places, "customer-welcome", S.dark, "kmark")}<h2>${esc(t("k_welcome"))}</h2><p class="sub">${esc(t("k_choose"))}</p>
    <button type="button" class="kchoice" data-act="go:door">${icon("product-attend")}<span><strong>${esc(t("k_attend"))}</strong><span>${esc(t("k_attend_sub"))}</span></span></button>
    <button type="button" class="kchoice" data-act="go:tickets">${icon("product-queue")}<span><strong>${esc(t("k_ticket"))}</strong><span>${esc(t("k_ticket_sub"))}</span></span></button>
    <button type="button" class="kchoice" data-act="go:answer">${icon("product-survey")}<span><strong>${esc(t("k_answer"))}</strong><span>${esc(t("k_answer_sub"))}</span></span></button></div>`;
}
const bar = (title: string): string => `<div class="kbar"><button type="button" class="kback" data-act="go:home" aria-label="${esc(t("k_home"))}">${icon("ui-arrow-left")}</button><h2>${esc(title)}</h2></div>`;
function screen(): string {
  if (S.mode === "door") return bar(t("k_attend")) + atDoor(PH.att, look(), SPEAK, true);
  if (S.mode === "tickets") return bar(t("k_ticket")) + quKioskView(PH.q, quLook());
  if (S.mode === "answer") return bar(t("k_answer")) + svKioskView(PH.s, svLook());
  return home();
}
/** Touch or buttons only (DEVICE 48.17.14): a kiosk with physical buttons works with arrows, OK and Back alone. */
const DM = new DeviceMode(DEVICES, "self-order-kiosk");
const DEV = wireDevice(DM, { t, icon: (id) => icon(id), screen: () => document.getElementById("screen"), pad: () => document.getElementById("pad"), back: () => { act("go:home"); }, redraw: () => draw(), rtl: () => document.getElementById("screen")?.dir === "rtl" });
/** The device side of the Emulator Panel (ts/src/emkit.ts, build section 3A): the connect request, the disconnected and locked screens,
 *  practice mode, key tones and vibration, the hardware helper and the delivery menu. */
const KIT = new EmKit(EMULATOR_REGISTER, kitFor(EMULATOR_REGISTER, "queue.kiosk", "Entrance kiosk", { short_side: 1080, touch: true, camera: true, speaker: true, device_print: true, hardware: ["ticket_printer"] }, "android"), (type, payload, origin) => { LOG.emit(type, payload, origin); });
const KW = wireKit(KIT, { t, icon: (id, cls) => icon(id, cls), online: () => S.online, redraw: () => draw() });
function draw(): void { drawScreen(); KW.after($("#screen")); }
function drawScreen(): void {
  const el = $("#screen"); DEV.draw(el); el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W); el.innerHTML = screen();
  const m = PH.members[1];
  $("#hint").textContent = S.mode === "door" && m ? t("ppl_door_sample", { pin: m.pin, idcn: m.idcn }) : "";
  $("#cam").setAttribute("aria-label", t("k_camera")); $("#reader").setAttribute("aria-label", t("k_reader"));
  const paper = $("#paper"), tk = S.mode === "tickets" ? PH.q.tk(PH.q.kioskDone) : undefined;
  paper.hidden = !tk; paper.innerHTML = tk ? quPaper(PH.q, tk, { ...quLook(), paper: true }) : "";
}
function act(a: string): void {
  if (a.startsWith("at:")) PH.att.act(a, { online: S.online, partner: !S.realUser });
  else if (a.startsWith("qu:")) PH.q.act(a, { online: S.online, partner: !S.realUser, pairCode, redraw: draw });
  else if (a.startsWith("sv:")) PH.s.act(a, { online: S.online, partner: !S.realUser, redraw: draw });
  else if (a === "go:answer") { S.mode = "answer"; PH.s.restartKiosk(); }
  else if (a === "go:tickets") { S.mode = "tickets"; PH.q.kioskDone = null; PH.q.refused = ""; }
  else if (a === "go:door") { S.mode = "door"; PH.att.doorReset(); }
  else if (a === "go:home") { S.mode = "home"; PH.att.doorReset(); }
  draw();
}
function panel(): void {
  const box = (id: string, on: boolean, label: string): string => `<label><input type="checkbox" data-kctl="${id}" ${on ? "checked" : ""}> <span>${esc(label)}</span></label>`;
  $("#panel").innerHTML = panelHtml(["online", "country", "dark", "lang"], S, W, C) + `<div class="ctl-extra">${box("face", PH.att.readers.face, t("k_camera"))}${box("finger", PH.att.readers.finger, t("k_reader"))}</div>` + DEV.control();
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  const eric = PH.members.find((m) => m.set === "idcn"), aline = PH.members.find((m) => m.set === "finger_idcn");
  const typePin = (pin: string): void => { S.mode = "door"; PH.att.doorReset(); PH.att.doorDir("in"); for (const d of pin) PH.att.doorDigit(d); };
  stateButtons($("#stateButtons"), ["home", "door", "door-finger", "door-idcn", "door-done", "tickets", "ticket-taken", "answer", "answer-done"], (k) => {
    for (const m of PH.members) if (m.state === "in") m.state = "out";            // each state starts from an empty building
    PH.q.kioskDone = null;
    if (k === "home") S.mode = "home";
    else if (k === "tickets") S.mode = "tickets";
    else if (k === "ticket-taken") { S.mode = "tickets"; act("qu:kiosk:SRV"); return; }
    else if (k === "answer") { S.mode = "answer"; PH.s.restartKiosk(); }
    else if (k === "answer-done") { S.mode = "answer"; PH.s.restartKiosk(); act("sv:k:5"); act("sv:knext"); act("sv:k:ppl_sv_c_under5:c"); act("sv:knext"); act("sv:k:yes:c"); act("sv:knext"); return; }
    else if (k === "door") { S.mode = "door"; PH.att.doorReset(); }
    else if (k === "door-finger" && aline) { PH.att.readers.finger = true; typePin(aline.pin); }
    else if (eric) { typePin(eric.pin); if (k === "door-done") { for (const d of eric.idcn) PH.att.doorDigit(d); PH.att.pickChecker(aline?.name ?? ""); PH.att.doorIdcn(); } }
    draw();
  });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? "";
  panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (b && DEV.act(b.dataset["act"] ?? "")) return; if (b && !b.hasAttribute("disabled")) act(b.dataset["act"] ?? ""); });
  $("#screen").addEventListener("input", (e) => { const el = e.target as HTMLTextAreaElement; if ((el.dataset["in"] ?? "").startsWith("sv:")) PH.s.input(el.dataset["in"]!, el.value); });
  $("#screen").addEventListener("change", (e) => { const el = e.target as HTMLSelectElement; if (el.dataset["act"] === "ppl:checker") { PH.pickChecker(el.value); draw(); } });
  $("#cam").addEventListener("click", () => { if (PH.door.out?.means === "face") act(PH.att.readers.face ? "at:readerok" : "at:readerbroken"); });
  $("#reader").addEventListener("click", () => { if (PH.door.out?.means === "finger") act(PH.att.readers.finger ? "at:readerok" : "at:readerbroken"); });
  $("#panel").addEventListener("change", (e) => {
    const el = e.target as HTMLInputElement & HTMLSelectElement;
    if (el.dataset["kctl"] === "face" || el.dataset["kctl"] === "finger") { PH.att.readers[el.dataset["kctl"] as "face" | "finger"] = el.checked; draw(); return; }
    if (DEV.change(el)) return;
    if (panelChange(el, S, DATA)) panel(); draw();
  });
  document.addEventListener("keydown", (e) => {
    if (DEV.key(e)) return;
    if ((e.target as HTMLElement).closest("input,select,textarea")) return;
    if (S.mode !== "door") return;
    if (/^\d$/.test(e.key)) { act(`at:digit:${e.key}`); e.preventDefault(); }
    else if (e.key === "Backspace") { act("at:doorback"); e.preventDefault(); }
    else if (e.key === "Enter" && !(e.target as HTMLElement).closest("button")) { act(PH.door.step === "done" ? "at:doornext" : "at:idcn"); e.preventDefault(); }
  });
  window.setInterval(() => { S.ticks += 1; LOG.tick(S.online, false, S.ticks, () => undefined); }, 400);
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 420);
}
main();
