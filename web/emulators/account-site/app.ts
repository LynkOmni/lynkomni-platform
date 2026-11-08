/* LynkOmni Account (account.lynkomni.com) in a browser window and on a phone (build section 2). Every part of the frame comes
 * from ts/src/shell.ts and every rule from ts/src/account.ts; this file holds the sample person, the screens and the event log.
 * Words come from web/shell/strings.en.json (the shell) and strings.en.json (this site) and their language packs. */
import { STATE_PICTURE, Undo, accountMenu, commandBar, connectionChip, deliverNow, esc, globeSheet, header, helpPanel, launcher, maskId, navigation, notificationsPanel, search, state, comingSoon, syncSheet, translator, undoToast, usernameField } from "../../../ts/src/shell.js";
import type { AddressMap, Entry, Icon, Link, NavItem, Notice, Pic, StateKind, SyncInfo, T, UsernameStatus, Viewport } from "../../../ts/src/shell.js";
import { DAY, PAGES, RECOVERY, REGISTRATION_STEPS, SECURITY_EVENT_KEY, SIGN_UP_STEPS, applicationStatus, canSubmit, closesAt, consentState, dataRequestDue, nextSignUpStep, pagePath, payoutChange, recoveryPath, recoveryReady, recoveryReadyAt, signInAlertNeeded } from "../../../ts/src/account.js";
import type { ApplicationStatus, Consent, Page, RecoveryPath, RegistrationStep, SignUpState } from "../../../ts/src/account.js";
import type { UserState } from "../../../ts/src/pos.js";

interface CountryPack { code: string; name: string; currency: string; tz: string; locale: string; sample: boolean; ready: Record<string, { ok: boolean; message: string }>; services: { service: string; name: string; icon: string; state: "available" | "coming_soon" }[] }
interface BuildData {
  icons: Record<string, string>;
  brand: { body: string; topLight: string; topDark: string; receipt: string };
  pictures: { offLight: string; offDark: string; offAlt: string };
  statePictures: Record<string, Record<"light" | "dark", { svg: string; alt: string; contrast?: string }>>;
  packs: Record<string, CountryPack>; packOrder: string[];
  addresses: AddressMap;
  i18n: Record<string, { native: string; dir: "ltr" | "rtl"; texts: Record<string, string> }>;
}
declare const DATA: BuildData;
interface Ev { n: number; type: string; origin: "device" | "server"; payload: unknown; sync: UserState; at: number }

const PACKS = DATA.i18n;
const EN: Record<string, string> = PACKS.en?.texts ?? {};
const TEST_LANGS = ["xx", "xx-rtl"];
type Overlay = null | "launcher" | "account" | "globe" | "cmd" | "help" | "bell" | "sync" | "stepup" | "pages";
type Screen = "signin" | "signup" | "recover" | Page;
const SCREENS: Screen[] = ["signin", "signup", "recover", ...PAGES];
const LYNKID = "LOID-4821-9035-7716";           // the sample person: illustrative, never an allocated identifier
const SHOP_OID = "LOOID-7351-2064-8912";
const T_NOW = (): number => Math.floor(Date.now() / 1000);

interface Standing { losub: string; merchant: string; cap: number; active: boolean }
const S = {
  size: "computer" as Viewport, lang: "en", theme: "light" as "light" | "dark", mode: "" as "" | "lite" | "sunlight", link: "good" as Link, country: "", realUser: false,
  screen: "overview" as Screen, overlay: null as Overlay, query: "", pending: 0, lastSync: null as number | null, events: [] as Ev[], undo: new Undo(), seen: new Set<string>(), notified: new Set<string>(),
  signUp: {} as SignUpState, username: "", cloud: null as UsernameStatus, recoveryCode: "7F3K-9Q2M-X81B-4TZC",
  recover: { otherDevice: null as boolean | null, hasCode: null as boolean | null, started: null as { path: RecoveryPath; startedAt: number; approvals: number; cancelled?: boolean } | null },
  passkeys: [{ locrd: "LOCRD-0001-0002-0003", device: "device_phone", at: T_NOW() - 40 * DAY, here: true }, { locrd: "LOCRD-0001-0002-0004", device: "device_laptop", at: T_NOW() - 12 * DAY, here: false }],
  sessions: [{ tail: "a1f3", site: "account", device: "device_phone", place: "sample_city", at: T_NOW() - 600 }, { tail: "9c0e", site: "merchant", device: "device_laptop", place: "sample_city", at: T_NOW() - 3 * 3600 }],
  seenDevices: [{ device: "device_phone", place: "sample_city" }, { device: "device_laptop", place: "sample_city" }],
  secEvents: [{ type: "SessionStarted", at: T_NOW() - 600 }, { type: "PasskeyEnrolled", at: T_NOW() - 12 * DAY }, { type: "ConsentGranted", at: T_NOW() - 20 * DAY }] as { type: string; at: number }[],
  consents: [{ scope: "accountant", grantee: "LOID-1100-2200-3300", purpose: "monthly books", expires: T_NOW() + 5 * DAY }] as Consent[],
  stepup: null as null | { ok: boolean; then: string },
  payout: null as null | { status: "applied" | "waiting"; readyAt: number },
  dataRequest: null as null | { due: number }, closing: null as null | number, marketing: { email: false, push: true },
  standing: [{ losub: "LOSUB-5100-0200-0031", merchant: "Blue Taxi", cap: 300000, active: true }] as Standing[],
  app: null as null | { status: ApplicationStatus; steps: Record<RegistrationStep, boolean>; lynkoid?: string },
  restrictedUntil: 0,
};
const $ = <T extends HTMLElement>(sel: string): T => document.querySelector(sel) as T;
const PSEUDO: Record<string, string> = { a: "à", c: "ç", e: "é", i: "î", n: "ñ", o: "ö", s: "š", u: "ü", y: "ý" };
const pseudo = (s: string): string => `[${s.replace(/[aceinosuy]/g, (c) => PSEUDO[c] ?? c)} ${"~".repeat(Math.max(1, Math.round(s.length * 0.4)))}]`;
const isTest = (): boolean => TEST_LANGS.includes(S.lang);
const t: T = (k, vars) => (isTest() ? pseudo(translator(EN)(k, vars)) : translator(PACKS[S.lang]?.texts ?? EN, EN)(k, vars));
const icon: Icon = (id, cls = "ic") => `<span class="${cls}" aria-hidden="true">${DATA.icons[id] ?? ""}</span>`;
const pack = (): CountryPack => DATA.packs[S.country] ?? (DATA.packs[DATA.packOrder[0] ?? ""] as CountryPack);
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
const secEvent = (type: string): void => { S.secEvents.unshift({ type, at: T_NOW() }); record(type, "server", { lynkid: LYNKID }); };

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
const PAGE_ICON: Record<Page, string> = { overview: "ui-home", profile: "ui-user", security: "ui-lock", businesses: "ui-grid", orders: "ui-cart", transactions: "ui-receipt", wallet: "ui-pay-wallet", billing: "ui-pay-card", memberships: "ui-check", privacy: "ui-doc", notifications: "ui-bell", support: "ui-info", payslips: "ui-doc", payments: "ui-pay-instant", start: "ui-bolt" };
const screenPath = (): string => (S.screen === "signin" ? "/sign-in" : S.screen === "signup" ? "/sign-up" : S.screen === "recover" ? "/recover" : pagePath(S.screen));
const sync = (): SyncInfo => ({ link: S.link, pending: S.pending, lastSync: S.lastSync, dataSaver: false, forcedOffline: false });
const statePic = (kind: StateKind): Pic | null => {
  const id = STATE_PICTURE[kind];
  if (!id || S.mode === "lite") return null;
  const p = DATA.statePictures[id]?.[S.mode === "sunlight" ? "light" : S.theme];
  return p ? { svg: S.mode === "sunlight" ? (p.contrast ?? p.svg) : p.svg, alt: p.alt } : null;
};
const title = (page: Page): string => `<div class="pagetitle"><h1>${esc(t(`page_${page}`))}</h1>${connectionChip(sync(), t, icon)}</div>`;
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
  if (step === "username") body = `<h2>${esc(t("step_username"))}</h2>${usernameField(S.username, S.cloud, (u) => u === "mamas.kitchen", t, icon)}<button class="primary" data-act="signup:username" ${S.cloud === "available" ? "" : "disabled"}>${esc(t("next"))}</button>`;
  else if (step === "contact") body = `<h2>${esc(t("step_contact"))}</h2><p class="muted">${esc(t("contact_hint"))}</p><div class="field"><label for="code">${esc(t("code_label"))}</label><input class="text" id="code" inputmode="numeric" value="482913"></div><button class="primary" data-act="signup:contact">${esc(t("next"))}</button>`;
  else if (step === "passkey") body = `<h2>${esc(t("step_passkey"))}</h2><p class="muted">${esc(t("passkey_hint"))}</p><button class="primary" data-act="signup:passkey">${icon("ui-lock")}<span>${esc(t("add_passkey"))}</span></button>`;
  else if (step === "recovery_code") body = `<h2>${esc(t("step_recovery_code"))}</h2><div class="codebox"><span>${esc(S.recoveryCode)}</span>${icon("ui-doc")}</div><div class="warn">${icon("ui-warning")}<span>${esc(t("recovery_code_hint"))}</span></div><button class="primary" data-act="signup:code">${esc(t("recovery_code_confirm"))}</button>`;
  else body = `<div class="okbox">${icon("ui-check")}<span>${esc(t("passkey_added"))}</span></div><div class="assist">${icon("ui-bolt")}<span><strong>${esc(t("assist_guide"))}:</strong> ${esc(t("recovery_code_push"))}</span></div><button class="primary" data-act="go:overview">${esc(t("continue"))}</button>`;
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
      return `${title("overview")}<div class="cards">
        <div class="card"><h2>${esc(t("overview_welcome", { name: t("person_name") }))}</h2><div class="muted">${esc(t("your_lynkid"))}</div><div class="lynkid-box"><span>${esc(maskId(LYNKID))}</span><button class="copy" data-act="copy:lynkid" aria-label="${esc(t("copy"))}">${icon("ui-copy")}</button></div></div>
        <div class="card"><h2>${esc(t("page_security"))}</h2>${todo ? wait(t("overview_security_todo")) : ok(t("overview_security_ok", { n: S.passkeys.length }))}<div class="actions"><button class="secondary" data-act="go:security">${esc(t("page_security"))}</button></div></div>
        <div class="card wide"><h2>${esc(t("shortcuts"))}</h2><div class="actions">${(["businesses", "wallet", "billing", "privacy", "payments", "start"] as Page[]).map((p) => `<button class="secondary" data-act="go:${p}">${icon(PAGE_ICON[p])}<span>${esc(t(`page_${p}`))}</span></button>`).join("")}</div></div>
      </div>`;
    }
    case "profile": return `${title("profile")}<div class="card">${rows([
      kv(esc(t("profile_name")), esc(t("person_name")), `<button class="secondary" data-act="edit:name">${esc(t("change"))}</button>`),
      kv(esc(t("profile_username")), "@grace.k", `<button class="secondary" data-act="edit:username">${esc(t("change"))}</button>`),
      kv(esc(t("profile_phone")), `•••• 0471 ${ok(t("verified"))}`), kv(esc(t("profile_email")), `g•••@example.org ${ok(t("verified"))}`),
      kv(esc(t("profile_language")), esc(langName(isTest() ? "en" : S.lang)), `<button class="secondary" data-act="shell:globe">${esc(t("change"))}</button>`),
      kv(esc(t("profile_region")), esc(pack().sample ? t("sample_country") : pack().name)), kv(esc(t("profile_timezone")), esc(pack().tz)),
    ])}<p class="muted">${esc(t("username_change_note"))}</p></div>`;
    case "security": return `${title("security")}<div class="cards">
      <div class="card"><h2>${esc(t("passkeys_devices"))}</h2>${rows(S.passkeys.map((p) => kv(esc(p.device.startsWith("device_") ? t(p.device) : p.device) + (p.here ? ` ${ok(t("this_device"))}` : ""), esc(t("added_on", { when: dateOf(p.at) })), `<button class="secondary" data-act="passkey:remove:${p.locrd}">${esc(t("remove"))}</button>`)))}<div class="actions"><button class="primary" data-act="passkey:add">${icon("ui-plus")}<span>${esc(t("add_passkey"))}</span></button></div><p class="muted">${esc(t("keep_one_passkey"))}</p></div>
      <div class="card"><h2>${esc(t("active_sessions"))}</h2>${rows(S.sessions.map((s) => kv(esc(t("session_line", { site: t(`site_${s.site}`), device: t(s.device), place: t(s.place) })), esc(whenOf(s.at)), `<button class="secondary" data-act="session:revoke:${s.tail}">${esc(t("remove"))}</button>`)))}<div class="actions"><button class="secondary" data-act="session:all">${icon("ui-signout")}<span>${esc(t("sign_out_everywhere"))}</span></button></div></div>
      <div class="card"><h2>${esc(t("recent_events"))}</h2><ul class="evlist">${S.secEvents.slice(0, 8).map((e) => `<li><span class="t">${esc(whenOf(e.at))}</span><span class="w">${esc(t(SECURITY_EVENT_KEY[e.type] ?? e.type))}</span></li>`).join("")}</ul></div>
      <div class="card"><h2>${esc(t("recovery_settings"))}</h2>${rows([ok(t("recovery_code_set")) + `<button class="secondary" data-act="recovery:newcode">${esc(t("new_recovery_code"))}</button>`, kv(esc(t("backup_contact")), "•••• 2210"), kv(esc(t("second_device")), S.passkeys.length > 1 ? ok(t("verified")) : wait(t("not_yet")))])}</div>
      <div class="card wide"><h2>${esc(t("connected_apps"))}</h2>${S.consents.length ? rows(S.consents.map((c, i) => { const st = consentState(c, now); return kv(esc(`${c.scope}: ${c.purpose}`), st === "ending_soon" ? wait(t("consent_ending", { n: Math.ceil((c.expires - now) / DAY) })) : st === "active" ? ok(t("consent_active", { when: dateOf(c.expires) })) : off(t("ev_consent_withdrawn")), st === "active" || st === "ending_soon" ? `<button class="secondary" data-act="consent:withdraw:${i}">${esc(t("revoke"))}</button>` : ""); })) : `<p class="muted">${esc(t("no_connected_apps"))}</p>`}</div>
    </div>`;
    case "businesses": return `${title("businesses")}<div class="cards">
      <div class="card"><h2>${esc(t("your_businesses"))}</h2>${rows([kv(esc(t("shop_name")), `${esc(maskId(SHOP_OID))} · ${esc(t("role_owner"))}`, `<button class="primary" data-act="open:business">${esc(t("switch_to"))}</button><button class="secondary" data-act="leave:owner">${esc(t("leave"))}</button>`)])}<p class="muted">${esc(t("last_owner_note"))}</p><div class="actions"><button class="secondary" data-act="go:start">${icon("ui-plus")}<span>${esc(t("create_business"))}</span></button></div></div>
      <div class="card"><h2>${esc(t("client_businesses"))}</h2>${rows([
        kv(esc(t("client_pharmacy")), `${esc(t("role_accountant"))} · ${ok(t("consent_active", { when: dateOf(now + 300 * DAY) }))}`, `<button class="primary" data-act="open:client1">${esc(t("switch_to"))}</button>`),
        kv(esc(t("client_taxi")), `${esc(t("role_accountant"))} · ${wait(t("consent_missing"))}`, `<button class="secondary" disabled>${esc(t("switch_to"))}</button>`),
      ])}</div></div>`;
    case "orders": return `${title("orders")}<div class="card">${state("empty", t, statePic("empty"), null)}<p class="muted">${esc(t("orders_empty"))}</p></div>`;
    case "transactions": return `${title("transactions")}<div class="card">${rows([kv(esc(t("shop_name")), esc(whenOf(now - 2 * DAY)) + " · " + esc(money(1500))), kv(esc(t("client_taxi")), `${esc(whenOf(now - 5 * DAY))} · ${esc(money(4200))} · ${wait(t("refund_owed", { amount: money(4200) }))}`)])}</div>`;
    case "wallet": return `${title("wallet")}<div class="cards">
      <div class="card"><h2>${esc(t("wallet_points"))}</h2>${rows([kv(esc(t("points_at", { n: n(240), shop: t("shop_name") })), "")])}</div>
      <div class="card"><h2>${esc(t("wallet_vouchers"))}</h2>${rows([kv(esc(t("voucher_at", { amount: money(500), shop: t("client_pharmacy") })), esc(dateOf(now + 30 * DAY)))])}</div>
      <div class="card"><h2>${esc(t("wallet_tickets"))}</h2><p class="muted">${esc(t("wallet_empty"))}</p></div></div>`;
    case "billing": return `${title("billing")}<div class="cards">
      <div class="card"><h2>${esc(t("shop_name"))}</h2>${rows([kv(esc(t("plan_line", { family: "LynkPOS", tier: "Plus" })), esc(t("next_bill", { amount: money(1200), when: dateOf(now + 7 * DAY) })), `<button class="secondary" data-act="plan:change">${esc(t("change_plan"))}</button>`)])}<div class="actions"><button class="secondary" data-act="go:transactions">${esc(t("invoices"))}</button><button class="secondary" data-act="open:methods">${esc(t("payment_methods"))}</button></div></div>
      <div class="card"><h2>${esc(t("client_pharmacy"))}</h2><p class="muted">${esc(t("no_plans"))}</p></div></div>`;
    case "memberships": return `${title("memberships")}<div class="card"><p class="muted">${esc(t("memberships_body"))}</p></div>`;
    case "privacy": return `${title("privacy")}<div class="cards">
      <div class="card"><h2>${esc(t("consent_log"))}</h2>${rows(S.consents.map((c) => kv(esc(`${c.scope}: ${c.purpose}`), esc(dateOf(c.expires)))))}</div>
      <div class="card"><h2>${esc(t("download_records"))}</h2><p class="muted">${esc(t("download_hint"))}</p>${S.dataRequest ? wait(t("download_requested", { when: dateOf(S.dataRequest.due) })) : `<div class="actions"><button class="primary" data-act="data:request">${icon("ui-doc")}<span>${esc(t("download_records"))}</span></button></div>`}</div>
      <div class="card"><h2>${esc(t("marketing_choices"))}</h2>${rows([`<label class="switch"><input type="checkbox" data-act="toggle:mkemail" ${S.marketing.email ? "checked" : ""}><span>${esc(t("marketing_email"))}</span></label>`, `<label class="switch"><input type="checkbox" data-act="toggle:mkpush" ${S.marketing.push ? "checked" : ""}><span>${esc(t("marketing_push"))}</span></label>`])}</div>
      <div class="card"><h2>${esc(t("close_account"))}</h2><p class="muted">${esc(t("close_hint"))}</p>${S.closing ? `${wait(t("close_requested", { when: dateOf(S.closing) }))}<div class="actions"><button class="primary" data-act="close:cancel">${esc(t("keep_account"))}</button></div>` : `<div class="actions"><button class="secondary" data-act="stepup:close">${esc(t("close_account"))}</button></div>`}</div></div>`;
    case "notifications": return `${title("notifications")}<div class="card">${rows([kv(esc(t("channels")), "push · email · SMS"), kv(esc(t("quiet_hours")), esc(t("quiet_hours_line", { start: clock(Date.UTC(2026, 0, 1, 22)), end: clock(Date.UTC(2026, 0, 1, 7)) })))])}<p class="muted">${esc(t("security_always"))}</p></div>`;
    case "support": return `${title("support")}<div class="card"><p class="muted">${esc(t("support_empty"))}</p><div class="actions"><button class="primary" data-act="support:open">${esc(t("open_case"))}</button></div><p class="muted">${esc(t("exchange_link"))}</p></div>`;
    case "payslips": return `${title("payslips")}<div class="card">${rows([kv(esc(t("payslip_line", { period: "2026-10", employer: t("client_pharmacy") })), "LODOC-9001-0044-2810", `<button class="secondary" data-act="open:payslip">${esc(t("switch_to"))}</button>`)])}<p class="muted">${esc(t("payslips_empty"))}</p></div>`;
    case "payments": {
      if (!ready("paylinks")) return `${title("payments")}<div class="card">${comingSoon("LynkCheckout", t, statePic("coming_soon"), S.notified.has("paylinks"))}</div>`;
      return `${title("payments")}<div class="card"><p class="muted">${esc(t("standing_intro"))}</p>${S.standing.length ? rows(S.standing.map((s, i) => kv(esc(t("standing_line", { merchant: s.merchant, cap: money(s.cap) })), s.active ? ok(t("standing_told")) : off(t("ev_consent_withdrawn")), s.active ? `<button class="secondary" data-act="standing:revoke:${i}">${esc(t("revoke"))}</button>` : ""))) : `<p class="muted">${esc(t("standing_empty"))}</p>`}</div>`;
    }
    case "start": {
      if (!ready("registration")) return `${title("start")}<div class="card">${comingSoon(t("page_start"), t, statePic("coming_soon"), S.notified.has("registration"))}</div>`;
      const a = S.app;
      if (!a) return `${title("start")}<div class="card"><p class="muted">${esc(t("start_intro"))}</p><div class="actions"><button class="primary" data-act="start:begin">${icon("ui-bolt")}<span>${esc(t("start_begin"))}</span></button></div></div>`;
      const stepRows = REGISTRATION_STEPS.map((st) => kv(esc(t(`start_step_${st}`)), a.steps[st] ? ok(t("done")) : off(t("not_yet")), a.status === "started" && !a.steps[st] ? `<button class="secondary" data-act="start:step:${st}">${esc(t("done"))}</button>` : ""));
      const foot = a.status === "started" ? `<div class="actions"><button class="primary" data-act="start:submit" ${canSubmit(a.steps) ? "" : "disabled"}>${esc(t("start_submit"))}</button></div>`
        : a.status === "submitted" ? `${wait(t("start_submitted"))}<div class="actions"><button class="secondary" data-act="start:poll">${esc(t("continue"))}</button></div>` : ok(t("start_approved", { lynkoid: a.lynkoid ?? "" }));
      return `${title("start")}<div class="card">${rows(stepRows)}${foot}<p class="muted">${esc(t("start_not_before"))}</p></div>`;
    }
  }
  return "";
}

function overlay(): string {
  const wrap = (cls: string, inner: string) => `<div class="overlay ${cls}" data-act="closeoverlay">${inner.replace(/^<(div|aside)/, '<$1 data-act="keep"')}</div>`;
  switch (S.overlay) {
    case "launcher": return wrap("", launcher(pack().services.map((s) => ({ id: s.service, name: s.name, icon: s.icon, href: `/${s.service}`, state: S.realUser ? s.state : "available" })), t, icon));
    case "pages": return wrap("", launcher(PAGES.map((p) => ({ id: `page-${p}`, name: t(`page_${p}`), icon: PAGE_ICON[p], href: pagePath(p), state: "available" as const })), t, icon));
    case "account": return wrap("end", accountMenu({ name: t("person_name"), lynkId: LYNKID, businesses: [{ id: "b1", name: t("shop_name"), current: true }, { id: "b2", name: t("client_pharmacy"), current: false }], role: "owner", roles: ["owner", "manager"], theme: S.mode === "lite" ? "lite" : S.mode === "sunlight" ? "sunlight" : S.theme, language: langName(isTest() ? "en" : S.lang), region: pack().sample ? t("sample_country") : pack().name }, t, icon));
    case "globe": return wrap("", globeSheet(Object.entries(PACKS).map(([code, p]) => ({ code, native: p.native, dir: p.dir })), DATA.packOrder.map((c) => ({ code: c, name: (DATA.packs[c] as CountryPack).sample ? t("sample_country") : (DATA.packs[c] as CountryPack).name })), { language: isTest() ? "en" : S.lang, region: pack().code }, t));
    case "cmd": {
      const index: Entry[] = [...PAGES.map((p): Entry => ({ id: p, kind: "setting", title: t(`page_${p}`), act: `go:${p}` })), { id: "h1", kind: "help", title: t("help_article_1"), act: "shell:help" }, { id: "h2", kind: "help", title: t("help_article_2"), act: "shell:help" }, { id: "a1", kind: "action", title: t("sign_out_everywhere"), act: "session:all" }];
      return wrap("", commandBar(S.query, search(index, S.query), t, icon));
    }
    case "help": return wrap("end", helpPanel(t(`page_${signedIn() ? (S.screen as Page) : "security"}`), [{ id: "1", title: t("help_article_1"), href: "/faq/account/recovery" }, { id: "2", title: t("help_article_2"), href: "/faq/account/passkeys" }], t, icon));
    case "bell": {
      const list: Notice[] = [
        { id: "n1", at: Date.now() - 60000, urgency: "security", title: t("notice_signin"), record: "LONTF-2201-4410-8832", href: "/security" },
        { id: "n2", at: Date.now() - 3600000, urgency: "transactional", title: t("notice_consent"), read: true, href: "/security" },
        { id: "n3", at: Date.now() - 7200000, urgency: "low", title: t("notice_renewal"), read: true, href: "/billing" },
      ];
      const d = deliverNow(list, new Date().getHours(), { startHour: 22, endHour: 7 }, S.seen);
      if (d.now.length || d.digest.length) record("NotificationsDelivered", "server", { now: d.now.map((x) => x.id), digest: d.digest.map((x) => x.id), held: d.held.map((x) => x.id) });
      return wrap("end", notificationsPanel(list, t, icon));
    }
    case "sync": return wrap("bottom", syncSheet(sync(), t, icon, clock));
    case "stepup": return wrap("", `<div class="sheet" role="dialog" aria-labelledby="suT"><h2 id="suT">${esc(t("stepup_needed"))}</h2><p class="muted">${esc(t("stepup_hint"))}</p><div class="field"><label for="suCode">${esc(t("code_label"))}</label><input class="text" id="suCode" inputmode="numeric" value="771204"></div><button class="primary" data-act="stepup:ok">${esc(t("confirm"))}</button><button class="secondary" data-act="closeoverlay">${esc(t("cancel"))}</button></div>`);
    default: return "";
  }
}

function draw(): void {
  const d = $("#display");
  d.className = `display ${S.theme}`;
  if (S.mode) d.setAttribute("data-mode", S.mode); else d.removeAttribute("data-mode");
  d.lang = S.lang === "xx-rtl" ? "ar" : S.lang === "xx" ? "en" : S.lang;
  d.dir = S.lang === "xx-rtl" ? "rtl" : S.lang === "xx" ? "ltr" : PACKS[S.lang]?.dir ?? "ltr";
  const logo = S.theme === "dark" ? DATA.brand.topDark : DATA.brand.topLight;
  const items = signedIn() ? navItems() : [];
  const head = header({ logo, nav: items, notifications: signedIn() ? 1 : 0, signedIn: signedIn(), title: S.size === "computer" ? undefined : t("site_short"), surface: "app" }, S.size, t, icon);
  const nav = signedIn() ? navigation(items, S.size, t, icon) : "";
  const toasts = S.undo.openToasts(Date.now()).map((u) => undoToast(u, Date.now(), t, icon)).join("");
  d.innerHTML = `<div class="shell">${head}<div class="shell-body">${S.size === "phone" ? "" : nav}<main class="shell-main" id="main">${page()}<div class="footer-line">${esc(S.realUser ? "" : t("sandbox"))} <span class="deeplink">account.lynkomni.com${esc(screenPath())}</span></div></main></div>${S.size === "phone" ? nav : ""}${overlay()}<div class="toasts">${toasts}</div></div>`;
  $("#device").className = `device ${S.size}`;
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
      S.overlay = S.overlay === map[v] ? null : (map[v] ?? null); S.query = ""; draw();
      if (S.overlay === "cmd") $<HTMLInputElement>("#cmdIn")?.focus();
      return;
    }
    case "nav": { if (v === "more") { S.overlay = S.overlay === "pages" ? null : "pages"; draw(); return; } S.screen = pick(SCREENS, v, S.screen); S.overlay = null; draw(); return; }
    case "go": S.screen = pick(SCREENS, v, S.screen); S.overlay = null; if (v === "recover") S.recover = { otherDevice: null, hasCode: null, started: null }; draw(); return;
    case "place": { const p = v.replace(/^page-/, ""); if (v.startsWith("page-")) S.screen = pick(SCREENS, p, S.screen); S.overlay = null; draw(); return; }
    case "lang": S.lang = pick(Object.keys(PACKS), v, S.lang); $<HTMLSelectElement>("#cLang").value = S.lang; S.overlay = null; draw(); return;
    case "business": case "role": case "region": case "open": case "notice": case "help": case "support": case "assist": case "copy": case "edit": case "plan": S.overlay = null; record("AccountAction", "device", { action: a }); draw(); return;
    case "signin": {
      const dev = v === "other" ? "device_unknown" : "device_phone";
      const alert = signInAlertNeeded(S.seenDevices, dev, "sample_city");
      S.sessions.unshift({ tail: Math.random().toString(16).slice(2, 6), site: "account", device: dev, place: "sample_city", at: now });
      secEvent("SessionStarted"); if (alert.alert) { secEvent("SecurityAlertSent"); S.secEvents[0]!.type = "SecurityAlertSent"; }
      S.screen = "overview"; draw(); return;
    }
    case "username": S.username = v; S.cloud = S.link === "offline" ? "checking" : v === "mamas.kitchen" ? "taken" : v.length >= 3 ? "available" : null; draw(); return;
    case "signup": {
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
      if (v === "add") { S.passkeys.push({ locrd: `LOCRD-0001-0002-${String(5 + S.passkeys.length).padStart(4, "0")}`, device: t("device_n", { n: S.passkeys.length + 1 }), at: now, here: false }); secEvent("PasskeyEnrolled"); draw(); return; }
      const locrd = v.replace(/^remove:/, "");
      if (S.passkeys.length <= 1) { draw(); return; }
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
      if (v === "ok") { const then = S.stepup?.then ?? ""; S.stepup = { ok: true, then }; S.overlay = null; record("StepUpPassed", "server", { scope: "sensitive" }); if (then.startsWith("passkey:")) act(then); else if (then === "close") { S.closing = closesAt(now); record("AccountCloseRequested", "server", { closes_at: S.closing }); } else if (then === "recovery:newcode") { S.recoveryCode = "2B8N-4KQ7-M1XZ-9RCD"; record("RecoveryCodeRotated", "server", {}); } S.stepup = null; draw(); return; }
      stepUp(v); return;
    }
    case "data": S.dataRequest = { due: dataRequestDue(now) }; record("DataRequestOpened", "server", { due_at: S.dataRequest.due }); draw(); return;
    case "close": if (v === "cancel") { S.closing = null; record("AccountCloseCancelled", "server", {}); } draw(); return;
    case "toggle": if (v === "mkemail") S.marketing.email = !S.marketing.email; if (v === "mkpush") S.marketing.push = !S.marketing.push; record("MarketingChoiceChanged", "server", { ...S.marketing }); draw(); return;
    case "standing": { const i = Number(v.replace(/^revoke:/, "")); const s = S.standing[i]; if (s) { s.active = false; record("StandingPaymentRevoked", "server", { losub: s.losub, by: "self" }); } draw(); return; }
    case "start": {
      if (v === "begin") { S.app = { status: "started", steps: { profile: false, registration: false, tax_number: false, bank_account: false } }; record("RegistrationStarted", "server", { country: pack().code }); }
      else if (v.startsWith("step:")) { const st = pick(REGISTRATION_STEPS, v.slice(5), "profile"); if (S.app) S.app.steps[st] = true; }
      else if (v === "submit" && S.app && canSubmit(S.app.steps)) { S.app.status = "submitted"; record("RegistrationSubmitted", "server", { gateway: "registration_gateway" }); }
      else if (v === "poll" && S.app) { S.app.status = applicationStatus(S.app.status, "approved"); S.app.lynkoid = "LOOID-2026-1108-0002"; record("RegistrationApproved", "server", { lynkoid: S.app.lynkoid }); }
      draw(); return;
    }
    case "leave": draw(); return;                                                                    // the last owner cannot leave (note on the page)
    case "notify": S.notified.add(v); record("NotifyMeSubscribed", "device", { service: v }); draw(); return;
    case "payout": { const r = payoutChange(v === "second", now); S.payout = r; record(r.status === "applied" ? "PayoutChangeApplied" : "PayoutChangeRequested", "server", r); draw(); return; }
    case "undo": { const r = S.undo.undo(v, Date.now()); record("AutomationUndone", "device", { id: v, result: r }); draw(); return; }
    case "sync": if (S.link !== "offline") { S.lastSync = Date.now(); S.events.forEach((e) => { if (e.sync === "queued") e.sync = "sent"; }); S.pending = 0; record("SyncCompleted", "server", {}); } S.overlay = null; draw(); return;
  }
}

function init(): void {
  const bind = (sel: string, fn: (el: HTMLInputElement) => void) => $<HTMLInputElement>(sel).addEventListener("change", (e) => fn(e.target as HTMLInputElement));
  bind("#cSize", (el) => { S.size = pick(["computer", "tablet", "phone"] as Viewport[], el.value, S.size); S.overlay = null; draw(); });
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
    if (el.id === "cmdIn") { S.query = plain(el.value); const list = $("#cmdList"); const index = overlay(); const m = /<ul id="cmdList"[^>]*>([\s\S]*?)<\/ul>/.exec(index); if (list && m) list.innerHTML = m[1]!; }
    if (el.id === "usernameIn") { act(`username:${el.value}`); const inp = $<HTMLInputElement>("#usernameIn"); inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); }
  });
  $("#display").addEventListener("change", (e) => { const el = e.target as HTMLInputElement; if (el.dataset["act"]?.startsWith("toggle:")) act(el.dataset["act"]); });
  document.addEventListener("keydown", (e) => { if (e.key === "/" && !(e.target as HTMLElement).matches("input,select,textarea")) { e.preventDefault(); act("shell:search"); } if (e.key === "Escape" && S.overlay) { S.overlay = null; draw(); } });
  const fit = () => { const w = $("#rig").clientWidth - 8, dev = { computer: 1280, tablet: 800, phone: 390 }[S.size]; document.documentElement.style.setProperty("--fit", String(Math.min(1, w / dev))); };
  new ResizeObserver(fit).observe($("#rig")); fit();
  bind("#cSize", () => fit());
  window.setInterval(() => { if (S.undo.openToasts(Date.now()).length || $(".toasts").children.length) draw(); }, 1000);
  draw(); drawLog();
}
init();
