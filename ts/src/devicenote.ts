/**
 * The plain line in the panel of a page that is not one device (a web page or a phone page): it works by touch, mouse or keyboard
 * on any device, so there is no touch screen or buttons choice to make (owner, 2026-11-26). Device emulators use
 * ts/src/devicemode.ts deviceChoiceHtml instead. Every page carries this part (web/build.mjs).
 */
export function anyDeviceHtml(t: (k: string) => string): string {
  return `<p class="vonly" data-ctl="version-only">${t("version_only_web")}</p>`;
}
