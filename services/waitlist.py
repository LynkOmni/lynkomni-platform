"""Notify me: people ask to be told when a service reaches their country (global availability rule, 2026-11-06).
Only a reference to the contact is kept (the personal data stays in the PII vault), joining needs explicit consent,
and leaving is always possible. When a service becomes available in a country, due() lists who to tell, once."""
from providers import availability


class Waitlist:
    def __init__(s):
        s.rows = {}            # (service, country, contact_ref) -> {"notified": bool}

    def join(s, service, country, contact_ref, consent):
        if not consent:
            raise PermissionError("Notify me needs the person's consent")
        if not str(contact_ref).startswith("pii_"):
            raise ValueError("store the contact in the PII vault and pass its reference, never the phone or email itself")
        a = availability(service, country)
        if a["state"] == "available":
            return {"joined": False, "reason": "already available in this country"}
        s.rows.setdefault((service, a["country"], contact_ref), {"notified": False})
        return {"joined": True, "message": a["message"]}

    def leave(s, service, country, contact_ref):
        return s.rows.pop((service, (country or "").upper(), contact_ref), None) is not None

    def due(s):
        """Contacts to notify now: the service became available in their country. Each person is told once."""
        out = []
        for (service, country, ref), row in s.rows.items():
            if not row["notified"] and availability(service, country)["state"] == "available":
                row["notified"] = True
                out.append({"service": service, "country": country, "contact_ref": ref})
        return out
