// Visuals: illustrations, charts, diagrams, share and store images, app and web icons.
// Mirrors the Python module `visuals` (see visuals/__init__.py). The table is generated from visuals/needs.v1.json,
// so code asks for a visual by id and theme and never builds a file path. There are no placeholders: an unknown id throws.
import { VISUALS } from "./visuals.generated.js";

export type VisualTheme = "light" | "dark" | "contrast-light" | "contrast-dark";
export type VisualMode = "lite" | "sunlight" | undefined;
export interface VisualRef { id: string; kind: string; theme: string; file: string; alt: string; decorative: boolean }

export function visualIds(): string[] { return Object.keys(VISUALS).sort(); }

function pickTheme(files: Record<string, string>, theme: string, mode: VisualMode): string {
  const t = mode === "sunlight" && (theme === "light" || theme === "dark") ? `contrast-${theme}` : theme;
  const have = Object.keys(files);
  if (have.includes(t)) return t;
  if (have.length === 1 && have[0] === "light") return "light"; // fixed-appearance images (link previews, store graphics)
  throw new Error(`no ${t} version of this visual; available: ${have.join(", ")}`);
}

export function visual(id: string, theme: VisualTheme = "light", mode?: VisualMode, ext: "svg" | "png" = "svg"): VisualRef {
  const v = VISUALS[id];
  if (!v) throw new Error(`no visual "${id}": add it to visuals/needs.v1.json and run python3 visuals/generate.py (never use a placeholder)`);
  const wanted = ext === "png" ? v.png : v.files; // SVG is preferred; png lists the raster files
  const th = pickTheme(wanted, theme, mode);
  const file = wanted[th];
  if (!file || !file.endsWith("." + ext)) throw new Error(`${id} has no .${ext} file for ${th}`);
  return { id, kind: v.kind, theme: th, file, alt: v.alt, decorative: v.kind === "illustration" };
}

/** Like visual(), but returns undefined in lite mode, which shows no decorative images. */
export function decorative(id: string, theme: VisualTheme = "light", mode?: VisualMode): VisualRef | undefined {
  const v = visual(id, theme, mode);
  return mode === "lite" && v.decorative ? undefined : v;
}

export function visualAlt(id: string): string { return visual(id).alt; }
