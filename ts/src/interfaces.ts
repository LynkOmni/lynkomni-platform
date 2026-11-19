/** The one decision function that picks the interface for a device (DEVICE, master blueprint 48.17). Port of
 *  core/interfaces.py; contract/vectors/interfaces.v1.json proves both choose the same interface for every combination of
 *  device facts. Order: Change view, the registered device record, what the device reports (never the browser's name), the
 *  safe default. A change is applied only at a safe moment (never during a payment, count or signature). */
export type Rule = "override" | "registered" | "reported" | "safe_default";
export type DeviceClass = "watch" | "phone" | "tablet" | "computer" | "tv" | "eink" | "voice";
export interface InterfaceSpec { class: DeviceClass; inputs: readonly string[]; note?: string }
/** lynk_name: the ecosystem device name (LynkMobile, LynkTab, LynkPC, LynkPOS, LynkKiosk, LynkDScreen); hardware without one keeps its plain name. */
export interface DeviceSpec { id: string; touch: string | null; non_touch: string | null; emulator: { touch: string | null; non_touch: string | null }; section: number; note?: string; lynk_name?: string }
export interface DeviceRegister {
  classes: Record<string, { distance: string }>;
  safe_default: string; interfaces: Record<string, InterfaceSpec>; devices: readonly DeviceSpec[];
  keys: Record<string, { label_key: string; colour_token?: string; physical?: string }>; every_interface_accepts: readonly string[];
  shapes: Shapes;
}
/** The TURN UPDATE numbers (master blueprint 76; catalog/devices.v1.json shapes). */
export interface Shapes {
  lockable: readonly string[]; buttons_only: readonly string[]; small_phone_below_px: number; short_below_px: number;
  phone_two_columns_from_px: number; tablet_from_px: number; computer_from_px: number; wide_from_px: number; max_line_ch: number;
  turn: { keep: readonly string[]; never: readonly string[]; announce_once: boolean; keep_step: readonly string[] };
  [more: string]: unknown;
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

export interface ShapeFacts { interface?: string | null; width?: number; height?: number; posture?: "flat" | "half_open" | null; device?: string | null; lock?: "upright" | "sideways" | null }
export interface Layout {
  orientation: "upright" | "sideways"; locked: boolean;
  nav: "bottom_bar" | "side_rail" | "rail" | "two_level" | "soft_keys" | "glance" | "board" | "voice";
  tabs: number; columns: number; header: "normal" | "small" | "shrinks"; helper: "none" | "slide_in" | "open";
  main_button: "bottom" | "top_end"; split: "none" | "fold"; max_line_ch: number;
}

/** The layout for a screen's shape (TURN UPDATE, 76). Port of core/interfaces.py layout(); the shared vectors prove both agree.
 *  A lock is obeyed only on a lockable fixed device; a person's own phone follows its own rotation lock (its reported size). */
export function layoutFor(reg: DeviceRegister, f: ShapeFacts = {}): Layout {
  const s = reg.shapes;
  const iface = f.interface && f.interface in reg.interfaces ? f.interface : reg.safe_default;
  let w = Math.trunc(f.width ?? 0), h = Math.trunc(f.height ?? 0);
  const locked = (f.lock === "upright" || f.lock === "sideways") && !!f.device && s.lockable.includes(f.device);
  if (locked && (f.lock === "sideways") !== (w > h)) [w, h] = [h, w];
  const orientation = w > h ? "sideways" : "upright";
  const out: Layout = { orientation, locked, nav: "bottom_bar", tabs: 0, columns: 1, header: "normal", helper: "none", main_button: "bottom", split: "none", max_line_ch: s.max_line_ch };
  let cls: string = reg.interfaces[iface]!.class;
  if (s.buttons_only.includes(iface)) return { ...out, nav: "soft_keys" };
  if (cls === "voice") return { ...out, nav: "voice" };
  if (cls === "watch") return { ...out, nav: "glance" };
  if (cls === "tv") return { ...out, nav: "board", columns: w >= s.wide_from_px ? 3 : 2 };
  if (!["phone", "tablet", "computer"].includes(cls) || iface === "universal")
    cls = w >= s.computer_from_px ? "computer" : Math.min(w, h) >= s.tablet_from_px ? "tablet" : "phone";
  if (cls === "phone") {
    if (orientation === "upright") Object.assign(out, { nav: "bottom_bar", tabs: w < s.small_phone_below_px ? 4 : 5 });
    else Object.assign(out, { nav: "side_rail", header: "small", columns: w >= s.phone_two_columns_from_px ? 2 : 1 });
  } else if (cls === "tablet") {
    Object.assign(out, { nav: "rail", columns: orientation === "sideways" ? 2 : 1, helper: orientation === "sideways" ? "open" : "slide_in" });
  } else {
    Object.assign(out, { nav: "two_level", columns: w >= s.wide_from_px ? 3 : 2, helper: "open", main_button: "top_end" });
  }
  if (h > 0 && h < s.short_below_px && out.header === "normal") out.header = "shrinks";
  if (f.posture === "half_open") out.split = "fold";
  return out;
}
