/* LynkOmni Account (account.lynkomni.com) in a browser window and on a phone (build section 2). Every part of the frame comes
 * from ts/src/shell.ts and every rule from ts/src/account.ts; this file holds the sample person, the screens and the event log.
 * Words come from web/shell/strings.en.json (the shell) and strings.en.json (this site) and their language packs. */
import { STATE_PICTURE, Undo, accountMenu, viewSheet, IFACE_NAME, commandBar, connectionChip, esc, filterRegions, globeSheet, regionName, header, helpPanel, launcher, maskId, navigation, search, state, comingSoon, syncSheet, translator, undoToast, usernameField } from "../../../ts/src/shell.js";
import type { AddressMap, Entry, Icon, Link, NavItem, Pic, StateKind, SyncInfo, T, UsernameStatus, Viewport } from "../../../ts/src/shell.js";
import { DAY, PAGES, RECOVERY, REGISTRATION_STEPS, SECURITY_EVENT_KEY, SIGN_UP_STEPS, applicationStatus, canSubmit, closesAt, consentState, dataRequestDue, nextSignUpStep, pagePath, payoutChange, recoveryPath, recoveryReady, recoveryReadyAt, signInAlertNeeded } from "../../../ts/src/account.js";
import type { ApplicationStatus, Consent, Page, RecoveryPath, RegistrationStep, SignUpState } from "../../../ts/src/account.js";
import type { UserState } from "../../../ts/src/pos.js";
import { brandMark, markFor } from "../../../ts/src/brand.js";
import { buildFooter, mainFooterHtml } from "../../../ts/src/footer.js";
import type { BrandPlaces } from "../../../ts/src/brand.js";
import { Tracking } from "../../../ts/src/tracking.js";
import type { View as TrackView } from "../../../ts/src/tracking.js";
import { REGISTER } from "../../../ts/src/tracking.generated.js";
import { trackerHtml } from "../../../ts/src/trackview.js";
import { browserFacts, chooseInterface } from "../../../ts/src/interfaces.js";
import type { Choice } from "../../../ts/src/interfaces.js";
import { DEVICES } from "../../../ts/src/interfaces.generated.js";
import { arrowNav, gestures } from "../../../ts/src/gestures.js";
import { bell, messagesList, whySheet } from "../../../ts/src/notify.js";
import type { Line, Sent } from "../../../ts/src/notify.js";
import { MESSAGES } from "../../../ts/src/parts.generated.js";
import { askBox, buildPack, confirmCard, decide, lookup, receipt } from "../../../ts/src/assist.js";
import { idcn } from "../../../ts/src/attendance.js";
import { ticketCard } from "../../../ts/src/peopleparts.js";
import { breadcrumbBar, trail } from "../../../ts/src/breadcrumbs.js";
import { TERMS_IN_FORCE, cardPlanName, contactWaitSeconds, coolOffSeconds, mayNow } from "../../../ts/src/protection.js";
const HEADER_ROOM = { computer: 160, tablet: 160, phone: 160 } as const;   // px the shell header gives its brand place at each size; web-header shows the logo from 96 px (brand/surfaces.v1.json), so every size has room for it

interface CountryPack { code: string; name: string; currency: string; tz: string; locale: string; sample: boolean; card_networks: string[]; wallets: string[]; providers: string[]; ready: Record<string, { ok: boolean; message: string }>; services: { service: string; id?: string; name: string; icon: string; plain: string; href?: string; state: "available" | "coming_soon" }[] }
interface BuildData {
  icons: Record<string, string>;
  brand: { body: string; receipt: string; places: BrandPlaces };
  pictures: { offLight: string; offDark: string; offAlt: string };
  statePictures: Record<string, Record<"light" | "dark", { svg: string; alt: string; contrast?: string }>>;
  packs: Record<string, CountryPack>; packOrder: string[];
  addresses: AddressMap;
  storefront: { tiers: string[]; prices_usd: Record<string, number>; share_bps: Record<string, number>; min_age: number };
  i18n: Record<string, { native: string; dir: "ltr" | "rtl"; texts: Record<string, string> }>;
}
declare const DATA: BuildData;
interface Ev { n: number; type: string; origin: "device" | "server"; payload: unknown; sync: UserState; at: number }

const PACKS = DATA.i18n;
const EN: Record<string, string> = PACKS.en?.texts ?? {};
const TEST_LANGS = ["xx", "xx-rtl"];
type Overlay = null | "launcher" | "account" | "globe" | "cmd" | "help" | "bell" | "why" | "sync" | "stepup" | "pages" | "view";
/** The views a browser can show the account site in (DEVICE, 48.17); the size follows the chosen view. */
const VIEWS = ["universal", "phone.touch", "tablet.touch", "computer.touch", "computer.pointer"] as const;
const SIZE_OF_CLASS: Record<string, Viewport> = { phone: "phone", watch: "phone", voice: "phone", tablet: "tablet", eink: "tablet", computer: "computer", tv: "computer" };
const TEST_VIEW: Record<string, string> = { computer: "computer.pointer", tablet: "tablet.touch", phone: "phone.touch" };
type Screen = "signin" | "signup" | "recover" | Page;
const SCREENS: Screen[] = ["signin", "signup", "recover", ...PAGES];
/** Sample credential ids in the one public id format (core/ids.py: valid check digits; tests/test_emulators.py checks every id written here). */
const SAMPLE_CRD = ["LOCRD-0001-0002-0015", "LOCRD-0001-0002-0023", "LOCRD-0001-0002-0031", "LOCRD-0001-0002-0049", "LOCRD-0001-0002-0056", "LOCRD-0001-0002-0064", "LOCRD-0001-0002-0072", "LOCRD-0001-0002-0080"];
const LYNKID = "LOID-4821-9035-7715";           // the sample person: illustrative, never an allocated identifier
const SHOP_OID = "LOOID-7351-2064-8911";
const T_NOW = (): number => Math.floor(Date.now() / 1000);

interface Standing { losub: string; merchant: string; cap: number; active: boolean }
const S = {
  size: "computer" as Viewport, lang: "en", theme: "light" as "light" | "dark", mode: "" as "" | "lite" | "sunlight", link: "good" as Link, country: "", realUser: false,
  screen: "overview" as Screen, overlay: null as Overlay, query: "", pending: 0, lastSync: null as number | null, events: [] as Ev[], undo: new Undo(), seen: new Set<string>(), notified: new Set<string>(),
  signUp: {} as SignUpState, username: "", cloud: null as UsernameStatus, recoveryCode: "7F3K-9Q2M-X81B-4TZC",
  recover: { otherDevice: null as boolean | null, hasCode: null as boolean | null, started: null as { path: RecoveryPath; startedAt: number; approvals: number; cancelled?: boolean } | null },
  passkeys: [{ locrd: SAMPLE_CRD[0] as string, device: "device_phone", at: T_NOW() - 40 * DAY, here: true }, { locrd: SAMPLE_CRD[1] as string, device: "device_laptop", at: T_NOW() - 12 * DAY, here: false }],
  sessions: [{ tail: "a1f3", site: "account", device: "device_phone", place: "sample_city", at: T_NOW() - 600 }, { tail: "9c0e", site: "merchant", device: "device_laptop", place: "sample_city", at: T_NOW() - 3 * 3600 }],
  seenDevices: [{ device: "device_phone", place: "sample_city" }, { device: "device_laptop", place: "sample_city" }],
  secEvents: [{ type: "SessionStarted", at: T_NOW() - 600 }, { type: "PasskeyEnrolled", at: T_NOW() - 12 * DAY }, { type: "ConsentGranted", at: T_NOW() - 20 * DAY }] as { type: string; at: number }[],
  consents: [{ scope: "accountant", grantee: "LOID-1100-2200-3302", purpose: "monthly books", expires: T_NOW() + 5 * DAY }] as Consent[],
  stepup: null as null | { ok: boolean; then: string },
  payout: null as null | { status: "applied" | "waiting"; readyAt: number },
  dataRequest: null as null | { due: number }, closing: null as null | number, marketing: { email: false, push: true },
  standing: [{ losub: "LOSUB-5100-0200-0030", merchant: "Blue Taxi", cap: 300000, active: true }] as Standing[],
  app: null as null | { status: ApplicationStatus; steps: Record<RegistrationStep, boolean>; lynkoid?: string },
  restrictedUntil: 0,
  workspaces: [] as { entity: "person" | "company" | "organisation" }[],
  testSize: "auto", override: null as string | null, choice: null as Choice | null,
  idCheck: null as null | "sent" | "confirmed", cases: [] as { side: "internal" | "external"; ref: string }[],
  // Arrive Safe and Collect Pass (NEW UPDATE 1): shares end by themselves; a trip plan is watched by the cloud
  shares: [] as { id: string; scope: "live" | "trips" | "zones"; until: number }[], plan: null as null | { due: number; checked: boolean }, passWindow: 0,
  // NEW UPDATE 4 section 2: My details (LynkAttend), My tickets (LynkQueue), My answers and the Panel (LynkSurvey)
  att: "closed" as "closed" | "code_sent" | "open", attShow: "" as "" | "pin" | "idcn", attRequest: null as null | { kind: "delete_my_details" | "dispute"; at: number }, wasThisYou: true,
  tkLate: false, tkLeft: false, answers: ["sv1", "sv2"] as string[], optOut: [] as string[], panel: false,
  // MASTER UPDATE section 2: protections (identity/protection.py decides; the page shows), the bell and Messages, LynkAssist
  coolOffUntil: 0, locked: false, advanced: false, secondWay: true, held: "" as "" | "locked" | "cool_off",
  contactChange: null as null | { until: number }, signupWay: "phone" as "phone" | "email", merged: 0,
  nset: { off: [] as string[], muted: [] as string[], paused: false, dnd: false, summary: false, lock: "neutral" as "neutral" | "full" | "none", deputy: null as null | number, tested: false, health: false, reminders: [] as { id: string; at: number }[] },
  lines: [] as Line[], sent: [] as Sent[], bellFilter: "all", lastOpened: 0, whyNid: "",
  history: [] as { id: string; action: string; ran: boolean; why: string; at: number; undone: boolean; was?: string }[], pendingAssist: null as null | string, assistFresh: false, ask: "",
};
/** Sample identity check and case references in the one public id format (core/ids.py; tests/test_emulators.py checks them). */
const SAMPLE_LOVER = "LOVER-3301-0442-1905";
const SAMPLE_MEMBER = "01a1ccc3-fe6e-7222-b62f-dff0086a4e75";   // a labelled sample record (NEW UPDATE 4); real ones come from the cloud
const SAMPLE_CASES = ["LOCASE-2101-7710-0042", "LOCASE-2101-7710-0059"];
const choose = (): Choice => chooseInterface(DEVICES, { ...browserFacts(window), override: S.testSize !== "auto" ? TEST_VIEW[S.testSize] ?? null : S.override });
const pct = (bps: number): string => { try { return new Intl.NumberFormat(locale(), { style: "percent", maximumFractionDigits: 2 }).format(bps / 10000); } catch { return `${bps / 100}%`; } };
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const PSEUDO: Record<string, string> = { a: "à", c: "ç", e: "é", i: "î", n: "ñ", o: "ö", s: "š", u: "ü", y: "ý" };
const pseudo = (s: string): string => `[${s.replace(/[aceinosuy]/g, (c) => PSEUDO[c] ?? c)} ${"~".repeat(Math.max(1, Math.round(s.length * 0.4)))}]`;
const isTest = (): boolean => TEST_LANGS.includes(S.lang);
const t: T = (k, vars) => (isTest() ? pseudo(translator(EN)(k, vars)) : translator(PACKS[S.lang]?.texts ?? EN, EN)(k, vars));
const icon: Icon = (id, cls = "ic") => `<span class="${cls}" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const pack = (): CountryPack => DATA.packs[S.country] ?? (DATA.packs[DATA.packOrder[0] ?? ""] as CountryPack);
/** The main footer (blueprint 26 A and B): every word from the language packs, payment methods from the chosen country's pack,
 *  the copyright line fixed and never translated. */
const appFooter = (): string => {
  const p = pack();
  return mainFooterHtml(buildFooter({ now: new Date(), lang: S.lang, words: (k) => (k in EN ? t(k) : undefined),
    pack: { code: p.code, name: p.name, currency: p.currency, tz: p.tz, languages: [], providers: p.providers, card_networks: p.card_networks, wallets: p.wallets } }), esc, (id) => DATA.icons[id] ?? "",
    { light: markFor(DATA.brand.places, "web-footer", false, FOOTER_LOGO_ROOM[S.size]).svg, dark: markFor(DATA.brand.places, "web-footer", true, FOOTER_LOGO_ROOM[S.size]).svg });
};
/** Room for the footer logo (brand surface web-footer): the full logo whenever 120 px or more is free, which is every size here. */
const FOOTER_LOGO_ROOM: Record<string, number> = { computer: 180, tablet: 180, phone: 160 };
const locale = (): string => `${isTest() ? "en" : S.lang}-${pack().code}`;
const money = (minor: number): string => { try { return new Intl.NumberFormat(locale(), { style: "currency", currency: pack().currency }).format(minor / 100); } catch { return `${pack().currency} ${(minor / 100).toFixed(2)}`; } };
const clock = (ms: number): string => new Intl.DateTimeFormat(locale(), { timeZone: pack().tz, hour: "2-digit", minute: "2-digit" }).format(ms);
const dateOf = (s: number): string => { try { return new Intl.DateTimeFormat(locale(), { timeZone: pack().tz, dateStyle: "medium" }).format(s * 1000); } catch { return new Date(s * 1000).toISOString().slice(0, 10); } };
const whenOf = (s: number): string => { try { return new Intl.DateTimeFormat(locale(), { timeZone: pack().tz, dateStyle: "medium", timeStyle: "short" }).format(s * 1000); } catch { return new Date(s * 1000).toISOString().slice(0, 16); } };
const langName = (code: string): string => PACKS[code]?.native ?? code;
const n = (x: number): string => { try { return new Intl.NumberFormat(locale()).format(x); } catch { return String(x); } };
const ready = (service: "paylinks" | "registration"): boolean => !S.realUser || (service === "paylinks" ? pack().ready["mobile_money"]?.ok === true : false);   // Start a business: no gateway is signed anywhere yet

function record(type: string, origin: "device" | "server", payload: unknown): void {
  const sync: UserState = origin === "server" ? "confirmed" : S.link === "offline" ? "queued" : "sent";
  S.events.unshift({ n: S.events.length + 1, type, origin, payload, sync, at: Date.now() });
  if (sync === "queued") S.pending++;
  drawLog();
}
/** The person's orders and requests (they are the customer, so the customer's view: no ids, addresses or positions), each a tracker from the shared engine (catalog/tracking.v1.json) replaying the cloud's
 *  events: the same steps the shop's phone, the rider's phone and the tracking page show. Sample records only. */
const TRK = new Tracking(REGISTER);
const ORDER_NOW = "0001-ord-now", ORDER_PAST = "0002-ord-past", DLV_NOW = "0003-dlv-now", DLV_PAST = "0004-dlv-past";
(() => {
  const at = T_NOW() - 1500, ev = (type: string, payload: Record<string, unknown>, dt: number): void => { TRK.apply({ type, payload, at: at + dt }, "shop"); };
  ev("OrderSentToKitchen", { order_id: ORDER_PAST, lines: [{ line_no: 0 }] }, -2 * DAY);
  ev("KitchenItemReady", { order_id: ORDER_PAST, line_no: 0 }, -2 * DAY + 600);
  ev("DeliveryRequested", { delivery_id: DLV_PAST, order_id: ORDER_PAST }, -2 * DAY + 650);
  ev("DeliveryAccepted", { delivery_id: DLV_PAST }, -2 * DAY + 700);
  ev("DeliveryPickedUp", { delivery_id: DLV_PAST }, -2 * DAY + 900);
  ev("DeliveryDelivered", { delivery_id: DLV_PAST, proof: "code" }, -2 * DAY + 1800);
  ev("OrderSentToKitchen", { order_id: ORDER_NOW, lines: [{ line_no: 0 }, { line_no: 1 }] }, 0);
  ev("KitchenItemReady", { order_id: ORDER_NOW, line_no: 0 }, 300);
  ev("KitchenItemReady", { order_id: ORDER_NOW, line_no: 1 }, 600);
  ev("DeliveryRequested", { delivery_id: DLV_NOW, order_id: ORDER_NOW }, 700);
  ev("DeliveryAccepted", { delivery_id: DLV_NOW, eta: new Date((at + 2700) * 1000).toISOString().slice(0, 19) + "Z" }, 760);
  ev("DeliveryPickedUp", { delivery_id: DLV_NOW }, 900);
  TRK.setProgress("delivery", DLV_NOW, 0.55);
})();
const trackLook = () => ({ t, esc, icon: (id: string) => icon(id), time: (iso: string) => { try { return clock(Date.parse(iso)); } catch { return iso.slice(11, 16); } }, chip: (st: UserState) => `<span class="chip st-${st}">${icon(`status-${st}`)}<span>${esc(t(`st_${st}`))}</span></span>` });
const tracker = (kind: string, id: string, title?: string): string => { const v: TrackView | null = TRK.view(kind, id, "customer", T_NOW()); return v ? trackerHtml(v, trackLook(), title) : ""; };
const secEvent = (type: string): void => { S.secEvents.unshift({ type, at: T_NOW() }); record(type, "server", { lynkid: LYNKID }); };

// ---------------------------------------------------------------- MASTER UPDATE section 2: the bell, Messages, protections, LynkAssist
/** A security or account message: one line in the bell and one record per channel on the Messages page. The sender address
 *  and the actions come from catalog/messages.v1.json (through parts.generated.ts), never typed here. */
const ACT_WORD: Record<string, string> = { this_was_not_me: "ntf_act_this_was_not_me", cancel_recovery: "ntf_act_cancel_recovery", cancel_change: "ntf_act_cancel_change", i_am_here: "ntf_act_i_am_here", snooze: "ntf_act_snooze", done: "ntf_act_done", cancel_close: "ntf_act_cancel_close" };
const AREAS = ["security", "account", "safety", "selling", "stock", "people"];
function tell(kind: string, title: string, at = Date.now()): void {
  const k = MESSAGES.kinds[kind]; if (!k) return;
  const nid = `n${S.lines.length + 1}`;
  S.lines.unshift({ nid, kind, title, at });
  const channels: Sent["channel"][] = k.priority === "critical" ? ["push", "email", "text"] : k.area === "security" ? ["push", "email"] : ["push"];
  for (const ch of channels) S.sent.unshift({ id: `${nid}-${ch}`, channel: ch, sender: ch === "email" ? k.sender : "LynkOmni", title, at, state: S.link === "offline" ? "queued" : "sent" });
}
const shownLines = (): Line[] => S.lines.map((l) => ({ ...l, title: t(l.title), actions: (MESSAGES.kinds[l.kind]?.actions ?? []).filter((a) => ACT_WORD[a]).map((a) => ({ id: a, label: t(ACT_WORD[a]!) })) }));
(() => { const at = Date.now(); tell("new_sign_in", "notice_signin", at - 60_000); tell("consent_ending", "notice_consent", at - 3_600_000); S.lines.forEach((l) => { l.read = l.kind !== "new_sign_in"; }); S.lastOpened = at - 1_800_000; })();
let kpack: { lang: string; entries: ReturnType<typeof buildPack> } | null = null;
const knowledge = () => { const lang = isTest() ? "en" : S.lang; if (!kpack || kpack.lang !== lang) kpack = { lang, entries: buildPack({ ...EN, ...(PACKS[lang]?.texts ?? {}) }) }; return kpack.entries; };
/** The protections the cloud enforces, shown before the person tries: a locked account or a cool-off holds these acts. */
const holds = (act: string): "" | "locked" | "cool_off" => { const r = mayNow(act, { locked: S.locked, heldUntil: S.coolOffUntil, now: T_NOW() }); return r.ok ? "" : (r.why ?? ""); };
const heldNote = (why: string): string => (why === "locked" ? off(t("lock_done")) : why === "cool_off" ? wait(t("held_note", { when: whenOf(S.coolOffUntil) })) : "");
/** A step that needs a fresh check that it is the person: true when the check just passed for this very step. */
const fresh = (then: string): boolean => { if (S.stepup?.ok && S.stepup.then === then) { S.stepup = null; return true; } stepUp(then); return false; };
function crumbs(): string {
  if (!signedIn()) return "";
  let steps: string[] = []; try { steps = trail("account.lynkomni.com", screenPath()); } catch { return ""; }
  const label = (p: string) => (p === "/" ? t("page_overview") : t(`page_${PAGES.find((x) => pagePath(x) === p) ?? "overview"}`));
  return breadcrumbBar(steps.map((p) => ({ path: p, label: label(p) })), S.size === "phone", t);
}
function securityCenter(now: number): string {
  const findings: { key: string; fix: string }[] = [];
  if (S.passkeys.length < 2 && !S.secondWay) findings.push({ key: "find_two_ways", fix: "passkey:add" });
  if (!S.advanced) findings.push({ key: "find_advanced", fix: "adv:on" });
  const checkup = `<div class="card wide"><h2>${esc(t("checkup_title"))}</h2>${heldNote(S.held)}${findings.length ? rows(findings.map((f) => kv(esc(t(f.key)), "", `<button class="secondary" data-act="${f.fix}">${esc(t("as_fix_this"))}</button>`))) : ok(t("checkup_all_good"))}</div>`;
  const cool = S.coolOffUntil > now ? `<div class="card wide"><div class="warn">${icon("ui-warning")}<span>${esc(t("cooloff_note", { when: whenOf(S.coolOffUntil) }))}</span></div><div class="actions"><button class="secondary" data-act="notme">${esc(t("ntf_act_this_was_not_me"))}</button></div></div>` : "";
  const two = `<div class="card"><h2>${esc(t("two_ways_title"))}</h2>${S.passkeys.length > 1 || S.secondWay ? ok(t("two_ways_ok")) : wait(t("two_ways_one"))}</div>`;
  const lock = `<div class="card"><h2>${esc(t("lock_title"))}</h2>${S.locked ? `${off(t("lock_done"))}<p class="muted">${esc(t("unlock_note"))}</p><div class="actions"><button class="primary" data-act="lock:undo">${esc(t("unlock"))}</button></div>` : `<p class="muted">${esc(t("lock_body"))}</p><div class="actions"><button class="primary" data-act="lock:start">${icon("ui-lock")}<span>${esc(t("lock_title"))}</span></button></div>`}</div>`;
  const adv = `<div class="card"><h2>${esc(t("adv_title"))}</h2><p class="muted">${esc(t("adv_body", { days: n(coolOffSeconds(true) / DAY), days2: n(contactWaitSeconds(true) / DAY) }))}</p>${S.advanced ? `${ok(t("adv_on"))}<div class="actions"><button class="secondary" data-act="adv:off">${esc(t("turn_off"))}</button></div>` : S.passkeys.length < 2 ? wait(t("adv_needs_two")) : `<div class="actions"><button class="primary" data-act="adv:on">${esc(t("turn_on"))}</button></div>`}</div>`;
  const staff = `<div class="card"><h2>${esc(t("staff_title"))}</h2>${rows([kv(esc(t("staff_line", { what: t("page_billing"), ref: SAMPLE_CASES[0] as string })), esc(whenOf(now - 4 * DAY)))])}</div>`;
  const succ = `<div class="card">${comingSoon(t("successor_title"), t, null, S.notified.has(t("successor_title")))}<p class="muted">${esc(t("successor_note"))}</p></div>`;
  return `${checkup}${cool}${two}${lock}${adv}${staff}${succ}`;
}
function notificationSettings(): string {
  const sw = (act: string, on: boolean, label: string, locked = false) => `<label class="switch"><input type="checkbox" data-act="toggle:${act}"${on ? " checked" : ""}${locked ? " disabled" : ""}><span>${esc(label)}</span></label>`;
  const chans: Sent["channel"][] = ["push", "email", "text", "bell"];
  const grid = AREAS.map((a) => { const locked = a === "security" || a === "safety"; return kv(`${esc(t(`ntf_area_${a}`))}${locked ? `<span class="sub">${esc(t("nset_locked"))}</span>` : ""}`, `<span class="wrapline">${chans.map((c) => sw(`grid:${a}:${c}`, locked || !S.nset.off.includes(`${a}:${c}`), t(`msg_ch_${c}`), locked)).join("")}</span>`); });
  const biz = [["b1", t("shop_name")], ["b2", t("client_pharmacy")]].map(([id, name]) => kv(esc(name ?? ""), sw(`biz:${id}`, !!id && S.nset.muted.includes(id), t("nset_mute"))));
  const lockChoice = (["neutral", "full", "none"] as const).map((m) => `<button type="button" class="chipbtn${S.nset.lock === m ? " on" : ""}" aria-pressed="${S.nset.lock === m}" data-act="nset:lock:${m}">${esc(t(`nset_lock_${m}`))}</button>`).join("");
  const deputy = S.nset.deputy ? `${ok(t("nset_deputy_on", { name: t("role_manager"), when: dateOf(S.nset.deputy) }))}<div class="actions"><button class="secondary" data-act="nset:enddeputy">${esc(t("nset_end"))}</button></div>` : `<div class="actions"><button class="secondary" data-act="nset:deputy">${esc(t("nset_deputy_set"))}</button></div>`;
  const reminders = S.nset.reminders.length ? rows(S.nset.reminders.map((r) => kv(esc(t("remind_sample")), esc(whenOf(r.at)), `<button class="secondary" data-act="nset:snooze:${r.id}">${esc(t("ntf_act_snooze"))}</button><button class="secondary" data-act="nset:done:${r.id}">${esc(t("ntf_act_done"))}</button>`))) : "";
  return `${pageTitle("notifications")}<div class="cards">
    <div class="card wide"><h2>${esc(t("nset_grid"))}</h2>${rows(grid)}<p class="muted">${esc(t("security_always"))}</p></div>
    <div class="card"><h2>${esc(t("your_businesses"))}</h2>${rows(biz)}</div>
    <div class="card"><h2>${esc(t("quiet_hours"))}</h2>${rows([sw("pause", S.nset.paused, t("nset_pause")), sw("dnd", S.nset.dnd, t("nset_dnd")), sw("summary", S.nset.summary, t("nset_summary"))])}${S.nset.paused ? `<p class="muted">${esc(t("nset_paused"))}</p>` : ""}<p class="muted">${esc(t("quiet_hours_line", { start: clock(Date.UTC(2026, 0, 1, 22)), end: clock(Date.UTC(2026, 0, 1, 7)) }))}</p></div>
    <div class="card"><h2>${esc(t("nset_lock"))}</h2><div class="nfilters" role="group" aria-label="${esc(t("nset_lock"))}">${lockChoice}</div></div>
    <div class="card"><h2>${esc(t("nset_deputy"))}</h2><p class="muted">${esc(t("nset_deputy_body"))}</p>${deputy}</div>
    <div class="card"><h2>${esc(t("nset_test"))}</h2><div class="actions"><button class="secondary" data-act="nset:test">${esc(t("nset_test"))}</button><button class="secondary" data-act="nset:health">${esc(t("nset_health"))}</button></div>${S.nset.tested ? ok(t("nset_test_sent")) : ""}${S.nset.health ? ok(t("nset_health_ok")) : ""}</div>
    <div class="card"><h2>${esc(t("nset_remind"))}</h2>${reminders}<div class="actions"><button class="secondary" data-act="nset:remind">${icon("ui-plus")}<span>${esc(t("nset_remind_add"))}</span></button></div></div>
  </div>`;
}
const ASSIST_DEMO: Record<string, string> = { change_language: "ah_demo_lang", lock_everything: "lock_title" };
function assistPage(): string {
  const now = Date.now();
  const pend = S.pendingAssist;
  const card = pend ? confirmCard({ what: t(ASSIST_DEMO[pend] ?? pend), d: decide(pend, { role: "person", fresh_check: S.assistFresh }) }, t, icon) : `<div class="actions">${Object.entries(ASSIST_DEMO).map(([id, key]) => `<button class="secondary" data-act="assistc:${id}">${icon("product-assist")}<span>${esc(t(key))}</span></button>`).join("")}</div>`;
  const last = S.history[0];
  const rec = last && last.ran && !pend ? receipt({ what: t(ASSIST_DEMO[last.action] ?? last.action), undoable: last.action === "change_language" && !last.undone, secondsLeft: Math.max(0, 30 - Math.round((now - last.at) / 1000)) }, t, icon) : "";
  const list = S.history.length ? rows(S.history.map((h) => kv(esc(t(ASSIST_DEMO[h.action] ?? h.action)), esc(whenOf(h.at / 1000)), h.undone ? off(t("undone")) : h.ran ? ok(t("done")) : off(t(h.why))))) : `<p class="muted">${esc(t("ah_empty"))}</p>`;
  return `${pageTitle("assist")}<div class="cards"><div class="card wide">${card}${rec}</div><div class="card wide"><h2>${esc(t("ah_title"))}</h2>${list}<p class="suggested">${esc(t("suggested_by_assist"))}</p></div></div>`;
}
function cardsByGroup(): string {
  if (S.realUser) return `<div class="card">${comingSoon("LynkVCard", t, statePic("coming_soon"), S.notified.has("LynkVCard"))}</div>`;
  const cards = [{ group: "prepaid", tier: "edge", last4: "4242" }, { group: "credit", tier: "hub", last4: "1881" }];
  const groups = ["prepaid", "debit", "credit"].filter((g) => cards.some((c) => c.group === g));
  return `<div class="card wide"><h2>${esc(t("cards_title"))}</h2>${groups.map((g) => `<h3>${esc(t(`card_${g}`))}</h3>${rows(cards.filter((c) => c.group === g).map((c) => kv(esc(t("card_line", { name: cardPlanName(c.group, c.tier), last4: c.last4 })), S.locked ? wait(t("card_freeze_sent")) : ok(t("st_confirmed")))))}${g === "credit" ? `<p class="muted">${esc(t("credit_note"))}</p>` : ""}`).join("")}</div>`;
}
function doLock(by: "in_person" | "not_me" | "assist"): void {
  S.locked = true; S.sessions = S.sessions.slice(0, 1);
  record("EverythingLocked", "server", { by, sessions_ended: true, cards: "freeze_sent", keys: "paused", shares_kept: S.shares.length });
  if (by === "not_me") record("NotMeReported", "server", { rolled_back: ["sessions", "contact_change"] });
  S.contactChange = null; tell("everything_locked", "lock_done");
}

// ---------------------------------------------------------------- navigation
const signedIn = (): boolean => !["signin", "signup", "recover"].includes(S.screen);
const navItems = (): NavItem[] => {
  const phone: NavItem[] = [
    { id: "overview", label: t("nav_overview"), icon: "ui-home", href: "/", current: S.screen === "overview" },
    { id: "security", label: t("nav_security"), icon: "ui-lock", href: "/security", current: S.screen === "security" },
    { id: "businesses", label: t("nav_businesses"), icon: "ui-grid", href: "/businesses", current: S.screen === "businesses" },
    { id: "wallet", label: t("nav_wallet"), icon: "ui-pay-wallet", href: "/wallet", current: S.screen === "wallet" },
    { id: "more", label: t("nav_more"), icon: "ui-menu", href: "/more", current: !["overview", "security", "businesses", "wallet"].includes(S.screen) },
  ];
  if (S.size === "phone") return phone;
  return PAGES.map((p) => ({ id: p, label: t(`page_${p}`), icon: PAGE_ICON[p], href: pagePath(p), current: S.screen === p }));
};
const PAGE_ICON: Record<Page, string> = { overview: "ui-home", profile: "ui-user", security: "ui-lock", businesses: "ui-grid", orders: "ui-cart", transactions: "ui-receipt", wallet: "ui-pay-wallet", billing: "ui-pay-card", memberships: "ui-check", privacy: "ui-doc", notifications: "ui-bell", support: "ui-info", payslips: "ui-doc", payments: "ui-pay-instant", start: "ui-bolt", storefront: "ui-cart", trips: "ui-globe", collect: "ui-qr", messages: "product-chat", assist: "product-assist",
  attendance: "product-attend", tickets: "product-queue", answers: "product-survey", panel: "product-survey" };
const screenPath = (): string => (S.screen === "signin" ? "/sign-in" : S.screen === "signup" ? "/sign-up" : S.screen === "recover" ? "/recover" : pagePath(S.screen));
const sync = (): SyncInfo => ({ link: S.link, pending: S.pending, lastSync: S.lastSync, dataSaver: false, forcedOffline: false });
const statePic = (kind: StateKind): Pic | null => {
  const id = STATE_PICTURE[kind];
  if (!id || S.mode === "lite") return null;
  const p = DATA.statePictures[id]?.[S.mode === "sunlight" ? "light" : S.theme];
  return p ? { svg: S.mode === "sunlight" ? (p.contrast ?? p.svg) : p.svg, alt: p.alt } : null;
};
const pageTitle = (page: Page): string => `<div class="pagetitle"><h1>${esc(t(`page_${page}`))}</h1>${connectionChip(sync(), t, icon)}</div>`;
const rows = (items: string[]): string => `<ul class="rows">${items.map((i) => `<li>${i}</li>`).join("")}</ul>`;
const kv = (k: string, v: string, action = ""): string => `<span class="k">${k}</span><span class="v">${v}</span>${action}`;
const ok = (s: string): string => `<span class="status-ok">${icon("ui-check")}<span>${esc(s)}</span></span>`;
const wait = (s: string): string => `<span class="status-wait">${icon("ui-sync")}<span>${esc(s)}</span></span>`;
const off = (s: string): string => `<span class="status-off">${icon("ui-info")}<span>${esc(s)}</span></span>`;

// ---------------------------------------------------------------- sign-in, sign-up, recovery
function authSignIn(): string {
  return `<div class="auth"><h1>${esc(t("signin_title"))}</h1><p class="lead">${esc(t("signin_hint"))}</p>
    <div class="field"><label for="who">${esc(t("username_or_lynkid"))}</label><input class="text" id="who" value="grace.k" autocomplete="username"></div>
    <button class="primary" data-act="signin:passkey">${icon("ui-lock")}<span>${esc(t("signin_passkey"))}</span></button>
    <p class="muted">${esc(t("signin_passkey_hint"))}</p>
    <button class="secondary" data-act="signin:other">${esc(t("signin_other"))}</button>
    <p class="muted">${esc(t("signin_pin"))}</p>
    <div class="okbox">${icon("ui-bell")}<span>${esc(t("signin_new_device_note"))}</span></div>
    <div class="actions"><span class="muted">${esc(t("no_account"))}</span> <button class="secondary" data-act="go:signup">${esc(t("create_account"))}</button></div>
    <div class="actions"><span class="muted">${esc(t("lost_access"))}</span> <button class="secondary" data-act="go:recover">${esc(t("recover"))}</button></div></div>`;
}
function authSignUp(): string {
  const step = nextSignUpStep(S.signUp);
  const idx = step ? SIGN_UP_STEPS.indexOf(step) : SIGN_UP_STEPS.length;
  const bar = `<ol class="steps" aria-label="${esc(t("step_of", { n: Math.min(idx + 1, 4), total: 4 }))}">${SIGN_UP_STEPS.map((_, i) => `<li class="${i <= idx ? "on" : ""}"></li>`).join("")}</ol>`;
  let body = "";
  if (step === "username") body = `<h2>${esc(t("step_username"))}</h2>${usernameField(S.username, S.cloud, (u) => u === "mamas.kitchen", t, icon)}<label class="check"><input type="checkbox" id="adultIn" data-act="toggle:adult"${S.signUp.adult ? " checked" : ""}><span>${esc(t("signup_adult", { age: n(DATA.storefront.min_age) }))}</span></label><p class="muted">${esc(t("signup_adult_note"))}</p><button class="primary" data-act="signup:username" ${S.cloud === "available" && S.signUp.adult ? "" : "disabled"}>${esc(t("next"))}</button>`;
  else if (step === "contact") body = `<h2>${esc(t("step_contact"))}</h2><div class="nfilters" role="group" aria-label="${esc(t("step_contact"))}">${(["phone", "email"] as const).map((w) => `<button type="button" class="chipbtn${S.signupWay === w ? " on" : ""}" aria-pressed="${S.signupWay === w}" data-act="signup:way:${w}">${esc(t(w === "phone" ? "way_phone" : "msg_ch_email"))}</button>`).join("")}</div><p class="muted">${esc(t("contact_hint"))}</p><div class="field"><label for="code">${esc(t("code_label"))}</label><input class="text" id="code" inputmode="numeric" value="482913"></div><button class="primary" data-act="signup:contact">${esc(t("next"))}</button>`;
  else if (step === "passkey") body = `<h2>${esc(t("step_passkey"))}</h2><p class="muted">${esc(t("passkey_hint"))}</p><button class="primary" data-act="signup:passkey">${icon("ui-lock")}<span>${esc(t("add_passkey"))}</span></button>`;
  else if (step === "recovery_code") body = `<h2>${esc(t("step_recovery_code"))}</h2><div class="codebox"><span>${esc(S.recoveryCode)}</span>${icon("ui-doc")}</div><div class="warn">${icon("ui-warning")}<span>${esc(t("recovery_code_hint"))}</span></div><button class="primary" data-act="signup:code">${esc(t("recovery_code_confirm"))}</button>`;
  else body = `<div class="okbox">${icon("ui-check")}<span>${esc(t("passkey_added"))}</span></div><h2>${esc(t("two_ways_title"))}</h2>${S.passkeys.length > 1 || S.secondWay ? ok(t("two_ways_ok")) : `${wait(t("two_ways_one"))}<div class="actions"><button class="secondary" data-act="passkey:add">${icon("ui-plus")}<span>${esc(t("add_passkey"))}</span></button></div>`}<div class="assist">${icon("ui-bolt")}<span><strong>${esc(t("assist_guide"))}:</strong> ${esc(t("recovery_code_push"))}</span></div><p class="muted">${esc(t("signup_later"))}</p>${S.merged ? ok(t("merge_done", { n: n(S.merged) })) : `<div class="actions"><button class="secondary" data-act="merge:do">${esc(t("merge_btn"))}</button></div>`}<button class="primary" data-act="go:overview">${esc(t("continue"))}</button>`;
  return `<div class="auth"><h1>${esc(t("signup_title"))}</h1><p class="lead">${esc(t("step_of", { n: Math.min(idx + 1, 4), total: 4 }))}</p>${bar}${body}<button class="secondary" data-act="go:signin">${esc(t("back"))}</button></div>`;
}
function authRecover(): string {
  const r = S.recover;
  let body = "";
  if (r.started) {
    const now = T_NOW(); const done = recoveryReady(r.started, now);
    body = done ? `<div class="okbox">${icon("ui-check")}<span>${esc(t("ev_recovery_completed"))}</span></div><div class="warn">${icon("ui-warning")}<span>${esc(t("recovery_restricted"))}</span></div><button class="primary" data-act="go:overview">${esc(t("continue"))}</button>`
      : `${wait(t("recovery_waiting", { when: whenOf(recoveryReadyAt(r.started)) }))}<p class="muted">${esc(t("recovery_cancel_note"))}</p><div class="assist">${icon("ui-bolt")}<span><strong>${esc(t("assist_guide"))}:</strong> ${esc(t("guide_steps", { steps: RECOVERY[r.started.path].needs.length + 1 }))}</span></div><div class="warn">${icon("ui-warning")}<span>${esc(t("recovery_restricted"))}</span></div><button class="secondary" data-act="recover:cancel">${esc(t("cancel"))}</button>`;
  } else if (r.otherDevice === null) body = `<h2>${esc(t("recover_question_device"))}</h2><div class="actions"><button class="primary" data-act="recover:device:yes">${esc(t("yes"))}</button><button class="secondary" data-act="recover:device:no">${esc(t("no"))}</button></div>`;
  else if (r.otherDevice) body = `<h2>${esc(t("path_device"))}</h2><p class="muted">${esc(t("path_device_body"))}</p><button class="primary" data-act="recover:start:device">${esc(t("start_recovery"))}</button>`;
  else if (r.hasCode === null) body = `<h2>${esc(t("recover_question_code"))}</h2><div class="actions"><button class="primary" data-act="recover:code:yes">${esc(t("yes"))}</button><button class="secondary" data-act="recover:code:no">${esc(t("no"))}</button></div>`;
  else if (r.hasCode) body = `<h2>${esc(t("path_code"))}</h2><p class="muted">${esc(t("path_code_body"))}</p><div class="field"><label for="rc">${esc(t("recovery_code"))}</label><input class="text" id="rc" value="${esc(S.recoveryCode)}"></div><div class="field"><label for="sms">${esc(t("sms_code"))}</label><input class="text" id="sms" inputmode="numeric" value="305117"></div><button class="primary" data-act="recover:start:code">${esc(t("start_recovery"))}</button>`;
  else body = `<h2>${esc(t("path_assisted"))}</h2><p class="muted">${esc(t("path_assisted_body"))}</p><button class="primary" data-act="recover:start:assisted">${esc(t("start_recovery"))}</button>`;
  return `<div class="auth"><h1>${esc(t("recover_title"))}</h1>${body}<div class="warn">${icon("ui-warning")}<span>${esc(t("never_allowed"))}</span></div><button class="secondary" data-act="go:signin">${esc(t("back"))}</button></div>`;
}

// ---------------------------------------------------------------- pages
function page(): string {
  const now = T_NOW();
  switch (S.screen) {
    case "signin": return authSignIn();
    case "signup": return authSignUp();
    case "recover": return authRecover();
    case "overview": {
      const todo = S.passkeys.length < 2;
      return `${pageTitle("overview")}<div class="cards">
        <div class="card"><h2>${esc(t("overview_welcome", { name: t("person_name") }))}</h2><div class="muted">${esc(t("your_lynkid"))}</div><div class="lynkid-box"><span>${esc(maskId(LYNKID))}</span><button class="copy" data-act="copy:lynkid" aria-label="${esc(t("copy"))}">${icon("ui-copy")}</button></div></div>
        <div class="card"><h2>${esc(t("page_security"))}</h2>${todo ? wait(t("overview_security_todo")) : ok(t("overview_security_ok", { n: S.passkeys.length }))}<div class="actions"><button class="secondary" data-act="go:security">${esc(t("page_security"))}</button></div></div>
        <div class="card wide"><h2>${esc(t("shortcuts"))}</h2><div class="actions">${(["businesses", "wallet", "billing", "privacy", "payments", "start"] as Page[]).map((p) => `<button class="secondary" data-act="go:${p}">${icon(PAGE_ICON[p])}<span>${esc(t(`page_${p}`))}</span></button>`).join("")}</div></div>
      </div>`;
    }
    case "profile": return `${pageTitle("profile")}<div class="card">${rows([
      kv(esc(t("profile_name")), esc(t("person_name")), `<button class="secondary" data-act="edit:name">${esc(t("change"))}</button>`),
      kv(esc(t("profile_username")), "@grace.k", `<button class="secondary" data-act="edit:username">${esc(t("change"))}</button>`),
      kv(esc(t("profile_phone")), `•••• 0471 ${S.contactChange ? wait(t("contact_wait", { when: whenOf(S.contactChange.until) })) : ok(t("verified"))}`, S.contactChange ? `<button class="secondary" data-act="contact:cancel">${esc(t("ntf_act_cancel_change"))}</button>` : `<button class="secondary" data-act="contact:start">${esc(t("change"))}</button>`), kv(esc(t("profile_email")), `g•••@example.org ${ok(t("verified"))}`),
      kv(esc(t("profile_language")), esc(langName(isTest() ? "en" : S.lang)), `<button class="secondary" data-act="shell:globe">${esc(t("change"))}</button>`),
      kv(esc(t("profile_region")), esc(pack().sample ? t("sample_country") : pack().name)), kv(esc(t("profile_timezone")), esc(pack().tz)),
    ])}<p class="muted">${esc(t("username_change_note"))}</p></div>`;
    case "security": return `${pageTitle("security")}<div class="cards">${securityCenter(now)}
      <div class="card"><h2>${esc(t("passkeys_devices"))}</h2>${rows(S.passkeys.map((p) => kv(esc(p.device.startsWith("device_") ? t(p.device) : p.device) + (p.here ? ` ${ok(t("this_device"))}` : ""), esc(t("added_on", { when: dateOf(p.at) })), `<button class="secondary" data-act="passkey:remove:${p.locrd}">${esc(t("remove"))}</button>`)))}<div class="actions"><button class="primary" data-act="passkey:add">${icon("ui-plus")}<span>${esc(t("add_passkey"))}</span></button></div><p class="muted">${esc(t("keep_one_passkey"))}</p></div>
      <div class="card"><h2>${esc(t("active_sessions"))}</h2>${rows(S.sessions.map((s) => kv(esc(t("session_line", { site: t(`site_${s.site}`), device: t(s.device), place: t(s.place) })), esc(whenOf(s.at)), `<button class="secondary" data-act="session:revoke:${s.tail}">${esc(t("remove"))}</button>`)))}<div class="actions"><button class="secondary" data-act="session:all">${icon("ui-signout")}<span>${esc(t("sign_out_everywhere"))}</span></button></div></div>
      <div class="card"><h2>${esc(t("recent_events"))}</h2><ul class="evlist">${S.secEvents.slice(0, 8).map((e) => `<li><span class="t">${esc(whenOf(e.at))}</span><span class="w">${esc(t(SECURITY_EVENT_KEY[e.type] ?? e.type))}</span></li>`).join("")}</ul></div>
      <div class="card"><h2>${esc(t("recovery_settings"))}</h2>${rows([ok(t("recovery_code_set")) + `<button class="secondary" data-act="recovery:newcode">${esc(t("new_recovery_code"))}</button>`, kv(esc(t("backup_contact")), "•••• 2210"), kv(esc(t("second_device")), S.passkeys.length > 1 ? ok(t("verified")) : wait(t("not_yet")))])}</div>
      <div class="card wide"><h2>${esc(t("connected_apps"))}</h2>${S.consents.length ? rows(S.consents.map((c, i) => { const st = consentState(c, now); return kv(esc(`${c.scope}: ${c.purpose}`), st === "ending_soon" ? wait(t("consent_ending", { n: Math.ceil((c.expires - now) / DAY) })) : st === "active" ? ok(t("consent_active", { when: dateOf(c.expires) })) : off(t("ev_consent_withdrawn")), st === "active" || st === "ending_soon" ? `<button class="secondary" data-act="consent:withdraw:${i}">${esc(t("revoke"))}</button>` : ""); })) : `<p class="muted">${esc(t("no_connected_apps"))}</p>`}</div>
    </div>`;
    case "businesses": return `${pageTitle("businesses")}<div class="cards">
      <div class="card"><h2>${esc(t("your_businesses"))}</h2>${rows([kv(esc(t("shop_name")), `${esc(maskId(SHOP_OID))} · ${esc(t("role_owner"))}`, `<button class="primary" data-act="open:business">${esc(t("switch_to"))}</button><button class="secondary" data-act="leave:owner">${esc(t("leave"))}</button>`)])}<p class="muted">${esc(t("last_owner_note"))}</p><div class="actions"><button class="secondary" data-act="go:start">${icon("ui-plus")}<span>${esc(t("create_business"))}</span></button></div></div>
      <div class="card"><h2>${esc(t("ws_title"))}</h2><p class="muted">${esc(t("ws_help"))}</p>${S.workspaces.length ? rows(S.workspaces.map((w) => kv(esc(t(`ws_name_${w.entity}`)), `${esc(t(`ws_kind_${w.entity}`))} · ${esc(t("role_owner"))}`, `<button class="primary" data-act="open:business">${esc(t("switch_to"))}</button>`))) : ""}<div class="actions">${(["person", "company", "organisation"] as const).map((e) => `<button class="secondary" data-act="ws:${e}">${icon(e === "person" ? "ui-user" : e === "company" ? "ui-grid" : "ui-home")}<span>${esc(t(`ws_${e}`))}</span></button>`).join("")}</div><p class="muted">${esc(t("ws_note"))}</p></div>
      <div class="card"><h2>${esc(t("client_businesses"))}</h2>${rows([
        kv(esc(t("client_pharmacy")), `${esc(t("role_accountant"))} · ${ok(t("consent_active", { when: dateOf(now + 300 * DAY) }))}`, `<button class="primary" data-act="open:client1">${esc(t("switch_to"))}</button>`),
        kv(esc(t("client_taxi")), `${esc(t("role_accountant"))} · ${wait(t("consent_missing"))}`, `<button class="secondary" disabled>${esc(t("switch_to"))}</button>`),
      ])}</div></div>`;
    case "orders": return `${pageTitle("orders")}<div class="cards"><div class="card">${tracker("order", ORDER_NOW, t("order_from", { shop: t("shop_name") }))}</div><div class="card">${tracker("order", ORDER_PAST, t("order_from", { shop: t("client_pharmacy") }))}</div></div><p class="muted">${esc(t("trk_privacy"))}</p>`;
    case "transactions": return `${pageTitle("transactions")}<div class="card">${rows([kv(esc(t("shop_name")), esc(whenOf(now - 2 * DAY)) + " · " + esc(money(1500))), kv(esc(t("client_taxi")), `${esc(whenOf(now - 5 * DAY))} · ${esc(money(4200))} · ${wait(t("refund_owed", { amount: money(4200) }))}`)])}</div>`;
    case "wallet": return `${pageTitle("wallet")}<div class="cards">
      <div class="card"><h2>${esc(t("wallet_points"))}</h2>${rows([kv(esc(t("points_at", { n: n(240), shop: t("shop_name") })), "")])}</div>
      <div class="card"><h2>${esc(t("wallet_vouchers"))}</h2>${rows([kv(esc(t("voucher_at", { amount: money(500), shop: t("client_pharmacy") })), esc(dateOf(now + 30 * DAY)))])}</div>
      <div class="card"><h2>${esc(t("wallet_tickets"))}</h2><p class="muted">${esc(t("wallet_empty"))}</p></div>${cardsByGroup()}</div>`;
    case "billing": return `${pageTitle("billing")}<div class="cards">
      <div class="card"><h2>${esc(t("shop_name"))}</h2>${rows([kv(esc(t("plan_line", { family: "LynkPOS", tier: "Plus" })), esc(t("next_bill", { amount: money(1200), when: dateOf(now + 7 * DAY) })), `<button class="secondary" data-act="plan:change">${esc(t("change_plan"))}</button>`)])}<div class="actions"><button class="secondary" data-act="go:transactions">${esc(t("invoices"))}</button><button class="secondary" data-act="open:methods">${esc(t("payment_methods"))}</button></div></div>
      <div class="card"><h2>${esc(t("movement_plans"))}</h2>${rows([kv(esc(t("plan_line", { family: "LynkMotion", tier: "Free" })), esc(t("plan_free_note"))), kv(esc(t("plan_line", { family: "LynkGuard", tier: "Free" })), esc(t("plan_free_note")))])}<p class="muted">${esc(t("movement_plans_note"))}</p><div class="actions"><button class="secondary" data-act="plan:change">${esc(t("change_plan"))}</button></div></div>
      <div class="card"><h2>${esc(t("client_pharmacy"))}</h2><p class="muted">${esc(t("no_plans"))}</p></div></div>`;
    case "memberships": return `${pageTitle("memberships")}<div class="card"><p class="muted">${esc(t("memberships_body"))}</p></div>`;
    case "privacy": return `${pageTitle("privacy")}<div class="cards">
      <div class="card"><h2>${esc(t("terms_title"))}</h2>${rows([kv(esc(t("terms_doc_terms")), esc(t("terms_line", { date: dateOf(Date.parse(TERMS_IN_FORCE.terms) / 1000) }))), kv(esc(t("terms_doc_privacy")), esc(t("terms_line", { date: dateOf(Date.parse(TERMS_IN_FORCE.privacy) / 1000) })))])}</div>
      <div class="card"><h2>${esc(t("consent_log"))}</h2>${rows(S.consents.map((c) => kv(esc(`${c.scope}: ${c.purpose}`), esc(dateOf(c.expires)))))}</div>
      <div class="card"><h2>${esc(t("download_records"))}</h2><p class="muted">${esc(t("download_hint"))}</p>${heldNote(S.held)}${S.dataRequest ? wait(t("download_requested", { when: dateOf(S.dataRequest.due) })) + tracker("data_request", "data-1") : `<div class="actions"><button class="primary" data-act="data:request">${icon("ui-doc")}<span>${esc(t("download_records"))}</span></button></div>`}</div>
      <div class="card"><h2>${esc(t("marketing_choices"))}</h2>${rows([`<label class="switch"><input type="checkbox" data-act="toggle:mkemail" ${S.marketing.email ? "checked" : ""}><span>${esc(t("marketing_email"))}</span></label>`, `<label class="switch"><input type="checkbox" data-act="toggle:mkpush" ${S.marketing.push ? "checked" : ""}><span>${esc(t("marketing_push"))}</span></label>`])}</div>
      <div class="card"><h2>${esc(t("close_account"))}</h2><p class="muted">${esc(t("close_hint"))}</p>${S.closing ? `${wait(t("close_requested", { when: dateOf(S.closing) }))}<div class="actions"><button class="primary" data-act="close:cancel">${esc(t("keep_account"))}</button></div>` : `<div class="actions"><button class="secondary" data-act="stepup:close">${esc(t("close_account"))}</button></div>`}</div></div>`;
    case "notifications": return notificationSettings();
    case "messages": return `${pageTitle("messages")}<div class="card">${messagesList([...S.sent].sort((x, y) => y.at - x.at).map((m) => ({ ...m, title: t(m.title) })), t, icon, (ms) => whenOf(ms / 1000))}</div>`;
    case "assist": return assistPage();
    case "support": {
      const desk = (side: "internal" | "external") => t(side === "external" ? "support_seller" : "support_workspace");
      const list = S.cases.length ? rows(S.cases.map((c) => kv(esc(t("support_case_line", { desk: desk(c.side), ref: c.ref })), wait(t(S.link === "offline" ? "st_queued" : "st_sent"))))) : `<p class="muted">${esc(t("support_empty"))}</p>`;
      return `${pageTitle("support")}<div class="card">${list}<div class="actions"><button class="primary" data-act="support:internal">${icon("ui-home")}<span>${esc(desk("internal"))}</span></button><button class="secondary" data-act="support:external">${icon("ui-cart")}<span>${esc(desk("external"))}</span></button></div><p class="muted">${esc(t("support_side_note"))}</p><p class="muted">${esc(t("exchange_link"))}</p></div>`;
    }
    case "storefront": {
      const sf = DATA.storefront, tier = "free";
      const handle = S.signUp.username || "grace.k";
      const id = S.idCheck === "confirmed" ? ok(t("sf_identity_done", { ref: SAMPLE_LOVER })) : S.idCheck === "sent" ? `${wait(t("sf_identity_sent"))}<div class="actions"><button class="secondary" data-act="idcheck:poll">${esc(t("sf_identity_poll"))}</button></div>`
        : `<div class="actions"><button class="primary" data-act="idcheck:start">${icon("ui-lock")}<span>${esc(t("sf_identity_start"))}</span></button></div>`;
      const idCard = S.realUser ? comingSoon(t("sf_identity"), t, statePic("coming_soon"), S.notified.has("identity")) : `<p class="muted">${esc(t("sf_identity_why"))}</p>${id}`;
      return `${pageTitle("storefront")}<div class="cards">
        <div class="card wide"><p class="muted">${esc(t("sf_intro"))}</p><div class="muted">${esc(t("sf_address"))}</div><div class="lynkid-box"><span class="deeplink">shop.lynkomni.com/${esc(handle)}</span></div><div class="actions"><button class="secondary" data-act="open:storefront">${esc(t("sf_open"))}</button></div></div>
        <div class="card"><h2>${esc(t("sf_plan"))}</h2><p>${esc(t("sf_plan_line", { plan: t(`plan_${tier}`), share: pct(sf.share_bps[tier] ?? 0) }))}</p><div class="actions"><button class="secondary" data-act="go:billing">${esc(t("sf_plans_link"))}</button></div></div>
        <div class="card"><h2>${esc(t("sf_identity"))}</h2>${idCard}</div>
        <div class="card wide"><p class="muted">${esc(t("sf_age", { age: n(sf.min_age) }))}</p></div>
      </div>`;
    }
    case "trips": {
      const scopes = ["live", "trips", "zones"] as const;
      const list = S.shares.length ? rows(S.shares.map((x) => kv(esc(`${t("share_with_sample")} · ${t(`share_scope_${x.scope}`)}`), esc(t("share_until", { time: clock(x.until * 1000) })), `<button class="secondary" data-act="share:stop:${esc(x.id)}">${esc(t("share_stop"))}</button>`)))
        : `<p class="muted">${esc(t("share_none"))}</p>`;
      const plan = S.plan ? (S.plan.checked ? ok(t("plan_done")) : `${wait(t("plan_due", { time: clock(S.plan.due * 1000) }))}<p>${esc(t("plan_contacts", { count: n(1) }))}</p><div class="actions"><button class="primary" data-act="plan:checkin">${icon("ui-check")}<span>${esc(t("plan_check_in"))}</span></button></div>`)
        : `<div class="actions"><button class="primary" data-act="plan:set">${icon("ui-bolt")}<span>${esc(t("plan_set"))}</span></button></div>`;
      return `${pageTitle("trips")}<div class="cards">
        <div class="card wide"><p class="muted">${esc(t("trips_intro"))}</p>${list}<div class="actions">${scopes.map((sc) => `<button class="secondary" data-act="share:start:${sc}">${esc(t(`share_scope_${sc}`))}</button>`).join("")}</div><p class="muted">${esc(t("share_visible"))}</p></div>
        <div class="card"><h2>${esc(t("plan_title"))}</h2><p class="muted">${esc(t("plan_intro"))}</p>${plan}</div></div>`;
    }
    case "collect": {
      const w = Math.floor(now / 60) + S.passWindow;
      const code = String((w * 7919 + 271828) % 1000000).padStart(6, "0");      // a labelled sample; the real code is made by the cloud (identity/arrive_safe.py)
      return `${pageTitle("collect")}<div class="cards">
        <div class="card wide"><p class="muted">${esc(t("collect_intro"))}</p><div class="lynkid-box"><span class="deeplink" aria-label="${esc(t("page_collect"))}">${esc(code.slice(0, 3) + " " + code.slice(3))}</span></div><p class="muted">${esc(t("collect_changes"))}</p><div class="actions"><button class="secondary" data-act="pass:next">${esc(t("collect_refresh"))}</button></div></div>
        <div class="card"><p>${esc(t("collect_waiting", { count: n(2) }))}</p><p class="muted">${esc(t("collect_once"))}</p></div></div>`;
    }
    case "attendance": {
      if (S.att !== "open") {
        const step = S.att === "closed" ? `<div class="actions"><button class="primary" data-act="att:code">${icon("ui-lock")}<span>${esc(t("att_send_code"))}</span></button></div>`
          : `${wait(t("att_code_sent"))}<div class="actions"><button class="primary" data-act="att:open">${esc(t("att_open"))}</button></div>`;
        return `${pageTitle("attendance")}<div class="card"><p class="muted">${esc(t("att_intro"))}</p>${rows([kv(esc(t("att_org")), esc(t("att_sample_org"))), kv(esc(t("att_pin")), "••••••")])}${step}</div>`;
      }
      const sample = idcn("NIN 1985 0412 3301") ?? "";
      const hidden = (what: "pin" | "idcn", value: string): string => S.attShow === what ? `<span class="deeplink" dir="ltr">${esc(value)}</span>` : "••••••";
      const req = S.attRequest ? `${wait(t(S.attRequest.kind === "dispute" ? "att_dispute_sent" : "att_delete_sent", { date: new Intl.DateTimeFormat(locale(), { dateStyle: "medium", timeZone: pack().tz }).format((S.attRequest.at + 30 * 86400) * 1000) }))}<p class="muted">${esc(t("att_reminders"))}</p>`
        : `<div class="actions"><button class="secondary" data-act="att:req:delete_my_details">${esc(t("att_delete"))}</button><button class="secondary" data-act="att:req:dispute">${esc(t("att_dispute"))}</button></div>`;
      return `${pageTitle("attendance")}<div class="cards">
        <div class="card"><h2>${esc(t("att_sample_org"))}</h2>${rows([kv(esc(t("att_set")), esc(t("att_set_face_idcn"))), kv(esc(t("att_pin")), hidden("pin", "482915"), `<button class="secondary" data-act="att:show:pin">${esc(t("att_show"))}</button>`), kv(esc(t("att_idcn")), hidden("idcn", sample), `<button class="secondary" data-act="att:show:idcn">${esc(t("att_show"))}</button>`)])}<p class="muted">${esc(t("att_keep_private"))}</p></div>
        <div class="card"><h2>${esc(t("att_records"))}</h2>${rows([kv(esc(t("att_today")), esc(t("att_in_at", { time: "07:58" }))), kv(esc(t("att_yesterday")), esc(t("att_in_out", { a: "07:55", b: "17:04", h: n(9), m: n(9) })))])}<div class="actions"><button class="secondary" data-act="att:proof">${icon("ui-doc")}<span>${esc(t("att_proof"))}</span></button></div><label class="switch"><input type="checkbox" data-act="toggle:wty"${S.wasThisYou ? " checked" : ""}><span>${esc(t("att_was_this_you"))}</span></label></div>
        <div class="card wide"><h2>${esc(t("att_your_details"))}</h2><p class="muted">${esc(t("att_only_manager_edits"))}</p>${req}</div></div>`;
    }
    case "tickets": {
      const live = S.tkLeft ? `<p class="muted">${esc(t("tk_left"))}</p>` : `${ticketCard({ section: "LAB", sectionName: t("tk_sample_section"), code: "A2K9P2", place: S.tkLate ? 7 : 4, waitMinutes: S.tkLate ? 21 : 12 }, t, icon)}<div class="actions"><button class="secondary" data-act="tk:late" ${S.tkLate ? "disabled" : ""}>${esc(t("tk_running_late"))}</button><button class="secondary" data-act="tk:leave">${esc(t("tk_leave"))}</button></div>${S.tkLate ? `<p class="muted">${esc(t("tk_late_once"))}</p>` : ""}`;
      return `${pageTitle("tickets")}<div class="cards"><div class="card">${live}</div><div class="card"><h2>${esc(t("tk_earlier"))}</h2>${rows([kv(`<span dir="ltr">PHA-B8P4T7</span>`, ok(t("tk_done")))])}<p class="muted">${esc(t("tk_no_account"))}</p></div></div>`;
    }
    case "answers": {
      const ORGS = ["sv1", "sv2"];
      const list = S.answers.length ? rows(S.answers.map((id) => kv(esc(t(`ans_${id}`)), "", `<button class="secondary" data-act="ans:del:${id}">${esc(t("ans_delete"))}</button>`))) : `<p class="muted">${esc(t("ans_none"))}</p>`;
      const stop = rows(ORGS.map((o) => kv(esc(t(`ans_org_${o}`)), S.optOut.includes(o) ? off(t("ans_stopped")) : "", S.optOut.includes(o) ? "" : `<button class="secondary" data-act="ans:stop:${o}">${esc(t("ans_dont_ask"))}</button>`)));
      return `${pageTitle("answers")}<div class="cards"><div class="card"><h2>${esc(t("ans_mine"))}</h2>${list}<p class="muted">${esc(t("ans_anonymous_note"))}</p></div><div class="card"><h2>${esc(t("ans_dont_ask"))}</h2>${stop}</div></div>`;
    }
    case "panel": {
      const pay = S.realUser ? comingSoon(t("panel_rewards"), t, statePic("coming_soon"), S.notified.has("survey_rewards")) : `<p class="muted">${esc(t("panel_rewards_sample"))}</p>`;
      const body = S.panel ? `${ok(t("panel_joined"))}<p class="muted">${esc(t("panel_never_seen"))}</p><div class="actions"><button class="secondary" data-act="panel:leave">${esc(t("panel_leave"))}</button></div>`
        : `<p class="muted">${esc(t("panel_intro"))}</p><div class="actions"><button class="primary" data-act="panel:join">${esc(t("panel_join"))}</button></div>`;
      return `${pageTitle("panel")}<div class="cards"><div class="card">${body}</div><div class="card"><h2>${esc(t("panel_rewards"))}</h2>${pay}</div></div>`;
    }
    case "payslips": return `${pageTitle("payslips")}<div class="card">${rows([kv(esc(t("payslip_line", { period: "2026-10", employer: t("client_pharmacy") })), "LODOC-9001-0044-2814", `<button class="secondary" data-act="open:payslip">${esc(t("switch_to"))}</button>`)])}<p class="muted">${esc(t("payslips_empty"))}</p></div>`;
    case "payments": {
      if (!ready("paylinks")) return `${pageTitle("payments")}<div class="card">${comingSoon("LynkCheckout", t, statePic("coming_soon"), S.notified.has("paylinks"))}</div>`;
      return `${pageTitle("payments")}<div class="card"><p class="muted">${esc(t("standing_intro"))}</p>${S.standing.length ? rows(S.standing.map((s, i) => kv(esc(t("standing_line", { merchant: s.merchant, cap: money(s.cap) })), s.active ? ok(t("standing_told")) : off(t("ev_consent_withdrawn")), s.active ? `<button class="secondary" data-act="standing:revoke:${i}">${esc(t("revoke"))}</button>` : ""))) : `<p class="muted">${esc(t("standing_empty"))}</p>`}</div>`;
    }
    case "start": {
      if (!ready("registration")) return `${pageTitle("start")}<div class="card">${comingSoon(t("page_start"), t, statePic("coming_soon"), S.notified.has("registration"))}</div>`;
      const a = S.app;
      if (!a) return `${pageTitle("start")}<div class="card"><p class="muted">${esc(t("start_intro"))}</p><div class="actions"><button class="primary" data-act="start:begin">${icon("ui-bolt")}<span>${esc(t("start_begin"))}</span></button></div></div>`;
      const stepRows = REGISTRATION_STEPS.map((st) => kv(esc(t(`start_step_${st}`)), a.steps[st] ? ok(t("done")) : off(t("not_yet")), a.status === "started" && !a.steps[st] ? `<button class="secondary" data-act="start:step:${st}">${esc(t("done"))}</button>` : ""));
      const foot = a.status === "started" ? `<div class="actions"><button class="primary" data-act="start:submit" ${canSubmit(a.steps) ? "" : "disabled"}>${esc(t("start_submit"))}</button></div>`
        : a.status === "submitted" ? `${wait(t("start_submitted"))}<div class="actions"><button class="secondary" data-act="start:poll">${esc(t("continue"))}</button></div>` : ok(t("start_approved", { lynkoid: a.lynkoid ?? "" }));
      return `${pageTitle("start")}<div class="card">${rows(stepRows)}${foot}<p class="muted">${esc(t("start_not_before"))}</p></div>`;
    }
  }
  return "";
}

function overlay(): string {
  const wrap = (cls: string, inner: string) => `<div class="overlay ${cls}" data-act="closeoverlay">${inner.replace(/^<(div|aside)/, '<$1 data-act="keep"')}</div>`;
  switch (S.overlay) {
    case "launcher": return wrap("", launcher(pack().services.map((s) => ({ id: s.id ?? s.service, name: s.name, plain: t(`ft_plain_${s.plain}`), icon: s.icon, href: s.href ?? `/${s.service}`, state: S.realUser ? s.state : "available" })), t, icon));
    case "pages": return wrap("", launcher(PAGES.map((p) => ({ id: `page-${p}`, name: t(`page_${p}`), icon: PAGE_ICON[p], href: pagePath(p), state: "available" as const })), t, icon));
    case "account": return wrap("end", accountMenu({ name: t("person_name"), lynkId: LYNKID, businesses: [{ id: "b1", name: t("shop_name"), current: true }, { id: "b2", name: t("client_pharmacy"), current: false }], role: "owner", roles: ["owner", "manager"], theme: S.mode === "lite" ? "lite" : S.mode === "sunlight" ? "sunlight" : S.theme, language: langName(isTest() ? "en" : S.lang), region: pack().sample ? t("sample_country") : pack().name, view: { name: t(IFACE_NAME[S.choice?.interface ?? "universal"] ?? "iface_universal") },
      links: [{ act: "go:storefront", label: t("page_storefront"), icon: "ui-cart" }, { act: "go:support", label: t("support_seller"), icon: "ui-info" }, { act: "go:trips", label: t("page_trips"), icon: "ui-globe" }, { act: "go:collect", label: t("page_collect"), icon: "ui-qr" }, { act: "go:messages", label: t("page_messages"), icon: "product-chat" }, { act: "go:assist", label: t("page_assist"), icon: "product-assist" }, { act: "lock:start", label: t("lock_title"), icon: "ui-lock" }] }, t, icon));
    case "view": return wrap("", viewSheet({ current: S.choice?.interface ?? "universal", rule: S.choice?.rule ?? "safe_default", options: [...VIEWS], ownerOnly: false, canChange: true }, t, icon));
    case "globe": return wrap("", globeSheet(Object.entries(PACKS).map(([code, p]) => ({ code, native: p.native, dir: p.dir })), DATA.packOrder.map((c) => ({ code: c, name: (DATA.packs[c] as CountryPack).sample ? t("sample_country") : regionName(c, isTest() ? "en" : S.lang, (DATA.packs[c] as CountryPack).name) })), { language: isTest() ? "en" : S.lang, region: pack().code }, t));
    case "cmd": {
      const index: Entry[] = [...PAGES.map((p): Entry => ({ id: p, kind: "setting", title: t(`page_${p}`), act: `go:${p}` })), { id: "h1", kind: "help", title: t("help_article_1"), act: "shell:help" }, { id: "h2", kind: "help", title: t("help_article_2"), act: "shell:help" }, { id: "a1", kind: "action", title: t("sign_out_everywhere"), act: "session:all" }, { id: "a2", kind: "action", title: t("support_seller"), act: "support:external" }, { id: "h3", kind: "help", title: t("help_storefront"), act: "shell:help" }, { id: "v1", kind: "setting", title: t("change_view"), act: "shell:view" }, { id: "a3", kind: "action", title: t("lock_title"), act: "lock:start" }];
      return wrap("", commandBar(S.query, search(index, S.query), t, icon));
    }
    case "help": return wrap("end", helpPanel(t(`page_${signedIn() ? (S.screen as Page) : "security"}`), [...(S.screen === "storefront" || S.screen === "support" ? [{ id: "3", title: t("help_storefront"), href: "/faq/storefront/start" }] : []), ...(S.screen === "security" || S.screen === "messages" || S.screen === "assist" || S.screen === "notifications" ? [{ id: "4", title: t("lock_title"), href: "/faq/account/lock-everything" }, { id: "5", title: t("page_messages"), href: "/faq/account/messages" }, { id: "6", title: t("page_assist"), href: "/faq/assist/history" }] : []), { id: "1", title: t("help_article_1"), href: "/faq/account/recovery" }, { id: "2", title: t("help_article_2"), href: "/faq/account/passkeys" }], t, icon,
      askBox({ query: S.ask, results: S.ask ? lookup(knowledge(), S.ask) : [], online: S.link !== "offline", builtOn: dateOf(T_NOW()) }, t, icon)));
    case "bell": {
      const present = AREAS.filter((a) => S.lines.some((l) => MESSAGES.kinds[l.kind]?.area === a)).map((a) => ({ id: a, label: t(`ntf_area_${a}`) }));
      return wrap("end", bell(shownLines(), { filter: S.bellFilter, lastOpened: S.lastOpened, areas: present }, t, icon, (ms) => clock(ms)));
    }
    case "why": { const l = shownLines().find((x) => x.nid === S.whyNid); return l ? wrap("", whySheet(l, t, icon)) : ""; }
    case "sync": return wrap("bottom", syncSheet(sync(), t, icon, clock));
    case "stepup": return wrap("", `<div class="sheet" role="dialog" aria-labelledby="suT"><h2 id="suT">${esc(t("stepup_needed"))}</h2><p class="muted">${esc(t("stepup_hint"))}</p><div class="field"><label for="suCode">${esc(t("code_label"))}</label><input class="text" id="suCode" inputmode="numeric" value="771204"></div><button class="primary" data-act="stepup:ok">${esc(t("confirm"))}</button><button class="secondary" data-act="closeoverlay">${esc(t("cancel"))}</button></div>`);
    default: return "";
  }
}

let lastOverlay: Overlay = null;
function draw(): void {
  if (lastOverlay === "bell" && S.overlay !== "bell" && S.overlay !== "why") S.lastOpened = Date.now();   // New becomes Earlier once the bell was seen
  if (S.overlay === "bell") S.lines.forEach((l) => { l.seen = true; });
  lastOverlay = S.overlay;
  S.choice = choose(); S.size = SIZE_OF_CLASS[S.choice.class] ?? "computer";
  const d = $("#display");
  d.dataset["deviceClass"] = S.choice.class; d.dataset["interface"] = S.choice.interface;      // type scale and focus rules per device (design tokens)
  d.className = `display ${S.theme}`;
  if (S.mode) d.setAttribute("data-mode", S.mode); else d.removeAttribute("data-mode");
  d.lang = S.lang === "xx-rtl" ? "ar" : S.lang === "xx" ? "en" : S.lang;
  d.dir = S.lang === "xx-rtl" ? "rtl" : S.lang === "xx" ? "ltr" : PACKS[S.lang]?.dir ?? "ltr";
  const logo = brandMark(DATA.brand.places, "web-header", S.theme === "dark", "brandfill", HEADER_ROOM[S.size]);
  const items = signedIn() ? navItems() : [];
  const head = header({ logo, nav: items, notifications: signedIn() ? S.lines.filter((l) => !l.read && MESSAGES.priorities[MESSAGES.kinds[l.kind]?.priority ?? "low"]?.raises_count).length : 0, signedIn: signedIn(), title: S.size === "computer" ? undefined : t("site_short"), surface: "app" }, S.size, t, icon);
  const nav = signedIn() ? navigation(items, S.size, t, icon) : "";
  const toasts = S.undo.openToasts(Date.now()).map((u) => undoToast(u, Date.now(), t, icon)).join("");
  d.innerHTML = `<div class="shell">${head}<div class="shell-body">${S.size === "phone" ? "" : nav}<main class="shell-main" id="main">${crumbs()}${page()}<div class="footer-line">${esc(S.realUser ? "" : t("sandbox"))} <span class="deeplink">account.lynkomni.com${esc(screenPath())}</span></div>${appFooter()}</main></div>${S.size === "phone" ? nav : ""}${overlay()}<div class="toasts">${toasts}</div></div>`;
  $("#device").className = `device ${S.size}`;
  $("#tab").className = `tab ${S.theme}`;                       // the tab and its icon follow the page theme (brand surface "favicon")
  $("#url").textContent = `https://account.lynkomni.com${screenPath()}`;
  $("#tabTitle").textContent = t("site_title");
  $("#screensHint").textContent = t("screens_hint");
  document.querySelectorAll<HTMLElement>("#stateButtons button").forEach((b) => b.classList.toggle("on", b.dataset["state"] === S.screen));
}
function drawLog(): void {
  const box = $("#log");
  const chip = (s: UserState) => `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`;
  box.innerHTML = S.events.slice(0, 40).map((e) => `<li><span class="n">#${e.n}</span><code>${esc(e.type)}</code><span class="org">${e.origin}</span>${chip(e.sync)}</li>`).join("") || `<li class="empty">No events yet. Try the page.</li>`;
}

/** Text from the page never carries HTML characters into state; a choice is only ever one of the known values. */
const plain = (s: string): string => s.replace(/[<>"'&]/g, "");
const pick = <V extends string>(allowed: readonly V[], value: string, fallback: V): V => allowed.find((x) => x === value) ?? fallback;
const stepUp = (then: string): void => { S.stepup = { ok: false, then }; S.overlay = "stepup"; draw(); };
function act(a: string): void {
  const [k, v = ""] = plain(a).split(/:(.*)/s);
  const now = T_NOW();
  switch (k) {
    case "keep": return;
    case "closeoverlay": case "closesheet": S.overlay = null; draw(); return;
    case "shell": {
      const map: Record<string, Overlay> = { launcher: "launcher", account: "account", globe: "globe", search: "cmd", help: "help", bell: "bell", sync: "sync", menu: "launcher" };
      if (v === "theme") { S.theme = S.theme === "dark" ? "light" : "dark"; $<HTMLInputElement>("#cDark").checked = S.theme === "dark"; S.overlay = null; draw(); return; }
      if (v === "signout") { S.screen = "signin"; S.overlay = null; record("SessionRevoked", "server", { by: "self" }); draw(); return; }
      if (v === "signin") { S.screen = "signin"; S.overlay = null; draw(); return; }
      if (v === "voice") { S.overlay = null; draw(); return; }
      if (v === "view" || v === "why") { S.overlay = "view"; draw(); if (v === "why") $("#whyView")?.focus(); return; }
      S.overlay = S.overlay === map[v] ? null : (map[v] ?? null); S.query = ""; draw();
      if (S.overlay === "cmd") $<HTMLInputElement>("#cmdIn")?.focus();
      return;
    }
    case "nav": { if (v === "more") { S.overlay = S.overlay === "pages" ? null : "pages"; draw(); return; } S.screen = pick(SCREENS, v, S.screen); S.overlay = null; draw(); return; }
    case "go": S.screen = pick(SCREENS, v, S.screen); S.overlay = null; if (v === "recover") S.recover = { otherDevice: null, hasCode: null, started: null }; draw(); return;
    case "place": { const p = v.replace(/^page-/, ""); if (v.startsWith("page-")) S.screen = pick(SCREENS, p, S.screen); S.overlay = null; draw(); return; }
    case "lang": S.lang = pick(Object.keys(PACKS), v, S.lang); $<HTMLSelectElement>("#cLang").value = S.lang; S.overlay = null; draw(); return;
    case "view": S.override = v === "auto" ? null : (VIEWS as readonly string[]).includes(v) ? v : null; S.overlay = null; draw(); record("InterfaceChosen", "device", { interface: S.choice?.interface, rule: S.choice?.rule }); return;
    case "support": {
      if (v !== "internal" && v !== "external") { S.overlay = null; record("AccountAction", "device", { action: a }); draw(); return; }
      const ref = SAMPLE_CASES[S.cases.length % SAMPLE_CASES.length] as string;
      S.cases.unshift({ side: v, ref }); S.screen = "support"; S.overlay = null;
      record("SupportCaseOpened", S.link === "offline" ? "device" : "server", { case: ref, side: v, channel: v === "external" ? "seller_support" : "support" }); draw(); return;
    }
    case "att": {
      const [what = "", x = ""] = v.split(":");
      if (what === "code") S.att = "code_sent";
      else if (what === "open") S.att = "open";
      else if (what === "show") { S.attShow = S.attShow === x ? "" : (x === "pin" ? "pin" : "idcn"); if (S.attShow === "pin") record("AttendancePinShown", "server", { member_id: SAMPLE_MEMBER, by: SAMPLE_MEMBER }); }
      else if (what === "req" && (x === "delete_my_details" || x === "dispute")) { S.attRequest = { kind: x, at: now }; record("AttendanceRequestRaised", "server", { member_id: SAMPLE_MEMBER, request_id: SAMPLE_MEMBER, kind: x }); }
      else if (what === "proof") record("AccountAction", "device", { action: "proof_of_attendance" });
      draw(); return;
    }
    case "tk": {
      if (v === "late" && !S.tkLate) { S.tkLate = true; record("TicketRunningLate", "server", { ticket_id: SAMPLE_MEMBER }); }
      if (v === "leave") { S.tkLeft = true; record("TicketLeft", "server", { ticket_id: SAMPLE_MEMBER }); }
      draw(); return;
    }
    case "ans": {
      const [what = "", x = ""] = v.split(":");
      if (what === "del") { S.answers = S.answers.filter((y) => y !== x); record("SurveyAnswerDeleted", "server", { answer_id: SAMPLE_MEMBER }); }
      if (what === "stop" && !S.optOut.includes(x)) { S.optOut.push(x); record("SurveyOptOut", "server", { organisation_id: SAMPLE_MEMBER }); }
      draw(); return;
    }
    case "panel": {
      S.panel = v === "join"; record("PanelMembership", "server", { member_ref: SAMPLE_MEMBER, state: S.panel ? "joined" : "left" }); draw(); return;
    }
    case "share": {
      const [what, x] = [v.split(":")[0], v.split(":").slice(1).join(":")];
      if (what === "start" && (x === "live" || x === "trips" || x === "zones")) { const id = `share-${S.shares.length + 1}`; S.shares.push({ id, scope: x, until: now + 3 * 3600 }); record("LocationShareStarted", "device", { share_id: id, scope: x, ends_at: now + 3 * 3600 }); }
      if (what === "stop") { S.shares = S.shares.filter((y) => y.id !== x); record("LocationShareEnded", "device", { share_id: x, reason: "stopped" }); }
      draw(); return;
    }
    case "pass": S.passWindow += 1; draw(); return;
    case "idcheck": {
      if (v === "start" && !S.idCheck) { S.idCheck = "sent"; record("IdentityCheckRequested", "device", { purpose: "first_paid_offer", partner: "sandbox" }); }
      if (v === "poll" && S.idCheck === "sent" && S.link !== "offline") { S.idCheck = "confirmed"; record("IdentityCheckConfirmed", "server", { lover: SAMPLE_LOVER, by: "partner" }); }
      draw(); return;
    }
    case "plan": if (v === "set") { S.plan = { due: now + 2 * 3600, checked: false }; record("TripPlanSet", "device", { due_at: S.plan.due, contacts: 1 }); draw(); return; }
      if (v === "checkin" && S.plan) { S.plan.checked = true; record("TripPlanCheckedIn", "device", {}); draw(); return; }
      S.overlay = null; record("AccountAction", "device", { action: a }); draw(); return;
    case "business": case "role": case "region": case "open": case "notice": case "help": case "copy": case "edit": S.overlay = null; record("AccountAction", "device", { action: a }); draw(); return;
    case "signin": {
      const dev = v === "other" ? "device_unknown" : "device_phone";
      const alert = signInAlertNeeded(S.seenDevices, dev, "sample_city");
      S.sessions.unshift({ tail: Math.random().toString(16).slice(2, 6), site: "account", device: dev, place: "sample_city", at: now });
      secEvent("SessionStarted"); if (alert.alert) { secEvent("SecurityAlertSent"); S.secEvents[0]!.type = "SecurityAlertSent"; }
      if (alert.alert) { S.coolOffUntil = now + coolOffSeconds(S.advanced); record("CoolOffStarted", "server", { until: S.coolOffUntil }); tell("cool_off_started", "cooloff_title"); }
      S.screen = "overview"; draw(); return;
    }
    case "username": S.username = v; S.cloud = S.link === "offline" ? "checking" : v === "mamas.kitchen" ? "taken" : v.length >= 3 ? "available" : null; draw(); return;
    case "signup": {
      if (v.startsWith("way:")) { S.signupWay = v === "way:email" ? "email" : "phone"; draw(); return; }
      if (v === "username" && S.cloud === "available") S.signUp.username = S.username;
      if (v === "contact") S.signUp.contactVerified = true;
      if (v === "passkey") { S.signUp.passkey = true; secEvent("PasskeyEnrolled"); }
      if (v === "code") { S.signUp.recoveryCodeConfirmed = true; record("AccountCreated", "server", { lynkid: LYNKID, username: S.signUp.username }); }
      draw(); return;
    }
    case "recover": {
      const [q, ans] = v.split(":");
      if (q === "device") S.recover.otherDevice = ans === "yes";
      if (q === "code") S.recover.hasCode = ans === "yes";
      if (q === "start") { const path = pick(["device", "code", "assisted"] as RecoveryPath[], ans ?? "", recoveryPath({ otherDevice: !!S.recover.otherDevice, recoveryCode: !!S.recover.hasCode, smsOk: true })); S.recover.started = { path, startedAt: now, approvals: 0 }; secEvent("RecoveryStarted"); if (path === "device") { S.restrictedUntil = now + DAY; secEvent("RecoveryCompleted"); } }
      if (q === "cancel" && S.recover.started) { S.recover.started = null; S.recover = { otherDevice: null, hasCode: null, started: null }; secEvent("RecoveryCancelled"); }
      draw(); return;
    }
    case "passkey": {
      if (v === "add") { S.passkeys.push({ locrd: SAMPLE_CRD[Math.min(S.passkeys.length, SAMPLE_CRD.length - 1)] as string, device: t("device_n", { n: S.passkeys.length + 1 }), at: now, here: false }); secEvent("PasskeyEnrolled"); draw(); return; }
      const locrd = v.replace(/^remove:/, "");
      if (S.passkeys.length <= (S.advanced ? 2 : 1)) { draw(); return; }                              // advanced protection keeps two passkeys
      S.held = holds("remove_passkey"); if (S.held) { record("SensitiveActHeld", "server", { act: "remove_passkey", why: S.held }); draw(); return; }
      if (!S.stepup?.ok) { stepUp(a); return; }
      S.passkeys = S.passkeys.filter((p) => p.locrd !== locrd); S.stepup = null; secEvent("PasskeyRevoked"); draw(); return;
    }
    case "session": {
      if (v === "all") { S.sessions = []; secEvent("SessionRevoked"); S.screen = "signin"; draw(); return; }
      const tail = v.replace(/^revoke:/, ""); S.sessions = S.sessions.filter((s) => s.tail !== tail); secEvent("SessionRevoked"); draw(); return;
    }
    case "recovery": if (v === "newcode") { stepUp(a); } return;
    case "consent": { const i = Number(v.replace(/^withdraw:/, "")); const c = S.consents[i]; if (c) { c.withdrawn = now; secEvent("ConsentWithdrawn"); } draw(); return; }
    case "stepup": {
      if (v === "ok") { const then = S.stepup?.then ?? ""; S.stepup = { ok: true, then }; S.overlay = null; record("StepUpPassed", "server", { scope: "sensitive" });
        if (/^(lock|adv|contact|merge|assistc):/.test(then)) { act(then); return; } if (then.startsWith("passkey:")) act(then); else if (then === "close") { S.closing = closesAt(now); record("AccountCloseRequested", "server", { closes_at: S.closing }); } else if (then === "recovery:newcode") { S.recoveryCode = "2B8N-4KQ7-M1XZ-9RCD"; record("RecoveryCodeRotated", "server", {}); } S.stepup = null; draw(); return; }
      stepUp(v); return;
    }
    case "ws": if (v === "person" || v === "company" || v === "organisation") { S.workspaces.push({ entity: v }); record("BusinessCreated", "server", { entity: v, kind: v === "person" ? "household" : v === "company" ? "business" : "nonprofit", type: v === "company" ? "shop" : "no_till" }); } draw(); return;
    case "data": S.held = holds("data_export"); if (S.held) { record("SensitiveActHeld", "server", { act: "data_export", why: S.held }); draw(); return; } S.dataRequest = { due: dataRequestDue(now) }; record("DataRequestOpened", "server", { due_at: S.dataRequest.due }); TRK.apply({ type: "DataRequestOpened", payload: { request_id: "data-1", due_at: new Date(S.dataRequest.due * 1000).toISOString().slice(0, 19) + "Z" }, at: now }, "account");
       draw(); return;
    case "close": if (v === "cancel") { S.closing = null; record("AccountCloseCancelled", "server", {}); } draw(); return;
    case "toggle": if (v === "adult") { S.signUp.adult = !S.signUp.adult; draw(); return; }
      if (v === "wty") { S.wasThisYou = !S.wasThisYou; record("NotificationChoiceChanged", "server", { choice: "attend_was_this_you", on: S.wasThisYou }); draw(); return; }
      if (v.startsWith("grid:")) { const key = v.slice(5); S.nset.off = S.nset.off.includes(key) ? S.nset.off.filter((y) => y !== key) : [...S.nset.off, key]; record("NotificationChoiceChanged", "server", { choice: key, on: !S.nset.off.includes(key) }); draw(); return; }
      if (v.startsWith("biz:")) { const b = v.slice(4); S.nset.muted = S.nset.muted.includes(b) ? S.nset.muted.filter((y) => y !== b) : [...S.nset.muted, b]; record("NotificationChoiceChanged", "server", { business: b, muted: S.nset.muted.includes(b) }); draw(); return; }
      if (v === "pause" || v === "dnd" || v === "summary") { const key = v === "pause" ? "paused" : v; S.nset[key] = !S.nset[key]; record("NotificationChoiceChanged", "server", { [key]: S.nset[key] }); draw(); return; } if (v === "mkemail") S.marketing.email = !S.marketing.email; if (v === "mkpush") S.marketing.push = !S.marketing.push; record("MarketingChoiceChanged", "server", { ...S.marketing }); draw(); return;
    case "standing": { const i = Number(v.replace(/^revoke:/, "")); const s = S.standing[i]; if (s) { s.active = false; record("StandingPaymentRevoked", "server", { losub: s.losub, by: "self" }); } draw(); return; }
    case "start": {
      if (v === "begin") { S.app = { status: "started", steps: { profile: false, registration: false, tax_number: false, bank_account: false } }; record("RegistrationStarted", "server", { country: pack().code }); }
      else if (v.startsWith("step:")) { const st = pick(REGISTRATION_STEPS, v.slice(5), "profile"); if (S.app) S.app.steps[st] = true; }
      else if (v === "submit" && S.app && canSubmit(S.app.steps)) { S.app.status = "submitted"; record("RegistrationSubmitted", "server", { gateway: "registration_gateway" }); }
      else if (v === "poll" && S.app) { S.app.status = applicationStatus(S.app.status, "approved"); S.app.lynkoid = "LOOID-2026-1108-0005"; record("RegistrationApproved", "server", { lynkoid: S.app.lynkoid }); }
      draw(); return;
    }
    case "leave": draw(); return;                                                                    // the last owner cannot leave (note on the page)
    case "ntf": {
      const [what = "", nid = "", extra = ""] = v.split(":");
      const l = S.lines.find((x) => x.nid === nid);
      if (what === "filter") { S.bellFilter = nid; draw(); return; }
      if (what === "allread") { S.lines.forEach((x) => { x.read = true; }); record("NotificationsRead", "device", { all: true, at: now }); draw(); return; }   // read on one device is read on every device (services/messages.py)
      if (!l) return;
      if (what === "read") { l.read = !l.read; record(l.read ? "NotificationRead" : "NotificationUnread", "device", { nid }); }
      if (what === "open") { l.read = true; S.overlay = null; S.screen = MESSAGES.kinds[l.kind]?.area === "security" ? "security" : "notifications"; record("NotificationOpened", "device", { nid, kind: l.kind }); }
      if (what === "why") { S.whyNid = nid; S.overlay = "why"; }
      if (what === "ack") { l.acknowledged = true; l.read = true; record("NotificationAcknowledged", "device", { nid, kind: l.kind }); }
      if (what === "act") {
        l.read = true; record("NotificationActed", "device", { nid, kind: l.kind, action: extra });
        if (extra === "this_was_not_me") { S.overlay = null; S.screen = "security"; doLock("not_me"); }
        if (extra === "cancel_change") { S.contactChange = null; record("ContactChangeCancelled", "server", { by: "old_contact" }); }
        if (extra === "done" || extra === "snooze") act(`nset:${extra}:${S.nset.reminders[0]?.id ?? ""}`);
      }
      draw(); return;
    }
    case "notme": S.screen = "security"; doLock("not_me"); draw(); return;
    case "lock": {
      if (v === "start" && !S.locked) { if (!fresh("lock:start")) return; doLock("in_person"); S.screen = "security"; S.overlay = null; }
      if (v === "undo" && S.locked) { if (!fresh("lock:undo")) return; S.locked = false; record("EverythingUnlocked", "server", { verified: true }); }
      draw(); return;
    }
    case "adv": {
      if (v === "on" && S.passkeys.length >= 2) { if (!fresh("adv:on")) return; S.advanced = true; record("AdvancedProtectionTurnedOn", "server", { passkeys: S.passkeys.length }); }
      if (v === "off") { if (!fresh("adv:off")) return; S.advanced = false; record("AdvancedProtectionTurnedOff", "server", {}); }
      draw(); return;
    }
    case "contact": {
      if (v === "start") { if (holds("contact_change")) { S.held = holds("contact_change"); record("SensitiveActHeld", "server", { act: "contact_change", why: S.held }); draw(); return; } if (!fresh("contact:start")) return;
        S.contactChange = { until: now + contactWaitSeconds(S.advanced) }; record("ContactChangeRequested", "server", { kind: "phone", applies_at: S.contactChange.until }); tell("contact_change_requested", "contact_title"); }
      if (v === "cancel" && S.contactChange) { S.contactChange = null; record("ContactChangeCancelled", "server", { by: "owner" }); }
      draw(); return;
    }
    case "merge": if (!fresh("merge:do")) return; S.merged = 3; record("ProvisionalAccountConfirmed", "server", { into: "existing", records: 3 }); draw(); return;
    case "nset": {
      const [what = "", x = ""] = v.split(":");
      if (what === "lock") S.nset.lock = pick(["neutral", "full", "none"] as const, x, S.nset.lock);
      if (what === "deputy") { S.nset.deputy = now + 14 * DAY; record("DeputyNamed", "server", { role: "manager", until: S.nset.deputy, personal_areas_stay: true }); }
      if (what === "enddeputy") { S.nset.deputy = null; record("DeputyEnded", "server", {}); }
      if (what === "test") { S.nset.tested = true; record("NotificationTestSent", "server", { channels: ["push", "email", "text", "bell"] }); }
      if (what === "health") S.nset.health = true;
      if (what === "remind") { const id = `r${S.nset.reminders.length + 1}`; S.nset.reminders.push({ id, at: now + DAY }); record("ReminderSet", "device", { reminder: id, due_at: now + DAY }); tell("personal_reminder", "remind_sample"); }
      if (what === "snooze") { const r = S.nset.reminders.find((y) => y.id === x); if (r) { r.at += 3600; record("ReminderSet", "device", { reminder: x, due_at: r.at, snoozed: true }); } }
      if (what === "done") { S.nset.reminders = S.nset.reminders.filter((y) => y.id !== x); record("ReminderCleared", "device", { reminder: x }); }
      draw(); return;
    }
    case "assistc": {
      if (v === "checked") { S.stepup = null; S.assistFresh = true; draw(); return; }
      S.pendingAssist = v in ASSIST_DEMO ? v : null; S.assistFresh = false; S.screen = "assist"; S.overlay = null; draw(); return;
    }
    case "assist": {
      const id = S.pendingAssist;
      if (v === "check" && id) { if (fresh("assistc:checked")) { S.assistFresh = true; draw(); } return; }
      if ((v === "confirm" || v === "deny") && id) {
        const d = decide(id, { role: "person", fresh_check: S.assistFresh, confirmed: v === "confirm" });
        const entry = { id: `h${S.history.length + 1}`, action: id, ran: v === "confirm" && d.run, why: v === "deny" ? "as_deny" : d.why, at: Date.now(), undone: false, was: S.lang };
        S.history.unshift(entry); S.pendingAssist = null; S.assistFresh = false;
        if (entry.ran && id === "change_language") S.lang = S.lang === "fr" ? "en" : "fr";
        if (entry.ran && id === "lock_everything") doLock("assist");
        record("AssistActionRecorded", "server", { action: id, class: d.class, needs: d.needs, ran: entry.ran });
        draw(); return;
      }
      if (v === "undo") { const h = S.history[0]; if (h && h.ran && !h.undone && h.action === "change_language" && Date.now() - h.at < 30_000) { S.lang = h.was ?? "en"; h.undone = true; record("AssistActionUndone", "device", { action: h.action }); } draw(); return; }
      if (v === "why") { S.overlay = "help"; draw(); return; }
      S.overlay = null; record("AccountAction", "device", { action: a }); draw(); return;
    }
    case "notify": S.notified.add(v); record("NotifyMeSubscribed", "device", { service: v }); draw(); return;
    case "payout": { const r = payoutChange(v === "second", now); S.payout = r; record(r.status === "applied" ? "PayoutChangeApplied" : "PayoutChangeRequested", "server", r); draw(); return; }
    case "undo": { const r = S.undo.undo(v, Date.now()); record("AutomationUndone", "device", { id: v, result: r }); draw(); return; }
    case "sync": if (S.link !== "offline") { S.lastSync = Date.now(); S.events.forEach((e) => { if (e.sync === "queued") e.sync = "sent"; }); S.pending = 0; record("SyncCompleted", "server", {}); } S.overlay = null; draw(); return;
  }
}

function init(): void {
  const bind = (sel: string, fn: (el: HTMLInputElement) => void) => $<HTMLInputElement>(sel).addEventListener("change", (e) => fn(e.target as HTMLInputElement));
  bind("#cSize", (el) => { S.testSize = pick(["auto", "computer", "tablet", "phone"], el.value, S.testSize); S.overlay = null; draw(); });
  bind("#cLink", (el) => { S.link = pick(["good", "weak", "offline"] as Link[], el.value, S.link); draw(); });
  bind("#cDark", (el) => { S.theme = el.checked ? "dark" : "light"; draw(); });
  bind("#cMode", (el) => { S.mode = pick(["", "lite", "sunlight"] as ("" | "lite" | "sunlight")[], el.value, S.mode); draw(); });
  bind("#cReal", (el) => { S.realUser = el.checked; draw(); });
  const country = $<HTMLSelectElement>("#cCountry");
  country.innerHTML = DATA.packOrder.map((c) => { const p = DATA.packs[c] as CountryPack; return `<option value="${esc(c)}">${esc(p.sample ? t("sample_country") : p.name)}</option>`; }).join("");
  country.addEventListener("change", (e) => { S.country = pick(DATA.packOrder, (e.target as HTMLSelectElement).value, S.country); draw(); });
  const sel = $<HTMLSelectElement>("#cLang");
  sel.insertAdjacentHTML("afterbegin", Object.entries(PACKS).map(([code, p]) => `<option value="${esc(code)}" lang="${esc(code)}" dir="${p.dir}">${esc(p.native)}</option>`).join(""));
  sel.value = "en";
  sel.addEventListener("change", (e) => { S.lang = pick(Object.keys(PACKS).concat(["xx", "xx-rtl"]), (e.target as HTMLSelectElement).value, S.lang); draw(); });
  $("#stateButtons").innerHTML = SCREENS.map((k) => `<button type="button" data-state="${k}">${esc(k === "signin" ? "Sign in" : k === "signup" ? "Sign up" : k === "recover" ? "Recover" : k)}</button>`).join("");
  $("#stateButtons").addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest<HTMLElement>("button[data-state]"); if (b) { const picked = SCREENS.find((k) => k === b.dataset["state"]); if (picked) { S.screen = picked; S.overlay = null; if (picked === "recover") S.recover = { otherDevice: null, hasCode: null, started: null }; if (picked === "signup") { S.signUp = {}; S.username = ""; S.cloud = null; } draw(); } } });
  $("#display").addEventListener("click", (e) => {
    const el = (e.target as HTMLElement).closest<HTMLElement>("[data-act]");
    if (!el) return;
    if (el.tagName === "A") e.preventDefault();
    if (el.tagName === "INPUT") return;                                       // switches act on change, not click
    if (el.dataset["act"] === "closeoverlay" && e.target !== el && !(el.tagName === "BUTTON")) return;
    act(el.dataset["act"]!);
  });
  $("#display").addEventListener("input", (e) => {
    const el = e.target as HTMLInputElement;
    if (el.dataset["filter"] === "regions") { const list = $("#regionList"); if (list) filterRegions(list, el.value); return; }
    if (el.id === "cmdIn") { S.query = plain(el.value); const list = $("#cmdList"); const index = overlay(); const m = /<ul id="cmdList"[^>]*>([\s\S]*?)<\/ul>/.exec(index); if (list && m) list.innerHTML = m[1]!; }
    if (el.id === "usernameIn") { act(`username:${el.value}`); const inp = $<HTMLInputElement>("#usernameIn"); inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); }
  });
  $("#display").addEventListener("change", (e) => { const el = e.target as HTMLInputElement; if (el.dataset["act"]?.startsWith("toggle:")) act(el.dataset["act"]); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && !(e.target as HTMLElement).matches("input,select,textarea")) { e.preventDefault(); act("shell:search"); }
    if (e.key === "Escape" && S.overlay) { S.overlay = null; draw(); return; }
    const group = (document.activeElement as HTMLElement | null)?.closest<HTMLElement>(".shell-nav, .lgrid, .choices");
    if (group) arrowNav(e, group, $("#display").dir === "rtl");                   // keyboard, remote and switch access move inside a group
  });
  gestures($("#display"), {
    edgeSwipe: () => { if (!S.overlay && signedIn()) act("shell:launcher"); },
    swipeDown: (el) => { if (S.overlay && el.closest(".overlay")) { S.overlay = null; draw(); } },
    longPress: (el) => { if (el.closest(".navitem")) { S.overlay = "help"; draw(); } },
  }, () => $("#display").dir === "rtl");
  const fit = () => { const w = $("#rig").clientWidth - 8, dev = { computer: 1280, tablet: 800, phone: 390 }[S.size] ?? 1280; document.documentElement.style.setProperty("--fit", String(Math.min(1, w / dev))); };
  new ResizeObserver(fit).observe($("#rig")); fit();
  bind("#cSize", () => fit());
  window.setInterval(() => { if (S.undo.openToasts(Date.now()).length || $(".toasts").children.length) draw(); }, 1000);
  draw(); drawLog();
}
init();
