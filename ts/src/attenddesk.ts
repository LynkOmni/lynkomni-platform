/** LynkAttend in full on a device (LynkA; master blueprint section 63; build section 3B): the manager's dashboard and the door.
 *  The same engine runs in the Business app (LynkMobile, LynkTab, LynkPC), on LynkPOS and on LynkKiosk; it mirrors the reference
 *  service (people/attendance.py, people/door.py) and takes every rule from ts/src/attendance.ts.
 *
 *  What never happens here: a PIN, an IDCN, an ID number, a name or a contact in an event; a PIN chosen or typed by a manager;
 *  a check-in that is blocked because a checker is away (it is flagged); a record changed quietly (the old line is kept); a
 *  person checking themself in by hand or naming themself as checker. PINs are created and sent by the cloud only, so those
 *  buttons wait for the internet; everything at the door works without it. Words are "ppl_" keys in web/shell. */
import { esc } from "./shell.js";
import type { Icon, T } from "./shell.js";
import { newId, randomBelow, randomBytes } from "./emulator.js";
import { ATTEND_SETS, IDCN_LENGTH, IDCN_TRIES, PIN_GROUP_SIZE, PIN_LENGTH, PIN_PAUSE_SECONDS, PIN_TRIES_BEFORE_PAUSE, checkerFlags, door, idcn, isEasyPin, meansOf, newPin, noCheckOutDue, pinGroupWarning, setsAllowed } from "./attendance.js";
import type { AttendSet, DoorOut, Means } from "./attendance.js";
import { idcnEntry } from "./peopleparts.js";

export type AtEmit = (type: string, payload: Record<string, unknown>, origin?: "device" | "server") => void;
type St = "queued" | "sent" | "accepted" | "confirmed" | "failed";
export const AT_TIERS = ["free", "plus", "pro", "max"] as const;
export type AtTier = (typeof AT_TIERS)[number];
/** The plan numbers the screens show (services/billing.py FEATURES lynkattend, passed in by the build; never typed here). */
export interface AtPlan { price_usd: number; people_included: number; extra_person_cents: number | null; branches: number | null; managers: number | null; door_devices: number | null }
export const SEND_WAYS = ["email", "lynkchat", "text"] as const;
const AT_PARTNER_WAYS = ["text"];
export const AGREE_WAYS = ["email_link", "code_text", "finger_signature", "full_id_number"] as const;
export const REQUEST_REMINDER_DAYS = [7, 14, 25] as const, REQUEST_DELETE_AFTER_DAYS = 30, WARN_TIMES = 3;
const AT_DID = ["registered", "confirmed", "pin_created", "pin_re_created", "pin_sent", "pin_shown", "hand_check_in", "corrected_missed_check_out", "details_deleted", "door_device_locked"];
const AT_HAND_REASONS = ["all_means_failed", "device_broken", "other"] as const;

export interface Person { id: string; name: string; set: AttendSet; idDoc: "official" | "work"; idNumber: string; idcn: string; pin: string; pinState: "none" | "live" | "blocked";
  agreed: string | null; enrolled: Means[]; confirmed: boolean; sent: string | null; lang: string; wasThisYou: boolean; onLeave: boolean; role: "staff" | "attendee";
  state: "not_yet" | "in" | "out"; means: string; at: number; flags: string[]; backup: string | null; rec: string | null }
export interface Rec { id: string; person: string; inAt: number; outAt: number | null; means: string; backup: string | null; checker: string | null; flags: string[]; old: { outAt: number | null; reason: string }[] }
interface Visitor { id: string; name: string; host: string; doc: "official" | "work" | "none"; state: "inside" | "waiting_for_manager" | "refused" | "left"; allowedBy: string | null; guardian: boolean }
interface Req { id: string; person: string; kind: "delete_my_details" | "dispute"; days: number; reminded: number; closed: string | null }
interface Draft { name: string; idNumber: string; idDoc: "official" | "work"; set: AttendSet; id: string | null }
interface DoorState { step: "pin" | "check" | "done"; dir: "in" | "out"; pin: string; pinFails: number; pausedUntil: number; member: Person | null; attempts: ("ok" | "fail")[]; broken: string[]; typed: string; checker: string | null; out: DoorOut | null; note: string; minutes: number }
interface DoorDevice { id: string; name: string; locked: boolean }
interface CourseEvent { id: string; name: string; attendees: number; sessions: number; cert: string }

const AT_SEED: [string, AttendSet, string, string, string][] = [["Aline", "finger_idcn", "482913", "305571", "fr"], ["Eric", "idcn", "739154", "120480", "en"], ["Grace", "face_idcn", "561840", "774209", "sw"], ["Joseph", "idcn", "205937", "918366", "ar"]];

export class AttendDesk {
  readonly placeId = newId();
  readonly deviceId = newId();
  readonly groupId = newId();
  readonly me = newId();                                   // the signed-in manager (never a person's own record)
  tier: AtTier = "plus";
  people: Person[] = AT_SEED.map(([name, set, pin, id, lang]) => ({ id: newId(), name, set, idDoc: "work" as const, idNumber: id, idcn: idcn(id) ?? "000000", pin, pinState: "live" as const, agreed: "email_link", enrolled: meansOf(set).filter((m) => m !== "idcn"),
    confirmed: true, sent: "email", lang, wasThisYou: true, onLeave: false, role: "staff" as const, state: "not_yet" as const, means: "", at: 0, flags: [], backup: null, rec: null }));
  usedPins = new Set(AT_SEED.map((x) => x[2]));               // every PIN the group ever gave, live or dead
  recs: Rec[] = [];
  checkers: string[] = this.people.slice(0, 3).map((p) => p.id);
  visitors: Visitor[] = [];
  requests: Req[] = [];
  history: { at: number; what: string; person: string | null }[] = [];
  messages: { person: string; rec: string; dir: "in" | "out"; at: number }[] = [];   // "Was this you?" on the person's own phone
  devices: DoorDevice[] = [{ id: this.deviceId, name: "LynkPOS", locked: false }];
  events: CourseEvent[] = [];
  shiftEnd: number | null = 17 * 60;
  allow = { face: true, finger: true };                    // what the country pack allows (unknown until the lawyer check: selectable with agreement)
  readers = { face: true, finger: true };                  // what this device has; a missing or broken reader moves to the next means
  clockWrong = false;
  shown = new Set<string>();
  open: string | null = null;
  draft: Draft | null = null;
  vdraft = { name: "", host: "", doc: "official" as Visitor["doc"], guardian: false };
  fire: { staff: string[]; visitors: string[] } | null = null;
  door: DoorState = AttendDesk.freshDoor();
  note = "";
  private lastMinutes = 0;
  constructor(private emit: AtEmit, readonly plans: Record<AtTier, AtPlan>, private now: () => number = Date.now) {}
  static freshDoor(dir: "in" | "out" = "in"): DoorState { return { step: "pin", dir, pin: "", pinFails: 0, pausedUntil: 0, member: null, attempts: [], broken: [], typed: "", checker: null, out: null, note: "", minutes: 0 }; }

  plan(): AtPlan { return this.plans[this.tier]; }
  person(id: string | null): Person | undefined { return this.people.find((p) => p.id === id); }
  private log(what: string, person: string | null = null): void { this.history.unshift({ at: this.now(), what, person }); }
  inCount(): number { return this.people.filter((p) => p.state === "in").length; }
  sets(): AttendSet[] { return setsAllowed(this.allow.face, this.allow.finger); }
  group(): { used: number; size: number; warn: boolean } { return { used: this.usedPins.size, size: PIN_GROUP_SIZE, warn: pinGroupWarning(this.usedPins.size) }; }
  /** Only people who checked in at least once this month are counted. */
  bill(): { people: number; included: number; extra: number; cents: number } {
    const n = new Set(this.recs.map((r) => r.person)).size, p = this.plan(), extra = Math.max(0, n - p.people_included);
    return { people: n, included: p.people_included, extra, cents: Math.round(p.price_usd * 100) + extra * (p.extra_person_cents ?? 0) };
  }

  // ---- registration (once per person, by the manager): details, set, agreement, enrolment, Confirm, Create PIN, Send PIN
  startDraft(): void { this.draft = { name: "", idNumber: "", idDoc: "work", set: this.sets().includes("idcn") ? "idcn" : this.sets()[0]!, id: null }; this.note = ""; }
  draftIdcn(): string | null { return this.draft ? idcn(this.draft.idNumber) : null; }
  full(): boolean { const p = this.plan(); return p.extra_person_cents === null && this.people.length >= p.people_included; }
  register(): boolean {
    const d = this.draft; if (!d || d.id) return false;
    if (!d.name.trim()) { this.note = "ppl_at_name_needed"; return false; }
    const code = idcn(d.idNumber);
    if (code === null) { this.note = "ppl_at_too_few"; return false; }       // "Please register another ID document for this person."
    if (!this.sets().includes(d.set)) { this.note = "ppl_at_not_allowed"; return false; }
    if (this.full()) { this.note = "ppl_at_limit"; return false; }
    const p: Person = { id: newId(), name: d.name.trim(), set: d.set, idDoc: d.idDoc, idNumber: d.idNumber, idcn: code, pin: "", pinState: "none", agreed: null, enrolled: [], confirmed: false, sent: null, lang: "en", wasThisYou: true,
      onLeave: false, role: "staff", state: "not_yet", means: "", at: 0, flags: [], backup: null, rec: null };
    this.people.push(p); d.id = p.id; this.note = "";
    this.emit("AttendancePersonRegistered", { member_id: p.id, place_id: this.placeId, set: p.set, id_document: p.idDoc, pin_group_id: this.groupId, role: "staff" });
    this.log("registered", p.id); return true;
  }
  /** The person agrees in one step; with the full ID number (a device without a touch screen) it must match, and it is not the IDCN. */
  agree(id: string, method: string, typedId = ""): boolean {
    const p = this.person(id); if (!p || p.agreed || !(AGREE_WAYS as readonly string[]).includes(method)) return false;
    if (method === "full_id_number" && typedId !== p.idNumber) { this.note = "ppl_at_id_mismatch"; return false; }
    p.agreed = method; this.note = "";
    this.emit("AttendanceConsentRecorded", { member_id: p.id, consent_id: newId(), method, covers: [...meansOf(p.set).filter((m) => m !== "idcn"), "no_sharing"] });
    return true;
  }
  needsEnrol(p: Person): Means[] { return meansOf(p.set).filter((m) => m !== "idcn" && !p.enrolled.includes(m)); }
  enrol(id: string, means: Means): boolean {
    const p = this.person(id); if (!p || !p.agreed || !this.needsEnrol(p).includes(means)) return false;
    if (!this.readers[means as "face" | "finger"]) { this.note = means === "finger" ? "ppl_at_reader_needed" : "ppl_at_camera_needed"; return false; }
    p.enrolled.push(means); this.note = "";
    this.emit("BiometricEnrolled", { member_id: p.id, means, device_id: this.deviceId }); return true;
  }
  confirm(id: string): boolean {
    const p = this.person(id); if (!p || !p.agreed || this.needsEnrol(p).length) return false;
    p.confirmed = true; this.log("confirmed", p.id); return true;
  }
  private draw = (): number => { const b = randomBytes(4); return ((b[0]! << 24) | (b[1]! << 16) | (b[2]! << 8) | b[3]!) >>> 0; };
  /** LynkOmni creates the PIN by itself (cloud only): the manager never types or chooses it. */
  createPin(id: string, online: boolean): boolean {
    const p = this.person(id); if (!p || !p.confirmed || p.pinState !== "none" || !online) return false;
    p.pin = newPin(this.draw, this.usedPins); this.usedPins.add(p.pin); p.pinState = "live";
    this.emit("AttendancePinCreated", { member_id: p.id, pin_group_id: this.groupId }, "server"); this.log("pin_created", p.id); return true;
  }
  recreatePin(id: string, online: boolean): boolean {
    const p = this.person(id); if (!p || p.pinState !== "blocked" || !online) return false;
    p.pin = newPin(this.draw, this.usedPins); this.usedPins.add(p.pin); p.pinState = "live"; p.sent = null;     // the old PIN is dead for ever
    this.emit("AttendancePinRecreated", { member_id: p.id }, "server"); this.log("pin_re_created", p.id); return true;
  }
  /** The PIN and the IDCN go together, to the person's own contact. A text message waits for the messaging partner. */
  sendPin(id: string, way: string, online: boolean, partner: boolean): "sent" | "coming_soon" | null {
    const p = this.person(id); if (!p || p.pinState !== "live" || !online || !(SEND_WAYS as readonly string[]).includes(way)) return null;
    if (AT_PARTNER_WAYS.includes(way) && !partner) return "coming_soon";
    p.sent = way; this.emit("AttendancePinSent", { member_id: p.id, channel: way }, "server"); this.log(`pin_sent_${way}`, p.id); return "sent";
  }
  toggleShow(id: string, online: boolean): void {
    if (this.shown.has(id)) { this.shown.delete(id); return; }
    const p = this.person(id); if (!p || !p.pin || !online) return;
    this.shown.add(id); this.emit("AttendancePinShown", { member_id: id, by: this.me }, "server"); this.log("pin_shown", id);   // every Show is recorded
  }
  toggleChecker(id: string): void { this.checkers = this.checkers.includes(id) ? this.checkers.filter((c) => c !== id) : [...this.checkers, id]; this.log("checker_list_set"); }

  // ---- the door: Check-in or Check-out, the PIN, then the person's set in the order Face, Finger, IDCN
  doorDir(dir: "in" | "out"): void { if (this.door.step === "pin") { this.door = AttendDesk.freshDoor(dir); } }
  doorDigit(d: string): void {
    const D = this.door;
    if (D.step === "pin" && this.now() >= D.pausedUntil && D.pin.length < PIN_LENGTH) { D.pin += d; D.note = ""; if (D.pin.length === PIN_LENGTH) this.doorPin(); }
    else if (D.step === "check" && D.out?.means === "idcn" && D.typed.length < IDCN_LENGTH) D.typed += d;
  }
  doorBack(): void { const D = this.door; if (D.step === "pin") D.pin = D.pin.slice(0, -1); else if (D.step === "check") D.typed = D.typed.slice(0, -1); }
  private doorPin(): void {
    const D = this.door, m = isEasyPin(D.pin) ? undefined : this.people.find((x) => x.pin === D.pin && x.pinState !== "none");
    D.pin = "";
    if (!m) { D.pinFails += 1; D.note = "ppl_door_pin_wrong"; if (D.pinFails >= PIN_TRIES_BEFORE_PAUSE) { D.pausedUntil = this.now() + PIN_PAUSE_SECONDS * 1000; D.pinFails = 0; D.note = "ppl_door_paused"; } return; }
    D.pinFails = 0;
    if (m.pinState === "blocked") { D.note = "ppl_door_blocked"; return; }
    if (D.dir === "in" && m.state === "in") { D.note = "ppl_at_already_in"; return; }
    if (D.dir === "out" && m.state !== "in") { D.note = "ppl_at_not_in"; return; }
    const broken = (["face", "finger"] as const).filter((x) => !this.readers[x]);
    D.member = m; D.step = "check"; D.attempts = []; D.broken = [...broken]; D.typed = ""; D.checker = null; D.out = door(m.set, [], D.broken);
  }
  /** The reader's answer for Face or Finger (on an emulator, the sandbox reader buttons). */
  doorReader(result: "ok" | "fail" | "not_working"): void {
    const D = this.door; if (D.step !== "check" || !D.out || D.out.means === "idcn" || !D.out.means) return;
    if (result === "not_working") D.broken.push(D.out.means); else D.attempts.push(result);
    this.doorRun();
  }
  doorIdcn(): void {
    const D = this.door; if (D.step !== "check" || D.out?.means !== "idcn" || D.typed.length !== IDCN_LENGTH || !D.checker || !D.member) return;
    D.attempts.push(D.typed === D.member.idcn ? "ok" : "fail"); D.typed = "";
    this.doorRun();
  }
  pickChecker(name: string): void { const m = this.door.member; this.door.checker = name && m && name !== m.name && this.doorCheckers().includes(name) ? name : null; }
  doorCheckers(): string[] { return this.checkers.map((c) => this.person(c)?.name ?? "").filter(Boolean); }
  idcnTriesLeft(): number | null {
    const D = this.door; if (!D.out || D.out.means !== "idcn") return null;
    const used = D.out.steps.filter((s) => s.means === "idcn" && s.result === "fail").length;
    return used ? IDCN_TRIES - used : null;
  }
  private doorRun(): void {
    const D = this.door, m = D.member!; D.out = door(m.set, D.attempts, D.broken);
    if (D.out.result === "waiting") return;
    D.step = "done";
    if (D.out.result === "pin_blocked") { m.pinState = "blocked"; this.emit("AttendancePinBlocked", { member_id: m.id, reason: "idcn_wrong_5_times" }); return; }
    if (D.out.result === "see_manager") return;
    const checker = D.out.means === "idcn" ? this.people.find((x) => x.name === D.checker) ?? null : null;
    const flags = [...(D.out.means === "idcn" ? checkerFlags(checker?.state === "in") : []), ...(this.clockWrong ? ["device_clock_wrong"] : [])];
    this.record(m, D.dir, D.out.means ?? "idcn", D.out.backup_from, checker?.id ?? null, flags);
    D.minutes = this.lastMinutes;
  }
  private record(m: Person, dir: "in" | "out", means: string, backup: string | null, checker: string | null, flags: string[], hand?: { by: string; reason: string }): void {
    const base: Record<string, unknown> = { member_id: m.id, device_id: this.deviceId, means };
    if (backup) base["backup_from"] = backup;
    if (checker) base["checker_id"] = checker;
    if (flags.length) base["flags"] = flags;
    if (dir === "in") {
      const rec: Rec = { id: newId(), person: m.id, inAt: this.now(), outAt: null, means, backup, checker, flags: [...flags], old: [] };
      this.recs.unshift(rec); m.rec = rec.id;
      this.emit("CheckedIn", { record_id: rec.id, ...base, ...(hand ? { hand_by: hand.by, hand_reason: hand.reason } : {}) });
      if (m.onLeave) this.flag(rec, "warning_sign");                                     // a check-in while approved leave is running
      const backups = this.recs.filter((r) => r.person === m.id && (r.backup || r.flags.includes("checker_not_checked_in"))).length;
      if (backups >= WARN_TIMES) this.flag(rec, "warning_sign");
    } else {
      const rec = this.recs.find((r) => r.id === m.rec); if (!rec) return;
      rec.outAt = this.now(); this.lastMinutes = Math.max(0, Math.round((rec.outAt - rec.inAt) / 60000));
      this.emit("CheckedOut", { record_id: rec.id, ...base, minutes: this.lastMinutes });
    }
    m.state = dir === "in" ? "in" : "out"; m.means = means; m.at = this.now(); m.flags = flags; m.backup = backup;
    if (m.wasThisYou && m.rec) this.messages.unshift({ person: m.id, rec: m.rec, dir, at: this.now() });
  }
  doorReset(): void { this.door = AttendDesk.freshDoor(this.door.dir); }
  private flag(rec: Rec, flag: string): void { if (rec.flags.includes(flag)) return; rec.flags.push(flag); this.emit("CheckInFlagged", { record_id: rec.id, flag }); }
  /** "Not me" on the person's own phone: the record is flagged and the manager is told at once. */
  notMe(recId: string): void { const rec = this.recs.find((r) => r.id === recId); if (rec) { this.flag(rec, "not_me"); this.messages = this.messages.filter((m) => m.rec !== recId); } }
  /** Every means failed: the manager checks the person in by hand, with a reason, never themself. */
  byHand(id: string, reason: string): boolean {
    const m = this.person(id); if (!m || m.state === "in" || m.id === this.me || !(AT_HAND_REASONS as readonly string[]).includes(reason)) return false;
    this.record(m, "in", "hand", null, null, ["by_hand", ...(this.clockWrong ? ["device_clock_wrong"] : [])], { by: this.me, reason }); this.log("hand_check_in", m.id); return true;
  }
  /** Missed check-out: marked 2 hours after the shift ends (at midnight without shifts); the manager fixes the time with a reason. */
  markNoCheckOut(minuteOfDay: number): number {
    let n = 0;
    for (const r of this.recs) if (r.outAt === null) { const d = new Date(r.inAt); if (minuteOfDay >= noCheckOutDue(d.getHours() * 60 + d.getMinutes(), this.shiftEnd) && !r.flags.includes("no_check_out")) { this.flag(r, "no_check_out"); n++; } }
    return n;
  }
  fixCheckOut(recId: string): boolean {
    const r = this.recs.find((x) => x.id === recId), m = r && this.person(r.person); if (!r || !m || r.outAt !== null || m.id === this.me) return false;
    r.old.push({ outAt: r.outAt, reason: "missed_check_out" });                          // the old line is kept
    const end = new Date(r.inAt); end.setHours(0, this.shiftEnd ?? 1439, 0, 0); r.outAt = Math.max(end.getTime(), r.inAt); m.state = "out";
    this.emit("AttendanceCorrected", { record_id: r.id, by: this.me, reason: "missed_check_out" }); this.log("corrected_missed_check_out", m.id); return true;
  }
  /** The clock guard: when the device comes online with a wrong clock, the records it made are marked for the manager. */
  clockChecked(): number { let n = 0; if (this.clockWrong) for (const r of this.recs) if (r.outAt === null && !r.flags.includes("device_clock_wrong")) { this.flag(r, "device_clock_wrong"); n++; } return n; }

  // ---- visitors and the fire list
  visitorIn(): boolean {
    const v = this.vdraft; if (!v.name.trim() || !this.person(v.host)) { this.note = "ppl_at_visitor_needed"; return false; }
    const waiting = v.doc === "none", vis: Visitor = { id: newId(), name: v.name.trim(), host: v.host, doc: v.doc, state: waiting ? "waiting_for_manager" : "inside", allowedBy: null, guardian: v.guardian };
    this.visitors.unshift(vis); this.note = "";
    this.emit("VisitorSignedIn", { visitor_id: vis.id, place_id: this.placeId, host_id: v.host, id_document: v.doc, ...(v.guardian ? { with_guardian: true } : {}) });
    this.vdraft = { name: "", host: "", doc: "official", guardian: false }; return true;
  }
  /** A visitor without an ID document gets in only with the manager's yes; the record shows who allowed it. */
  decideVisitor(id: string, decision: "allow" | "refuse"): void {
    const v = this.visitors.find((x) => x.id === id); if (!v || v.state !== "waiting_for_manager") return;
    v.state = decision === "allow" ? "inside" : "refused"; v.allowedBy = decision === "allow" ? this.me : null;
    this.emit("VisitorDecision", { visitor_id: id, decision, by: this.me }); this.log(`visitor_${decision}`);
  }
  visitorOut(id: string): void { const v = this.visitors.find((x) => x.id === id); if (v?.state === "inside") { v.state = "left"; this.emit("VisitorSignedOut", { visitor_id: id }); } }
  openFire(): void { this.fire = { staff: this.people.filter((p) => p.state === "in").map((p) => p.id), visitors: this.visitors.filter((v) => v.state === "inside").map((v) => v.id) }; this.emit("FireListOpened", { place_id: this.placeId, by: this.me }); }

  // ---- the person's control: delete my details or a dispute, reminders at 7, 14 and 25 days, deleted by themselves after 30
  ask(id: string, kind: Req["kind"]): void {
    if (!this.person(id) || this.requests.some((r) => r.person === id && !r.closed)) return;
    const r: Req = { id: newId(), person: id, kind, days: 0, reminded: 0, closed: null }; this.requests.unshift(r);
    this.emit("AttendanceRequestRaised", { member_id: id, request_id: r.id, kind }, "server");
  }
  daysPass(n: number): void {
    for (const r of this.requests) if (!r.closed) {
      r.days += n; r.reminded = REQUEST_REMINDER_DAYS.filter((d) => r.days >= d).length;
      if (r.days >= REQUEST_DELETE_AFTER_DAYS) { this.remove(r.person, "thirty_days_passed"); r.closed = "deleted_after_30_days"; }
    }
  }
  closeRequest(id: string, del: boolean): void {
    const r = this.requests.find((x) => x.id === id); if (!r || r.closed) return;
    if (del) this.remove(r.person, "manager"); r.closed = del ? "deleted" : "answered"; this.log("request_closed");
  }
  /** Every personal detail goes; the PIN stays used in its group so it is never given again. */
  private remove(id: string, by: "manager" | "thirty_days_passed"): void {
    if (!this.person(id)) return;
    this.people = this.people.filter((p) => p.id !== id); this.checkers = this.checkers.filter((c) => c !== id); this.recs = this.recs.filter((r) => r.person !== id);
    this.messages = this.messages.filter((m) => m.person !== id); if (this.open === id) this.open = null;
    this.emit("AttendanceDetailsDeleted", { member_id: id, by }, "server"); this.log("details_deleted");
  }
  addEvent(name: string): boolean {
    const limit = this.tier === "free" ? 1 : this.tier === "plus" ? 5 : null;
    if (limit !== null && this.events.length >= limit) { this.note = "ppl_at_limit"; return false; }
    this.events.unshift({ id: newId(), name, attendees: 0, sessions: 0, cert: Array.from({ length: 4 }, () => randomBelow(36).toString(36)).join("").toUpperCase() }); return true;
  }
  lockDevice(id: string): void { const d = this.devices.find((x) => x.id === id); if (d && !d.locked) { d.locked = true; this.log("door_device_locked"); } }

  // ---- inputs and actions: every control is a button ("at:...") or a field (data-in "at:...")
  input(key: string, value: string): boolean {
    if (!key.startsWith("at:")) return false;
    const k = key.slice(3);
    if (k === "name" && this.draft) this.draft.name = value.slice(0, 60);
    else if (k === "idnum" && this.draft) this.draft.idNumber = value.replace(/\s/g, "").slice(0, 24);
    else if (k === "vname") this.vdraft.name = value.slice(0, 60);
    else if (k === "vhost") this.vdraft.host = value;
    else return false;
    return true;
  }
  act(a: string, ctx: { online: boolean; partner: boolean; typed?: string }): boolean {
    if (!a.startsWith("at:")) return false;
    const [, k = "", v = "", w = ""] = a.split(":");
    switch (k) {
      case "new": this.startDraft(); break;
      case "doc": if (this.draft && !this.draft.id && (v === "official" || v === "work")) this.draft.idDoc = v; break;
      case "set": if (this.draft && !this.draft.id && (ATTEND_SETS as readonly string[]).includes(v)) this.draft.set = v as AttendSet; break;
      case "register": this.register(); break;
      case "agree": this.agree(v, w, ctx.typed ?? ""); break;
      case "enrol": this.enrol(v, w as Means); break;
      case "confirm": this.confirm(v); break;
      case "createpin": this.createPin(v, ctx.online); break;
      case "recreate": this.recreatePin(v, ctx.online); break;
      case "send": this.note = this.sendPin(v, w, ctx.online, ctx.partner) === "coming_soon" ? "coming_soon" : ""; break;
      case "show": this.toggleShow(v, ctx.online); break;
      case "open": this.open = this.open === v ? null : v; this.note = ""; break;
      case "donenew": this.draft = null; break;
      case "checker": this.toggleChecker(v); break;
      case "leave": { const p = this.person(v); if (p) { p.onLeave = !p.onLeave; this.log("leave_approved", v); } break; }
      case "wty": { const p = this.person(v); if (p) p.wasThisYou = !p.wasThisYou; break; }
      case "hand": this.byHand(v, w); break;
      case "fixout": this.fixCheckOut(v); break;
      case "notme": this.notMe(v); break;
      case "shift": this.shiftEnd = v === "none" ? null : Number(v); break;
      case "late": this.markNoCheckOut(1439); break;
      case "vdoc": if (v === "official" || v === "work" || v === "none") this.vdraft.doc = v; break;
      case "vguard": this.vdraft.guardian = !this.vdraft.guardian; break;
      case "vin": this.visitorIn(); break;
      case "vallow": this.decideVisitor(v, "allow"); break;
      case "vrefuse": this.decideVisitor(v, "refuse"); break;
      case "vout": this.visitorOut(v); break;
      case "fire": this.openFire(); break;
      case "fireclose": this.fire = null; break;
      case "ask": this.ask(v, w === "dispute" ? "dispute" : "delete_my_details"); break;
      case "days": this.daysPass(Number(v) || 0); break;
      case "reqdelete": this.closeRequest(v, true); break;
      case "reqanswer": this.closeRequest(v, false); break;
      case "event": this.addEvent(w || "ppl_at_sample_course"); break;
      case "lockdev": this.lockDevice(v); break;
      case "reader": if (v === "face" || v === "finger") this.readers[v] = !this.readers[v]; break;
      case "allow": { const on = !(this.allow.face && this.allow.finger); this.allow = { face: on, finger: on }; break; }
      case "clock": this.clockWrong = !this.clockWrong; if (!this.clockWrong) break; this.clockChecked(); break;
      case "dir": this.doorDir(v === "out" ? "out" : "in"); break;
      case "digit": if (/^\d$/.test(v)) this.doorDigit(v); break;
      case "doorback": this.doorBack(); break;
      case "doornext": this.doorReset(); break;
      case "readerok": this.doorReader("ok"); break;
      case "readerfail": this.doorReader("fail"); break;
      case "readerbroken": this.doorReader("not_working"); break;
      case "idcn": this.doorIdcn(); break;
      default: return false;
    }
    return true;
  }
}

// ---- drawing ------------------------------------------------------------------------------------------------------------
export interface AtLook { t: T; icon: Icon; clock: (ms: number) => string; money: (usdCents: number) => string; online: boolean; partner: boolean; mayManage: boolean }
const atOn = (on: boolean): string => `aria-pressed="${on}"`;
const atChip = (s: St, L: AtLook): string => `<span class="chip st-${s}">${L.icon(`status-${s}`)}<span>${esc(L.t(`st_${s}`))}</span></span>`;
const atTag = (text: string, kind = ""): string => `<span class="tag ${kind}">${esc(text)}</span>`;
const atCard = (item: string, title: string, body: string): string => `<div class="card ph-card" data-item="${item}" role="group" aria-label="${esc(title)}"><h2>${esc(title)}</h2>${body}</div>`;
const atOffline = (L: AtLook): string => (L.online ? "" : `<p class="sub" role="status">${esc(L.t("ppl_at_needs_online"))}</p>`);
const atFlags = (flags: readonly string[], L: AtLook): string => flags.map((f) => atTag(L.t(`ppl_flag_${f}`), "warn")).join(" ");
const atOff = (off: boolean): string => (off ? "disabled" : "");

/** The people list, the PIN group and the open requests (app.lynkomni.com/attendance/people). */
export function peopleView(d: AttendDesk, L: AtLook): string {
  const g = d.group();
  const rows = d.people.map((p) => {
    const open = d.open === p.id, req = d.requests.find((r) => r.person === p.id && !r.closed);
    const detail = !open ? "" : `<div class="ph-detail"><p class="sub">${esc(L.t("ppl_at_set"))}: ${esc(L.t(`ppl_set_${p.set}`))} · ${esc(L.t(`ppl_at_doc_${p.idDoc}`))}</p>
      <p>${esc(L.t("ppl_at_pin"))}: <strong dir="ltr">${d.shown.has(p.id) ? esc(p.pin) : "••••••"}</strong> · IDCN: <strong dir="ltr">${d.shown.has(p.id) ? esc(p.idcn) : "••••••"}</strong></p>
      <div class="ph-row"><button type="button" class="ghost small" data-act="at:show:${p.id}" ${atOn(d.shown.has(p.id))} ${atOff(!L.mayManage || !L.online || !p.pin)}>${esc(L.t(d.shown.has(p.id) ? "ppl_at_hide" : "ppl_at_show"))}</button>
        ${p.pinState === "blocked" ? `<button type="button" class="primary small" data-act="at:recreate:${p.id}" ${atOff(!L.mayManage || !L.online)}>${esc(L.t("ppl_at_recreate"))}</button>` : ""}
        ${p.pinState === "live" ? SEND_WAYS.map((w) => `<button type="button" class="ghost small" data-act="at:send:${p.id}:${w}" ${atOff(!L.mayManage || !L.online)}>${esc(L.t(`ppl_at_way_${w}`))}</button>`).join("") : ""}</div>
      ${p.sent ? `<p class="sub">${esc(L.t("ppl_at_sent_by", { way: L.t(`ppl_at_way_${p.sent}`) }))}</p>` : ""}${d.note === "coming_soon" ? `<p class="info" role="status">${esc(L.t("coming_soon"))}</p>` : ""}${atOffline(L)}
      <p class="sub">${esc(L.t("ppl_at_show_note"))}</p>
      <div class="ph-row"><button type="button" class="ghost small" data-act="at:ask:${p.id}:delete" ${atOff(!!req)}>${esc(L.t("ppl_at_sandbox_delete"))}</button><button type="button" class="ghost small" data-act="at:ask:${p.id}:dispute" ${atOff(!!req)}>${esc(L.t("ppl_at_sandbox_dispute"))}</button></div></div>`;
    return `<li><button type="button" class="rowbtn" data-act="at:open:${p.id}" aria-expanded="${open}"><span class="main"><span class="nm">${esc(p.name)}</span><span class="sub">${esc(L.t(`ppl_set_${p.set}`))}</span></span>
      ${p.pinState === "blocked" ? atTag(L.t("ppl_at_pin_blocked"), "warn") : p.pinState === "none" ? atTag(L.t("ppl_at_no_pin")) : ""}${req ? atTag(L.t(`ppl_at_req_${req.kind}`), "warn") : ""}</button>${detail}</li>`; }).join("");
  const reqs = d.requests.filter((r) => !r.closed);
  const reqList = reqs.length ? reqs.map((r) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(d.person(r.person)?.name ?? "")} · ${esc(L.t(`ppl_at_req_${r.kind}`))}</span>
      <span class="sub">${esc(L.t("ppl_at_req_days", { n: Math.max(0, REQUEST_DELETE_AFTER_DAYS - r.days) }))}${r.reminded ? ` · ${esc(L.t("ppl_at_req_reminded", { n: r.reminded }))}` : ""}</span></span></div>
      <div class="ph-row"><button type="button" class="primary small" data-act="at:reqdelete:${r.id}" ${atOff(!L.mayManage)}>${esc(L.t("ppl_at_delete_details"))}</button>${r.kind === "dispute" ? `<button type="button" class="ghost small" data-act="at:reqanswer:${r.id}" ${atOff(!L.mayManage)}>${esc(L.t("ppl_at_answered"))}</button>` : ""}</div></li>`).join("")
    : `<li><p class="sub">${esc(L.t("ppl_at_no_requests"))}</p></li>`;
  return atCard("people_list", L.t("ppl_people"), `<button type="button" class="primary inline" data-act="at:new" ${atOff(!L.mayManage)}>${esc(L.t("ppl_at_register"))}</button>${d.full() ? `<p class="info">${esc(L.t("ppl_at_limit", { n: d.plan().people_included }))}</p>` : ""}<ul class="list">${rows}</ul>`)
    + atCard("pin_group", L.t("ppl_at_pin_group"), `<p>${esc(L.t("ppl_at_group_used", { used: g.used, size: g.size }))}</p>${g.warn ? `<p class="info" role="status">${esc(L.t("ppl_at_group_warn"))}</p>` : ""}<p class="sub">${esc(L.t("ppl_at_group_note"))}</p>`)
    + atCard("requests", L.t("ppl_at_requests"), `<ul class="list">${reqList}</ul><div class="ph-row"><button type="button" class="ghost small" data-act="at:days:7" ${atOff(!reqs.length)}>${esc(L.t("ppl_at_sandbox_days", { n: 7 }))}</button></div><p class="sub">${esc(L.t("ppl_at_req_note"))}</p>`);
}

/** Registration, one step after the other (app.lynkomni.com/attendance/people/new). */
export function registerView(d: AttendDesk, L: AtLook): string {
  const dr = d.draft ?? { name: "", idNumber: "", idDoc: "work" as const, set: "idcn" as AttendSet, id: null };
  const p = d.person(dr.id), code = idcn(dr.idNumber), locked = !!p, sets = d.sets();
  const note = d.note && d.note !== "coming_soon" ? `<p class="info" role="alert">${esc(L.t(d.note, { n: d.plan().people_included }))}</p>` : "";
  const step1 = atCard("id_document", L.t("ppl_at_step_details"), `<label class="field"><span>${esc(L.t("ppl_at_name"))}</span><input id="atName" data-in="at:name" value="${esc(dr.name)}" autocomplete="off" ${atOff(locked)} placeholder="${esc(L.t("hint_name"))}" aria-label="${esc(L.t("ppl_at_name"))}"></label>
    <div class="ph-choices small">${(["work", "official"] as const).map((x) => `<button type="button" class="ph-choice" data-act="at:doc:${x}" ${atOn(dr.idDoc === x)} ${atOff(locked)}><strong>${esc(L.t(`ppl_at_doc_${x}`))}</strong></button>`).join("")}</div>
    <label class="field"><span>${esc(L.t("ppl_at_id_number"))}</span><input id="atId" data-in="at:idnum" value="${esc(dr.idNumber)}" autocomplete="off" autocapitalize="characters" spellcheck="false" dir="ltr" ${atOff(locked)}></label>
    <p role="status">${dr.idNumber ? (code ? `IDCN: <strong dir="ltr">${esc(code)}</strong>` : esc(L.t("ppl_at_too_few"))) : esc(L.t("ppl_at_idcn_made"))}</p>`);
  const step2 = atCard("set_choice", L.t("ppl_at_set"), `<div class="ph-choices">${ATTEND_SETS.map((x) => `<button type="button" class="ph-choice" data-act="at:set:${x}" ${atOn(dr.set === x)} ${atOff(locked || !sets.includes(x))}><strong>${esc(L.t(`ppl_set_${x}`))}</strong>${sets.includes(x) ? "" : `<span>${esc(L.t("coming_soon"))}</span>`}</button>`).join("")}</div>
    ${dr.set.includes("finger") ? `<p class="info" role="status">${esc(L.t(d.readers.finger ? "ppl_at_reader_ready" : "ppl_at_reader_needed"))}</p>` : ""}<p class="sub">${esc(L.t("ppl_at_set_note"))}</p>
    ${locked ? "" : `<button type="button" class="primary inline" data-act="at:register" ${atOff(!L.mayManage)}>${esc(L.t("ppl_at_save_person"))}</button>`}${note}`);
  if (!p) return step1 + step2 + ["agreement", "enrolment", "confirm_person", "create_pin", "send_pin"].map((i) => `<span data-item="${i}" hidden></span>`).join("");
  const need = d.needsEnrol(p);
  const step3 = atCard("agreement", L.t("ppl_at_agreement"), p.agreed ? `<p role="status">${L.icon("ui-check")} ${esc(L.t("ppl_at_agreed", { way: L.t(`ppl_at_agree_${p.agreed}`) }))}</p>`
    : `<p>${esc(L.t("ppl_at_agree_text"))}</p><div class="ph-row">${AGREE_WAYS.filter((w) => w !== "full_id_number").map((w) => `<button type="button" class="ghost small" data-act="at:agree:${p.id}:${w}">${esc(L.t(`ppl_at_agree_${w}`))}</button>`).join("")}</div>
      <label class="field"><span>${esc(L.t("ppl_at_agree_full_id_number"))}</span><input id="atFull" data-typed autocomplete="off" autocapitalize="characters" spellcheck="false" dir="ltr"></label>
      <button type="button" class="ghost inline" data-act="at:agree:${p.id}:full_id_number">${esc(L.t("ppl_at_agree_typed"))}</button>${note}`);
  const step4 = atCard("enrolment", L.t("ppl_at_enrolment"), !meansOf(p.set).some((m) => m !== "idcn") ? `<p class="sub">${esc(L.t("ppl_at_no_enrolment"))}</p>`
    : `<div class="ph-row">${meansOf(p.set).filter((m) => m !== "idcn").map((m) => p.enrolled.includes(m) ? `<span role="status">${L.icon("ui-check")} ${esc(L.t(`ppl_means_${m}`))}</span>` : `<button type="button" class="ghost small" data-act="at:enrol:${p.id}:${m}" ${atOff(!p.agreed)}>${esc(L.t(`ppl_at_enrol_${m}`))}</button>`).join("")}</div>${note}`);
  const step5 = atCard("confirm_person", L.t("ppl_at_confirm"), p.confirmed ? `<p role="status">${L.icon("ui-check")} ${esc(L.t("ppl_at_confirmed"))}</p>` : `<button type="button" class="primary inline" data-act="at:confirm:${p.id}" ${atOff(!p.agreed || need.length > 0 || !L.mayManage)}>${esc(L.t("ppl_at_confirm"))}</button>`);
  const step6 = atCard("create_pin", L.t("ppl_at_create_pin"), p.pinState !== "none" ? `<p role="status">${L.icon("ui-check")} ${esc(L.t("ppl_at_pin_made"))}</p>` : `<button type="button" class="primary inline" data-act="at:createpin:${p.id}" ${atOff(!p.confirmed || !L.online || !L.mayManage)}>${esc(L.t("ppl_at_create_pin"))}</button><p class="sub">${esc(L.t("ppl_at_pin_note"))}</p>${atOffline(L)}`);
  const step7 = atCard("send_pin", L.t("ppl_at_send_pin"), `<div class="ph-row">${SEND_WAYS.map((w) => `<button type="button" class="ghost small" data-act="at:send:${p.id}:${w}" ${atOn(p.sent === w)} ${atOff(p.pinState !== "live" || !L.online || !L.mayManage)}>${esc(L.t(`ppl_at_way_${w}`))}</button>`).join("")}</div>
    ${p.sent ? `<p role="status">${atChip("sent", L)} ${esc(L.t("ppl_at_sent_by", { way: L.t(`ppl_at_way_${p.sent}`) }))}</p>` : ""}${d.note === "coming_soon" ? `<p class="info" role="status">${esc(L.t("coming_soon"))}</p>` : ""}
    <p class="sub">${esc(L.t("ppl_at_send_note"))}</p>${p.sent ? `<button type="button" class="primary inline" data-act="at:donenew">${esc(L.t("ppl_at_done"))}</button>` : ""}`);
  return step1 + step2 + step3 + step4 + step5 + step6 + step7;
}

/** Everyone, live: who is inside, how they checked in, the checker named, every backup and flag (app.lynkomni.com/attendance/check-ins). */
export function checkInsView(d: AttendDesk, L: AtLook): string {
  const rows = d.people.map((p) => { const r = d.recs.find((x) => x.id === p.rec);
    return `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(p.name)}</span><span class="sub">${esc(L.t(p.onLeave && p.state === "not_yet" ? "ppl_at_on_leave" : `ppl_state_${p.state}`))}${p.at ? ` · ${esc(L.clock(p.at))} · ${esc(L.t(`ppl_means_${p.means}`))}` : ""}${r?.checker ? ` · ${esc(L.t("ppl_at_checker_was", { name: d.person(r.checker)?.name ?? "" }))}` : ""}</span>
      ${r && (r.backup || r.flags.length) ? `<span class="sub">${r.backup ? atTag(L.t(`ppl_at_backup_${r.backup}`), "warn") : ""} ${atFlags(r.flags, L)}</span>` : ""}</span></div></li>`; }).join("");
  const flagged = d.recs.filter((r) => r.flags.length || r.backup);
  const absent = d.people.filter((p) => p.state !== "in" && p.id !== d.me);
  const open = d.recs.filter((r) => r.outAt === null && r.flags.includes("no_check_out"));
  return atCard("live_view", `${L.t("ppl_today")} · ${L.t("ppl_in_count", { n: d.inCount(), of: d.people.length })}`, `<ul class="list">${rows}</ul>`)
    + atCard("flags", L.t("ppl_at_please_check"), flagged.length ? `<ul class="list">${flagged.map((r) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(d.person(r.person)?.name ?? "")} · ${esc(L.clock(r.inAt))}</span><span class="sub">${r.backup ? atTag(L.t(`ppl_at_backup_${r.backup}`), "warn") : ""} ${atFlags(r.flags, L)}</span></span></div></li>`).join("")}</ul><p class="sub">${esc(L.t("ppl_at_flag_note"))}</p>` : `<p class="sub">${esc(L.t("ppl_at_no_flags"))}</p>`)
    + atCard("hand_check_in", L.t("ppl_at_by_hand"), `<p class="sub">${esc(L.t("ppl_at_hand_note"))}</p><ul class="list">${absent.map((p) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(p.name)}</span></span></div><div class="ph-row">${AT_HAND_REASONS.map((r) => `<button type="button" class="ghost small" data-act="at:hand:${p.id}:${r}" ${atOff(!L.mayManage)}>${esc(L.t(`ppl_at_hand_${r}`))}</button>`).join("")}</div></li>`).join("")}</ul>`)
    + atCard("corrections", L.t("ppl_at_no_check_out"), open.length ? `<ul class="list">${open.map((r) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(d.person(r.person)?.name ?? "")}</span><span class="sub">${esc(L.t("ppl_at_in_at", { time: L.clock(r.inAt) }))}</span></span><button type="button" class="primary small" data-act="at:fixout:${r.id}" ${atOff(!L.mayManage)}>${esc(L.t("ppl_at_fix_time"))}</button></div></li>`).join("")}</ul>` : `<p class="sub">${esc(L.t("ppl_at_none_open"))}</p>`)
    + `<div class="ph-row"><button type="button" class="ghost small" data-act="at:late">${esc(L.t("ppl_at_sandbox_late"))}</button></div><p class="sub">${esc(L.t("ppl_at_correct_note"))}</p>`;
}

/** Visitors and the fire list (app.lynkomni.com/attendance/visitors). No photo is ever taken. */
export function visitorsView(d: AttendDesk, L: AtLook): string {
  const v = d.vdraft, name = (id: string): string => d.person(id)?.name ?? d.visitors.find((x) => x.id === id)?.name ?? "";
  const list = d.visitors.length ? d.visitors.map((x) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(x.name)}</span><span class="sub">${esc(L.t("ppl_at_visiting", { name: name(x.host) }))} · ${esc(L.t(`ppl_at_vstate_${x.state}`))}${x.allowedBy ? ` · ${esc(L.t("ppl_at_allowed_by_manager"))}` : ""}</span></span>
      ${x.state === "inside" ? `<button type="button" class="ghost small" data-act="at:vout:${x.id}">${esc(L.t("ppl_at_sign_out"))}</button>` : ""}</div></li>`).join("") : `<li><p class="sub">${esc(L.t("ppl_at_no_visitors"))}</p></li>`;
  const waiting = d.visitors.filter((x) => x.state === "waiting_for_manager");
  return atCard("visitor_list", L.t("ppl_at_visitors"), `<ul class="list">${list}</ul>`)
    + atCard("sign_in_visitor", L.t("ppl_at_sign_in_visitor"), `<label class="field"><span>${esc(L.t("ppl_at_name"))}</span><input id="atV" data-in="at:vname" value="${esc(v.name)}" autocomplete="off" placeholder="${esc(L.t("hint_name"))}" aria-label="${esc(L.t("ppl_at_name"))}"></label>
      <label class="field"><span>${esc(L.t("ppl_at_host"))}</span><select id="atH" data-in="at:vhost"><option value="">${esc(L.t("ppl_at_host"))}</option>${d.people.map((p) => `<option value="${p.id}"${v.host === p.id ? " selected" : ""}>${esc(p.name)}</option>`).join("")}</select></label>
      <div class="ph-choices small">${(["official", "work", "none"] as const).map((x) => `<button type="button" class="ph-choice" data-act="at:vdoc:${x}" ${atOn(v.doc === x)}><strong>${esc(L.t(`ppl_at_doc_${x}`))}</strong></button>`).join("")}</div>
      <button type="button" class="ph-toggle" data-act="at:vguard" ${atOn(v.guardian)}><span>${esc(L.t("ppl_at_guardian"))}</span></button>
      <button type="button" class="primary inline" data-act="at:vin">${esc(L.t(v.doc === "none" ? "ppl_at_ask_manager" : "ppl_at_sign_in_visitor"))}</button>${d.note === "ppl_at_visitor_needed" ? `<p class="info" role="alert">${esc(L.t(d.note))}</p>` : ""}<p class="sub">${esc(L.t("ppl_at_visitor_note"))}</p>`)
    + atCard("ask_manager", L.t("ppl_at_ask_manager"), waiting.length ? `<ul class="list">${waiting.map((x) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(x.name)}</span><span class="sub">${esc(L.t("ppl_at_doc_none"))}</span></span></div><div class="ph-row"><button type="button" class="primary small" data-act="at:vallow:${x.id}" ${atOff(!L.mayManage)}>${esc(L.t("ppl_at_allow"))}</button><button type="button" class="ghost small" data-act="at:vrefuse:${x.id}" ${atOff(!L.mayManage)}>${esc(L.t("ppl_at_refuse"))}</button></div></li>`).join("")}</ul>` : `<p class="sub">${esc(L.t("ppl_at_none_waiting"))}</p>`)
    + atCard("fire_list", L.t("ppl_at_fire_list"), d.fire ? `<p role="status"><strong>${esc(L.t("ppl_at_fire_count", { n: d.fire.staff.length + d.fire.visitors.length }))}</strong></p><ul class="list">${[...d.fire.staff, ...d.fire.visitors].map((id) => `<li><label class="ph-tick"><input type="checkbox"><span>${esc(name(id))}</span></label></li>`).join("")}</ul><button type="button" class="ghost inline" data-act="at:fireclose">${esc(L.t("close"))}</button>`
      : `<button type="button" class="primary inline" data-act="at:fire">${esc(L.t("ppl_at_fire_open"))}</button><p class="sub">${esc(L.t("ppl_at_fire_note"))}</p>`);
}

export function checkersView(d: AttendDesk, L: AtLook): string {
  return atCard("checker_list", L.t("ppl_checkers"), `<p class="sub">${esc(L.t("ppl_at_checker_note"))}</p><ul class="list">${d.people.map((p) => `<li><button type="button" class="ph-toggle" data-act="at:checker:${p.id}" ${atOn(d.checkers.includes(p.id))} ${atOff(!L.mayManage)}><span>${esc(p.name)}</span><strong>${esc(L.t(d.checkers.includes(p.id) ? "ppl_on" : "ppl_off"))}</strong></button></li>`).join("")}</ul>`);
}
export function shiftsView(d: AttendDesk, L: AtLook): string {
  const opts: [string, string][] = [["960", "16:00"], ["1020", "17:00"], ["1080", "18:00"], ["none", L.t("ppl_at_no_shift")]];
  return atCard("shift_times", L.t("ppl_at_shift_end"), `<div class="ph-choices small">${opts.map(([v, label]) => `<button type="button" class="ph-choice" data-act="at:shift:${v}" ${atOn(String(d.shiftEnd ?? "none") === v)} ${atOff(!L.mayManage)}><strong dir="ltr">${esc(label)}</strong></button>`).join("")}</div>`)
    + atCard("missed_check_out", L.t("ppl_at_no_check_out"), `<p>${esc(L.t("ppl_at_no_check_out_rule"))}</p>`);
}
export function leaveView(d: AttendDesk, L: AtLook): string {
  return atCard("leave_list", L.t("ppl_at_leave"), `<p class="sub">${esc(L.t("ppl_at_leave_note"))}</p><ul class="list">${d.people.map((p) => `<li><button type="button" class="ph-toggle" data-act="at:leave:${p.id}" ${atOn(p.onLeave)} ${atOff(!L.mayManage)}><span>${esc(p.name)}</span><strong>${esc(L.t(p.onLeave ? "ppl_at_on_leave" : "ppl_at_at_work"))}</strong></button></li>`).join("")}</ul>`);
}
export function eventsView(d: AttendDesk, L: AtLook): string {
  return atCard("event_list", L.t("ppl_at_events"), `<button type="button" class="primary inline" data-act="at:event:new" ${atOff(!L.mayManage)}>${esc(L.t("ppl_at_add_event"))}</button>${d.note === "ppl_at_limit" ? `<p class="info" role="alert">${esc(L.t("ppl_at_event_limit"))}</p>` : ""}
      <ul class="list">${d.events.length ? d.events.map((e, i) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(L.t("ppl_at_sample_course"))} ${i + 1}</span><span class="sub">${esc(L.t("ppl_at_own_group"))}</span></span></div></li>`).join("") : `<li><p class="sub">${esc(L.t("ppl_at_no_events"))}</p></li>`}</ul>`)
    + atCard("certificates", L.t("ppl_at_certificates"), d.tier === "free" || d.tier === "plus" ? `<p class="sub">${esc(L.t("ppl_at_cert_tier"))}</p>` : `<p>${esc(L.t("ppl_at_cert_note"))}</p>${d.events.map((e) => `<p>${esc(L.t("ppl_at_cert_code"))}: <strong dir="ltr">${esc(e.cert)}</strong></p>`).join("")}`);
}
export function devicesView(d: AttendDesk, L: AtLook): string {
  const p = d.plan();
  return atCard("door_devices", L.t("ppl_at_door_devices"), `<ul class="list">${d.devices.map((x) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(x.name)}</span><span class="sub">${esc(L.t(x.locked ? "ppl_at_locked" : "ppl_at_added"))}</span></span></div></li>`).join("")}</ul>
      <p class="sub">${esc(L.t("ppl_at_only_added"))}${p.door_devices !== null ? ` ${esc(L.t("ppl_at_device_limit", { n: p.door_devices }))}` : ""}</p>`)
    + atCard("device_lock", L.t("ppl_at_lost_device"), `<ul class="list">${d.devices.map((x) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(x.name)}</span></span><button type="button" class="ghost small" data-act="at:lockdev:${x.id}" ${atOff(x.locked || !L.mayManage)}>${esc(L.t(x.locked ? "ppl_at_locked" : "ppl_at_lock"))}</button></div></li>`).join("")}</ul><p class="sub">${esc(L.t("ppl_at_lock_note"))}</p>`)
    + atCard("clock_guard", L.t("ppl_at_clock_guard"), `<button type="button" class="ph-toggle" data-act="at:clock" ${atOn(d.clockWrong)}><span>${esc(L.t("ppl_at_sandbox_clock"))}</span><strong>${esc(L.t(d.clockWrong ? "ppl_on" : "ppl_off"))}</strong></button><p class="sub">${esc(L.t("ppl_at_clock_note"))}</p>
      ${(["face", "finger"] as const).map((m) => `<button type="button" class="ph-toggle" data-act="at:reader:${m}" ${atOn(d.readers[m])}><span>${esc(L.t(`ppl_at_reader_${m}`))}</span><strong>${esc(L.t(d.readers[m] ? "ppl_on" : "ppl_off"))}</strong></button>`).join("")}
      <button type="button" class="ph-toggle" data-act="at:allow" ${atOn(d.allow.face && d.allow.finger)}><span>${esc(L.t("ppl_at_country_allows"))}</span><strong>${esc(L.t(d.allow.face && d.allow.finger ? "ppl_on" : "ppl_off"))}</strong></button>`);
}
export function reportsView(d: AttendDesk, L: AtLook): string {
  const b = d.bill(), p = d.plan();
  const mins = (id: string): number => d.recs.filter((r) => r.person === id && r.outAt !== null).reduce((n, r) => n + Math.round(((r.outAt ?? 0) - r.inAt) / 60000), 0);
  return atCard("hours_report", L.t("ppl_at_hours"), `<ul class="list">${d.people.map((x) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(x.name)}</span></span><strong>${esc(L.t("ppl_at_h_m", { h: Math.floor(mins(x.id) / 60), m: mins(x.id) % 60 }))}</strong></div></li>`).join("")}</ul>`)
    + atCard("manager_history", L.t("ppl_at_history"), d.history.length ? `<ul class="list">${d.history.slice(0, 12).map((h) => `<li><div class="rowbtn static"><span class="main"><span class="nm">${esc(L.t(`ppl_at_did_${AT_DID.includes(h.what.replace(/^pin_sent_.*/, "pin_sent")) ? h.what.replace(/^pin_sent_.*/, "pin_sent") : "other"}`))}</span><span class="sub">${esc(L.clock(h.at))}${h.person && d.person(h.person) ? ` · ${esc(d.person(h.person)!.name)}` : ""}</span></span></div></li>`).join("")}</ul>` : `<p class="sub">${esc(L.t("ppl_at_no_history"))}</p>`)
    + atCard("billing_count", L.t("ppl_at_billing"), `<p>${esc(L.t("ppl_at_bill_line", { people: b.people, included: b.included }))}</p><p><strong>${esc(L.money(b.cents))}</strong> ${atTag(L.t("ppl_at_placeholder"))}</p>
      <p class="sub">${esc(p.extra_person_cents === null ? L.t("ppl_at_bill_free", { n: p.people_included }) : L.t("ppl_at_bill_extra", { price: L.money(p.extra_person_cents) }))}</p><p class="sub">${esc(L.t("ppl_at_bill_note"))}</p>`);
}

/** The door on any device: Check-in or Check-out, the PIN (dots only), then the person's set; in the person's own language after
 *  the PIN. Works by touch, by the device's number keys, or by the on-screen keys with arrows and OK. */
export function atDoor(d: AttendDesk, L: AtLook, speak?: { t: (lang: string) => T; dir: (lang: string) => "ltr" | "rtl"; code: (lang: string) => string }, keys = false): string {
  const D = d.door, m = D.member;
  const tl = m && speak ? speak.t(m.lang) : L.t, attrs = m && speak ? ` lang="${esc(speak.code(m.lang))}" dir="${speak.dir(m.lang)}"` : "";
  const pad = keys ? `<div class="ph-keys" dir="ltr">${[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => `<button type="button" data-act="at:digit:${n}">${n}</button>`).join("")}<button type="button" data-act="at:doorback" aria-label="${esc(L.t("ppl_at_delete_key"))}">${L.icon("ui-arrow-left")}</button><button type="button" data-act="at:digit:0">0</button><span></span></div>` : "";
  if (D.step === "pin") return `<div class="ph-door" data-item="door_screen"><div class="ph-choices small">${(["in", "out"] as const).map((x) => `<button type="button" class="ph-choice" data-act="at:dir:${x}" ${atOn(D.dir === x)}><strong>${esc(L.t(x === "in" ? "ppl_check_in" : "ppl_at_check_out"))}</strong></button>`).join("")}</div>
    <h2>${esc(L.t("ppl_door_pin"))}</h2><div class="dots" role="img" aria-label="${esc(L.t("ppl_digits_typed", { n: D.pin.length, of: PIN_LENGTH }))}">${Array.from({ length: PIN_LENGTH }, (_, i) => `<i class="${i < D.pin.length ? "on" : ""}"></i>`).join("")}</div>
    ${D.note ? `<p class="note" role="alert">${esc(L.t(D.note))}</p>` : ""}${pad}<p class="sub">${esc(L.t("ppl_door_offline"))}</p></div>`;
  if (D.step === "done" && D.out && m) {
    const ok = D.out.result === "in";
    const msg = ok ? tl(D.dir === "in" ? "ppl_door_welcome" : "ppl_door_bye", { name: m.name, time: L.clock(m.at) }) : tl(D.out.result === "pin_blocked" ? "ppl_door_blocked" : "ppl_door_see_manager");
    return `<div class="ph-door done" data-item="door_screen"${attrs}>${L.icon(ok ? "ui-check" : "ui-warning", "bigcheck")}<h2 role="status">${esc(msg)}</h2>${ok && D.dir === "out" ? `<p>${esc(tl("ppl_at_today_time", { h: Math.floor(D.minutes / 60), m: D.minutes % 60 }))}</p>` : ""}
      ${ok && D.out.backup_from ? `<p class="sub">${esc(tl(`ppl_at_backup_${D.out.backup_from}`))}</p>` : ""}${ok ? m.flags.map((f) => `<p class="sub">${esc(tl(`ppl_flag_${f}`))}</p>`).join("") : ""}
      <button type="button" class="primary" data-act="at:doornext">${esc(L.t("ppl_next_person"))}</button></div>`;
  }
  const means = D.out?.means, moved = D.out?.backup_from ? `<p class="note" role="status">${esc(tl(`ppl_at_backup_${D.out.backup_from}`))}</p>` : "";
  if (means === "idcn" && m) return `<div class="ph-door" data-item="door_screen"${attrs}>${moved}${idcnEntry({ typed: D.typed.length, checkers: d.doorCheckers(), me: m.name, chosen: D.checker, triesLeft: d.idcnTriesLeft() }, tl)}${pad}
    <button type="button" class="primary" data-act="at:idcn" ${atOff(D.typed.length !== IDCN_LENGTH || !D.checker)}>${esc(tl(D.dir === "in" ? "ppl_check_in" : "ppl_at_check_out"))}</button></div>`;
  return `<div class="ph-door" data-item="door_screen"${attrs}>${moved}<h2>${esc(tl(means === "face" ? "ppl_door_face" : "ppl_door_finger"))}</h2>${L.icon(means === "face" ? "ui-user" : "ui-lock", "bigcheck")}
    <p class="sub">${esc(L.t("ppl_reader_sandbox"))}</p><div class="ph-row" dir="ltr"><button type="button" class="primary" data-act="at:readerok">${esc(L.t("ppl_reader_ok"))}</button>
    <button type="button" class="ghost" data-act="at:readerfail">${esc(L.t("ppl_reader_fail"))}</button><button type="button" class="ghost" data-act="at:readerbroken">${esc(L.t("ppl_reader_broken"))}</button></div></div>`;
}
/** "Was this you?" as the person sees it on their own phone, with Not me. */
export function wasThisYou(d: AttendDesk, L: AtLook): string {
  const m = d.messages[0], p = m && d.person(m.person);
  if (!m || !p) return "";
  return `<div class="card ph-card" data-item="was_this_you" role="group" aria-label="${esc(L.t("ppl_at_wty_title"))}"><h2>${esc(L.t("ppl_at_wty_title"))} ${atTag(L.t("ppl_at_persons_phone"))}</h2>
    <p>${esc(L.t(m.dir === "in" ? "ppl_at_wty_in" : "ppl_at_wty_out", { time: L.clock(m.at) }))}</p><button type="button" class="ghost inline" data-act="at:notme:${m.rec}">${esc(L.t("ppl_at_not_me"))}</button></div>`;
}
