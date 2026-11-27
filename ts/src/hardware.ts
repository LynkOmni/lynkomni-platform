/**
 * The shared hardware part (DRIVER UPDATE D12, D13, D18; blueprint 95): what each piece of hardware on a device is doing, and the
 * tester's Hardware control that plugs, unplugs, empties or breaks each one so the stand-in can be seen taking over. Every emulator
 * gets it through the device kit (ts/src/emkit.ts); its rules come only from catalog/drivers.v1.json through ts/src/drivers.ts.
 * A piece of hardware never stops the work: when it is down, its stand-in takes over, or the work goes on by hand.
 */
import { DRIVERS } from "./drivers.generated.js";
import { conditionsFor, roleStatus, type RoleStatus } from "./drivers.js";
import { hardwareNoneHtml } from "./devicenote.js";

type T = (k: string) => string;
const hwEsc = (s: string): string => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c] ?? c);

/** Every condition a tester can give a piece of hardware, in the register's order. */
export const HW_CONDITIONS: string[] = Object.keys(DRIVERS.conditions);

/** The hardware of one device and the condition of each piece (all connected to begin with). */
export class HwSim {
  cond: Record<string, string> = {};
  constructor(public roles: string[]) { for (const r of roles) this.cond[r] = "connected"; }
  set(role: string, condition: string): boolean {
    if (!this.roles.includes(role) || !conditionsFor(DRIVERS, role).includes(condition)) return false;
    this.cond[role] = condition; return true;
  }
  status(role: string): RoleStatus { return roleStatus(DRIVERS, role, this.cond[role] ?? "connected"); }
  /** The pieces that are not simply connected and fine: they get a line on the device. */
  problems(): RoleStatus[] { return this.roles.map((r) => this.status(r)).filter((s) => s.state !== "connected" || s.warning); }
  /** True when a role's work goes to its stand-in or by hand right now. */
  down(role: string): boolean { return this.status(role).next !== null; }
}

/** The tester's Hardware control in the panel, or the plain line when the device uses no extra hardware. */
export function hardwarePanelHtml(t: T, sim: HwSim): string {
  if (!sim.roles.length) return hardwareNoneHtml(t);
  return `<div class="ctl-extra" data-ctl="hardware" role="group" aria-label="${hwEsc(t("emk_hw_panel"))}"><p class="plabel">${hwEsc(t("emk_hw_panel"))}</p>${sim.roles.map((r) =>
    `<label><span>${hwEsc(t(`emk_hw_${r}`))}</span> <select data-kit="hw:${r}">${conditionsFor(DRIVERS, r).map((c) =>
      `<option value="${c}"${sim.cond[r] === c ? " selected" : ""}>${hwEsc(t(`emk_hwc_${c}`))}</option>`).join("")}</select></label>`).join("")}</div>`;
}

/** The line on the device's own screen for each piece that is not fine: what happened and what is used instead. Nothing when all is fine. */
export function hardwareLineHtml(t: T, sim: HwSim): string {
  const p = sim.problems();
  if (!p.length) return "";
  return `<div class="hwd-line" role="status">${p.map((s) => {
    const instead = s.stand_in ? ` ${hwEsc(t("emk_hw_using").replace("{x}", t(`emk_hws_${s.stand_in}`)))}` : s.next === "by_hand" ? ` ${hwEsc(t("emk_hw_by_hand"))}` : "";
    return `<p><strong>${hwEsc(t(`emk_hw_${s.role}`))}:</strong> ${hwEsc(t(`emk_hwc_${sim.cond[s.role]}`))}.${instead}</p>`;
  }).join("")}</div>`;
}
