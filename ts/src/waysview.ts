/** Sign-up, sign-in, Can't sign in? and the security page on screen (section 4C points 3 and 5). Every screen that signs a person
 *  up, signs them in, takes them back in or shows their security is drawn only here, from the rules of ts/src/waysin.ts. Words
 *  live in web/waysin (prefix wy_). No DOM here: functions return HTML strings, the host binds data-act="wy:..." and
 *  data-in="wy:...", and waysAct / waysInput change the state. The host passes its own phone, email and code fields (the shared
 *  field parts) and its button classes. Sample values are labelled Sample; codes are made on the device only for the sample.
 *  Rules kept on screen: sign-up is online only and keeps what was typed; email and phone are both needed, each with its own code;
 *  the legal name is kept apart from the display name; codes and the recovery code are shown once; sign-in offers the person's own
 *  ways, strongest first, and an extra check for a new or unusual sign-in; the hub offers only the ways the person has, with their
 *  waits; never a password, questions, a text, email or call alone, or support finishing it; one Cancel on every old device. */
import { WAYS_IN } from "./waysin.generated.js";
import { signUpNext, legalNameProblem, identifierKind, signInWays, extraChecks, recoveryWays, backupCodesLeftNote, checkup, contactsProblem,
  antiPhishingProblem, sessionHours, restrictedAfterRecovery, ownerCheckMethod, ownerCheckOutcome } from "./waysin.js";
import { noticeHtml } from "./errorbox.js";
import { hintFor } from "./hints.js";
import { check, handleBoxHtml, HANDLE_HINT } from "./usernames.js";

type WyT = (key: string, vars?: Record<string, string | number>) => string;
export interface WaysLook {
  t: WyT; icon: (id: string) => string; when: (epochS: number) => string; num: (n: number) => string;
  btn: { primary: string; secondary: string };
  phoneField: (id: string, label: string) => string; emailField: (id: string, label: string) => string; codeField: (id: string, label: string) => string;
}
export interface WaysState {
  now: number; online: boolean; has: string[]; strongest: boolean; minAge: number;
  su: { done: string[]; adult: boolean; legal: string; tried: boolean; username: string; codes: string[]; recovery: string; device: number; network: number };
  si: { who: string; step: "who" | "ways" | "extra" | "done"; unusual: string[]; remember: boolean; qr: boolean; numbers: number };
  rc: { problem: string | null; way: string | null; started: number | null; readyAt: number | null; cancelled: boolean; done: number | null; locked: boolean; blocked: boolean };
  sec: { left: number; shown: string[] | null; auth: "off" | "setup" | "on"; authKey: string; keys: number; contacts: string[]; word: string; wordSaved: boolean;
    lock: string[]; old: string[]; activity: { type: string; at: number }[]; appLock: boolean; privacy: boolean; basic: boolean };
  /** The phone owner check (point 4): consent, which check applies, and the answer written by the cloud (sample answers here). */
  po: { consent: boolean; method: string; state: "none" | "sent" | "confirmed" | "partial" | "failed" | "waiting"; until: number | null };
}
const wyEsc = (s: string): string => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const WY_ALPHABET = WAYS_IN.backup_codes.alphabet;

/** A fresh state for the sample person (Grace): the ways she has and her security settings. */
export function waysStart(now: number, random: (n: number) => number): WaysState {
  const code = (): string => { let c = ""; for (let i = 0; i < WAYS_IN.backup_codes.length; i++) c += WY_ALPHABET[random(WY_ALPHABET.length)]; return `${c.slice(0, 5)}-${c.slice(5)}`; };
  const codes = Array.from({ length: WAYS_IN.backup_codes.count }, code);
  return {
    now, online: true, has: ["passkey", "other_device", "email_code", "text_code", "backup_code", "recovery_code", "email_and_phone", "id_check"], strongest: false, minAge: 18,
    su: { done: [], adult: false, legal: "", tried: false, username: "", codes, recovery: `${code()}-${code()}`, device: 0, network: 0 },
    si: { who: "grace.k", step: "who", unusual: [], remember: true, qr: false, numbers: 10 + random(90) },
    rc: { problem: null, way: null, started: null, readyAt: null, cancelled: false, done: null, locked: false, blocked: false },
    sec: { left: WAYS_IN.backup_codes.count, shown: null, auth: "off", authKey: "", keys: 0, contacts: [], word: "", wordSaved: false, lock: [], old: ["Old tablet"], activity: [], appLock: false, privacy: false, basic: false },
    po: { consent: false, method: ownerCheckMethod(true), state: "none", until: null },
  };
}

const wyBtn = (look: WaysLook, kind: "primary" | "secondary", act: string, label: string, extra = ""): string =>
  `<button type="button" class="${look.btn[kind]}" data-act="wy:${wyEsc(act)}"${extra}>${wyEsc(label)}</button>`;
const wyNever = (look: WaysLook): string =>
  `<div class="wy-never"><p class="wy-sub">${wyEsc(look.t("wy_never_title"))}</p><ul>${WAYS_IN.recovery.never.map((n) => `<li>${wyEsc(look.t(`wy_never_${n}`))}</li>`).join("")}</ul></div>`;

// ---- sign-up -------------------------------------------------------------------------------------------------------------
/** The sign-up screen: one step at a time in the fixed order, online only, with the step bar. */
export function signUpHtml(look: WaysLook, st: WaysState): string {
  const t = look.t, steps: readonly string[] = WAYS_IN.sign_up.steps, step = signUpNext(st.su.done);
  const idx = step === null ? steps.length : steps.indexOf(step);
  const bar = `<ol class="wy-bar" aria-label="${wyEsc(t("wy_step_of", { n: look.num(Math.min(idx + 1, steps.length)), total: look.num(steps.length) }))}">${steps.map((_, i) => `<li class="${i <= idx ? "on" : ""}"></li>`).join("")}</ol>`;
  if (!st.online && step !== null) {
    return `<section class="wy" data-wy="signup"><h1>${wyEsc(t("wy_signup_title"))}</h1>${bar}${noticeHtml(t, { level: "warning", text: t("wy_offline_signup"), how: t("fd_go_online") })}</section>`;
  }
  if (st.su.device >= WAYS_IN.sign_up.abuse.per_device_hour || st.su.network >= WAYS_IN.sign_up.abuse.per_network_hour) {
    return `<section class="wy" data-wy="signup"><h1>${wyEsc(t("wy_signup_title"))}</h1>${noticeHtml(t, { level: "warning", text: t("wy_too_many"), how: t("fd_wait_retry") })}</section>`;
  }
  let body = "";
  const next = (enabled = true, extra = ""): string => wyBtn(look, "primary", `su:next:${step}`, t("wy_next"), (enabled ? "" : " disabled") + extra);
  switch (step) {
    case "country": body = `<p class="wy-note">${wyEsc(t("wy_country_note"))}</p>${next()}`; break;
    case "username": {
      const u = check(st.su.username);
      body = `<div class="wy-field"><label for="wyUser">${wyEsc(t("username"))}</label>${handleBoxHtml({ id: "wyUser", kind: "user", value: st.su.username, attrs: `data-in="wy:username" autocomplete="username" aria-describedby="wyUser-msg"` })}</div>`
        + (st.su.username && !u.ok ? noticeHtml(t, { level: "error", text: t(`username_${u.reason}`), field: "wyUser", how: t("fd_type_again") }) : "")
        + `<p class="wy-note">${wyEsc(t("username_rule", { example: HANDLE_HINT.user }))}</p>${next()}`; break;
    }
    case "age": body = `<label class="wy-check"><input type="checkbox" data-in="wy:adult"${st.su.adult ? " checked" : ""}><span>${wyEsc(t("wy_age_confirm", { age: look.num(st.minAge) }))}</span></label><p class="wy-note">${wyEsc(t("wy_age_note"))}</p>${next(st.su.adult)}`; break;
    case "legal_name": {
      const why = st.su.tried ? legalNameProblem(st.su.legal) : null;
      body = `<div class="wy-field"><label for="wyLegal">${wyEsc(t("wy_legal_label"))}</label><input class="text" id="wyLegal" data-in="wy:legal" autocomplete="name" value="${wyEsc(st.su.legal)}" placeholder="${wyEsc(t("hint_name"))}" aria-describedby="wyLegal-msg"></div>`
        + (why ? noticeHtml(t, { level: "error", text: t(`wy_legal_${why}`), field: "wyLegal", how: t("fd_type_again") }) : "")
        + `<p class="wy-note">${wyEsc(t("wy_legal_note"))}</p>${next()}`; break;
    }
    case "email": body = `${look.emailField("wyEmail", t("wy_step_email"))}<p class="wy-note">${wyEsc(t("wy_email_note"))}</p>${next(true, ' data-needs-email="wyEmail" data-wait')}`; break;
    case "email_code": body = `${look.codeField("wyEmailCode", t("wy_step_email_code"))}<p class="wy-note">${wyEsc(t("wy_code_note"))}</p>${next(true, " data-wait")}`; break;
    case "phone": body = `${look.phoneField("wyPhone", t("wy_step_phone"))}<p class="wy-note">${wyEsc(t("wy_phone_note"))}</p>${next(true, ' data-needs-phone="wyPhone" data-wait')}`; break;
    case "phone_code": body = `${look.codeField("wyPhoneCode", t("wy_step_phone_code"))}<p class="wy-note">${wyEsc(t("wy_code_note"))}</p>${next(true, " data-wait")}`; break;
    case "passkey": body = `<p class="wy-note">${wyEsc(t("wy_passkey_note"))}</p>${wyBtn(look, "primary", "su:next:passkey", t("wy_add_passkey"))}`; break;
    case "recovery": body = `${noticeHtml(t, { level: "warning", text: t("wy_recovery_note") })}
      <div class="wy-codes"><p class="wy-sub">${wyEsc(t("wy_recovery_code"))} <span class="wy-sample">${wyEsc(t("wy_sample"))}</span></p><p class="wy-code" dir="ltr">${wyEsc(st.su.recovery)}</p>
      <p class="wy-sub">${wyEsc(t("wy_backup_codes"))}</p><ol class="wy-list" dir="ltr">${st.su.codes.map((c) => `<li>${wyEsc(c)}</li>`).join("")}</ol></div>
      <div class="wy-btns">${wyBtn(look, "secondary", "su:keep:download", t("wy_download"))}${wyBtn(look, "secondary", "su:keep:print", t("wy_print"))}${wyBtn(look, "secondary", "su:keep:copy", t("wy_copy"))}</div>
      ${wyBtn(look, "primary", "su:next:recovery", t("wy_kept_them"))}`; break;
    default: body = `${noticeHtml(t, { level: "success", text: t("wy_signup_done") })}`;
  }
  const title = step === null ? "" : `<h2>${wyEsc(t(`wy_step_${step}`))}</h2>`;
  const back = step === null || step === "recovery" ? "" : wyBtn(look, "secondary", idx > 0 ? "su:back" : "go:signin", t("wy_back"));
  return `<section class="wy" data-wy="signup"><h1>${wyEsc(t("wy_signup_title"))}</h1><p class="wy-sub">${wyEsc(t("wy_step_of", { n: look.num(Math.min(idx + 1, steps.length)), total: look.num(steps.length) }))}</p>${bar}${title}${body}${back}</section>`;
}

// ---- sign-in -------------------------------------------------------------------------------------------------------------
/** The sign-in screen: one box for username, email or phone, then the person's ways (strongest first), then an extra check
 *  when the sign-in is new or unusual. Codes by email or text come last; Can't sign in? opens the hub. */
export function signInHtml(look: WaysLook, st: WaysState): string {
  const t = look.t, si = st.si;
  const links = `<div class="wy-links"><span class="wy-sub">${wyEsc(t("wy_no_account"))}</span>${wyBtn(look, "secondary", "go:signup", t("wy_create"))}${wyBtn(look, "secondary", "go:recover", t("wy_cant_sign_in"))}</div>`;
  let body = "";
  if (si.step === "who") {
    const kind = identifierKind(si.who);
    body = `<div class="wy-field"><label for="wyWho">${wyEsc(t("wy_who_label"))}</label><input class="text" id="wyWho" data-in="wy:who" autocomplete="username webauthn" value="${wyEsc(si.who)}" placeholder="${wyEsc(hintFor("username", t))}"></div>
      <p class="wy-note" id="wyWhoIs" aria-live="polite">${wyEsc(t("wy_who_is", { kind: t(`wy_kind_${kind}`) }))}</p>${wyBtn(look, "primary", "si:who", t("wy_next"), si.who.trim() ? "" : " disabled")}`;
  } else if (si.step === "ways") {
    const ways = signInWays(st.has.concat(["qr_code"]), st.strongest);
    body = `<div class="wy-ways">${ways.map((w, i) => wyBtn(look, i === 0 ? "primary" : "secondary", `si:way:${w}`, t(`wy_way_${w}`))).join("")}</div>
      ${si.qr ? `<div class="wy-qr"><div class="wy-qrbox" role="img" aria-label="${wyEsc(t("wy_way_qr_code"))}">${look.icon("ui-qr")}</div><p class="wy-note">${wyEsc(t("wy_qr_note"))}</p></div>` : ""}
      <label class="wy-check"><input type="checkbox" data-in="wy:remember"${si.remember ? " checked" : ""}><span>${wyEsc(t("wy_remember"))}</span></label>
      <p class="wy-note">${wyEsc(t("wy_remember_note"))}</p>`;
  } else if (si.step === "extra") {
    const extra = extraChecks(st.has.concat(st.sec.auth === "on" ? ["authenticator"] : []));
    body = `<h2>${wyEsc(t("wy_extra_title"))}</h2><p class="wy-note">${wyEsc(t("wy_extra_note"))}</p>
      ${si.unusual.length ? `<ul class="wy-list">${si.unusual.map((u) => `<li>${wyEsc(t(`wy_unusual_${u}`))}</li>`).join("")}</ul>` : ""}
      ${look.codeField("wyExtraCode", t(`wy_way_${extra[0] ?? "backup_code"}`))}${wyBtn(look, "primary", "si:extra", t("wy_next"), " data-wait")}`;
  } else {
    body = `${noticeHtml(t, { level: "success", text: t("wy_signed_in") })}<p class="wy-note">${wyEsc(t("wy_alert_note"))}</p>`
      + (st.sec.basic ? noticeHtml(t, { level: "info", text: t("wy_basic_limits") }) : "");
  }
  return `<section class="wy" data-wy="signin"><h1>${wyEsc(t("wy_signin_title"))}</h1>${body}${si.step === "done" ? "" : links}</section>`;
}

// ---- Can't sign in? --------------------------------------------------------------------------------------------------------
const waitWords = (look: WaysLook, h: number): string => (h ? look.t("wy_wait_hours", { n: look.num(h) }) : look.t("wy_wait_none"));
/** The hub: what's wrong, then only the ways back in this person has, strongest first, with their waits. */
export function recoverHtml(look: WaysLook, st: WaysState): string {
  const t = look.t, rc = st.rc;
  let body = "";
  if (rc.blocked) body = noticeHtml(t, { level: "error", text: t("wy_blocked"), how: t("fd_contact_support") });
  else if (rc.done !== null) {
    const restricted = restrictedAfterRecovery("payouts", rc.done, st.now);
    body = `${noticeHtml(t, { level: "success", text: t("wy_recovered") })}${restricted ? noticeHtml(t, { level: "info", text: t("wy_restricted") }) : ""}${wyBtn(look, "primary", "rc:checkup", t("wy_open_checkup"))}`;
  } else if (rc.cancelled) body = noticeHtml(t, { level: "info", text: t("wy_stopped") });
  else if (rc.started !== null && rc.readyAt !== null) {
    body = `${noticeHtml(t, { level: "info", text: t("wy_waiting", { when: look.when(rc.readyAt) }) })}<p class="wy-note">${wyEsc(t("wy_waiting_note"))}</p>
      <div class="wy-btns">${wyBtn(look, "secondary", "rc:cancel", t("wy_cancel_old"))}${st.now >= rc.readyAt ? wyBtn(look, "primary", "rc:finish", t("wy_next"), " data-wait") : ""}</div>`;
  } else if (rc.problem === null) {
    body = `<p class="wy-note">${wyEsc(t("wy_recover_lead"))}</p><div class="wy-ways">${WAYS_IN.recovery.problems.map((p) => wyBtn(look, "secondary", `rc:problem:${p}`, t(`wy_problem_${p}`))).join("")}</div>`;
  } else if (rc.problem === "someone_else" && !rc.locked) {
    body = `${noticeHtml(t, { level: "warning", text: t("wy_lock_first") })}${wyBtn(look, "primary", "rc:lock", t("wy_lock_now"), " data-wait")}`;
  } else if (rc.way === null) {
    const ways = recoveryWays(st.has.concat(st.sec.contacts.length >= WAYS_IN.recovery_contacts.min ? ["recovery_contacts"] : []));
    body = `${rc.locked ? noticeHtml(t, { level: "success", text: t("wy_locked") }) : ""}<h2>${wyEsc(t("wy_ways_title"))}</h2><ul class="wy-rows">${ways.map((w) => `<li><span class="wy-main"><span class="wy-nm">${wyEsc(t(`wy_way_${w.id}`))}</span><span class="wy-sub">${wyEsc(waitWords(look, w.wait_h))}</span></span>${wyBtn(look, "secondary", `rc:way:${w.id}`, t("wy_start"))}</li>`).join("")}</ul>`;
  } else {
    const w = rc.way, form = w === "backup_code" || w === "recovery_code" ? look.codeField("wyRcCode", t(`wy_way_${w}`))
      : w === "email_and_phone" ? `${look.codeField("wyRcEmail", t("wy_step_email_code"))}${look.codeField("wyRcPhone", t("wy_step_phone_code"))}`
      : `<p class="wy-note">${wyEsc(t(w === "other_device" ? "wy_way_other_device_note" : w === "recovery_contacts" ? "wy_way_contacts_note" : "wy_way_id_note"))}</p>`;
    body = `<h2>${wyEsc(t(`wy_way_${w}`))}</h2>${form}${wyBtn(look, "primary", `rc:start:${w}`, t("wy_start"), " data-wait")}${wyBtn(look, "secondary", "rc:ways", t("wy_back"))}`;
  }
  return `<section class="wy" data-wy="recover"><h1>${wyEsc(t("wy_recover_title"))}</h1>${body}${wyNever(look)}${wyBtn(look, "secondary", "go:signin", t("wy_back"))}</section>`;
}
/** The I lost my phone page: lock without signing in, with a backup code or the recovery code. */
export function lostPhoneHtml(look: WaysLook, st: WaysState): string {
  const t = look.t;
  return `<section class="wy" data-wy="lost"><h1>${wyEsc(t("wy_lost_title"))}</h1><p class="wy-note">${wyEsc(t("wy_lost_note"))}</p>
    ${st.rc.locked ? noticeHtml(t, { level: "success", text: t("wy_lost_done") }) : `<div class="wy-field"><label for="wyLostWho">${wyEsc(t("wy_who_label"))}</label><input class="text" id="wyLostWho" data-in="wy:who" value="${wyEsc(st.si.who)}" placeholder="${wyEsc(hintFor("username", t))}"></div>${look.codeField("wyLostCode", t("wy_way_backup_code"))}${wyBtn(look, "primary", "rc:lostlock", t("wy_lock_now"), " data-wait")}`}</section>`;
}

// ---- the security page ---------------------------------------------------------------------------------------------------
/** The security page: the checkup first, then every way in and every protection, each with its own switch or fix. */
export function securityHtml(look: WaysLook, st: WaysState): string {
  const t = look.t, s = st.sec;
  const missing = checkup({ second_way: st.has.length > 1 && (s.keys > 0 || s.auth === "on" || st.has.includes("other_device")), backup_codes: !backupCodesLeftNote(s.left), recovery_contacts: s.contacts.length >= WAYS_IN.recovery_contacts.min,
    anti_phishing_word: s.wordSaved, old_devices: !s.old.length, number_confirmed: true });
  const sec = (title: string, inner: string, id: string): string => `<section class="wy-card" data-wy-part="${id}"><h2>${wyEsc(t(title))}</h2>${inner}</section>`;
  const codesNote = backupCodesLeftNote(s.left);
  const contactsWhy = s.contacts.length ? contactsProblem(s.contacts) : null;
  const wordWhy = s.word ? antiPhishingProblem(s.word) : null;
  const parts = [
    sec("wy_checkup_title", missing.length ? `<ul class="wy-rows">${missing.map((m) => `<li><span class="wy-main"><span class="wy-nm">${wyEsc(t(`wy_check_${m}`))}</span></span>${wyBtn(look, "secondary", `sec:fix:${m}`, t("wy_fix"))}</li>`).join("")}</ul>` : noticeHtml(t, { level: "success", text: t("wy_checkup_ok") }), "checkup"),
    sec("wy_backup_codes", `<p class="wy-note">${wyEsc(t("wy_codes_left", { n: look.num(s.left) }))}</p>${codesNote ? noticeHtml(t, { level: "warning", text: t(`wy_codes_${codesNote}`) }) : ""}${s.shown ? `<ol class="wy-list" dir="ltr">${s.shown.map((c) => `<li>${wyEsc(c)}</li>`).join("")}</ol><span class="wy-sample">${wyEsc(t("wy_sample"))}</span>` : ""}${wyBtn(look, "secondary", "sec:codes", t("wy_make_new_codes"), " data-wait")}`, "codes"),
    sec("wy_auth_title", `<p class="wy-note">${wyEsc(t("wy_auth_note"))}</p>${s.auth === "on" ? `<p class="wy-sub">${wyEsc(t("wy_auth_on"))}</p>${wyBtn(look, "secondary", "sec:authoff", t("wy_turn_off"))}<p class="wy-note">${wyEsc(t("wy_turn_off_note"))}</p>`
      : s.auth === "setup" ? `<p class="wy-sub">${wyEsc(t("wy_auth_key"))} <span class="wy-sample">${wyEsc(t("wy_sample"))}</span></p><p class="wy-code" dir="ltr">${wyEsc(s.authKey)}</p>${look.codeField("wyAuthCode", t("wy_way_authenticator"))}${wyBtn(look, "primary", "sec:authon", t("wy_auth_turn_on"), " data-wait")}`
      : wyBtn(look, "secondary", "sec:authsetup", t("wy_auth_turn_on"))}`, "authenticator"),
    sec("wy_keys_title", `<p class="wy-note">${wyEsc(t("wy_keys_note"))}</p>${s.keys ? `<p class="wy-sub">${wyEsc(look.num(s.keys))}</p>` : ""}${wyBtn(look, "secondary", "sec:key", t("wy_add_key"))}`, "keys"),
    sec("wy_contacts_title", `<p class="wy-note">${wyEsc(t("wy_contacts_note"))}</p>${s.contacts.length ? `<ul class="wy-list">${s.contacts.map((c) => `<li><bdi>${wyEsc(c)}</bdi></li>`).join("")}</ul>` : ""}${contactsWhy ? noticeHtml(t, { level: "warning", text: t(`wy_contacts_${contactsWhy}`) }) : ""}${s.contacts.length < WAYS_IN.recovery_contacts.max ? wyBtn(look, "secondary", "sec:contact", t("wy_add_contact")) : ""}`, "contacts"),
    sec("wy_word_title", `<p class="wy-note">${wyEsc(t("wy_word_note"))}</p><div class="wy-field"><label for="wyWord">${wyEsc(t("wy_word_label"))}</label><input class="text" id="wyWord" data-in="wy:word" autocomplete="off" value="${wyEsc(s.word)}" placeholder="${wyEsc(t("wy_hint_word"))}"></div>${wordWhy ? noticeHtml(t, { level: "error", text: t(`wy_word_${wordWhy}`), field: "wyWord", how: t("fd_type_again") }) : ""}${s.wordSaved ? `<p class="wy-sub">${wyEsc(t("wy_saved"))}</p>` : ""}${wyBtn(look, "primary", "sec:word", t("wy_save"), s.word && !wordWhy ? " data-wait" : " disabled")}`, "word"),
    sec("wy_country_lock_title", `<p class="wy-note">${wyEsc(t("wy_country_lock_note"))}</p>${s.lock.length ? `<p class="wy-sub" dir="ltr">${wyEsc(s.lock.join(" "))}</p>` : ""}${wyBtn(look, "secondary", "sec:lock", t(s.lock.length ? "wy_remove" : "wy_save"))}`, "country"),
    sec("wy_strongest_title", `<label class="wy-check"><input type="checkbox" data-in="wy:strongest"${st.strongest ? " checked" : ""}><span>${wyEsc(t("wy_strongest_note"))}</span></label>`, "strongest"),
    sec("wy_devices_title", `${s.old.length ? `<ul class="wy-rows">${s.old.map((d) => `<li><span class="wy-main"><span class="wy-nm">${wyEsc(d)}</span><span class="wy-sub">${wyEsc(t("wy_old_device"))}</span></span>${wyBtn(look, "secondary", "sec:old", t("wy_remove"))}</li>`).join("")}</ul>` : ""}
      <label class="wy-check"><input type="checkbox" data-in="wy:applock"${s.appLock ? " checked" : ""}><span>${wyEsc(t("wy_app_lock"))}</span></label>
      <label class="wy-check"><input type="checkbox" data-in="wy:privacy"${s.privacy ? " checked" : ""}><span>${wyEsc(t("wy_privacy_screen"))}</span></label>`, "devices"),
    sec("wy_activity_title", s.activity.length ? `<ul class="wy-rows">${s.activity.slice(0, 8).map((a, i) => `<li><span class="wy-main"><span class="wy-nm">${wyEsc(t(`wy_ev_${a.type}`))}</span><span class="wy-sub">${wyEsc(look.when(a.at))}</span></span>${wyBtn(look, "secondary", `sec:notme:${i}`, t("wy_not_me"))}</li>`).join("")}</ul>` : `<p class="wy-note">${wyEsc(t("wy_alert_note"))}</p>`, "activity"),
    sec("wy_po_title", phoneOwnerHtml(look, st), "phone_owner"),
    sec("wy_org_title", `<p class="wy-note">${wyEsc(t("wy_org_note"))}</p>`, "org"),
  ];
  return `<div class="wy wy-sec" data-wy="security">${s.basic ? noticeHtml(t, { level: "info", text: t("wy_basic_limits") }) : ""}${parts.join("")}</div>`;
}

/** The phone owner check card (section 4C point 4): only for the activities in the register, always with consent; the
 *  answer is the cloud's (here a labelled sample), each answer with its fix; never charged to the person. */
export function phoneOwnerHtml(look: WaysLook, st: WaysState): string {
  const t = look.t, po = st.po;
  const acts = `<p class="wy-sub">${wyEsc(t("wy_po_for"))}</p><ul class="wy-list">${WAYS_IN.phone_owner.activities.map((a) => `<li>${wyEsc(t(`wy_po_act_${a}`))}</li>`).join("")}</ul>`;
  const how = `<p class="wy-note">${wyEsc(t(po.method === "network" ? "wy_po_network" : "wy_po_id_doc"))}</p>`;
  const fixBtns = (fixes: readonly string[]): string => fixes.map((f) => wyBtn(look, "secondary", `po:fix:${f}`, t(`wy_po_fix_${f.replace("check_", "")}`))).join("");
  let body = "";
  if (po.state === "none") {
    body = `<label class="wy-check"><input type="checkbox" data-in="wy:poconsent"${po.consent ? " checked" : ""}><span>${wyEsc(t("wy_po_consent"))}</span></label>`
      + wyBtn(look, "primary", "po:check", t("wy_po_check"), po.consent ? " data-wait" : ` disabled data-why="${wyEsc(t("wy_po_why"))}"`);
  } else if (po.state === "sent") {
    body = noticeHtml(t, { level: "info", text: t("wy_po_sent") })
      + (po.method === "network" ? `<p class="wy-sub">${wyEsc(t("wy_po_sample"))} <span class="wy-sample">${wyEsc(t("wy_sample"))}</span></p><div class="wy-btns">${(["match", "partial", "no_match", "sim"] as const).map((a) => wyBtn(look, "secondary", `po:answer:${a}`, t(`wy_po_s_${a}`))).join("")}</div>` : "");
  } else if (po.state === "confirmed") body = noticeHtml(t, { level: "success", text: t("wy_po_match", { n: look.num(WAYS_IN.phone_owner.match_valid_days) }) });
  else if (po.state === "partial") body = noticeHtml(t, { level: "warning", text: t("wy_po_partial") }) + `<div class="wy-btns">${fixBtns(WAYS_IN.phone_owner.partial_fixes)}</div>`;
  else if (po.state === "failed") body = noticeHtml(t, { level: "error", text: t("wy_po_no_match"), how: t("wy_po_fix_number") }) + `<div class="wy-btns">${fixBtns(WAYS_IN.phone_owner.no_match_fixes)}</div>`;
  else body = noticeHtml(t, { level: "warning", text: t("wy_po_wait", { when: look.when(po.until ?? st.now) }), how: t("wy_po_wait_how") });
  return `<p class="wy-note">${wyEsc(t("wy_po_note"))}</p>${acts}${how}${body}<p class="wy-note">${wyEsc(t("wy_po_free"))}</p>`;
}

// ---- what a tap or a typed letter changes ----------------------------------------------------------------------------------
const WY_CODE_EVENTS: Record<string, string> = { codes: "BackupCodesMade", authon: "ExtraCheckTurnedOn", key: "SecurityKeyAdded", word: "AntiPhishingWordSet", lock: "CountryLockSet", contact: "RecoveryContactsSet" };
/** Applies a wy: act. Returns the account event the cloud would write (for the host's event log), or null. The host's own
 *  acts (go:signup, go:recover, go:signin, rc:checkup) come back as { go } for it to follow. */
export function waysAct(st: WaysState, act: string, random: (n: number) => number): { event?: string; go?: string } {
  const [area, verb, arg] = act.replace(/^wy:/, "").split(":") as [string, string, string | undefined];
  if (area === "go") return { go: verb };
  if (area === "su") {
    if (verb === "back") { st.su.done.pop(); return {}; }
    if (verb === "next" && arg) {
      if (arg === "legal_name") { st.su.tried = true; if (legalNameProblem(st.su.legal)) return {}; }
      if (arg === "age" && !st.su.adult) return {};
      if (arg === "username" && !check(st.su.username).ok) return {};
      if (!st.su.done.includes(arg)) st.su.done.push(arg);
      return arg === "recovery" ? { event: "AccountCreated" } : {};
    }
    return {};
  }
  if (area === "si") {
    if (verb === "who") { st.si.step = "ways"; return {}; }
    if (verb === "way") {
      if (arg === "qr_code") { st.si.qr = !st.si.qr; return {}; }
      st.si.step = st.si.unusual.length || arg === "email_code" || arg === "text_code" ? "extra" : "done";
      return st.si.step === "done" ? { event: "SessionStarted" } : {};
    }
    if (verb === "extra") { st.si.step = "done"; return { event: "SessionStarted" }; }
    return {};
  }
  if (area === "rc") {
    const rc = st.rc;
    if (verb === "problem") { rc.problem = arg ?? null; rc.way = null; return {}; }
    if (verb === "ways") { rc.way = null; return {}; }
    if (verb === "way") { rc.way = arg ?? null; return {}; }
    if (verb === "lock" || verb === "lostlock") { rc.locked = true; return { event: "EverythingLocked" }; }
    if (verb === "start" && arg) {
      const w = WAYS_IN.recovery.ways.find((x) => x.id === arg);
      if (!w) return {};
      rc.started = st.now; rc.readyAt = st.now + w.wait_h * 3600;
      if (!w.wait_h) { rc.done = st.now; return { event: "RecoveryCompleted" }; }
      return { event: "RecoveryStarted" };
    }
    if (verb === "cancel") { rc.cancelled = true; return { event: "RecoveryCancelled" }; }
    if (verb === "finish" && rc.readyAt !== null && st.now >= rc.readyAt) { rc.done = st.now; return { event: "RecoveryCompleted" }; }
    if (verb === "checkup") return { go: "security" };
    return {};
  }
  if (area === "po") {
    const po = st.po;
    if (verb === "check" && po.consent) { po.state = "sent"; return { event: "PhoneOwnerCheckRequested" }; }
    if (verb === "answer" && po.state === "sent") {
      const out = ownerCheckOutcome(arg === "sim" ? "match" : arg ?? "match", arg === "sim" ? st.now - 3600 : null, st.now);
      po.state = ({ go: "confirmed", fix: "partial", stop: "failed", wait: "waiting" } as const)[out.result]; po.until = out.until;
      return { event: "PhoneOwnerCheckAnswered" };
    }
    if (verb === "fix") {
      if (arg === "id_document") { po.method = ownerCheckMethod(false); po.state = "sent"; return { event: "IdentityCheckRequested" }; }
      po.state = "none"; po.consent = false; return {};
    }
    return {};
  }
  if (area === "sec") {
    const s = st.sec, ev = WY_CODE_EVENTS[verb];
    if (verb === "codes") { const fresh = waysStart(st.now, random).su.codes; s.shown = fresh; s.left = fresh.length; }
    else if (verb === "authsetup") { s.auth = "setup"; let k = ""; for (let i = 0; i < 32; i++) k += WY_ALPHABET[random(WY_ALPHABET.length)]; s.authKey = k.replace(/(.{4})/g, "$1 ").trim(); return {}; }
    else if (verb === "authon") s.auth = "on";
    else if (verb === "authoff") { s.auth = "off"; return { event: "ExtraCheckTurnedOff" }; }
    else if (verb === "key") s.keys += 1;
    else if (verb === "contact") { const pool = ["ama.k", "jean.h", "nadia.r", "kofi.m", "lina.s"]; const next = pool.find((p) => !s.contacts.includes(p)); if (next) s.contacts.push(next); if (s.contacts.length < WAYS_IN.recovery_contacts.min) return {}; }
    else if (verb === "word") { if (antiPhishingProblem(s.word)) return {}; s.wordSaved = true; }
    else if (verb === "lock") { s.lock = s.lock.length ? [] : ["CM"]; }
    else if (verb === "old") { s.old = []; return { event: "OldDeviceSignedOut" }; }
    else if (verb === "notme") return { event: "EverythingLocked" };
    else if (verb === "fix") {
      const fixes: Record<string, string> = { backup_codes: "codes", recovery_contacts: "contact", old_devices: "old", second_way: "key" };
      if (arg === "recovery_contacts") { while (s.contacts.length < WAYS_IN.recovery_contacts.min - 1) waysAct(st, "wy:sec:contact", random); }
      return arg && fixes[arg] ? waysAct(st, `wy:sec:${fixes[arg]}`, random) : { go: "focus:wyWord" };
    }
    if (ev) s.activity.unshift({ type: ev, at: st.now });
    return ev ? { event: ev } : {};
  }
  return {};
}
/** Applies a typed or ticked wy: input. */
/** While a person types in a sign-in box, the note (username, email or phone) and Next follow the typing in place, with no redraw,
 *  so the box keeps its focus and the next tap is never lost (owner 2026-11-26: either email or phone signs in). Hosts call it on input. */
export function waysTyped(root: ParentNode, st: WaysState, field: string, t: WaysLook["t"]): void {
  if (field.replace(/^wy:/, "") !== "who") return;
  const note = root.querySelector<HTMLElement>("#wyWhoIs");
  if (note) note.textContent = t("wy_who_is", { kind: t(`wy_kind_${identifierKind(st.si.who)}`) });
  const next = root.querySelector<HTMLButtonElement>('[data-act$="si:who"]');
  if (next) next.disabled = !st.si.who.trim();
}
export function waysInput(st: WaysState, field: string, value: string, checked: boolean): void {
  const f = field.replace(/^wy:/, "");
  if (f === "adult") st.su.adult = checked;
  else if (f === "legal") { st.su.legal = value; st.su.tried = false; }
  else if (f === "username") st.su.username = value.trim().replace(/^@/, "").toLowerCase().slice(0, 30);
  else if (f === "who") st.si.who = value;
  else if (f === "remember") st.si.remember = checked;
  else if (f === "word") { st.sec.word = value; st.sec.wordSaved = false; }
  else if (f === "strongest") st.strongest = checked;
  else if (f === "applock") st.sec.appLock = checked;
  else if (f === "privacy") st.sec.privacy = checked;
  else if (f === "poconsent") st.po.consent = checked;
}
/** How long the session lasts for the Remember this device choice (shown in the host's session list). */
export const waysSessionHours = (st: WaysState): number => sessionHours(st.si.remember);
