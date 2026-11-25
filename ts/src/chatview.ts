/** The shared chat part (CHAT UPDATE, master blueprint 74; section 4 step C2). Every chat screen in LynkOmni draws its inbox
 *  rows and its conversation with these parts, from the chat register (catalog/chat.v1.json through ts/src/chat.ts):
 *    - messages with the five states (the reader's 'seen' choice followed), 'edited', a quoted reply and message details,
 *    - live signs, always with words (still words when motion is off), announced once to a screen reader, never stored,
 *    - your own connection ('Waiting for internet', 'Back online'), the unread line and LynkAssist always named,
 *    - LynkAssist's answer as it is written, with its stage and Stop; upload progress with pause and cancel,
 *    - buttons and small forms (a tap sends the choice as the person's own message), cards from their own service,
 *    - masking before a message is queued, with the warning 'LynkOmni and its staff never ask for this',
 *    - chat sounds and vibration from the design tokens, following the person's switches and the protected screens,
 *    - 'Chat about this', 'Why did I get this chat?' and 'Who is helping me?'.
 *  No DOM here: parts return HTML strings and the host binds data-act. Words come from web/chat (prefix ch_) through the host's
 *  t(). Chat is customer-and-business and support only; it is never called end-to-end encrypted. */
import type { ChatRegister, ChatState, SoundMoment } from "./chat.js";
import { liveSign, mask, ownConnection, shownState, chatSoundFor } from "./chat.js";
import type { SoundSet, Sound } from "./keytones.js";
import { playSound } from "./keytones.js";
import { noticeHtml } from "./errorbox.js";

export type T = (key: string, vars?: Record<string, string | number>) => string;
export type Icon = (id: string, cls?: string) => string;
const chEsc = (s: string): string => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export interface ChatLook {
  t: T; icon: Icon;
  /** the state chip with its word and icon (the five states only) */
  chip: (s: ChatState) => string;
  /** a card drawn by its own service (its words, states and actions); the chat only shows it */
  card?: (kind: string, label: string) => string;
  clock: (at: number) => string;
  reducedMotion?: boolean;
}
export interface ChatChoice { id: string; label: string }
export interface ChatField { id: string; kind: "date" | "option" | "place" | "address_confirm" | "number" | "short_text"; label: string; options?: readonly string[];
  /** the host's own example when the field asks for something specific (a sample order number from the id registry) */
  hint?: string }
export interface ChatMsg {
  id: string; author: string; out: boolean; text: string; at: number; state: ChatState;
  edited?: boolean; replyTo?: string; card?: { kind: string; label: string };
  choices?: readonly ChatChoice[]; chosen?: string; form?: readonly ChatField[]; answered?: boolean;
  /** LynkAssist's answer while it is written: its stage, then the words so far; stopped keeps what was written */
  stream?: { stage: string; done?: boolean; stopped?: boolean };
  upload?: { kind: "photo" | "file"; pct: number; paused?: boolean };
  times?: Partial<Record<"written" | "sent" | "accepted" | "confirmed" | "edited", number>>;
  /** the host's own line under the text (the 'Translated from' note with its switch back) */
  noteHtml?: string;
}
export interface ThreadView {
  id: string; kind: string; title: string; side: "internal" | "external";
  msgs: readonly ChatMsg[];
  /** a live sign from the other side, while both sides are online */
  sign?: { sign: string; author: string; vars?: Record<string, string | number> };
  online: boolean; wasOffline?: boolean; queued?: number;
  /** the first unread message */
  unreadFrom?: string;
  /** the reader turned 'seen' off (a person; teams always show it) */
  readerShowsSeen?: boolean; reader?: string;
  teamView?: boolean; senderAllowsSigns?: boolean;
  draft: string; draftHint: string;
  /** what masking found in the draft, shown before sending */
  warning?: readonly string[];
  muted?: string | null;
  /** for support: LynkAssist answers first and a person is one tap away */
  assistFirst?: boolean;
  /** why this chat came to this reader (a routing reason) */
  reason?: string;
  /** the message whose details are open */
  details?: string;
  /** the host's own tools just above the composer (a business's card buttons, saved replies) */
  beforeCompose?: string;
  act?: string;
}

/** The words a code may hide behind in the reader's language (ch_code_words, comma separated). */
export const codeWords = (t: T): string[] => t("ch_code_words").split(/[,،、]/).map((w) => w.trim()).filter(Boolean);

/** Masks a draft before it is queued: card numbers keep their last four, codes are hidden when a code word is there. */
export function prepareSend(reg: ChatRegister, t: T, draft: string): { text: string; found: string[] } {
  return mask(reg, draft.trim(), codeWords(t));
}

/** The live sign line: words always, a moving mark only when motion is allowed; announced once (role status, polite). */
export function signHtml(reg: ChatRegister, look: ChatLook, v: Pick<ThreadView, "sign" | "online" | "teamView" | "senderAllowsSigns">): string {
  if (!v.sign) return "";
  const s = liveSign(reg, v.sign.sign, v.sign.author, { onlineBoth: v.online, reducedMotion: look.reducedMotion, teamView: v.teamView, senderAllows: v.senderAllowsSigns !== false });
  if (!s) return "";
  const vars: Record<string, string | number> = {};
  for (const k of s.vars) vars[k] = v.sign.vars?.[k] ?? "";
  return `<p class="ch-sign" role="status" aria-live="polite" data-motion="${chEsc(s.motion)}" data-sign="${chEsc(v.sign.sign)}"><span class="ch-mark" aria-hidden="true"><i></i><i></i><i></i></span><span>${chEsc(look.t(s.words, vars))}</span></p>`;
}

function chMeta(reg: ChatRegister, look: ChatLook, m: ChatMsg, v: ThreadView, act: string): string {
  const st = m.out ? shownState(m.state, v.reader ?? "customer", v.readerShowsSeen !== false) : null;
  return `<span class="ch-meta">${chEsc(look.clock(m.at))}${m.edited ? ` · <span>${chEsc(look.t("ch_edited"))}</span>` : ""}${st ? look.chip(st) : ""}
    <button class="ch-more" data-act="${act}:details:${chEsc(m.id)}" aria-label="${chEsc(look.t("ch_details"))}">${look.icon("ui-info")}</button></span>${st === "failed" ? `<button class="ch-retry" data-act="${act}:retry:${chEsc(m.id)}">${chEsc(look.t("ch_try_again"))}</button>` : ""}`;
}

function chStream(reg: ChatRegister, look: ChatLook, m: ChatMsg, act: string): string {
  const s = m.stream; if (!s) return "";
  if (s.done || s.stopped) return s.stopped ? `<span class="ch-note">${chEsc(look.t("ch_stopped"))}</span>` : "";
  const shown = liveSign(reg, s.stage, "assistant", { reducedMotion: look.reducedMotion });
  return `${shown ? `<span class="ch-stage" data-motion="${chEsc(shown.motion)}"><span class="ch-mark" aria-hidden="true"><i></i><i></i><i></i></span>${chEsc(look.t(shown.words, { what: look.t("ch_what_order") }))}</span>` : ""}
    <button class="ch-stop" data-act="${act}:stop:${chEsc(m.id)}">${chEsc(look.t("ch_stop"))}</button>`;
}

function chUpload(look: ChatLook, m: ChatMsg, act: string): string {
  const u = m.upload; if (!u || u.pct >= 100) return "";
  return `<span class="ch-upload"><span class="ch-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${u.pct}" aria-label="${chEsc(look.t(u.kind === "photo" ? "ch_sign_sending_photo" : "ch_sign_sending_file"))}"><span style="inline-size:${Math.max(0, Math.min(100, u.pct))}%"></span></span>
    <span class="ch-pct">${chEsc(look.t("ch_upload", { pct: u.pct }))}</span><button data-act="${act}:${u.paused ? "resume" : "pause"}:${chEsc(m.id)}">${chEsc(look.t(u.paused ? "ch_resume" : "ch_pause"))}</button><button data-act="${act}:cancelup:${chEsc(m.id)}">${chEsc(look.t("ch_cancel"))}</button></span>`;
}

function chTools(reg: ChatRegister, look: ChatLook, m: ChatMsg, act: string): string {
  let out = "";
  if (m.choices?.length) {
    out += `<span class="ch-choices" role="group" aria-label="${chEsc(look.t("ch_choose"))}">${m.choices.slice(0, reg.tools.choices.max).map((c) => `<button data-act="${act}:choice:${chEsc(m.id)}:${chEsc(c.id)}" aria-pressed="${m.chosen === c.id}"${m.chosen ? " disabled" : ""}>${chEsc(c.label)}</button>`).join("")}</span>`;
  }
  if (m.form?.length) {
    const fields = m.form.slice(0, reg.tools.form_max_fields).filter((f) => reg.tools.form_fields.includes(f.kind));
    out += `<span class="ch-form">${fields.map((f) => {
      const id = `chf-${chEsc(m.id)}-${chEsc(f.id)}`;
      const input = f.kind === "option" ? `<select id="${id}"${m.answered ? ' disabled data-why="shown"' : ""}>${(f.options ?? []).map((o) => `<option>${chEsc(o)}</option>`).join("")}</select>`
        : f.kind === "address_confirm" ? `<input id="${id}" type="checkbox"${m.answered ? ' disabled data-why="shown"' : ""}>`
        : `<input id="${id}" type="${f.kind === "date" ? "date" : f.kind === "number" ? "number" : "text"}" inputmode="${f.kind === "number" ? "numeric" : "text"}" placeholder="${chEsc(f.hint ?? look.t(`ch_hint_${f.kind}`))}"${m.answered ? ' disabled data-why="shown"' : ""}>`;
      return `<label for="${id}"><span>${chEsc(f.label)}</span>${input}</label>`;
    }).join("")}${m.answered ? `<span class="ch-note">${chEsc(look.t("ch_answered"))}</span>` : `<button class="primary" data-act="${act}:form:${chEsc(m.id)}">${chEsc(look.t("ch_form_send"))}</button>`}</span>`;
  }
  return out;
}

/** One message: the assistant always named, a quoted reply, the card from its service, the text, tools, then time, state and details. */
export function messageHtml(reg: ChatRegister, look: ChatLook, m: ChatMsg, v: ThreadView, quoted?: ChatMsg): string {
  const act = v.act ?? "ch";
  const who = m.author === "assistant" ? `<span class="ch-who">${look.icon("product-assist")}${chEsc(look.t("ch_assist_label"))}</span>` : "";
  const quote = quoted ? `<span class="ch-quote"><span class="ch-note">${chEsc(look.t("ch_reply_to"))}</span>${chEsc(quoted.text.slice(0, 80))}</span>` : "";
  const card = m.card && look.card ? look.card(m.card.kind, m.card.label) : "";
  return `<div class="ch-msg ${m.out ? "out" : "in"}${m.author === "assistant" ? " assist" : ""}" data-id="${chEsc(m.id)}">${who}${quote}${card}${m.text ? `<span class="ch-text">${chEsc(m.text)}</span>` : ""}${m.noteHtml ?? ""}
    ${chStream(reg, look, m, act)}${chUpload(look, m, act)}${chTools(reg, look, m, act)}${chMeta(reg, look, m, v, act)}</div>`;
}

/** Message details: when it was written, sent, reached them, seen and edited. */
export function detailsHtml(reg: ChatRegister, look: ChatLook, m: ChatMsg, act = "ch"): string {
  const rows = (["written", "sent", "accepted", "confirmed", "edited"] as const).filter((k) => m.times?.[k] !== undefined);
  return `<div class="ch-details" role="dialog" aria-label="${chEsc(look.t("ch_details"))}"><h3>${chEsc(look.t("ch_details"))}</h3><dl>${rows.map((k) => `<dt>${chEsc(look.t(`ch_d_${k}`))}</dt><dd>${chEsc(look.clock(m.times![k]!))}</dd>`).join("")}</dl>
    <button data-act="${act}:closedetails">${chEsc(look.t("ch_close"))}</button></div>`;
}

/** The warning before a card number or code is sent: it will be hidden; LynkOmni and its staff never ask for it. */
export function warningHtml(look: ChatLook, found: readonly string[], act = "ch"): string {
  if (!found.length) return "";
  // section 4C point 2: drawn by the shared message part, with its two ways on
  return noticeHtml(look.t, { level: "warning", cls: "ch-warn", text: look.t("ch_warn_never_ask"), fix: { label: look.t("ch_edit_first"), act: `${act}:edit` }, also: [{ label: look.t("ch_send_masked"), act: `${act}:sendmasked` }] });
}

/** The composer: a visible label, an example as its hint, Send, a voice message and a photo or file. */
export function composerHtml(look: ChatLook, v: Pick<ThreadView, "draft" | "draftHint" | "act">): string {
  const act = v.act ?? "ch";
  return `<div class="ch-compose"><label class="ch-label" for="chIn">${chEsc(look.t("ch_write"))}</label>
    <button class="iconbtn" data-act="${act}:attach" aria-label="${chEsc(look.t("ch_attach"))}">${look.icon("ui-doc")}</button>
    <input id="chIn" data-in="chat" data-draft="chat:${chEsc(v.act ?? "thread")}" value="${chEsc(v.draft)}" placeholder="${chEsc(v.draftHint)}" autocomplete="off" enterkeyhint="send">
    <button class="iconbtn" data-act="${act}:record" aria-label="${chEsc(look.t("ch_record"))}">${look.icon("ui-mic")}</button>
    <button class="iconbtn primary" data-act="${act}:send" aria-label="${chEsc(look.t("ch_send"))}">${look.icon("ui-chevron-right", "ic fwd")}</button></div>`;
}

/** A conversation: the help line on top, the messages with the unread line, the live sign, your own connection, the masking
 *  warning and the composer. */
export function threadHtml(reg: ChatRegister, look: ChatLook, v: ThreadView): string {
  const act = v.act ?? "ch";
  const byId = new Map(v.msgs.map((m) => [m.id, m]));
  const top = [
    v.assistFirst ? `<p class="ch-help">${look.icon("product-assist")}<span>${chEsc(look.t("ch_assist_first"))}</span><button data-act="${act}:person">${chEsc(look.t("ch_talk_person"))}</button></p>` : "",
    v.reason ? `<details class="ch-why"><summary>${chEsc(look.t(v.teamView ? "ch_why_got_chat" : "ch_who_helps"))}</summary><p>${chEsc(look.t(`ch_reason_${v.reason}`))}</p></details>` : "",
    v.side === "external" ? `<p class="ch-side">${chEsc(look.t("ch_side_storefront"))}</p>` : "",
  ].join("");
  const conn = ownConnection(reg, v.online, !!v.wasOffline, v.queued ?? 0);
  const details = v.details ? byId.get(v.details) : undefined;
  return `<div class="ch-thread" data-kind="${chEsc(v.kind)}">${top}
    <div class="ch-msgs" role="log" aria-label="${chEsc(v.title)}">${v.msgs.map((m) => `${m.id === v.unreadFrom ? `<p class="ch-unread"><span>${chEsc(look.t("ch_unread_line"))}</span></p>` : ""}${messageHtml(reg, look, m, v, m.replyTo ? byId.get(m.replyTo) : undefined)}`).join("")}</div>
    ${signHtml(reg, look, v)}${conn ? `<p class="ch-conn" role="status">${look.icon(v.online ? "ui-sync" : "ui-offline")}<span>${chEsc(look.t(conn.words, { n: conn.n }))}</span></p>` : ""}
    ${details ? detailsHtml(reg, look, details, act) : ""}${warningHtml(look, v.warning ?? [], act)}${v.beforeCompose ?? ""}${composerHtml(look, v)}
    <p class="ch-protect">${chEsc(look.t("ch_protected_note"))}</p></div>`;
}

export interface InboxRow { id: string; name: string; last: string; at: number | null; unread: number; support?: boolean; side?: "internal" | "external"; sign?: { sign: string; author: string }; muted?: boolean }
/** An inbox row: Support pinned, the live sign replacing the last message for a moment, the unread count, the side in words. */
export function inboxRowHtml(reg: ChatRegister, look: ChatLook, r: InboxRow, o: { online: boolean; act?: string; pinnedWord?: string }): string {
  const s = r.sign ? liveSign(reg, r.sign.sign, r.sign.author, { onlineBoth: o.online, reducedMotion: look.reducedMotion }) : null;
  const sub = s ? `<span class="sub ch-row-sign">${chEsc(look.t(s.words))}</span>` : `<span class="sub">${chEsc(r.last)}</span>`;
  return `<li${r.support ? ' data-item="support_pinned"' : ""}><button class="rowbtn" data-act="${o.act ?? "thread"}:${chEsc(r.id)}"><span class="avatar" aria-hidden="true">${r.support ? look.icon("product-chat") : chEsc(r.name.slice(0, 1))}</span>
    <span class="main"><span class="nm">${chEsc(r.name)}${r.support && o.pinnedWord ? ` · ${chEsc(o.pinnedWord)}` : ""}${r.side === "external" ? ` · ${chEsc(look.t("ch_side_word"))}` : ""}</span>${sub}</span>
    ${r.muted ? `<span class="ch-muted" aria-label="${chEsc(look.t("ch_muted"))}">${look.icon("ui-bell")}</span>` : ""}${r.unread ? `<span class="pill ok">${r.unread}</span>` : `<span class="sub">${chEsc(r.at !== null ? look.clock(r.at) : "")}</span>`}</button></li>`;
}

/** 'Chat about this' on a record: opens the conversation with the record attached as its card. */
export function chatAboutHtml(look: ChatLook, record: string, id: string, act = "chatabout"): string {
  return `<button class="secondary ch-about" data-act="${act}:${chEsc(record)}:${chEsc(id)}">${look.icon("product-chat")}<span>${chEsc(look.t("ch_chat_about"))}</span></button>`;
}

/** Mute one conversation for an hour, a day or always (switches, never hidden). */
export function muteHtml(reg: ChatRegister, look: ChatLook, muted: string | null | undefined, act = "ch"): string {
  return `<div class="ch-mute" role="group" aria-label="${chEsc(look.t("ch_mute"))}">${reg.sounds.mute_for.map((m) => `<button data-act="${act}:mute:${m}" aria-pressed="${muted === m}">${chEsc(look.t(`ch_mute_${m}`))}</button>`).join("")}${muted ? `<button data-act="${act}:unmute">${chEsc(look.t("ch_unmute"))}</button>` : ""}</div>`;
}

/** Plays a chat event's tone and vibration from the design tokens, following the register's rules and the person's switches
 *  (sounds, vibration, volume). Returns what was decided, so the screen always shows the matching sign. */
export function playChat(reg: ChatRegister, snd: SoundSet, event: string, moment: SoundMoment, volume: "low" | "medium" | "high" = "medium"): { tone: string | null; vibrate: string | null; banner: boolean } {
  const out = chatSoundFor(reg, event, moment);
  if (out.tone && out.tone !== "notification") playSound(snd, out.tone as Sound, { tones: true, vibration: false, volume });
  if (out.vibrate && typeof navigator !== "undefined" && "vibrate" in navigator) { try { navigator.vibrate(snd.vibrate[out.vibrate] ?? []); } catch { /* no vibration on this device */ } }
  return out;
}

/** sha256 of a message's text as hex (MessagePosted carries only this, never the text). Small and synchronous, so a message
 *  queued offline gets its fingerprint at once. */
export function chatDigest(text: string): string {
  const K = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152,
    0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb,
    0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c,
    0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2];
  const bytes = Array.from(new TextEncoder().encode(text));
  const bits = bytes.length * 8;
  bytes.push(0x80);
  while (bytes.length % 64 !== 56) bytes.push(0);
  for (let i = 7; i >= 0; i--) bytes.push(i >= 4 ? 0 : (bits >>> (i * 8)) & 0xff);
  const H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
  const r = (x: number, n: number): number => (x >>> n) | (x << (32 - n));
  const w = new Array<number>(64).fill(0);
  for (let o = 0; o < bytes.length; o += 64) {
    for (let i = 0; i < 16; i++) w[i] = ((bytes[o + i * 4]! << 24) | (bytes[o + i * 4 + 1]! << 16) | (bytes[o + i * 4 + 2]! << 8) | bytes[o + i * 4 + 3]!) >>> 0;
    for (let i = 16; i < 64; i++) {
      const a = w[i - 15]!, b = w[i - 2]!;
      w[i] = (w[i - 16]! + (r(a, 7) ^ r(a, 18) ^ (a >>> 3)) + w[i - 7]! + (r(b, 17) ^ r(b, 19) ^ (b >>> 10))) >>> 0;
    }
    let [a, b, c, d, e, f, g, h] = H as [number, number, number, number, number, number, number, number];
    for (let i = 0; i < 64; i++) {
      const t1 = (h + (r(e, 6) ^ r(e, 11) ^ r(e, 25)) + ((e & f) ^ (~e & g)) + K[i]! + w[i]!) >>> 0;
      const t2 = ((r(a, 2) ^ r(a, 13) ^ r(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
      h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
    }
    const add = [a, b, c, d, e, f, g, h];
    for (let i = 0; i < 8; i++) H[i] = (H[i]! + add[i]!) >>> 0;
  }
  return H.map((x) => x.toString(16).padStart(8, "0")).join("");
}
