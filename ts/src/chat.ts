/** The conversation engine's rules (CHAT UPDATE, master blueprint 74; build section 4 step C1): the TypeScript port of
 *  core/chat.py, checked against contract/vectors/chat.v1.json. The register travels in ts/src/chat.generated.ts (python3
 *  tools/chat_vectors.py). Live signs are worked out only to be drawn, never stored; masking runs before a message is queued. */

export type ChatState = "queued" | "sent" | "accepted" | "confirmed" | "failed";
interface SignRule { from: string[]; motion: string; words: string; vars?: string[]; team_only?: boolean; person_can_turn_off?: boolean; stage?: number; lasts?: string; counter?: string }
interface SoundRule { tone: string | null; vibrate: string | null; own_action?: boolean; repeat_until_opened?: boolean; build_section?: string; note?: string }
interface CardRule { service: string; actions: string[]; link: string; build_section: string; offline: string; note?: string }
export interface ChatRegister {
  kinds: Record<string, { side: string; between: string[]; inbox: string; desk: string | null }>;
  states: { order: ChatState[]; next: Record<string, string[]>; device_writes: string[]; cloud_writes: string[] };
  edit: { window_minutes: number };
  live_signs: { ends_after_s: number; send_every_s: number; signs: Record<string, SignRule>; own_connection: { reconnecting: string; back_online: string; offline: string }; assist_stages: string[] };
  sounds: { batch_window_ms: number; protected_screens: string[]; events: Record<string, SoundRule>; mute_for: string[] };
  masking: { card: { min_digits: number; max_digits: number; separators: string; keep_last: number }; code: { min_digits: number; max_digits: number; shown_as: string }; mask_char: string; warn_words: string };
  routing: {
    support: { fast_lane: { topics: string[]; desk: Record<string, string> }; max_open_per_helper: number };
    team: { rules: string[]; escalate_after_min: { default: number; min: number; max: number } };
  };
  offline: { what: Record<string, string> };
  cards: { kinds: Record<string, CardRule> };
  tools: { choices: { max: number }; form_fields: string[]; form_max_fields: number };
  [k: string]: unknown;
}
const ALWAYS_SEEN = ["business", "support", "assistant"];

// ---- message states --------------------------------------------------------------------------------------------------------
export function canMove(reg: ChatRegister, from: string, to: string, writer: "device" | "cloud"): boolean {
  if (!(reg.states.next[from] ?? []).includes(to)) return false;
  const may = writer === "device" ? reg.states.device_writes : reg.states.cloud_writes;
  return may.includes(to) || (writer === "device" && from === "failed" && to === "queued");
}
/** The state the writer sees: a person who turned 'seen' off stops at accepted; teams, support and LynkAssist always show seen. */
export function shownState(state: ChatState, reader: string, readerShowsSeen = true): ChatState {
  return state === "confirmed" && !ALWAYS_SEEN.includes(reader) && !readerShowsSeen ? "accepted" : state;
}
export function editAllowed(reg: ChatRegister, body: string, author: string, me: string, minutesSince: number): boolean {
  return body === "text" && author === me && author !== "system" && minutesSince >= 0 && minutesSince <= reg.edit.window_minutes;
}
export interface Msg { id: string; written_at: number; device_seq: number; [k: string]: unknown }
/** Never lost, never doubled, always in order. */
export function ordered<M extends Msg>(messages: readonly M[]): M[] {
  const seen = new Set<string>(); const out: M[] = [];
  for (const m of messages) { if (seen.has(m.id)) continue; seen.add(m.id); out.push(m); }
  return out.sort((a, b) => a.written_at - b.written_at || a.device_seq - b.device_seq || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

// ---- masking ---------------------------------------------------------------------------------------------------------------
function chLuhn(d: string): boolean {
  let total = 0;
  for (let i = 0; i < d.length; i++) { let n = Number(d[d.length - 1 - i]); if (i % 2) n = n > 4 ? n * 2 - 9 : n * 2; total += n; }
  return total % 10 === 0;
}
const chCased = (ch: string): boolean => ch.toUpperCase() !== ch.toLowerCase();
const chLetter = (ch: string): boolean => /\p{L}/u.test(ch);
/** A code word in cased scripts only as a whole word ('pin' not in 'spinach'); in scripts without spaces anywhere. */
export function hasWord(text: string, word: string): boolean {
  const low = [...text.toLowerCase()]; const w = [...(word ?? "").toLowerCase()];
  if (!w.length) return false;
  for (let i = 0; i + w.length <= low.length; i++) {
    if (w.some((c, j) => low[i + j] !== c)) continue;
    const before = (i > 0 ? low[i - 1] : "") ?? ""; const after = (i + w.length < low.length ? low[i + w.length] : "") ?? "";
    if (!(chCased(w[0] ?? "") && before && chLetter(before)) && !(chCased(w[w.length - 1] ?? "") && after && chLetter(after))) return true;
  }
  return false;
}
const reEsc = (s: string): string => s.replace(/[.*+?^${}()|[\]\\-]/g, "\\$&");
/** Masks card numbers always (last four kept) and 4 to 8 digit codes when a code word is present; returns what was found. */
export function mask(reg: ChatRegister, text: string, codeWords: readonly string[] = []): { text: string; found: string[] } {
  const m = reg.masking; const c = m.card; const found = new Set<string>(); const kept: string[] = [];
  const cardRe = new RegExp(`(?<![0-9])[0-9](?:[${reEsc(c.separators)}]?[0-9]){${c.min_digits - 1},${c.max_digits - 1}}(?![0-9])`, "g");
  let out = text.replace(cardRe, (raw) => {
    const digits = raw.replace(/[^0-9]/g, "");
    if (digits.length >= c.min_digits && digits.length <= c.max_digits && chLuhn(digits)) {
      found.add("card"); kept.push(`${m.mask_char.repeat(4)} ${digits.slice(-c.keep_last)}`); return `\u0000${kept.length - 1}\u0000`;
    }
    return raw;
  });
  if (codeWords.some((w) => hasWord(out, w))) {
    const k = m.code;
    out = out.replace(new RegExp(`(?<![0-9\\u0000])[0-9]{${k.min_digits},${k.max_digits}}(?![0-9\\u0000])`, "g"), () => { found.add("code"); return k.shown_as; });
  }
  out = out.replace(/\u0000(\d+)\u0000/g, (_s, i: string) => kept[Number(i)] ?? "");
  return { text: out, found: [...found].sort() };
}

// ---- live signs ------------------------------------------------------------------------------------------------------------
export interface SignShown { words: string; motion: string; vars: string[] }
export function liveSign(reg: ChatRegister, sign: string, author: string, o: { onlineBoth?: boolean; reducedMotion?: boolean; teamView?: boolean; senderAllows?: boolean } = {}): SignShown | null {
  const s = reg.live_signs.signs[sign];
  if (!s || !s.from.includes(author) || o.onlineBoth === false) return null;
  if (s.team_only && !o.teamView) return null;
  if (s.person_can_turn_off && o.senderAllows === false) return null;
  return { words: s.words, motion: o.reducedMotion ? "none" : s.motion, vars: [...(s.vars ?? [])] };
}
export function ownConnection(reg: ChatRegister, online: boolean, wasOffline: boolean, queued: number): { words: string; n: number } | null {
  const oc = reg.live_signs.own_connection;
  if (!online) return { words: oc.offline, n: queued };
  return wasOffline ? { words: oc.back_online, n: queued } : null;
}

// ---- sounds and vibration --------------------------------------------------------------------------------------------------
export interface SoundMoment { sounds?: boolean; vibration?: boolean; silent?: boolean; dnd?: boolean; quiet_hours?: boolean; focus?: boolean; muted?: boolean; screen?: string; chat_open?: boolean; since_last_ms?: number }
export interface SoundOut { tone: string | null; vibrate: string | null; banner: boolean }
export function soundFor(reg: ChatRegister, event: string, s: SoundMoment): SoundOut {
  const snd = reg.sounds;
  if (event === "received") event = s.chat_open ? "received_open" : "received_closed";
  const e = snd.events[event];
  if (!e || (e.tone === null && e.vibrate === null)) return { tone: null, vibrate: null, banner: false };
  const own = !!e.own_action;
  if (s.screen && snd.protected_screens.includes(s.screen)) return { tone: null, vibrate: null, banner: !own };
  const hushed = (!own && !!(s.muted || s.dnd || s.quiet_hours || s.focus)) || (!own && event.startsWith("received") && (s.since_last_ms ?? 1e9) < snd.batch_window_ms);
  const tone = hushed || s.silent || s.sounds === false ? null : e.tone;
  const vibrate = hushed || s.vibration === false ? null : e.vibrate;
  return { tone, vibrate, banner: false };
}

// ---- routing ---------------------------------------------------------------------------------------------------------------
export interface Helper { id: string; available?: boolean; on_shift?: boolean; open?: number; topics?: string[]; sides?: string[]; countries?: string[]; languages?: string[] }
export interface SupportConv { topic?: string; wants_person?: boolean; side?: string; country?: string; language?: string; last_helper?: string; was_with?: string }
export interface SupportRoute { to: string; desk: string | null; helper: string | null; reason: string; translate: boolean }
export function routeSupport(reg: ChatRegister, conv: SupportConv, helpers: readonly Helper[], openNow = true): SupportRoute {
  const r = reg.routing.support; const topic = conv.topic ?? "general";
  if (r.fast_lane.topics.includes(topic)) return { to: "desk", desk: r.fast_lane.desk[topic] ?? null, helper: null, reason: "fast_lane", translate: false };
  if (!conv.wants_person) return { to: "assistant", desk: null, helper: null, reason: "assistant_first", translate: false };
  if (!openNow) return { to: "case", desk: topic, helper: null, reason: "out_of_hours", translate: false };
  const side = conv.side ?? "internal";
  const can = helpers.filter((h) => h.available && h.on_shift && (h.open ?? 0) < r.max_open_per_helper && (h.topics ?? []).includes(topic)
    && (h.sides ?? ["internal", "external"]).includes(side) && (!h.countries || !h.countries.length || h.countries.includes(conv.country ?? "")));
  if (!can.length) return { to: "line", desk: topic, helper: null, reason: conv.was_with ? "back_in_line" : "least_busy", translate: false };
  const lang = conv.language ?? "";
  const same = can.find((h) => h.id === conv.last_helper);
  if (same) return { to: "helper", desk: topic, helper: same.id, reason: "same_helper", translate: !(same.languages ?? []).includes(lang) };
  const speakers = can.filter((h) => (h.languages ?? []).includes(lang));
  const pool = speakers.length ? speakers : can;
  const h = [...pool].sort((a, b) => (a.open ?? 0) - (b.open ?? 0) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0))[0]!;
  return { to: "helper", desk: topic, helper: h.id, reason: speakers.length && speakers.length < can.length ? "language" : "least_busy", translate: !speakers.length };
}
export interface Staff { id: string; on_shift?: boolean; open?: number; branch?: string; products?: string[]; languages?: string[] }
export interface TeamConv { branch?: string; product?: string; language?: string; served_by?: string }
export function routeTeam(reg: ChatRegister, conv: TeamConv, staff: readonly Staff[], mode = "least_busy", turn = 0): { to: string; staff: string | null; reason: string } {
  const on = staff.filter((p) => p.on_shift);
  if (!on.length) return { to: "line", staff: null, reason: "back_in_line" };
  if (on.length === 1) return { to: "staff", staff: on[0]!.id, reason: "only_one_on_shift" };
  const byId = (a: Staff, b: Staff): number => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
  let pool = on;
  for (const rule of reg.routing.team.rules) {
    let hit: Staff[];
    if (rule === "served_before") hit = pool.filter((p) => p.id === conv.served_by);
    else if (rule === "branch") hit = pool.filter((p) => !!conv.branch && p.branch === conv.branch);
    else if (rule === "product_or_order") hit = pool.filter((p) => !!conv.product && (p.products ?? []).includes(conv.product));
    else hit = pool.filter((p) => !!conv.language && (p.languages ?? []).includes(conv.language));
    if (hit.length) { if (rule === "served_before") return { to: "staff", staff: hit[0]!.id, reason: "rule" }; pool = hit; }
  }
  if (mode === "take_turns") { const s = [...pool].sort(byId); return { to: "staff", staff: s[turn % s.length]!.id, reason: "take_turns" }; }
  const pick = [...pool].sort((a, b) => (a.open ?? 0) - (b.open ?? 0) || byId(a, b))[0]!;
  return { to: "staff", staff: pick.id, reason: pool.length < on.length ? "rule" : "least_busy" };
}
export function escalate(reg: ChatRegister, minutesWaiting: number, setting?: number | null): boolean {
  const e = reg.routing.team.escalate_after_min;
  return minutesWaiting >= Math.min(Math.max(setting ?? e.default, e.min), e.max);
}
/** 'Usually replies within' from real figures, or null with fewer than 20 replies (never invented). */
export function replyTime(firstReplyMinutes: readonly number[]): number | null {
  if (firstReplyMinutes.length < 20) return null;
  const xs = [...firstReplyMinutes].sort((a, b) => a - b); const n = xs.length;
  const med = n % 2 ? xs[(n - 1) / 2]! : (xs[n / 2 - 1]! + xs[n / 2]!) / 2;
  for (const b of [5, 10, 15, 30, 60, 120, 240, 1440]) if (med <= b) return b;
  return null;
}

// ---- offline, cards and tools ----------------------------------------------------------------------------------------------
export const offlineRule = (reg: ChatRegister, what: string): string => reg.offline.what[what] ?? "waits";
export function cardAction(reg: ChatRegister, kind: string, action: string, online = true): boolean {
  const c = reg.cards.kinds[kind];
  if (!c || !c.actions.includes(action)) return false;
  if (!online && (c.offline === "not_offered" || ["pay", "accept", "sign", "open_secure_step"].includes(action))) return false;
  return true;
}
export function toolsOk(reg: ChatRegister, choices = 0, fields: readonly string[] = []): boolean {
  const t = reg.tools;
  return choices <= t.choices.max && fields.length <= t.form_max_fields && fields.every((f) => t.form_fields.includes(f));
}
