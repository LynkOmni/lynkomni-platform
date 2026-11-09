/** Touch gestures for every touch interface (DEVICE, 48.17): swipe and long-press for fingers and pens, with the same result
 *  always reachable without a gesture (a button or a key), so nothing is gesture-only. Pointer Events cover touch, pen and mouse.
 *  - swipe from the start edge (inline-start, so it mirrors in right-to-left) opens the menu
 *  - swipe down on a sheet closes it
 *  - long-press (500 ms, little movement) asks for help on the item */
export interface GestureHandlers {
  edgeSwipe?: () => void;
  swipeDown?: (target: HTMLElement) => void;
  longPress?: (target: HTMLElement) => void;
}
export const EDGE_PX = 24, SWIPE_PX = 60, LONG_MS = 500, STILL_PX = 10;

/** Pure: which gesture a finished stroke was (tested without a browser). dx is in reading direction (positive = towards the end). */
export function classify(s: { x0: number; y0: number; x1: number; y1: number; ms: number; edgeStart: boolean }): "edge_swipe" | "swipe_down" | "long_press" | "tap" | null {
  const dx = s.x1 - s.x0, dy = s.y1 - s.y0, still = Math.abs(dx) < STILL_PX && Math.abs(dy) < STILL_PX;
  if (still && s.ms >= LONG_MS) return "long_press";
  if (s.edgeStart && dx > SWIPE_PX && Math.abs(dy) < Math.abs(dx)) return "edge_swipe";
  if (dy > SWIPE_PX && Math.abs(dx) < dy / 2) return "swipe_down";
  return still ? "tap" : null;
}

/** Attach the gestures to a root element. Only touch and pen strokes count; a mouse uses the buttons. Returns a detach function. */
export function gestures(root: HTMLElement, h: GestureHandlers, rtl: () => boolean): () => void {
  let start: { x: number; y: number; t: number; edge: boolean; target: HTMLElement; id: number } | null = null;
  let timer = 0, fired = false;
  const rect = () => root.getBoundingClientRect();
  const down = (e: PointerEvent) => {
    if (e.pointerType === "mouse") return;
    const r = rect(), fromStart = rtl() ? r.right - e.clientX : e.clientX - r.left;
    start = { x: e.clientX, y: e.clientY, t: performance.now(), edge: fromStart <= EDGE_PX, target: e.target as HTMLElement, id: e.pointerId };
    fired = false;
    window.clearTimeout(timer);
    timer = window.setTimeout(() => { if (start && h.longPress) { fired = true; h.longPress(start.target); } }, LONG_MS);
  };
  const move = (e: PointerEvent) => {
    if (start && e.pointerId === start.id && (Math.abs(e.clientX - start.x) > STILL_PX || Math.abs(e.clientY - start.y) > STILL_PX)) window.clearTimeout(timer);
  };
  const up = (e: PointerEvent) => {
    window.clearTimeout(timer);
    if (!start || e.pointerId !== start.id || fired) { start = null; return; }
    const sign = rtl() ? -1 : 1;
    const g = classify({ x0: 0, y0: start.y, x1: sign * (e.clientX - start.x), y1: e.clientY, ms: performance.now() - start.t, edgeStart: start.edge });
    if (g === "edge_swipe") h.edgeSwipe?.();
    else if (g === "swipe_down") h.swipeDown?.(start.target);
    start = null;
  };
  const cancel = () => { window.clearTimeout(timer); start = null; };
  root.addEventListener("pointerdown", down); root.addEventListener("pointermove", move);
  root.addEventListener("pointerup", up); root.addEventListener("pointercancel", cancel);
  return () => { root.removeEventListener("pointerdown", down); root.removeEventListener("pointermove", move); root.removeEventListener("pointerup", up); root.removeEventListener("pointercancel", cancel); };
}

/** Arrow-key and remote navigation inside a group of buttons or links (keyboard, TV remote, switch access): one stop per group
 *  with Tab, arrows move between items, Home and End jump. Returns true when the key was handled. */
export function arrowNav(e: KeyboardEvent, group: HTMLElement, rtl: boolean): boolean {
  const items = Array.from(group.querySelectorAll<HTMLElement>("a[href],button:not([disabled])")).filter((x) => x.offsetParent !== null);
  const i = items.indexOf(document.activeElement as HTMLElement);
  if (i < 0 || !items.length) return false;
  const next = rtl ? "ArrowLeft" : "ArrowRight", prev = rtl ? "ArrowRight" : "ArrowLeft";
  let j = i;
  if (e.key === next || e.key === "ArrowDown") j = (i + 1) % items.length;
  else if (e.key === prev || e.key === "ArrowUp") j = (i - 1 + items.length) % items.length;
  else if (e.key === "Home") j = 0;
  else if (e.key === "End") j = items.length - 1;
  else return false;
  e.preventDefault(); items[j]!.focus();
  return true;
}
