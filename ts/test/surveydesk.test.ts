import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SV_OPEN_PLAN, SurveyDesk, svBuilderView, svCDisplayView, svCheck, svDevicesView, svKioskView, svPhoneView, svPlanView, svRealDifference, svResearchView, svResultsView, svRewardsView,
  svScreenView, svSurveysView, svTasksView, svTemplate, svWriteIt } from "../src/surveydesk.js";
import type { SvLook, SvPlan } from "../src/surveydesk.js";
import type { AtTier } from "../src/attenddesk.js";
import { MIN_GROUP } from "../src/survey.js";

/** LynkSurvey in full on a device (build section 3B): every event is a contract version 6 event with no name or phone number;
 *  no result below 5 answers anywhere; "Please check" never deletes; the plan sets what is offered; the same answers as the
 *  Python reference (people/survey.py) for the clear question check and "Real difference or chance?". */
const t = (k: string, v: Record<string, string | number> = {}): string => k + (Object.keys(v).length ? JSON.stringify(v) : "");
const icon = (id: string): string => `<i data-icon="${id}"></i>`;
const LOOK: SvLook = { t, icon, clock: () => "09:00", money: (c) => `$${(c / 100).toFixed(2)}`, online: true, partner: false, mayManage: true, place: "Sample place", powered: "<small>Powered</small>" };
const FREE: SvPlan = { ...SV_OPEN_PLAN, creators_included: 1, extra_creator_cents: null, answers_per_month: 300, live_surveys: 3, whatsapp_and_chat: false, basic_phone: false, field_and_paper: false, voice_call: false,
  write_it_for_me: false, logic: "basic", repeating: false, automatic: [], staff_journey: false, experience_dashboards: false, library_and_brand_kit: false, approval: false, call_back: false, rewards: false, panel: false,
  own_hardware: false, own_logo: false, research: ["margins", "sample_size", "research_record"], downloads: [] };
const PLUS: SvPlan = { ...SV_OPEN_PLAN, approval: false, panel: false, experience_dashboards: false, research: ["margins", "sample_size", "research_record", "compare_groups", "before_after", "themes_basic"], downloads: ["spreadsheet", "csv"], automatic: ["lynkpos", "lynkqueue", "lynkchat"] };
const PLANS: Record<AtTier, SvPlan> = { free: FREE, plus: PLUS, pro: SV_OPEN_PLAN, max: SV_OPEN_PLAN };
const CONTRACT = JSON.parse(readFileSync(new URL("../../../contract/event-payloads.v6.json", import.meta.url).pathname, "utf8")).events as Record<string, { origins: string[]; payload: { required?: string[]; properties: Record<string, { enum?: unknown[] }> } }>;
function desk(): { d: SurveyDesk; log: { type: string; payload: Record<string, unknown>; origin?: string }[] } {
  const log: { type: string; payload: Record<string, unknown>; origin?: string }[] = [];
  return { d: new SurveyDesk((type, payload, origin) => { log.push({ type, payload, origin }); }, PLANS, () => 1_800_000_000_000), log };
}
function inContract(log: { type: string; payload: Record<string, unknown>; origin?: string }[]): void {
  for (const e of log) {
    const c = CONTRACT[e.type]; if (!c) throw new Error(`${e.type} is not a contract event`);
    assert.ok(c.origins.includes(e.origin ?? "device"), `${e.type} from ${e.origin ?? "device"}`);
    for (const r of c.payload.required ?? []) assert.ok(r in e.payload, `${e.type} needs ${r}`);
    for (const [k, v] of Object.entries(e.payload)) {
      const prop: { enum?: unknown[] } | undefined = c.payload.properties[k]; if (!prop) throw new Error(`${e.type} must not carry ${k}`);
      if (prop.enum) assert.ok(prop.enum.includes(v), `${e.type}.${k} = ${String(v)}`);
    }
    assert.ok(!/phone_number|"name"|contact/i.test(JSON.stringify(e.payload)), `${e.type} carries no name or phone number`);
  }
}

test("the clear question check and real difference agree with the Python reference", () => {
  const qs = [{ id: "a", type: "rating" as const, key: null, text: "Don't you agree our service is great?", choices: [] }, { id: "b", type: "yes_no" as const, key: null, text: "Is it fast and is it cheap?", choices: [] },
    { id: "c", type: "choice" as const, key: null, text: "Which political party do you support?", choices: [] }];
  assert.deepEqual(svCheck(qs).map((c) => [c.q, c.problem]), [["a", "pushes_towards_an_answer"], ["b", "two_questions_in_one"], ["c", "sensitive_topic"]]);
  assert.equal(svRealDifference(100, 5, 20, 5), "real"); assert.equal(svRealDifference(62, 40, 55, 40), "could_be_chance"); assert.equal(svRealDifference(50, 4, 50, 40), "too_few");
  assert.equal(svWriteIt("I want to know why customers don't come back").kind, "recommend");
  assert.equal(svCheck(svTemplate("satisfaction")).length, 0, "ready-made questions need no change");
});

test("building, a new version once answers arrived, approval and the plan's live-survey number", () => {
  const { d, log } = desk(); d.tier = "pro";
  d.act("sv:new", { online: true, partner: false, redraw: () => undefined });
  const s = d.save(); assert.equal(s.version, 1);
  d.approvalOn = true; assert.equal(d.setState(s.id, "open"), false); assert.equal(d.refused, "needs_approval_first");
  d.submit(s.id); d.decide(s.id, "send_back"); d.submit(s.id); d.decide(s.id, "approve"); assert.ok(d.setState(s.id, "open"));
  d.answer(s.id, "kiosk", { visit: { number: 4 } }, { online: true });
  d.edit(s.id); d.draft.questions.push({ id: "extra", type: "yes_no", key: null, text: "Was it clean?", choices: [] }); assert.equal(d.save().version, 2);
  const free = desk().d; free.tier = "free";
  for (let i = 0; i < 2; i++) { free.draft = free.blank("quick_rating"); free.setState(free.save().id, "open"); }
  free.draft = free.blank("quick_rating"); const third = free.save(); assert.equal(free.setState(third.id, "open"), false); assert.equal(free.refused, "plan_limit_live_surveys");
  assert.equal(free.kindAllowed("what_matters_most"), false); assert.equal(free.typeAllowed("ranking"), false);
  inContract(log);
});

test("results never show below 5 answers, Please check never deletes, and anonymous answers carry nobody", () => {
  const { d, log } = desk();
  const s = d.blank("satisfaction"); s.state = "open"; s.anonymous = true; d.surveys.push(s); d.cur = s.id;
  for (const r of [5, 4, 2, 4]) d.answer(s.id, "kiosk", { visit: { number: r } }, { online: false });
  assert.equal(d.result(s.questions[0]!, d.rows()), null);
  const html = svResultsView(d, LOOK); assert.match(html, /ppl_too_few/); assert.doesNotMatch(html, /sv-fill/);
  d.answer(s.id, "kiosk", { visit: { number: 4 } }, { online: false });
  const r = d.result(s.questions[0]!, d.rows())!; assert.equal(r.n, 5); assert.equal(r.good, 80);
  const fast = d.answer(s.id, "smartphone", { visit: { number: 5 } }, { online: true, seconds: 1 })!;
  assert.equal(fast.result, "please_check"); assert.ok(d.answers.includes(fast));
  d.decideFlag(fast.id, false); assert.equal(fast.result, "set_aside"); assert.ok(d.answers.includes(fast), "set aside, never deleted");
  assert.equal(d.answers.filter((a) => a.survey === s.id && a.st === "queued").length, 5, "answered offline: queued, never shown as sent");
  inContract(log);
});

test("the kiosk and the phone ask one question a page, and Why? only after an unhappy answer", () => {
  const { d, log } = desk(); const ctx = { online: true, partner: false, redraw: () => undefined };
  const main = d.sv()!;
  d.restartKiosk(); d.act("sv:k:5", ctx); d.act("sv:knext", ctx);
  assert.equal(d.visible(main, d.kiosk.answers).some((x) => x.id === "better"), false, "a happy person is not asked why");
  d.act("sv:k:ppl_sv_c_under5:c", ctx); d.act("sv:knext", ctx); d.act("sv:k:yes:c", ctx); d.act("sv:knext", ctx);
  assert.ok(d.kiosk.done); assert.match(svKioskView(d, LOOK), /ppl_thanks/);
  d.act("sv:kagain", ctx); d.act("sv:k:1", ctx);
  assert.ok(d.visible(main, d.kiosk.answers).some((x) => x.id === "better"), "an unhappy person is asked why");
  main.rule = "one_per_phone"; d.act("sv:pstart", ctx); assert.equal(d.phone.step, "code");
  d.input("sv:pcode", "12345"); d.act("sv:pcode", ctx); assert.equal(d.phone.step, "code");
  d.input("sv:pcode", "123456"); d.act("sv:pcode", ctx); assert.equal(d.phone.step, "question");
  d.phone.way = "whatsapp"; assert.equal(d.wayWhy("whatsapp", true), "coming_soon"); d.tier = "free"; assert.equal(d.wayWhy("whatsapp", false), "plan");
  inContract(log);
});

test("research tools by plan, rewards through the partner, the panel never shows who, and every screen draws", () => {
  const { d, log } = desk(); const ctx = { online: true, partner: true, redraw: () => undefined };
  d.tier = "pro";
  const html = svResearchView(d, LOOK);
  assert.match(html, /ppl_sv_diff_/); assert.match(html, /ppl_sv_balanced/); assert.match(html, /ppl_sv_theme_waiting_time/);
  d.tier = "plus"; assert.match(svResearchView(d, LOOK), /ppl_sv_from_pro/);
  const a = d.answers.find((x) => x.survey === d.cur && x.result === "accepted")!;
  d.act(`sv:reward:${a.id}:airtime`, ctx); assert.equal(d.rewards[0]!.state, "coming_to_country", "never paid before a partner is signed");
  d.act(`sv:reward:${a.id}:airtime`, ctx); assert.equal(d.refused, "one_reward_per_person");
  d.tier = "pro"; d.panel.wanted = 500; d.act("sv:panel", ctx); assert.equal(d.panel.reached, 500); assert.match(svRewardsView(d, LOOK), /ppl_sv_panel_never/);
  for (const draw of [svSurveysView, svBuilderView, svResultsView, svTasksView, svDevicesView, svPlanView, svScreenView, svPhoneView]) assert.ok(draw(d, LOOK).length > 50);
  assert.match(svCDisplayView(d, 2, LOOK), /ppl_rate_us/);
  assert.ok(MIN_GROUP === 5);
  inContract(log);
});
