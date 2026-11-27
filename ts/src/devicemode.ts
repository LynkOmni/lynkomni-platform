/** Touch and non-touch versions of every device (DEVICE 48.17.14). A device emulator is the device itself, so its interface comes
 *  from its registered device record (catalog/devices.v1.json, confirmed by LynkDriver from the attached hardware) through the one
 *  decision function, with the owner's Change view on top. In a non-touch version the screen ignores taps: everything is reached
 *  with the device's own keys (arrows or a navigation pad, OK, Back), focus is always visible and moves to the nearest control in
 *  the direction pressed (mirrored right-to-left). */
import { chooseInterface } from "./interfaces.js";
import type { Choice, DeviceRegister, Version } from "./interfaces.js";

/** Inputs that point straight at the screen (catalog/devices.v1.json inputs). */
const POINTING = ["touch", "stylus", "mouse", "trackpad"];

export class DeviceMode {
  version: Version;
  override: string | null = null;
  constructor(private reg: DeviceRegister, public device: string, version?: Version) {
    const d = reg.devices.find((x) => x.id === device);
    if (!d) throw new Error(`unknown device ${device}`);
    this.version = version ?? (d.touch ? "touch" : "non_touch");
  }
  /** The versions this device is made in (touch, non-touch or both). */
  versions(): Version[] { const d = this.reg.devices.find((x) => x.id === this.device)!; return (["touch", "non_touch"] as Version[]).filter((v) => d[v] !== null); }
  choice(): Choice { return chooseInterface(this.reg, { registered: { device: this.device, version: this.version }, override: this.override }); }
  /** Whether the screen takes direct pointing: a finger, a stylus, a mouse or a trackpad. Only a buttons-only screen (arrows, keypad,
   *  remote) ignores taps; a computer with a mouse is clicked like any computer (owner report 2026-11-19). */
  touch(): boolean { const i = this.reg.interfaces[this.choice().interface]?.inputs ?? []; return POINTING.some((x) => i.includes(x)); }
  /** Marks the screen root: type scale (device class), focus rules (interface) and whether taps count. */
  apply(root: HTMLElement): void {
    const c = this.choice();
    root.dataset["deviceClass"] = c.class; root.dataset["interface"] = c.interface; root.dataset["touch"] = this.touch() ? "yes" : "no";
  }
  /** The testing control in the emulator panel: which hardware version is registered (real devices are told by LynkDriver). */
  control(label: string, words: Record<Version, string>, only?: Record<Version, string>): string {
    const v = this.versions();
    if (v.length < 2) return only && v[0] ? `<p class="vonly" data-ctl="version-only">${only[v[0]]}</p>` : "";   // said plainly, never left out
    return `<label class="row"><span>${label}</span> <select data-ctl="version">${v.map((x) => `<option value="${x}"${x === this.version ? " selected" : ""}>${words[x]}</option>`).join("")}</select></label>`;
  }
  /** A computer's version without touch is a mouse and keyboard, not buttons. */
  pointer(): boolean { const d = this.reg.devices.find((x) => x.id === this.device); return /pointer/.test(String(d?.non_touch ?? "")); }
}

export type Dir = "up" | "down" | "left" | "right";
/** The control on the screen that last had focus. A pad key pressed with a finger or a mouse must never take the focus away from
 *  the screen: the pad refuses focus (see wireDevice), and this is the fallback when a browser moves it anyway. */
let lastOnScreen: HTMLElement | null = null;
function current(root: HTMLElement): HTMLElement | null {
  const a = document.activeElement as HTMLElement | null;
  if (a && root.contains(a)) return a;
  return lastOnScreen && root.contains(lastOnScreen) ? lastOnScreen : null;
}
const FOCUSABLE = "button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), [tabindex='0']";

/** Moves focus to the nearest visible control in a direction (spatial navigation for arrows, remotes and pads). The first press
 *  with nothing focused lands on the first control. Returns true when focus moved. */
export function moveFocus(root: HTMLElement, dir: Dir, rtl = false): boolean {
  // Only controls a person can reach: never one taken out of the order (tabindex -1) or hidden from people (aria-hidden), such as
  // the native list under LynkOmni's own drop-down, which sits exactly under its button.
  const items = Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && !el.closest("[hidden]") && el.getAttribute("tabindex") !== "-1" && !el.closest("[aria-hidden='true']"); });
  if (!items.length) return false;
  const cur = current(root);
  if (!cur || !items.includes(cur)) { items[0]!.focus(); return true; }
  const d: Dir = rtl && (dir === "left" || dir === "right") ? (dir === "left" ? "right" : "left") : dir;
  const a = cur.getBoundingClientRect(), ax = a.left + a.width / 2, ay = a.top + a.height / 2;
  let best: HTMLElement | null = null, score = Infinity;
  for (const el of items) {
    if (el === cur) continue;
    const b = el.getBoundingClientRect(), bx = b.left + b.width / 2, by = b.top + b.height / 2, dx = bx - ax, dy = by - ay;
    const along = d === "down" ? dy : d === "up" ? -dy : d === "right" ? dx : -dx;
    const across = d === "down" || d === "up" ? Math.abs(dx) : Math.abs(dy);
    if (along <= 1) continue;
    const s = along + across * 2;
    if (s < score) { score = s; best = el; }
  }
  if (!best) {                                                       // nothing further that way: wrap in reading order
    const i = items.indexOf(cur), next = d === "down" || d === "right" ? items[(i + 1) % items.length] : items[(i - 1 + items.length) % items.length];
    best = next ?? null;
  }
  if (!best) return false;
  best.focus(); best.scrollIntoView({ block: "nearest", inline: "nearest" });
  return true;
}

/** The keys of a non-touch device mapped to one meaning each (catalog/devices.v1.json keys): arrows move, OK confirms the focused
 *  control, Back cancels. Returns the meaning, or null for other keys. */
export function keyMeaning(key: string): Dir | "ok" | "back" | null {
  return key === "ArrowUp" ? "up" : key === "ArrowDown" ? "down" : key === "ArrowLeft" ? "left" : key === "ArrowRight" ? "right"
    : key === "Enter" || key === " " ? "ok" : key === "Escape" || key === "Backspace" ? "back" : null;
}

/** The navigation pad on a non-touch device body: four arrows, OK and Back, each a 44 px key with its name. */
export function navPad(words: { up: string; down: string; left: string; right: string; ok: string; back: string }, icon: (id: string) => string): string {
  const k = (act: string, label: string, inner: string, cls = "") => `<button type="button" class="padkey${cls}" data-act="pad:${act}" aria-label="${label}">${inner}</button>`;
  return `<div class="navpad" role="group" aria-label="${words.ok} / ${words.back}">${k("up", words.up, "▲", " up")}${k("left", words.left, "◀", " left")}${k("ok", words.ok, words.ok, " ok")}${k("right", words.right, "▶", " right")}${k("down", words.down, "▼", " down")}${k("back", words.back, icon("ui-undo"), " back")}</div>`;
}

/** After the screen redraws, puts the focus back on the same control; when that control is gone or can no longer be used (for
 *  example a kitchen line just marked ready), on the first control instead, so the focus never leaves the screen. */
function refocus(root: HTMLElement, act: string | undefined, rtl: boolean): void {
  let again = act ? root.querySelector<HTMLElement>(`[data-act="${CSS.escape(act)}"]`) : null;
  // A drop-down's name is on its list (select), and the person was on the drop-down's button beside it.
  if (again?.matches("select.lo-src")) again = again.parentElement?.querySelector<HTMLElement>(".lo-selbtn") ?? again;
  if (again) again.focus();
  if (!root.contains(document.activeElement)) { lastOnScreen = null; moveFocus(root, "down", rtl); }
}

/** The name a control is found by again after a redraw: its data-act, or its list's for a drop-down button. */
function actOf(el: HTMLElement): string | undefined {
  return el.dataset["act"] ?? el.closest(".lo-sel")?.querySelector<HTMLElement>("select")?.dataset["act"];
}

/** The open list of LynkOmni's drop-down (ts/src/chooser.ts) that holds or belongs to the focused control, if any. */
function openList(cur: HTMLElement | null): HTMLElement | null {
  const wrap = cur?.closest<HTMLElement>(".lo-sel");
  return wrap?.querySelector<HTMLElement>(".lo-pop") ? wrap : null;
}

/** Runs a pad key or a physical key on a non-touch screen: moves focus, clicks the focused control on OK, or calls back(). While a
 *  drop-down's list is open, the keys work inside it: up and down move through the choices, OK picks one and Back closes the list,
 *  as on a real kiosk or TV. */
export function padPress(root: HTMLElement, what: Dir | "ok" | "back", back: () => void, rtl = false): void {
  const cur0 = current(root);
  if (openList(cur0)) {
    const key = what === "up" ? "ArrowUp" : what === "down" ? "ArrowDown" : what === "ok" ? "Enter" : what === "back" ? "Escape" : null;
    if (key) cur0!.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
    return;
  }
  if (what === "back") { back(); return; }
  if (what === "ok") {
    const cur = current(root);
    if (!cur) { moveFocus(root, "down", rtl); return; }
    const act = actOf(cur);
    cur.click();                                                      // the screen redraws: focus returns to the same control, or the first one
    refocus(root, act, rtl);
    return;
  }
  moveFocus(root, what, rtl);
}

/** Everything a device emulator needs for its two versions, in one place: the panel control, the pad under the screen, physical
 *  keys and pad taps on a non-touch screen, and the marks on the screen root. */
export interface DeviceWiring {
  /** The panel's testing control (empty when the device comes in one version only). */
  control(): string;
  /** Call from the panel's change listener: true when it was the version control. */
  change(el: HTMLElement): boolean;
  /** Call from draw(): marks the root and shows or hides the navigation pad. */
  draw(root: HTMLElement): void;
  /** Call first in the click handler: true when a pad key was pressed. */
  act(a: string): boolean;
  /** Call first in the keydown handler: true when a non-touch screen used the key. */
  key(e: KeyboardEvent): boolean;
}
export function wireDevice(mode: DeviceMode, o: { t: (k: string) => string; icon: (id: string) => string; screen: () => HTMLElement | null; pad: () => HTMLElement | null; back: () => void; redraw: () => void; rtl: () => boolean }): DeviceWiring {
  const press = (w: Dir | "ok" | "back"): void => { const r = o.screen(); if (r) padPress(r, w, o.back, o.rtl()); };
  if (typeof document !== "undefined") {
    // Remember the focused control on the screen, and keep a tapped or clicked pad key from taking the focus.
    document.addEventListener("focusin", (e) => { const r = o.screen(), t = e.target as HTMLElement | null; if (r && t && r.contains(t)) lastOnScreen = t; });
    document.addEventListener("mousedown", (e) => { if ((e.target as HTMLElement | null)?.closest?.(".padkey")) e.preventDefault(); });
  }
  return {
    control: () => deviceChoiceHtml(mode, o.t),
    change: (el) => {
      if (el.dataset["ctl"] !== "version") return false;
      const v = (el as HTMLSelectElement).value;
      if (v === "touch" || v === "non_touch") mode.version = v;
      o.redraw(); return true;
    },
    draw: (root) => {
      mode.apply(root);
      const pad = o.pad();
      if (pad) pad.innerHTML = mode.touch() ? "" : navPad({ up: o.t("key_up"), down: o.t("key_down"), left: o.t("key_left"), right: o.t("key_right"), ok: o.t("key_ok"), back: o.t("key_back") }, o.icon);
      // A redraw replaces the screen's controls: on a buttons-only screen the focus goes back to the same control, or the first.
      const had = lastOnScreen;
      if (!mode.touch() && had) queueMicrotask(() => {
        if (document.contains(had) || (document.activeElement && document.activeElement !== document.body)) return;
        refocus(root, actOf(had), o.rtl());
      });
    },
    act: (a) => {
      const m = /^pad:(up|down|left|right|ok|back)$/.exec(a);
      if (!m) return false;
      press(m[1] as Dir | "ok" | "back"); return true;
    },
    key: (e) => {
      if (mode.touch()) return false;
      if (!e.isTrusted) return false;                              // a key the screen sent itself (padPress inside an open list)
      if (e.defaultPrevented) return true;                         // the focused control used it already (an open drop-down list)
      if ((e.target as HTMLElement | null)?.closest?.(".panel, aside")) return false;     // the emulator's own panel keeps its keys
      const w = keyMeaning(e.key);
      if (!w) return false;
      e.preventDefault(); press(w); return true;
    },
  };
}

/** Every device emulator's panel says how the device is used (owner, 2026-11-26): the choice where the real device can be either a
 *  touch screen or buttons (a mouse and keyboard on a computer), and a plain line where it can only be one, so nobody looks for a
 *  choice that the device does not have. */
export function deviceChoiceHtml(mode: DeviceMode, t: (k: string) => string): string {
  return mode.control(t("version_testing"), { touch: t("version_touch"), non_touch: mode.pointer() ? t("version_pointer") : t("version_non_touch") },
    { touch: t("version_only_touch"), non_touch: t("version_only_non_touch") });
}
