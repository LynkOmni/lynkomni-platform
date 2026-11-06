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
