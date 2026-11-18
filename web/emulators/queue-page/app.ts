/** LynkQueue on a person's own phone (NEW UPDATE 4; build section 3B): the page behind the QR code at the door or the link, with
 *  no app and no account. See the wait before taking a ticket, join (the link, WhatsApp, LynkChat or a basic phone, as the place's
 *  plan and the country's partner allow), follow the place in the queue, Running late once, Leave queue, "Please come now", and the
 *  place's public queue page. The buttons beside it play reception and the counters. Never a name; the phone number is never shown. */
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, panelChange, panelHtml, stateButtons } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";
import type { UserState } from "../../../ts/src/pos.js";
import { DeviceMode, wireDevice } from "../../../ts/src/devicemode.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";
import { QueueDesk, pairCode, quDriver, quPhoneView, quPublicView } from "../../../ts/src/queuedesk.js";
import type { QuLook, QuPlan } from "../../../ts/src/queuedesk.js";
import type { AtTier } from "../../../ts/src/attenddesk.js";

declare const DATA: Build & { people: { queue: Record<AtTier, QuPlan> } };
const TIERS = ["free", "plus", "pro", "max"] as const;
type Tab = "ticket" | "public";
const S: PanelState & { ticks: number; tab: Tab } = { online: true, fail: false, type: "shop", tier: "plus", country: "", realUser: false, practice: false, dark: false, lang: "en", ticks: 0, tab: "ticket" };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <E extends HTMLElement>(sel: string): E => document.querySelector(sel) as E;
const icon = (id: string, cls = "ic"): string => `<span class="${cls}" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); });
const Q = new QueueDesk((type, payload, origin) => { LOG.emit(type, payload, origin); }, DATA.people.queue);
const clock = (ms: number): string => new Intl.DateTimeFormat(`${W.htmlLang()}-${C.pack().code}`, { timeZone: C.pack().tz, hour: "2-digit", minute: "2-digit" }).format(ms);
const look = (): QuLook => ({ t, icon, clock, money: (c) => C.money(c, "USD"), online: S.online, partner: !S.realUser, mayManage: false, place: t("qp_place"), powered: `<small class="pb">${esc(t("ppl_qu_powered", { brand: "LynkOmni" }))}</small>` });
const DM = new DeviceMode(DEVICES, "smartphone");
const DEV = wireDevice(DM, { t, icon: (id) => icon(id), screen: () => document.getElementById("screen"), pad: () => null, back: () => undefined, redraw: () => draw(), rtl: () => document.getElementById("screen")?.dir === "rtl" });

function draw(): void {
  const el = $("#screen"); DEV.draw(el); el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); applyRoot(el, W);
  Q.tier = S.tier as AtTier;
  const tabs = `<div class="qp-tabs" role="tablist">${(["ticket", "public"] as const).map((k) => `<button type="button" role="tab" aria-selected="${S.tab === k}" data-act="tab:${k}">${esc(t(`qp_tab_${k}`))}</button>`).join("")}</div>`;
  el.innerHTML = `<p class="qp-addr" dir="ltr">shop.lynkomni.com/sample.place/queue</p>${tabs}<div class="qp-body" role="tabpanel">${S.tab === "ticket" ? quPhoneView(Q, look()) : quPublicView(Q, look())}${S.online ? "" : `<p class="notice" role="status">${esc(t("qp_offline"))}</p>`}</div>${Q.plan.own_logo ? "" : look().powered}`;
  const tl = $("#till"); applyRoot(tl, W); tl.innerHTML = quDriver(Q, look());
}
function act(a: string): void {
  // The person's own buttons need the internet (the page talks to the cloud); the building's own devices do not.
  const mineOnly = /^qu:(join|late|leave|way|atplace|pnew)/.test(a);
  if (a.startsWith("qu:")) { if (!mineOnly || S.online || /^qu:(way|atplace|pnew)/.test(a)) Q.act(a, { online: S.online, partner: !S.realUser, pairCode, redraw: draw }); }
  else if (a === "tab:ticket" || a === "tab:public") S.tab = a.slice(4) as Tab;
  draw();
}
function panel(): void {
  $("#panel").innerHTML = panelHtml(["online", "plan", "country", "dark", "lang"], S, W, C, { tiers: TIERS })
    + `<div class="ctl-extra"><label><input type="checkbox" data-kctl="only" ${Q.joinFrom === "only_at_the_place" ? "checked" : ""}> <span>${esc(t("ppl_qu_join_only_at_the_place"))}</span></label>
      <label><input type="checkbox" data-kctl="public" ${Q.publicPage ? "checked" : ""}> <span>${esc(t("ppl_qu_public"))}</span></label></div>`;
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
  stateButtons($("#stateButtons"), ["see-the-wait", "my-ticket", "please-come", "my-turn", "missed", "public-page"], (k) => {
    for (const c of Q.counters) { if (c.serving) Q.finish(c.id, "served"); Q.counterState(c.id, "open"); }
    const old = Q.tk(Q.phone.ticket); if (old && old.state === "waiting") Q.leave(old.id);
    Q.phone.ticket = null; Q.phone.way = "smartphone"; Q.phone.note = ""; S.tab = k === "public-page" ? "public" : "ticket";
    const c1 = Q.counters[0];
    if (k !== "see-the-wait" && k !== "public-page" && c1) {
      while (Q.waiting("SRV").length < (k === "my-ticket" ? 7 : 2)) Q.issue("SRV", false, "reception");
      const me = Q.phoneJoin("SRV", true);
      if (me && (k === "my-turn" || k === "missed")) { while (Q.tk(c1.serving)?.id !== me.id) { if (c1.serving) Q.finish(c1.id, "served"); if (!Q.callNext(c1.id)) break; } }
      if (me && k === "missed") { Q.callAgain(c1.id); Q.callAgain(c1.id); Q.finish(c1.id, "missed"); }
    }
    draw();
  });
}
function main(): void {
  S.country = DATA.packOrder[0] ?? "";
  panel(); draw();
  document.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("[data-act]"); if (b && DEV.act(b.dataset["act"] ?? "")) return; if (b && !b.hasAttribute("disabled")) act(b.dataset["act"] ?? ""); });
  $("#panel").addEventListener("change", (e) => {
    const el = e.target as HTMLInputElement & HTMLSelectElement;
    if (el.dataset["kctl"] === "only") { Q.joinFrom = el.checked ? "only_at_the_place" : "anywhere"; draw(); return; }
    if (el.dataset["kctl"] === "public") { Q.publicPage = el.checked; draw(); return; }
    if (DEV.change(el)) return;
    if (panelChange(el, S, DATA, { tiers: TIERS })) panel(); draw();
  });
  window.setInterval(() => { S.ticks += 1; LOG.tick(S.online, false, S.ticks, () => undefined); }, 400);
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 380);
}
main();
