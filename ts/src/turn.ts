/** Turning the device (TURN UPDATE, master blueprint 76.2): turning, folding, splitting the screen or resizing a window only
 *  changes the shape. The new layout (ts/src/interfaces.ts layoutFor) is written as attributes on the screen root and the styles do
 *  the rest, so a turn never redraws a screen: typed text, the cursor, open panels, the basket, a payment step, a signature stroke
 *  and a recording stay exactly as they were, and nothing restarts, repeats or is cancelled. The scroll position of every scrolling
 *  box and the focused control are put back if the browser moved them, and a screen reader hears the new layout once. */
import type { DeviceRegister, Layout, ShapeFacts } from "./interfaces.js";
import { layoutFor } from "./interfaces.js";

export interface TurnRoot {
  setAttribute(name: string, value: string): void;
  getAttribute(name: string): string | null;
}

/** The attributes a layout writes on the screen root (styles read only these; screens never measure the window themselves). */
export function layoutAttributes(l: Layout): Record<string, string> {
  return {
    "data-orientation": l.orientation, "data-nav": l.nav, "data-tabs": String(l.tabs), "data-columns": String(l.columns),
    "data-header": l.header, "data-helper": l.helper, "data-main-button": l.main_button, "data-split": l.split,
    "data-locked": l.locked ? "true" : "false",
  };
}

/** Writes the layout on the root. Returns true only when something changed (the caller announces it once). */
export function applyLayout(root: TurnRoot, l: Layout): boolean {
  let changed = false;
  for (const [k, v] of Object.entries(layoutAttributes(l))) {
    if (root.getAttribute(k) !== v) { root.setAttribute(k, v); changed = true; }
  }
  return changed;
}

/** The words a screen reader hears after a turn: one message, only when the layout really changed (keys in web/navigation). */
export const turnMessageKey = (before: Layout | null, after: Layout): string | null =>
  !before || before.orientation === after.orientation ? null : after.orientation === "sideways" ? "nv_turned_sideways" : "nv_turned_upright";

export interface ScrollBox { scrollTop: number; scrollLeft: number }
export interface Kept { scroll: [ScrollBox, number, number][]; focus: { focus(o?: { preventScroll?: boolean }): void } | null }

/** What a turn must never lose that the browser itself may move: every scroll position and the focused control. */
export function keep(boxes: Iterable<ScrollBox>, focused: Kept["focus"]): Kept {
  return { scroll: [...boxes].map((b) => [b, b.scrollTop, b.scrollLeft] as [ScrollBox, number, number]), focus: focused };
}
export function restoreKept(k: Kept, active: unknown): void {
  for (const [b, top, left] of k.scroll) { if (b.scrollTop !== top) b.scrollTop = top; if (b.scrollLeft !== left) b.scrollLeft = left; }
  if (k.focus && active !== k.focus) k.focus.focus({ preventScroll: true });
}

/** Works out the layout for the window's present shape and applies it; returns the layout and the message to announce (or null). */
export function turn(reg: DeviceRegister, root: TurnRoot, facts: ShapeFacts, before: Layout | null): { layout: Layout; announce: string | null } {
  const layout = layoutFor(reg, facts);
  const changed = applyLayout(root, layout);
  return { layout, announce: changed ? turnMessageKey(before, layout) : null };
}

/** The shape of a device held upright or turned sideways, from its upright size (TURN UPDATE 76.8): the emulators of a phone or a
 *  tablet use it with layoutFor, so every screen already built is tried in both directions. */
export function turnedShape(turn: "upright" | "sideways" | undefined, upright: { interface: string; width: number; height: number; device?: string }): { interface: string; width: number; height: number; device?: string } {
  return turn === "sideways" ? { ...upright, width: upright.height, height: upright.width } : upright;
}

