/** The device side of the Emulator Panel (EMULATOR UPDATE, master blueprint 70.4 to 70.10; build section 3A): what every emulator
 *  shows about its connection, on every device that runs one. The connect request with Accept or Deny; "Add to home screen" after
 *  Accept; the plain disconnected message with the Connect request button; Mark as lost and re-approval; practice mode clearly
 *  marked; key tones and press vibration with the device's settings; the hardware helper; the delivery menu; and the service's
 *  artwork in spare space. The rules are ts/src/emulators.ts (the port of core/emulators.py); the tones are the design tokens.
 *
 *  The device only asks: it writes EmulatorRequestAnswered, EmulatorConnectAsked, EmulatorSettingsChanged and DeviceHealthReported
 *  (contract v7). Connected, disconnected, lost, swapped and approved again are written by the cloud alone, so the screen shows
 *  them only when the cloud says so (here, the emulator's controls play the cloud). The five user states only. Every choice is a
 *  real button, so the kit works by touch and by arrows, OK and Back alike. */
import { loadPrefs, savePrefs } from "./soundprefs.js";
import type { Volume } from "./soundprefs.js";
import { esc } from "./shell.js";
import type { Icon, T } from "./shell.js";
import { newId } from "./emulator.js";
import { canRun, deliveryWays, fitScreen, hardwareAdvice, tones } from "./emulators.js";
import type { Caps, EmulatorRegister, Tones, ToneSetting, Way } from "./emulators.js";
import { PRIVATE_ENTRY, playSound, soundForAct } from "./keytones.js";
import { PageWait, wireBusy } from "./placeholder.js";
import type { Sound } from "./keytones.js";

export type Link = "connected" | "request" | "disconnected" | "asked" | "lost" | "reapproval";
export const LINKS: readonly Link[] = ["connected", "request", "disconnected", "asked", "lost", "reapproval"];
export type Emit = (type: string, payload: Record<string, unknown>, origin?: "device" | "server") => void;
type St = "queued" | "sent" | "accepted" | "confirmed" | "failed";

export interface KitLook { t: T; icon: Icon; online: boolean; busy: boolean }
export interface KitOptions {
  /** The register entry this device runs (catalog/emulators.v1.json), its device name and what the device can do. */
  emulator: string; service: string; deviceName: string; caps: Caps; os: string;
  /** Customer-facing screens follow the manager's tone setting; staff screens let the user change it where allowed. */
  customerFacing: boolean;
  /** The kinds of hardware this emulator may use (register "hardware"). */
  hardware: string[];
}

/** The tone and vibration for one press, from the design tokens; silent where the browser has no sound or vibration. */
export function play(reg: EmulatorRegister, kind: Sound, s: Tones): void { playSound(reg.sounds, kind, s); }

/** The device side of a panel emulator. The waiting state (first open, skeletons, Updating, Retry) comes from PageWait (83). */
export class EmKit extends PageWait {
  link: Link = "connected";
  practice = false;
  homeAdded = false;
  /** The connect request on screen: which business, which emulator, who sent it (word keys, so the request follows the screen's
   *  language; never a code in an event). */
  request: { assignment: string; business: string; sentBy: string; state: St } | null = null;
  askState: St | null = null;
  /** The manager's default and the user's own choice where allowed (70.6). */
  manager: ToneSetting = { tones: true, vibration: true, volume: "medium", user_may_change: true, pin_same_tone: false };
  /** The signed-in person's own choice: their account's Sounds and vibration, remembered and followed here (catalog/sounds.v1.json). */
  user: ToneSetting = (({ tones, vibration, volume }) => ({ tones, vibration, volume }))(loadPrefs());
  silent = false;
  quietHours = false;
  sheet: "" | "settings" | "hardware" | "delivery" = "";
  hwKind = "";
  lastWay = "";
  readonly deviceId = newId();
  constructor(private reg: EmulatorRegister, private o: KitOptions, private emit: Emit) { super(); this.hwKind = o.hardware[0] ?? ""; }

  get vibrates(): boolean { return typeof navigator !== "undefined" && "vibrate" in navigator; }
  /** The tones in force now (core/emulators.tones through the port). */
  now(): Tones { return tones(this.manager, this.o.customerFacing ? null : this.user, this.o.customerFacing, this.silent, this.quietHours, true); }
  press(kind: Sound): void { play(this.reg, kind, this.now()); }

  // ---- what the cloud says (the emulator's controls play the cloud) ------------------------------------------------------------
  /** A manager offered this emulator to the device (QR code, Lynk Code or link). */
  offered(business: string, sentBy: string): void { this.request = { assignment: newId(), business, sentBy, state: "sent" }; this.link = "request"; this.sheet = ""; }
  cloud(link: Link): void {
    if (link === "connected" && this.link === "disconnected") this.askState = null;
    this.link = link; if (link !== "request") this.request = null; this.sheet = "";
  }
  /** The person at the device taps Accept or Deny. Answering needs the cloud once (class C), so offline it waits for the link. */
  answer(accept: boolean, online: boolean): boolean {
    const r = this.request; if (!r || !online) return false;
    this.emit("EmulatorRequestAnswered", { assignment_id: r.assignment, device_id: this.deviceId, answer: accept ? "accept" : "deny" }, "device");
    r.state = accept ? "accepted" : "failed";
    if (accept) { this.link = "connected"; this.homeAdded = false; this.press("confirm"); }
    else { this.link = "disconnected"; this.press("cancel"); }
    return true;
  }
  /** The Connect request button on a disconnected emulator: a question for the manager, kept and sent when the link is back. */
  ask(online: boolean): void {
    if (this.link !== "disconnected") return;
    this.emit("EmulatorConnectAsked", { device_id: this.deviceId, emulator: this.o.emulator }, "device");
    this.link = "asked"; this.askState = online ? "sent" : "queued";
  }
  /** Key tones on or off, vibration on or off, volume (where the manager lets the user change them). */
  setTone(key: "tones" | "vibration" | "volume", value: boolean | string): boolean {
    if (this.o.customerFacing || this.manager.user_may_change === false) return false;
    if (key === "volume") { if (!["low", "medium", "high"].includes(String(value))) return false; this.user.volume = String(value); }
    else this.user[key] = Boolean(value);
    savePrefs(key === "volume" ? { volume: String(value) as Volume } : { [key]: Boolean(value) });
    const s = this.now();
    this.emit("EmulatorSettingsChanged", { device_id: this.deviceId, tones: s.tones, vibration: s.vibration, volume: s.volume, pin_same_tone: s.pin_tones === "same", by: "device" }, "device");
    this.press("key"); return true;
  }
  health(online: boolean, unsent: number, printer?: string): void {
    const p: Record<string, unknown> = { device_id: this.deviceId, online, unsent };
    if (printer) p["printer"] = printer;
    this.emit("DeviceHealthReported", p, "device");
  }
  /** Whether the screen behind may be used: only when connected (practice included). */
  usable(): boolean { return this.link === "connected"; }

  act(a: string, L: KitLook): boolean {
    if (!a.startsWith("emk:")) return false;
    const [, k = "", v = ""] = a.split(":");
    switch (k) {
      case "retry": this.retry(); break;                     // Retry starts the wait again; online it arrives, offline it waits again
      case "accept": this.answer(true, L.online); break;
      case "deny": this.answer(false, L.online); break;
      case "ask": this.ask(L.online); this.press("confirm"); break;
      case "home": this.homeAdded = true; this.press("confirm"); break;
      case "sheet": this.sheet = (["settings", "hardware", "delivery", ""] as const).includes(v as never) ? (v as EmKit["sheet"]) : ""; this.press("key"); break;
      case "tones": this.setTone("tones", v === "on"); break;
      case "vibration": this.setTone("vibration", v === "on"); break;
      case "volume": this.setTone("volume", v); break;
      case "hw": this.hwKind = v; this.press("key"); break;
      case "way": this.lastWay = v; this.press(v === "print" ? "printer" : "confirm"); break;
      default: return false;
    }
    return true;
  }

  // ---- drawing ------------------------------------------------------------------------------------------------------------
  /** The screen that stands in for the emulator while it is not connected, or "" when the emulator itself shows. */
  cover(L: KitLook): string {
    const t = L.t;
    const box = (ic: string, title: string, body: string, more = ""): string =>
      `<div class="emk" role="region" aria-label="${esc(title)}"><div class="emk-card"><span class="emk-ic" aria-hidden="true">${L.icon(ic)}</span><h2>${esc(title)}</h2>${body}${more}</div></div>`;
    switch (this.link) {
      case "request": {
        const r = this.request; if (!r) return "";
        return box("ui-bell", t("emk_request_title"), `<p><strong>${esc(t(r.business))}</strong></p><p>${esc(t("emk_request_body", { emulator: t(`emk_em_${this.o.emulator.replace(".", "_")}`), by: t(r.sentBy) }))}</p>
          ${L.online ? "" : `<p class="emk-note" role="status">${esc(t("emk_request_offline"))}</p>`}`,
          `<div class="emk-row"><button type="button" class="emk-btn primary" data-act="emk:accept" ${L.online ? "" : "disabled"}>${esc(t("emk_accept"))}</button><button type="button" class="emk-btn" data-act="emk:deny" ${L.online ? "" : "disabled"}>${esc(t("emk_deny"))}</button></div>`);
      }
      case "disconnected":
      case "asked":
        return box("ui-lock", t("emk_disconnected_title"), `<p>${esc(t("emk_disconnected_body", { emulator: t(`emk_em_${this.o.emulator.replace(".", "_")}`) }))}</p>`,
          this.link === "asked" ? `<p class="emk-state" role="status">${chipHtml(this.askState ?? "sent", t, L.icon)} ${esc(t("emk_asked"))}</p>`
            : `<button type="button" class="emk-btn primary" data-act="emk:ask">${esc(t("emk_connect_request"))}</button>`);
      case "lost": return box("ui-lock", t("emk_lost_title"), `<p>${esc(t("emk_lost_body"))}</p>`);
      case "reapproval": return box("ui-sync", t("emk_reapproval_title"), `<p>${esc(t("emk_reapproval_body"))}</p>`);
      default: return "";
    }
  }
  /** Shown above a connected emulator: practice mode, and the one-time "Add to home screen" step after Accept. */
  banner(L: KitLook): string {
    const t = L.t; let out = "";
    if (this.practice) out += `<p class="emk-practice" role="status">${L.icon("ui-info")} <strong>${esc(t("emk_practice"))}</strong> ${esc(t("emk_practice_body"))}</p>`;
    if (this.link === "connected" && this.request?.state === "accepted" && !this.homeAdded)
      out += `<div class="emk-home"><p>${esc(t("emk_home_body", { name: t(`emk_em_${this.o.emulator.replace(".", "_")}`) }))}</p><button type="button" class="emk-btn" data-act="emk:home">${esc(t("emk_home"))}</button></div>`;
    return out;
  }
  /** The device's own settings sheet: key tones, vibration and volume (where allowed), the hardware helper and the delivery menu. */
  sheetHtml(L: KitLook): string {
    if (!this.sheet) return "";
    const t = L.t, s = this.now(), may = !this.o.customerFacing && this.manager.user_may_change !== false;
    const onOff = (key: "tones" | "vibration", on: boolean, label: string): string =>
      `<button type="button" class="emk-toggle" data-act="emk:${key}:${on ? "off" : "on"}" aria-pressed="${on}" ${may ? "" : "disabled"}><span>${esc(label)}</span><strong>${esc(t(on ? "emk_on" : "emk_off"))}</strong></button>`;
    const head = `<div class="emk-tabs" role="group" aria-label="${esc(t("emk_device_settings"))}">${(["settings", "hardware", "delivery"] as const).map((k) =>
      `<button type="button" class="emk-btn" data-act="emk:sheet:${k}" aria-pressed="${this.sheet === k}">${esc(t(`emk_tab_${k}`))}</button>`).join("")}<button type="button" class="emk-btn" data-act="emk:sheet:">${esc(t("emk_close"))}</button></div>`;
    let body = "";
    if (this.sheet === "settings") {
      body = `<h2>${esc(this.o.deviceName)}</h2>${onOff("tones", s.tones, t("emk_key_tones"))}${onOff("vibration", s.vibration, t("emk_vibration"))}
        <div class="emk-row" role="group" aria-label="${esc(t("emk_volume"))}"><span>${esc(t("emk_volume"))}</span>${["low", "medium", "high"].map((v) =>
          `<button type="button" class="emk-btn" data-act="emk:volume:${v}" aria-pressed="${s.volume === v}" ${may ? "" : "disabled"}>${esc(t(`emk_vol_${v}`))}</button>`).join("")}</div>
        <p class="emk-note">${esc(t(may ? "emk_tones_note" : this.o.customerFacing ? "emk_tones_manager_kiosk" : "emk_tones_manager"))}</p>
        ${this.vibrates ? "" : `<p class="emk-note">${esc(t("emk_no_vibration"))}</p>`}${this.silent || this.quietHours ? `<p class="emk-note">${esc(t("emk_quiet"))}</p>` : ""}
        <p class="emk-note">${esc(t(s.pin_tones === "same" ? "emk_pin_same" : "emk_pin_per_key"))}</p>`;
    } else if (this.sheet === "hardware") {
      const adv = this.hwKind ? hardwareAdvice(this.reg, this.hwKind, this.o.os) : { ways: [], fallback: null };
      body = `<h2>${esc(t("emk_hw_title"))}</h2><div class="emk-choices">${this.o.hardware.map((h) => `<button type="button" class="emk-choice" data-act="emk:hw:${h}" aria-pressed="${this.hwKind === h}"><strong>${esc(t(`emk_hw_${h}`))}</strong></button>`).join("") || `<p class="emk-note">${esc(t("emk_hw_none"))}</p>`}</div>
        ${this.hwKind ? (adv.ways.length ? `<p>${esc(t("emk_hw_ways"))}</p><ol class="emk-ways">${adv.ways.map((w) => `<li>${esc(t(`emk_way_${w}`))}</li>`).join("")}</ol>`
          : `<p role="status">${esc(t("emk_hw_another"))}</p>`) : ""}<p class="emk-note">${esc(t("emk_hw_note"))}</p>`;
    } else {
      const ways: Way[] = deliveryWays(this.o.caps, L.online, Boolean(this.o.caps.device_print), true, true);
      body = `<h2>${esc(t("emk_send_title"))}</h2><div class="emk-choices">${ways.map((w) => `<button type="button" class="emk-choice" data-act="emk:way:${w.way}" aria-pressed="${this.lastWay === w.way}"><strong>${esc(t(`emk_send_${w.way}`))}</strong>${w.state === "queued" ? `<span>${esc(t("st_queued"))}</span>` : ""}</button>`).join("")}</div>
        <p class="emk-note">${esc(t("emk_send_note"))}</p>`;
    }
    return `<div class="emk-sheet" role="dialog" aria-label="${esc(t("emk_device_settings"))}">${head}${body}</div>`;
  }
  /** The check before assigning, as this device would answer it ("Will it work?"). */
  willItWork(t: T): string {
    const r = canRun(this.reg, this.o.emulator, { ...this.o.caps, os: this.o.os });
    return r.ok ? (r.missing.length ? r.missing.map((m) => t(`emk_way_round_${m.way}`)).join(" ") : t("emk_will_work")) : t(`emk_refused_${r.refused}`);
  }
  /** The service's artwork in spare space beside a fitted screen (70.5): never during a payment, cash count or signature, never in lite mode. */
  art(screenW: number, screenH: number, designW: number, designH: number, picture: string, lite: boolean, busy: boolean): string {
    const f = fitScreen(this.reg, screenW, screenH, designW, designH);
    if (lite || f.artwork === "none" || !picture) return "";
    return `<div class="emk-art ${f.artwork}${busy ? " still" : ""}" aria-hidden="true">${picture}</div>`;
  }
}

function chipHtml(s: St, t: T, icon: Icon): string { return `<span class="chip st-${s}">${icon(`status-${s}`)}<span>${esc(t(`st_${s}`))}</span></span>`; }

/** The emulator's own controls play the cloud's side for the kit (testers only; never on a real device). */
export function kitControl(k: EmKit, t: T): string {
  return `<div class="ctl-extra" role="group" aria-label="${esc(t("emk_panel_testing"))}"><p class="plabel">${esc(t("emk_panel_testing"))}</p>
    <label><span>${esc(t("emk_cloud_says"))}</span> <select data-kit="link">${(["connected", "request", "disconnected", "lost", "reapproval"] as const).map((l) =>
      `<option value="${l}" ${k.link === l || (l === "disconnected" && k.link === "asked") ? "selected" : ""}>${esc(t(`emk_link_${l}`))}</option>`).join("")}</select></label>
    <label><input type="checkbox" data-kit="practice" ${k.practice ? "checked" : ""}> <span>${esc(t("emk_practice"))}</span></label>
    <label><input type="checkbox" data-kit="quiet" ${k.quietHours ? "checked" : ""}> <span>${esc(t("emk_quiet_hours"))}</span></label>
    <label><input type="checkbox" data-kit="firstopen" ${k.firstOpen ? "checked" : ""}> <span>${esc(t("emk_first_open"))}</span></label>
    <button type="button" class="emk-btn" data-act="emk:sheet:settings">${esc(t("emk_device_settings"))}</button></div>`;
}
/** The control changes: what the cloud says, practice mode and quiet hours. */
export function kitChange(k: EmKit, el: HTMLInputElement & HTMLSelectElement, business: string, sentBy: string): boolean {
  const w = el.dataset["kit"]; if (!w) return false;
  if (w === "link") { const v = el.value as Link; if (v === "request") k.offered(business, sentBy); else k.cloud(v); }
  else if (w === "practice") k.practice = el.checked;
  else if (w === "firstopen") { k.setFirstOpen(el.checked); }
  else if (w === "quiet") k.quietHours = el.checked;
  return true;
}
/** The sound for a pressed control on a device (every press also shows on the screen). */
export function soundFor(el: HTMLElement, device?: HTMLElement | null, pinTones: "same" | "per_key" = "per_key"): Sound {
  const pressedAttr = el.getAttribute("aria-pressed") ?? el.getAttribute("aria-checked");
  const privateEntry = Boolean(el.closest(PRIVATE_ENTRY) || device?.querySelector(PRIVATE_ENTRY));
  return soundForAct(el.dataset["act"] ?? "", { primary: el.classList.contains("primary") || el.classList.contains("dsh-primary"), pressed: pressedAttr === null ? null : pressedAttr === "true",
    privateEntry, pinTones, text: el.textContent?.trim() });
}

/** The kit's options for one emulator of the register: its service, whether it faces customers and its hardware come from
 *  catalog/emulators.v1.json, never typed in an emulator. */
export function kitFor(reg: EmulatorRegister, emulator: string, deviceName: string, caps: Caps, os: string): KitOptions {
  const e = reg.emulators.find((x) => x.id === emulator);
  if (!e) throw new Error(`${emulator} is not in catalog/emulators.v1.json`);
  return { emulator, service: e.shared_with ?? e.service, deviceName, caps, os, customerFacing: e.customer_facing, hardware: e.hardware };
}

export interface KitWiring {
  /** At the end of every draw: not connected, the kit's screen replaces the emulator's (still inside the screen, so arrows, OK and
   *  Back reach it); connected, the practice banner and "Add to home screen" go on top and the settings sheet over it. */
  after: (screen: HTMLElement) => void;
}
/** Wires the kit into an emulator. The kit listens for its own presses (emk:) and controls (data-kit), and gives every press on the
 *  device its tone and vibration; the emulator only calls after() at the end of draw(), which also keeps the tester control beside the device. */
export function wireKit(k: EmKit, o: { t: T; icon: Icon; online: () => boolean; busy?: () => boolean; redraw: () => void; device?: () => HTMLElement | null }): KitWiring {
  const look = (): KitLook => ({ t: o.t, icon: o.icon, online: o.online(), busy: o.busy?.() ?? false });
  if (typeof document !== "undefined") {
    document.addEventListener("click", (e) => {
      const b = (e.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-act]");
      if (!b || b.hasAttribute("disabled")) return;
      const a = b.dataset["act"] ?? "";
      if (a.startsWith("emk:")) { e.stopImmediatePropagation(); k.act(a, look()); o.redraw(); return; }
      const dev = o.device?.() ?? document.getElementById("rig");
      if (dev && dev.contains(b) && !b.closest(".panel, aside")) k.press(soundFor(b, dev, k.now().pin_tones));
    }, true);
    wireBusy(document, o.t);
    document.addEventListener("change", (e) => {
      const el = e.target as HTMLInputElement & HTMLSelectElement;
      if (!el?.dataset?.["kit"]) return;
      e.stopImmediatePropagation();
      kitChange(k, el, "emk_sample_business", "emk_sent_by_owner"); o.redraw();
    }, true);
  }
  return {
    after: (screen) => {
      if (typeof document !== "undefined") {                        // the tester control keeps its place beside the device across redraws
        let ctl = document.getElementById("emkCtl");
        if (!ctl) { document.querySelector("aside.panel")?.insertAdjacentHTML("beforeend", '<div id="emkCtl"></div>'); ctl = document.getElementById("emkCtl"); }
        if (ctl && !ctl.contains(document.activeElement)) ctl.innerHTML = kitControl(k, o.t);
      }
      const c = k.cover(look()), sh = k.sheetHtml(look());
      if (c) { screen.innerHTML = c + sh; return; }
      k.apply(screen, { t: o.t, online: o.online, redraw: o.redraw, retryAct: "emk:retry", retryClass: "emk-btn" });
      const b = k.banner(look());
      if (b) screen.insertAdjacentHTML("afterbegin", b);
      if (sh) screen.insertAdjacentHTML("beforeend", sh);
    },
  };
}



