/**
 * The plain line in the panel of a page that is not one device (a web page or a phone page): it works by touch, mouse or keyboard
 * on any device, so there is no touch screen or buttons choice to make (owner, 2026-11-26). Device emulators use
 * ts/src/devicemode.ts deviceChoiceHtml instead. Every page carries this part (web/build.mjs).
 */
export function anyDeviceHtml(t: (k: string) => string): string {
  return `<p class="vonly" data-ctl="version-only">${t("version_only_web")}</p>` + hardwareNoneHtml(t);
}

/** The plain line in the panel of a page or device that uses no extra hardware (DRIVER UPDATE D13): everything works on its own
 *  screen and keys. Pages with hardware show the Hardware control of ts/src/hardware.ts through the device kit instead. */
export function hardwareNoneHtml(t: (k: string) => string): string {
  return `<p class="vonly" data-ctl="hardware-none">${t("hw_none_page")}</p>`;
}

/** The plain line for a device that does not turn, with its reason (owner, 2026-11-26): its panel says so instead of offering a
 *  turn it cannot make. Devices that can turn offer Upright or Sideways (the panel's turn control). */
export function turnFixedHtml(t: (k: string) => string, why: "turn_fixed_terminal" | "turn_fixed_counter" | "turn_fixed_laptop" | "turn_fixed_card" | "turn_fixed_pair" | "turn_fixed_keypad"): string {
  return `<p class="vonly" data-ctl="turn-fixed">${t(why)}</p>`;
}
