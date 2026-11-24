/** LynkOmni tracking (owner request 9 November 2026): the TypeScript port of services/tracking.py. One engine follows every
 *  tracked thing (deliveries, orders, payments, agent requests, repairs, invoices, registrations and the rest of
 *  catalog/tracking.v1.json) from the event log. A step is reached only by the event that proves it; the chip uses only the five
 *  states; customers see customer steps and never an id, address, name or position; live progress is a share in steps of 5%.
 *  Shared vectors: contract/vectors/tracking.v1.json (tools/tracking_vectors.py). */
export type TrackState = "queued" | "sent" | "accepted" | "confirmed" | "failed";
export type Audience = "merchant" | "customer" | "person" | "staff";
export interface Rule { event?: string; state?: string; child?: string; step?: string; when?: Record<string, readonly unknown[]>; all_of?: { list: string; from: string; unique: string } }
export interface Step { id: string; state: TrackState; customer: boolean; terminal?: boolean; optional?: boolean; again?: boolean; on: readonly Rule[] }
export interface ScanRule { event: string; proof?: readonly string[] }
export interface Kind {
  id: string; record: string | null; key: string; note?: string; family: string; ui_section: number | string; live_progress?: boolean;
  promise?: Record<string, number>; working_time?: boolean; waits_on_customer?: readonly string[]; scan?: Record<string, ScanRule>;
  checks?: Record<string, readonly string[]>; partner_status?: Record<string, Record<string, string>>; keep_days?: number;
  parent?: { kind: string; event: string; field: string }; eta?: readonly { event: string; field: string }[];
  aliases?: readonly { event: string; from: string; to: string }[]; viewers: Record<string, string>; steps: readonly Step[];
}
/** The register as the apps carry it (ts/src/tracking.generated.ts): the prose, rules and planned list stay in catalog/tracking.v1.json. */
export interface Engine { at_risk_bp?: number; stuck_factor?: number; keep_days?: number; extra_steps_max?: number; two_second_ms?: number }
export interface Register { version: number; description?: string; states: readonly string[]; rules?: readonly string[]; kinds: readonly Kind[]; engine?: Engine; planned?: readonly { id: string; record: string; ui_section: number; note: string }[] }
export interface TrackEvent { type: string; payload: Record<string, unknown>; at?: number | string | null; id?: string }
export interface StepView { id: string; label: string; state: TrackState; done: boolean; current: boolean; at: string | null }
export interface View {
  kind: string; label: string; state: TrackState; step: string | null; ended: boolean; steps: StepView[]; eta: string | null; late: boolean;
  progress: number | null; record?: string; children: unknown[]; parent?: { kind: string; record: string }; public_id?: string;
  extra?: { id: string; label: string; at: string | null }[]; risk?: Risk | null; clash?: string[]; practice?: boolean;
}
export type Risk = "on_time" | "at_risk" | "late";
/** Opening hours for working-time promises: minutes east of UTC and, per weekday (Monday = "0"), [open, close] in minutes after midnight. */
export interface Hours { offset_min?: number; days?: Record<string, readonly (readonly [number, number])[]> }
export interface Exception { kind: string; record: string; step: string; why: "clash" | "failed" | "stuck" | "late" | "at_risk" | "waiting_on_customer"; since: string | null }
export interface TowerRow { kind: string; record: string; step: string; state: TrackState; risk: Risk | null; since: string | null }
export interface Change { kind: string; record: string; step: string; state: TrackState; customer: boolean; owner: string | null; at: number | null }
interface Rec { owner: string | null; reached: Map<number, number | null>; order: number[]; seen: Map<string, Record<string, unknown>>; eta: number | null; parent: [string, string] | null; children: [string, string][]; progress: number | null;
  clash: { step: string; at: number | null }[]; extra: { id: string; label: string; customer: boolean; at: number | null }[]; practice: boolean; endedAt: number | null }

export const STATES: readonly TrackState[] = ["queued", "sent", "accepted", "confirmed", "failed"];

export function epoch(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  if (typeof v === "number") return v;
  return Math.floor(Date.parse(String(v).slice(0, 19) + "Z") / 1000);
}
export const isoAt = (ts: number | null): string | null => (ts === null ? null : new Date(ts * 1000).toISOString().slice(0, 19) + "Z");

export class Tracking {
  readonly kinds = new Map<string, Kind>();
  private byEvent = new Map<string, [string, number, Rule][]>();
  private byState = new Map<string, number[]>();
  private byChild = new Map<string, [string, number][]>();
  readonly recs = new Map<string, Rec>();
  private alias = new Map<string, string>();
  private lines = new Map<string, Set<unknown>>();
  readonly subs = new Map<string, { channel: string; lang: string }>();
  private applied = new Set<string>();
  readonly extraDefs = new Map<string, { id: string; label: string; customer: boolean }[]>();

  constructor(readonly reg: Register) {
    for (const k of reg.kinds) {
      this.kinds.set(k.id, k);
      k.steps.forEach((st, i) => {
        for (const rule of st.on) {
          if (rule.event) this.push(this.byEvent, rule.event, [k.id, i, rule]);
          else if (rule.state) this.push(this.byState, `${k.id}|${rule.state}`, i);
          else if (rule.child) this.push(this.byChild, `${rule.child}|${rule.step}`, [k.id, i]);
        }
      });
    }
  }
  private push<V>(m: Map<string, V[]>, key: string, v: V): void { const a = m.get(key); if (a) a.push(v); else m.set(key, [v]); }
  private key(kind: string, record: string): string { return `${kind}|${record}`; }
  private rec(kind: string, record: string, owner: string | null): Rec {
    let r = this.recs.get(this.key(kind, record));
    if (!r) { r = { owner, reached: new Map(), order: [], seen: new Map(), eta: null, parent: null, children: [], progress: null, clash: [], extra: [], practice: false, endedAt: null }; this.recs.set(this.key(kind, record), r); }
    else if (owner && !r.owner) r.owner = owner;
    return r;
  }
  private kind(id: string): Kind { const k = this.kinds.get(id); if (!k) throw new Error(`unknown tracking kind ${id}`); return k; }
  private endedRec(kind: string, r: Rec): boolean { const steps = this.kind(kind).steps; return [...r.reached.keys()].some((i) => !!steps[i]!.terminal); }
  private reach(kind: string, record: string, i: number, at: number | null, changes: Change[]): void {
    const r = this.recs.get(this.key(kind, record))!;
    const step = this.kind(kind).steps[i]!;
    if (this.endedRec(kind, r)) {
      const endI = r.order[r.order.length - 1]!, endAt = r.reached.get(endI) ?? null;
      if (step.terminal && i !== endI && !r.reached.has(i) && !r.clash.some((c) => c.step === step.id)) r.clash.push({ step: step.id, at });   // two endings: the earlier stands
      else if (!r.reached.has(i) && at !== null && endAt !== null && at < endAt && i < endI) { r.reached.set(i, at); r.order.splice(r.order.length - 1, 0, i); }
      return;
    }
    const curI = r.order.length ? r.order[r.order.length - 1]! : null;
    if (!r.reached.has(i) && curI !== null && i < curI && at !== null && (r.reached.get(curI) ?? null) !== null && at < r.reached.get(curI)! && !step.terminal) {
      r.reached.set(i, at); r.order.splice(r.order.length - 1, 0, i);   // an earlier step arriving late stays in the past
      return;
    }
    if (r.reached.has(i)) {   // a step counts once, unless the register says it can come again (a queue ticket waits again after Put back or Send to)
      if (!step.again || r.order[r.order.length - 1] === i) return;
      r.order.splice(r.order.indexOf(i), 1);
    }
    r.reached.set(i, at); r.order.push(i);
    if (step.terminal) { r.progress = null; r.endedAt = at; }
    changes.push({ kind, record, step: step.id, state: step.state, customer: !!step.customer, owner: r.owner, at });
    for (const [pk, pi] of this.byChild.get(`${kind}|${step.id}`) ?? []) if (r.parent && r.parent[0] === pk) this.reach(pk, r.parent[1], pi, at, changes);
  }

  apply(event: TrackEvent, owner: string | null = null): Change[] {
    const etype = event.type, p = event.payload ?? {}, at = epoch(event.at ?? null), changes: Change[] = [];
    if (event.id !== undefined) { if (this.applied.has(event.id)) return changes; this.applied.add(event.id); }   // the same event twice counts once
    if (etype === "TrackingStepMarked") return this.markExtra(p, at, owner);
    if (etype === "TrackingSubscribed" && typeof p["kind"] === "string" && this.kinds.has(p["kind"])) {
      this.subs.set(this.key(p["kind"], String(p["record"])), { channel: String(p["channel"]), lang: String(p["lang"] ?? "en") });
      return changes;
    }
    for (const k of this.reg.kinds) {
      for (const a of k.aliases ?? []) if (a.event === etype && a.from in p && a.to in p) this.alias.set(this.key(k.id, String(p[a.from])), String(p[a.to]));
      const par = k.parent;
      if (par && par.event === etype && k.key in p && p[par.field]) {
        const childId = String(p[k.key]), parentId = String(p[par.field]);
        const child = this.rec(k.id, childId, owner), parent = this.rec(par.kind, parentId, owner);
        child.parent = [par.kind, parentId];
        if (!parent.children.some(([ck, cr]) => ck === k.id && cr === childId)) parent.children.push([k.id, childId]);
      }
    }
    for (const [kind, i, rule] of this.byEvent.get(etype) ?? []) {
      const k = this.kind(kind);
      let record: string | undefined = p[k.key] === undefined || p[k.key] === null ? undefined : String(p[k.key]);
      if (record === undefined) for (const a of k.aliases ?? []) if (a.from in p) { record = this.alias.get(this.key(kind, String(p[a.from]))); break; }
      if (record === undefined) continue;
      const r = this.rec(kind, record, owner);
      if (p["practice"] === true) r.practice = true;
      const etaRule = (k.eta ?? []).find((x) => x.event === etype && x.field in p);
      if (etaRule) r.eta = epoch(p[etaRule.field]);
      if (rule.when && !Object.entries(rule.when).every(([f, vals]) => vals.includes(p[f]))) continue;
      if (!r.seen.has(etype)) r.seen.set(etype, p);
      if (rule.all_of) {
        const sk = `${kind}|${record}|${etype}`; let seen = this.lines.get(sk); if (!seen) { seen = new Set(); this.lines.set(sk, seen); }
        seen.add(p[rule.all_of.unique]);
        const source = r.seen.get(rule.all_of.from);
        const list = source ? source[rule.all_of.list] : undefined;
        if (!source || seen.size < (Array.isArray(list) ? list.length : 0)) continue;
      }
      this.reach(kind, record, i, at, changes);
    }
    return changes;
  }

  feedState(kind: string, record: string, state: string, at: number | string, owner: string | null = null): Change[] {
    if (!this.kinds.has(kind)) throw new Error(`unknown tracking kind ${kind}`);
    this.rec(kind, record, owner);
    const changes: Change[] = [];
    for (const i of this.byState.get(`${kind}|${state}`) ?? []) this.reach(kind, record, i, epoch(at), changes);
    return changes;
  }
  setProgress(kind: string, record: string, share: number, eta: number | string | null = null): boolean {
    const k = this.kind(kind), r = this.recs.get(this.key(kind, record));
    if (!k.live_progress || !r || this.endedRec(kind, r) || this.current(kind, r) !== "on_the_way") return false;
    const s = Math.max(0, Math.min(1, share));
    r.progress = (Math.floor(s * 20 + 0.5) * 5) / 100;
    if (eta !== null) r.eta = epoch(eta);
    return true;
  }
  private current(kind: string, r: Rec): string | null { return r.order.length ? this.kind(kind).steps[r.order[r.order.length - 1]!]!.id : null; }
  state(kind: string, record: string): TrackState {
    const r = this.recs.get(this.key(kind, record));
    return r && r.order.length ? this.kind(kind).steps[r.order[r.order.length - 1]!]!.state : "queued";
  }
  ended(kind: string, record: string): boolean { const r = this.recs.get(this.key(kind, record)); return !!r && this.endedRec(kind, r); }

  view(kind: string, record: string, audience: Audience = "merchant", now = Date.now() / 1000, publicId?: string): View | null {
    const k = this.kind(kind), r = this.recs.get(this.key(kind, record));
    if (!r) return null;
    const steps = k.steps, ended = this.endedRec(kind, r);
    const kids = new Set(r.children.map(([c]) => c));
    const eligible = (st: Step): boolean => st.on.every((rule) => rule.child === undefined || kids.has(rule.child));
    const order = steps.map((_, i) => i).sort((a, b) => {
      const ka = steps[a]!.on.some((rule) => rule.child !== undefined && kids.has(rule.child)) ? 0 : 1;
      const kb = steps[b]!.on.some((rule) => rule.child !== undefined && kids.has(rule.child)) ? 0 : 1;
      return ka - kb || a - b;
    });
    const expectedEnd = ended ? null : order.find((i) => !!steps[i]!.terminal && !steps[i]!.optional && steps[i]!.state !== "failed" && eligible(steps[i]!)) ?? null;
    const cur = this.current(kind, r);
    const out: StepView[] = [];
    steps.forEach((st, i) => {
      if (audience === "customer" && !st.customer) return;
      const done = r.reached.has(i);
      if (st.terminal) { if (!(done || i === expectedEnd)) return; }
      else if (!done && (ended || st.optional || st.state === "failed" || !eligible(st))) return;
      out.push({ id: st.id, label: `trk_${st.id}`, state: st.state, done, current: st.id === cur, at: isoAt(r.reached.get(i) ?? null) });
    });
    const eta = ended ? null : r.eta;
    const v: View = { kind, label: `trk_k_${kind}`, state: this.state(kind, record), step: cur, ended, steps: out, eta: isoAt(eta), late: eta !== null && now > eta && !ended,
      progress: k.live_progress && !ended ? r.progress : null, children: [] };
    if (audience !== "customer") {
      v.record = record;
      v.children = r.children.map(([ck, cr]) => ({ kind: ck, record: cr, state: this.state(ck, cr), step: this.current(ck, this.recs.get(this.key(ck, cr))!) }));
      if (r.parent) v.parent = { kind: r.parent[0], record: r.parent[1] };
    } else v.children = r.children.map(([ck, cr]) => this.view(ck, cr, "customer", now));
    const extra = r.extra.filter((x) => audience !== "customer" || x.customer);
    if (extra.length) v.extra = [...extra].sort((a, b) => (a.at ?? 0) - (b.at ?? 0) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)).map((x) => ({ id: x.id, label: x.label, at: isoAt(x.at) }));
    if (audience !== "customer") {
      v.risk = this.risk(kind, record, now);
      if (r.clash.length) v.clash = r.clash.map((c) => c.step);
      if (r.practice) v.practice = true;
    }
    if (publicId) v.public_id = publicId;
    return v;
  }
  active(owner: string | null = null, now = Date.now() / 1000): View[] {
    const out: [number, string, string][] = [];
    for (const [key, r] of this.recs) {
      const [kind, record] = [key.slice(0, key.indexOf("|")), key.slice(key.indexOf("|") + 1)];
      if ((owner === null || r.owner === owner) && r.order.length && !this.endedRec(kind, r)) out.push([Math.max(...[...r.reached.values()].map((x) => x ?? 0)), kind, record]);
    }
    out.sort((a, b) => b[0] - a[0] || (a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0) || (a[2] < b[2] ? -1 : a[2] > b[2] ? 1 : 0));
    return out.map(([, kind, record]) => this.view(kind, record, "merchant", now)!);
  }
  late(now: number, owner: string | null = null): View[] { return this.active(owner, now).filter((v) => v.late); }

  // ---- the section 4 engine upgrade (TRACKING UPDATE 72.3), the same as services/tracking.py
  setExtraSteps(owner: string, kind: string, steps: readonly { id: string; label: string; customer?: boolean }[]): void {
    const k = this.kind(kind);
    if (steps.length > (this.reg.engine?.extra_steps_max ?? 5)) throw new Error("too many extra steps");
    const ids = steps.map((x) => x.id);
    if (new Set(ids).size !== ids.length || ids.some((i) => !/^[a-z][a-z0-9_]{1,30}$/.test(i) || k.steps.some((st) => st.id === i))) throw new Error("an extra step needs its own id");
    this.extraDefs.set(this.key(owner, kind), steps.map((x) => ({ id: x.id, label: String(x.label).slice(0, 60), customer: !!x.customer })));
  }
  private markExtra(p: Record<string, unknown>, at: number | null, owner: string | null): Change[] {
    const kind = String(p["kind"] ?? ""), record = String(p["record"] ?? ""), xid = String(p["extra_step"] ?? "");
    const r = this.recs.get(this.key(kind, record));
    if (!r || this.endedRec(kind, r)) return [];
    const d = (this.extraDefs.get(this.key(r.owner ?? owner ?? "", kind)) ?? []).find((x) => x.id === xid);
    if (!d || r.extra.some((x) => x.id === xid)) return [];
    r.extra.push({ id: xid, label: d.label, customer: d.customer, at });
    return [];
  }
  private spent(k: Kind, entered: number, now: number, hours?: Hours): number {
    return k.working_time && hours ? workingMinutes(entered, now, hours) : Math.max(0, Math.floor(Math.trunc(now - entered) / 60));
  }
  risk(kind: string, record: string, now: number, hours?: Hours): Risk | null {
    const k = this.kind(kind), r = this.recs.get(this.key(kind, record));
    if (!r || !r.order.length || this.endedRec(kind, r)) return null;
    const i = r.order[r.order.length - 1]!, target = k.promise?.[k.steps[i]!.id], entered = r.reached.get(i) ?? null;
    if (target === undefined || entered === null) return null;
    const spent = this.spent(k, entered, now, hours);
    if (spent >= target) return "late";
    return spent * 10000 >= target * (this.reg.engine?.at_risk_bp ?? 8000) ? "at_risk" : "on_time";
  }
  private stuck(kind: string, r: Rec, now: number, hours?: Hours): boolean {
    const k = this.kind(kind), i = r.order[r.order.length - 1]!, target = k.promise?.[k.steps[i]!.id], entered = r.reached.get(i) ?? null;
    if (target === undefined || entered === null) return false;
    return this.spent(k, entered, now, hours) >= target * (this.reg.engine?.stuck_factor ?? 2);
  }
  private split(key: string): [string, string] { const at = key.indexOf("|"); return [key.slice(0, at), key.slice(at + 1)]; }
  exceptions(owner: string, now: number, hours?: Hours): Exception[] {
    const order: Exception["why"][] = ["clash", "failed", "stuck", "late", "at_risk", "waiting_on_customer"];
    const out: Exception[] = [];
    for (const [key, r] of this.recs) {
      if (r.owner !== owner || r.practice || !r.order.length) continue;
      const [kind, record] = this.split(key), k = this.kind(kind), cur = k.steps[r.order[r.order.length - 1]!]!;
      let why: Exception["why"] | null = null;
      if (r.clash.length) why = "clash";
      else if (this.endedRec(kind, r)) why = cur.state === "failed" ? "failed" : null;
      else if (this.stuck(kind, r, now, hours)) why = "stuck";
      else { const rk = this.risk(kind, record, now, hours); why = rk === "late" || rk === "at_risk" ? rk : (k.waits_on_customer ?? []).includes(cur.id) ? "waiting_on_customer" : null; }
      if (why) out.push({ kind, record, step: cur.id, why, since: isoAt(r.reached.get(r.order[r.order.length - 1]!) ?? null) });
    }
    const cmp = (a: string, b: string): number => (a < b ? -1 : a > b ? 1 : 0);
    return out.sort((a, b) => order.indexOf(a.why) - order.indexOf(b.why) || cmp(a.since ?? "", b.since ?? "") || cmp(a.kind, b.kind) || cmp(a.record, b.record));
  }
  tower(owner: string, now: number, kind?: string, step?: string, hours?: Hours): { rows: TowerRow[]; counts: Record<Risk, number>; total: number } {
    const rank = (x: Risk | null): number => (x === "late" ? 0 : x === "at_risk" ? 1 : x === "on_time" ? 2 : 3);
    const rows: TowerRow[] = [];
    for (const [key, r] of this.recs) {
      const [kid, record] = this.split(key);
      if (r.owner !== owner || r.practice || !r.order.length || this.endedRec(kid, r)) continue;
      const cur = this.kind(kid).steps[r.order[r.order.length - 1]!]!;
      if ((kind && kid !== kind) || (step && cur.id !== step)) continue;
      rows.push({ kind: kid, record, step: cur.id, state: cur.state, risk: this.risk(kid, record, now, hours), since: isoAt(r.reached.get(r.order[r.order.length - 1]!) ?? null) });
    }
    const cmp = (a: string, b: string): number => (a < b ? -1 : a > b ? 1 : 0);
    rows.sort((a, b) => rank(a.risk) - rank(b.risk) || cmp(a.since ?? "", b.since ?? "") || cmp(a.kind, b.kind) || cmp(a.record, b.record));
    const counts = { late: 0, at_risk: 0, on_time: 0 } as Record<Risk, number>;
    for (const x of rows) if (x.risk) counts[x.risk] += 1;
    return { rows, counts, total: rows.length };
  }
  partnerEvent(kind: string, partner: string, code: string): string | null { return this.kind(kind).partner_status?.[partner]?.[code] ?? null; }
  scan(kind: string, record: string, step: string, proof?: string | null, clientEvents?: ReadonlySet<string>): { ok: boolean; event: string | null; why: string[] } {
    const k = this.kind(kind), r = this.recs.get(this.key(kind, record)), why: string[] = [];
    const rule = k.scan?.[step];
    if (!rule) return { ok: false, event: null, why: ["not_scannable"] };
    if (clientEvents && !clientEvents.has(rule.event)) why.push("cloud_only");
    if (r && this.endedRec(kind, r)) why.push("ended");
    if (rule.proof && rule.proof.length && !(proof && rule.proof.includes(proof))) why.push("needs_proof");
    for (const c of k.checks?.[step] ?? []) if (c.startsWith("after:")) {
      const need = k.steps.findIndex((st) => st.id === c.slice(6));
      if (!r || !r.reached.has(need)) why.push(c);
    }
    return { ok: why.length === 0, event: why.length ? null : rule.event, why };
  }
  prune(now: number): number {
    let n = 0;
    for (const [key, r] of [...this.recs]) {
      const [kind] = this.split(key);
      if (r.endedAt !== null && this.endedRec(kind, r) && now > r.endedAt + 86400 * (this.kind(kind).keep_days ?? this.reg.engine?.keep_days ?? 400)) { this.recs.delete(key); n += 1; }
    }
    return n;
  }
}

/** A promise from real capacity: base minutes plus whole rounds of the waiting work (rounded up) times one round's minutes. */
export function promiseMinutes(base: number, load: number, capacity: number, perRound: number): number {
  if (capacity < 1 || base < 0 || load < 0 || perRound < 0) throw new Error("capacity at least 1, nothing below zero");
  return base + Math.ceil(load / capacity) * perRound;
}
/** Whole minutes between two times inside opening hours (Monday = "0"), the same as services/tracking.py working_minutes. */
export function workingMinutes(start: number, end: number, hours?: Hours | null): number {
  if (!hours) return Math.max(0, Math.floor((end - start) / 60));
  if (end <= start) return 0;
  const off = Math.trunc(hours.offset_min ?? 0) * 60;
  let total = 0;
  for (let day = Math.floor((start + off) / 86400); day <= Math.floor((end + off) / 86400); day++) {
    const base = day * 86400 - off;
    for (const [o, c] of hours.days?.[String((day + 3) % 7)] ?? []) {
      const a = Math.max(start, base + o * 60), b = Math.min(end, base + c * 60);
      if (b > a) total += Math.floor((b - a) / 60);
    }
  }
  return total;
}

/** A percent for screens ("45%"), from a progress share. */
export const percent = (share: number | null): number | null => (share === null ? null : Math.round(share * 100));
