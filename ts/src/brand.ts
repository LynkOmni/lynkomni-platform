/** LynkOmni brand policy for TypeScript code (web, PWA, dashboards, Node services).
 *  The artwork and its manifest come from @lynkomni/icons (its `brand` export). This file decides WHICH asset to show
 *  and refuses unsafe sources. It never contains a brand colour or a logo file name: those come from the manifest. */
export const BRAND_THEMES = ["light", "dark", "contrast-light", "contrast-dark"] as const;
export type BrandTheme = (typeof BRAND_THEMES)[number];
export type BrandVariant = BrandTheme | "mono";
export type BrandAssetId = "emblem" | "logo" | "wordmark";

/** The part of @lynkomni/icons' brand manifest this code needs. */
export interface BrandManifest {
  assets: Record<string, { minWidthPx: number; accessibleName: string; variants: Record<string, { svg: string }> }>;
  icons?: Record<string, { group: string; accessibleName: string; svg: string }>;
}

/** The five user-facing states, and only these (design tokens `states`). */
export const STATUS_STATES = ["queued", "sent", "accepted", "confirmed", "failed"] as const;
export type StatusState = (typeof STATUS_STATES)[number];

/** Path of a one-colour icon inside the package, e.g. "icons/<file>.svg" (mirrors Python brand.icon). */
export function iconFile(m: BrandManifest, id: string): { file: string; accessibleName: string } {
  const i = m.icons?.[id];
  if (!i) throw new Error(`unknown icon ${id}`);
  return { file: i.svg, accessibleName: i.accessibleName };
}

/** The icon for one of the five states. Any other word throws (mirrors Python brand.status_icon). */
export function statusIconFile(m: BrandManifest, state: string): { file: string; accessibleName: string } {
  if (!(STATUS_STATES as readonly string[]).includes(state)) throw new Error(`${state} is not a user-facing state; use queued, sent, accepted, confirmed or failed`);
  return iconFile(m, `status-${state}`);
}

export const themeVariant = (theme: string): BrandTheme => {
  if (!(BRAND_THEMES as readonly string[]).includes(theme)) throw new Error(`unknown theme ${theme}`);
  return theme as BrandTheme;
};

/** Path of an asset inside the package, e.g. "svg/<file>.svg". Throws for an unknown asset or variant. */
export function brandFile(m: BrandManifest, id: string, variant: BrandVariant): string {
  const a = m.assets[id];
  if (!a) throw new Error(`unknown brand asset ${id}`);
  const v = a.variants[variant];
  if (!v) throw new Error(`unknown variant ${variant} for ${id}`);
  return v.svg;
}

/** Where a bundled brand file is served from. `base` must be a path on this site (or a data: URI), never another
 *  host: logos are bundled so they work offline and cannot be swapped remotely. */
export function brandSrc(base: string, m: BrandManifest, id: string, variant: BrandVariant): string {
  if (/^[a-z][a-z0-9+.-]*:/i.test(base) || base.startsWith("//")) throw new Error("brand files must be served from this site, not another host");
  return `${base.replace(/\/+$/, "")}/${brandFile(m, id, variant)}`;
}

/** Smallest width (px) the asset may be shown at. */
export const minWidth = (m: BrandManifest, id: string): number => {
  const a = m.assets[id];
  if (!a) throw new Error(`unknown brand asset ${id}`);
  return a.minWidthPx;
};

export interface InvoiceBrand { show_lynkomni: boolean; asset: BrandAssetId | null; screen: BrandVariant | null; print: BrandVariant | null; merchant_logo: boolean }
const INVOICE: Record<string, InvoiceBrand> = {
  lynkomni: { show_lynkomni: true, asset: "logo", screen: "light", print: "mono", merchant_logo: false },
  logo: { show_lynkomni: false, asset: null, screen: null, print: null, merchant_logo: true },
  full: { show_lynkomni: false, asset: null, screen: null, print: null, merchant_logo: true },
};
/** Same table as brand/__init__.py (invoice_brand). The tier names come from billing.FEATURES invoice_branding. */
export function invoiceBrand(tier: string): InvoiceBrand {
  const b = INVOICE[tier];
  if (!b) throw new Error(`unknown invoice branding tier ${tier}`);
  return { ...b };
}

/** Placement: which of logo, emblem and wordmark goes where. Same rules as brand/surfaces.v1.json (the Python module
 *  reads the same file; the test below checks both agree). */
export interface SurfaceRule { asset: BrandAssetId; minWidthPx?: number }
export interface Surface { id: string; colour: "theme" | "mono"; print?: "mono"; choose: SurfaceRule[]; uses: { asset: string; variants: string[] }[] }
export interface SurfacePolicy { surfaces: Surface[] }

export function chooseAsset(policy: SurfacePolicy, surfaceId: string, widthPx?: number): BrandAssetId {
  const s = policy.surfaces.find((x) => x.id === surfaceId);
  if (!s) throw new Error(`unknown brand surface ${surfaceId}`);
  const first = s.choose[0];
  const last = s.choose[s.choose.length - 1];
  if (!first || !last) throw new Error(`surface ${surfaceId} has no rules`);
  if (widthPx === undefined) return first.asset;
  for (const r of s.choose) if (widthPx >= (r.minWidthPx ?? 0)) return r.asset;
  return last.asset;
}

/** Variant for a place: one-colour places and print use mono, everything else follows the theme. */
export function surfaceVariant(policy: SurfacePolicy, surfaceId: string, theme: string, printing = false): BrandVariant {
  const s = policy.surfaces.find((x) => x.id === surfaceId);
  if (!s) throw new Error(`unknown brand surface ${surfaceId}`);
  const t = themeVariant(theme);
  return s.colour === "mono" || (printing && s.print === "mono") ? "mono" : t;
}

export const NO_BADGE_SCREENS: readonly string[] = ["payment", "refund", "void", "cash-count", "fiscal", "private-chat"];
/** Whether the small "Powered by LynkOmni" wordmark shows. `tier` is billing.FEATURES powered_by. */
export function poweredBy(tier: string, screen: string, merchantRemoved = false): boolean {
  if (tier !== "required" && tier !== "removable") throw new Error(`unknown powered_by value ${tier}`);
  if (NO_BADGE_SCREENS.includes(screen)) return false;
  return tier === "required" ? true : !merchantRemoved;
}

/** The brand mark for a place on screen (brand/surfaces.v1.json), as the emulator build hands it over: the choices in order,
 *  each with the smallest width it needs and its light and dark drawing. The screen says which place it is and how much
 *  room it has; the first choice that fits wins (no width given = the place's first choice). Never a file name here. */
export interface PlaceChoice { asset: BrandAssetId; minWidthPx: number; light: string; dark: string }
export type BrandPlaces = Record<string, PlaceChoice[]>;
export function markFor(places: BrandPlaces, place: string, dark: boolean, widthPx?: number): { asset: BrandAssetId; svg: string } {
  const choices = places[place];
  if (!choices || choices.length === 0) throw new Error(`unknown brand place ${place}`);
  const pick = (widthPx === undefined ? choices[0] : choices.find((c) => widthPx >= c.minWidthPx)) ?? choices[choices.length - 1]!;
  return { asset: pick.asset, svg: dark ? pick.dark : pick.light };
}
/** The mark wrapped for the page: one image named LynkOmni, tagged with its place and asset so tests can check the rules. */
export function brandMark(places: BrandPlaces, place: string, dark: boolean, cls: string, widthPx?: number): string {
  const m = markFor(places, place, dark, widthPx);
  return `<span class="${cls}" role="img" aria-label="LynkOmni" data-brand-place="${place}" data-brand-asset="${m.asset}">${m.svg}</span>`;
}
