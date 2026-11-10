/** Sign-up, sign-in, help and notifications on phones with no apps (MASTER UPDATE sections 54, 55 and 62; build section 3):
 *  the TypeScript port of identity/basic_phone.py, proved by contract/vectors/basicphone.v1.json. One engine for USSD, text
 *  messages and a voice menu; pages are word keys with values, so every channel speaks the person's language. A number alone
 *  never opens an account (the PIN is the second proof); recovery is online only; no secret is ever shown, except the recovery
 *  code once, to the person who just created the account. */
import { pinProblem } from "./signin.js";

export type BpScreen = "welcome" | "pin" | "locked" | "age" | "too_young" | "username" | "new_pin" | "pin_again" | "terms" | "created" | "home"
  | "messages" | "read" | "help" | "states" | "state" | "pin_help" | "link_sent" | "handed" | "bye";
export interface BpState { screen: BpScreen; signed_in: boolean; username: string | null; pin: string | null; note: [string, Record<string, string | number>] | null; pick: number | null; back: BpScreen }
export type BpLine = [string, Record<string, string | number>];
export interface BpCtx { age: number; lines: [string, string][]; recovery?: string; case?: string }
export type PinCheck = "ok" | "locked" | ["wrong", number];
export interface BpRules { pinCheck: (pin: string) => PinCheck; usernameCheck: (u: string) => string | null; taken: (u: string) => boolean }
export type BpAction = { sign_in: true } | { wrong_pin: number } | { create: { username: string; pin: string } } | { read: string } | { send_link: "help" } | { hand_over: "help" };

export const BP_WELCOME = ["sign_in", "create", "help"] as const;
export const BP_HELP = ["states", "pin_help", "link", "person"] as const;
export const BP_STATES = ["queued", "sent", "accepted", "confirmed", "failed"] as const;
export const BP_MAX_LINES = 5;

export const bpStart = (): BpState => ({ screen: "welcome", signed_in: false, username: null, pin: null, note: null, pick: null, back: "welcome" });

export function bpPage(state: BpState, ctx: BpCtx): BpLine[] {
  const note: BpLine[] = state.note ? [state.note] : [];
  const back: BpLine[] = [["ch_back", { n: 0 }]];
  switch (state.screen) {
    case "welcome": return [["bp_title", {}], ...BP_WELCOME.map((k, i): BpLine => [`bp_${k}`, { n: i + 1 }]), ["ch_end", { n: 0 }]];
    case "pin": return [...note, ["bp_enter_pin", {}]];
    case "locked": return [["bp_locked", {}]];
    case "age": return [["bp_age", { age: ctx.age }], ["bp_yes", { n: 1 }], ["bp_no", { n: 2 }]];
    case "too_young": return [["bp_too_young", { age: ctx.age }]];
    case "username": return [...note, ["bp_username", {}]];
    case "new_pin": return [...note, ["bp_new_pin", {}]];
    case "pin_again": return [["bp_pin_again", {}]];
    case "terms": return [["bp_terms", {}], ["bp_agree", { n: 1 }], ...back];
    case "created": return [["bp_created", { username: state.username ?? "" }], ["bp_recovery", { code: ctx.recovery ?? "" }]];
    case "home": return [["bp_home", {}], ["bp_messages", { n: 1, count: ctx.lines.length }], ["bp_help", { n: 2 }], ["ch_end", { n: 0 }]];
    case "messages": {
      const lines = ctx.lines.slice(0, BP_MAX_LINES);
      return [...(lines.length ? lines.map(([, t], i): BpLine => ["bp_msg_line", { n: i + 1, title: t }]) : [["bp_no_messages", {}] as BpLine]), ...back];
    }
    case "read": return state.pick !== null && state.pick < ctx.lines.length ? [["bp_msg_read", { title: ctx.lines[state.pick]![1] }], ...back] : back;
    case "help": return [["bp_help_title", {}], ...BP_HELP.map((k, i): BpLine => [`bp_help_${k}`, { n: i + 1 }]), ...back];
    case "states": return [["bp_states_title", {}], ...BP_STATES.map((k, i): BpLine => [`bp_state_${k}`, { n: i + 1 }]), ...back];
    case "state": return [[`kp_state_${BP_STATES[state.pick ?? 0]}`, {}], ...back];
    case "pin_help": return [["bp_pin_help", {}], ...back];
    case "link_sent": return [["bp_link_sent", {}]];
    case "handed": return [["bp_handed", { case: ctx.case ?? "" }]];
    default: return [["ch_bye", {}]];
  }
}

const to = (s: BpState, screen: BpScreen, note: BpState["note"] = null): BpState => ({ ...s, screen, note });
const num = (t: string): boolean => /^\d+$/.test(t);

export function bpStep(state: BpState, text: string, ctx: BpCtx, rules: BpRules): [BpState, boolean, BpAction | null] {
  const s: BpState = { ...state }, t = (text ?? "").trim(), n = num(t) ? Number(t) : -1;
  switch (s.screen) {
    case "welcome": {
      if (t === "0") return [to(s, "bye"), true, null];
      const pick = n >= 1 && n <= BP_WELCOME.length ? BP_WELCOME[n - 1] : null;
      if (pick === "sign_in") return [to(s, "pin"), false, null];
      if (pick === "create") return [to(s, "age"), false, null];
      if (pick === "help") return [to({ ...s, back: "welcome" }, "help"), false, null];
      return [s, false, null];
    }
    case "pin": {
      const r = rules.pinCheck(t);
      if (r === "ok") return [to({ ...s, signed_in: true }, "home"), false, { sign_in: true }];
      if (r === "locked") return [to(s, "locked"), true, null];
      return [to(s, "pin", ["bp_wrong_pin", { left: r[1] }]), false, { wrong_pin: r[1] }];
    }
    case "age":
      if (t === "1") return [to(s, "username"), false, null];
      if (t === "2") return [to(s, "too_young"), true, null];
      return [s, false, null];
    case "username": {
      const u = t.toLowerCase().replace(/^@/, "");
      const why = rules.usernameCheck(u);
      if (why) return [to(s, "username", [`username_${why}`, {}]), false, null];
      if (rules.taken(u)) return [to(s, "username", ["username_taken", {}]), false, null];
      return [to({ ...s, username: u }, "new_pin"), false, null];
    }
    case "new_pin":
      if (pinProblem(t)) return [to(s, "new_pin", ["bp_pin_rule", {}]), false, null];
      return [to({ ...s, pin: t }, "pin_again"), false, null];
    case "pin_again":
      if (t !== s.pin) return [to({ ...s, pin: null }, "new_pin", ["bp_pin_mismatch", {}]), false, null];
      return [to(s, "terms"), false, null];
    case "terms":
      if (t === "0") return [bpStart(), false, null];
      if (t === "1") return [to({ ...s, pin: null }, "created"), true, { create: { username: s.username ?? "", pin: s.pin ?? "" } }];
      return [s, false, null];
    case "home":
      if (t === "0") return [to(s, "bye"), true, null];
      if (t === "1") return [to(s, "messages"), false, null];
      if (t === "2") return [to({ ...s, back: "home" }, "help"), false, null];
      return [s, false, null];
    case "messages": {
      if (t === "0") return [to(s, "home"), false, null];
      const lines = ctx.lines.slice(0, BP_MAX_LINES);
      if (n >= 1 && n <= lines.length) return [to({ ...s, pick: n - 1 }, "read"), false, { read: lines[n - 1]![0] }];
      return [s, false, null];
    }
    case "read": return t === "0" ? [to(s, "messages"), false, null] : [s, false, null];
    case "help": {
      if (t === "0") return [to(s, s.back || "welcome"), false, null];
      const pick = n >= 1 && n <= BP_HELP.length ? BP_HELP[n - 1] : null;
      if (pick === "states") return [to(s, "states"), false, null];
      if (pick === "pin_help") return [to(s, "pin_help"), false, null];
      if (pick === "link") return [to(s, "link_sent"), true, { send_link: "help" }];
      if (pick === "person") return [to(s, "handed"), true, { hand_over: "help" }];
      return [s, false, null];
    }
    case "states":
      if (t === "0") return [to(s, "help"), false, null];
      if (n >= 1 && n <= BP_STATES.length) return [to({ ...s, pick: n - 1 }, "state"), false, null];
      return [s, false, null];
    case "state": case "pin_help":
      return t === "0" ? [to(s, s.screen === "state" ? "states" : "help"), false, null] : [s, false, null];
    default: return [s, true, null];
  }
}

export function textNotification(title: string, record: string | null, words: (k: string) => string): string {
  return [title, ...(record ? [`${words("msg_record")} ${record}`] : []), words("bp_read_more")].join(" ");
}
