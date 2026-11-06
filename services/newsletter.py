"""Newsletter: double opt-in, explicit consent, minimal data, one-click unsubscribe. Nothing is pre-ticked and nobody is subscribed until they confirm.
The mailer is a separate adapter: this module returns the message to send and never claims it was delivered."""
import re, time
from core.capability import Capabilities
TOPICS = {"product", "merchant", "developer", "company"}
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

class Newsletter:
    CONSENT_VERSION = "newsletter-v1"
    def __init__(s, p):
        s.p, s.db = p, p.c.store.db
        s.caps = Capabilities(s.db)
        s.db.executescript("""create table if not exists newsletter(email text primary key, language text, country text, topics text, state text, consent_id text, consent_version text, created real, confirmed real, last_try real);""")
    def subscribe(s, email, language, country, topics, consent, honeypot="", now=None):
        now = now or time.time(); generic = {"status": "check_your_email"}      # the answer never reveals whether an address is already subscribed
        if honeypot: return generic                                              # a bot filled the hidden field: store nothing
        if not consent: raise ValueError("consent is required and cannot be pre-ticked")
        if not _EMAIL.match(email or "") or not set(topics) <= TOPICS: raise ValueError("invalid email or topic")
        email = email.strip().lower(); row = s.db.execute("select state, last_try from newsletter where email=?", (email,)).fetchone()
        if row and row[1] and now - row[1] < 3600: return generic                # at most one confirmation email per hour per address
        consent_id = s.p.ids.assign("CNS", "nl:" + email)
        s.db.execute("insert or replace into newsletter values(?,?,?,?,?,?,?,?,?,?)", (email, language, country, ",".join(sorted(topics)), "confirmed" if row and row[0] == "confirmed" else "pending", consent_id, s.CONSENT_VERSION, now, None, now)); s.db.commit()
        if row and row[0] == "confirmed": return generic
        return {**generic, "mail": {"to": email, "language": language, "confirm_token": s.caps.issue("newsletter_confirm", email, "confirm", ttl=48 * 3600, now=now)}}
    def confirm(s, token, now=None):
        email = s.caps.verify(token, "newsletter_confirm", "confirm", now=now)["subject"]
        s.db.execute("update newsletter set state='confirmed', confirmed=? where email=?", (now or time.time(), email)); s.db.commit(); return {"status": "subscribed"}
    def unsubscribe_token(s, email, now=None): return s.caps.issue("newsletter_unsubscribe", email, "unsubscribe", ttl=3650 * 86400, single_use=False, now=now)
    def unsubscribe(s, token, now=None):
        email = s.caps.verify(token, "newsletter_unsubscribe", "unsubscribe", now=now, consume=False)["subject"]
        s.db.execute("update newsletter set state='unsubscribed' where email=?", (email,)); s.db.commit(); return {"status": "unsubscribed"}   # one click, no login
    def state(s, email): r = s.db.execute("select state from newsletter where email=?", (email.lower(),)).fetchone(); return r[0] if r else None
    def delete(s, email): s.db.execute("delete from newsletter where email=?", (email.lower(),)); s.db.commit()   # the consent record id stays, the address does not
