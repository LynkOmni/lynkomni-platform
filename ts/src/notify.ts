/** The notification bell and the message parts (MASTER UPDATE, master blueprint sections 56 and 62; build section 1).
 *  services/messages.py is the engine (what is sent, to whom, when, folded how); these parts only draw what it decided, on
 *  every interface: the bell with its count, New and Earlier, filters, folded lines, actions with "Done by" and Undo, the empty
 *  state, banners, "Why am I seeing this?", the sound, vibration and light for each priority, the lock-screen wording, and the
 *  message parts (an email, a text and the Messages list). Words come through t(); the kinds and priorities from the register. */
import { MESSAGES } from "./parts.generated.js";
import { esc } from "./shell.js";
import type { Icon, T } from "./shell.js";

export type Priority = "critical" | "high" | "normal" | "low";
export interface Line { nid: string; kind: string; title: string; body?: string; at: number; count?: number; read?: boolean; seen?: boolean; record?: string;
  actions?: { id: string; label: string }[]; doneBy?: string; acknowledged?: boolean; business?: string }

export const kindOf = (kind: string) => MESSAGES.kinds[kind];
export const priorityOf = (kind: string): Priority => kindOf(kind)?.priority ?? "normal";
/** The count on the bell: unseen lines whose priority raises it (low never does). Shown as 99+ past 99, nothing at 0. */
export function count(lines: Line[]): number {
  return lines.filter((l) => !l.seen && MESSAGES.priorities[priorityOf(l.kind)]?.raises_count).length;
}
export const badge = (n: number): string => (n <= 0 ? "" : n > 99 ? "99+" : String(n));

/** Ranked only by what needs action, never by what someone paid for: unacknowledged critical, then lines with an action still
 *  open, then by priority, then newest first. */
const RANK: Record<Priority, number> = { critical: 0, high: 1, normal: 2, low: 3 };
export function ranked(lines: Line[]): Line[] {
  const needs = (l: Line) => (priorityOf(l.kind) === "critical" && !l.acknowledged ? 0 : l.actions?.length && !l.doneBy ? 1 : 2);
  return [...lines].sort((a, b) => needs(a) - needs(b) || RANK[priorityOf(a.kind)] - RANK[priorityOf(b.kind)] || b.at - a.at);
}

export type Filter = "all" | "unread" | string;     // or an area of the register (security, sales, stock ...)
export const AREA_ICON: Record<string, string> = { security: "ui-lock", account: "ui-user", safety: "product-guard", selling: "ui-receipt", money: "ui-pay-wallet", stock: "product-stock", devices: "ui-settings", staff: "ui-user", support: "product-chat", assist: "product-assist", orders: "ui-cart", marketing: "ui-bell", agent: "ui-float", billing: "ui-receipt", bookings: "product-booking", developers: "product-dev", movement: "product-motion", office: "product-ledger", proof: "ui-doc", storefront: "ui-cart" };
const iconFor = (kind: string) => AREA_ICON[kindOf(kind)?.area ?? ""] ?? "ui-bell";

function lineHtml(l: Line, t: T, icon: Icon, when: (ms: number) => string): string {
  const p = priorityOf(l.kind);
  const acts = l.doneBy ? `<p class="ndone">${icon("ui-check")}<span>${esc(t("ntf_done_by", { name: l.doneBy }))}</span></p>`
    : (l.actions ?? []).length ? `<div class="nacts">${(l.actions ?? []).map((a) => `<button type="button" class="chipbtn" data-act="ntf:act:${esc(l.nid)}:${esc(a.id)}">${esc(a.label)}</button>`).join("")}</div>` : "";
  const ack = p === "critical" && !l.acknowledged ? `<button type="button" class="primary small" data-act="ntf:ack:${esc(l.nid)}">${esc(t("ntf_acknowledge"))}</button>` : "";
  return `<li class="nline p-${p}${l.read ? "" : " unread"}"><div class="nicon">${icon(iconFor(l.kind))}</div><div class="ntext"><a href="#" data-act="ntf:open:${esc(l.nid)}"><span class="nt">${esc(l.title)}</span>${l.count && l.count > 1 ? `<span class="ncount">${esc(t("ntf_times", { n: l.count }))}</span>` : ""}${l.body ? `<span class="nb">${esc(l.body)}</span>` : ""}</a><span class="nmeta">${p === "critical" || p === "high" ? `<span class="nprio">${esc(t(`ntf_prio_${p}`))}</span>` : ""}<time>${esc(when(l.at))}</time>${l.record ? `<code class="rec">${esc(l.record)}</code>` : ""}</span>${acts}${ack}</div><div class="nmenu"><button type="button" class="hbtn" data-act="ntf:read:${esc(l.nid)}" aria-label="${esc(l.read ? t("ntf_mark_unread") : t("ntf_mark_read"))}">${icon(l.read ? "ui-bell" : "ui-check")}</button><button type="button" class="hbtn" data-act="ntf:why:${esc(l.nid)}" aria-label="${esc(t("ntf_why"))}">${icon("ui-info")}</button></div></li>`;
}

/** The bell's list: filters, then New (since the bell was last opened) and Earlier; folded lines show how many times. */
export function bell(lines: Line[], o: { filter: Filter; lastOpened: number; areas: { id: string; label: string }[] }, t: T, icon: Icon, when: (ms: number) => string): string {
  const shown = ranked(lines.filter((l) => o.filter === "all" || (o.filter === "unread" ? !l.read : kindOf(l.kind)?.area === o.filter)));
  const fresh = shown.filter((l) => l.at > o.lastOpened), earlier = shown.filter((l) => l.at <= o.lastOpened);
  const chip = (id: string, label: string) => `<button type="button" class="chipbtn${o.filter === id ? " on" : ""}" data-act="ntf:filter:${esc(id)}" aria-pressed="${o.filter === id}">${esc(label)}</button>`;
  const filters = `<div class="nfilters" role="group" aria-label="${esc(t("ntf_filters"))}">${chip("all", t("ntf_all"))}${chip("unread", t("ntf_unread"))}${o.areas.map((a) => chip(a.id, a.label)).join("")}</div>`;
  const section = (title: string, ls: Line[]) => ls.length ? `<h3 class="nsec">${esc(title)}</h3><ul class="nlist">${ls.map((l) => lineHtml(l, t, icon, when)).join("")}</ul>` : "";
  const empty = shown.length ? "" : `<div class="nempty" role="status">${icon("ui-check")}<p>${esc(o.filter === "all" ? t("ntf_empty") : t("ntf_empty_filter"))}</p></div>`;
  return `<div class="notifications" role="dialog" aria-label="${esc(t("notifications"))}"><div class="nhead"><h2>${esc(t("notifications"))}</h2><button type="button" class="link" data-act="ntf:allread">${esc(t("ntf_mark_all"))}</button></div>${filters}${section(t("ntf_new"), fresh)}${section(t("ntf_earlier"), earlier)}${empty}<p class="note">${esc(t("ntf_history", { days: MESSAGES.history_days }))}</p><a class="mitem" href="#" data-act="go:notifications">${icon("ui-settings")}<span>${esc(t("notification_settings"))}</span></a></div>`;
}

/** "Why am I seeing this?": the event that caused it, the reason it reached this person and whether it can be turned off. */
export function whySheet(l: Line, t: T, icon: Icon): string {
  const k = kindOf(l.kind);
  const because = k ? t(`ntf_basis_${k.basis}`) : "";
  return `<div class="sheet why" role="dialog" aria-label="${esc(t("ntf_why"))}"><h2>${esc(t("ntf_why"))}</h2><p><strong>${esc(l.title)}</strong></p><p>${icon("ui-info")}<span>${esc(because)}</span></p><p class="note">${esc(k?.can_turn_off ? t("ntf_can_turn_off") : t("ntf_cannot_turn_off"))}</p><button type="button" class="secondary" data-act="closesheet">${esc(t("close"))}</button></div>`;
}

/** A banner on screen while the person is using the app: high slides in and leaves by itself; critical stays until acknowledged. */
export function banner(l: Line, t: T, icon: Icon): string {
  const p = priorityOf(l.kind);
  if (p !== "critical" && p !== "high") return "";
  return `<div class="nbanner p-${p}" role="${p === "critical" ? "alert" : "status"}">${icon(iconFor(l.kind))}<span class="nt">${esc(l.title)}</span>${p === "critical" ? `<button type="button" class="primary small" data-act="ntf:ack:${esc(l.nid)}">${esc(t("ntf_acknowledge"))}</button>` : `<button type="button" class="hbtn" data-act="ntf:dismiss:${esc(l.nid)}" aria-label="${esc(t("close"))}">${icon("ui-close")}</button>`}</div>`;
}

/** How each priority is felt: never by colour, sound or vibration alone (there is always the line and its word). In quiet hours,
 *  do not disturb or silent mode only critical makes a sound. Tones are frequency (Hz) and length (ms) pairs. */
export interface Feel { tones: [number, number][]; vibrate: number[]; light: "none" | "once" | "repeat"; repeat: boolean }
export const FEEL: Record<Priority, Feel> = {
  critical: { tones: [[880, 180], [0, 90], [880, 180], [0, 90], [1175, 260]], vibrate: [400, 200, 400, 200, 400], light: "repeat", repeat: true },
  high: { tones: [[784, 140], [0, 80], [988, 160]], vibrate: [200, 100, 200], light: "once", repeat: false },
  normal: { tones: [[659, 120]], vibrate: [150], light: "once", repeat: false },
  low: { tones: [], vibrate: [], light: "none", repeat: false },
};
export function feelFor(p: Priority, o: { quiet: boolean; silent: boolean; lowData: boolean }): Feel {
  const f = FEEL[p];
  if (p === "critical") return f;
  if (o.quiet || o.silent) return { tones: [], vibrate: o.silent ? [] : f.vibrate.slice(0, 1), light: f.light === "none" ? "none" : "once", repeat: false };
  return f;
}
/** The lock screen never shows the content unless the person chose "full" for that kind: the service and a neutral sentence. */
export const lockScreen = (service: string, mode: "neutral" | "full" | "none", full: string, t: T): string => (mode === "none" ? "" : mode === "full" ? full : t("ntf_lock_neutral", { service }));

// ---------------------------------------------------------------- the message parts (section 56)
/** A text message: GSM-7 when every character fits (160 a part, 153 when split), otherwise Unicode (70 a part, 67 when split). */
const GSM = "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà";
const GSM_EXT = "^{}\\[~]|€";
export function textParts(text: string): { encoding: "gsm7" | "unicode"; units: number; parts: number } {
  const chars = Array.from(text);
  const gsm = chars.every((c) => GSM.includes(c) || GSM_EXT.includes(c));
  const units = gsm ? chars.reduce((n, c) => n + (GSM_EXT.includes(c) ? 2 : 1), 0) : chars.length;
  const [one, many] = gsm ? [160, 153] : [70, 67];
  return { encoding: gsm ? "gsm7" : "unicode", units, parts: units === 0 ? 0 : units <= one ? 1 : Math.ceil(units / many) };
}
export interface Mail { title: string; lines: string[]; record?: string; button?: { label: string; href: string }; reason: string; optIn: boolean; lang: string; dir: "ltr" | "rtl" }
/** The email part: the logo (brand place email-header, passed in), one title, short lines, the record number, at most one
 *  button to a lynkomni.com address, then why the person got it, and a one-tap stop only for messages they opted into. */
export function mailPart(m: Mail, logo: string, t: T): string {
  const btn = m.button && /^https:\/\/([a-z0-9-]+\.)?lynkomni\.com(\/|$)/.test(m.button.href) ? `<p><a class="mbtn" href="${esc(m.button.href)}">${esc(m.button.label)}</a></p>` : "";
  return `<article class="mail" lang="${esc(m.lang)}" dir="${m.dir}"><header class="mhead">${logo}</header><h3>${esc(m.title)}</h3>${m.lines.map((l) => `<p>${esc(l)}</p>`).join("")}${m.record ? `<p class="mrec">${esc(t("msg_record"))} <code>${esc(m.record)}</code></p>` : ""}${btn}<footer class="mfoot"><p>${esc(m.reason)}</p>${m.optIn ? `<p><a href="#" data-act="msg:stop">${esc(t("msg_stop"))}</a></p>` : ""}<p>${esc(t("msg_never_ask"))}</p></footer></article>`;
}
export function textPart(text: string, t: T): string {
  const p = textParts(text);
  return `<div class="smsbubble"><p>${esc(text)}</p><p class="note">${esc(t("msg_text_parts", { n: p.parts }))}</p></div>`;
}
export interface Sent { id: string; channel: "email" | "text" | "push" | "bell"; sender: string; title: string; at: number; state: "queued" | "sent" | "accepted" | "confirmed" | "failed" }
/** The Messages part: what LynkOmni sent this person, on which channel and from which address, with its state word. */
export function messagesList(items: Sent[], t: T, icon: Icon, when: (ms: number) => string): string {
  const ch: Record<Sent["channel"], string> = { email: "ui-doc", text: "product-chat", push: "ui-bell", bell: "ui-bell" };
  return `<div class="messages"><h2>${esc(t("msg_title"))}</h2><ul class="mlist2">${items.map((m) => `<li>${icon(ch[m.channel])}<div><strong>${esc(m.title)}</strong><span class="muted">${esc(t(`msg_ch_${m.channel}`))} · ${esc(m.sender)} · <time>${esc(when(m.at))}</time></span></div><span class="chip st-${m.state}">${icon(`status-${m.state}`)}<span>${esc(t(`st_${m.state}`))}</span></span></li>`).join("") || `<li class="none">${esc(t("msg_none"))}</li>`}</ul><p class="note">${esc(t("msg_no_tracking"))}</p></div>`;
}
