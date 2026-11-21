// Placeholders done properly (PLACEHOLDER UPDATE, owner 2026-11-19, master blueprint section 83; rules in
// catalog/placeholders.v1.json, checked by tests/test_placeholders.py). Three parts, shared by every screen:
//  1. Loading skeletons shaped like the real content, so nothing jumps when it arrives. They appear only when loading takes
//     longer than a moment, stay at least a moment once shown, and turn into a "taking longer" note with Retry when slow.
//  2. Field hints: an example of what to type, never the instruction (the label stays visible). Sensitive fields get none.
//  3. Designed empty states come from shell.ts state(); this file only decides when loading becomes one of them.
// Cached content is always shown first; a skeleton is only for content the device has never had.

/** The shapes a skeleton can take: one per page template and part. */
export type SkeletonShape = "list" | "cards" | "record" | "form" | "table" | "chart" | "chat" | "tracker" | "tiles" | "media" | "text";
export const SHAPES: readonly SkeletonShape[] = ["list", "cards", "record", "form", "table", "chart", "chat", "tracker", "tiles", "media", "text"];

/** Timing (ms): nothing before SHOW_AFTER (no flash), at least MIN_SHOW once shown, a "taking longer" note after SLOW_AFTER. */
export const TIMING = { SHOW_AFTER: 300, MIN_SHOW: 300, SLOW_AFTER: 8000 } as const;

export type Phase = "nothing" | "skeleton" | "slow";
/** What a screen shows while it waits: pure, so every device and the tests agree. */
export function loadingPhase(elapsedMs: number, cached: boolean): Phase {
  if (cached) return "nothing";                         // cached content stays on screen; a quiet "Updating" chip may show
  if (elapsedMs < TIMING.SHOW_AFTER) return "nothing";
  return elapsedMs < TIMING.SLOW_AFTER ? "skeleton" : "slow";
}
/** How long a skeleton that was shown must stay before the content replaces it (never a flash). */
export function holdFor(shownAtMs: number, nowMs: number): number {
  return Math.max(0, TIMING.MIN_SHOW - (nowMs - shownAtMs));
}

const phEsc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] as string));
const phBar = (cls: string) => `<span class="skel ${cls}" aria-hidden="true"></span>`;

/** A skeleton in the shape of the content to come. count = how many rows or cards the screen showed last time (default 3).
 *  One polite "Loading" for the whole block; screen readers never hear each grey bar. */
export function skeletonHtml(shape: SkeletonShape, loadingWord: string, count = 3): string {
  const n = Math.max(1, Math.min(count, 12));
  const rep = (f: () => string) => Array.from({ length: n }, f).join("");
  const body: Record<SkeletonShape, () => string> = {
    list: () => rep(() => `<span class="skel-row">${phBar("dot")}<span class="skel-col">${phBar("line")}${phBar("line short")}</span></span>`),
    cards: () => `<span class="skel-grid">${rep(() => `<span class="skel-card">${phBar("media")}${phBar("line")}${phBar("line short")}</span>`)}</span>`,
    record: () => `${phBar("title")}${phBar("line short")}${rep(() => `<span class="skel-pair">${phBar("label")}${phBar("line")}</span>`)}`,
    form: () => rep(() => `<span class="skel-field">${phBar("label")}${phBar("input")}</span>`) + phBar("button"),
    table: () => `<span class="skel-table">${rep(() => `<span class="skel-tr">${phBar("cell")}${phBar("cell")}${phBar("cell")}</span>`)}</span>`,
    chart: () => `<span class="skel-chart">${phBar("axis")}${rep(() => phBar("col"))}</span>`,
    chat: () => rep(() => `<span class="skel-msg">${phBar("bubble")}</span>`),
    tracker: () => `<span class="skel-steps">${rep(() => `<span class="skel-step">${phBar("dot")}${phBar("line short")}</span>`)}</span>`,
    tiles: () => `<span class="skel-grid">${rep(() => `<span class="skel-tile">${phBar("label")}${phBar("figure")}</span>`)}</span>`,
    media: () => phBar("media"),
    text: () => rep(() => phBar("line")) + phBar("line short"),
  };
  return `<div class="skeleton skel-${shape}" role="status" aria-busy="true" aria-live="polite" aria-label="${phEsc(loadingWord)}" data-skeleton="${shape}">${body[shape]()}</div>`;
}

// Field hints live in ts/src/hints.ts (a small part of their own).
