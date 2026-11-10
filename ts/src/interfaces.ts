/** The one decision function that picks the interface for a device (DEVICE, master blueprint 48.17). Port of
 *  core/interfaces.py; contract/vectors/interfaces.v1.json proves both choose the same interface for every combination of
 *  device facts. Order: Change view, the registered device record, what the device reports (never the browser's name), the
 *  safe default. A change is applied only at a safe moment (never during a payment, count or signature). */
export type Rule = "override" | "registered" | "reported" | "safe_default";
export type DeviceClass = "watch" | "phone" | "tablet" | "computer" | "tv" | "eink" | "voice";
export interface InterfaceSpec { class: DeviceClass; inputs: readonly string[]; note?: string }
export interface DeviceSpec { id: string; touch: string | null; non_touch: string | null; emulator: { touch: string | null; non_touch: string | null }; section: number; note?: string }
export interface DeviceRegister {
  classes: Record<string, { distance: string }>;
  safe_default: string; interfaces: Record<string, InterfaceSpec>; devices: readonly DeviceSpec[];
  keys: Record<string, { label_key: string; colour_token?: string; physical?: string }>; every_interface_accepts: readonly string[];
}
export type Version = "touch" | "non_touch";
export interface DeviceRef { device: string; version: Version }
export interface Facts {
  override?: DeviceRef | string | null; registered?: DeviceRef | null;
  os_class?: "phone" | "tablet" | "desktop" | "tv" | "watch" | "car" | "eink" | "speaker" | null;
  touch?: boolean; coarse?: boolean; fine?: boolean; hover?: boolean; keyboard?: boolean; remote?: boolean;
  width?: number; height?: number; moving?: boolean; last_input?: "touch" | "pen" | "mouse" | "keyboard" | "remote" | null; no_apps?: boolean;
}
export interface Choice { interface: string; class: DeviceClass; rule: Rule }

function ifaceFromDevice(reg: DeviceRegister, spec: DeviceRef | string | null | undefined): string | null {
  if (typeof spec === "string") return spec in reg.interfaces ? spec : null;
  if (!spec || typeof spec !== "object") return null;
  const d = reg.devices.find((x) => x.id === spec.device);
  if (!d || (spec.version !== "touch" && spec.version !== "non_touch")) return null;
  return d[spec.version];
}

function ifaceReported(f: Facts): string | null {
  const os = f.os_class ?? null, w = f.width ?? 0, touch = !!f.touch, fine = !!f.fine, last = f.last_input ?? null;
  if (os === "car") return "car.voice";
  if (os === "speaker") return "voice.only";
  if (os === "watch") return "watch.touch";
  if (os === "tv") return "tv.remote";
  if (os === "eink") return touch ? "eink.touch" : "eink.buttons";
  if (f.no_apps) return "phone.text";
  if (touch) {
    if ((os === "desktop" || w >= 1024) && (fine || f.keyboard)) return last === "mouse" || last === "keyboard" ? "computer.pointer" : "computer.touch";
    if (os === "phone" || (os === null && w > 0 && w < 600)) return "phone.touch";
    if (os === "tablet" || w >= 600) return "tablet.touch";
    return null;
  }
  if (fine && (f.hover || os === "desktop")) return "computer.pointer";
  if (f.remote && os === null && w >= 1024) return "tv.remote";              // a TV that does not say so: remote keys on a big screen
  if (f.keyboard && !fine && w > 0 && w < 600) return os === "phone" ? "phone.feature" : "phone.keypad";
  return null;
}

export function chooseInterface(reg: DeviceRegister, facts: Facts = {}): Choice {
  const steps: [Rule, () => string | null][] = [["override", () => ifaceFromDevice(reg, facts.override)], ["registered", () => ifaceFromDevice(reg, facts.registered)], ["reported", () => ifaceReported(facts)]];
  for (const [rule, pick] of steps) {
    const i = pick();
    if (i) return { interface: i, class: reg.interfaces[i]!.class, rule };
  }
  const s = reg.safe_default;
  return { interface: s, class: reg.interfaces[s]!.class, rule: "safe_default" };
}

export const safeToSwitch = (task: string | null): boolean => task !== "payment" && task !== "count" && task !== "signature";

/** What this browser reports about itself (capabilities only, never its name). Used by apps and emulators. */
export function browserFacts(win: { matchMedia(q: string): { matches: boolean }; innerWidth: number; innerHeight: number; navigator: { maxTouchPoints?: number } }): Facts {
  const m = (q: string): boolean => { try { return win.matchMedia(q).matches; } catch { return false; } };
  return {
    touch: (win.navigator.maxTouchPoints ?? 0) > 0 || m("(any-pointer: coarse)"),
    coarse: m("(pointer: coarse)"), fine: m("(any-pointer: fine)"), hover: m("(any-hover: hover)"),
    width: win.innerWidth, height: win.innerHeight,
  };
}
