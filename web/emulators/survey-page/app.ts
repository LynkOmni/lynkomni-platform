/** LynkSurvey on a person's own phone (NEW UPDATE 4; build section 3B): the page behind a link, a QR code, WhatsApp, LynkChat or an
 *  email, with no app and no account. Who is asking, why and how long it takes; agreement before a sensitive question; the code
 *  for "one per phone"; one question a page ("Why?" only after an unhappy answer); thank you, My answers and "Don't ask me again".
 *  The box beside it shows what the organisation sees (never fewer than 5 answers, never who gave an anonymous one). */
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, panelChange, panelHtml, stateButtons } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";
import type { UserState } from "../../../ts/src/pos.js";
import { DeviceMode, wireDevice } from "../../../ts/src/devicemode.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";
import { SurveyDesk, svPhoneView, svScreenView, svTemplate } from "../../../ts/src/surveydesk.js";
import type { SvLook, SvPlan } from "../../../ts/src/surveydesk.js";
import type { AtTier } from "../../../ts/src/attenddesk.js";

declare const DATA: Build & { people: { survey: Record<AtTier, SvPlan> } };
const TIERS = ["free", "plus", "pro", "max"] as const;
const S: PanelState & { ticks: number } = { online: true, fail: false, type: "shop", tier: "plus", country: "", realUser: false, practice: false, dark: false, lang: "en", ticks: 0 };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <E extends HTMLElement>(sel: string): E => document.querySelector(sel) as E;
const icon = (id: string, cls = "ic"): string => `<span class="${cls}" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); });
const D = new SurveyDesk((type, payload, origin) => { LOG.emit(type, payload, origin); }, DATA.people.survey);
const clock = (ms: number): string => new Intl.DateTimeFormat(`${W.htmlLang()}-${C.pack().code}`, { timeZone: C.pack().tz, hour: "2-digit", minute: "2-digit" }).format(ms);
const look = (): SvLook => ({ t, icon, clock, money: (c) => C.money(c, "USD"), online: S.online, partner: !S.realUser, mayManage: false, place: t("sp_place"), powered: `<small class="pb">${esc(t("ppl_qu_powered", { brand: "LynkOmni" }))}</small>` });
const DM = new DeviceMode(DEVICES, "smartphone");
const DEV = wireDevice(DM, { t, icon: (id) => icon(id), screen: () => document.getElementById("screen"), pad: () => null, back: () => undefined, redraw: () => draw(), rtl: () => document.getElementById("screen")?.dir === "rtl" });

function draw(): void {
  const el = $("#screen"); DEV.draw(el); el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W);
  D.tier = S.tier as AtTier;
  el.innerHTML = `<p class="sp-addr" dir="ltr">shop.lynkomni.com/sample.place/survey</p><div class="sp-body">${svPhoneView(D, look())}${S.online ? "" : `<p class="sub" role="status">${esc(t("sp_offline"))}</p>`}</div>`;
  const tl = $("#till"); applyRoot(tl, W);
  const mine = D.answers.filter((a) => !a.sample && a.survey === D.cur).slice(-1)[0];
  tl.innerHTML = `<h3>${esc(t("sp_side"))}</h3>${mine ? `<p>${chip(mine.st)}</p>` : ""}${svScreenView(D, look())}<p class="sub">${esc(t("sp_side_note"))}</p>`;
}
function act(a: string): void {
  if (a.startsWith("sv:")) D.act(a, { online: S.online, partner: !S.realUser, redraw: draw });
  draw();
}
function reset(k: string): void {
  const s = D.sv(); if (!s) return;
  s.state = k === "closed" ? "closed" : "open"; s.rule = k === "one-per-phone" ? "one_per_phone" : "open"; s.anonymous = k === "anonymous";
  s.questions = k === "sensitive" ? [{ id: "visit", type: "rating", key: null, text: t("ppl_sv_sample_sensitive"), choices: [] }, ...svTemplate("satisfaction").slice(1)] : svTemplate("satisfaction");
  D.optedOut = false; D.phone = { ...D.phone, step: "consent", i: 0, answers: {}, code: "", consent: false, way: "smartphone", note: "" };
  if (k === "question") D.phone.step = "question";
  if (k === "done") D.phone.step = "done";
}
function panel(): void {
  $("#panel").innerHTML = panelHtml(["online", "plan", "country", "dark", "lang"], S, W, C, { tiers: TIERS });
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), ["consent", "question", "anonymous", "sensitive", "one-per-phone", "done", "closed"], (k) => { reset(k); draw(); });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? "";
  panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (b && DEV.act(b.dataset["act"] ?? "")) return; if (b && !b.hasAttribute("disabled")) act(b.dataset["act"] ?? ""); });
  document.addEventListener("input", (e) => { const el = e.target as HTMLInputElement; const k = el.dataset["in"] ?? ""; if (k.startsWith("sv:")) D.input(k, el.value); if (k === "sv:pcode") draw(); });
  $("#panel").addEventListener("change", (e) => {
    const el = e.target as HTMLInputElement & HTMLSelectElement;
    if (DEV.change(el)) return;
    const wasOffline = !S.online;
    if (panelChange(el, S, DATA, { tiers: TIERS })) panel();
    if (wasOffline && S.online) D.onlineAgain();
    draw();
  });
  window.setInterval(() => { S.ticks += 1; LOG.tick(S.online, false, S.ticks, () => undefined); }, 400);
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 380);
}
main();
