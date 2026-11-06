"""PII vault and claims guard. Events carry only references, so deleting a person's data never breaks the append-only hash chain.
Claims guard: product copy may not say 'end-to-end' unless the product really is end-to-end encrypted."""
import re, secrets
PII_FIELDS = {"customer_name", "full_name", "phone", "email", "address", "note", "customer_note", "id_number"}
DEVICE_FORBIDDEN = {"phone", "email", "address", "note", "customer_note", "customer_name", "id_number"}   # never in a device event (product names are fine)
ENCRYPTION = {"business_chat": "transport+at_rest", "support_chat": "transport+at_rest"}   # no product is end-to-end encrypted
class PiiVault:
    def __init__(s, db):
        s.db = db; db.execute("create table if not exists pii_vault(ref text primary key, subject text, field text, value text)"); db.commit()
    def put(s, subject, field, value):
        ref = "pii_" + secrets.token_hex(8); s.db.execute("insert into pii_vault values(?,?,?,?)", (ref, subject, field, value)); s.db.commit(); return ref
    def get(s, ref):
        r = s.db.execute("select value from pii_vault where ref=?", (ref,)).fetchone(); return r[0] if r else None
    def delete_subject(s, subject):
        c = s.db.execute("delete from pii_vault where subject=?", (subject,)); s.db.commit(); return c.rowcount
    def scrub(s, subject, payload):
        """Replace personal fields with vault references. The event keeps its shape and its hash."""
        return {k: (s.put(subject, k, v) if k in PII_FIELDS and isinstance(v, str) else v) for k, v in payload.items()}
_PHONE, _EMAIL = re.compile(r"\+\d[\d ()-]{7,}\d|\b\d{10,}\b"), re.compile(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", re.I)
def contains_pii(value):
    return isinstance(value, str) and bool(_PHONE.search(value) or _EMAIL.search(value))
def assert_no_pii(event):
    """Device events must carry no phone numbers, emails or free-text notes."""
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in DEVICE_FORBIDDEN or walk(v): return True
        elif isinstance(x, list): return any(walk(i) for i in x)
        return contains_pii(x)
    if walk(event.get("payload", {})): raise ValueError("personal data found in a device event: use a vault reference")
def check_claim(product, text):
    if "end-to-end" in text.lower() and "e2ee" not in ENCRYPTION.get(product, ""):
        raise ValueError(f"{product} is not end-to-end encrypted: do not claim it")
    return text
