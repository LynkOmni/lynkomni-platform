/** Languages, writing direction and the font files each language needs, for every LynkOmni app.
 *  Data comes from design/fonts/scripts.v1.json through fonts.generated.ts. Locale changes presentation only. */
import { FIRST_LOAD, LANGUAGES, SCRIPT_FILES } from "./fonts.generated.js";

export { LANGUAGES };
export type Direction = "ltr" | "rtl";

/** "ar-AE" -> "ar"; unknown languages return null. */
export function baseLanguage(tag: string): string | null {
  const t = tag.trim().toLowerCase().replace("_", "-");
  if (LANGUAGES[t]) return t;
  const base = t.split("-")[0] ?? "";
  return LANGUAGES[base] ? base : null;
}

/** Writing direction for a language tag. Unknown languages are left to right. */
export function direction(tag: string): Direction {
  const b = baseLanguage(tag);
  return b ? (LANGUAGES[b]?.dir ?? "ltr") : "ltr";
}

/** The attributes the root element of every page or screen gets: <html lang=".." dir="..">. */
export function rootAttributes(tag: string): { lang: string; dir: Direction } {
  return { lang: tag, dir: direction(tag) };
}

/** Font files to store on the device so text shows offline: always the Latin pair (numbers, prices, product names),
 *  plus the files of each script the merchant's languages use. Paths are relative to /fonts/. */
export function fontFilesFor(tags: readonly string[]): string[] {
  const out = new Set<string>(FIRST_LOAD);
  for (const tag of tags) {
    const b = baseLanguage(tag);
    const lang = b ? LANGUAGES[b] : undefined;
    for (const script of lang ? [lang.script, ...(lang.also ?? [])] : []) for (const f of SCRIPT_FILES[script] ?? []) out.add(f);
  }
  return [...out];
}

/** Every font file, for a full offline install (for example a shared shop terminal with several languages). */
export const ALL_FONT_FILES: readonly string[] = [...new Set(Object.values(SCRIPT_FILES).flat())];
