/** LynkSurvey in full on a device (LynkS; master blueprint section 63; build section 3B): building, approval, answering on every
 *  device, live results and the research tools, call back, "You said, we did", rewards, the LynkSurvey Panel, verified results and
 *  the plan. The same engine runs in the Business app (LynkMobile, LynkTab, LynkPC), on LynkKiosk, LynkDScreen, LynkCDisplay, the
 *  person's phone and LynkPOS; it mirrors the reference service (people/survey.py) and takes every rule from ts/src/survey.ts.
 *
 *  What never happens here: a result for fewer than 5 answers (anywhere, in any tool); the author of an anonymous answer; a name
 *  or a phone number in an event; an answer deleted because it was flagged ("Please check" is only a flag); a reward shown as paid
 *  before the partner says so. Answers given on this device are written at once and sent when the link is back (the five states).
 *  Words are "ppl_sv_" keys in web/shell. Sample answers are labelled "Sandbox" wherever they appear. */
import { planPreviewHtml } from "./placeholder.js";
import { hintFor } from "./hints.js";
import { codeFieldHtml, resendWait, asciiDigits } from "./codefield.js";
import { esc } from "./shell.js";
import { noticeHtml, type Notice } from "./errorbox.js";
import type { T } from "./shell.js";
import { newId } from "./emulator.js";
import { MIN_GROUP, RULES, canShow, groupOpen, margin, mayAnswer, realAnswerFlags, sampleSize } from "./survey.js";
import { quickRating, rateUs, scoreScale } from "./peopleparts.js";
import type { AtEmit, AtLook, AtTier } from "./attenddesk.js";

type St = "queued" | "sent" | "accepted" | "confirmed" | "failed";
/** The plan numbers the screens show (services/billing.py FEATURES lynksurvey, passed in by the build; never typed here). */
export interface SvPlan { price_usd: number; creators_included: number; extra_creator_cents: number | null; answers_per_month: number; live_surveys: number | null; places: number | null;
  org_tree: string | null; lynkchat_way: boolean; basic_phone: boolean; field_and_paper: boolean; voice_call: boolean; write_it_for_me: boolean; logic: string; repeating: boolean;
  automatic: string[]; staff_journey: boolean; experience_dashboards: boolean; library_and_brand_kit: boolean; approval: boolean; call_back: boolean; rewards: boolean; panel: boolean;
  own_hardware: boolean; company_login: boolean; own_logo: boolean; api: string | boolean; research: string[]; downloads: string[]; reports: string; history_months: number | null; several_countries: boolean }
export const SV_KINDS = ["quick_rating", "satisfaction", "recommend", "staff_pulse", "staff_journey", "poll", "event_feedback", "research", "consultation", "what_matters_most", "trade_off", "form"] as const;
export type SvKind = (typeof SV_KINDS)[number];
export const SV_QTYPES = ["choice", "many", "yes_no", "stars", "rating", "score", "number", "date", "short", "long", "ranking", "spoken", "best_worst", "offer_pick"] as const;
export type SvQType = (typeof SV_QTYPES)[number];
const SV_BASIC: readonly string[] = ["choice", "yes_no", "stars", "rating", "score", "short"];
export const SV_WAYS = ["smartphone", "website", "lynkchat", "basic_phone", "voice", "kiosk", "pos", "email", "field", "paper"] as const;
export type SvWay = (typeof SV_WAYS)[number];
const SV_WAY_FEATURE: Partial<Record<SvWay, keyof SvPlan>> = { lynkchat: "lynkchat_way", basic_phone: "basic_phone", field: "field_and_paper", paper: "field_and_paper", voice: "voice_call" };
const SV_PARTNER_WAYS: readonly string[] = ["basic_phone", "voice"];          // need the people_messages or survey_voice partner in that country
const SV_SHARED_WAYS: readonly string[] = ["kiosk", "pos", "field", "paper"];
const SV_KIND_RESEARCH: Partial<Record<SvKind, string>> = { what_matters_most: "what_matters_most", trade_off: "trade_off" };
/** The clear question check (people/survey.py check_questions): pushing towards an answer, too long, two in one, sensitive topics. */
const SV_LEADING = ["don't you agree", "dont you agree", "do you agree that our", "isn't it", "wouldn't you", "surely", "how great", "how much do you love", "don't you think"];
const SV_SENSITIVE = ["health", "illness", "disease", "religion", "faith", "church", "mosque", "politic", "party", "vote", "sexual", "ethnic", "tribe", "income", "salary"];
export const SV_LONG = 140, SV_UNHAPPY: Record<string, number> = { rating: 2, stars: 2, score: 6 };
export const SV_DEVICE_KINDS = ["kiosk", "tablet", "pos", "field", "screen", "counter_display", "button_stand", "printer", "scanner", "speaker"] as const;
export type SvDevKind = (typeof SV_DEVICE_KINDS)[number];
const SV_NO_DISPLAY: readonly string[] = ["button_stand", "printer", "scanner", "speaker"];   // run through LynkDriver; paid tiers
/** The ecosystem names of the display devices (catalog/devices.v1.json lynk_names; the same in every language). */
export const SV_LYNK: Partial<Record<SvDevKind, string>> = { kiosk: "LynkKiosk", tablet: "LynkTab", pos: "LynkPOS", field: "LynkMobile", screen: "LynkDScreen", counter_display: "LynkCDisplay" };
/** File formats are names, shown as they are in every language (the spreadsheet is a word). */
const SV_FORMATS: Record<string, string> = { csv: "CSV", spss: "SPSS", stata: "Stata", r: "R" };
export const SV_MARGINS = [3, 5, 10] as const;
/** A plan with every part open, for a device that was given no plan numbers (tests); real screens always get services/billing.py's. */
export const SV_OPEN_PLAN: SvPlan = { price_usd: 0, creators_included: 5, extra_creator_cents: 0, answers_per_month: 0, live_surveys: null, places: null, org_tree: "full", lynkchat_way: true, basic_phone: true,
  field_and_paper: true, voice_call: true, write_it_for_me: true, logic: "full", repeating: true, automatic: ["all", "api"], staff_journey: true, experience_dashboards: true, library_and_brand_kit: true, approval: true,
  call_back: true, rewards: true, panel: true, own_hardware: true, company_login: true, own_logo: true, api: "full", research: ["margins", "sample_size", "research_record", "compare_groups", "before_after", "themes",
  "real_difference", "groups_to_fill", "balancing", "what_matters_most", "trade_off"], downloads: ["spreadsheet", "csv", "spss", "stata", "r"], reports: "custom", history_months: null, several_countries: true };
export const SV_LANGUAGES = 38;                     // every language of design/fonts/scripts.v1.json

export interface SvQ { id: string; type: SvQType; key: string | null; text: string; choices: { key: string | null; text: string }[] }
export interface SvSurvey { id: string; kind: SvKind; rule: (typeof RULES)[number]; anonymous: boolean; version: number; state: "draft" | "waiting_for_approval" | "sent_back" | "approved" | "open" | "paused" | "closed" | "test";
  questions: SvQ[]; whyOnlyIfUnhappy: boolean; targets: Record<string, number>; after: string | null; repeatDays: number | null; note: string; by: "me" | "other"; library: boolean; sample: boolean; st: St }
export interface SvAnswer { id: string; survey: string; version: number; way: SvWay; place: string; group: string; answers: Record<string, { number?: number; choice?: string; text?: string }>;
  result: "accepted" | "please_check" | "set_aside"; reason: string | null; test: boolean; at: number; st: St; sample: boolean; callBack: boolean; enteredBy: boolean }
interface SvTask { id: string; answer: string; state: "created" | "done"; due: number }
interface SvReward { id: string; answer: string; kind: "airtime" | "credit" | "voucher" | "cash"; state: "sent" | "paid" | "failed" | "coming_to_country"; amount: number }
interface SvDevice { id: string; kind: SvDevKind; locked: boolean; state: St }
interface SvLine { at: number; what: string; survey: string | null }
export const SV_PLACES = ["ppl_sv_place_a", "ppl_sv_place_b"] as const;
export const SV_GROUPS = ["ppl_sv_group_women", "ppl_sv_group_men"] as const;
const SV_SEED_TEXTS = ["ppl_sv_text_wait", "ppl_sv_text_kind", "ppl_sv_text_price", "ppl_sv_text_clean", "ppl_sv_text_slow", "ppl_sv_text_rude"];
/** The themes LynkAssist groups written answers into (sandbox keyword groups, labelled a suggestion, checked and corrected by the researcher). */
const SV_THEMES: Record<string, string[]> = { waiting_time: ["ppl_sv_text_wait", "ppl_sv_text_slow"], staff_kindness: ["ppl_sv_text_kind", "ppl_sv_text_rude"], price: ["ppl_sv_text_price"], cleanliness: ["ppl_sv_text_clean"] };

const q = (id: string, type: SvQType, key: string, choices: string[] = []): SvQ => ({ id, type, key, text: "", choices: choices.map((c) => ({ key: c, text: "" })) });
/** Ready-made questions for each kind (the creator changes anything); words are keys, so they show in the reader's language. */
export function svTemplate(kind: SvKind): SvQ[] {
  switch (kind) {
    case "quick_rating": return [q("visit", "rating", "ppl_rate_title")];
    case "recommend": return [q("recommend", "score", "ppl_sv_q_recommend"), q("why", "long", "ppl_sv_q_why_score")];
    case "staff_pulse": case "staff_journey": return [q("feel", "rating", "ppl_sv_q_feel"), q("tools", "yes_no", "ppl_sv_q_tools"), q("change", "long", "ppl_sv_q_change")];
    case "poll": return [q("pick", "choice", "ppl_sv_q_pick", ["ppl_sv_c_morning", "ppl_sv_c_afternoon", "ppl_sv_c_evening"])];
    case "what_matters_most": return [q("most", "best_worst", "ppl_sv_q_most", ["ppl_sv_c_speed", "ppl_sv_c_price", "ppl_sv_c_kindness"])];
    case "trade_off": return [q("offer", "offer_pick", "ppl_sv_q_offer", ["ppl_sv_c_offer_a", "ppl_sv_c_offer_b"])];
    case "form": return [q("name", "short", "ppl_sv_q_name"), q("request", "long", "ppl_sv_q_request")];
    default: return [q("visit", "rating", "ppl_rate_title"), q("wait", "choice", "ppl_sv_q_wait", ["ppl_sv_c_under5", "ppl_sv_c_5to15", "ppl_sv_c_over15"]), q("again", "yes_no", "ppl_sv_q_again"), q("better", "long", "ppl_sv_q_better")];
  }
}
/** "Write it for me" (sandbox LynkAssist, people/survey.py write_it_for_me): one sentence becomes a draft, labelled a suggestion. */
export function svWriteIt(sentence: string): { kind: SvKind; questions: SvQ[] } {
  const low = sentence.toLowerCase();
  const has = (...w: string[]): boolean => w.some((x) => low.includes(x));
  const kind: SvKind = has("come back", "return", "lose", "loyal", "recommend") ? "recommend" : has("staff", "team", "employee", "workers") ? "staff_pulse" : "satisfaction";
  return { kind, questions: svTemplate(kind) };
}
/** The clear question check on what a creator typed. */
export function svCheck(qs: readonly SvQ[]): { q: string; problem: "pushes_towards_an_answer" | "too_long" | "two_questions_in_one" | "sensitive_topic" }[] {
  const out: { q: string; problem: "pushes_towards_an_answer" | "too_long" | "two_questions_in_one" | "sensitive_topic" }[] = [];
  for (const x of qs) {
    if (x.key) continue;
    const low = x.text.toLowerCase();
    if (SV_LEADING.some((w) => low.includes(w))) out.push({ q: x.id, problem: "pushes_towards_an_answer" });
    if (x.text.length > SV_LONG) out.push({ q: x.id, problem: "too_long" });
    if ((x.text.match(/\?/g) ?? []).length > 1 || (low.includes(" and ") && ["rating", "stars", "score", "yes_no"].includes(x.type))) out.push({ q: x.id, problem: "two_questions_in_one" });
    if (SV_SENSITIVE.some((w) => low.includes(w))) out.push({ q: x.id, problem: "sensitive_topic" });
  }
  return out;
}
/** "Real difference or chance?" at 95%, in plain words (people/survey.py real_difference). */
export function svRealDifference(p1: number, n1: number, p2: number, n2: number): "too_few" | "no_difference" | "real" | "could_be_chance" {
  if (Math.min(n1, n2) < MIN_GROUP) return "too_few";
  const a = p1 / 100, b = p2 / 100, pool = (a * n1 + b * n2) / (n1 + n2), se = Math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2));
  if (se === 0) return a === b ? "no_difference" : "real";
  return Math.abs(a - b) / se >= 1.96 ? "real" : "could_be_chance";
}
const pct = (k: number, n: number): number => Math.floor((k * 100) / n + 0.5);
/** A short check value over the answers and the method, so anyone can see the results were not changed (the cloud's is SHA-256). */
export function svDigest(text: string): string {
  let h1 = 0x811c9dc5, h2 = 0x01000193;
  for (let i = 0; i < text.length; i++) { const c = text.charCodeAt(i); h1 = Math.imul(h1 ^ c, 16777619) >>> 0; h2 = Math.imul(h2 + c, 2246822519) >>> 0; }
  return (h1.toString(16).padStart(8, "0") + h2.toString(16).padStart(8, "0")).toUpperCase();
}

export class SurveyDesk {
  readonly placeId = newId();
  deviceId = newId();
  tier: AtTier = "plus";
  approvalOn = false;
  surveys: SvSurvey[] = [];
  answers: SvAnswer[] = [];
  tasks: SvTask[] = [];
  rewards: SvReward[] = [];
  devices: SvDevice[] = [];
  history: SvLine[] = [];
  said: { survey: string; text: string; told: number; public: boolean }[] = [];
  verified: Record<string, string> = {};
  optedOut = false;
  /** Answers this organisation received earlier this month (the plan's count); on LynkSurvey Free the day the limit is reached still works. */
  earlierThisMonth = 0;
  creatorsActive = 1;
  panelMembers = 1240;
  // what the screens are in the middle of
  cur = "";
  draft: SvSurvey;
  sentence = "";
  wrote = false;
  marginPick: (typeof SV_MARGINS)[number] = 5;
  population = "";
  preview: "smartphone" | "basic_phone" | "kiosk" | "pos" | "voice" = "smartphone";
  filterWay = "";
  compareBy: "group" | "place" | "way" = "group";
  refused = "";
  kiosk = { i: 0, answers: {} as SvAnswer["answers"], done: false, started: 0 };
  phone = { step: "consent" as "consent" | "code" | "question" | "done", i: 0, answers: {} as SvAnswer["answers"], code: "", consent: false, way: "smartphone" as SvWay, note: "", sent: [] as number[] };
  panel = { country: "GH", wanted: 500, reached: null as number | null };
  youSaid = "";
  addKind: SvDevKind = "kiosk";
  /** The person entering answers on this device is a field worker (answers are marked "Entered by staff"). */
  field = false;
  constructor(private emit: AtEmit, readonly plans: Record<AtTier, SvPlan>, private now: () => number = Date.now) {
    const main: SvSurvey = this.blank("satisfaction"); main.state = "open"; main.sample = true; main.st = "confirmed"; main.after = "lynkqueue";
    const research: SvSurvey = { ...this.blank("research"), questions: [...svTemplate("satisfaction").slice(0, 1), q("most", "best_worst", "ppl_sv_q_most", ["ppl_sv_c_speed", "ppl_sv_c_price", "ppl_sv_c_kindness"]), q("offer", "offer_pick", "ppl_sv_q_offer", ["ppl_sv_c_offer_a", "ppl_sv_c_offer_b"])], sample: true, st: "confirmed" };
    this.surveys = [main, research]; this.cur = main.id; this.draft = this.blank("satisfaction");
    // SANDBOX answers so results and research tools have something to read (labelled wherever shown)
    const seq = [5, 4, 4, 5, 3, 4, 2, 5, 4, 1, 4, 5, 3, 4, 5, 2, 4, 4, 5, 3, 1, 4, 5, 4, 2, 4];
    seq.forEach((r, i) => {
      const a: SvAnswer = { id: newId(), survey: main.id, version: 1, way: (["kiosk", "smartphone", "pos", "field"] as const)[i % 4]!, place: SV_PLACES[i % 2]!, group: SV_GROUPS[i % 3 === 0 ? 1 : 0]!,
        answers: { visit: { number: r }, wait: { choice: ["ppl_sv_c_under5", "ppl_sv_c_5to15", "ppl_sv_c_over15"][r <= 2 ? 2 : r === 3 ? 1 : 0]! }, again: { choice: r >= 3 ? "yes" : "no" }, better: { text: SV_SEED_TEXTS[i % SV_SEED_TEXTS.length]! } },
        result: "accepted", reason: null, test: false, at: this.now() - (seq.length - i) * 600000, st: "confirmed", sample: true, callBack: r <= 2 && i % 2 === 0, enteredBy: i % 4 === 3 };
      this.answers.push(a);
      const ra: SvAnswer = { ...a, id: newId(), survey: research.id, answers: { visit: { number: r }, most: { choice: i % 3 ? "ppl_sv_c_speed|ppl_sv_c_price" : "ppl_sv_c_kindness|ppl_sv_c_price" }, offer: { choice: i % 3 ? "ppl_sv_c_offer_a" : "ppl_sv_c_offer_b" } } };
      this.answers.push(ra);
    });
    const flagged = this.answers[4]!; flagged.result = "please_check"; flagged.reason = "too_fast";        // an answer of the main survey
    for (const a of this.answers.filter((x) => x.survey === main.id && x.callBack)) this.tasks.push({ id: newId(), answer: a.id, state: "created", due: this.now() + 48 * 3600000 });
    this.devices = [{ id: this.deviceId, kind: "tablet", locked: false, state: "confirmed" }, { id: newId(), kind: "kiosk", locked: false, state: "confirmed" }, { id: newId(), kind: "screen", locked: false, state: "confirmed" },
      { id: newId(), kind: "counter_display", locked: false, state: "confirmed" }, { id: newId(), kind: "pos", locked: false, state: "confirmed" }];
  }
  get plan(): SvPlan { return this.plans[this.tier]; }
  sv(id = this.cur): SvSurvey | undefined { return this.surveys.find((s) => s.id === id); }
  qText(x: { key: string | null; text: string }, t: T): string { return x.key ? t(x.key) : x.text; }
  private log(what: string, survey: string | null = null): void { this.history.unshift({ at: this.now(), what, survey }); }
  blank(kind: SvKind): SvSurvey {
    return { id: newId(), kind, rule: "open", anonymous: false, version: 1, state: "draft", questions: svTemplate(kind), whyOnlyIfUnhappy: true, targets: {}, after: null, repeatDays: null, note: "", by: "me", library: false, sample: false, st: "queued" };
  }

  // ---- building -----------------------------------------------------------------------------------------------------------
  kindAllowed(k: SvKind): boolean { const r = SV_KIND_RESEARCH[k]; return (k !== "staff_journey" || this.plan.staff_journey) && (!r || this.plan.research.includes(r)); }
  typeAllowed(ty: SvQType): boolean { return this.plan.logic !== "basic" || SV_BASIC.includes(ty); }
  pickKind(k: SvKind): void { if (this.kindAllowed(k)) { this.draft = { ...this.draft, kind: k, questions: svTemplate(k) }; this.wrote = false; } }
  writeIt(): void {
    if (!this.plan.write_it_for_me || !this.sentence.trim()) return;
    const w = svWriteIt(this.sentence); this.draft = { ...this.draft, kind: w.kind, questions: w.questions.filter((x) => this.typeAllowed(x.type)) }; this.wrote = true;
  }
  addQuestion(ty: SvQType): void { if (!this.typeAllowed(ty)) return; const n = this.draft.questions.length + 1; this.draft.questions.push({ id: `q${n}_${ty}`.slice(0, 64), type: ty, key: null, text: "", choices: ty === "choice" || ty === "many" || ty === "best_worst" || ty === "offer_pick" || ty === "ranking" ? [{ key: null, text: "" }, { key: null, text: "" }] : [] }); }
  removeQuestion(i: number): void { if (this.draft.questions.length > 1) this.draft.questions.splice(i, 1); }
  liveCount(): number { return this.surveys.filter((s) => s.state === "open").length; }
  /** Saves the draft: a new survey, or a new version of one that already has answers (answers are never mixed). */
  save(): SvSurvey {
    const d = this.draft, existing = this.surveys.find((s) => s.id === d.id);
    if (existing) {
      const answered = this.answers.some((a) => a.survey === d.id && a.version === existing.version && !a.test);
      Object.assign(existing, { ...d, version: answered ? existing.version + 1 : existing.version, state: existing.state === "approved" || existing.state === "sent_back" ? "draft" : existing.state });
      this.emit("SurveySaved", { survey_id: existing.id, version: existing.version, kind: existing.kind, rule: existing.rule, anonymous: existing.anonymous, languages: ["en"] });
      this.log("changed", existing.id); this.draft = { ...existing, questions: existing.questions.map((x) => ({ ...x, choices: [...x.choices] })) }; return existing;
    }
    const s: SvSurvey = { ...d, questions: d.questions.map((x) => ({ ...x, choices: [...x.choices] })), st: "queued" };
    this.surveys.unshift(s); this.cur = s.id;
    this.emit("SurveySaved", { survey_id: s.id, version: 1, kind: s.kind, rule: s.rule, anonymous: s.anonymous, languages: ["en"] });
    this.log("built", s.id); this.draft = { ...s, questions: s.questions.map((x) => ({ ...x, choices: [...x.choices] })) }; return s;
  }
  edit(id: string): void { const s = this.sv(id); if (s) { this.draft = { ...s, questions: s.questions.map((x) => ({ ...x, choices: [...x.choices] })) }; this.cur = id; } }
  submit(id: string): void { const s = this.sv(id); if (s && this.approvalOn) { s.state = "waiting_for_approval"; this.log("sent_for_approval", id); } }
  decide(id: string, decision: "approve" | "send_back"): void {
    const s = this.sv(id); if (!s || s.state !== "waiting_for_approval") return;
    s.state = decision === "approve" ? "approved" : "sent_back"; s.note = decision === "send_back" ? "ppl_sv_note_shorter" : "";
    this.emit("SurveyApproval", { survey_id: s.id, version: s.version, decision, by: this.placeId }); this.log(`approval_${decision}`, id);
  }
  /** Open, pause, close or test mode; opening checks approval and the plan's live-survey number. */
  setState(id: string, state: "open" | "paused" | "closed" | "test"): boolean {
    const s = this.sv(id); this.refused = ""; if (!s) return false;
    if (state === "open") {
      if (this.approvalOn && !["approved", "paused"].includes(s.state)) { this.refused = "needs_approval_first"; return false; }
      if (this.plan.live_surveys !== null && s.state !== "open" && this.liveCount() >= this.plan.live_surveys) { this.refused = "plan_limit_live_surveys"; return false; }
    }
    s.state = state; this.emit("SurveyStateChanged", { survey_id: s.id, state }); this.log(`state_${state}`, id); return true;
  }

  // ---- answering ----------------------------------------------------------------------------------------------------------
  wayWhy(way: SvWay, partner: boolean): "" | "plan" | "coming_soon" {
    const f = SV_WAY_FEATURE[way]; if (f && !this.plan[f]) return "plan";
    if (SV_PARTNER_WAYS.includes(way) && partner) return "coming_soon";
    return "";
  }
  /** One answer: plan, rule, groups to fill, "Real answers only" (a flag, never a deletion), the five states and the event. */
  answer(survey: string, way: SvWay, answers: SvAnswer["answers"], o: { seconds?: number; group?: string; online: boolean; place?: string }): SvAnswer | null {
    const s = this.sv(survey); this.refused = "";
    if (!s || !["open", "test"].includes(s.state)) { this.refused = "survey_closed"; return null; }
    if (this.plan.extra_creator_cents === null && this.earlierThisMonth + this.received() >= this.plan.answers_per_month && !this.answeredToday()) { this.refused = "free_limit_reached"; return null; }
    const why = mayAnswer(s.rule, false, true, true, true); if (why) { this.refused = why; return null; }
    const group = o.group ?? SV_GROUPS[0];
    if (Object.keys(s.targets).length && !groupOpen(group!, this.groupCounts(survey), s.targets)) { this.refused = "group_full"; return null; }
    const nums = Object.values(answers).map((v) => v.number ?? v.choice).filter((v) => v !== undefined);
    const flags = realAnswerFlags(o.seconds ?? 60, Object.keys(answers).length, nums.length >= 5 && new Set(nums).size === 1, 1, SV_SHARED_WAYS.includes(way));
    const a: SvAnswer = { id: newId(), survey, version: s.version, way, place: o.place ?? SV_PLACES[0]!, group: group!, answers, result: flags.length ? "please_check" : "accepted", reason: flags[0] ?? null,
      test: s.state === "test", at: this.now(), st: o.online ? "sent" : "queued", sample: false, callBack: false, enteredBy: this.field && (way === "field" || way === "paper") };
    this.answers.push(a);
    const p: Record<string, unknown> = { answer_id: a.id, survey_id: survey, version: s.version, way, device_id: this.deviceId, language: "en",
      answers: Object.entries(answers).map(([k, v]) => ({ q: k, ...v })) };
    if (a.test) p.test = true;
    if (a.enteredBy) p.entered_by = this.placeId;
    this.emit("SurveyAnswered", p);
    if (o.online) setTimeout(() => { a.st = "accepted"; }, 900);
    return a;
  }
  received(): number { return this.answers.filter((a) => !a.test && !a.sample && a.at >= this.now() - 31 * 86400000).length; }
  private answeredToday(): boolean { return false; }
  groupCounts(survey: string): Record<string, number> {
    const out: Record<string, number> = {};
    for (const a of this.answers) if (a.survey === survey && !a.test && a.result === "accepted") out[a.group] = (out[a.group] ?? 0) + 1;
    return out;
  }
  onlineAgain(): void { for (const a of this.answers) if (a.st === "queued") { a.st = "sent"; setTimeout(() => { a.st = "accepted"; }, 900); } }
  decideFlag(id: string, keep: boolean): void { const a = this.answers.find((x) => x.id === id); if (a && a.result === "please_check") { a.result = keep ? "accepted" : "set_aside"; this.log(keep ? "kept_answer" : "set_answer_aside", a.survey); } }

  // ---- results (never for fewer than 5) and the research tools ----------------------------------------------------------------
  rows(survey = this.cur, f: { way?: string; group?: string; place?: string; version?: number } = {}): SvAnswer[] {
    const s = this.sv(survey); const v = f.version ?? s?.version ?? 1;
    return this.answers.filter((a) => a.survey === survey && !a.test && a.result === "accepted" && a.version === v && (!f.way || a.way === f.way) && (!f.group || a.group === f.group) && (!f.place || a.place === f.place));
  }
  /** One question's result: average and the good share with its margin, or the share of each choice; null below 5 answers. */
  result(qn: SvQ, rows: SvAnswer[]): { n: number; avgTenths?: number; good?: number; margin?: number | null; recommend?: number; shares?: { c: string; p: number; m: number | null }[]; written?: number } | null {
    const got = rows.map((r) => r.answers[qn.id]).filter((x): x is NonNullable<typeof x> => !!x);
    if (!canShow(got.length)) return null;
    if (["rating", "stars", "score", "number"].includes(qn.type)) {
      const nums = got.map((x) => x.number).filter((x): x is number => typeof x === "number"); if (!canShow(nums.length)) return null;
      const good = pct(nums.filter((x) => x >= (qn.type === "score" ? 9 : 4)).length, nums.length);
      const out: { n: number; avgTenths: number; good: number; margin: number | null; recommend?: number } = { n: nums.length, avgTenths: Math.floor((nums.reduce((a, b) => a + b, 0) * 10) / nums.length + 0.5), good, margin: margin(good, nums.length) };
      if (qn.type === "score") out.recommend = Math.round(((nums.filter((x) => x >= 9).length - nums.filter((x) => x <= 6).length) * 100) / nums.length);
      return out;
    }
    if (["choice", "yes_no", "many"].includes(qn.type)) {
      const c: Record<string, number> = {};
      for (const x of got) for (const v of (qn.type === "many" ? (x.choice ?? "").split("|") : [x.choice ?? ""])) c[v] = (c[v] ?? 0) + 1;
      return { n: got.length, shares: Object.entries(c).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ c: k, p: pct(v, got.length), m: margin(pct(v, got.length), got.length) })) };
    }
    return { n: got.length, written: got.filter((x) => x.text).length };
  }
  compare(qn: SvQ, by: "group" | "place" | "way"): { v: string; r: ReturnType<SurveyDesk["result"]> }[] {
    const vals = by === "group" ? [...SV_GROUPS] : by === "place" ? [...SV_PLACES] : [...new Set(this.rows().map((a) => a.way))];
    return vals.map((v) => ({ v, r: this.result(qn, this.rows(this.cur, { [by]: v })) }));
  }
  /** Balancing: the good share re-weighted so the groups match the population (shares in whole percents that add to 100). */
  balanced(qn: SvQ, women: number): { raw: number; balanced: number } | null {
    const all = this.result(qn, this.rows()); if (!all || all.good === undefined) return null;
    const w = this.result(qn, this.rows(this.cur, { group: SV_GROUPS[0] })), m = this.result(qn, this.rows(this.cur, { group: SV_GROUPS[1] }));
    if (!w || !m || w.good === undefined || m.good === undefined) return null;
    return { raw: all.good, balanced: Math.floor((w.good * women + m.good * (100 - women)) / 100 + 0.5) };
  }
  themes(qn: SvQ): { theme: string; p: number }[] | null {
    const texts = this.rows().map((a) => a.answers[qn.id]?.text).filter((x): x is string => !!x);
    if (!canShow(texts.length)) return null;
    const basic = !this.plan.research.includes("themes");
    return Object.entries(SV_THEMES).map(([k, keys]) => ({ theme: k, p: pct(texts.filter((x) => keys.includes(x)).length, texts.length) })).filter((x) => x.p > 0 && (!basic || x.p >= 20)).sort((a, b) => b.p - a.p);
  }
  bestWorst(qn: SvQ): string[] | null {
    const got = this.rows().map((a) => a.answers[qn.id]?.choice).filter((x): x is string => !!x); if (!canShow(got.length)) return null;
    const sc: Record<string, number> = {};
    for (const x of got) { const [b = "", w = ""] = x.split("|"); sc[b] = (sc[b] ?? 0) + 1; sc[w] = (sc[w] ?? 0) - 1; }
    return Object.entries(sc).filter(([k]) => k).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([k]) => k);
  }
  summary(): { lines: string[] } | null { return canShow(this.rows().length) ? { lines: [] } : null; }
  verify(): string {
    const s = this.sv(); if (!s) return "";
    const body = JSON.stringify(this.rows().map((a) => [a.id, a.answers])) + JSON.stringify({ rule: s.rule, anonymous: s.anonymous, version: s.version, kind: s.kind });
    const d = svDigest(body); this.verified[s.id] = d; this.log("results_verified", s.id); return d;
  }
  stillTrue(): boolean | null {
    const s = this.sv(); const d = s && this.verified[s.id]; if (!s || !d) return null;
    return svDigest(JSON.stringify(this.rows().map((a) => [a.id, a.answers])) + JSON.stringify({ rule: s.rule, anonymous: s.anonymous, version: s.version, kind: s.kind })) === d;
  }
  csv(): string {
    const s = this.sv(), rows = this.rows(); if (!s || !canShow(rows.length)) return "";
    const head = ["answer", ...s.questions.map((x) => x.id), "way"].join(",");
    return [head, ...rows.slice(0, 3).map((r, i) => [i + 1, ...s.questions.map((x) => { const v = r.answers[x.id]; return v ? String(v.number ?? v.choice ?? (v.text ? "…" : "")) : ""; }), r.way].join(","))].join("\n");
  }

  // ---- closing the loop, rewards and the panel ------------------------------------------------------------------------------
  callBackDone(id: string): void {
    const tk = this.tasks.find((x) => x.id === id); if (!tk || tk.state === "done") return;
    tk.state = "done"; this.emit("SurveyCallBack", { task_id: tk.id, answer_id: tk.answer, state: "done", by: this.placeId }); this.log("call_back_done", this.cur);
  }
  sendYouSaid(): void {
    const s = this.sv(); if (!s || !this.youSaid.trim() || !this.plan.call_back) return;
    const told = s.anonymous ? 0 : new Set(this.rows().filter((a) => !a.sample).map((a) => a.id)).size;
    this.said.unshift({ survey: s.id, text: this.youSaid.trim(), told, public: s.anonymous }); this.youSaid = ""; this.log("you_said_we_did", s.id);
  }
  /** A reward after the "Real answers only" check, one per person per survey, through the partner; cash given by a field worker is recorded. */
  reward(answer: string, kind: SvReward["kind"], partner: boolean): void {
    const a = this.answers.find((x) => x.id === answer); this.refused = "";
    if (!this.plan.rewards || !a || a.result !== "accepted" || a.test) { this.refused = "only_after_the_check"; return; }
    if (this.rewards.some((r) => r.answer === answer)) { this.refused = "one_reward_per_person"; return; }
    const r: SvReward = { id: newId(), answer, kind, state: kind === "cash" ? "paid" : partner ? "coming_to_country" : "sent", amount: 500 };
    this.rewards.unshift(r);
    if (kind === "cash") this.emit("SurveyCashRewardRecorded", { reward_id: r.id, answer_id: answer, amount: r.amount, currency: "XAF" });
  }
  partnerAnswer(id: string, result: "paid" | "failed"): void { const r = this.rewards.find((x) => x.id === id); if (r && r.state === "sent") r.state = result; }
  askPanel(): void { if (this.plan.panel) this.panel.reached = Math.min(this.panel.wanted, this.panelMembers); }

  // ---- devices and the plan -------------------------------------------------------------------------------------------------
  has(kind: SvDevKind): boolean { return (this.plan.own_hardware || !SV_NO_DISPLAY.includes(kind)) && this.devices.some((d) => d.kind === kind && !d.locked && d.state === "confirmed"); }
  addDevice(online: boolean, redraw: () => void): void {
    this.refused = "";
    if (SV_NO_DISPLAY.includes(this.addKind) && !this.plan.own_hardware) { this.refused = "plan_no_hardware_without_display"; return; }
    const d: SvDevice = { id: newId(), kind: this.addKind, locked: false, state: online ? "sent" : "queued" }; this.devices.push(d); this.log(`device_${this.addKind}`);
    if (online) setTimeout(() => { d.state = "confirmed"; redraw(); }, 1200);
  }
  lock(id: string): void { const d = this.devices.find((x) => x.id === id); if (d && d.id !== this.deviceId) { d.locked = true; this.log("device_locked"); } }
  usage(): { answers: number; included: number; creators: number; creatorsIncluded: number; extraCents: number; freeStops: boolean } {
    const answers = this.earlierThisMonth + this.received(), p = this.plan;
    const over = Math.max(0, answers - p.answers_per_month), extraCreators = Math.max(0, this.creatorsActive - p.creators_included);
    return { answers, included: p.answers_per_month, creators: this.creatorsActive, creatorsIncluded: p.creators_included, extraCents: p.extra_creator_cents === null ? 0 : extraCreators * p.extra_creator_cents + Math.ceil(over / 1000) * 100, freeStops: p.extra_creator_cents === null && over > 0 };
  }

  // ---- the kiosk and the person's phone: one question at a time --------------------------------------------------------------
  visible(s: SvSurvey, got: SvAnswer["answers"]): SvQ[] {
    const first = s.questions[0];
    return s.questions.filter((x, i) => {
      if (i === 0 || !s.whyOnlyIfUnhappy || x.type !== "long" || !first || !(first.type in SV_UNHAPPY)) return true;
      const n = got[first.id]?.number; return n !== undefined && n <= SV_UNHAPPY[first.type]!;      // "Why?" appears only after an unhappy answer
    });
  }
  give(who: "kiosk" | "phone", qid: string, v: { number?: number; choice?: string; text?: string }): void {
    const st = who === "kiosk" ? this.kiosk : this.phone; st.answers[qid] = v;
  }
  next(who: "kiosk" | "phone", online: boolean): void {
    const s = this.sv(); if (!s) return;
    const st = who === "kiosk" ? this.kiosk : this.phone, list = this.visible(s, st.answers);
    if (st.i + 1 < list.length) { st.i += 1; return; }
    const a = this.answer(s.id, who === "kiosk" ? (this.field ? "field" : "kiosk") : this.phone.way, st.answers, { online, seconds: who === "kiosk" ? Math.max(20, Math.round((this.now() - this.kiosk.started) / 1000)) : 40 });
    if (who === "kiosk") { this.kiosk.done = !!a; } else { this.phone.step = a ? "done" : this.phone.step; this.phone.note = a ? "" : this.refused; }
  }
  restartKiosk(): void { this.kiosk = { i: 0, answers: {}, done: false, started: this.now() }; }

  act(a: string, ctx: { online: boolean; partner: boolean; redraw: () => void }): boolean {
    if (!a.startsWith("sv:")) return false;
    const [, k = "", v = "", w = ""] = a.split(":");
    switch (k) {
      case "open": if (this.sv(v)) { this.cur = v; this.restartKiosk(); this.phone = { ...this.phone, step: "consent", i: 0, answers: {} }; } break;
      case "new": this.draft = this.blank("satisfaction"); this.sentence = ""; this.wrote = false; break;
      case "edit": this.edit(v); break;
      case "kind": this.pickKind(v as SvKind); break;
      case "write": this.writeIt(); break;
      case "addq": this.addQuestion(v as SvQType); break;
      case "rmq": this.removeQuestion(Number(v)); break;
      case "rule": if ((RULES as readonly string[]).includes(v)) this.draft.rule = v as SvSurvey["rule"]; break;
      case "anon": this.draft.anonymous = !this.draft.anonymous; break;
      case "why": this.draft.whyOnlyIfUnhappy = !this.draft.whyOnlyIfUnhappy; break;
      case "after": this.draft.after = this.draft.after === v ? null : v; break;
      case "repeat": if (this.plan.repeating) this.draft.repeatDays = this.draft.repeatDays ? null : 30; break;
      case "margin": { const n = Number(v); if ((SV_MARGINS as readonly number[]).includes(n)) this.marginPick = n as (typeof SV_MARGINS)[number]; break; }
      case "preview": if (["smartphone", "basic_phone", "kiosk", "pos", "voice"].includes(v)) this.preview = v as SurveyDesk["preview"]; break;
      case "save": this.save(); break;
      case "approval": if (this.plan.approval) this.approvalOn = !this.approvalOn; break;
      case "submit": this.submit(v); break;
      case "approve": this.decide(v, "approve"); break;
      case "sendback": this.decide(v, "send_back"); break;
      case "state": this.setState(v, w as "open" | "paused" | "closed" | "test"); break;
      case "library": { const s = this.sv(v); if (s && this.plan.library_and_brand_kit) s.library = !s.library; break; }
      case "way": this.filterWay = this.filterWay === v ? "" : v; break;
      case "cmp": if (["group", "place", "way"].includes(v)) this.compareBy = v as SurveyDesk["compareBy"]; break;
      case "keep": this.decideFlag(v, true); break;
      case "aside": this.decideFlag(v, false); break;
      case "verify": this.verify(); break;
      case "cbdone": this.callBackDone(v); break;
      case "yousaid": this.sendYouSaid(); break;
      case "reward": this.reward(v, (w || "airtime") as SvReward["kind"], ctx.partner); break;
      case "rpaid": this.partnerAnswer(v, w === "failed" ? "failed" : "paid"); break;
      case "panel": this.askPanel(); break;
      case "devkind": if ((SV_DEVICE_KINDS as readonly string[]).includes(v)) this.addKind = v as SvDevKind; break;
      case "adddev": this.addDevice(ctx.online, ctx.redraw); break;
      case "lock": this.lock(v); break;
      case "field": this.field = !this.field; break;
      // the kiosk and the person's phone
      case "k": { const s = this.sv(); const qn = s && this.visible(s, this.kiosk.answers)[this.kiosk.i]; if (qn) this.give("kiosk", qn.id, w === "c" ? { choice: v } : { number: Number(v) }); break; }
      case "knext": this.next("kiosk", ctx.online); break;
      case "kagain": this.restartKiosk(); break;
      case "pway": if ((SV_WAYS as readonly string[]).includes(v)) { this.phone.way = v as SvWay; this.phone.note = ""; } break;
      case "pconsent": this.phone.consent = !this.phone.consent; break;
      case "pstart": { const s = this.sv(); const why = this.wayWhy(this.phone.way, ctx.partner); this.phone.note = why;
        if (!why && s && (!s.questions.some((x) => svCheck([x]).some((c) => c.problem === "sensitive_topic")) || this.phone.consent)) { this.phone.step = s.rule === "one_per_phone" ? "code" : "question"; if (this.phone.step === "code") this.phone.sent = [Date.now() / 1000]; } break; }
      case "presend": if (!resendWait(this.phone.sent, Date.now() / 1000)) this.phone.sent = [...this.phone.sent, Date.now() / 1000]; break;
      case "pcode": if (/^\d{6}$/.test(this.phone.code)) this.phone.step = "question"; break;
      case "p": { const s = this.sv(); const qn = s && this.visible(s, this.phone.answers)[this.phone.i]; if (qn) this.give("phone", qn.id, w === "c" ? { choice: v } : { number: Number(v) }); break; }
      case "pnext": this.next("phone", ctx.online); break;
      case "pagain": this.phone = { ...this.phone, step: "consent", i: 0, answers: {}, code: "", note: "" }; break;
      case "optout": this.optedOut = true; break;
      default: return false;
    }
    return true;
  }
  /** Typed fields and selects ("sv:..."), so the screen can be redrawn without losing them. */
  input(k: string, v: string): boolean {
    const [p, f = "", c = "", d = ""] = k.split(":"); if (p !== "sv") return false;
    const qn = this.draft.questions[Number(c)];
    // Plain typing needs no redraw (the box keeps its place and the person keeps typing); the rest redraw what they change.
    if (f === "sentence") { this.sentence = v.slice(0, 200); return false; }
    if (f === "qtext" && qn) { qn.text = v.slice(0, 300); qn.key = null; return false; }
    if (f === "qchoice" && qn && qn.choices[Number(d)]) { qn.choices[Number(d)] = { key: null, text: v.slice(0, 120) }; return false; }
    if (f === "yousaid") { this.youSaid = v.slice(0, 300); return false; }
    if (f === "ktext") { this.give("kiosk", c, { text: v.slice(0, 1000) }); return false; }
    if (f === "ptext") { this.give("phone", c, { text: v.slice(0, 1000) }); return false; }
    if (f === "target") { const n = Number(v); if (Number.isInteger(n) && n >= 0 && this.plan.research.includes("groups_to_fill")) { if (n) this.draft.targets[c] = n; else delete this.draft.targets[c]; } }
    else if (f === "population") this.population = v.replace(/[^0-9]/g, "").slice(0, 7);
    else if (f === "pcode") this.phone.code = asciiDigits(v).replace(/[^0-9]/g, "").slice(0, 6);
    else if (f === "pcountry") this.panel.country = v.slice(0, 2).toUpperCase();
    else if (f === "pwanted") { const n = Number(v); if (Number.isInteger(n) && n > 0) this.panel.wanted = Math.min(n, 100000); }
    else return false;
    return true;
  }
}

// ---- drawing ----------------------------------------------------------------------------------------------------------------
/** What a survey screen needs beyond the shared look: the organisation's name, and "Powered by LynkOmni" where the plan asks for it. */
export interface SvLook extends AtLook { place: string; powered: string; country?: string }   // country: the page's own country code, the example in the panel's country field
const svOn = (on: boolean): string => `aria-pressed="${on}"`;
const svOff = (off: boolean): string => (off ? "disabled" : "");
const svTag = (text: string, kind = ""): string => `<span class="tag ${kind}">${esc(text)}</span>`;
const svCard = (item: string, title: string, body: string): string => `<div class="card ph-card" data-item="${item}" role="group" aria-label="${esc(title)}"><h2>${esc(title)}</h2>${body}</div>`;
const svChip = (s: St, L: AtLook): string => `<span class="chip st-${s}">${L.icon(`status-${s}`)}<span>${esc(L.t(`st_${s}`))}</span></span>`;
const svRow = (name: string, sub: string, end = ""): string => `<li><div class="rowbtn static sv-row"><span class="main"><span class="nm">${name}</span><span class="sub">${sub}</span></span>${end}</div></li>`;
const svTenth = (n: number): string => (n / 10).toFixed(1);
const svPlanTag = (L: AtLook, tier: "plus" | "pro"): string => svTag(L.t(`ppl_sv_from_${tier}`));
export const svKindName = (k: string, t: T): string => t(`ppl_sv_kind_${k}`);
const svWayName = (w: string, t: T): string => t(`ppl_sv_way_${w}`);
const svState = (s: string, t: T): string => t(`ppl_sv_state_${s}`);
const svChoice = (c: string, t: T): string => (c === "yes" ? t("ppl_sv_yes") : c === "no" ? t("ppl_sv_no") : c.startsWith("ppl_") ? c.split("|").map((x) => t(x)).join(" · ") : c);
const svWhy = (why: string, t: T): string => (why ? t(`ppl_sv_why_${why}`) : "");
/** On a staff screen, a refusal because of the plan shows what the feature does and Upgrade (83.7); any other refusal stays a warning. */
const SV_WHAT: Record<string, string> = { plan_limit_live_surveys: "ppl_sv_what_live_surveys", plan_no_hardware_without_display: "ppl_sv_what_hardware" };
/** Every survey refusal through the shared message part (section 4C point 2): an error says what to do, the rest are information. */
const SV_HOW: Record<string, string> = { free_limit_reached: "fd_owner_plan", invitation_needed: "fd_use_code", needs_approval_first: "fd_needs_approval", plan_way: "fd_choose_other", sign_in_needed: "fd_sign_in" };
function svNotice(why: string, t: T, text = svWhy(why, t)): string {
  const n: Notice = why === "confirm_phone_first" ? { level: "error", text, field: "svPcode", fix: { label: t("fd_go_to", { field: t("ppl_sv_code") }), focus: "svPcode" } }
    : SV_HOW[why] ? { level: "error", text, how: t(SV_HOW[why]!) }
    : { level: why === "only_after_the_check" ? "warning" : "info", text };
  return noticeHtml(t, n);
}
const svRefusedStaff = (why: string, t: T): string => SV_WHAT[why] ? planPreviewHtml(t, `ppl_sv_why_${why}`, SV_WHAT[why]!) : svNotice(why, t);
const svBar = (label: string, p: number, m: number | null, t: T): string =>
  `<li class="sv-bar"><span class="sv-l">${esc(label)}</span><span class="sv-track" aria-hidden="true"><span class="sv-fill" style="inline-size:${Math.max(0, Math.min(100, p))}%"></span></span><span class="sv-p">${esc(t("ppl_sv_share", { p, m: m === null ? "0.0" : svTenth(m) }))}</span></li>`;

/** The surveys: each with its state in words, the live line, approval and the library. */
export function svSurveysView(d: SurveyDesk, L: SvLook): string {
  const t = L.t, p = d.plan, off = svOff(!L.mayManage);
  const live = `<p class="sub">${esc(t("ppl_sv_live_line", { open: d.liveCount(), check: d.answers.filter((a) => a.result === "please_check").length, calls: d.tasks.filter((x) => x.state === "created").length }))}</p>`;
  const rows = d.surveys.map((s) => svRow(esc(svKindName(s.kind, t)), `${esc(svState(s.state, t))} · ${esc(t("ppl_answers_n", { n: d.rows(s.id).length }))}${s.sample ? ` · ${esc(t("ppl_sandbox_answers"))}` : ""}${s.library ? ` · ${esc(t("ppl_sv_in_library"))}` : ""}`,
    `<button type="button" class="ghost small" data-act="sv:open:${s.id}" ${svOn(d.cur === s.id)}>${esc(t("ppl_sv_choose"))}</button><button type="button" class="ghost small" data-act="sv:edit:${s.id}">${esc(t("ppl_sv_change"))}</button>`)).join("");
  const appr = `<button type="button" class="ph-toggle" data-act="sv:approval" ${svOn(d.approvalOn)} ${svOff(!p.approval || !L.mayManage)}><span>${esc(t("ppl_sv_approval"))}</span><strong>${esc(t(d.approvalOn ? "ppl_on" : "ppl_off"))}</strong></button>
    ${p.approval ? `<p class="sub">${esc(t("ppl_sv_approval_help"))}</p>` : svPlanTag(L, "pro")}`;
  const waiting = d.surveys.filter((s) => s.state === "waiting_for_approval").map((s) => `<div class="ph-row"><span>${esc(svKindName(s.kind, t))}</span><button type="button" class="primary small" data-act="sv:approve:${s.id}" ${off}>${esc(t("ppl_sv_approve"))}</button><button type="button" class="ghost small" data-act="sv:sendback:${s.id}" ${off}>${esc(t("ppl_sv_send_back"))}</button></div>`).join("");
  return svCard("sv_list", t("ppl_surveys"), `${live}<ul class="list">${rows}</ul><button type="button" class="primary inline" data-act="sv:new" data-nav="survey_new">${esc(t("ppl_sv_new"))}</button>`)
    + svCard("sv_approval", t("ppl_sv_approval"), appr + waiting);
}

/** Building: kind, "Write it for me", the questions with the clear question check, who may answer, anonymity, groups to fill,
 *  "How many people do I need?", the moment it follows, preview on every device, test mode, approval and Send. */
export function svBuilderView(d: SurveyDesk, L: SvLook): string {
  const t = L.t, p = d.plan, dr = d.draft, off = svOff(!L.mayManage);
  const kinds = `<div class="ph-choices small">${SV_KINDS.map((k) => `<button type="button" class="ph-choice" data-act="sv:kind:${k}" ${svOn(dr.kind === k)} ${svOff(!d.kindAllowed(k))}><strong>${esc(svKindName(k, t))}</strong>${d.kindAllowed(k) ? "" : `<span>${esc(t("ppl_sv_from_pro"))}</span>`}</button>`).join("")}</div>`;
  const write = p.write_it_for_me ? `<label class="field"><span>${esc(t("ppl_sv_write_it"))}</span><textarea class="sv-text" rows="2" data-in="sv:sentence" data-draft="sv:sentence" autocomplete="off" aria-label="${esc(t("ppl_sv_write_it"))}" placeholder="${esc(t("ppl_sv_write_it_example"))}">${esc(d.sentence)}</textarea></label>
    <button type="button" class="ghost inline" data-act="sv:write" ${svOff(!d.sentence.trim())}>${esc(t("ppl_sv_write"))}</button>${d.wrote ? `<p class="sub">${svTag(t("ppl_sv_assist"))} ${esc(t("ppl_sv_write_note"))}</p>` : ""}` : `<p class="sub">${esc(t("ppl_sv_write_it"))} ${svPlanTag(L, "plus")}</p>`;
  const checks = svCheck(dr.questions);
  const qs = dr.questions.map((x, i) => {
    const mine = checks.filter((c) => c.q === x.id).map((c) => svTag(t(`ppl_sv_check_${c.problem}`), "warn")).join(" ");
    const choices = x.choices.length ? `<div class="sv-choices">${x.choices.map((c, j) => `<label class="field small"><span>${esc(t("ppl_sv_choice_n", { n: j + 1 }))}</span><textarea class="sv-text" rows="1" data-in="sv:qchoice:${i}:${j}" data-draft="sv:qchoice:${i}:${j}" autocomplete="off" placeholder="${esc(t("hint_answer"))}" aria-label="${esc(t("ppl_sv_choice_n", { n: j + 1 }))}">${esc(d.qText(c, t))}</textarea></label>`).join("")}</div>` : "";
    return `<li class="sv-q"><label class="field"><span>${esc(t("ppl_sv_question_n", { n: i + 1 }))} · ${esc(t(`ppl_sv_type_${x.type}`))}</span><textarea class="sv-text" rows="2" data-in="sv:qtext:${i}" data-draft="sv:qtext:${i}" autocomplete="off" placeholder="${esc(t("hint_question"))}" aria-label="${esc(t("ppl_sv_question_n", { n: i + 1 }))} · ${esc(t(`ppl_sv_type_${x.type}`))}">${esc(d.qText(x, t))}</textarea></label>${choices}
      <div class="ph-row">${mine}<button type="button" class="ghost small" data-act="sv:rmq:${i}" ${svOff(dr.questions.length < 2)}>${esc(t("ppl_sv_remove"))}</button></div></li>`;
  }).join("");
  const add = `<div class="ph-row sv-add">${(["rating", "score", "choice", "yes_no", "long", "number", "spoken", "ranking"] as const).map((ty) => `<button type="button" class="ghost small" data-act="sv:addq:${ty}" ${svOff(!d.typeAllowed(ty))}>${esc(t(`ppl_sv_type_${ty}`))}</button>`).join("")}</div>`;
  const logic = `<button type="button" class="ph-toggle" data-act="sv:why" ${svOn(dr.whyOnlyIfUnhappy)} ${svOff(p.logic === "basic")}><span>${esc(t("ppl_sv_logic_why"))}</span><strong>${esc(t(dr.whyOnlyIfUnhappy ? "ppl_on" : "ppl_off"))}</strong></button>`;
  const rules = `<div class="ph-choices small">${RULES.map((r) => `<button type="button" class="ph-choice" data-act="sv:rule:${r}" ${svOn(dr.rule === r)}><strong>${esc(t(`ppl_sv_rule_${r}`))}</strong><span>${esc(t(`ppl_sv_rule_${r}_help`))}</span></button>`).join("")}</div>`;
  const anon = `<button type="button" class="ph-toggle" data-act="sv:anon" ${svOn(dr.anonymous)}><span>${esc(t("ppl_sv_anonymous"))}</span><strong>${esc(t(dr.anonymous ? "ppl_on" : "ppl_off"))}</strong></button>${dr.anonymous ? `<p class="sub">${esc(t("ppl_sv_anonymous_line"))}</p>` : ""}`;
  const fill = p.research.includes("groups_to_fill") ? SV_GROUPS.map((g) => `<label class="field small"><span>${esc(t(g))}</span><input inputmode="numeric" data-in="sv:target:${g}" value="${dr.targets[g] ?? ""}" autocomplete="off" placeholder="${esc(hintFor("count", t))}" aria-label="${esc(t(g))}"></label>`).join("") + `<p class="sub">${esc(t("ppl_sv_fill_help"))}</p>` : `<p class="sub">${svPlanTag(L, "pro")}</p>`;
  const need = `<div class="ph-row">${SV_MARGINS.map((m) => `<button type="button" class="ghost small" data-act="sv:margin:${m}" ${svOn(d.marginPick === m)}>±${m}%</button>`).join("")}</div><p>${esc(t("ppl_sv_need", { m: d.marginPick, n: sampleSize(d.marginPick) }))}</p>`;
  const after = `<div class="ph-row">${(["lynkpos", "lynkqueue", "lynkchat", "lynkattend"] as const).map((s) => { const ok = p.automatic.includes("all") || p.automatic.includes(s);
    return `<button type="button" class="ghost small" data-act="sv:after:${s}" ${svOn(dr.after === s)} ${svOff(!ok)}>${esc(t(`ppl_sv_after_${s}`))}</button>`; }).join("")}</div><p class="sub">${esc(t("ppl_sv_after_help"))}</p>
    <button type="button" class="ph-toggle" data-act="sv:repeat" ${svOn(!!dr.repeatDays)} ${svOff(!p.repeating)}><span>${esc(t("ppl_sv_repeat"))}</span><strong>${esc(t(dr.repeatDays ? "ppl_on" : "ppl_off"))}</strong></button>`;
  const prev = `<div class="ph-row">${(["smartphone", "basic_phone", "kiosk", "pos", "voice"] as const).map((w) => `<button type="button" class="ghost small" data-act="sv:preview:${w}" ${svOn(d.preview === w)}>${esc(w === "kiosk" ? "LynkKiosk" : w === "pos" ? "LynkPOS" : svWayName(w, t))}</button>`).join("")}</div>
    <div class="sv-preview" data-item="sv_preview">${svPreview(d, L)}</div>`;
  const saved = d.surveys.find((s) => s.id === dr.id);
  const actions = `<div class="ph-row"><button type="button" class="primary" data-act="sv:save" ${off}>${esc(t("ppl_sv_save"))}</button>${saved ? `
    <button type="button" class="ghost" data-act="sv:state:${saved.id}:test" ${off}>${esc(t("ppl_sv_test"))}</button>${d.approvalOn && !["approved", "open", "paused"].includes(saved.state) ? `<button type="button" class="ghost" data-act="sv:submit:${saved.id}" ${off}>${esc(t("ppl_sv_submit"))}</button>` : ""}
    <button type="button" class="primary" data-act="sv:state:${saved.id}:open" ${off}>${esc(t("ppl_sv_send"))}</button><button type="button" class="ghost" data-act="sv:state:${saved.id}:paused" ${svOff(saved.state !== "open")}>${esc(t("ppl_sv_pause"))}</button>
    <button type="button" class="ghost" data-act="sv:state:${saved.id}:closed" ${svOff(saved.state === "closed")}>${esc(t("ppl_sv_close"))}</button>` : ""}</div>
    ${saved ? `<p class="sub" role="status">${esc(svState(saved.state, t))}${saved.note ? ` · ${esc(t(saved.note))}` : ""} · ${esc(t("ppl_sv_version", { n: saved.version }))}</p>` : ""}${d.refused ? svRefusedStaff(d.refused, t) : ""}
    <p class="sub">${esc(t("ppl_sv_version_help"))}</p>`;
  return svCard("sv_kind", t("ppl_sv_kind"), kinds + write)
    + svCard("sv_questions", t("ppl_sv_questions"), `<ul class="list sv-qs">${qs}</ul>${add}${logic}${checks.length ? `<p class="sub">${esc(t("ppl_sv_check_help"))}</p>` : `<p class="sub">${esc(t("ppl_sv_check_ok"))}</p>`}`)
    + svCard("sv_languages", t("ppl_sv_languages"), `<p>${esc(t("ppl_sv_languages_help", { n: SV_LANGUAGES }))}</p>`)
    + svCard("sv_who", t("ppl_sv_who"), rules + anon)
    + svCard("sv_fill", t("ppl_sv_fill"), fill)
    + svCard("sv_need", t("ppl_sv_need_title"), need)
    + svCard("sv_after", t("ppl_sv_after"), after)
    + svCard("sv_preview_card", t("ppl_sv_preview"), prev)
    + svCard("sv_send", t("ppl_sv_send_title"), actions);
}
/** What the person sees on each kind of device: the same survey, the same words. */
export function svPreview(d: SurveyDesk, L: SvLook): string {
  const t = L.t, first = d.draft.questions[0]; if (!first) return "";
  if (d.preview === "basic_phone" || d.preview === "voice") return `<pre class="bussd">1/${d.draft.questions.length}. ${esc(d.qText(first, t))}\n${esc(first.type === "score" ? t("ppl_sv_prev_score") : first.type === "yes_no" ? t("ppl_sv_prev_yes_no") : t("ppl_sv_prev_rate"))}</pre>${d.preview === "voice" ? `<p class="sub">${esc(t("ppl_sv_voice_note"))}</p>` : ""}`;
  return `<div class="sv-q-show">${svAsk(first, null, "p", t, (x) => d.qText(x, t))}</div>`;
}
/** One question on a screen, by its type: the rating dials, the 0 to 10 score, yes or no, choices or a written answer. */
function svAsk(x: SvQ, got: { number?: number; choice?: string; text?: string } | null, who: "k" | "p", t: T, text: (x: { key: string | null; text: string }) => string): string {
  const title = text(x);
  if (x.type === "rating" || x.type === "stars") return quickRating(title, got?.number ?? null, t).replace(/data-act="ppl:rate:(\d)"/g, `data-act="sv:${who}:$1"`);
  if (x.type === "score") return scoreScale(title, got?.number ?? null, t).replace(/data-act="ppl:score:(\d+)"/g, `data-act="sv:${who}:$1"`);
  if (x.type === "yes_no") return `<fieldset class="sv-yn"><legend>${esc(title)}</legend><div class="ph-row">${["yes", "no"].map((c) => `<button type="button" class="ph-choice" data-act="sv:${who}:${c}:c" ${svOn(got?.choice === c)}><strong>${esc(t(`ppl_sv_${c}`))}</strong></button>`).join("")}</div></fieldset>`;
  if (["choice", "many", "best_worst", "offer_pick", "ranking"].includes(x.type)) return `<fieldset class="sv-ch"><legend>${esc(title)}</legend><div class="ph-choices small">${x.choices.map((c) => { const v = c.key ?? c.text;
    return `<button type="button" class="ph-choice" data-act="sv:${who}:${esc(v)}:c" ${svOn(got?.choice === v)}><strong>${esc(text(c))}</strong></button>`; }).join("")}</div></fieldset>`;
  return `<label class="field"><span>${esc(title)}</span><textarea data-in="sv:${who === "k" ? "ktext" : "ptext"}:${x.id}" rows="3" placeholder="${esc(t("hint_answer"))}" aria-label="${esc(title)}">${esc(got?.text ?? "")}</textarea></label><p class="sub">${esc(t("ppl_sv_skip_ok"))}</p>`;
}

/** Live results: the LynkAssist summary, each question with its margin, filters, "Please check", goals, verified results. */
export function svResultsView(d: SurveyDesk, L: SvLook): string {
  const t = L.t, s = d.sv(), p = d.plan; if (!s) return "";
  const rows = d.rows(s.id, { way: d.filterWay || undefined });
  const ways = [...new Set(d.rows(s.id).map((a) => a.way))];
  const filters = `<div class="ph-row">${ways.map((w) => `<button type="button" class="ghost small" data-act="sv:way:${w}" ${svOn(d.filterWay === w)}>${esc(svWayName(w, t))}</button>`).join("")}</div>`;
  if (!canShow(rows.length)) return svCard("sv_results", `${t("ppl_results")} · ${svKindName(s.kind, t)}`, `${filters}<p class="sub">${esc(t("ppl_too_few", { n: MIN_GROUP }))}</p>`);
  const qhtml = s.questions.map((x) => {
    const r = d.result(x, rows), name = esc(d.qText(x, t));
    if (!r) return `<li><p class="nm">${name}</p><p class="sub">${esc(t("ppl_too_few", { n: MIN_GROUP }))}</p></li>`;
    if (r.good !== undefined) return `<li><p class="nm">${name}</p><p>${esc(t("ppl_average", { avg: svTenth(r.avgTenths ?? 0) }))}${r.recommend !== undefined ? ` · ${esc(t("ppl_sv_recommend_score", { n: r.recommend }))}` : ""}</p><ul class="sv-bars">${svBar(t("ppl_sv_good"), r.good, r.margin ?? null, t)}</ul></li>`;
    if (r.shares) return `<li><p class="nm">${name}</p><ul class="sv-bars">${r.shares.map((x2) => svBar(svChoice(x2.c, t), x2.p, x2.m, t)).join("")}</ul></li>`;
    return `<li><p class="nm">${name}</p><p class="sub">${esc(t("ppl_sv_written_n", { n: r.written ?? 0 }))}</p></li>`;
  }).join("");
  const first = s.questions.find((x) => x.type === "rating" || x.type === "score"), fr = first ? d.result(first, rows) : null;
  const sum = fr && fr.good !== undefined ? `<p>${svTag(t("ppl_sv_assist"))} ${esc(t("ppl_sv_summary", { p: fr.good, m: svTenth(fr.margin ?? 0), n: rows.length }))}</p>` : "";
  const unhappy = d.answers.filter((a) => a.survey === s.id && !a.test && a.result === "accepted" && first && (a.answers[first.id]?.number ?? 9) <= (SV_UNHAPPY[first.type] ?? 2)).length;
  const alert = unhappy >= 3 ? `<p class="notice" role="status">${L.icon("ui-bell")} ${esc(t("ppl_sv_alert", { n: unhappy }))}</p>` : "";
  const flagged = d.answers.filter((a) => a.survey === s.id && a.result === "please_check");
  const check = svCard("sv_check", t("ppl_sv_please_check"), !flagged.length ? `<p class="sub">${esc(t("ppl_sv_check_none"))}</p>` : `<ul class="list">${flagged.map((a) => svRow(esc(t(`ppl_sv_reason_${a.reason ?? "too_fast"}`)), esc(L.clock(a.at)),
    `<button type="button" class="ghost small" data-act="sv:keep:${a.id}" ${svOff(!L.mayManage)}>${esc(t("ppl_sv_keep"))}</button><button type="button" class="ghost small" data-act="sv:aside:${a.id}" ${svOff(!L.mayManage)}>${esc(t("ppl_sv_set_aside"))}</button>`)).join("")}</ul><p class="sub">${esc(t("ppl_sv_check_never"))}</p>`);
  const goal = svCard("sv_goal", t("ppl_sv_goal"), !p.experience_dashboards ? `<p class="sub">${svPlanTag(L, "pro")}</p>` : fr && fr.good !== undefined ? `<p>${esc(t("ppl_sv_goal_line", { goal: 80 }))}</p><p>${svTag(t(fr.good >= 80 ? "ppl_sv_on_track" : "ppl_sv_below_goal"), fr.good >= 80 ? "" : "warn")}</p>` : `<p class="sub">${esc(t("ppl_too_few", { n: MIN_GROUP }))}</p>`);
  const ver = d.verified[s.id], still = d.stillTrue();
  const verified = svCard("sv_verified", t("ppl_sv_verified"), `${ver ? `<p dir="ltr" class="mono">${esc(ver)}</p><p role="status">${svTag(t(still ? "ppl_sv_real" : "ppl_sv_changed"), still ? "" : "warn")}</p>` : ""}<button type="button" class="ghost inline" data-act="sv:verify" ${svOff(!L.mayManage)}>${esc(t("ppl_sv_verify"))}</button><p class="sub">${esc(t("ppl_sv_verified_help"))}</p>`);
  return svCard("sv_results", `${t("ppl_results")} · ${svKindName(s.kind, t)}`, `${filters}${s.sample ? `<p class="sub">${svTag(t("ppl_sandbox_answers"))}</p>` : ""}${sum}${alert}<ul class="list sv-res">${qhtml}</ul><p class="sub">${esc(t("ppl_answers_n", { n: rows.length }))} · ${esc(t("ppl_sv_margin_help"))}</p>`)
    + check + goal + verified;
}

/** The research tools (by plan): compare groups, real difference or chance, balancing, themes, what matters most, trade-off, downloads. */
export function svResearchView(d: SurveyDesk, L: SvLook): string {
  const t = L.t, p = d.plan, s = d.sv(); if (!s) return "";
  const first = s.questions.find((x) => x.type === "rating" || x.type === "score");
  const has = (k: string): boolean => p.research.includes(k);
  const locked = (tier: "plus" | "pro"): string => `<p class="sub">${svPlanTag(L, tier)}</p>`;
  let cmp = "";
  if (!has("compare_groups")) cmp = locked("plus");
  else if (first) {
    const out = d.compare(first, d.compareBy);
    cmp = `<div class="ph-row">${(["group", "place", "way"] as const).map((b) => `<button type="button" class="ghost small" data-act="sv:cmp:${b}" ${svOn(d.compareBy === b)}>${esc(t(`ppl_sv_by_${b}`))}</button>`).join("")}</div>
      <ul class="sv-bars">${out.map((o) => o.r && o.r.good !== undefined ? svBar(o.v.startsWith("ppl_") ? t(o.v) : svWayName(o.v, t), o.r.good, o.r.margin ?? null, t) : `<li class="sv-bar"><span class="sv-l">${esc(o.v.startsWith("ppl_") ? t(o.v) : svWayName(o.v, t))}</span><span class="sv-p">${esc(t("ppl_too_few", { n: MIN_GROUP }))}</span></li>`).join("")}</ul>`;
    const two = out.filter((o) => o.r && o.r.good !== undefined).slice(0, 2);
    if (two.length === 2) cmp += has("real_difference") ? `<p>${esc(t(`ppl_sv_diff_${svRealDifference(two[0]!.r!.good!, two[0]!.r!.n, two[1]!.r!.good!, two[1]!.r!.n)}`))}</p>` : locked("pro");
  }
  const bal = !has("balancing") ? locked("pro") : (() => { const b = first ? d.balanced(first, 52) : null;
    return b ? `<p>${esc(t("ppl_sv_balanced", { raw: b.raw, bal: b.balanced }))}</p><p class="sub">${esc(t("ppl_sv_balanced_help"))}</p>` : `<p class="sub">${esc(t("ppl_too_few", { n: MIN_GROUP }))}</p>`; })();
  const long = s.questions.find((x) => x.type === "long");
  const th = !has("themes") && !has("themes_basic") ? locked("plus") : (() => { const r = long ? d.themes(long) : null;
    return r ? `<p class="sub">${svTag(t("ppl_sv_assist"))}</p><ul class="sv-bars">${r.map((x) => svBar(t(`ppl_sv_theme_${x.theme}`), x.p, null, t)).join("")}</ul><p class="sub">${esc(t("ppl_sv_themes_help"))}</p>` : `<p class="sub">${esc(t("ppl_too_few", { n: MIN_GROUP }))}</p>`; })();
  const research = d.surveys.find((x) => x.kind === "research");
  const bw = research?.questions.find((x) => x.type === "best_worst"), op = research?.questions.find((x) => x.type === "offer_pick");
  const mm = !has("what_matters_most") ? locked("pro") : (() => { const prev = d.cur; if (research) d.cur = research.id; const o = bw ? d.bestWorst(bw) : null; const r = op ? d.result({ ...op, type: "choice" }, d.rows()) : null; d.cur = prev;
    return `${o ? `<ol class="sv-order">${o.map((k) => `<li>${esc(t(k))}</li>`).join("")}</ol>` : ""}${r?.shares ? `<ul class="sv-bars">${r.shares.map((x) => svBar(svChoice(x.c, t), x.p, x.m, t)).join("")}</ul>` : ""}<p class="sub">${svTag(t("ppl_sandbox_answers"))}</p>`; })();
  const dl = `<div class="ph-row">${["spreadsheet", "csv", "spss", "stata", "r"].map((f) => `<button type="button" class="ghost small" ${svOff(!p.downloads.includes(f))}>${esc(SV_FORMATS[f] ?? t("ppl_sv_dl_spreadsheet"))}</button>`).join("")}</div>${p.downloads.length ? `<pre class="sv-csv" dir="ltr">${esc(d.csv())}</pre>` : locked("plus")}<p class="sub">${esc(t("ppl_sv_dl_help"))}</p>`;
  return svCard("sv_compare", t("ppl_sv_compare"), cmp) + svCard("sv_balance", t("ppl_sv_balance"), bal) + svCard("sv_themes", t("ppl_sv_themes"), th)
    + svCard("sv_matters", t("ppl_sv_matters"), mm) + svCard("sv_downloads", t("ppl_sv_downloads"), dl)
    + svCard("sv_record", t("ppl_sv_record"), `<p class="sub">${esc(t("ppl_sv_record_help"))}</p>`);
}

/** Closing the loop: Call back tasks with their time limit, and "You said, we did". */
export function svTasksView(d: SurveyDesk, L: SvLook): string {
  const t = L.t, p = d.plan, s = d.sv();
  const tasks = !p.call_back ? `<p class="sub">${svPlanTag(L, "plus")}</p>` : `<ul class="list">${d.tasks.map((x) => svRow(esc(t(x.state === "done" ? "ppl_sv_cb_done" : "ppl_sv_cb_open")), esc(t("ppl_sv_cb_due", { time: L.clock(x.due) })),
    x.state === "created" ? `<button type="button" class="ghost small" data-act="sv:cbdone:${x.id}">${esc(t("ppl_sv_mark_done"))}</button>` : "")).join("") || `<li><p class="sub">${esc(t("ppl_sv_cb_none"))}</p></li>`}</ul><p class="sub">${esc(t("ppl_sv_cb_help"))}</p>`;
  const said = !p.call_back || !s ? "" : `<label class="field"><span>${esc(t("ppl_sv_you_said"))}</span><textarea data-in="sv:yousaid" data-draft="sv:yousaid" rows="2" placeholder="${esc(t("hint_yousaid"))}" aria-label="${esc(t("ppl_sv_you_said"))}">${esc(d.youSaid)}</textarea></label><button type="button" class="primary inline" data-act="sv:yousaid" ${svOff(!d.youSaid.trim() || !L.mayManage)}>${esc(t("ppl_sv_send_message"))}</button>
    ${d.said.filter((x) => x.survey === s.id).map((x) => `<p class="sub" role="status">${esc(x.public ? t("ppl_sv_said_public") : t("ppl_sv_said_told", { n: x.told }))}</p>`).join("")}`;
  return svCard("sv_tasks", t("ppl_sv_call_back"), tasks) + svCard("sv_said", t("ppl_sv_you_said_title"), said || `<p class="sub">${svPlanTag(L, "plus")}</p>`);
}

/** Rewards through the licensed payment partner, cash recorded by a field worker, and the LynkSurvey Panel (never who the people are). */
export function svRewardsView(d: SurveyDesk, L: SvLook): string {
  const t = L.t, p = d.plan, s = d.sv();
  const pick = s ? d.answers.find((a) => a.survey === s.id && a.result === "accepted" && !a.test && !d.rewards.some((r) => r.answer === a.id)) : undefined;
  const rewards = !p.rewards ? `<p class="sub">${svPlanTag(L, "plus")}</p>` : `<div class="ph-row">${(["airtime", "credit", "voucher", "cash"] as const).map((k) => `<button type="button" class="ghost small" data-act="sv:reward:${pick?.id ?? ""}:${k}" ${svOff(!pick)}>${esc(t(`ppl_sv_reward_${k}`))}</button>`).join("")}</div>
    <ul class="list">${d.rewards.map((r) => svRow(esc(t(`ppl_sv_reward_${r.kind}`)), esc(t(`ppl_sv_reward_state_${r.state}`)), r.state === "sent" ? `<button type="button" class="ghost small" data-act="sv:rpaid:${r.id}:paid">${esc(t("ppl_sv_partner_paid"))}</button>` : "")).join("")}</ul>
    ${d.refused === "only_after_the_check" || d.refused === "one_reward_per_person" ? svNotice(d.refused, t) : ""}<p class="sub">${esc(t("ppl_sv_reward_help"))}</p>`;
  const panel = !p.panel ? `<p class="sub">${svPlanTag(L, "pro")}</p>` : `<p>${esc(t("ppl_sv_panel_members", { n: d.panelMembers.toLocaleString("en") }))} ${svTag(t("ppl_sandbox_answers"))}</p>
    <div class="ph-row"><label class="field small"><span>${esc(t("ppl_sv_panel_country"))}</span><input data-in="sv:pcountry" value="${esc(d.panel.country)}" autocomplete="off" dir="ltr" placeholder="${esc(hintFor("country", t, undefined, L.country))}" aria-label="${esc(t("ppl_sv_panel_country"))}"></label><label class="field small"><span>${esc(t("ppl_sv_panel_wanted"))}</span><input inputmode="numeric" data-in="sv:pwanted" value="${d.panel.wanted}" autocomplete="off" placeholder="${esc(hintFor("count", t))}" aria-label="${esc(t("ppl_sv_panel_wanted"))}"></label></div>
    <button type="button" class="primary inline" data-act="sv:panel">${esc(t("ppl_sv_panel_ask"))}</button>${d.panel.reached !== null ? `<p role="status">${esc(t("ppl_sv_panel_reached", { n: d.panel.reached, of: d.panel.wanted }))}</p>` : ""}<p class="sub">${esc(t("ppl_sv_panel_never"))}</p>`;
  return svCard("sv_rewards", t("ppl_sv_rewards"), rewards) + svCard("sv_panel", t("ppl_sv_panel"), panel);
}

/** The devices that collect answers (only added ones), hardware without a display on paid tiers, and the device lock. */
export function svDevicesView(d: SurveyDesk, L: SvLook): string {
  const t = L.t, p = d.plan, off = svOff(!L.mayManage);
  const name = (k: SvDevKind): string => SV_LYNK[k] ?? t(`ppl_sv_dev_${k}`);
  const rows = d.devices.map((x) => svRow(esc(name(x.kind)), x.locked ? esc(t("ppl_sv_locked")) : "", `${svChip(x.locked ? "failed" : x.state, L)}${x.locked || x.id === d.deviceId ? "" : `<button type="button" class="ghost small" data-act="sv:lock:${x.id}" ${off}>${esc(t("ppl_sv_lock"))}</button>`}`)).join("");
  const kinds = `<div class="ph-choices small">${SV_DEVICE_KINDS.map((k) => `<button type="button" class="ph-choice" data-act="sv:devkind:${k}" ${svOn(d.addKind === k)} ${svOff(SV_NO_DISPLAY.includes(k) && !p.own_hardware)}><strong>${esc(name(k))}</strong></button>`).join("")}</div>`;
  const field = `<button type="button" class="ph-toggle" data-act="sv:field" ${svOn(d.field)} ${svOff(!p.field_and_paper)}><span>${esc(t("ppl_sv_field"))}</span><strong>${esc(t(d.field ? "ppl_on" : "ppl_off"))}</strong></button>${p.field_and_paper ? `<p class="sub">${esc(t("ppl_sv_field_help"))}</p>` : svPlanTag(L, "plus")}`;
  return svCard("sv_devices", t("ppl_sv_devices"), `<ul class="list">${rows}</ul>${kinds}<button type="button" class="primary inline" data-act="sv:adddev" ${off}>${esc(t("ppl_add_device"))}</button>${d.refused === "plan_no_hardware_without_display" ? svRefusedStaff(d.refused, t) : ""}<p class="sub">${esc(t("ppl_sv_devices_help"))}</p>`)
    + svCard("sv_field", t("ppl_sv_field_title"), field);
}

/** Everything that was done, and what this month counts against the plan (creators who built or sent, answers). */
export function svPlanView(d: SurveyDesk, L: SvLook): string {
  const t = L.t, u = d.usage(), p = d.plan;
  const hist = d.history.slice(0, 12).map((h) => svRow(esc(t(`ppl_sv_did_${h.what.replace(/^(state|approval|device)_.*/, "$1")}`, { what: t(`ppl_sv_state_${h.what.replace(/^state_/, "")}`) })), esc(L.clock(h.at)))).join("");
  const plan = `<p>${esc(t("ppl_sv_used", { used: u.answers.toLocaleString("en"), included: u.included.toLocaleString("en") }))}</p><p>${esc(t("ppl_sv_creators", { n: u.creators, included: u.creatorsIncluded }))}</p>
    ${p.extra_creator_cents === null ? `<p class="sub">${esc(t("ppl_sv_free_note"))}</p>` : `<p class="sub">${esc(t("ppl_sv_extra_note", { creator: L.money(p.extra_creator_cents), answers: L.money(100) }))}</p>`}
    <p class="sub">${esc(t("ppl_sv_creators_help"))}</p>${p.own_logo ? "" : L.powered}`;
  return svCard("sv_plan", t("ppl_sv_your_plan"), plan) + svCard("sv_history", t("ppl_sv_history"), `<ul class="list">${hist || `<li><p class="sub">${esc(t("ppl_sv_history_none"))}</p></li>`}</ul>`);
}

// ---- device screens ----------------------------------------------------------------------------------------------------------
/** LynkKiosk: one person at a time, one question a page; the answer is saved on the kiosk at once (also offline), then it starts again. */
export function svKioskView(d: SurveyDesk, L: SvLook): string {
  const t = L.t, s = d.sv(); if (!s || !["open", "test"].includes(s.state)) return `<div class="svkiosk"><p class="sub">${esc(t("ppl_sv_why_survey_closed"))}</p></div>`;
  if (d.kiosk.done) return `<div class="svkiosk done" role="status"><p class="plabel">${esc(t("ppl_thanks"))}</p><button type="button" class="primary inline" data-act="sv:kagain">${esc(t("ppl_next_person"))}</button></div>`;
  const list = d.visible(s, d.kiosk.answers), x = list[d.kiosk.i]; if (!x) return "";
  const got = d.kiosk.answers[x.id] ?? null;
  return `<div class="svkiosk">${d.kiosk.i === 0 ? `<p class="sub">${esc(t("ppl_sv_consent_line", { org: L.place, n: list.length, m: Math.max(1, Math.ceil(list.length / 2)) }))}${s.anonymous ? ` ${esc(t("ppl_sv_anonymous_line"))}` : ""}</p>` : ""}
    <p class="sub">${esc(t("ppl_sv_q_of", { i: d.kiosk.i + 1, n: list.length }))}</p>${svAsk(x, got, "k", t, (y) => d.qText(y, t))}
    <button type="button" class="primary inline" data-act="sv:knext" ${svOff(!got && x.type !== "long")}>${esc(t(d.kiosk.i + 1 < list.length ? "ppl_sv_next" : "ppl_sv_finish"))}</button>${d.refused ? svNotice(d.refused, t) : ""}${d.plan.own_logo ? "" : L.powered}</div>`;
}
/** LynkDScreen: the live poll on the wall (results build up as people answer, never below 5) and the QR to answer. */
export function svScreenView(d: SurveyDesk, L: SvLook): string {
  const t = L.t, s = d.sv(); if (!s) return "";
  const x = s.questions.find((y) => y.type !== "long"), r = x ? d.result(x, d.rows()) : null;
  const bars = !x || !r ? `<p class="sub">${esc(t("ppl_too_few", { n: MIN_GROUP }))}</p>` : r.good !== undefined ? `<p class="svs-big">${esc(t("ppl_average", { avg: svTenth(r.avgTenths ?? 0) }))}</p><ul class="sv-bars">${svBar(t("ppl_sv_good"), r.good, r.margin ?? null, t)}</ul>`
    : `<ul class="sv-bars">${(r.shares ?? []).map((y) => svBar(svChoice(y.c, t), y.p, y.m, t)).join("")}</ul>`;
  return `<div class="svscreen"><h2 class="qs-title">${esc(x ? d.qText(x, t) : svKindName(s.kind, t))}</h2>${bars}<p class="sub" aria-live="polite">${esc(t("ppl_answers_n", { n: d.rows().length }))}</p>${rateUs(L.icon, t)}${d.plan.own_logo ? "" : L.powered}</div>`;
}
/** LynkCDisplay: "Rate us" for this counter, with the QR. */
export function svCDisplayView(d: SurveyDesk, counter: number, L: SvLook): string {
  return `<div class="qcd svcd" data-wait-area data-shape="text"><p class="qcd-name">${esc(L.t("ppl_counter_n", { n: counter }))}</p>${rateUs(L.icon, L.t)}</div>`;
}
/** The person's phone (link, QR, website, LynkChat, email): consent first, the code for "one per phone", one question a
 *  page, then thank you with My answers and "Don't ask me again". No app and no account. */
export function svPhoneView(d: SurveyDesk, L: SvLook): string {
  const t = L.t, s = d.sv(), ph = d.phone; if (!s) return "";
  if (!["open", "test"].includes(s.state)) return `<div class="svphone"><p class="sub">${esc(t("ppl_sv_why_survey_closed"))}</p></div>`;
  const list = d.visible(s, ph.answers), sensitive = s.questions.some((x) => svCheck([x]).some((c) => c.problem === "sensitive_topic"));
  if (ph.step === "consent") {
    const ways = `<div class="ph-choices small">${(["smartphone", "lynkchat", "email"] as const).map((w) => `<button type="button" class="ph-choice" data-act="sv:pway:${w}" ${svOn(ph.way === w)}><strong>${esc(svWayName(w, t))}</strong></button>`).join("")}</div>`;
    const note = ph.note === "plan" ? t("ppl_sv_why_plan_way") : ph.note === "coming_soon" ? t("coming_soon") : "";
    return `<div class="svphone"><h2>${esc(L.place)}</h2><p>${esc(t("ppl_sv_consent_line", { org: L.place, n: list.length, m: Math.max(1, Math.ceil(list.length / 2)) }))}</p><p class="sub">${esc(t("ppl_sv_why_asked"))}</p>
      ${s.anonymous ? `<p class="notice">${esc(t("ppl_sv_anonymous_line"))}</p>` : ""}${sensitive ? `<button type="button" class="ph-toggle" data-act="sv:pconsent" ${svOn(ph.consent)}><span>${esc(t("ppl_sv_sensitive_agree"))}</span><strong>${esc(t(ph.consent ? "ppl_on" : "ppl_off"))}</strong></button>` : ""}
      ${ways}${note ? svNotice(ph.note === "plan" ? "plan_way" : "coming_soon", t, note) : ""}<button type="button" class="primary inline" data-act="sv:pstart">${esc(t("ppl_sv_start"))}</button><p class="sub">${esc(t("ppl_sv_no_account"))}</p>${d.plan.own_logo ? "" : L.powered}</div>`;
  }
  if (ph.step === "code") return `<div class="svphone"><p>${esc(t("ppl_sv_code_sent"))}</p>${codeFieldHtml({ t, lang: typeof document === "undefined" ? "en" : document.documentElement.lang || "en" }, { id: "svPcode", label: t("ppl_sv_code"), value: ph.code, act: "sv:pcode", resendAct: "sv:presend", sent: ph.sent })}
    <button type="button" class="primary inline" data-act="sv:pcode" ${svOff(!/^\d{6}$/.test(ph.code))}>${esc(t("ppl_sv_next"))}</button><p class="sub">${esc(t("ppl_sv_phone_kept"))}</p></div>`;
  if (ph.step === "done") return `<div class="svphone" role="status"><p class="plabel">${esc(t("ppl_thanks"))}</p>${s.anonymous ? "" : `<p class="sub">${esc(t("ppl_sv_in_my_answers"))}</p>`}
    <button type="button" class="ghost inline" data-act="sv:optout" ${svOff(d.optedOut)}>${esc(t(d.optedOut ? "ppl_sv_not_asked" : "ppl_sv_dont_ask"))}</button><button type="button" class="ghost inline" data-act="sv:pagain">${esc(t("ppl_sv_again"))}</button></div>`;
  const x = list[ph.i]; if (!x) return "";
  const got = ph.answers[x.id] ?? null;
  return `<div class="svphone"><p class="sub">${esc(t("ppl_sv_q_of", { i: ph.i + 1, n: list.length }))}</p>${svAsk(x, got, "p", t, (y) => d.qText(y, t))}
    <button type="button" class="primary inline" data-act="sv:pnext" ${svOff(!got && x.type !== "long")}>${esc(t(ph.i + 1 < list.length ? "ppl_sv_next" : "ppl_sv_finish"))}</button>${ph.note && ph.step === "question" ? svNotice(ph.note, t) : ""}</div>`;
}
