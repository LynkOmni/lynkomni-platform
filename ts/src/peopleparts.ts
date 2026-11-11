/** Shared parts for LynkAttend, LynkQueue and LynkSurvey (NEW UPDATE 4, master blueprint section 63; build section 1): the ticket
 *  card, the IDCN entry with the checker list, the quick rating, the 0 to 10 score and the "Rate us" QR. Each part draws from the
 *  rules (ts/src/attendance.ts, ts/src/queue.ts, ts/src/survey.ts) and its words (keys "ppl_") travel only in pages that import it.
 *
 *  Every part works by touch and by keys alone: a real button or select for every choice, a visible focus ring, the state said in
 *  words beside any colour; numbers and Lynk Codes are shown as they are in every language (the voice reads codes one by one). */
import { esc } from "./shell.js";
import type { Icon, T } from "./shell.js";
import { checkerChoices, IDCN_LENGTH } from "./attendance.js";
import { validCode, validSection, ticketNumber } from "./queue.js";

/** "LAB-A2K9P2" read character by character, the way the calling voice says it ("L A B, A 2 K 9 P 2"). */
export const spoken = (section: string, code: string): string => `${[...section].join(" ")}, ${[...code].join(" ")}`;

export interface TicketView { section: string; sectionName: string; code: string; place: number | null; waitMinutes: number | null; counter?: string | null }
/** The ticket as a person sees it: the big ticket number, the section name, the place as a plain number and the estimate. */
export function ticketCard(v: TicketView, t: T, icon: Icon): string {
  if (!validSection(v.section) || !validCode(v.code)) throw new Error("not a LynkQueue ticket");
  const num = ticketNumber(v.section, v.code);
  const called = v.counter ? `<p class="tcalled" role="status">${icon("ui-check")}<span>${esc(t("ppl_your_turn", { counter: v.counter }))}</span></p>` : "";
  const place = v.place !== null && !v.counter ? `<p class="tplace">${esc(t("ppl_place", { n: String(v.place) }))}</p>` : "";
  const wait = v.waitMinutes !== null && !v.counter ? `<p class="twait">${esc(t("ppl_wait", { m: String(v.waitMinutes) }))} <span class="tag">${esc(t("ppl_estimate"))}</span></p>` : "";
  return `<div class="ticket" aria-label="${esc(t("ppl_ticket_label"))}: ${esc(spoken(v.section, v.code))}"><p class="tlabel">${esc(t("ppl_ticket_label"))}</p>`
    + `<p class="tnum" dir="ltr"><span class="tsec">${esc(v.section)}</span>-<span class="tcode">${esc(v.code)}</span></p><p class="tname">${esc(v.sectionName)}</p>${called}${place}${wait}</div>`;
}

export interface IdcnEntry { typed: number; checkers: readonly string[]; me: string; chosen: string | null; triesLeft: number | null }
/** The IDCN step at the door: 6 dots for the digits typed (never the digits), the notice and the checker list without the
 *  person's own name. A select works with arrows and OK on buttons-only devices. */
export function idcnEntry(e: IdcnEntry, t: T): string {
  const dots = Array.from({ length: IDCN_LENGTH }, (_, i) => `<span class="dot${i < e.typed ? " on" : ""}"></span>`).join("");
  const opts = checkerChoices(e.checkers, e.me).map((c) => `<option value="${esc(c)}"${c === e.chosen ? " selected" : ""}>${esc(c)}</option>`).join("");
  const left = e.triesLeft !== null ? `<p class="warn" role="alert">${esc(t("ppl_idcn_wrong", { n: String(e.triesLeft) }))}</p>` : "";
  return `<div class="idcn"><p class="plabel" id="idcnL">${esc(t("ppl_idcn_label"))}</p><div class="dots" role="img" aria-labelledby="idcnL" aria-describedby="idcnN">${dots}</div>`
    + `<p class="sr" id="idcnN">${esc(t("ppl_digits_typed", { n: String(e.typed), of: String(IDCN_LENGTH) }))}</p>${left}`
    + `<p class="notice" role="note">${esc(t("ppl_checker_notice"))}</p><label class="plabel" for="checker">${esc(t("ppl_checker_pick"))}</label>`
    + `<select id="checker" data-act="ppl:checker"><option value="">${esc(t("ppl_checker_pick"))}</option>${opts}</select></div>`;
}

export const RATING = ["ppl_rate_1", "ppl_rate_2", "ppl_rate_3", "ppl_rate_4", "ppl_rate_5"] as const;
const FACES = ["😞", "🙁", "😐", "🙂", "😀"] as const;
/** The quick rating: five buttons, each with its word (never the picture alone), 1 = very bad to 5 = very good. */
export function quickRating(title: string, chosen: number | null, t: T): string {
  const b = RATING.map((k, i) => `<button type="button" class="rate${chosen === i + 1 ? " on" : ""}" data-act="ppl:rate:${i + 1}" aria-pressed="${chosen === i + 1}"><span class="face" aria-hidden="true">${FACES[i]}</span><span>${esc(t(k))}</span></button>`).join("");
  return `<fieldset class="rating"><legend>${esc(title)}</legend><div class="rates">${b}</div>${chosen ? `<p class="ok" role="status">${esc(t("ppl_thanks"))}</p>` : ""}</fieldset>`;
}

/** The 0 to 10 "Would you recommend us?" score, with the words at both ends. */
export function scoreScale(title: string, chosen: number | null, t: T): string {
  const b = Array.from({ length: 11 }, (_, n) => `<button type="button" class="score${chosen === n ? " on" : ""}" data-act="ppl:score:${n}" aria-pressed="${chosen === n}">${n}</button>`).join("");
  return `<fieldset class="scale"><legend>${esc(title)}</legend><div class="scores" dir="ltr">${b}</div><p class="ends"><span>${esc(t("ppl_score_low"))}</span><span>${esc(t("ppl_score_high"))}</span></p></fieldset>`;
}

/** "Rate us" for a counter display or a poster: the QR to answer on a phone, and the words beside it. */
export function rateUs(icon: Icon, t: T): string {
  return `<div class="rateus"><span class="qr" aria-hidden="true">${icon("ui-qr", "qrbig")}</span><div><p class="plabel">${esc(t("ppl_rate_us"))}</p><p class="muted">${esc(t("ppl_scan_to_answer"))}</p></div></div>`;
}
