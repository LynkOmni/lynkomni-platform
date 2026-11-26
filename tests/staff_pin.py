"""Signing in with the sample staff PIN in browser tests (owner, 2026-11-26: the review panel never skips the PIN).

A screen button on a staff device waits on the lock screen; a person types their PIN and the chosen screen opens. Browser tests
that visit screens through the panel do the same with the first person's sample PIN, so every check looks at the real screen."""

# device: the first person's sample PIN (web/emulators/<device>/app.ts STAFF)
PINS = {"counter-tablet": "1234", "stock-scanner": "2468", "rider-phone": "1357", "kitchen-screen": "3691", "bet-counter": "1234"}
# Buttons that only lock, pick a person, ask for the duress PIN or open a manager's approval pad.
NOT_A_SCREEN = {"locked", "lock_screen", "pick_staff", "duress", "approve_second"}


def sign_in(pg, device, state=""):
    """Types the sample PIN when the lock screen is showing; does nothing anywhere else."""
    pin = PINS.get(device)
    if not pin or state in NOT_A_SCREEN or pg.locator('[data-act="gate:lock"]').count():
        return
    if pg.locator('[data-act="pin:ok"]').count():
        for d in pin:
            pg.click(f'[data-act="pin:{d}"] >> visible=true', timeout=3000)
        pg.click('[data-act="pin:ok"] >> visible=true', timeout=3000)
    elif pg.locator('.lock [data-act="d1"]').count():   # the counter tablet's own pad opens at the fourth digit
        for d in pin:
            pg.click(f'.lock [data-act="d{d}"]', timeout=3000)


def jump(pg, device, state, timeout=None):
    """Presses a panel screen button, then signs in if the lock asks."""
    kw = {"timeout": timeout} if timeout else {}
    pg.click(f'#stateButtons [data-state="{state}"]', **kw)
    sign_in(pg, device, state)
