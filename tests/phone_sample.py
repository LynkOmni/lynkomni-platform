"""Type a phone number the way a person would: the country's own sample number, shown as the field's placeholder
(ts/src/fields.ts phoneFieldHtml). The sample country follows the browser's region, so a fixed number only fits some
machines (found 2026-11-26: "0788123456" never completed a +237 number)."""


def fill_phone(pg, selector, fallback="0788123456"):
    sample = pg.get_attribute(selector, "placeholder") or ""
    digits = "".join(c for c in sample if c.isdigit()) or fallback
    pg.fill(selector, digits)
    return digits


def sign_in_business(pg, who="grace@example.com", check=None):
    """Sign in to the Business app like a person: one box for a username, email or phone number, then a way (here the
    passkey). Email and phone are both kept on every account and either one signs in (owner, 2026-11-26)."""
    pg.fill("#wyWho", who)
    pg.click('[data-act="wy:si:who"]')
    if check:
        check("ways to sign in")
    pg.click('[data-act="wy:si:way:passkey"]')
