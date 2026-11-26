/** LynkBet betting counter (BETTING UPDATE, owner 2026-11-24, master blueprint section 86): a countertop LynkPOS with a ticket
 *  printer, a ticket scanner and a cash drawer, for shops of licensed betting operators. Every rule comes from ts/src/betting.ts
 *  (catalog/betting.v1.json): the operator's system takes the bet, sets the odds, decides every result and amount, and answers
 *  each request; the counter only asks. Online a bet is sent at once; offline it is a queued slip only where the operator allows it
 *  (refused slips are refunded in full); payouts, referrals and cancelling are online only. Two sides: the counter (workspace,
 *  /sell/betting) and the shop's Storefront betting page it manages (/external/betting). No country, currency or operator is
 *  written here: amounts are whole minor units of the chosen country's currency and the operators are sandbox samples. */
import type { UserState } from "../../../ts/src/pos.js";
import { noticeHtml, type Notice as Msg } from "../../../ts/src/errorbox.js";
import { Country, EventLog, Words, applyRoot, esc, fitToWidth, newId, panelChange, panelHtml, stateButtons } from "../../../ts/src/emulator.js";
import type { Build, PanelState } from "../../../ts/src/emulator.js";
import { designedState, panelShell, sampleAccount } from "../../../ts/src/deviceshell.js";
import type { Entry } from "../../../ts/src/shell.js";
import { DeviceMode, wireDevice } from "../../../ts/src/devicemode.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";
import { StaffLock, deviceBanners, knowledgeFor, raiseLocal, staffPicker, staffWhoRow, lockWhoButton } from "../../../ts/src/devicekit.js";
import { pinPad } from "../../../ts/src/signin.js";
import type { Line as Notice } from "../../../ts/src/notify.js";
import { EmKit, kitFor, wireKit } from "../../../ts/src/emkit.js";
import { EMULATOR_REGISTER } from "../../../ts/src/emulators.generated.js";
import { watchNames } from "../../../ts/src/names.js";
import { BETTING } from "../../../ts/src/betting.generated.js";
import { betAdultAge, betCancelCheck, betCheckAnswer, betCommission, betExpectedCash, betFlags, betMayHandOverCash, betOddsText, betOfflineSlip,
  betPossibleWin, betReferNext, betSlipResult, betStakeCheck, betTotalOdds, betTwoPersonNeeded } from "../../../ts/src/betting.js";
import type { BetCheckAnswer, BetOddsFormat, BetTicket } from "../../../ts/src/betting.js";

declare const DATA: Build;
type View = "lock" | "approve" | "home" | "games" | "slip" | "check" | "answer" | "refer" | "refs" | "shift" | "safer" | "storefront";
type Pick = "home" | "draw" | "away";
interface Sel { game: number; pick: Pick; odds: number }
interface Placed { code: string; stake: number; odds: number[]; sels: Sel[]; win: number; state: UserState; result: "pending" | "won" | "lost"; paid: boolean; expires: number; at: number; method: string; operator: number }
interface Referral { code: string; amount: number; way: string; step: string }
let LINES: Notice[] = [];
/** MASTER UPDATE section 3, as on every LynkPOS device: each person signs in with their own PIN, so every bet and payout is tied to a
 *  person (samples; a real device keeps only a slow salted hash). 8642 is the cashier's sample duress PIN: the quiet limited view opens
 *  (taking bets for cash only) and the alert leaves silently by the first path out. Wrong PINs make the person wait, then lock that PIN;
 *  nothing is ever deleted. A manager or the owner, never the person serving, approves big payouts and cancelling with their own PIN. */
const STAFF = new StaffLock([
  { person: "c1", name: "Aline", role: "cashier", pin: "1234", duress: "8642" },
  { person: "m1", name: "Eric", role: "manager", pin: "2580" },
  { person: "o1", name: "Grace", role: "owner", pin: "4719" },
]);
const IDLE_LOCK_MS = 120_000;
interface Approval { purpose: "second" | "cancel"; person: string | null; back: View }
const S: PanelState & { view: View; sels: Sel[]; stakeUnits: number; method: "cash" | "mobile_money"; age: boolean; bet: Placed | null; operator: number; fmt: BetOddsFormat;
  ticket: (BetTicket & { code: string }) | null; answer: BetCheckAnswer | null; lock: UserState | null; handed: boolean; second: boolean; photos: { ticket: boolean; id: boolean }; way: string;
  placed: Placed[]; refs: Referral[]; disputes: string[]; stakes: number[]; payouts: number[]; scans: Record<string, number>; drawerOpen: boolean; ticks: number;
  offlineSlips: boolean; cancelManager: boolean; cancelled: string | null; sfOn: boolean; note: string | null;
  who: string; picking: boolean; pin: string; limited: boolean; idle: boolean; lastInput: number; pictures: boolean; keySound: boolean; approval: Approval | null; approvedBy: string } = {
  online: true, fail: false, type: "agent_point", tier: "plus", country: "", realUser: false, practice: false, dark: false, lang: "en",
  view: "lock", sels: [], stakeUnits: 2, method: "cash", age: false, bet: null, operator: 1, fmt: "decimal", ticket: null, answer: null, lock: null, handed: false, second: false,
  photos: { ticket: false, id: false }, way: "mobile_money", placed: [], refs: [], disputes: [], stakes: [], payouts: [], scans: {}, drawerOpen: false, ticks: 0,
  offlineSlips: true, cancelManager: false, cancelled: null, sfOn: false, note: null,
  who: "c1", picking: false, pin: "", limited: false, idle: false, lastInput: Date.now(), pictures: false, keySound: true, approval: null, approvedBy: "" };
const W = new Words(DATA.i18n, () => S.lang); const t = W.t;
const C = new Country(DATA, () => S.country, () => S.lang);
const $ = <E extends HTMLElement>(sel: string): E => document.querySelector(sel) as E;
const icon = (id: string, cls = "ic"): string => `<span class="${cls}" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const chip = (s: UserState): string => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
const LOG = new EventLog(() => { const el = document.getElementById("log"); if (el) el.innerHTML = LOG.html(esc, chip, t("no_events")); });

/** One whole unit of the shop's currency in minor units (2 decimals for most, none for some): sample amounts follow the currency. */
/** The operator's answer on a scanned ticket (section 4C point 2): a win is good news, a refusal says what to do, a flag is never an accusation. */
function btAnswer(a: string, text: string): Msg {
  return a === "pay" ? { level: "success", text } : a === "not_valid" ? { level: "error", text, how: t("fd_check_retry") }
    : a === "refer" || a === "short_of_cash" || a === "already_paid" ? { level: "warning", text } : { level: "info", text };
}
function unit(): number {
  try { return 10 ** (new Intl.NumberFormat("en", { style: "currency", currency: C.pack().currency }).resolvedOptions().maximumFractionDigits ?? 2); } catch { return 100; }
}
const money = (minor: number): string => C.money(minor);
/** The sandbox operators' answers (labelled Sample): limits per shop, games and odds. A real operator sends its own. */
const OP = { minStake: () => unit(), maxStake: () => 500 * unit(), shopMax: () => 200 * unit(), opening: () => 300 * unit(), expiryDays: 60, commissionBps: 500,
  secondFrom: () => 100 * unit(), slipCap: () => 50 * unit(), shopSlipCap: () => 200 * unit(), leadMinutes: 30, cancelMinutes: 10 };
const GAMES = [1, 2, 3, 4, 5].map((n) => ({ n, live: n === 2, startsIn: n === 2 ? 0 : 20 + 40 * n, odds: { home: 1700 + 90 * n, draw: 3100 + 40 * n, away: 2050 + 130 * n } as Record<Pick, number> }));
const STAKES = [1, 2, 5, 10, 20, 50];
const FORMATS = BETTING.odds_formats as readonly BetOddsFormat[];
const odds = (o: number): string => betOddsText(o, S.fmt);
const today = (): number => Math.floor(Date.now() / 86_400_000);
const signed = (): boolean => !S.realUser;                                // a country where no licensed operator is signed shows Coming to your country soon.
const drawer = (): number => betExpectedCash(OP.opening(), S.stakes, S.payouts);
const age = (): number => betAdultAge(null);
const operatorName = (n = S.operator): string => t("bt_sample_operator", { n });
let serial = 0;
const betSampleCode = (): string => { serial += 1; return `SAMPLE${String(48_210_000 + serial).padStart(8, "0")}`; };

// ---- the shell parts on this device: search, help, account, connection chip, first-run card, the screen's address ----
const DSH = panelShell({
  st: S, t, icon: (id) => icon(id), clock: (ms) => C.clock(ms),
  native: () => (DATA.i18n[S.lang]?.native ?? S.lang), region: () => (C.pack().sample ? t("sample_country") : C.pack().name), currency: () => C.pack().currency,
  pending: () => LOG.pending().count, lastSync: () => LOG.events.find((e) => e.sync === "accepted")?.at ?? null,
  screen: () => (S.view === "storefront" ? { id: "betting_storefront", title: shellTitle(), path: "/external/betting" } : { id: "betting", title: shellTitle(), path: "/sell/betting" }),
  entries: (): Entry[] => [{ id: "bet", kind: "action", title: t("bt_place"), act: "go:games" }, { id: "check", kind: "action", title: t("bt_check"), act: "go:check" },
    { id: "refs", kind: "action", title: t("bt_refs"), act: "go:refs" }, { id: "shift", kind: "action", title: t("bt_shift"), act: "go:shift" }, { id: "safer", kind: "action", title: t("bt_safer"), act: "go:safer" },
    { id: "storefront", kind: "action", title: t("bt_storefront"), act: "go:storefront" }],
  account: () => sampleAccount(t, STAFF.find(S.who)?.role ?? "cashier", ["cashier", "manager", "owner"], t("bt_shop"), S.dark ? "dark" : "light", DATA.i18n[S.lang]?.native ?? S.lang, C.pack().sample ? t("sample_country") : C.pack().name),
  run: (a) => { if (a.startsWith("ntf:")) { const nid = a.split(":")[2]; LINES.forEach((l) => { if (l.nid === nid || a === "ntf:allread") { l.read = true; l.acknowledged = true; } }); return; } act(a); },
  redraw: () => draw(), firstRun: true,
  lines: () => LINES, knowledge: () => knowledgeFor(DATA.i18n, S.lang), crumbLabel: (p) => t(p === "/" ? "bt_shop" : p === "/sell" ? "sell" : p === "/external" ? "bt_storefront" : "bt_title"),
});
const shellTitle = (): string => document.querySelector("#screen h1, #screen h2")?.textContent?.trim() || t("bt_title");
const bar = (title: string, back: View = "home"): string => `<div class="bbar"><button type="button" class="bback" data-act="go:${back}" aria-label="${esc(t("back"))}">${icon("ui-arrow-left")}</button><h2>${esc(title)}</h2></div>`;
const rows = (r: [string, string][]): string => `<ul class="brows">${r.map(([a, b]) => `<li><span>${esc(a)}</span><span>${esc(b)}</span></li>`).join("")}</ul>`;
const toggle = (act_: string, on: boolean, label: string): string => `<button type="button" class="bcheck" data-act="${act_}" aria-pressed="${on}"><span class="box">${on ? icon("ui-check") : ""}</span><span>${esc(label)}</span></button>`;
const choices = (label: string, items: readonly string[], cur: string, act_: string, word: (x: string) => string): string =>
  `<div class="bchips" role="group" aria-label="${esc(label)}">${items.map((x) => `<button type="button" class="bchoice" data-act="${act_}:${x}" aria-pressed="${x === cur}">${esc(word(x))}</button>`).join("")}</div>`;
/** Offline, a bet is only a queued slip, and only where the operator allows it. */
const canTakeBets = (): boolean => signed() && (S.online || S.offlineSlips);

/** Who is serving, with Lock the counter (also from the Back key on the lock screen's way out). */
function whoRow(): string {
  const me = STAFF.find(S.who);
  return staffWhoRow(me?.name ?? "", me?.role ?? "cashier", t, (id) => icon(id));   // the same row with Lock on every staff device
}
function home(): string {
  if (S.limited) return `<div class="btiles"><button type="button" class="btile" data-act="go:games"${canTakeBets() ? "" : " disabled"}>${icon("lit-tickets")}<strong>${esc(t("bt_place"))}</strong></button></div><p class="sub">${esc(t("bt_never_credit"))}</p>`;
  const tile = (go: View, ic: string, label: string, off: boolean): string => `<button type="button" class="btile" data-act="go:${go}"${off ? ` disabled data-why="${esc(t("bt_needs_net"))}"` : ""}>${icon(ic)}<strong>${esc(t(label))}</strong></button>`;
  return `<div class="bop"><span>${esc(t("bt_operator", { name: operatorName() }))}</span><span>${esc(t("cash_in_drawer"))} <strong>${esc(money(drawer()))}</strong></span></div>
    ${choices(t("bt_operator_pick"), ["1", "2"], String(S.operator), "op", (x) => operatorName(Number(x)))}
    ${S.online ? "" : noticeHtml(t, S.offlineSlips ? { level: "warning", text: t("bt_offline_mode") } : { level: "error", text: t("bt_needs_net"), how: t("fd_go_online") })}
    <div class="btiles" data-wait-area data-shape="tiles">${tile("games", "lit-tickets", "bt_place", !canTakeBets())}${tile("check", "ui-qr", "bt_check", false)}${tile("refs", "ui-doc", "bt_refs", false)}${tile("shift", "ui-float", "bt_shift", false)}${tile("safer", "ui-info", "bt_safer", false)}${tile("storefront", "ui-globe", "bt_storefront", false)}</div>
    <p class="sub">${esc(t("bt_never_credit"))}</p>`;
}
function games(): string {
  const picked = (g: number, p: Pick): boolean => S.sels.some((s) => s.game === g && s.pick === p);
  return bar(t("bt_games")) + `<h3>${esc(t("bt_format"))}</h3>${choices(t("bt_format"), FORMATS, S.fmt, "fmt", (x) => t(`bt_fmt_${x}`))}
    <button type="button" class="ghost" data-act="booking">${icon("ui-qr")} ${esc(t("bt_booking_code"))}</button>${S.note ? `<p class="bnote">${esc(S.note)}</p>` : ""}
    <ul class="bgames">${GAMES.map((g) => `<li class="bgame"><h3>${esc(t("bt_game", { n: g.n }))}${g.live ? ` <span class="chip st-sent">${esc(t("bt_live"))}</span>` : ""}</h3><div class="bodds" role="group" aria-label="${esc(t("bt_game", { n: g.n }))}">${(["home", "draw", "away"] as Pick[]).map((p) =>
    `<button type="button" class="bodd" data-act="pick:${g.n}:${p}" aria-pressed="${picked(g.n, p)}"><small>${esc(t(`bt_${p}`))}</small><b dir="ltr">${odds(g.odds[p])}</b></button>`).join("")}</div></li>`).join("")}</ul>
    <div class="bactions"><button type="button" class="primary" data-act="go:slip"${S.sels.length ? "" : ` disabled data-why="${esc(t("bt_slip_empty"))}"`}>${esc(t("bt_slip"))} (${S.sels.length})</button></div>`;
}
/** Why a slip may not be taken now: online the usual checks; offline the operator's offline rules. */
function slipBlock(stake: number): string | null {
  if (!signed()) return "bt_coming";
  if (!S.age) return "bt_age_needed";
  if (betStakeCheck(stake, OP.minStake(), OP.maxStake()) !== "ok") return "bt_stake";
  if (S.online) return null;
  const queued = S.placed.filter((p) => p.state === "queued").reduce((a, p) => a + p.stake, 0);
  const worst = S.sels.reduce<string>((acc, s) => { if (acc !== "ok") return acc; const g = GAMES.find((x) => x.n === s.game); return betOfflineSlip(S.offlineSlips, g?.live ? "live" : "sports", g?.startsIn ?? 0, OP.leadMinutes, stake, OP.slipCap(), queued, OP.shopSlipCap()); }, "ok");
  return worst === "ok" ? null : `bt_slip_${worst}`;
}
function placedView(b: Placed): string {
  const canCancel = betCancelCheck(S.online, true, false, S.cancelManager, Math.floor((Date.now() - b.at) / 60000), OP.cancelMinutes);
  const head = b.state === "failed" ? `<p class="bbad">${esc(t(b.method === "queued_refund" ? "bt_slip_refused" : "bt_failed", { amount: money(b.stake) }))}</p>`
    : b.state === "queued" ? `<p>${chip("queued")} <strong>${esc(t("bt_queued_slip"))}</strong></p><p class="sub">${esc(t("bt_queued_note"))}</p>`
    : b.state === "confirmed" ? `<p class="bgood">${esc(t("bt_confirmed"))}</p>` : `<p>${chip("sent")} ${esc(t("bt_waiting"))}</p>`;
  const body = b.state === "confirmed" || b.state === "queued" ? `${b.state === "confirmed" ? `<p class="bbig" dir="ltr">${esc(b.code)}</p>` : ""}${rows([[t("bt_stake"), money(b.stake)], [t("bt_possible"), money(b.win)]])}
      <p class="bnote">${esc(t(b.method === "cash" ? "bt_take" : "bt_take_momo", { amount: money(b.stake) }))}</p>` : "";
  const why = canCancel === "offline" ? "bt_payout_offline" : canCancel === "manager_needed" ? "bt_cancel_manager" : "bt_cancel_no";
  const cancel = b.state === "confirmed" && S.cancelled !== b.code ? `${S.cancelManager ? `<p class="bgood">${icon("ui-check")} ${esc(t("bt_approved_by", { name: S.approvedBy }))}</p>` : `<button type="button" class="ghost" data-act="approve:cancel"${S.online ? "" : " disabled"}>${icon("ui-lock")} ${esc(t("bt_cancel_manager"))}</button>`}
      <button type="button" class="ghost" data-act="cancel" data-wait${canCancel === "ok" ? "" : ` disabled data-why="${esc(t(why))}"`}>${esc(t("bt_cancel"))}</button>
      <button type="button" class="ghost" data-act="reprint">${esc(t("bt_reprint"))}</button>` : S.cancelled === b.code ? noticeHtml(t, { level: "info", text: t("bt_cancelled", { amount: money(b.stake) }) }) : "";
  return bar(t("bt_slip")) + head + body + cancel + `<div class="bactions"><button type="button" class="primary" data-act="newbet"${b.state === "sent" ? " disabled" : ""}>${esc(t("bt_new"))}</button></div>`;
}
function slip(): string {
  if (S.bet) return placedView(S.bet);
  if (!S.sels.length) return bar(t("bt_slip"), "games") + `<p class="sub">${esc(t("bt_slip_empty"))}</p>`;
  const stake = S.stakeUnits * unit(), list = S.sels.map((s) => s.odds);
  const why = slipBlock(stake);
  return bar(t("bt_slip"), "games") + `<ul class="brows">${S.sels.map((s) => `<li><span>${esc(t("bt_game", { n: s.game }))}: ${esc(t(`bt_${s.pick}`))}</span><span dir="ltr">${odds(s.odds)}</span></li>`).join("")}</ul>
    ${rows([[t("bt_total_odds"), odds(betTotalOdds(list))]])}
    <h3>${esc(t("bt_stake"))}</h3>${choices(t("bt_stake"), STAKES.map(String), String(S.stakeUnits), "stake", (u) => money(Number(u) * unit()))}
    <h3>${esc(t("bt_paid_by"))}</h3>${choices(t("bt_paid_by"), ["cash", "mobile_money"], S.method, "method", (m) => t(m))}
    ${rows([[t("bt_possible"), money(betPossibleWin(stake, list))]])}
    ${toggle("age", S.age, t("bt_age", { age: age() }))}
    ${why ? noticeHtml(t, { level: S.online ? "info" : "warning", text: t(why) }) : S.online ? "" : `<p class="bnote">${esc(t("bt_queued_note"))}</p>`}
    <div class="bactions"><button type="button" class="primary" data-act="send" data-wait${why ? ` disabled data-why="${esc(t(why))}"` : ""}>${esc(t(S.online ? "bt_send" : "bt_queue"))}</button></div>`;
}
function checkView(): string {
  return bar(t("bt_check")) + `<p>${esc(t("bt_scan_hint"))}</p>${S.online ? "" : noticeHtml(t, { level: "error", text: t("bt_payout_offline"), how: t("fd_go_online") })}<div class="bactions"><button type="button" class="primary" data-act="scan">${icon("ui-qr")} ${esc(t("scan"))}</button></div>`;
}
function answerView(): string {
  const tk = S.ticket, a = S.answer;
  if (!tk || !a) return checkView();
  const amt = money(tk.payable ?? 0), head = `<p class="sub" dir="ltr">${esc(tk.code)}</p>`;
  if (a === "pay") {
    const needSecond = betTwoPersonNeeded(tk.payable ?? 0, OP.secondFrom());
    const lockLine = S.lock ? `<p>${chip(S.lock)} ${esc(t(S.lock === "confirmed" ? "bt_locked" : S.lock === "failed" ? "bt_lock_failed" : "bt_waiting"))}</p>` : "";
    const ready = S.online && (!needSecond || S.second) && S.lock !== "sent";
    const btn = S.handed ? `<p class="bgood">${esc(t("bt_paid"))}</p><div class="bactions"><button type="button" class="primary" data-act="go:check">${esc(t("bt_next_ticket"))}</button></div>`
      : betMayHandOverCash(S.lock ?? "") ? `<div class="bactions"><button type="button" class="primary" data-act="handover">${esc(t("bt_hand", { amount: amt }))}</button></div>`
      : `${needSecond ? `<p class="sub">${esc(t("bt_second_needed", { amount: money(OP.secondFrom()) }))}</p>${S.second ? `<p class="bgood">${icon("ui-check")} ${esc(t("bt_approved_by", { name: S.approvedBy }))}</p>` : `<button type="button" class="ghost" data-act="approve:second"${S.online ? "" : " disabled"}>${icon("ui-lock")} ${esc(t("bt_second"))}</button>`}` : ""}
        ${S.online ? "" : noticeHtml(t, { level: "error", text: t("bt_payout_offline"), how: t("fd_go_online") })}
        <div class="bactions"><button type="button" class="primary" data-act="lock" data-wait${ready ? "" : ` disabled data-why="${esc(t(S.online ? "bt_second" : "bt_payout_offline"))}"`}>${esc(t("bt_lock"))}</button></div>`;
    return bar(t("bt_check"), "check") + head + `<p class="bgood">${esc(t("bt_a_pay", { amount: amt }))}</p><p class="bbig">${esc(amt)}</p><p class="sub">${esc(t("bt_locked_note"))}</p>${lockLine}${btn}`;
  }
  if (a === "refer" || a === "short_of_cash")
    return bar(t("bt_check"), "check") + head + `${noticeHtml(t, btAnswer(a, t(`bt_a_${a}`, { amount: amt })))}<p class="sub">${esc(t("bt_keep"))}</p>
      <div class="bactions"><button type="button" class="primary" data-act="go:refer"${S.online ? "" : ` disabled data-why="${esc(t("bt_payout_offline"))}"`}>${esc(t("bt_refer"))}</button></div>`;
  const dispute = a === "lost" ? (S.disputes.includes(tk.code) ? `<p class="bnote">${esc(t("bt_dispute_sent"))}</p>` : `<button type="button" class="ghost" data-act="dispute">${esc(t("bt_dispute"))}</button>`) : "";
  return bar(t("bt_check"), "check") + head + `<p class="bbad">${esc(t(`bt_a_${a}`))}</p><p class="sub">${esc(t("bt_keep"))}</p>${dispute}
    <div class="bactions"><button type="button" class="ghost" data-act="go:check">${esc(t("bt_next_ticket"))}</button></div>`;
}
function referView(): string {
  const tk = S.ticket; if (!tk) return checkView();
  const ready = S.photos.ticket && S.photos.id && S.online;
  return bar(t("bt_refer"), "answer") + `<p class="bbig">${esc(money(tk.payable ?? 0))}</p>${toggle("photo:ticket", S.photos.ticket, t("bt_photo_ticket"))}${toggle("photo:id", S.photos.id, t("bt_photo_id"))}<p class="sub">${esc(t("bt_photos_note"))}</p>
    <h3>${esc(t("bt_way"))}</h3>${choices(t("bt_way"), BETTING.payout_ways, S.way, "way", (w) => t(`bt_way_${w}`))}
    <div class="bactions"><button type="button" class="primary" data-act="refer" data-wait${ready ? "" : ` disabled data-why="${esc(t(S.online ? "bt_photos_first" : "bt_payout_offline"))}"`}>${esc(t("bt_refer_send"))}</button></div>`;
}
function refsView(): string {
  if (!S.refs.length) return bar(t("bt_refs")) + designedState("empty", t, DATA.statePictures, S.dark, { label: t("bt_check"), act: "go:check" }) + `<p class="sub">${esc(t("bt_no_refs"))}</p>`;
  const steps = BETTING.refer_steps as readonly string[];
  return bar(t("bt_refs")) + S.refs.map((r) => `<div class="bref"><p dir="ltr"><strong>${esc(r.code)}</strong></p><p>${esc(money(r.amount))} · ${esc(t(`bt_way_${r.way}`))}</p>
    <ul class="bsteps">${steps.map((s, i) => { const at = steps.indexOf(r.step); return `<li><span>${esc(t(`bt_step_${s}`))}</span>${i < at ? chip("confirmed") : i === at ? chip(s === "paid" ? "confirmed" : "sent") : ""}</li>`; }).join("")}</ul>
    ${r.step === "paid" && r.way === "cash_at_shop" ? `<p class="bnote">${esc(t("bt_collect"))}</p>` : ""}</div>`).join("");
}
function shiftView(): string {
  const stakes = S.stakes.reduce((a, b) => a + b, 0), paid = S.payouts.reduce((a, b) => a + b, 0);
  const fl = betFlags(S.scans, S.payouts, OP.shopMax());
  return bar(t("bt_shift")) + rows([[t("bt_opening"), money(OP.opening())], [t("bt_stakes"), money(stakes)], [t("bt_payouts"), money(paid)], [t("expected_cash"), money(drawer())],
    [t("commission"), money(betCommission(stakes, OP.commissionBps))]]) + `<p class="sub">${esc(t("bt_commission_note"))}</p>
    <h3>${esc(t("bt_checks"))}</h3>${fl.length ? fl.map((f) => noticeHtml(t, { level: "warning", text: f.startsWith("repeat_scans:") ? t("bt_flag_repeat", { code: f.split(":")[1] ?? "", n: S.scans[f.split(":")[1] ?? ""] ?? 0 }) : t("bt_flag_big") })).join("") + `<p class="sub">${esc(t("bt_flag_note"))}</p>` : `<p class="sub">${esc(t("bt_no_flags"))}</p>`}`;
}
function saferView(): string {
  return bar(t("bt_safer")) + `<p>${esc(t("bt_safer_age", { age: age() }))}</p><p>${esc(t("bt_safer_limits"))}</p><p>${esc(t("bt_safer_exclude"))}</p><p>${esc(t("bt_never_credit"))}</p>
    <p class="bnote">${esc(t("bt_safer_help"))} ${esc(t("bt_help_line"))}</p>`;
}
/** The Storefront side (/external/betting): what the shop's public betting page shows, only where the law allows. */
function storefrontView(): string {
  const items = ["bt_sf_details", "bt_sf_operators", "bt_sf_check", "bt_sf_booking", "bt_sf_help"];
  return bar(t("bt_storefront")) + `<p class="sub">${esc(t("bt_sf_note"))}</p>${toggle("sf", S.sfOn, t("bt_sf_show"))}
    <ul class="brows">${items.map((k) => `<li><span>${esc(t(k))}</span><span>${S.sfOn ? chip("confirmed") : ""}</span></li>`).join("")}</ul>`;
}
/** The lock screen: who is using the counter, then their own PIN on the shared pad (pictures, a tone per key, waits and lock). */
function lockView(): string {
  if (S.picking) return `<div class="block">${staffPicker(STAFF.staff, t, (id) => icon(id))}</div>`;
  const me = STAFF.find(S.who), waitLeft = Math.max(0, Math.ceil(((STAFF.waitUntil.get(S.who) ?? 0) - Date.now()) / 1000));
  return `<div class="block"><p class="who">${lockWhoButton(me?.name ?? "", me?.role ?? "cashier", t, (id) => icon(id))}</p>
    ${S.idle ? `<p class="sub" role="status">${esc(t("locked_idle"))}</p>` : ""}
    ${STAFF.hard.has(S.who) ? noticeHtml(t, { level: "error", text: t("dk_hard_locked"), how: t("fd_ask_manager") }) : ""}
    ${pad(me?.name ?? "", STAFF.wrong.get(S.who) ?? 0, waitLeft, S.who)}<p class="sub">${esc(t("dk_own_pin"))}</p><p class="hint">${esc(t("bt_pin_hint"))}</p>${me?.duress ? `<p class="hint">${esc(t("dk_duress_sample", { pin: me.duress }))}</p>` : ""}</div>`;
}
const pad = (name: string, wrong: number, waitLeft: number, person: string): string =>
  pinPad({ entered: S.pin.length, length: STAFF.lengthOf(person), wrong, waitLeft, pictures: S.pictures, sound: S.keySound, title: t("dk_pin_for", { name }) }, t, (id) => icon(id));
/** A manager or the owner, never the person serving, approves with their own PIN on this counter. */
function approveView(): string {
  const ap = S.approval; if (!ap) return home();
  const title = t(ap.purpose === "second" ? "bt_second" : "bt_cancel_manager");
  if (!ap.person) {
    const who = STAFF.staff.filter((x) => (x.role === "manager" || x.role === "owner") && x.person !== S.who);
    return bar(title, ap.back) + `<p class="sub">${esc(t("bt_approver"))}</p>${staffPicker(who, t, (id) => icon(id))}`;
  }
  const m = STAFF.find(ap.person), waitLeft = Math.max(0, Math.ceil(((STAFF.waitUntil.get(ap.person) ?? 0) - Date.now()) / 1000));
  return bar(title, ap.back) + pad(m?.name ?? "", STAFF.wrong.get(ap.person) ?? 0, waitLeft, ap.person) + (STAFF.hard.has(ap.person) ? noticeHtml(t, { level: "error", text: t("dk_hard_locked"), how: t("fd_ask_manager") }) : "");
}
function screen(): string {
  const head = `<header class="bhead"><h1>${esc(t("bt_title"))}</h1>${DSH.bar()}</header>${DSH.crumbs(true)}${deviceBanners(LINES, t, (id) => icon(id))}`;
  if (S.view === "lock") return `<header class="bhead"><h1>${esc(t("bt_title"))}</h1></header>${lockView()}`;
  if (S.view === "approve") return head + approveView();
  const who = whoRow();   // every screen opened with a staff PIN shows who is serving, with Lock (owner, 2026-11-25)
  if (!signed() && S.view !== "safer") return head + who + designedState("coming_soon", t, DATA.statePictures, S.dark, { label: t("bt_safer"), act: "go:safer" }) + `<p class="sub">${esc(t("bt_coming"))}</p>`;
  const v = S.view;
  const body = v === "games" ? games() : v === "slip" ? slip() : v === "check" ? checkView() : v === "answer" ? answerView() : v === "refer" ? referView() : v === "refs" ? refsView()
    : v === "shift" ? shiftView() : v === "safer" ? saferView() : v === "storefront" ? storefrontView() : home();
  return head + who + body;
}

// ---- the printer: the operator's ticket, a queued slip, a copy and the payout slip ----
function print(lines: string[], withQr: string | null): void {
  const wrap = $("#paperWrap"), p = $("#paper");
  p.innerHTML = `<div class="rhead">${DATA.brand.receipt}</div><pre>${esc(lines.join("\n"))}</pre>${withQr ? `${icon("ui-qr", "qr")}<strong dir="ltr">${esc(withQr)}</strong>` : ""}`;
  wrap.hidden = false;
}
function ticketPaper(b: Placed, copy = false): void {
  print([b.state === "queued" ? t("bt_queued_slip") : t("bt_paper_head"), ...(copy ? [t("bt_copy")] : []), operatorName(b.operator), "",
    ...b.sels.map((s) => `${t("bt_game", { n: s.game })}: ${t(`bt_${s.pick}`)}  ${odds(s.odds)}`), "",
    `${t("bt_total_odds")}: ${odds(betTotalOdds(b.odds))}`, `${t("bt_stake")}: ${money(b.stake)}`, `${t("bt_possible")}: ${money(b.win)}`,
    t("bt_paper_expires", { date: C.date(b.expires * 86_400_000) }), "", t("bt_safer_help"), t("bt_help_line")], b.state === "queued" || copy ? null : b.code);
}

// ---- the operators' answers (sandbox): the device only asks; the cloud alone writes the answer ----
function answerBet(b: Placed, id: string): void {
  const ok = !S.fail && S.online;
  if (b.state === "queued") {                                                     // a queued slip: a ticket, or the whole stake back
    const r = betSlipResult(ok, b.stake);
    if (r.ticket) { b.state = "confirmed"; LOG.emit("BetConfirmed", { request_id: id, ticket_ref: b.code, possible_win: b.win }, "server"); if (S.bet === b) ticketPaper(b); }
    else {
      b.state = "failed"; const cash = b.method === "cash"; b.method = "queued_refund";
      if (cash && S.stakes.includes(b.stake)) S.stakes.splice(S.stakes.indexOf(b.stake), 1);
      LOG.emit("BetFailed", { request_id: id, reason: "odds_changed", refund_due: true }, "server");
      LINES = raiseLocal(LINES, "sync_retried", t("bt_slip_refused", { amount: money(r.refund) }), Date.now());
    }
    draw(); return;
  }
  if (!ok) { b.state = "failed"; LOG.emit("BetFailed", { request_id: id, reason: S.online ? "partner_declined" : "timeout", refund_due: false }, "server"); draw(); return; }
  b.state = "confirmed"; S.placed.unshift(b); if (b.method === "cash") { S.stakes.push(b.stake); S.drawerOpen = true; }
  LOG.emit("BetConfirmed", { request_id: id, ticket_ref: b.code, possible_win: b.win }, "server");
  ticketPaper(b); draw();
}
const pendingSlips: { b: Placed; id: string }[] = [];
function send(): void {
  const stake = S.stakeUnits * unit(), list = S.sels.map((s) => s.odds);
  if (slipBlock(stake)) return;
  const b: Placed = { code: betSampleCode(), stake, odds: list, sels: [...S.sels], win: betPossibleWin(stake, list), state: S.online ? "sent" : "queued", result: "pending", paid: false,
    expires: today() + OP.expiryDays, at: Date.now(), method: S.method, operator: S.operator };
  S.bet = b; const id = newId();
  LOG.emit("BetRequested", { request_id: id, operator_id: newId(), kind: "sports", selections: list.length, stake, currency: C.pack().currency, method: S.method, queued_offline: !S.online }, "device", S.online ? "sent" : "queued");
  if (!S.online) { S.placed.unshift(b); if (S.method === "cash") { S.stakes.push(stake); S.drawerOpen = true; } pendingSlips.push({ b, id }); ticketPaper(b); draw(); return; }
  draw(); setTimeout(() => { answerBet(b, id); }, 900);
}
/** A scan reads the ticket's code; the operator answers what it knows (sample tickets come from the panel's state buttons). Offline the
 *  counter shows the last known state and never pays. */
function scanned(tk: (BetTicket & { code: string }) | null): void {
  const beam = document.getElementById("beam"); beam?.classList.add("on"); setTimeout(() => beam?.classList.remove("on"), 400);
  if (!signed()) { S.view = "home"; draw(); return; }
  const last = S.placed.find((p) => p.state === "confirmed");
  const ticket = tk ?? (last ? { code: last.code, known: true, result: last.result, paid: last.paid, payable: last.result === "won" ? last.win : 0, expires: last.expires } : null);
  if (!ticket) { S.view = "check"; draw(); return; }
  S.scans[ticket.code] = (S.scans[ticket.code] ?? 0) + 1;
  S.ticket = ticket; S.answer = betCheckAnswer(ticket, today(), OP.shopMax(), drawer()); S.lock = null; S.handed = false; S.second = false; S.approvedBy = ""; S.photos = { ticket: false, id: false }; S.view = "answer";
  LOG.emit("BetTicketChecked", { ticket_ref: ticket.code, answer: S.answer }, "device", S.online ? "sent" : "queued");
  draw();
}
function lock(): void {
  const tk = S.ticket; if (!tk || S.answer !== "pay" || !S.online) return;
  if (betTwoPersonNeeded(tk.payable ?? 0, OP.secondFrom()) && !S.second) return;
  S.lock = "sent"; LOG.emit("BetPayoutLockAsked", { ticket_ref: tk.code, operator_id: newId() }, "device", "sent"); draw();
  setTimeout(() => {
    S.lock = S.fail || !S.online ? "failed" : "confirmed";
    if (S.lock === "confirmed") { tk.paid = true; const p = S.placed.find((x) => x.code === tk.code); if (p) p.paid = true; LOG.emit("BetPayoutLocked", { ticket_ref: tk.code, payable: tk.payable }, "server"); }
    else LOG.emit("BetPayoutLockFailed", { ticket_ref: tk.code, reason: "timeout" }, "server");
    draw();
  }, 800);
}
function handover(): void {
  const tk = S.ticket; if (!tk || !betMayHandOverCash(S.lock ?? "")) return;
  S.payouts.push(tk.payable ?? 0); S.handed = true; S.drawerOpen = true;
  LOG.emit("BetPaidOut", { ticket_ref: tk.code, paid: tk.payable, from: "shop_cash" }, "device", "sent");
  print([t("bt_paper_payout"), operatorName(), "", `${t("bt_ticket", { code: tk.code })}`, `${t("amount")}: ${money(tk.payable ?? 0)}`, C.clock(Date.now())], null);
  if (drawer() < OP.opening() / 5) LINES = raiseLocal(LINES, "sync_retried", t("bt_low_cash"), Date.now());
  draw();
}
function refer(): void {
  const tk = S.ticket; if (!tk || !S.photos.ticket || !S.photos.id || !S.online) return;
  S.refs.unshift({ code: tk.code, amount: tk.payable ?? 0, way: S.way, step: "referred" }); S.view = "refs";
  LOG.emit("BetReferred", { referral_id: newId(), ticket_ref: tk.code, operator_id: newId(), way: S.way, evidence_ref: "EVD-SAMPLE-1" }, "device", "sent");
  draw();
}
function cancelBet(): void {
  const b = S.bet; if (!b || b.state !== "confirmed") return;
  if (betCancelCheck(S.online, true, false, S.cancelManager, Math.floor((Date.now() - b.at) / 60000), OP.cancelMinutes) !== "ok") return;
  LOG.emit("BetCancelAsked", { ticket_ref: b.code, manager_approved: true }, "device", "sent");
  setTimeout(() => { S.cancelled = b.code; if (b.method === "cash" && S.stakes.includes(b.stake)) S.stakes.splice(S.stakes.indexOf(b.stake), 1); LOG.emit("BetCancelled", { ticket_ref: b.code, refund: b.stake }, "server"); draw(); }, 700);
}

/** Touch or buttons only (DEVICE 48.17.14): a counter without touch works with its arrows, OK and Back. */
const DM = new DeviceMode(DEVICES, "smart-terminal");
const DEV = wireDevice(DM, { t, icon: (id) => icon(id), screen: () => document.getElementById("screen"), pad: () => document.getElementById("pad"), back: () => { act("go:home"); }, redraw: () => draw(), rtl: () => document.getElementById("screen")?.dir === "rtl" });
/** The device side of the Emulator Panel (ts/src/emkit.ts): connect request, disconnected and locked screens, practice mode, key tones and vibration. */
const KIT = new EmKit(EMULATOR_REGISTER, kitFor(EMULATOR_REGISTER, "bet.counter", "Betting counter", { short_side: 420, touch: true, speaker: true }, "android"), (type, payload, origin) => { LOG.emit(type, payload, origin); });
const KW = wireKit(KIT, { t, icon: (id) => icon(id), online: () => S.online, redraw: () => draw() });
function draw(): void { drawScreen(); KW.after($("#screen")); }
function drawScreen(): void {
  const el = $("#screen"); DEV.draw(el); el.classList.toggle("dark", S.dark); el.classList.toggle("light", !S.dark); el.classList.toggle("lowlit", DSH.pictures);
  applyRoot(el, W); el.innerHTML = screen() + DSH.overlay();
  $("#drawer").classList.toggle("open", S.drawerOpen);
  const ad = document.getElementById("address"); if (ad) ad.textContent = DSH.address();
}
const SAMPLES: Record<string, () => BetTicket & { code: string }> = {
  win: () => ({ code: betSampleCode(), known: true, result: "won", payable: 35 * unit(), expires: today() + 30 }),
  win_second: () => ({ code: betSampleCode(), known: true, result: "won", payable: 150 * unit(), expires: today() + 30 }),
  big_win: () => ({ code: betSampleCode(), known: true, result: "won", payable: 1_250 * unit(), expires: today() + 30 }),
  paid: () => ({ code: betSampleCode(), known: true, result: "won", paid: true, payable: 40 * unit(), expires: today() + 30 }),
  pending: () => ({ code: betSampleCode(), known: true, result: "pending", expires: today() + 30 }),
  lost: () => ({ code: betSampleCode(), known: true, result: "lost", expires: today() + 30 }),
  expired: () => ({ code: betSampleCode(), known: true, result: "won", payable: 20 * unit(), expires: today() - 1 }),
  unknown: () => ({ code: betSampleCode(), known: false }),
};
function panel(): void {
  $("#panel").innerHTML = panelHtml(["online", "fail", "country", "real", "dark", "lang"], S, W, C, { help: t("bt_try") }) + DEV.control();
  $("#panel").querySelector("h3")?.insertAdjacentHTML("afterend", `<label><input type="checkbox" data-ctl="slips" ${S.offlineSlips ? "checked" : ""}> <span>${esc(t("bt_offline_slips"))}</span></label>`);
  stateButtons($("#stateButtons"), ["lock_screen", "pick_staff", "approve_second", "duress", "home", "games", "slip", "confirmed", "offline_slip", ...Object.keys(SAMPLES), "refer", "referrals", "shift", "safer", "storefront", "games_end_win", "games_end_lost"], (k) => {
    if (k === "lock_screen" || k === "pick_staff" || k === "duress") { lockCounter(false); if (k === "pick_staff") S.picking = true; panel(); draw(); return; }   // duress: type the sample duress PIN shown on the lock
    if (S.view === "lock" || S.limited) { if (S.limited) lockCounter(false); THEN = () => jump(k); S.picking = false; panel(); draw(); return; }   // never out of the quiet duress view either   // a panel jump never skips the PIN (owner, 2026-11-26)
    if (S.view === "approve") { S.view = "home"; S.approval = null; S.pin = ""; }
    jump(k);
  });
  $("#log").innerHTML = LOG.html(esc, chip, t("no_events"));
}
/** The screen a panel button chose, once someone is signed in. */
let THEN: (() => void) | null = null;
function jump(k: string): void {
    S.lastInput = Date.now();
    if (k === "approve_second") { S.online = true; scanned(SAMPLES["win_second"]!()); act("approve:second"); panel(); return; }
    if (k in SAMPLES) { S.online = true; scanned(SAMPLES[k]!()); panel(); return; }
    if (k === "games" || k === "home" || k === "shift" || k === "safer" || k === "storefront") S.view = k;
    if (k === "slip" || k === "confirmed" || k === "offline_slip") {
      if (!S.sels.length) S.sels = [{ game: 1, pick: "home", odds: GAMES[0]!.odds.home }, { game: 3, pick: "away", odds: GAMES[2]!.odds.away }];
      S.view = "slip"; S.bet = null; if (k === "offline_slip") { S.online = false; S.offlineSlips = true; }
      if (k !== "slip") { S.age = true; send(); }
    }
    if (k === "refer") { scanned(SAMPLES["big_win"]!()); S.photos = { ticket: true, id: true }; S.view = "refer"; }
    if (k === "referrals") { if (!S.refs.length) { scanned(SAMPLES["big_win"]!()); S.photos = { ticket: true, id: true }; refer(); } S.view = "refs"; }
    if (k === "games_end_win" || k === "games_end_lost") { const b = S.placed.find((p) => p.state === "confirmed"); if (b) b.result = k === "games_end_win" ? "won" : "lost"; S.view = "check"; }
    panel(); draw();
}
/** Sign in, lock, change person and the manager's approval: the only acts on the lock screen and the approval pad. */
function signInAct(k: string, x: string, y: string): boolean {
  const onPad = S.view === "lock" || (S.view === "approve" && !!S.approval?.person);
  if (k === "staff" && x === "change" && S.view === "lock") { S.picking = true; S.pin = ""; draw(); return true; }
  if (k === "staff" && x === "pick") {
    if (S.view === "approve" && S.approval) S.approval.person = y; else { S.who = y; S.picking = false; }
    S.pin = ""; draw(); return true;
  }
  if (k !== "pin" || !onPad) return S.view === "lock";
  if (x === "pictures") { S.pictures = !S.pictures; draw(); return true; }
  if (x === "sound") { S.keySound = !S.keySound; draw(); return true; }
  if (x === "clear") { S.pin = S.pin.slice(0, -1); draw(); return true; }
  const full = STAFF.lengthOf(S.view === "lock" ? S.who : S.approval?.person ?? S.who);   // this person's PIN length: never a digit more
  if (/^\d$/.test(x)) { if (S.pin.length < full) S.pin += x; if (S.pin.length < full) { draw(); return true; } }   // full: checked at once
  else if (x !== "ok" || !S.pin) return true;
  const pin = S.pin; S.pin = "";
  if (S.view === "lock") {
    const r = STAFF.signIn(S.who, pin, Date.now());
    if (r.ok) {
      S.limited = r.view === "limited"; S.idle = false; S.view = "home"; S.lastInput = Date.now();
      const go = THEN; THEN = null; if (go && !S.limited) { go(); return true; }   // the screen chosen in the panel, never past a duress PIN
      if (S.limited) { S.method = "cash"; const n = STAFF.pathsOut(S.online ? ["internet"] : []); for (let i = 0; i < n; i++) LOG.emit("DuressSignalled", { device_id: "bet-counter", person: S.who, path: "internet", at: Date.now() }, "server", "accepted"); }
    } else if (r.reason === "hard_locked") { LOG.emit("DeviceHardLocked", { device: "bet-counter" }); LINES = raiseLocal(LINES, "device_hard_locked", t("dk_hard_locked"), Date.now()); }
    draw(); return true;
  }
  const ap = S.approval; if (!ap?.person) return true;
  const m = STAFF.find(ap.person), r = STAFF.signIn(ap.person, pin, Date.now());
  if (r.ok && r.view === "full" && m && (m.role === "manager" || m.role === "owner") && m.person !== S.who) {
    S.approvedBy = m.name; if (ap.purpose === "second") S.second = true; else S.cancelManager = true;
    S.view = ap.back; S.approval = null;
  }
  draw(); return true;
}
function lockCounter(idle: boolean): void {
  S.view = "lock"; S.pin = ""; S.picking = false; S.limited = false; S.idle = idle; THEN = null; S.approval = null; S.second = false; S.cancelManager = false; S.drawerOpen = false;
  draw();
}
function act(a: string): void {
  const [k = "", x = "", y = ""] = a.split(":");
  S.lastInput = Date.now();
  if (signInAct(k, x, y)) return;
  if (k === "lockcounter" || a === "gate:lock") { lockCounter(false); return; }
  if (k === "approve") { if ((x === "second" || x === "cancel") && S.online) { S.approval = { purpose: x, person: null, back: S.view === "approve" ? "home" : S.view }; S.pin = ""; S.view = "approve"; draw(); } return; }
  if (S.limited && k === "go" && x !== "games" && x !== "slip" && x !== "home") return;           // the quiet duress view only takes bets for cash
  if (S.limited && k === "method") return;
  if (k === "go") { S.approval = null; S.view = (["home", "games", "slip", "check", "answer", "refer", "refs", "shift", "safer", "storefront"] as View[]).includes(x as View) ? (x as View) : "home"; if (S.view === "slip" && S.bet?.state !== "sent") S.bet = null; S.note = null; draw(); return; }
  if (k === "pick") { const g = GAMES.find((q) => q.n === Number(x)), p = y as Pick; if (!g) return; const had = S.sels.find((s) => s.game === g.n); S.sels = S.sels.filter((s) => s.game !== g.n); if (!had || had.pick !== p) S.sels.push({ game: g.n, pick: p, odds: g.odds[p] }); S.sels.sort((m, n) => m.game - n.game); draw(); return; }
  if (k === "booking") { S.sels = [{ game: 4, pick: "home", odds: GAMES[3]!.odds.home }, { game: 5, pick: "draw", odds: GAMES[4]!.odds.draw }]; S.note = t("bt_booking_loaded", { code: "B7K2Q9" }); draw(); return; }
  if (k === "fmt") { if ((FORMATS as readonly string[]).includes(x)) S.fmt = x as BetOddsFormat; draw(); return; }
  if (k === "op") { S.operator = x === "2" ? 2 : 1; draw(); return; }
  if (k === "stake") { S.stakeUnits = Number(x) || 1; draw(); return; }
  if (k === "method") { S.method = x === "mobile_money" ? "mobile_money" : "cash"; draw(); return; }
  if (k === "age") { S.age = !S.age; draw(); return; }
  if (k === "send") { send(); return; }
  if (k === "newbet") { S.bet = null; S.sels = []; S.age = false; S.drawerOpen = false; S.cancelManager = false; S.approvedBy = ""; S.view = "games"; draw(); return; }
  if (k === "cancel") { cancelBet(); return; }
  if (k === "reprint") { if (S.bet) ticketPaper(S.bet, true); return; }
  if (k === "scan") { scanned(null); return; }
  if (k === "lock") { lock(); return; }
  if (k === "handover") { handover(); return; }
  if (k === "dispute") { const tk = S.ticket; if (tk) { S.disputes.push(tk.code); LOG.emit("BetDisputeOpened", { dispute_id: newId(), ticket_ref: tk.code }, "device", S.online ? "sent" : "queued"); } draw(); return; }
  if (k === "photo") { if (x === "ticket" || x === "id") S.photos[x] = !S.photos[x]; draw(); return; }
  if (k === "way") { if ((BETTING.payout_ways as readonly string[]).includes(x)) S.way = x; draw(); return; }
  if (k === "refer") { refer(); return; }
  if (k === "sf") { S.sfOn = !S.sfOn; draw(); return; }
}
function main(): void {
  S.country = DATA.packOrder[0] ?? "";
  panel(); draw();
  document.addEventListener("click", (e) => {
    const target = e.target as HTMLElement;
    if (target.closest("#tear")) { $("#paperWrap").hidden = true; S.drawerOpen = false; draw(); return; }
    const b = target.closest<HTMLElement>("[data-act]"); if (!b) return;
    if (b.classList.contains("dsh-scrim") && target.closest("[data-stop]")) return;
    if (DEV.act(b.dataset["act"] ?? "")) return;
    if (DSH.act(b.dataset["act"] ?? "")) return;
    act(b.dataset["act"] ?? "");
  });
  document.addEventListener("input", (e) => { DSH.input(e.target as HTMLInputElement); });
  document.addEventListener("keydown", (e) => {
    S.lastInput = Date.now();
    const onPad = (S.view === "lock" && !S.picking) || (S.view === "approve" && !!S.approval?.person);
    if (onPad && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const k = /^\d$/.test(e.key) ? e.key : e.key === "Backspace" ? "clear" : e.key === "Enter" && S.pin ? "ok" : "";
      if (k) { e.preventDefault(); act(`pin:${k}`); return; }
    }
    if (DSH.key(e)) return; DEV.key(e);
  });
  (window as unknown as { __settle: () => void }).__settle = () => { DSH.settle(); draw(); };
  $("#panel").addEventListener("change", (e) => {
    const el = e.target as HTMLInputElement;
    if (el.dataset["ctl"] === "slips") { S.offlineSlips = el.checked; draw(); return; }
    if (DEV.change(el)) return;
    if (panelChange(el, S, DATA)) panel();
    draw();
  });
  window.setInterval(() => {
    S.ticks += 1;
    let changed = LOG.tick(S.online, false, S.ticks, () => undefined);
    // back online: queued slips go to the operator, which accepts them or returns the stake
    if (S.online && pendingSlips.length) { for (const q of pendingSlips.splice(0)) answerBet(q.b, q.id); changed = true; }
    // the operator works through each referral (sandbox): checking, approved, paid; only its answers move a step
    if (S.ticks % 5 === 0) for (const r of S.refs) { const n = betReferNext(r.step); if (n && S.online && !S.fail) { r.step = n; changed = true; LOG.emit("BetReferralAnswered", { referral_id: r.code, step: n }, "server"); } }
    if (S.view !== "lock" && S.lock !== "sent" && Date.now() - S.lastInput > IDLE_LOCK_MS) { lockCounter(true); return; }   // two minutes without use
    if ((S.view === "lock" || S.view === "approve") && S.ticks % 3 === 0 && [...STAFF.waitUntil.values()].some((u) => u > Date.now() - 1500)) changed = true;
    if (changed) draw();
  }, 400);
  fitToWidth($("#rig"), Number($("#rig").dataset["width"]) || 460);
}
main();
/** Every Lynk name on this page carries its plain word (catalog/names.v1.json, ts/src/names.ts). */
watchNames(document.body, () => t);
