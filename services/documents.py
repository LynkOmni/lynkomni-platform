"""Printable and emailable documents: invoice, receipt, email shell. They only show logos through the brand module.

Rules (see CLAUDE.md): ask brand.for_surface for a place, never a file; no colours are written here (text inherits the
reader's colours); the LynkOmni logo shows on an invoice only on the Free LynkInv tier; the small "Powered by LynkOmni"
wordmark follows billing.FEATURES powered_by and never appears on payment, refund, void, cash-count, fiscal or private-chat
screens (so never on a receipt); an invoice is never called a tax invoice (the label comes from Invoicing.label); an invoice
says "Paid" only when its state is paid, which needs the provider to confirm. The merchant's own logo (PNG, JPEG or WebP,
never SVG) is added in a later step, so for now a merchant's name is shown as text.
All text is escaped. Money is integer minor units + currency code, formatted by core.money.fmt."""
import base64, html
import brand
from core.money import fmt
from services.merchant_logo import data_uri as merchant_logo_uri

EMAIL_THEMES = ("light", "dark")      # the email PNGs exist for these two only


def _esc(x): return html.escape(str(x), quote=True)


def _svg_img(asset, height):
    """An <img> for a vendored SVG, with the asset's own accessible name as alt text."""
    return f'<img src="{brand.data_uri(asset.id, asset.variant)}" alt="{_esc(asset.accessible_name)}" height="{int(height)}">'


def _png_img(asset_id, theme, height):
    """For email: the generated PNG, because many mail apps do not draw SVG."""
    if theme not in EMAIL_THEMES:
        raise ValueError("email images exist for light and dark only")
    path = brand.raster(f"email/{asset_id}-{theme}.png")
    with open(path, "rb") as f:
        uri = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
    name = brand.manifest()["assets"][asset_id]["accessibleName"]
    return f'<img src="{uri}" alt="{_esc(name)}" height="{int(height)}">'


def _page(title, body, lang="en"):
    return (f'<!doctype html><html lang="{_esc(lang)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{_esc(title)}</title></head><body>{body}</body></html>')


def _badge_html(iv, merchant, theme, screen, merchant_removed):
    tier = iv.ent(merchant).get("powered_by", "required")
    if not brand.powered_by(tier, screen, merchant_removed):
        return ""
    return f'<p><small>Powered by {_svg_img(brand.for_surface("powered-by-badge", theme), 14)}</small></p>'


def invoice_html(platform, merchant, invoice_id, theme="light", printing=False, merchant_name=None, merchant_removed_badge=False, merchant_logo=None):
    """The invoice page. Header carries the LynkOmni logo only on the Free tier; paid tiers show the merchant's name as text."""
    iv = platform.invoicing
    v = iv.inv[invoice_id]
    if v["merchant"] != merchant:
        raise PermissionError("this invoice belongs to another merchant")
    show = brand.invoice_brand(iv.ent(merchant).get("invoice_branding", "lynkomni"))
    head = _svg_img(brand.for_surface("invoice-header", theme, printing=printing), 36) if show["show_lynkomni"] else ""
    if merchant_logo and show["merchant_logo"]:       # only tiers that allow it; re-checked now, never trusted from storage
        head = f'<img src="{_esc(merchant_logo_uri(merchant_logo))}" alt="{_esc(merchant_name or "Merchant logo")}" height="36">'
    cur = v["currency"]
    rows = "".join(
        f'<tr><td>{_esc(ln.get("description", ""))}</td><td>{_esc(_qty(ln["qty_milli"]))}</td><td>{_esc(fmt(ln["unit_minor"], cur))}</td></tr>'
        for ln in v["lines"])
    state = iv.state(invoice_id)
    status = {"paid": "Paid", "overdue": "Overdue", "void": "Void", "credited": "Credited", "partially_paid": "Partly paid"}.get(state, "Not yet paid")
    body = (f'<header>{head}<h1>{_esc(v["label"])}</h1><p>Number {_esc(v["series"])}-{_esc(v["number"])}</p><p>{_esc(merchant_name or "")}</p></header>'
            f'<p>For {_esc(v["customer"])}</p><table><thead><tr><th>Item</th><th>Quantity</th><th>Unit price</th></tr></thead><tbody>{rows}</tbody></table>'
            f'<p>Net {_esc(fmt(v["net_minor"], cur))}</p><p>Tax {_esc(fmt(v["tax_minor"], cur))}</p><p><strong>Total {_esc(fmt(v["total_minor"], cur))}</strong></p>'
            f'<p>Status: {status}</p>{_badge_html(iv, merchant, theme, "invoice", merchant_removed_badge)}')
    return _page(f'{v["label"]} {v["series"]}-{v["number"]}', body)


def receipt_html(platform, merchant, invoice_id, payment_index, theme="light", printing=True, merchant_name=None):
    """A receipt for one confirmed payment. One-colour wordmark header, never a badge (receipts are payment screens).
    Cash payments are written by the merchant at the till; electronic payments only exist here after the provider confirmed them."""
    iv = platform.invoicing
    v = iv.inv[invoice_id]
    if v["merchant"] != merchant:
        raise PermissionError("this invoice belongs to another merchant")
    pays = v["payments"]
    if not (0 <= payment_index < len(pays)):
        raise KeyError("no such payment on this invoice")
    p = pays[payment_index]
    cur = v["currency"]
    head = _svg_img(brand.for_surface("receipt-header", theme, printing=printing), 20)
    body = (f'<header>{head}<h1>Receipt</h1><p>{_esc(merchant_name or "")}</p></header>'
            f'<p>For invoice {_esc(v["series"])}-{_esc(v["number"])}</p><p>Paid {_esc(fmt(p["amount_minor"], cur))} by {_esc(p["method"].replace("_", " "))}</p>'
            f'<p>Still owed {_esc(fmt(iv.outstanding(invoice_id), cur))}</p><p><small>This receipt is not a tax receipt.</small></p>')
    return _page("Receipt", body)


def email_html(subject, paragraphs, theme="light"):
    """A plain notice email: logo on top, wordmark in the footer. Never both marks side by side."""
    head = _png_img(brand.choose_asset("email-header"), theme, 32)
    foot = _png_img(brand.choose_asset("email-footer"), theme, 16)
    body = (f'<header>{head}</header><h1>{_esc(subject)}</h1>' + "".join(f"<p>{_esc(t)}</p>" for t in paragraphs) + f'<footer>{foot}</footer>')
    return _page(subject, body)


def _qty(milli):
    """Quantities are integer thousandths; show them without floats."""
    whole, frac = divmod(int(milli), 1000)
    return str(whole) if not frac else f"{whole}.{frac:03d}".rstrip("0")

