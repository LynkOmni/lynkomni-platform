"""Type a phone number the way a person would: the country's own sample number, shown as the field's placeholder
(ts/src/fields.ts phoneFieldHtml). The sample country follows the browser's region, so a fixed number only fits some
machines (found 2026-11-26: "0788123456" never completed a +237 number)."""


def fill_phone(pg, selector, fallback="0788123456"):
    sample = pg.get_attribute(selector, "placeholder") or ""
    digits = "".join(c for c in sample if c.isdigit()) or fallback
    pg.fill(selector, digits)
    return digits


def sign_in_business(pg, who="grace@example.com", check=None):
    """Sign in to the Business app like a person: choose how (email, username or phone, in that order; owner 2026-11-26),
    type it in that field, then a way (here the passkey)."""
    via = "email" if "@" in who else "phone" if who.replace(" ", "").lstrip("+").isdigit() else "username"
    pg.click(f'[data-act="wy:si:via:{via}"]')
    if check:
        check(f"sign in with {via}")
    if via == "email":
        pg.locator("#wyWhoEmail").click(); pg.keyboard.type(who)
    elif via == "phone":
        fill_phone(pg, "#wyWhoPhone")
    else:
        pg.locator("#wyWho").click(); pg.keyboard.type(who)
    pg.click('[data-act="wy:si:who"]')
    if check:
        check("ways to sign in")
    pg.click('[data-act="wy:si:way:passkey"]')


def choose_and_type_who(pg, who="grace.k"):
    """On a sign-in screen: Continue with username, then type it (the ways to sign in come next)."""
    pg.click('[data-act="wy:si:via:username"]')
    pg.locator("#wyWho").click(); pg.keyboard.type(who)


def pass_age(pg, year="1990", month="5", day="14", root=""):
    """The neutral age gate (owner 2026-11-26): types a sample adult birth date into the three boxes, presses Next and confirms.
    The age needed is never on the screen and the date is forgotten as soon as Next is pressed."""
    for k, v in (("y", year), ("m", month), ("d", day)):
        box = pg.locator(f'{root} [data-in="wy:birth_{k}"]'.strip())
        box.click(); box.press_sequentially(v)
    pg.click(f'{root} [data-act="wy:su:next:age"]'.strip())
    pg.click(f'{root} [data-act="wy:su:age:yes"]'.strip())   # Is this right? once; then the answer is locked
