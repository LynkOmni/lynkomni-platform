/** Ads on screens (ADS UPDATE, master blueprint 79; section 4 row 79.10): the device-side rules of services/ads.py (checked against
 *  contract/vectors/ads.v1.json) and the one shared ad slot every screen draws. The slot is drawn only after the screen is ready, from
 *  the device's cached bundle, never moves anything already on screen and leaves no gap and no message when there is no ad. It is
 *  always labelled, carries "Why am I seeing this?" and "Report this ad", has no animation, sound or pop-up, and lite mode hides it.
 *  Words live in web/pos (keys ad_*). */
import { ADS } from "./ads.generated.js";

export interface AdContext { screen?: string | null; audience?: string | null; workspace?: string | null; ad_free?: boolean; hosting?: boolean; lite?: boolean; country_on?: boolean }

/** The rule a screen asks before it draws an ad slot. Throws for a place that is not in the register (ads only where the allow-list says). */
export function mayShow(place: string, c: AdContext = {}): boolean {
  if (!(ADS.places as readonly string[]).includes(place)) throw new Error(`unknown ad place ${place}`);
  if ((c.screen && (ADS.never as readonly string[]).includes(c.screen)) || (c.audience && (ADS.never_audiences as readonly string[]).includes(c.audience))
      || (c.workspace && ((ADS.never_audiences as readonly string[]).includes(c.workspace) || c.workspace === "school"))) return false;
  if (c.lite || c.ad_free || !c.country_on) return false;
  return (ADS.hosted_by_choice as readonly string[]).includes(place) ? Boolean(c.hosting) : true;
}

/** An impression counts only when at least half the ad was on screen for at least a second. */
export const counts = (pct: number | null, ms: number | null): boolean => (pct ?? 0) >= ADS.min_visible_pct && (ms ?? 0) >= ADS.min_visible_ms;

export interface Ad { id: string; text: string; sample: boolean }
export interface AdLook { t: (k: string, v?: Record<string, string | number>) => string; esc: (s: string) => string; icon: (id: string) => string }

/** The labelled ad slot, or "" (no gap) when there is none. The buttons carry data-act="ad:why:<id>" and "ad:report:<id>". */
export function slotHtml(place: string, ad: Ad | null, L: AdLook, kind: "card" | "line" = "card"): string {
  if (!ad) return "";
  const label = `<span class="ad-label">${L.esc(L.t("ad_sponsored"))}${ad.sample ? ` · ${L.esc(L.t("ad_sample"))}` : ""}</span>`;
  if (kind === "line") return `<p class="ad-line" data-ad="${L.esc(place)}">${label} ${L.esc(ad.text)}</p>`;
  return `<aside class="ad-slot" data-ad="${L.esc(place)}" aria-label="${L.esc(L.t("ad_sponsored"))}">${label}<p class="ad-text">${L.esc(ad.text)}</p>`
    + `<p class="ad-acts"><button type="button" class="linkbtn" data-act="ad:why:${L.esc(ad.id)}">${L.esc(L.t("ad_why"))}</button>`
    + `<button type="button" class="linkbtn" data-act="ad:report:${L.esc(ad.id)}">${L.esc(L.t("ad_report"))}</button></p></aside>`;
}

/** The answer under "Why am I seeing this?": contextual only, never who the person is. */
export const whyHtml = (L: AdLook): string => `<p class="ad-why" role="status">${L.esc(L.t("ad_why_text"))}</p>`;
