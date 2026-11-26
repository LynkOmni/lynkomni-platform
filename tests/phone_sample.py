"""Type a phone number the way a person would: the country's own sample number, shown as the field's placeholder
(ts/src/fields.ts phoneFieldHtml). The sample country follows the browser's region, so a fixed number only fits some
machines (found 2026-11-26: "0788123456" never completed a +237 number)."""


def fill_phone(pg, selector, fallback="0788123456"):
    sample = pg.get_attribute(selector, "placeholder") or ""
    digits = "".join(c for c in sample if c.isdigit()) or fallback
    pg.fill(selector, digits)
    return digits
