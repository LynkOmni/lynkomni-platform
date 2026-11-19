// The Emulator Panel's rules (EMULATOR UPDATE, master blueprint section 70; build section 3A): the TypeScript port of
// core/emulators.py. Slots, counting, the check before assigning, hardware ways, key tones, the delivery menu, the five states and
// screen fit. The shared vectors in contract/vectors/emulators.v1.json decide when the two disagree.
import { CAPACITY, code } from "./queue.js";

export type Limit = number | null | "own_units";
export interface EmulatorInfo { id: string; service: string; counted: boolean; shared_with: string | null; touch: boolean; user: string; planned: boolean; customer_facing: boolean; hardware: string[]; devices: string[]; min_short_side_px: number; outputs: string[] }
export interface EmulatorRegister {
  emulators: EmulatorInfo[]; names: Record<string, string>; slots: Record<string, Record<string, Limit>>;
  /** One more staff device a month per family on Plus and Pro, the day pass, and the plan prices (all from services/billing.py). */
  extra_cents: Record<string, number>; day_pass_cents: number; day_pass_max_days: number; prices: Record<string, { tiers: string[]; cents: number[] }>;
  code_minutes: number; reapprove_days: number; downgrade_grace_days: number; artwork_min_px: number;
  hardware_ways: Record<string, string[]>; os_ways: Record<string, string[]>;
  /** The shared tone set from the design tokens (design/tokens.v1.json sounds). */
  sounds: { volume_gain: Record<string, number>; tones: Record<string, [number, number][]>; vibrate: Record<string, number[]>;
    /** Each number key's own telephone keypad pair (Hz), played together for keypad_ms (owner, 19 November 2026). */
    keypad?: Record<string, [number, number]>; keypad_ms?: number };
}
export interface Connection { device: string; emulator: string; connected?: boolean; practice?: boolean }
export const EM_STATES = ["queued", "sent", "accepted", "confirmed", "failed"] as const;
export const VOLUMES = ["low", "medium", "high"] as const;

const find = (r: EmulatorRegister, id: string): EmulatorInfo => {
  const e = r.emulators.find((x) => x.id === id);
  if (!e) throw new Error(`no such emulator: ${id}`);
  return e;
};

/** The family whose plan a connected emulator counts against, or null when it is free (customer-facing). */
export function countsFor(r: EmulatorRegister, id: string): string | null {
  const e = find(r, id);
  return e.counted ? e.shared_with ?? e.service : null;
}

/** Distinct devices with a connected, counted emulator of the family (a shared till counts once; practice never counts). */
export function inUse(r: EmulatorRegister, family: string, conns: readonly Connection[]): number {
  const devices = new Set<string>();
  for (const c of conns) if (c.connected && !c.practice && countsFor(r, c.emulator) === family) devices.add(c.device);
  return devices.size;
}

export function mayConnect(r: EmulatorRegister, limit: Limit, family: string, conns: readonly Connection[], add: Connection, extra = 0): [boolean, string | null] {
  const fam = countsFor(r, add.emulator);
  if (fam === null || add.practice || limit === null || limit === "own_units" || fam !== family) return [true, null];
  return inUse(r, family, [...conns, { ...add, connected: true }]) <= limit + extra ? [true, null] : [false, "plan_limit"];
}

export const codeValid = (r: EmulatorRegister, issued: number, now: number, used = false): boolean => !used && now - issued >= 0 && now - issued <= r.code_minutes * 60;
export const newCode = (n: number): string => code(n % CAPACITY);

export interface Caps { short_side?: number; touch?: boolean; keys?: boolean; camera?: boolean; speaker?: boolean; vibration?: boolean; os?: string; hardware?: string[]; device_print?: boolean; print_through?: boolean; nearby?: boolean }
export interface RunCheck { ok: boolean; refused: string | null; missing: { need: string; way: string }[] }
/** The check before assigning: refused only when the device cannot run the emulator at all, with the way round for the rest. */
export function canRun(r: EmulatorRegister, id: string, caps: Caps): RunCheck {
  const e = find(r, id);
  if ((caps.short_side ?? 0) < e.min_short_side_px) return { ok: false, refused: "screen_too_small", missing: [] };
  if (!caps.touch && !caps.keys) return { ok: false, refused: "no_way_to_use", missing: [] };
  const missing: { need: string; way: string }[] = [];
  if (!e.touch && caps.touch && !caps.keys) missing.push({ need: "remote_or_keys", way: "use_remote_or_keyboard" });
  const hw = new Set(caps.hardware ?? []);
  for (const need of e.outputs) {
    if (need === "camera_or_scanner" && !caps.camera && !hw.has("scanner")) missing.push({ need, way: "connect_a_scanner" });
    if (need === "speaker" && !caps.speaker) missing.push({ need, way: "use_a_device_with_sound" });
  }
  return { ok: true, refused: null, missing };
}

export function connectWays(r: EmulatorRegister, kind: string, os: string): string[] {
  const allowed = r.os_ways[os] ?? r.os_ways["other"] ?? [];
  return (r.hardware_ways[kind] ?? []).filter((w) => allowed.includes(w));
}
export function hardwareAdvice(r: EmulatorRegister, kind: string, os: string): { ways: string[]; fallback: string | null } {
  const ways = connectWays(r, kind, os);
  return ways.length ? { ways, fallback: null } : { ways: [], fallback: "through_another_device" };
}

export interface ToneSetting { tones?: boolean; vibration?: boolean; volume?: string; user_may_change?: boolean; pin_same_tone?: boolean }
export interface Tones { tones: boolean; vibration: boolean; volume: string; pin_tones: "same" | "per_key" }
/** Key tones and press vibration: the manager's setting, the user's choice where allowed; off in silent mode and quiet hours. */
export function tones(manager: ToneSetting, user: ToneSetting | null = null, customerFacing = false, silent = false, quietHours = false, vibrates = true): Tones {
  const s = { tones: manager.tones ?? true, vibration: manager.vibration ?? true, volume: manager.volume ?? "medium" };
  if (user && (manager.user_may_change ?? true) && !customerFacing) {
    if (user.tones !== undefined && user.tones !== null) s.tones = user.tones;
    if (user.vibration !== undefined && user.vibration !== null) s.vibration = user.vibration;
    if (user.volume !== undefined && user.volume !== null) s.volume = user.volume;
  }
  if (!(VOLUMES as readonly string[]).includes(s.volume)) s.volume = "medium";
  if (silent || quietHours) s.tones = false;
  if (!vibrates) s.vibration = false;
  return { tones: Boolean(s.tones), vibration: Boolean(s.vibration), volume: s.volume, pin_tones: manager.pin_same_tone ? "same" : "per_key" };
}

export interface Way { way: string; state: "now" | "queued" }
/** The delivery menu: only what works on this device now, in a fixed order; offline, messages wait as "queued". */
export function deliveryWays(caps: Caps, online: boolean, printerReady: boolean, customerKnown: boolean, contactGiven: boolean): Way[] {
  const out: Way[] = [];
  const later = online ? "now" : "queued";
  if (printerReady || caps.device_print || caps.print_through) out.push({ way: "print", state: "now" });
  out.push({ way: "qr", state: "now" });
  if (customerKnown) out.push({ way: "account", state: later }, { way: "lynkchat", state: later });
  if (contactGiven) out.push({ way: "message", state: later });
  if (caps.nearby) out.push({ way: "nearby", state: "now" });
  out.push({ way: "file", state: "now" });
  return out;
}

const STEP_STATE: Record<string, (typeof EM_STATES)[number]> = {
  made_offline: "queued", offered: "sent", accepted: "accepted", connected: "confirmed", denied: "failed", expired: "failed", disconnect_sent: "sent", disconnected: "confirmed",
};
export function requestState(step: string): (typeof EM_STATES)[number] {
  const s = STEP_STATE[step];
  if (!s) throw new Error(`no such step: ${step}`);
  return s;
}
export const reapprovalDue = (r: EmulatorRegister, lastSeenDay: number, today: number): boolean => today - lastSeenDay >= r.reapprove_days;

export function downgrade(r: EmulatorRegister, limit: Limit, family: string, conns: readonly Connection[]): { to_disconnect: number; grace_days: number } {
  if (limit === null || limit === "own_units") return { to_disconnect: 0, grace_days: 0 };
  const over = Math.max(0, inUse(r, family, conns) - limit);
  return { to_disconnect: over, grace_days: over ? r.downgrade_grace_days : 0 };
}

/** Python's round(): halves go to the even neighbour, so both languages fit a screen to the same pixel. */
export function roundHalfEven(x: number): number {
  const f = Math.floor(x), d = x - f;
  if (d > 0.5) return f + 1;
  if (d < 0.5) return f;
  return f % 2 === 0 ? f : f + 1;
}
export interface Fit { scale_pct: number; width: number; height: number; spare_x: number; spare_y: number; artwork: "sides" | "top_bottom" | "none" }
/** Fits an emulator's screen into a device's without stretching (one scale, 0.75 to 1.5), the spare space filled by artwork. */
export function fitScreen(r: EmulatorRegister, screenW: number, screenH: number, designW: number, designH: number): Fit {
  const scale = Math.max(0.75, Math.min(1.5, Math.min(screenW / designW, screenH / designH)));
  const width = roundHalfEven(designW * scale), height = roundHalfEven(designH * scale);
  const spare_x = Math.max(0, screenW - width), spare_y = Math.max(0, screenH - height);
  const artwork = spare_x >= 2 * r.artwork_min_px ? "sides" : spare_y >= 2 * r.artwork_min_px ? "top_bottom" : "none";
  return { scale_pct: roundHalfEven(scale * 100), width, height, spare_x, spare_y, artwork };
}

export const slots = (r: EmulatorRegister, family: string, tier: string): Limit => r.slots[family]?.[tier] ?? null;

/** The next tier when it costs less a month than this tier with these extra devices (shown, never applied by itself), else null. */
export function cheaperTier(r: EmulatorRegister, family: string, tier: string, extras: number): string | null {
  const p = r.prices[family], cents = r.extra_cents[family];
  if (!p || !extras || cents === undefined) return null;
  const i = p.tiers.indexOf(tier);
  if (i < 0 || i + 1 >= p.tiers.length) return null;
  const next = p.tiers[i + 1]!, now = (p.cents[i] ?? 0) + extras * cents, nxt = p.cents[i + 1] ?? 0;
  const ns = slots(r, family, next), cs = slots(r, family, tier);
  const fits = ns === null || (typeof ns === "number" && typeof cs === "number" && ns >= cs + extras);
  return fits && nxt <= now ? next : null;
}
