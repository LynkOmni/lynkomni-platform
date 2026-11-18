/** LynkDScreen: the main calling screen of LynkQueue (NEW UPDATE 4; build section 3B), on any TV with a browser, display board or
 *  monitor. It only follows the queue keeper: the tickets being called and their counters, "back soon", how many wait in each
 *  section and the QR code to join (changing every few minutes when people may join only at the place). A chime plays and a voice
 *  reads each call in up to two languages. The buttons beside it play reception and the counters. Ticket numbers only, never a name. */
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, panelChange, panelHtml, reducedMotion, stateButtons } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";
import type { UserState } from "../../../ts/src/pos.js";
import type { T } from "../../../ts/src/shell.js";
import { DeviceMode, wireDevice } from "../../../ts/src/devicemode.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";
import { QueueDesk, pairCode, pairCodeAt, quDriver, quScreenView, quVoice } from "../../../ts/src/queuedesk.js";
import type { QuLook, QuPlan } from "../../../ts/src/queuedesk.js";
import type { AtTier } from "../../../ts/src/attenddesk.js";

declare const DATA: Build & { people: { queue: Record<AtTier, QuPlan> } };
const TIERS = ["free", "plus", "pro", "max"] as const;
const S: PanelState & { ticks: number; sound: boolean; said: string; second: string } = { online: true, fail: false, type: "shop", tier: "plus", country: "", realUser: false, practice: false, dark: true, lang: "en", ticks: 0, sound: false, said: "", second: "" };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <E extends HTMLElement>(sel: string): E => document.querySelector(sel) as E;
const icon = (id: string, cls = "ic"): string => `<span class="${cls}" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); });
const Q = new QueueDesk((type, payload, origin) => { LOG.emit(type, payload, origin); }, DATA.people.queue);
const clock = (ms: number): string => new Intl.DateTimeFormat(`${W.htmlLang()}-${C.pack().code}`, { timeZone: C.pack().tz, hour: "2-digit", minute: "2-digit" }).format(ms);
const look = (): QuLook => ({ t, icon, clock, money: (c) => C.money(c, "USD"), online: S.online, partner: !S.realUser, mayManage: false, place: t("ds_place"), powered: `<small class="pb">${esc(t("ppl_qu_powered", { brand: "LynkOmni" }))}</small>` });
/** The voice reads in the place's languages (only the words change; the number is read character by character in every one). */
const speakIn = (lang: string): T => (k, vars = {}) => (W.isTest() ? t(k, vars) : (DATA.i18n[lang]?.texts[k] ?? DATA.i18n["en"]?.texts[k] ?? k).replace(/\{(\w+)\}/g, (m, v: string) => (v in vars ? String(vars[v]) : m)));
const DM = new DeviceMode(DEVICES, "queue-display");
const DEV = wireDevice(DM, { t, icon: (id) => icon(id), screen: () => document.getElementById("screen"), pad: () => document.getElementById("pad"), back: () => undefined, redraw: () => draw(), rtl: () => document.getElementById("screen")?.dir === "rtl" });

/** The chime and the voice through the screen's own speaker: two soft notes, then the call read aloud. Off until switched on, and silent where the browser has no sound. */
function chime(text: string, lang: string): void {
  if (!S.sound) return;
  try {
    const AC = (window as unknown as { AudioContext?: typeof AudioContext }).AudioContext; if (!AC) return;
    const ac = new AC(), now = ac.currentTime;
    for (const [i, f] of [660, 880].entries()) { const o = ac.createOscillator(), g = ac.createGain(); o.frequency.value = f; g.gain.setValueAtTime(0.0001, now + i * 0.22); g.gain.exponentialRampToValueAtTime(0.2, now + i * 0.22 + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.22 + 0.2); o.connect(g).connect(ac.destination); o.start(now + i * 0.22); o.stop(now + i * 0.22 + 0.21); }
    if ("speechSynthesis" in window) { const u = new SpeechSynthesisUtterance(text); u.lang = lang; window.speechSynthesis.speak(u); }
  } catch { /* no sound on this device: the screen still shows and says the call in words */ }
}
function draw(): void {
  const el = $("#screen"); DEV.draw(el); el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W);
  Q.tier = S.tier as AtTier; Q.voice = S.second && S.second !== S.lang ? [S.lang, S.second] : [S.lang];
  const top = Q.tickets.filter((x) => x.state === "called").sort((a, b) => (b.calledAt ?? 0) - (a.calledAt ?? 0))[0];
  el.innerHTML = quScreenView(Q, look(), speakIn, pairCodeAt(Math.floor(Date.now() / 180_000)))
    + `<div class="ds-keys"><button type="button" class="ghost" data-act="ds:again" ${top ? "" : "disabled"}>${esc(t("ds_say_again"))}</button><button type="button" class="ghost" data-act="ds:sound" aria-pressed="${S.sound}">${esc(t("ds_sound"))}: ${esc(t(S.sound ? "ppl_on" : "ppl_off"))}</button></div>`;
  const key = top ? `${top.id}:${top.calls}` : "";
  if (top && key !== S.said) chime(quVoice(Q, top, t), W.htmlLang());
  S.said = key;
  const tl = $("#till"); applyRoot(tl, W); tl.innerHTML = quDriver(Q, look());
}
function act(a: string): void {
  if (a.startsWith("qu:")) Q.act(a, { online: S.online, partner: !S.realUser, pairCode, redraw: draw });
  else if (a === "ds:sound") S.sound = !S.sound;
  else if (a === "ds:again") S.said = "";
  draw();
}
function panel(): void {
  const langs = Object.keys(DATA.i18n);
  $("#panel").innerHTML = panelHtml(["online", "plan", "country", "dark", "lang"], S, W, C, { tiers: TIERS })
    + `<div class="ctl-extra"><label class="center"><span>${esc(t("ds_second_language"))}</span> <select data-kctl="second"><option value="">–</option>${langs.map((l) => `<option value="${esc(l)}" ${S.second === l ? "selected" : ""}>${esc(DATA.i18n[l]?.native ?? l)}</option>`).join("")}</select></label>
      <label><input type="checkbox" data-kctl="only" ${Q.joinFrom === "only_at_the_place" ? "checked" : ""}> <span>${esc(t("ppl_qu_join_only_at_the_place"))}</span></label></div>` + DEV.control();
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), ["waiting", "called", "two-called", "back-soon"], (k) => {
    for (const c of Q.counters) { if (c.serving) Q.finish(c.id, "served"); Q.counterState(c.id, "open"); }
    while (Q.waiting().length < 4) Q.issue("SRV", false, "reception");
    const [c1, c2] = Q.counters;
    if (c1 && k !== "waiting") Q.callNext(c1.id);
    if (c2 && k === "two-called") Q.callNext(c2.id);
    if (c2 && k === "back-soon") Q.counterState(c2.id, "paused");
    draw();
  });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? "";
  panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (b && DEV.act(b.dataset["act"] ?? "")) return; if (b && !b.hasAttribute("disabled")) act(b.dataset["act"] ?? ""); });
  $("#panel").addEventListener("change", (e) => {
    const el = e.target as HTMLInputElement & HTMLSelectElement;
    if (el.dataset["kctl"] === "second") { S.second = el.value; draw(); return; }
    if (el.dataset["kctl"] === "only") { Q.joinFrom = el.checked ? "only_at_the_place" : "anywhere"; draw(); return; }
    if (DEV.change(el)) return;
    if (panelChange(el, S, DATA, { tiers: TIERS })) panel(); draw();
  });
  document.addEventListener("keydown", (e) => { if (DEV.key(e)) return; });
  window.setInterval(() => { S.ticks += 1; LOG.tick(S.online, false, S.ticks, () => undefined); if (!reducedMotion() && S.ticks % 15 === 0 && document.querySelector("#screen .flash")) draw(); }, 400);
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 724);
}
main();
