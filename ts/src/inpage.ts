/** Every demo page keeps its links in the page (section 4 step D2b, found by the fit guard's raw-word walk on CI): a link the
 *  screen handles itself carries data-act, so the browser never follows its href (a real address kept for hosted pages, screen
 *  readers and "open in new tab"); the screen's own click handler still runs. Added to every emulator by web/build.mjs. */
export function keepLinksInPage(doc: Document): void {
  doc.addEventListener("click", (e) => {
    const t = e.target as Element | null;
    const a = t && typeof t.closest === "function" ? t.closest("a[data-act]") : null;
    if (a && !(e as MouseEvent).ctrlKey && !(e as MouseEvent).metaKey && !(e as MouseEvent).shiftKey) e.preventDefault();
  }, true);
}
if (typeof document !== "undefined") keepLinksInPage(document);
