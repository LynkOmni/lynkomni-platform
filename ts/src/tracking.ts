/** LynkOmni tracking (owner request 9 November 2026): the TypeScript port of services/tracking.py. One engine follows every
 *  tracked thing (deliveries, orders, payments, agent requests, repairs, invoices, registrations and the rest of
 *  catalog/tracking.v1.json) from the event log. A step is reached only by the event that proves it; the chip uses only the five
 *  states; customers see customer steps and never an id, address, name or position; live progress is a share in steps of 5%.
 *  Shared vectors: contract/vectors/tracking.v1.json (tools/tracking_vectors.py). */
export type TrackState = "queued" | "sent" | "accepted" | "confirmed" | "failed";
export type Audience = "merchant" | "customer" | "person" | "staff";
export interface Rule { event?: string; state?: string; child?: string; step?: string; when?: Record<string, readonly unknown[]>; all_of?: { list: string; from: string; unique: string } }
export interface Step { id: string; state: TrackState; customer: boolean; terminal?: boolean; optional?: boolean; on: readonly Rule[] }
export interface Kind {
  id: string; record: string | null; key: string; family: string; ui_section: number; live_progress?: boolean;
  parent?: { kind: string; event: string; field: string }; eta?: readonly { event: string; field: string }[];
  aliases?: readonly { event: string; from: string; to: string }[]; viewers: Record<string, string>; steps: readonly Step[];
}
/** The register as the apps carry it (ts/src/tracking.generated.ts): the prose, rules and planned list stay in catalog/tracking.v1.json. */
export interface Register { version: number; description?: string; states: readonly string[]; rules?: readonly string[]; kinds: readonly Kind[]; planned?: readonly { id: string; record: string; ui_section: number; note: string }[] }
export interface TrackEvent { type: string; payload: Record<string, unknown>; at?: number | string | null }
export interface StepView { id: string; label: string; state: TrackState; done: boolean; current: boolean; at: string | null }
export interface View {
  kind: string; label: string; state: TrackState; step: string | null; ended: boolean; steps: StepView[]; eta: string | null; late: boolean;
  progress: number | null; record?: string; children: unknown[]; parent?: { kind: string; record: string }; public_id?: string;
}
export interface Change { kind: string; record: string; step: string; state: TrackState; customer: boolean; owner: string | null; at: number | null }
interface Rec { owner: string | null; reached: Map<number, number | null>; order: number[]; seen: Map<string, Record<string, unknown>>; eta: number | null; parent: [string, string] | null; children: [string, string][]; progress: number | null }

export const STATES: readonly TrackState[] = ["queued", "sent", "accepted", "confirmed", "failed"];

export function epoch(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  if (typeof v === "number") return v;
  return Math.floor(Date.parse(String(v).slice(0, 19) + "Z") / 1000);
}
export const iso = (ts: number | null): string | null => (ts === null ? null : new Date(ts * 1000).toISOString().slice(0, 19) + "Z");

export class Tracking {
  readonly kinds = new Map<string, Kind>();
  private byEvent = new Map<string, [string, number, Rule][]>();
  private byState = new Map<string, number[]>();
  private byChild = new Map<string, [string, number][]>();
  readonly recs = new Map<string, Rec>();
  private alias = new Map<string, string>();
  private lines = new Map<string, Set<unknown>>();
  readonly subs = new Map<string, { channel: string; lang: string }>();

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
    if (!r) { r = { owner, reached: new Map(), order: [], seen: new Map(), eta: null, parent: null, children: [], progress: null }; this.recs.set(this.key(kind, record), r); }
    else if (owner && !r.owner) r.owner = owner;
    return r;
  }
  private kind(id: string): Kind { const k = this.kinds.get(id); if (!k) throw new Error(`unknown tracking kind ${id}`); return k; }
  private endedRec(kind: string, r: Rec): boolean { const steps = this.kind(kind).steps; return [...r.reached.keys()].some((i) => !!steps[i]!.terminal); }
  private reach(kind: string, record: string, i: number, at: number | null, changes: Change[]): void {
    const r = this.recs.get(this.key(kind, record))!;
    if (r.reached.has(i) || this.endedRec(kind, r)) return;
    r.reached.set(i, at); r.order.push(i);
    const step = this.kind(kind).steps[i]!;
    if (step.terminal) r.progress = null;
    changes.push({ kind, record, step: step.id, state: step.state, customer: !!step.customer, owner: r.owner, at });
    for (const [pk, pi] of this.byChild.get(`${kind}|${step.id}`) ?? []) if (r.parent && r.parent[0] === pk) this.reach(pk, r.parent[1], pi, at, changes);
  }

  apply(event: TrackEvent, owner: string | null = null): Change[] {
    const etype = event.type, p = event.payload ?? {}, at = epoch(event.at ?? null), changes: Change[] = [];
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
      out.push({ id: st.id, label: `trk_${st.id}`, state: st.state, done, current: st.id === cur, at: iso(r.reached.get(i) ?? null) });
    });
    const eta = ended ? null : r.eta;
    const v: View = { kind, label: `trk_k_${kind}`, state: this.state(kind, record), step: cur, ended, steps: out, eta: iso(eta), late: eta !== null && now > eta && !ended,
      progress: k.live_progress && !ended ? r.progress : null, children: [] };
    if (audience !== "customer") {
      v.record = record;
      v.children = r.children.map(([ck, cr]) => ({ kind: ck, record: cr, state: this.state(ck, cr), step: this.current(ck, this.recs.get(this.key(ck, cr))!) }));
      if (r.parent) v.parent = { kind: r.parent[0], record: r.parent[1] };
    } else v.children = r.children.map(([ck, cr]) => this.view(ck, cr, "customer", now));
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
}

/** A percent for screens ("45%"), from a progress share. */
export const percent = (share: number | null): number | null => (share === null ? null : Math.round(share * 100));
